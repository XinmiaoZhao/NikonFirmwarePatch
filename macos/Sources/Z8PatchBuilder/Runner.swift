import Foundation

/// Output of one toolkit process.
struct ToolOutput: Sendable {
    let status: Int32
    let stdout: String
    let stderr: String

    /// The toolkit reports failures as a final `ERROR: …` line (or argparse's `error:` line).
    var errorLine: String? {
        stderr.split(separator: "\n").map(String.init).last { $0.hasPrefix("ERROR: ") || $0.contains(": error: ") }
            ?? stderr.split(separator: "\n").last.map(String.init)
    }

    func json() -> [String: Any]? {
        guard let start = stdout.firstIndex(of: "{"), let end = stdout.lastIndex(of: "}") else { return nil }
        return (try? JSONSerialization.jsonObject(with: Data(stdout[start...end].utf8))) as? [String: Any]
    }
}

struct ToolCancelled: Error {}

/// Runs one Python process at a time and lets the caller cancel it (SIGTERM, then SIGKILL).
final class ToolRunner: @unchecked Sendable {
    let layout: ToolkitLayout
    private let lock = NSLock()
    private var current: Process?
    private var cancelled = false

    init(layout: ToolkitLayout) { self.layout = layout }

    func cancel() {
        lock.lock()
        cancelled = true
        let p = current
        lock.unlock()
        guard let p, p.isRunning else { return }
        p.terminate()
        DispatchQueue.global().asyncAfter(deadline: .now() + 3) {
            if p.isRunning { kill(p.processIdentifier, SIGKILL) }
        }
    }

    func resetCancel() {
        lock.lock(); cancelled = false; lock.unlock()
    }

    var isCancelled: Bool {
        lock.lock(); defer { lock.unlock() }
        return cancelled
    }

    /// `python <flags> <toolkit>/<script> <args…>`; every output line is passed to `onLine`.
    func python(_ script: String, _ args: [String], onLine: @escaping @Sendable (String) -> Void) async throws -> ToolOutput {
        try await run(executable: layout.python,
                      arguments: ToolkitLayout.pythonFlags + [layout.script(script).path] + args,
                      onLine: onLine)
    }

    func run(executable: URL, arguments: [String], onLine: @escaping @Sendable (String) -> Void) async throws -> ToolOutput {
        let process = Process()
        process.executableURL = executable
        process.arguments = arguments
        process.environment = ToolkitLayout.environment
        process.currentDirectoryURL = FileManager.default.temporaryDirectory
        process.standardInput = FileHandle.nullDevice
        let out = Pipe(), err = Pipe()
        process.standardOutput = out
        process.standardError = err
        let collector = OutputCollector(onLine: onLine)

        return try await withCheckedThrowingContinuation { continuation in
            let group = DispatchGroup()
            for (pipe, isErr) in [(out, false), (err, true)] {
                group.enter()
                pipe.fileHandleForReading.readabilityHandler = { handle in
                    let data = handle.availableData
                    if data.isEmpty {
                        handle.readabilityHandler = nil
                        group.leave()
                    } else {
                        collector.append(data, isErr: isErr)
                    }
                }
            }
            group.enter()
            process.terminationHandler = { _ in group.leave() }
            lock.lock()
            if cancelled {
                lock.unlock()
                continuation.resume(throwing: ToolCancelled())
                return
            }
            current = process
            do {
                try process.run()
                lock.unlock()
            } catch {
                current = nil
                lock.unlock()
                out.fileHandleForReading.readabilityHandler = nil
                err.fileHandleForReading.readabilityHandler = nil
                continuation.resume(throwing: error)
                return
            }
            group.notify(queue: .global()) { [self] in
                lock.lock()
                current = nil
                let wasCancelled = cancelled
                lock.unlock()
                let result = collector.finish(status: process.terminationStatus)
                if wasCancelled { continuation.resume(throwing: ToolCancelled()) }
                else { continuation.resume(returning: result) }
            }
        }
    }
}

private final class OutputCollector: @unchecked Sendable {
    private let lock = NSLock()
    private var stdout = Data(), stderr = Data()
    private var partial = [false: Data(), true: Data()]
    private let onLine: @Sendable (String) -> Void

    init(onLine: @escaping @Sendable (String) -> Void) { self.onLine = onLine }

    func append(_ data: Data, isErr: Bool) {
        lock.lock()
        if isErr { stderr.append(data) } else { stdout.append(data) }
        var buffer = partial[isErr]! + data
        var lines: [String] = []
        while let nl = buffer.firstIndex(of: 0x0A) {
            lines.append(String(decoding: buffer[buffer.startIndex..<nl], as: UTF8.self))
            buffer = Data(buffer[buffer.index(after: nl)...])
        }
        partial[isErr] = buffer
        lock.unlock()
        lines.forEach(onLine)
    }

    func finish(status: Int32) -> ToolOutput {
        lock.lock(); defer { lock.unlock() }
        for key in [false, true] where !(partial[key]!.isEmpty) {
            onLine(String(decoding: partial[key]!, as: UTF8.self))
        }
        return ToolOutput(status: status, stdout: String(decoding: stdout, as: UTF8.self),
                          stderr: String(decoding: stderr, as: UTF8.self))
    }
}

// MARK: - Build pipeline

struct BuildRequest: Sendable {
    var input: URL
    var features: [FeatureID]
    var version: String
    var tag: String
    var outputFolder: URL
    var codeSource: CodeSource
    var compiler: String
    var expected: InputFacts

    var fileName: String { "Z_8_" + version.replacingOccurrences(of: ".", with: "") + ".bin" }
    var featureArgs: [String] { features.map(\.rawValue) }
}

struct BuildOutcome: Sendable {
    var folder: URL
    var fileName: String
    var bytes: Int64
    var sha256: String
    var identity: String
    var features: [FeatureID]
}

/// Failure with the step it happened in and the toolkit's own message.
struct BuildFailure: Error, Sendable {
    let step: Int
    let message: String
    /// What the app did with an output folder created by this build (nil if none existed).
    var cleanup: String? = nil
}

enum CodeSource: String, CaseIterable, Identifiable, Sendable {
    case prebuilt, source
    var id: String { rawValue }
}

/// The four steps of README §4. `report(step, state)` drives the progress list.
struct BuildPipeline {
    enum Event: Sendable { case started(Int), finished(Int), log(String) }

    let runner: ToolRunner

    func run(_ r: BuildRequest, events: @escaping @Sendable (Event) -> Void) async throws -> BuildOutcome {
        let log: @Sendable (String) -> Void = { events(.log($0)) }
        let fm = FileManager.default
        func fail(_ step: Int, _ message: String) -> BuildFailure { BuildFailure(step: step, message: message) }

        // 1. Input: length and SHA-256 by the app, then the toolkit's read-only check.
        events(.started(1))
        log("$ sha256 " + r.input.path)
        guard let digest = sha256File(r.input), digest.bytes == r.expected.bytes, digest.sha256 == r.expected.sha256 else {
            throw fail(1, "Input is not the original Z8 C 3.11 (length or SHA-256 differs)")
        }
        log("  " + digest.sha256)
        log("$ patch.py " + r.input.lastPathComponent + " --check")
        let check = try await runner.python("patch.py", [r.input.path, "--check"], onLine: { log("  " + $0) })
        guard check.status == 0, let cj = check.json(), cj["status"] as? String == "COMPATIBLE",
              cj["input_sha256"] as? String == r.expected.sha256 else {
            throw fail(1, check.errorLine ?? "patch.py --check did not report COMPATIBLE")
        }
        events(.finished(1))

        // 2. Build into a folder that must not exist yet (the CLI creates it only after validation).
        events(.started(2))
        guard !fm.fileExists(atPath: r.outputFolder.path) else {
            throw fail(2, "Output folder already exists: " + r.outputFolder.path)
        }
        var args = [r.input.path, "--features"] + r.featureArgs + ["--version", r.version, "--tag", r.tag]
        if r.codeSource == .source { args += ["--code-source", "source", "--compiler", r.compiler] }
        args += ["--output", r.outputFolder.path]
        log("$ patch.py " + args.map { $0.contains(" ") ? "'\($0)'" : $0 }.joined(separator: " "))
        let built: ToolOutput
        do {
            built = try await runner.python("patch.py", args, onLine: { log("  " + $0) })
        } catch is ToolCancelled {
            throw BuildFailure(step: 2, message: "Cancelled", cleanup: removeIncomplete(r))
        }
        guard built.status == 0, let bj = built.json(), bj["status"] as? String == "BUILT_AND_LOCALLY_VERIFIED",
              let sha = bj["sha256"] as? String else {
            var failure = fail(2, built.errorLine ?? "patch.py did not report BUILT_AND_LOCALLY_VERIFIED")
            failure.cleanup = removeIncomplete(r)
            throw failure
        }
        let identity = bj["output_identity"] as? String ?? "\(r.version).\(r.tag)"
        events(.finished(2))

        let bin = r.outputFolder.appendingPathComponent(r.fileName)
        do {
            // 3. Independent verification in a separate process; verify.py never imports the builder.
            events(.started(3))
            let vargs = [r.input.path, bin.path, "--features"] + r.featureArgs + ["--version", r.version, "--tag", r.tag]
            log("$ verify.py " + vargs.joined(separator: " "))
            let verified = try await runner.python("verify.py", vargs, onLine: { log("  " + $0) })
            guard verified.status == 0, let vj = verified.json(), vj["status"] as? String == "PASS",
                  vj["output_sha256"] as? String == sha,
                  (vj["features"] as? [String])?.sorted() == r.featureArgs.sorted() else {
                throw fail(3, verified.errorLine ?? "verify.py did not report PASS for this build")
            }
            events(.finished(3))

            // 4. Read back the written files.
            events(.started(4))
            log("$ readback " + r.outputFolder.lastPathComponent)
            let names = Set((try? fm.contentsOfDirectory(atPath: r.outputFolder.path)) ?? [])
            guard names == [r.fileName, "manifest.json", "SHA256SUMS.txt"] else {
                throw fail(4, "Unexpected output files: " + names.sorted().joined(separator: ", "))
            }
            guard let back = sha256File(bin), back.sha256 == sha, back.bytes == r.expected.bytes else {
                throw fail(4, "Re-read .bin differs from the build report")
            }
            guard let mdata = try? Data(contentsOf: r.outputFolder.appendingPathComponent("manifest.json")),
                  let manifest = (try? JSONSerialization.jsonObject(with: mdata)) as? [String: Any],
                  manifest["output_sha256"] as? String == sha, manifest["output_filename"] as? String == r.fileName,
                  (manifest["output_bytes"] as? NSNumber)?.int64Value == back.bytes else {
                throw fail(4, "manifest.json does not match the written file")
            }
            let sums = (try? String(contentsOf: r.outputFolder.appendingPathComponent("SHA256SUMS.txt"), encoding: .utf8)) ?? ""
            guard sums == sha + "  " + r.fileName + "\n" else {
                throw fail(4, "SHA256SUMS.txt does not match the written file")
            }
            log("  sha256 \(sha) == manifest.json == SHA256SUMS.txt")
            events(.finished(4))
            return BuildOutcome(folder: r.outputFolder, fileName: r.fileName, bytes: back.bytes, sha256: sha,
                                identity: identity, features: r.features)
        } catch let failure as BuildFailure {
            var failure = failure
            failure.cleanup = quarantine(bin)
            throw failure
        } catch is ToolCancelled {
            // A cancelled verification leaves nothing behind that looks like a finished build.
            throw BuildFailure(step: 3, message: "Cancelled", cleanup: removeIncomplete(r))
        }
    }

    /// Cancelled or failed build: remove a folder that only holds this build's own outputs.
    private func removeIncomplete(_ r: BuildRequest) -> String? {
        let fm = FileManager.default
        guard fm.fileExists(atPath: r.outputFolder.path) else { return nil }
        let names = Set((try? fm.contentsOfDirectory(atPath: r.outputFolder.path)) ?? [])
        guard names.isSubset(of: [r.fileName, "manifest.json", "SHA256SUMS.txt"]),
              (try? fm.removeItem(at: r.outputFolder)) != nil else {
            return "kept:" + r.outputFolder.path
        }
        return "removed:" + r.outputFolder.path
    }

    /// Built but not verified: rename the .bin so it cannot be mistaken for an installable package.
    private func quarantine(_ bin: URL) -> String? {
        let fm = FileManager.default
        guard fm.fileExists(atPath: bin.path) else { return nil }
        let target = bin.appendingPathExtension("unverified")
        guard (try? fm.moveItem(at: bin, to: target)) != nil else { return "kept:" + bin.path }
        return "renamed:" + target.path
    }
}

// MARK: - Compiler check (source mode)

struct CompilerCheck: Sendable {
    enum Verdict: Sendable { case reviewed, different, missing }
    let verdict: Verdict
    let versionLine: String

    /// `<compiler> --version` with the same PATH the toolkit uses. Without developer tools the
    /// /usr/bin/clang shim would open an installer dialog, so check xcode-select first.
    static func run(_ compiler: String, reviewed: String?) async -> CompilerCheck {
        let runner = ToolRunner(layout: ToolkitLayout(toolkit: URL(fileURLWithPath: "/"), python: URL(fileURLWithPath: "/usr/bin/false")))
        if !compiler.contains("/") {
            let dev = try? await runner.run(executable: URL(fileURLWithPath: "/usr/bin/xcode-select"), arguments: ["-p"], onLine: { _ in })
            if dev?.status != 0 { return CompilerCheck(verdict: .missing, versionLine: "") }
        }
        guard let out = try? await runner.run(executable: URL(fileURLWithPath: "/usr/bin/env"),
                                              arguments: [compiler, "--version"], onLine: { _ in }),
              out.status == 0, let first = out.stdout.split(separator: "\n").first.map(String.init) else {
            return CompilerCheck(verdict: .missing, versionLine: "")
        }
        return CompilerCheck(verdict: first == reviewed ? .reviewed : .different, versionLine: first)
    }
}
