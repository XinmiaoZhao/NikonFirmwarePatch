import CryptoKit
import Foundation

/// Where the bundled toolkit and interpreter live. `Z8_TOOLKIT_DIR` + `Z8_PYTHON` override the
/// bundle for development runs (`swift run`) and tests.
struct ToolkitLayout: Sendable {
    let toolkit: URL
    let python: URL

    /// Interpreter flags: ignore PYTHON* variables and user site-packages, never write bytecode into
    /// the signed bundle, UTF-8 I/O. Not -I: isolated mode also drops the script directory from
    /// sys.path, which the toolkit's own imports need.
    static let pythonFlags = ["-E", "-s", "-B", "-X", "utf8"]

    /// Child processes get a fixed environment; clang (source mode) resolves through /usr/bin.
    static var environment: [String: String] {
        ["PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
         "HOME": NSHomeDirectory(), "TMPDIR": NSTemporaryDirectory()]
    }

    static func locate() -> ToolkitLayout? {
        let env = ProcessInfo.processInfo.environment
        if let t = env["Z8_TOOLKIT_DIR"], let p = env["Z8_PYTHON"] {
            return ToolkitLayout(toolkit: URL(fileURLWithPath: t, isDirectory: true), python: URL(fileURLWithPath: p))
        }
        guard let resources = Bundle.main.resourceURL else { return nil }
        return ToolkitLayout(toolkit: resources.appendingPathComponent("toolkit", isDirectory: true),
                             python: resources.appendingPathComponent("runtime/bin/python3.12"))
    }

    func script(_ name: String) -> URL { toolkit.appendingPathComponent(name) }
}

struct ReleaseManifest: Decodable {
    struct File: Decodable { let bytes: Int; let sha256: String }
    let schema: Int
    let tag: String
    let source_commit: String
    let files: [String: File]
}

struct InputFacts: Decodable, Sendable {
    let bytes: Int64
    let sha256: String
}

struct ToolkitStatus: Sendable {
    var tag = "—"
    var commit = "—"
    var checkedFiles = 0
    var problems: [String] = []
    var reviewedCompiler: String?
    var input = InputFacts(bytes: 99_051_117, sha256: "")
    var ok: Bool { problems.isEmpty }
}

enum Toolkit {
    /// Members the app needs; matches toolkit_member() in macos/scripts/build_app.py.
    static func isRuntimeMember(_ name: String) -> Bool {
        ["patch.py", "features.py", "verify.py", "LICENSE", "NOTICE.md"].contains(name)
            || name.hasPrefix("resources/")
            || name.range(of: #"^z8[a-z0-9]+/"#, options: .regularExpression) != nil
    }

    /// Checks every bundled toolkit file against release-manifest.json and loads the catalog.
    static func inspect(_ layout: ToolkitLayout?) -> (ToolkitStatus, ParsedCatalog?) {
        var status = ToolkitStatus()
        guard let layout else {
            status.problems = ["Bundled toolkit not found"]
            return (status, nil)
        }
        let fm = FileManager.default
        let root = layout.toolkit.standardizedFileURL
        guard let data = try? Data(contentsOf: root.appendingPathComponent("release-manifest.json")),
              let manifest = try? JSONDecoder().decode(ReleaseManifest.self, from: data), manifest.schema == 2 else {
            status.problems = ["release-manifest.json missing or unreadable"]
            return (status, nil)
        }
        status.tag = manifest.tag
        status.commit = manifest.source_commit
        var seen = Set<String>()
        if let walker = fm.enumerator(at: root, includingPropertiesForKeys: [.isRegularFileKey], options: []) {
            for case let url as URL in walker {
                guard (try? url.resourceValues(forKeys: [.isRegularFileKey]))?.isRegularFile == true else { continue }
                let rel = String(url.standardizedFileURL.path.dropFirst(root.path.count + 1))
                if rel == "release-manifest.json" { continue }
                seen.insert(rel)
                guard let expected = manifest.files[rel] else {
                    status.problems.append("Unlisted file: " + rel)
                    continue
                }
                guard let bytes = try? Data(contentsOf: url), bytes.count == expected.bytes,
                      sha256Hex(bytes) == expected.sha256 else {
                    status.problems.append("Differs from the release manifest: " + rel)
                    continue
                }
                status.checkedFiles += 1
            }
        }
        for name in manifest.files.keys.sorted() where isRuntimeMember(name) && !seen.contains(name) {
            status.problems.append("Missing: " + name)
        }
        if !fm.isExecutableFile(atPath: layout.python.path) {
            status.problems.append("Bundled Python not found")
        }
        if let raw = try? Data(contentsOf: root.appendingPathComponent("resources/input.json")),
           let facts = try? JSONDecoder().decode(InputFacts.self, from: raw) {
            status.input = facts
        } else {
            status.problems.append("resources/input.json unreadable")
        }
        if let raw = try? Data(contentsOf: root.appendingPathComponent("resources/compiled.json")),
           let json = try? JSONSerialization.jsonObject(with: raw) as? [String: Any],
           let units = json["units"] as? [String: [String: Any]] {
            let compilers = Set(units.values.compactMap { $0["compiler"] as? String })
            status.reviewedCompiler = compilers.count == 1 ? compilers.first : nil
        }
        var parsed: ParsedCatalog?
        do {
            parsed = try Catalog.parse(Data(contentsOf: root.appendingPathComponent("resources/gui-catalog.json")))
        } catch {
            status.problems.append("gui-catalog.json: " + error.localizedDescription)
        }
        return (status, parsed)
    }
}

func sha256Hex(_ data: Data) -> String {
    SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
}

/// Streaming SHA-256 of a file with progress callbacks.
func sha256File(_ url: URL, progress: ((Double) -> Void)? = nil) -> (bytes: Int64, sha256: String)? {
    guard let handle = try? FileHandle(forReadingFrom: url),
          let size = (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber)?.int64Value
    else { return nil }
    defer { try? handle.close() }
    var hasher = SHA256()
    var done: Int64 = 0
    var lastReport = 0.0
    while let chunk = try? handle.read(upToCount: 4 << 20), !chunk.isEmpty {
        hasher.update(data: chunk)
        done += Int64(chunk.count)
        let f = size > 0 ? Double(done) / Double(size) : 1
        if f - lastReport > 0.04 { lastReport = f; progress?(f) }
    }
    return (done, hasher.finalize().map { String(format: "%02x", $0) }.joined())
}
