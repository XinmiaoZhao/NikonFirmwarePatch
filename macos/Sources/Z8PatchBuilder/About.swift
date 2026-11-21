import AppKit
import SwiftUI

/// Authorship and license notices (GPL-3.0's "Appropriate Legal Notices"): the copyright, no warranty,
/// the license and where to read it. Shown in the About panel and in Settings › About.
enum AppInfo {
    /// Matches NSHumanReadableCopyright in Info.plist (macos/scripts/build_app.py) and InfoPlist.strings.
    static func copyright(_ lang: Lang) -> String { lang.t("© 2026 Xinmiao Zhao and contributors") }

    /// "github.com/owner/repo", for link text.
    static var repositoryLabel: String {
        (Catalog.repository.host() ?? "") + Catalog.repository.path()
    }

    static var license: URL { Catalog.repositoryFile("LICENSE") }
    static var notice: URL { Catalog.repositoryFile("NOTICE.md") }

    /// The app's own name in the bundle's localization (the menu bar's language).
    static var appName: String {
        Bundle.main.localizedInfoDictionary?["CFBundleName"] as? String
            ?? Bundle.main.infoDictionary?["CFBundleName"] as? String
            ?? "Z8 Patch Builder"
    }
}

/// The standard About panel with credits: toolkit identity, repository and license. The copyright
/// line below them comes from Info.plist. Written in the menu bar's language, like the menu item.
@MainActor
enum AboutPanel {
    static func show() {
        NSApp.orderFrontStandardAboutPanel(options: [.credits: credits(Lang.menuBar)])
        NSApp.activate(ignoringOtherApps: true)
    }

    static func credits(_ lang: Lang) -> NSAttributedString {
        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = .center
        paragraph.paragraphSpacing = 4
        let base: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: NSFont.smallSystemFontSize),
            .foregroundColor: NSColor.secondaryLabelColor,
            .paragraphStyle: paragraph,
        ]
        let text = NSMutableAttributedString()
        func add(_ string: String, link: URL? = nil) {
            var attributes = base
            if let link { attributes[.link] = link }
            text.append(NSAttributedString(string: string, attributes: attributes))
        }
        if Catalog.toolkitTag != "—" {
            add(lang.t("Toolkit \(Catalog.toolkitTag) · source \(String(Catalog.toolkitCommit.prefix(12)))") + "\n")
        }
        add(AppInfo.repositoryLabel, link: Catalog.repository)
        add("\n")
        add("GPL-3.0-only", link: AppInfo.license)
        add(" · " + lang.t("No warranty") + "\n" + lang.t("Not affiliated with Nikon"))
        return text
    }
}

/// Copyright, repository, license, components and acknowledgements; shared by Settings and its
/// documentation render.
struct AboutRows: View {
    @Environment(\.lang) private var lang

    var body: some View {
        LabeledContent(lang.t("Copyright"), value: AppInfo.copyright(lang))
        LabeledContent(lang.t("Repository")) {
            Link(AppInfo.repositoryLabel, destination: Catalog.repository)
        }
        LabeledContent(lang.t("License")) {
            Link(destination: AppInfo.license) { Text(verbatim: "GPL-3.0-only") }
        }
        LabeledContent(lang.t("Bundled components"), value: "CPython 3.12 · capstone 5.0.7")
        LabeledContent(lang.t("Acknowledgements")) {
            Link(lang.t("Contributors"), destination: AppInfo.notice)
        }
        Text(lang.t("This software comes with no warranty. This project is not affiliated with Nikon; Nikon firmware keeps its own license. Component licenses ship in Resources/licenses."))
            .font(.callout)
            .foregroundStyle(.secondary)
            .fixedSize(horizontal: false, vertical: true)
    }
}
