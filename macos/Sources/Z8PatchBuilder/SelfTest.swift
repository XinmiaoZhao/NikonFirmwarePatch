import Foundation

/// `Z8PatchBuilder --self-test`: toolkit members against release-manifest.json, the feature catalog,
/// and the bundled interpreter importing the toolkit (`patch.py --help` imports features and capstone).
/// Prints JSON and returns the exit status. Reads no firmware and writes nothing.
enum SelfTest {
    static func run() -> Int32 {
        let layout = ToolkitLayout.locate()
        let (status, parsed) = Toolkit.inspect(layout)
        var report: [String: Any] = [
            "toolkit_tag": status.tag, "toolkit_commit": status.commit,
            "toolkit_files_checked": status.checkedFiles, "problems": status.problems,
            "catalog_features": parsed?.features.map(\.id.rawValue) ?? [],
            "reviewed_compiler": status.reviewedCompiler ?? NSNull(),
        ]
        var ok = status.ok && parsed != nil
        if let layout, status.ok {
            let help = runBlocking(layout.python, ToolkitLayout.pythonFlags + [layout.script("patch.py").path, "--help"])
            // Import every bundled module, not only those patch.py imports at start-up.
            let modules = toolkitModules(layout.toolkit)
            let imports = runBlocking(layout.python, ToolkitLayout.pythonFlags + ["-c",
                "import importlib, sys; sys.path.insert(0, sys.argv[1]); [importlib.import_module(m) for m in sys.argv[2:]]",
                layout.toolkit.path] + modules)
            report["modules_imported"] = imports.status == 0 ? modules.count : 0
            if imports.status != 0 { report["import_stderr"] = imports.stderr }
            let version = runBlocking(layout.python, ToolkitLayout.pythonFlags + ["-c", "import sys, capstone; print(sys.version.split()[0], capstone.__version__)"])
            report["patch_help_exit"] = help.status
            report["python_capstone"] = version.stdout.trimmingCharacters(in: .whitespacesAndNewlines)
            ok = ok && help.status == 0 && help.stdout.contains("--features") && version.status == 0
                && imports.status == 0 && modules.count > 10
            if help.status != 0 { report["patch_help_stderr"] = help.stderr }
        }
        report["status"] = ok ? "PASS" : "FAIL"
        let data = try! JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
        FileHandle.standardOutput.write(data + Data("\n".utf8))
        return ok ? 0 : 1
    }

    /// `features`, `verify` and every module under the z8 packages, as dotted names.
    static func toolkitModules(_ root: URL) -> [String] {
        var names = ["features", "verify"]
        let fm = FileManager.default
        for dir in ((try? fm.contentsOfDirectory(atPath: root.path)) ?? []).sorted() where dir.hasPrefix("z8") {
            guard let walker = fm.enumerator(atPath: root.appendingPathComponent(dir).path) else { continue }
            for case let rel as String in walker where rel.hasSuffix(".py") {
                let parts = (dir + "/" + rel).dropLast(3).split(separator: "/").map(String.init)
                names.append((parts.last == "__init__" ? parts.dropLast() : parts[...]).joined(separator: "."))
            }
        }
        return names.sorted()
    }

    private static func runBlocking(_ exe: URL, _ args: [String]) -> ToolOutput {
        let p = Process()
        p.executableURL = exe
        p.arguments = args
        p.environment = ToolkitLayout.environment
        p.currentDirectoryURL = FileManager.default.temporaryDirectory
        let out = Pipe(), err = Pipe()
        p.standardOutput = out
        p.standardError = err
        do { try p.run() } catch { return ToolOutput(status: -1, stdout: "", stderr: error.localizedDescription) }
        let o = out.fileHandleForReading.readDataToEndOfFile()
        let e = err.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        return ToolOutput(status: p.terminationStatus, stdout: String(decoding: o, as: UTF8.self), stderr: String(decoding: e, as: UTF8.self))
    }
}
