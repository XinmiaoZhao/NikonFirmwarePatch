import AppKit
import SwiftUI

@main
enum Entry {
    static func main() {
        // `--self-test` checks the bundle without opening a window (used by build_app.py and CI).
        if CommandLine.arguments.dropFirst().first == "--self-test" {
            exit(SelfTest.run())
        }
        Z8PatchBuilderApp.main()
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

struct Z8PatchBuilderApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @State private var model = BuilderModel()
    @AppStorage("languagePreference") private var languagePreference: LanguagePreference = .system
    @AppStorage("appearancePreference") private var appearancePreference: AppearancePreference = .system

    var body: some Scene {
        Window("Z8 Patch Builder", id: "main") {
            RootView(model: model)
                .environment(\.lang, languagePreference.resolved)
                .environment(\.locale, languagePreference.resolved.locale)
                .frame(minWidth: 980, minHeight: 660)
                .onAppear {
                    applyAppearance()
                    if !model.toolkitInspected { model.inspectToolkit() }
#if DEBUG
                    Snapshotter.startIfRequested(model: model)
                    SheetProbe.startIfRequested(model: model)
                    LanguageProbe.startIfRequested(model: model)
#endif
                }
                .onChange(of: appearancePreference) { applyAppearance() }
        }
        .defaultSize(width: 1220, height: 820)
        .commands { AppCommands(model: model) }

        Settings {
            SettingsView(model: model)
                .environment(\.lang, languagePreference.resolved)
                .environment(\.locale, languagePreference.resolved.locale)
        }
    }

    private func applyAppearance() {
        NSApp.appearance = appearancePreference.nsAppearance
    }
}

/// Main window, or a blocking explanation when the bundled toolkit is unusable.
struct RootView: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        if !model.toolkitInspected {
            ProgressView(lang.t("Checking the bundled toolkit…"))
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if Catalog.features.isEmpty {
            ContentUnavailableView {
                Label(lang.t("Bundled Toolkit Unavailable"), systemImage: "exclamationmark.octagon")
            } description: {
                Text(lang.t("The toolkit inside the app is missing or modified, so building is disabled. Download the app again from the GitHub release."))
                Text(model.toolkit.problems.prefix(5).joined(separator: "\n"))
                    .font(.system(.caption, design: .monospaced))
            }
        } else {
            MainView(model: model)
        }
    }
}

struct AppCommands: Commands {
    let model: BuilderModel
    @AppStorage("languagePreference") private var languagePreference: LanguagePreference = .system
    @AppStorage("appearancePreference") private var appearancePreference: AppearancePreference = .system

    var body: some Commands {
        // The system items (app menu, File, Edit, View, Window) keep the launch language, so the app's own
        // items do too: the menu bar is never mixed, and switches as a whole when the app is reopened.
        let lang = Lang.menuBar
        CommandGroup(replacing: .appInfo) {
            Button(lang.t("About \(AppInfo.appName)")) { AboutPanel.show() }
        }
        CommandGroup(replacing: .newItem) {
            Button(lang.t("Open Original Firmware…")) { model.requestOpenInput = true }
                .keyboardShortcut("o")
            Button(lang.t("Choose Export Location…")) { model.requestChooseOutput = true }
                .keyboardShortcut("o", modifiers: [.command, .shift])
        }
        CommandMenu(lang.t("Build")) {
            Button(lang.t("Build Firmware…")) { model.beginBuild() }
                .keyboardShortcut("b")
                .disabled(!model.canBuild || model.showFlow)
            Divider()
            Button(lang.t("Select All Feature Groups")) { model.selectAll() }
                .keyboardShortcut("a", modifiers: [.command, .shift])
            Button(lang.t("Clear Selection")) { model.clearSelection() }
        }
        CommandGroup(after: .sidebar) {
            Button(model.showInspector ? lang.t("Hide Inspector") : lang.t("Show Inspector")) {
                model.showInspector.toggle()
            }
            .keyboardShortcut("i", modifiers: [.command, .option])
            Picker(lang.t("Appearance"), selection: $appearancePreference) {
                ForEach(AppearancePreference.allCases) { Text($0.title(lang)).tag($0) }
            }
            Picker(lang.t("Language"), selection: LanguagePreference.binding(languagePreference)) {
                ForEach(LanguagePreference.allCases) { Text($0.title(lang, current: languagePreference)).tag($0) }
            }
            Divider()
        }
        CommandGroup(replacing: .help) {
            Link(lang.t("Known Issues and Limits"), destination: Catalog.repositoryFile("docs/known-issues.md"))
            Link(lang.t("Validation Coverage"), destination: Catalog.repositoryFile("docs/validation.md"))
            Link(lang.t("Release Notes"), destination: Catalog.releasePage)
            Divider()
            Link(lang.t("GitHub Repository"), destination: Catalog.repository)
        }
    }
}
