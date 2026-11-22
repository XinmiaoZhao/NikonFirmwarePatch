import XCTest
@testable import Z8PatchBuilder

/// Checks that need no firmware, interpreter or compiler.
final class UnitTests: XCTestCase {
    static let repo = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()

    func testRepositoryCatalogParses() throws {
        let data = try Data(contentsOf: Self.repo.appendingPathComponent("resources/gui-catalog.json"))
        let parsed = try Catalog.parse(data)
        XCTAssertEqual(parsed.features.map(\.id), FeatureID.allCases)
        for f in parsed.features {
            XCTAssertEqual(f.guide.count, FeatureGuide.timing[f.id]!.bounds.count, f.id.rawValue)
            XCTAssertFalse(f.limits.isEmpty)
        }
    }

    func testCatalogRejectsWrongIdsAndGuideLength() throws {
        let data = try Data(contentsOf: Self.repo.appendingPathComponent("resources/gui-catalog.json"))
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        var rows = try XCTUnwrap(json["features"] as? [[String: Any]])
        rows[0]["id"] = "video-recording-x"
        json["features"] = rows
        XCTAssertThrowsError(try Catalog.parse(JSONSerialization.data(withJSONObject: json)))
        rows[0]["id"] = "video-recording"
        rows[0]["guide"] = Array((rows[0]["guide"] as! [Any]).prefix(2))
        json["features"] = rows
        XCTAssertThrowsError(try Catalog.parse(JSONSerialization.data(withJSONObject: json)))
    }

    func testToolOutputParsing() {
        let ok = ToolOutput(status: 0, stdout: "noise\n{\n  \"status\": \"PASS\"\n}\n", stderr: "")
        XCTAssertEqual(ok.json()?["status"] as? String, "PASS")
        let bad = ToolOutput(status: 1, stdout: "", stderr: "Traceback…\nERROR: Output directory already exists; use a new directory\n")
        XCTAssertEqual(bad.errorLine, "ERROR: Output directory already exists; use a new directory")
        let usage = ToolOutput(status: 2, stdout: "", stderr: "usage: patch.py …\npatch.py: error: argument --features: invalid choice: 'x'\n")
        XCTAssertEqual(usage.errorLine, "patch.py: error: argument --features: invalid choice: 'x'")
    }

    func testRuntimeMemberRuleMatchesBuildScript() {
        XCTAssertTrue(Toolkit.isRuntimeMember("patch.py"))
        XCTAssertTrue(Toolkit.isRuntimeMember("resources/gui-catalog.json"))
        XCTAssertTrue(Toolkit.isRuntimeMember("z8pixelshift/src/nefx.c"))
        XCTAssertFalse(Toolkit.isRuntimeMember("docs/known-issues.md"))
        XCTAssertFalse(Toolkit.isRuntimeMember("luts/RWG_Log3G10_F_v1_65.cube"))
        XCTAssertFalse(Toolkit.isRuntimeMember("macos/Package.swift"))
        XCTAssertFalse(Toolkit.isRuntimeMember("tests/validate.py"))
        // Every toolkit package (including names with digits, such as z8h265) must be bundled.
        let dirs = try! FileManager.default.contentsOfDirectory(atPath: Self.repo.path).filter { $0.hasPrefix("z8") }
        XCTAssertGreaterThanOrEqual(dirs.count, 9)
        for d in dirs { XCTAssertTrue(Toolkit.isRuntimeMember(d + "/__init__.py"), d) }
    }

    /// A toolkit directory is accepted only if every file matches the manifest and nothing is missing.
    func testToolkitIntegrityNegativeControls() throws {
        let fm = FileManager.default
        let dir = fm.temporaryDirectory.appendingPathComponent("z8gui-integrity-\(UUID())", isDirectory: true)
        defer { try? fm.removeItem(at: dir) }
        let toolkit = dir.appendingPathComponent("toolkit", isDirectory: true)
        try fm.createDirectory(at: toolkit.appendingPathComponent("resources"), withIntermediateDirectories: true)
        let python = dir.appendingPathComponent("python3.12")
        try Data("#!/bin/sh\n".utf8).write(to: python)
        try fm.setAttributes([.posixPermissions: 0o755], ofItemAtPath: python.path)
        let catalog = try Data(contentsOf: Self.repo.appendingPathComponent("resources/gui-catalog.json"))
        let input = Data(#"{"id": "x", "bytes": 99051117, "sha256": "ab"}"#.utf8)
        let members: [String: Data] = ["patch.py": Data("print()\n".utf8), "resources/gui-catalog.json": catalog,
                                       "resources/input.json": input]
        for (name, raw) in members { try raw.write(to: toolkit.appendingPathComponent(name)) }
        func writeManifest(_ files: [String: Data]) throws {
            let record: [String: Any] = ["schema": 2, "tag": "v0.0.0-rc.1", "source_commit": String(repeating: "0", count: 40),
                                         "files": files.mapValues { ["bytes": $0.count, "sha256": sha256Hex($0)] }]
            try JSONSerialization.data(withJSONObject: record).write(to: toolkit.appendingPathComponent("release-manifest.json"))
        }
        let layout = ToolkitLayout(toolkit: toolkit, python: python)
        try writeManifest(members)
        XCTAssertTrue(Toolkit.inspect(layout).0.ok, Toolkit.inspect(layout).0.problems.joined(separator: "; "))

        try Data("print(1)\n".utf8).write(to: toolkit.appendingPathComponent("patch.py"))
        XCTAssertTrue(Toolkit.inspect(layout).0.problems.contains("Differs from the release manifest: patch.py"))
        try members["patch.py"]!.write(to: toolkit.appendingPathComponent("patch.py"))

        try Data().write(to: toolkit.appendingPathComponent("resources/extra.json"))
        XCTAssertTrue(Toolkit.inspect(layout).0.problems.contains("Unlisted file: resources/extra.json"))
        try fm.removeItem(at: toolkit.appendingPathComponent("resources/extra.json"))

        var listed = members
        listed["verify.py"] = Data("x".utf8)
        try writeManifest(listed)
        XCTAssertTrue(Toolkit.inspect(layout).0.problems.contains("Missing: verify.py"))
    }

    @MainActor func testOutputFolderNamingNeverReusesAFolder() throws {
        let fm = FileManager.default
        let parent = fm.temporaryDirectory.appendingPathComponent("z8gui-names-\(UUID())", isDirectory: true)
        try fm.createDirectory(at: parent, withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: parent) }
        let model = BuilderModel(layout: nil)
        model.outputParent = parent
        model.version = "04.08"
        model.tag = "p0"
        model.selected = [.stillPhotoTools, .videoRecording]
        model.refreshOutputName()
        XCTAssertEqual(model.outputFolderName, "Z8-04.08.p0-video+photo")
        XCTAssertEqual(model.outputFileName, "Z_8_0408.bin")
        try fm.createDirectory(at: parent.appendingPathComponent("Z8-04.08.p0-video+photo"), withIntermediateDirectories: false)
        model.refreshOutputName()
        XCTAssertEqual(model.outputFolderName, "Z8-04.08.p0-video+photo 2")
        model.version = "4.6"
        XCTAssertFalse(model.versionValid)
        model.version = "00.01"
        XCTAssertTrue(model.offlineOnlyVersion)
        model.tag = "P0"
        XCTAssertFalse(model.tagValid)
    }

    /// "System" follows macOS's localization rule over the preferred-language list, not only its first entry.
    func testSystemLanguageMatching() {
        XCTAssertEqual(Lang.matching(["en-CN", "zh-Hans-CN", "zh-Hant-CN"]), .en)
        XCTAssertEqual(Lang.matching(["zh-Hans-CN", "en-US"]), .zhHans)
        XCTAssertEqual(Lang.matching(["ja-JP", "zh-Hans-CN", "en-US"]), .zhHans)
        XCTAssertEqual(Lang.matching(["ja-JP", "zh-Hant-TW", "zh-Hans-CN"]), .zhHant)
        XCTAssertEqual(Lang.matching(["de-DE", "fr-FR"]), .en)
        for traditional in ["zh-Hant-TW", "zh-Hant-HK", "zh-Hant-MO", "zh-TW", "zh-HK", "yue-Hant-HK"] {
            XCTAssertEqual(Lang.matching([traditional, "en-US"]), .zhHant, traditional)
        }
        for simplified in ["zh-CN", "zh-SG", "zh-Hans-HK"] {
            XCTAssertEqual(Lang.matching([simplified, "en-US"]), .zhHans, simplified)
        }
        XCTAssertEqual(Lang.matching([]), .en)
    }

    /// Catalog text must carry every UI language; a missing one is a load error, not an empty label.
    func testCatalogTextNeedsEveryLanguage() throws {
        let full = Data(#"{"en": "Framing", "zh-Hans": "画幅", "zh-Hant": "畫幅"}"#.utf8)
        let text = try JSONDecoder().decode(L.self, from: full)
        XCTAssertEqual(Lang.allCases.map { text($0) }, ["Framing", "画幅", "畫幅"])
        for broken in [#"{"en": "Framing", "zh-Hans": "画幅"}"#, #"{"en": "Framing", "zh": "画幅", "zh-Hant": "畫幅"}"#,
                       #"{"en": "Framing", "zh-Hans": "画幅", "zh-Hant": "畫幅", "ja": "画角"}"#] {
            XCTAssertThrowsError(try JSONDecoder().decode(L.self, from: Data(broken.utf8)), broken)
        }
    }

    /// The System entry names what choosing it gives. With a fixed language stored, Locale.preferredLanguages
    /// is this app's own override, which choosing System removes (the user saw "System (繁體中文)" while
    /// 繁體中文 was stored, then got English).
    func testSystemOptionNamesWhatSystemGives() throws {
        let user = ["en-CN", "zh-Hans-CN", "zh-Hant-CN"]
        for fixed in [LanguagePreference.zhHans, .zhHant, .en] {
            let own = try XCTUnwrap(fixed.appleLanguages)
            XCTAssertEqual(LanguagePreference.systemLang(current: fixed, preferred: own, withoutAppDomain: user), .en, fixed.rawValue)
        }
        XCTAssertEqual(LanguagePreference.systemLang(current: .en, preferred: ["en"], withoutAppDomain: ["zh-Hant-TW", "en-US"]), .zhHant)
        XCTAssertEqual(LanguagePreference.systemLang(current: .zhHant, preferred: ["zh-Hant"], withoutAppDomain: []), .en)
        // With System stored, AppleLanguages in the app's domain is System Settings' per-app language.
        XCTAssertEqual(LanguagePreference.systemLang(current: .system, preferred: ["zh-Hant"], withoutAppDomain: user), .zhHant)
        XCTAssertEqual(LanguagePreference.systemLang(current: .system, preferred: user, withoutAppDomain: user), .en)
    }

    /// The AppleLanguages override must already be updated when observers of the preference fire
    /// (@AppStorage re-renders through key-value observation), or "System" resolves against the old override.
    func testLanguageStoreOrder() throws {
        // A suite named by an absolute path keeps its plist in that folder, not in ~/Library/Preferences
        // (cfprefsd writes an empty plist there even after the domain is removed).
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("z8gui-test-language-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        addTeardownBlock { try? FileManager.default.removeItem(at: dir) }
        let name = dir.appendingPathComponent("prefs").path
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defer { defaults.removePersistentDomain(forName: name) }
        let observer = PreferenceObserver(defaults: defaults, domain: name)
        defaults.addObserver(observer, forKeyPath: LanguagePreference.key, options: [.new], context: nil)
        defer { defaults.removeObserver(observer, forKeyPath: LanguagePreference.key) }

        LanguagePreference.zhHans.store(in: defaults)
        LanguagePreference.system.store(in: defaults)
        LanguagePreference.zhHant.store(in: defaults)
        LanguagePreference.en.store(in: defaults)
        XCTAssertEqual(observer.seen.map(\.preference), ["zh-Hans", "system", "zh-Hant", "en"])
        XCTAssertEqual(observer.seen.map(\.appleLanguages), [["zh-Hans"], nil, ["zh-Hant"], ["en"]])
    }
}

private final class PreferenceObserver: NSObject {
    let defaults: UserDefaults
    let domain: String
    var seen: [(preference: String?, appleLanguages: [String]?)] = []

    init(defaults: UserDefaults, domain: String) {
        self.defaults = defaults
        self.domain = domain
    }

    override func observeValue(forKeyPath keyPath: String?, of object: Any?, change: [NSKeyValueChangeKey: Any]?, context: UnsafeMutableRawPointer?) {
        let own = defaults.persistentDomain(forName: domain)
        seen.append((defaults.string(forKey: LanguagePreference.key), own?["AppleLanguages"] as? [String]))
    }
}
