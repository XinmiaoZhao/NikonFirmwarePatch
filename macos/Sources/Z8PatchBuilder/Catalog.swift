import Foundation
import SwiftUI

// Feature text comes from resources/gui-catalog.json in the bundled toolkit, so the wording always
// ships with the engine that builds. tests/validate_gui_catalog.py checks it against features.py
// and docs/. Icons, colours and the guide animation timing stay in the app.

enum FeatureID: String, CaseIterable, Identifiable, Codable {
    case videoRecording = "video-recording"
    case logColour = "log-colour"
    case stillPhotoTools = "still-photo-tools"
    case rawPrecapture = "raw-precapture"

    var id: String { rawValue }

    /// Short token for the default output folder name.
    var short: String {
        switch self {
        case .videoRecording: return "video"
        case .logColour: return "log"
        case .stillPhotoTools: return "photo"
        case .rawPrecapture: return "precapture"
        }
    }

    var symbol: String {
        switch self {
        case .videoRecording: return "film.stack"
        case .logColour: return "camera.filters"
        case .stillPhotoTools: return "photo.stack"
        case .rawPrecapture: return "clock.arrow.circlepath"
        }
    }

    var tint: Color {
        switch self {
        case .videoRecording: return .blue
        case .logColour: return .orange
        case .stillPhotoTools: return .teal
        case .rawPrecapture: return .purple
        }
    }
}

enum LimitLevel: String, Codable { case caution, note }

struct FeatureLimit: Identifiable {
    let id = UUID()
    let level: LimitLevel
    let title: L
    let detail: L
    let sourcePath: String
}

struct DocLink: Identifiable {
    let id = UUID()
    let title: L
    let path: String

    var url: URL { Catalog.repositoryFile(path) }
}

struct Feature: Identifiable {
    let id: FeatureID
    let name: L
    let summary: L
    let intro: L
    let includes: [L]
    let cameraEntry: L
    let limits: [FeatureLimit]
    let docs: [DocLink]
    let guide: [L]

    var symbol: String { id.symbol }
    var tint: Color { id.tint }
    var cautionCount: Int { limits.filter { $0.level == .caution }.count }
}

/// JSON shape of resources/gui-catalog.json (schema 2: text in en, zh-Hans and zh-Hant).
struct CatalogFile: Decodable {
    struct Limit: Decodable {
        struct Source: Decodable { let path: String; let quote: String }
        let level: LimitLevel
        let title: L
        let detail: L
        let source: Source
    }
    struct Doc: Decodable { let title: L; let path: String }
    struct Row: Decodable {
        let id: String
        let name: L
        let summary: L
        let intro: L
        let includes: [L]
        let camera_entry: L
        let limits: [Limit]
        let docs: [Doc]
        let guide: [L]
    }
    let schema: Int
    let features: [Row]
}

enum CatalogError: LocalizedError {
    case schema(Int)
    case ids([String])
    case guide(FeatureID, Int, Int)

    var errorDescription: String? {
        switch self {
        case .schema(let s): return "Unsupported gui-catalog schema \(s)"
        case .ids(let ids): return "Feature ids differ from the app: \(ids.joined(separator: ", "))"
        case .guide(let id, let have, let want): return "Guide for \(id.rawValue) has \(have) captions; the animation has \(want) steps"
        }
    }
}

struct ParsedCatalog {
    let features: [Feature]
}

enum Catalog {
    static let repository = URL(string: "https://github.com/XinmiaoZhao/NikonFirmwarePatch")!

    /// Installed once at launch from the bundled toolkit (Toolkit.load()).
    static private(set) var features: [Feature] = []
    static private(set) var toolkitTag = "—"
    static private(set) var toolkitCommit = "—"
    static private(set) var linkRef = "main"

    static func feature(_ id: FeatureID) -> Feature { features.first { $0.id == id }! }

    static func parse(_ data: Data) throws -> ParsedCatalog {
        let file = try JSONDecoder().decode(CatalogFile.self, from: data)
        guard file.schema == 2 else { throw CatalogError.schema(file.schema) }
        let ids = file.features.map(\.id)
        guard ids == FeatureID.allCases.map(\.rawValue) else { throw CatalogError.ids(ids) }
        let features = file.features.map { row -> Feature in
            Feature(id: FeatureID(rawValue: row.id)!, name: row.name, summary: row.summary, intro: row.intro,
                    includes: row.includes, cameraEntry: row.camera_entry,
                    limits: row.limits.map { FeatureLimit(level: $0.level, title: $0.title, detail: $0.detail, sourcePath: $0.source.path) },
                    docs: row.docs.map { DocLink(title: $0.title, path: $0.path) },
                    guide: row.guide)
        }
        for f in features {
            let want = FeatureGuide.timing[f.id]!.bounds.count
            guard f.guide.count == want else { throw CatalogError.guide(f.id, f.guide.count, want) }
        }
        return ParsedCatalog(features: features)
    }

    static func install(_ parsed: ParsedCatalog, tag: String, commit: String) {
        features = parsed.features
        toolkitTag = tag
        toolkitCommit = commit
        // Development tags (v0.0.0-…) are never published; their documents live on main.
        linkRef = tag.hasPrefix("v0.0.0") || tag == "—" ? "main" : tag
    }

    static func repositoryFile(_ path: String) -> URL {
        repository.appendingPathComponent("blob").appendingPathComponent(linkRef).appendingPathComponent(path)
    }

    static var releasePage: URL {
        linkRef == "main" ? repository.appendingPathComponent("releases")
                          : repository.appendingPathComponent("releases/tag").appendingPathComponent(linkRef)
    }
}
