import SwiftUI

struct InspectorView: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        ScrollView {
            if let id = model.focused {
                FeatureDetail(feature: Catalog.feature(id), model: model)
                    .padding(20)
                    .id(id)
            } else {
                ContentUnavailableView(lang.t("Select a Feature Group"),
                                       systemImage: "square.grid.2x2",
                                       description: Text(lang.t("Select a card to see its description, camera controls and known limits.")))
                    .padding(.top, 80)
            }
        }
        .background(Color.cardBackground)
    }
}

struct FeatureDetail: View {
    let feature: Feature
    var model: BuilderModel
    @Environment(\.lang) private var lang
    @State private var expanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            // Header
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 12) {
                    FeatureIcon(feature: feature, size: 46)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(feature.name(lang)).font(.title2.weight(.bold))
                        Text(verbatim: "--features \(feature.id.rawValue)")
                            .font(.system(.caption, design: .monospaced))
                            .foregroundStyle(.secondary)
                            .textSelection(.enabled)
                    }
                }
                Toggle(lang.t("Include in this build"),
                       isOn: Binding(get: { model.selected.contains(feature.id) },
                                     set: { on in
                                         if on { model.selected.insert(feature.id) } else { model.selected.remove(feature.id) }
                                     }))
                    .toggleStyle(.checkbox)
            }

            DetailSection(title: lang.t("Operation Guide")) {
                VStack(alignment: .leading, spacing: 6) {
                    GuidePlayer(guide: FeatureGuide.of(feature.id), onExpand: { expanded = true })
                    Text(lang.t("Illustrative animation; camera menus are redrawn in the camera’s own wording."))
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .sheet(isPresented: $expanded) {
                GuideSheet(feature: feature, onClose: { expanded = false })
                    .environment(\.lang, lang)
            }

            DetailSection(title: lang.t(LocalizedStringResource("inspector.about", defaultValue: "About"))) {
                Text(feature.intro(lang))
                    .fixedSize(horizontal: false, vertical: true)
                    .lineSpacing(2)
            }

            DetailSection(title: lang.t("Includes")) {
                VStack(alignment: .leading, spacing: 7) {
                    ForEach(feature.includes, id: \.self) { item in
                        Label {
                            Text(item(lang)).fixedSize(horizontal: false, vertical: true)
                        } icon: {
                            Image(systemName: "checkmark").font(.caption.weight(.bold)).foregroundStyle(feature.tint)
                        }
                    }
                }
            }

            DetailSection(title: lang.t("Camera Controls")) {
                Label(feature.cameraEntry(lang), systemImage: "camera")
                    .fixedSize(horizontal: false, vertical: true)
            }

            DetailSection(title: lang.t("Known Limits"), badge: "\(feature.limits.count)") {
                VStack(alignment: .leading, spacing: 10) {
                    ForEach(feature.limits) { limit in
                        LimitRow(limit: limit)
                    }
                }
            }

            DetailSection(title: lang.t("Documentation")) {
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(feature.docs) { doc in
                        Link(destination: doc.url) {
                            Label(doc.title(lang), systemImage: "arrow.up.right.square")
                        }
                    }
                    Link(destination: Catalog.repositoryFile("docs/known-issues.md")) {
                        Label(lang.t("All known issues"), systemImage: "arrow.up.right.square")
                    }
                }
                .font(.callout)
            }
        }
    }
}

struct DetailSection<Content: View>: View {
    let title: String
    var badge: String? = nil
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(spacing: 6) {
                Text(title.uppercased())
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .tracking(0.4)
                if let badge {
                    Text(badge)
                        .font(.caption2.weight(.bold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 1)
                        .foregroundStyle(.orange)
                        .background(Capsule().fill(.orange.opacity(0.15)))
                }
            }
            content.font(.callout)
        }
    }
}

struct LimitRow: View {
    let limit: FeatureLimit
    @Environment(\.lang) private var lang

    var body: some View {
        HStack(alignment: .top, spacing: 9) {
            Image(systemName: limit.level == .caution ? "exclamationmark.triangle.fill" : "info.circle")
                .foregroundStyle(limit.level == .caution ? Color.orange : Color.secondary)
                .frame(width: 16)
                .padding(.top, 1)
            VStack(alignment: .leading, spacing: 2) {
                Text(limit.title(lang)).fontWeight(.medium).fixedSize(horizontal: false, vertical: true)
                Text(limit.detail(lang)).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 9, style: .continuous)
            .fill(limit.level == .caution ? Color.orange.opacity(0.08) : Color.subtleFill))
    }
}
