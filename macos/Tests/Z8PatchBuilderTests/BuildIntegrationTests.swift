import XCTest
@testable import Z8PatchBuilder

/// End-to-end checks with real firmware; skipped unless these are set:
///   Z8_APP          built "Z8 Patch Builder.app" (its bundled toolkit and Python are used)
///   Z8_STOCK        original Z_8_0311.bin (read only)
///   Z8_CLI_PYTHON   a separate interpreter with capstone 5.0.7 for the command-line reference
///   Z8_CLI_TOOLKIT  the extracted toolkit ZIP the app was built from
/// Every one of the 15 selections is built through the app's pipeline and through patch.py on the
/// command line; the firmware and checksum files must be byte-identical.
final class BuildIntegrationTests: XCTestCase {
    struct Env {
        let layout: ToolkitLayout
        let stock: URL
        let cliPython: URL
        let cliToolkit: URL
        let facts: InputFacts
    }

    func env() throws -> Env {
        let e = ProcessInfo.processInfo.environment
        guard let app = e["Z8_APP"], let stock = e["Z8_STOCK"], let py = e["Z8_CLI_PYTHON"], let tk = e["Z8_CLI_TOOLKIT"] else {
            throw XCTSkip("Set Z8_APP, Z8_STOCK, Z8_CLI_PYTHON and Z8_CLI_TOOLKIT to run firmware builds")
        }
        let resources = URL(fileURLWithPath: app).appendingPathComponent("Contents/Resources")
        let layout = ToolkitLayout(toolkit: resources.appendingPathComponent("toolkit"),
                                   python: resources.appendingPathComponent("runtime/bin/python3.12"))
        let (status, _) = Toolkit.inspect(layout)
        XCTAssertTrue(status.ok, status.problems.joined(separator: "; "))
        return Env(layout: layout, stock: URL(fileURLWithPath: stock), cliPython: URL(fileURLWithPath: py),
                   cliToolkit: URL(fileURLWithPath: tk), facts: status.input)
    }

    func scratch(_ name: String) throws -> URL {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("z8gui-it-\(name)-\(UUID())", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        addTeardownBlock { try? FileManager.default.removeItem(at: dir) }
        return dir
    }

    func request(_ env: Env, _ features: [FeatureID], input: URL? = nil, folder: URL) -> BuildRequest {
        BuildRequest(input: input ?? env.stock, features: features, version: "00.00", tag: "t0", outputFolder: folder,
                     codeSource: .prebuilt, compiler: "clang", expected: env.facts)
    }

    func cli(_ env: Env, _ args: [String]) async throws -> ToolOutput {
        try await ToolRunner(layout: env.layout).run(executable: env.cliPython,
                                                     arguments: ["-B", env.cliToolkit.appendingPathComponent("patch.py").path] + args,
                                                     onLine: { _ in })
    }

    func testAllFifteenSelectionsMatchCommandLine() async throws {
        let env = try env()
        let dir = try scratch("all")
        var rows: [String] = []
        for mask in 1..<16 {
            let features = FeatureID.allCases.enumerated().filter { mask & (1 << $0.offset) != 0 }.map(\.element)
            let label = features.map(\.short).joined(separator: "+")
            let appFolder = dir.appendingPathComponent("app-" + label)
            let outcome = try await BuildPipeline(runner: ToolRunner(layout: env.layout)).run(request(env, features, folder: appFolder)) { _ in }
            let cliFolder = dir.appendingPathComponent("cli-" + label)
            let out = try await cli(env, [env.stock.path, "--features"] + features.map(\.rawValue) +
                                    ["--version", "00.00", "--tag", "t0", "--output", cliFolder.path])
            XCTAssertEqual(out.status, 0, out.stderr)
            for name in ["Z_8_0000.bin", "SHA256SUMS.txt"] {
                let a = try Data(contentsOf: appFolder.appendingPathComponent(name))
                let b = try Data(contentsOf: cliFolder.appendingPathComponent(name))
                XCTAssertEqual(sha256Hex(a), sha256Hex(b), "\(label) \(name)")
            }
            // manifest.json differs only in source_hashes, which lists the files present beside patch.py:
            // the app bundles the runtime subset, the ZIP has everything. Shared entries must agree.
            var am = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: appFolder.appendingPathComponent("manifest.json"))) as? [String: Any])
            var cm = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: cliFolder.appendingPathComponent("manifest.json"))) as? [String: Any])
            let ah = try XCTUnwrap(am.removeValue(forKey: "source_hashes") as? [String: String])
            let ch = try XCTUnwrap(cm.removeValue(forKey: "source_hashes") as? [String: String])
            XCTAssertTrue(ah.allSatisfy { ch[$0.key] == $0.value }, label)
            XCTAssertEqual(NSDictionary(dictionary: am), NSDictionary(dictionary: cm), label)
            rows.append("\(label) \(outcome.sha256)")
        }
        let report = rows.joined(separator: "\n") + "\n"
        if let path = ProcessInfo.processInfo.environment["Z8_REPORT"] {
            try report.write(toFile: path, atomically: true, encoding: .utf8)
        }
        print(report)
        XCTAssertEqual(Set(rows.map { $0.split(separator: " ")[1] }).count, 15, "Every selection must give distinct bytes")
    }

    func testRejectsModifiedAndPatchedInputs() async throws {
        let env = try env()
        let dir = try scratch("inputs")
        let flipped = dir.appendingPathComponent("Z_8_0311.bin")
        var bytes = try Data(contentsOf: env.stock)
        bytes[0x2400000] ^= 1
        try bytes.write(to: flipped)
        let folder = dir.appendingPathComponent("out-flipped")
        do {
            _ = try await BuildPipeline(runner: ToolRunner(layout: env.layout)).run(request(env, [.videoRecording], input: flipped, folder: folder)) { _ in }
            XCTFail("Accepted a modified input")
        } catch let f as BuildFailure {
            XCTAssertEqual(f.step, 1)
        }
        XCTAssertFalse(FileManager.default.fileExists(atPath: folder.path))

        // A patched package is rejected by the toolkit itself, not only by the app's hash check.
        let built = dir.appendingPathComponent("built")
        _ = try await BuildPipeline(runner: ToolRunner(layout: env.layout)).run(request(env, [.logColour], folder: built)) { _ in }
        let check = try await ToolRunner(layout: env.layout).python("patch.py", [built.appendingPathComponent("Z_8_0000.bin").path, "--check"], onLine: { _ in })
        XCTAssertNotEqual(check.status, 0)
        XCTAssertEqual(check.errorLine, "ERROR: Input must match the official Nikon Z8 C 3.11 SHA-256; modified inputs are not supported")
    }

    func testExistingOutputFolderIsNeverTouched() async throws {
        let env = try env()
        let dir = try scratch("exists")
        let folder = dir.appendingPathComponent("taken")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
        let marker = folder.appendingPathComponent("keep.txt")
        try Data("mine".utf8).write(to: marker)
        do {
            _ = try await BuildPipeline(runner: ToolRunner(layout: env.layout)).run(request(env, [.videoRecording], folder: folder)) { _ in }
            XCTFail("Built into an existing folder")
        } catch let f as BuildFailure {
            XCTAssertEqual(f.step, 2)
            XCTAssertNil(f.cleanup)
        }
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: folder.path), ["keep.txt"])
    }

    func testCancelDuringBuildLeavesNoOutput() async throws {
        let env = try env()
        let dir = try scratch("cancel")
        let folder = dir.appendingPathComponent("out")
        let runner = ToolRunner(layout: env.layout)
        let task = Task { try await BuildPipeline(runner: runner).run(request(env, FeatureID.allCases, folder: folder)) { _ in } }
        // Step 1 (hash + --check) takes about a second; cancel while patch.py is composing.
        try await Task.sleep(for: .seconds(3))
        runner.cancel()
        do {
            _ = try await task.value
            XCTFail("Cancelled build reported success")
        } catch let f as BuildFailure {
            XCTAssertEqual(f.message, "Cancelled")
        } catch is ToolCancelled {}
        XCTAssertFalse(FileManager.default.fileExists(atPath: folder.path))
    }

    /// A toolkit whose verify.py fails: the app must not report success and must rename the .bin.
    func testVerificationFailureQuarantinesTheFirmware() async throws {
        let env = try env()
        let dir = try scratch("verify")
        let toolkit = dir.appendingPathComponent("toolkit", isDirectory: true)
        try FileManager.default.copyItem(at: env.layout.toolkit, to: toolkit)
        let verify = toolkit.appendingPathComponent("verify.py")
        let original = try String(contentsOf: verify, encoding: .utf8)
        // Keep verify_pair importable for patch.py's own in-process check; only the CLI entry point fails.
        try original.replacingOccurrences(of: "if __name__ == '__main__':", with: "if __name__ == '__main__':\n    raise SystemExit('ERROR: injected verification failure')\nif False:")
            .write(to: verify, atomically: true, encoding: .utf8)
        let layout = ToolkitLayout(toolkit: toolkit, python: env.layout.python)
        let folder = dir.appendingPathComponent("out")
        do {
            _ = try await BuildPipeline(runner: ToolRunner(layout: layout)).run(request(env, [.logColour], folder: folder)) { _ in }
            XCTFail("Verification failure reported success")
        } catch let f as BuildFailure {
            XCTAssertEqual(f.step, 3)
            XCTAssertEqual(f.message, "ERROR: injected verification failure")
            XCTAssertTrue(f.cleanup?.hasPrefix("renamed:") == true, f.cleanup ?? "nil")
        }
        let names = Set(try FileManager.default.contentsOfDirectory(atPath: folder.path))
        XCTAssertEqual(names, ["Z_8_0000.bin.unverified", "manifest.json", "SHA256SUMS.txt"])
    }

    func testSourceModeMatchesPrebuilt() async throws {
        let env = try env()
        let dir = try scratch("source")
        var r = request(env, FeatureID.allCases, folder: dir.appendingPathComponent("source"))
        r.codeSource = .source
        r.compiler = "/usr/bin/clang"
        let source = try await BuildPipeline(runner: ToolRunner(layout: env.layout)).run(r) { _ in }
        let prebuilt = try await BuildPipeline(runner: ToolRunner(layout: env.layout))
            .run(request(env, FeatureID.allCases, folder: dir.appendingPathComponent("prebuilt"))) { _ in }
        XCTAssertEqual(source.sha256, prebuilt.sha256)
        let check = await CompilerCheck.run("/usr/bin/clang", reviewed: Toolkit.inspect(env.layout).0.reviewedCompiler)
        XCTAssertEqual(check.verdict, .reviewed, check.versionLine)
    }
}
