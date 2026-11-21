import AppKit
import SwiftUI

/// UI languages, switchable at run time. Interface strings are written in English where they are used
/// and translated in Resources/Localizable.xcstrings (a String Catalog), which build_app.py compiles
/// into the bundle's .lproj folders. Feature text comes from the toolkit catalog
/// (resources/gui-catalog.json). A new language needs a case here, its translations in both catalogs
/// and an .lproj folder with InfoPlist.strings.
enum Lang: String, CaseIterable, Sendable {
    case en = "en"
    case zhHans = "zh-Hans"
    case zhHant = "zh-Hant"

    /// Localizes in this language rather than the one the app launched in, so the window switches
    /// without a relaunch. A string without a translation falls back to the English source.
    func t(_ text: LocalizedStringResource) -> String {
        var text = text
        text.locale = locale
        return String(localized: text)
    }

    var locale: Locale { Locale(identifier: rawValue) }

    /// Each language's own name, shown the same way in every UI language.
    var nativeName: String {
        switch self {
        case .en: return "English"
        case .zhHans: return "简体中文"
        case .zhHant: return "繁體中文"
        }
    }

    /// Localizations the bundle ships (CFBundleLocalizations); English is the development region.
    static let localizations = allCases.map(\.rawValue)

    init(localization: String?) { self = localization.flatMap(Lang.init(rawValue:)) ?? .en }

    /// macOS's own rule: the first language in the preference list that the app ships, else English.
    /// Languages the app does not ship fall through to the next entry.
    static func matching(_ preferredLanguages: [String]) -> Lang {
        Lang(localization: Bundle.preferredLocalizations(from: localizations, forPreferences: preferredLanguages).first)
    }

    /// AppKit and SwiftUI localize their own menu-bar items once, at launch, from the app's
    /// localization, so the whole menu bar stays in this language until the app is reopened.
    static let menuBar = Lang(localization: Bundle.main.preferredLocalizations.first)
}

extension LocalizedStringResource {
    /// Same call shape as catalog text, e.g. `step.title(lang)`.
    func callAsFunction(_ lang: Lang) -> String { lang.t(self) }
}

/// Catalog text in every UI language: an object with the keys "en", "zh-Hans" and "zh-Hant".
struct L: Hashable, Decodable, Sendable {
    private let text: [Lang: String]

    init(from decoder: Decoder) throws {
        let values = try decoder.singleValueContainer().decode([String: String].self)
        guard Set(values.keys) == Set(Lang.localizations) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath,
                debugDescription: "Expected exactly \(Lang.localizations.joined(separator: ", ")); found \(values.keys.sorted().joined(separator: ", "))"))
        }
        text = Dictionary(uniqueKeysWithValues: Lang.allCases.map { ($0, values[$0.rawValue]!) })
    }

    func callAsFunction(_ lang: Lang) -> String { text[lang]! }
}

enum LanguagePreference: String, CaseIterable, Identifiable {
    case system
    case zhHans = "zh-Hans"
    case zhHant = "zh-Hant"
    case en

    var id: String { rawValue }

    static let key = "languagePreference"

    /// The chosen language; nil for System.
    var lang: Lang? { Lang(rawValue: rawValue) }

    /// For System, `Locale.preferredLanguages`: the user's list, or this app's own list when System
    /// Settings sets a per-app language (the same AppleLanguages key that `store` writes for a fixed choice).
    var resolved: Lang { lang ?? Lang.matching(Locale.preferredLanguages) }

    /// Picker title. System names the language that choosing it would give, from the stored `current`.
    func title(_ lang: Lang, current: LanguagePreference) -> String {
        self.lang?.nativeName ?? lang.t("System (\(Self.systemLang(current: current).nativeName))")
    }

    /// What System gives. While System is stored, AppleLanguages in this app's domain can only be System
    /// Settings' per-app language, which `Locale.preferredLanguages` already includes. While a fixed
    /// language is stored, `Locale.preferredLanguages` is this app's own override, which `store` removes
    /// when System is chosen; what is left is the list without this app's domain.
    static func systemLang(current: LanguagePreference,
                           preferred: [String] = Locale.preferredLanguages,
                           withoutAppDomain: [String] = languagesWithoutAppDomain) -> Lang {
        Lang.matching(current == .system ? preferred : withoutAppDomain)
    }

    /// AppleLanguages from the launch arguments or the user's global list, skipping this app's own domain.
    static var languagesWithoutAppDomain: [String] {
        CFPreferencesCopyAppValue("AppleLanguages" as CFString, kCFPreferencesAnyApplication) as? [String] ?? []
    }

    /// AppleLanguages for this app's domain, which sets the menu-bar language at the next launch.
    var appleLanguages: [String]? { lang.map { [$0.rawValue] } }

    /// Saves the choice. AppleLanguages goes first: storing the preference re-renders the views, and
    /// "System" must then resolve without this app's previous override.
    func store(in defaults: UserDefaults = .standard) {
        if let list = appleLanguages {
            defaults.set(list, forKey: "AppleLanguages")
        } else {
            defaults.removeObject(forKey: "AppleLanguages")
        }
        defaults.set(rawValue, forKey: Self.key)
    }

    /// Picker binding that saves through `store`.
    static func binding(_ current: LanguagePreference) -> Binding<LanguagePreference> {
        Binding(get: { current }, set: { $0.store() })
    }
}

enum AppearancePreference: String, CaseIterable, Identifiable {
    case system, light, dark

    var id: String { rawValue }

    var nsAppearance: NSAppearance? {
        switch self {
        case .system: return nil
        case .light: return NSAppearance(named: .aqua)
        case .dark: return NSAppearance(named: .darkAqua)
        }
    }

    func title(_ lang: Lang) -> String {
        switch self {
        case .system: return lang.t("System")
        case .light: return lang.t("Light")
        case .dark: return lang.t("Dark")
        }
    }
}

private struct LangKey: EnvironmentKey {
    static let defaultValue: Lang = .zhHans
}

extension EnvironmentValues {
    var lang: Lang {
        get { self[LangKey.self] }
        set { self[LangKey.self] = newValue }
    }
}

extension Color {
    private static func dynamic(light: NSColor, dark: NSColor) -> Color {
        Color(nsColor: NSColor(name: nil) { appearance in
            appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua ? dark : light
        })
    }

    /// Page behind the grouped cards (System Settings–like contrast).
    static let pageBackground = dynamic(light: NSColor(white: 0.955, alpha: 1),
                                        dark: NSColor(white: 0.115, alpha: 1))
    static let cardBackground = dynamic(light: .white, dark: NSColor(white: 0.165, alpha: 1))
    static let cardStroke = dynamic(light: NSColor(white: 0, alpha: 0.08),
                                    dark: NSColor(white: 1, alpha: 0.09))
    /// Neutral backdrop around documentation renders.
    static let backdrop = dynamic(light: NSColor(white: 0.86, alpha: 1), dark: NSColor(white: 0.06, alpha: 1))
    static let subtleFill = dynamic(light: NSColor(white: 0, alpha: 0.035),
                                    dark: NSColor(white: 1, alpha: 0.05))
}

func formattedBytes(_ value: Int64, _ lang: Lang) -> String {
    let n = NumberFormatter()
    n.numberStyle = .decimal
    n.locale = lang.locale
    let s = n.string(from: NSNumber(value: value)) ?? "\(value)"
    return lang.t("\(s) bytes")
}

func abbreviatedPath(_ url: URL) -> String {
    (url.path as NSString).abbreviatingWithTildeInPath
}
