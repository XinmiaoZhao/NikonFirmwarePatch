import AppKit
import SwiftUI

struct SettingsView: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang
    @AppStorage("languagePreference") private var languagePreference: LanguagePreference = .system
    @AppStorage("appearancePreference") private var appearancePreference: AppearancePreference = .system

    var body: some View {
        Form {
            Section {
                Picker(lang.t("Language"), selection: LanguagePreference.binding(languagePreference)) {
                    ForEach(LanguagePreference.allCases) { Text($0.title(lang, current: languagePreference)).tag($0) }
                }
                if lang != Lang.menuBar {
                    MenuBarLanguageRow(model: model, menuBar: Lang.menuBar)
                }
                Picker(lang.t("Appearance"), selection: $appearancePreference) {
                    ForEach(AppearancePreference.allCases) { Text($0.title(lang)).tag($0) }
                }
                .pickerStyle(.segmented)
            } footer: {
                SystemLanguageNote()
            }

            Section(lang.t("Bundled Toolkit")) {
                ToolkitRows(model: model)
            }

            Section(lang.t("About")) {
                AboutRows()
            }
        }
        .formStyle(.grouped)
        .frame(width: 520)
        .fixedSize(horizontal: false, vertical: true)
        .navigationTitle(lang.t("Settings"))
    }
}

/// Shown while the window text and the menu bar differ: the menu bar switches only on a relaunch.
struct MenuBarLanguageRow: View {
    var model: BuilderModel
    var menuBar: Lang
    @Environment(\.lang) private var lang

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(lang.t("The menu bar is still in \(menuBar.nativeName)"))
                Text(detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 8)
            Button(lang.t("Relaunch")) { AppRelaunch.relaunch() }
                .disabled(model.isBuilding)
        }
    }

    private var detail: String {
        if model.isBuilding {
            return lang.t("You can relaunch once the build finishes.")
        }
        if model.hasSessionChoices {
            return lang.t("It switches when the app relaunches. The opened firmware and selected groups need choosing again.")
        }
        return lang.t("It switches when the app relaunches.")
    }
}

struct SystemLanguageNote: View {
    @Environment(\.lang) private var lang

    var body: some View {
        Text(lang.t("System: the first language in the macOS Preferred Languages list that the app provides (Simplified Chinese, Traditional Chinese or English); English if none is listed."))
            .font(.caption)
            .foregroundStyle(.secondary)
            .fixedSize(horizontal: false, vertical: true)
    }
}

enum AppRelaunch {
    /// Starts a new instance of this bundle and quits this one once the new one is running.
    @MainActor static func relaunch() {
        let config = NSWorkspace.OpenConfiguration()
        config.createsNewApplicationInstance = true
        NSWorkspace.shared.openApplication(at: Bundle.main.bundleURL, configuration: config) { _, error in
            let started = error == nil
            Task { @MainActor in
                if started { NSApp.terminate(nil) } else { NSSound.beep() }
            }
        }
    }
}

/// Toolkit identity and the launch self-check, shared by Settings and its documentation render.
struct ToolkitRows: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        LabeledContent(lang.t("Version"), value: model.toolkit.tag)
        LabeledContent(lang.t("Source commit")) {
            Text(String(model.toolkit.commit.prefix(12))).font(.system(.body, design: .monospaced)).textSelection(.enabled)
        }
        LabeledContent(lang.t("File check")) {
            if !model.toolkitInspected {
                ProgressView().controlSize(.small)
            } else if model.toolkit.ok {
                Label(lang.t("\(model.toolkit.checkedFiles) files match the release manifest"),
                      systemImage: "checkmark.seal.fill")
                    .foregroundStyle(.green)
            } else {
                Label(lang.t("\(model.toolkit.problems.count) problems; building disabled"),
                      systemImage: "xmark.octagon.fill")
                    .foregroundStyle(.red)
                    .help(model.toolkit.problems.joined(separator: "\n"))
            }
        }
        LabeledContent(lang.t("Supported input"), value: lang.t("Original Z8 C 3.11"))
    }
}
