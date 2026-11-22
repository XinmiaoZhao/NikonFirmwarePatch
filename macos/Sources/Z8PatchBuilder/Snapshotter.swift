#if DEBUG
import AppKit
import SwiftUI

/// `-snapshotDir <dir> -snapshotPrefix <prefix>`: walks fixed preview states and renders them to PNG,
/// then quits. Rendering is offscreen (no Screen Recording permission). On macOS 26, in-window
/// `cacheDisplay` drops ScrollView and glass content, so each state is composed from the same SwiftUI
/// views in a borderless offscreen window; the title strip in these images is a drawn stand-in for the
/// system title bar. The live app is the authoritative preview.
enum Snapshotter {
    @MainActor static var activity: NSObjectProtocol?

    @MainActor static func startIfRequested(model: BuilderModel) {
        // Passed through the argument domain; a bare path in argv would be treated by AppKit as a
        // document to open and suppress the main window.
        guard let path = UserDefaults.standard.string(forKey: "snapshotDir") else { return }
        let dir = URL(fileURLWithPath: path, isDirectory: true)
        let prefix = UserDefaults.standard.string(forKey: "snapshotPrefix") ?? "shot"
        // Keep timers running while in the background (App Nap stalled an earlier walk).
        activity = ProcessInfo.processInfo.beginActivity(options: [.userInitiated, .latencyCritical], reason: "UI snapshots")
        Task { @MainActor in
            await run(model: model, dir: dir, prefix: prefix)
            NSApp.terminate(nil)
        }
    }

    @MainActor private static func pause(_ s: Double = 0.5) async {
        try? await Task.sleep(for: .seconds(s))
    }

    @MainActor private static func ready(_ model: BuilderModel, _ selection: [FeatureID], focus: FeatureID, stock: URL?) async {
        if let stock {
            if case .checked(let info) = model.input, info.url == stock, info.isValid {} else {
                model.loadInput(stock)
                for _ in 0..<200 {
                    if case .checked(let info) = model.input, info.toolkitCheck != .running { break }
                    await pause(0.1)
                }
            }
        } else {
            model.mockValidInput()
        }
        model.selected = Set(selection)
        model.focused = focus
        model.version = BuilderModel.defaultVersion
        model.tag = "p0"
        model.showInspector = true
        model.showAdvanced = false
        model.refreshOutputName()
    }

    @MainActor private static func waitForBuild(_ model: BuilderModel) async {
        for _ in 0..<1200 where model.stage == .running { await pause(0.1) }
    }

    @MainActor static func run(model: BuilderModel, dir: URL, prefix: String) async {
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        for _ in 0..<100 where !model.toolkitInspected { await pause(0.1) }
        await pause(1.0)
        let lang = (UserDefaults.standard.string(forKey: "languagePreference").flatMap(LanguagePreference.init(rawValue:)) ?? .system).resolved
        let dark = UserDefaults.standard.string(forKey: "appearancePreference") == "dark"
        let appearance = NSAppearance(named: dark ? .darkAqua : .aqua)!
        // `-snapshotStock <Z_8_0311.bin>` runs real checks and builds into a temporary folder.
        let stock = UserDefaults.standard.string(forKey: "snapshotStock").map { URL(fileURLWithPath: $0) }
        let work = FileManager.default.temporaryDirectory.appendingPathComponent("z8gui-snapshots-" + prefix, isDirectory: true)
        try? FileManager.default.removeItem(at: work)
        try? FileManager.default.createDirectory(at: work, withIntermediateDirectories: true)
        model.outputParent = work

        var guideTime: Double = 7.2
        func shot<V: View>(_ name: String, width: CGFloat, @ViewBuilder _ view: () -> V) async {
            let root = view()
                .environment(\.lang, lang)
                .environment(\.locale, lang.locale)
                .environment(\.guideFixedTime, guideTime)
            await render(root, width: width, appearance: appearance, to: dir.appendingPathComponent("\(prefix)-\(name).png"))
            FileHandle.standardError.write("snapshot: \(name)\n".data(using: .utf8)!)
        }

        model.resetForSnapshots()
        model.focused = .videoRecording
        await shot("01-empty", width: 1300) { WindowMock(model: model) }

        await ready(model, [.videoRecording, .logColour, .stillPhotoTools], focus: .stillPhotoTools, stock: stock)
        await shot("02-ready", width: 1300) { WindowMock(model: model) }
        await shot("03-page-full", width: 900) {
            MainPageContent(model: model).frame(width: 900).background(Color.pageBackground)
        }

        await ready(model, FeatureID.allCases, focus: .rawPrecapture, stock: stock)
        model.showAdvanced = true
        model.codeSource = .source
        for _ in 0..<50 where model.checkingCompiler { await pause(0.1) }
        await shot("04-photo-inspector", width: 1300) { WindowMock(model: model, scrollOffset: 700) }
        model.codeSource = .prebuilt
        for f in FeatureID.allCases {
            model.focused = f
            await shot("inspector-\(f.rawValue)", width: 380) {
                FeatureDetail(feature: Catalog.feature(f), model: model)
                    .padding(20).frame(width: 380).background(Color.cardBackground)
            }
        }

        model.showAdvanced = false
        await shot("13-minimum-size", width: 1040) { WindowMock(model: model, width: 980, height: 660) }
        let savedInput = model.input
        model.mockInvalidInput()
        model.selected = [.videoRecording]
        model.focused = .videoRecording
        model.showAdvanced = false
        await shot("05-invalid-input", width: 1300) { WindowMock(model: model) }
        model.input = savedInput

        await ready(model, [.videoRecording, .logColour, .stillPhotoTools], focus: .stillPhotoTools, stock: stock)
        model.beginBuild()
        model.showFlow = false   // keep the real window free of sheets; the mock draws it
        await shot("06-risk", width: 1300) { WindowMock(model: model, sheet: AnyView(RiskConfirmView(model: model))) }
        model.showSelectedLimits = true
        model.acknowledged = true
        await shot("07-risk-expanded", width: 1300) { WindowMock(model: model, height: 1000, sheet: AnyView(RiskConfirmView(model: model))) }

        if stock != nil {
            // A real build of all four groups as 04.08.p0 (the README example), into the temporary folder.
            await ready(model, FeatureID.allCases, focus: .videoRecording, stock: stock)
            model.beginBuild()
            model.showFlow = false
            model.acknowledged = true
            model.showLog = true
            model.startBuild()
            for _ in 0..<600 where !(model.steps.count == 4 && model.steps[2].state == .running) { await pause(0.05) }
            await shot("08-progress", width: 1300) { WindowMock(model: model, sheet: AnyView(ProgressStageView(model: model))) }
            await waitForBuild(model)
            model.showLog = false
            await shot("09-result", width: 1300) { WindowMock(model: model, sheet: AnyView(model.stage == .succeeded ? AnyView(ResultView(model: model)) : AnyView(ProgressStageView(model: model)))) }
            if let r = model.result { FileHandle.standardError.write("snapshot build: \(r.identity) \(r.sha256)\n".data(using: .utf8)!) }
            // A real cancellation during the build step.
            model.beginBuild()
            model.showFlow = false
            model.acknowledged = true
            model.startBuild()
            for _ in 0..<600 where !(model.steps.count == 4 && model.steps[1].state == .running) { await pause(0.05) }
            await pause(1.5)
            model.cancelBuild()
            await waitForBuild(model)
            model.showLog = true
            await shot("10-cancelled", width: 1300) { WindowMock(model: model, sheet: AnyView(ProgressStageView(model: model))) }
            model.showLog = false
        }

        let times: [FeatureID: [Double]] = [
            .videoRecording: [1.0, 3.5, 4.9, 6.6, 9.4, 11.5, 12.9, 15.5, 17.0, 19.4, 21.7, 23.4],
            .logColour: [0.9, 3.5, 4.8, 7.0, 9.0, 11.2],
            .stillPhotoTools: [1.0, 3.5, 4.6, 6.8, 8.8, 11.5, 13.0, 15.5, 16.8, 19.0, 21.0, 23.4],
            .rawPrecapture: [1.2, 3.6, 5.5, 7.6, 9.0, 11.5],
        ]
        for f in FeatureID.allCases {
            await shot("guide-\(f.rawValue)", width: 1300) { GuideStrip(id: f, times: times[f]!) }
        }
        guideTime = 7.2
        await shot("12-guide-sheet", width: 940) {
            GuideSheet(feature: Catalog.feature(.videoRecording))
                .frame(width: 880)
                .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(Color.cardBackground))
                .padding(30)
                .background(Color.backdrop)
        }
        guideTime = 7.2

        await shot("11-settings", width: 600) {
            SettingsMock(model: model).frame(width: 540).padding(30).background(Color.backdrop)
        }
        await shot("11b-settings-relaunch", width: 600) {
            SettingsMock(model: model, menuBar: lang == .en ? .zhHans : .en).frame(width: 540).padding(30).background(Color.backdrop)
        }
        try? FileManager.default.removeItem(at: work)
    }

    @MainActor private static func render<V: View>(_ root: V, width: CGFloat, appearance: NSAppearance, to url: URL) async {
        let host = NSHostingView(rootView: root)
        host.appearance = appearance
        let size = host.fittingSize
        let frame = NSRect(x: -6000, y: -6000, width: max(width, size.width), height: size.height)
        let window = NSWindow(contentRect: frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.appearance = appearance
        window.isOpaque = false
        window.backgroundColor = .clear
        window.contentView = host
        host.frame = NSRect(origin: .zero, size: frame.size)
        window.orderBack(nil)
        await pause(0.8)
        if let rep = host.bitmapImageRepForCachingDisplay(in: host.bounds) {
            host.cacheDisplay(in: host.bounds, to: rep)
            try? rep.representation(using: .png, properties: [:])?.write(to: url)
        }
        window.orderOut(nil)
    }
}

/// `-sheetProbe <file.json>`: opens the risk sheet in the real window, expands and collapses the
/// known-limits disclosure, and records the sheet window's frame every 4 ms, then quits. A sheet
/// window that follows the content animation shows many intermediate heights; one that jumps shows a
/// single step.
enum SheetProbe {
    private final class Samples: @unchecked Sendable { var rows: [[Double]] = [] }  // main thread only

    @MainActor static func startIfRequested(model: BuilderModel) {
        guard let path = UserDefaults.standard.string(forKey: "sheetProbe") else { return }
        Snapshotter.activity = ProcessInfo.processInfo.beginActivity(options: [.userInitiated, .latencyCritical], reason: "Sheet probe")
        Task { @MainActor in
            var record: [String: Any] = [:]
            for _ in 0..<100 where !model.toolkitInspected { try? await Task.sleep(for: .seconds(0.1)) }
            model.mockValidInput()
            model.selected = Set(FeatureID.allCases)
            model.version = BuilderModel.defaultVersion
            model.tag = "p0"
            model.outputParent = FileManager.default.temporaryDirectory
            model.refreshOutputName()
            model.beginBuild()
            try? await Task.sleep(for: .seconds(1.5))
            if let sheet = NSApp.windows.first(where: { $0.isSheet && $0.isVisible }) {
                var runs: [[String: Any]] = []
                for expand in [true, false] {
                    let samples = Samples()
                    let start = CACurrentMediaTime()
                    let timer = Timer(timeInterval: 0.004, repeats: true) { _ in
                        MainActor.assumeIsolated {
                            samples.rows.append([CACurrentMediaTime() - start, sheet.frame.height, sheet.frame.maxY])
                        }
                    }
                    RunLoop.main.add(timer, forMode: .common)
                    try? await Task.sleep(for: .seconds(0.15))
                    withAnimation(SheetDisclosure<EmptyView, EmptyView>.animation) { model.showSelectedLimits = expand }
                    try? await Task.sleep(for: .seconds(0.6))
                    timer.invalidate()
                    runs.append(["expand": expand, "toggle_at": 0.15, "samples": samples.rows])
                }
                record["runs"] = runs
                record["limit_count"] = model.selectedLimitCount
            } else {
                record["error"] = "no visible sheet window"
            }
            if let data = try? JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted]) {
                try? data.write(to: URL(fileURLWithPath: path))
            }
            model.showFlow = false
            NSApp.terminate(nil)
        }
    }
}

/// `-languageProbe <json> [-languageProbeSteps system,zh-Hans,zh-Hant,en] [-languageProbeRelaunch YES]`: records the
/// menu bar, the main window title and the toolbar at launch and after each stored choice (saved through
/// `LanguagePreference.store`, the picker's own path), opens Settings from the toolbar button, then quits
/// or relaunches. Run it from a copy with its own bundle identifier: it writes that domain's settings.
enum LanguageProbe {
    @MainActor static func startIfRequested(model: BuilderModel) {
        guard let path = UserDefaults.standard.string(forKey: "languageProbe") else { return }
        let steps = (UserDefaults.standard.string(forKey: "languageProbeSteps") ?? "")
            .split(separator: ",").compactMap { LanguagePreference(rawValue: String($0)) }
        let relaunch = UserDefaults.standard.bool(forKey: "languageProbeRelaunch")
        Snapshotter.activity = ProcessInfo.processInfo.beginActivity(options: [.userInitiated, .latencyCritical], reason: "Language probe")
        Task { @MainActor in
            for _ in 0..<100 where !model.toolkitInspected { try? await Task.sleep(for: .seconds(0.1)) }
            try? await Task.sleep(for: .seconds(0.8))
            var record: [String: Any] = [
                "pid": ProcessInfo.processInfo.processIdentifier,
                "menu_bar_lang": Lang.menuBar.rawValue,
                "bundle_preferred_localizations": Bundle.main.preferredLocalizations,
                "locale_preferred_languages_at_launch": Locale.preferredLanguages,
                "launch": state(),
            ]
            var after: [[String: Any]] = []
            for pref in steps {
                pref.store()
                try? await Task.sleep(for: .seconds(0.5))
                after.append(["stored": pref.rawValue] .merging(state()) { a, _ in a })
            }
            record["after_store"] = after
            record["settings_from_toolbar"] = await openSettingsFromToolbar()
            if let data = try? JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys]) {
                try? data.write(to: URL(fileURLWithPath: path))
            }
            if relaunch { AppRelaunch.relaunch() } else { NSApp.terminate(nil) }
        }
    }

    @MainActor private static func state() -> [String: Any] {
        let pref = LanguagePreference(rawValue: UserDefaults.standard.string(forKey: LanguagePreference.key) ?? "") ?? .system
        let main = NSApp.windows.first { $0.isVisible && !$0.isSheet && $0.toolbar != nil }
        return [
            "preference": pref.rawValue,
            "resolved": pref.resolved.rawValue,
            "system_option": LanguagePreference.systemLang(current: pref).rawValue,
            "system_option_title": LanguagePreference.system.title(pref.resolved, current: pref),
            "locale_preferred_languages": Locale.preferredLanguages,
            "languages_without_app_domain": LanguagePreference.languagesWithoutAppDomain,
            "app_domain_apple_languages": (UserDefaults.standard.persistentDomain(forName: Bundle.main.bundleIdentifier ?? "")?["AppleLanguages"] as? [String]) ?? NSNull(),
            "relaunch_row_shown": pref.resolved != Lang.menuBar,
            "window_title": main?.title ?? NSNull(),
            "toolbar_items": main?.toolbar?.items.map { $0.label } ?? [],
            "menu": menuTree(NSApp.mainMenu, depth: 2),
        ]
    }

    private static func menuTree(_ menu: NSMenu?, depth: Int) -> [Any] {
        guard let menu else { return [] }
        return menu.items.filter { !$0.isSeparatorItem && !$0.title.isEmpty && !$0.isHidden }.map { item -> Any in
            if depth > 0, let sub = item.submenu, !sub.items.isEmpty { return [item.title: menuTree(sub, depth: depth - 1)] }
            return item.title
        }
    }

    /// Presses the toolbar's settings button through its accessibility element, like VoiceOver would.
    @MainActor private static func openSettingsFromToolbar() async -> [String: Any] {
        guard let main = NSApp.windows.first(where: { $0.isVisible && !$0.isSheet && $0.toolbar != nil }) else {
            return ["error": "no main window"]
        }
        let before = Set(NSApp.windows.filter(\.isVisible).map(ObjectIdentifier.init))
        // SwiftUI buttons expose no accessibility role until an assistive client connects; use the toolbar
        // item's own action (or its view's button) the way a click would reach it.
        func buttons(in view: NSView) -> [NSButton] {
            view.subviews.flatMap { sub -> [NSButton] in
                if let button = sub as? NSButton { return [button] }
                return buttons(in: sub)
            }
        }
        let items = main.toolbar?.items ?? []
        let tree = items.map { item in
            "\(item.itemIdentifier.rawValue) label=\(item.label) view=\(item.view.map { "\(type(of: $0))" } ?? "-") action=\(item.action.map(NSStringFromSelector) ?? "-") buttons=\(item.view.map { buttons(in: $0).count } ?? 0)"
        }
        let item = items.first { candidate in Lang.allCases.contains { $0.t("Settings") == candidate.label } }
        var pressed = false
        if let view = item?.view {
            // A real click: mouse down and up at the item's centre, through the window's event path.
            let point = view.convert(NSPoint(x: view.bounds.midX, y: view.bounds.midY), to: nil)
            func event(_ type: NSEvent.EventType) -> NSEvent? {
                NSEvent.mouseEvent(with: type, location: point, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime,
                                   windowNumber: main.windowNumber, context: nil, eventNumber: 0, clickCount: 1, pressure: 1)
            }
            if let down = event(.leftMouseDown), let up = event(.leftMouseUp) {
                NSApp.postEvent(up, atStart: false)
                main.sendEvent(down)
                pressed = true
            }
        }
        let label = item?.label ?? "-"
        try? await Task.sleep(for: .seconds(0.8))
        let opened = NSApp.windows.filter { $0.isVisible && !before.contains(ObjectIdentifier($0)) }
        let result: [String: Any] = ["pressed": pressed, "button_label": label, "new_windows": opened.map(\.title),
                                     "toolbar_items": tree]
        opened.forEach { $0.close() }
        return result
    }
}

/// Window-shaped composition of the real views for documentation renders.
struct WindowMock: View {
    var model: BuilderModel
    var width: CGFloat = 1240
    var height: CGFloat = 860
    var scrollOffset: CGFloat = 0
    var sheet: AnyView? = nil
    @Environment(\.lang) private var lang

    var body: some View {
        ZStack(alignment: .top) {
            VStack(spacing: 0) {
                titleStrip
                Divider()
                HStack(spacing: 0) {
                    VStack(spacing: 0) {
                        // overlay() keeps the tall page from driving the layout height.
                        Color.pageBackground
                            .overlay(alignment: .top) {
                                MainPageContent(model: model).offset(y: -scrollOffset)
                            }
                            .clipped()
                        BottomBarMock(model: model)
                    }
                    Divider()
                    Color.cardBackground
                        .overlay(alignment: .top) {
                            if let id = model.focused {
                                FeatureDetail(feature: Catalog.feature(id), model: model).padding(20)
                            }
                        }
                        .frame(width: 350)
                        .clipped()
                }
            }
            if let sheet {
                Color.black.opacity(0.18)
                sheet
                    .frame(width: 580)
                    .background(RoundedRectangle(cornerRadius: 18, style: .continuous).fill(Color.cardBackground))
                    .overlay(RoundedRectangle(cornerRadius: 18, style: .continuous).strokeBorder(Color.cardStroke))
                    .shadow(color: .black.opacity(0.28), radius: 30, y: 12)
                    .padding(.top, 60)
            }
        }
        .frame(width: width, height: height)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).strokeBorder(Color.black.opacity(0.22), lineWidth: 0.5))
        .shadow(color: .black.opacity(0.22), radius: 18, y: 8)
        .padding(30)
        .background(Color.backdrop)
    }

    private var titleStrip: some View {
        HStack(spacing: 14) {
            HStack(spacing: 8) {
                Circle().fill(Color(red: 1, green: 0.37, blue: 0.34))
                Circle().fill(Color(red: 1, green: 0.74, blue: 0.18))
                Circle().fill(Color(red: 0.16, green: 0.79, blue: 0.25))
            }
            .frame(width: 56, height: 12)
            VStack(alignment: .leading, spacing: 1) {
                Text(lang.t("Z8 Patch Builder")).font(.headline)
                Text(lang.t("Toolkit \(Catalog.toolkitTag) · Original C 3.11"))
                    .font(.caption).foregroundStyle(.secondary)
            }
            .padding(.leading, 12)
            Spacer()
            Image(systemName: "gearshape")
                .padding(.horizontal, 10).padding(.vertical, 6)
                .background(Capsule().fill(Color.subtleFill))
            Image(systemName: "sidebar.trailing")
                .padding(.horizontal, 10).padding(.vertical, 6)
                .background(Capsule().fill(Color.subtleFill))
        }
        .foregroundStyle(.primary)
        .padding(.horizontal, 18)
        .frame(height: 52)
        .background(Color.cardBackground)
    }
}

/// BottomBar with a solid background (materials do not render offscreen).
struct BottomBarMock: View {
    var model: BuilderModel

    var body: some View {
        BottomBar(model: model, solid: true)
    }
}

/// Static copy of the Settings layout (grouped Form is scroll-backed and does not render offscreen).
struct SettingsMock: View {
    var model: BuilderModel
    /// Menu-bar language to show; the relaunch row appears when it differs from the window language.
    var menuBar: Lang? = nil
    @Environment(\.lang) private var lang
    @AppStorage("languagePreference") private var languagePreference: LanguagePreference = .system
    @AppStorage("appearancePreference") private var appearancePreference: AppearancePreference = .system

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            group {
                row(lang.t("Language")) {
                    Picker("" as String, selection: $languagePreference) {
                        ForEach(LanguagePreference.allCases) { Text($0.title(lang, current: languagePreference)).tag($0) }
                    }
                    .labelsHidden().fixedSize()
                }
                if let menuBar, menuBar != lang {
                    Divider()
                    MenuBarLanguageRow(model: model, menuBar: menuBar)
                }
                Divider()
                row(lang.t("Appearance")) {
                    Picker("" as String, selection: $appearancePreference) {
                        ForEach(AppearancePreference.allCases) { Text($0.title(lang)).tag($0) }
                    }
                    .pickerStyle(.segmented).labelsHidden().frame(width: 220)
                }
            }
            SystemLanguageNote().padding(.horizontal, 6)
            Text(lang.t("Bundled Toolkit")).font(.headline).padding(.horizontal, 6)
            group { ToolkitRows(model: model).labeledContentStyle(SpreadLabeledContent()) }
            Text(lang.t("About")).font(.headline).padding(.horizontal, 6)
            group { AboutRows().labeledContentStyle(SpreadLabeledContent()) }
        }
        .padding(20)
        .background(Color.pageBackground)
    }

    private func group<C: View>(@ViewBuilder _ c: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 10) { c() }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(14)
            .card()
    }

    private func row<C: View>(_ title: String, @ViewBuilder _ c: () -> C) -> some View {
        HStack { Text(title); Spacer(); c() }
    }
}

/// Grouped-form look for LabeledContent outside a Form.
struct SpreadLabeledContent: LabeledContentStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack { configuration.label; Spacer(); configuration.content.foregroundStyle(.secondary) }
    }
}

/// Keyframes of one guide for review: each frame is rendered at a fixed time.
struct GuideStrip: View {
    let id: FeatureID
    let times: [Double]
    @Environment(\.lang) private var lang

    var body: some View {
        let guide = FeatureGuide.of(id)
        let feature = Catalog.feature(id)
        VStack(alignment: .leading, spacing: 18) {
            HStack(spacing: 10) {
                FeatureIcon(feature: feature, size: 30)
                Text(lang.t("Guide keyframes · \(feature.name(lang))")).font(.title2.weight(.semibold))
            }
            LazyVGrid(columns: Array(repeating: GridItem(.fixed(290), spacing: 18), count: 4), alignment: .leading, spacing: 18) {
                ForEach(times, id: \.self) { t in
                    let i = guide.stepIndex(at: t)
                    VStack(alignment: .leading, spacing: 6) {
                        CamBezel { GuideScene(id: id, t: t) }
                        Text(lang.t("Step \(i + 1) · \(String(format: "%.1f", t)) s"))
                            .font(.caption.weight(.semibold)).foregroundStyle(.secondary)
                    }
                }
            }
            VStack(alignment: .leading, spacing: 6) {
                ForEach(guide.steps) { step in
                    Text("\(step.id + 1). " + step.caption(lang)).font(.callout).fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .padding(28)
        .frame(width: 1300, alignment: .leading)
        .background(Color.pageBackground)
    }
}
#endif
