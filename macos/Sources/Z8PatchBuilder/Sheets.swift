import AppKit
import SwiftUI

struct BuildFlowSheet: View {
    @Bindable var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        Group {
            switch model.stage {
            case .confirm: RiskConfirmView(model: model)
            case .running, .failed: ProgressStageView(model: model)
            case .succeeded: ResultView(model: model)
            }
        }
        .frame(width: 580)
        .animation(.easeInOut(duration: 0.2), value: model.stage)
    }
}

// MARK: - Risk confirmation

struct RiskConfirmView: View {
    @Bindable var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .top, spacing: 16) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 40))
                    .foregroundStyle(.yellow, .black.opacity(0.75))
                    .symbolRenderingMode(.palette)
                VStack(alignment: .leading, spacing: 5) {
                    Text(lang.t("Before You Build Experimental Firmware"))
                        .font(.title2.weight(.bold))
                    Text(lang.t("This step only creates local files. Installing them on a camera is your decision."))
                        .foregroundStyle(.secondary)
                }
            }

            VStack(alignment: .leading, spacing: 10) {
                RiskPoint(symbol: "bolt.trianglebadge.exclamationmark",
                          text: lang.t("This is unofficial, experimental firmware. Installing it can cause data loss, card corruption or camera malfunction."))
                RiskPoint(symbol: "checklist",
                          text: lang.t("Offline checks cover the file, patch windows and preserved bytes; they cannot prove safe operation on a camera."))
                RiskPoint(symbol: "sdcard",
                          text: lang.t("The app never writes to memory cards and never updates the camera."))
                RiskPoint(symbol: "arrow.uturn.backward.circle",
                          text: lang.t("Avoid irreplaceable work. If something goes wrong, reinstall a complete package that previously worked."))
                RiskPoint(symbol: "doc.plaintext",
                          text: lang.t("This project is not affiliated with Nikon and is provided under GPL-3.0 without warranty."))
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
            .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(Color.subtleFill))

            VStack(alignment: .leading, spacing: 8) {
                SummaryLine(label: lang.t("Groups"),
                            value: model.orderedSelection.map { Catalog.feature($0).name(lang) }.joined(separator: lang.t(LocalizedStringResource(", ", comment: "Separator between feature group names"))))
                SummaryLine(label: lang.t("Identity"), value: "\(model.version).\(model.tag) · \(model.outputFileName)", mono: true)
                SummaryLine(label: lang.t("Export to"), value: model.outputFolder.map(abbreviatedPath) ?? "—", mono: true)
                SheetDisclosure(isExpanded: $model.showSelectedLimits) {
                    SelectedLimitList(model: model)
                } label: {
                    Text(lang.t("Known limits of the selected groups (\(model.selectedLimitCount))"))
                        .font(.callout.weight(.medium))
                }
            }

            Divider()

            Toggle(isOn: $model.acknowledged) {
                Text(lang.t("I have read and understand these risks and accept responsibility for installing the result."))
                    .fixedSize(horizontal: false, vertical: true)
            }
            .toggleStyle(.checkbox)

            HStack {
                Spacer()
                Button(lang.t("Cancel")) { model.showFlow = false }
                    .keyboardShortcut(.cancelAction)
                Button(lang.t("Start Build")) { model.startBuild() }
                    .keyboardShortcut(.defaultAction)
                    .disabled(!model.acknowledged)
            }
            .controlSize(.large)
        }
        .padding(24)
    }
}

/// The selected groups' known limits. The list scrolls once it is taller than `maxHeight`, so the
/// sheet keeps the same size however many limits the catalog lists. An overflowing list fades out at
/// its bottom edge, so a cut that happens to fall between two groups still reads as "more below";
/// the extra bottom padding lets the last row clear the fade when scrolled to the end.
struct SelectedLimitList: View {
    var model: BuilderModel
    static let maxHeight: CGFloat = 210
    static let fade: CGFloat = 28
    @State private var listHeight: CGFloat = 0
    @Environment(\.lang) private var lang

    private var overflows: Bool { listHeight > Self.maxHeight }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(model.orderedSelection) { id in
                    let f = Catalog.feature(id)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(f.name(lang)).font(.callout.weight(.semibold))
                        ForEach(f.limits) { limit in
                            Label(limit.title(lang), systemImage: limit.level == .caution ? "exclamationmark.triangle.fill" : "info.circle")
                                .font(.callout)
                                .foregroundStyle(limit.level == .caution ? Color.orange : Color.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .onGeometryChange(for: CGFloat.self) { $0.size.height } action: { listHeight = $0 }
            .padding(.bottom, overflows ? Self.fade : 0)
        }
        .scrollBounceBehavior(.basedOnSize)
        .scrollIndicatorsFlash(trigger: model.showSelectedLimits)
        .frame(height: min(max(listHeight, 1), Self.maxHeight))
        .mask {
            VStack(spacing: 0) {
                Color.black
                LinearGradient(colors: [.black, .black.opacity(overflows ? 0 : 1)], startPoint: .top, endPoint: .bottom)
                    .frame(height: Self.fade)
            }
        }
        .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Color.subtleFill))
    }
}

/// A disclosure for content inside a sheet. A sheet window takes the size of the final layout at
/// once, so with `DisclosureGroup` the window jumped while the content was still animating, and on
/// collapse the window shrank first and cut off the fading text. Here the revealed height is
/// animatable data: SwiftUI lays the view out again on every animation frame, and the sheet window
/// grows and shrinks together with the content.
struct SheetDisclosure<Label: View, Content: View>: View {
    @Binding var isExpanded: Bool
    @ViewBuilder var content: () -> Content
    @ViewBuilder var label: () -> Label
    @State private var contentHeight: CGFloat = 0
    @Environment(\.lang) private var lang

    static var animation: Animation { .easeInOut(duration: 0.25) }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button {
                withAnimation(Self.animation) { isExpanded.toggle() }
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.secondary)
                        .rotationEffect(.degrees(isExpanded ? 90 : 0))
                        .frame(width: 14, height: 14)
                    label()
                    Spacer(minLength: 0)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityValue(isExpanded ? lang.t("Expanded") : lang.t("Collapsed"))

            content()
                .padding(.top, 8)
                .fixedSize(horizontal: false, vertical: true)
                .onGeometryChange(for: CGFloat.self) { $0.size.height } action: { contentHeight = $0 }
                .modifier(RevealHeight(fraction: isExpanded ? 1 : 0, height: contentHeight))
                .allowsHitTesting(isExpanded)
                .accessibilityHidden(!isExpanded)
        }
    }
}

/// Shows the top `fraction` of a view whose full height is `height`.
private struct RevealHeight: ViewModifier, Animatable {
    var fraction: CGFloat
    var height: CGFloat

    var animatableData: CGFloat {
        get { fraction }
        set { fraction = newValue }
    }

    func body(content: Content) -> some View {
        content
            .opacity(fraction)
            .frame(height: height * fraction, alignment: .top)
            .clipped()
    }
}

struct RiskPoint: View {
    let symbol: String
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: symbol).foregroundStyle(.orange).frame(width: 20)
            Text(text).fixedSize(horizontal: false, vertical: true)
        }
        .font(.callout)
    }
}

struct SummaryLine: View {
    let label: String
    let value: String
    var mono = false

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(label).foregroundStyle(.secondary).frame(width: 74, alignment: .leading)
            Text(value)
                .font(mono ? .system(.callout, design: .monospaced) : .callout)
                .lineLimit(2)
                .truncationMode(.middle)
                .textSelection(.enabled)
            Spacer(minLength: 0)
        }
        .font(.callout)
    }
}

// MARK: - Progress

struct ProgressStageView: View {
    @Bindable var model: BuilderModel
    @Environment(\.lang) private var lang

    private var doneCount: Int { model.steps.filter { $0.state == .done }.count }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(spacing: 14) {
                if model.stage == .failed {
                    Image(systemName: "xmark.octagon.fill").font(.system(size: 36)).foregroundStyle(.red)
                } else {
                    ProgressView().controlSize(.large)
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text(model.stage == .failed ? lang.t("Build Stopped") : lang.t("Building \(model.outputFileName)"))
                        .font(.title2.weight(.bold))
                    Text(model.stage == .failed
                         ? (model.failure?(lang) ?? "")
                         : lang.t("Keep the app open. The original input is read-only and stays unchanged."))
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                    if model.stage == .failed, let detail = model.failureDetail {
                        Text(detail)
                            .font(.system(.callout, design: .monospaced))
                            .foregroundStyle(.red)
                            .textSelection(.enabled)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    if model.stage == .failed, let note = model.cleanupNote {
                        Text(note(lang))
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }

            ProgressView(value: Double(doneCount), total: Double(max(model.steps.count, 1)))
                .tint(model.stage == .failed ? .red : .accentColor)

            VStack(spacing: 0) {
                ForEach(Array(model.steps.enumerated()), id: \.element.id) { index, step in
                    StepRow(step: step)
                    if index < model.steps.count - 1 { Divider().padding(.leading, 44) }
                }
            }
            .card()

            SheetDisclosure(isExpanded: $model.showLog) {
                ScrollView {
                    Text(model.log.joined(separator: "\n"))
                        .font(.system(.caption, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .textSelection(.enabled)
                        .padding(10)
                }
                .defaultScrollAnchor(.bottom)
                .frame(height: 150)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color.subtleFill))
            } label: {
                Text(lang.t("Detailed log")).font(.callout.weight(.medium))
            }

            HStack {
                if model.stage == .failed {
                    Button(lang.t("Copy Log")) {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(model.log.joined(separator: "\n"), forType: .string)
                    }
                }
                Spacer()
                if model.stage == .failed {
                    Button(lang.t("Close")) { model.showFlow = false }
                        .keyboardShortcut(.defaultAction)
                } else {
                    Button(lang.t("Cancel Build")) { model.cancelBuild() }
                        .keyboardShortcut(.cancelAction)
                }
            }
            .controlSize(.large)
        }
        .padding(24)
    }
}

struct StepRow: View {
    let step: BuildStep
    @Environment(\.lang) private var lang

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Group {
                switch step.state {
                case .pending: Image(systemName: "circle").foregroundStyle(.tertiary)
                case .running: ProgressView().controlSize(.small)
                case .done: Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                case .failed: Image(systemName: "xmark.circle.fill").foregroundStyle(.red)
                }
            }
            .font(.title3)
            .frame(width: 20, height: 20)
            VStack(alignment: .leading, spacing: 2) {
                Text(step.title(lang)).font(.body.weight(.medium))
                    .foregroundStyle(step.state == .pending ? .secondary : .primary)
                Text(step.detail(lang)).font(.callout).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer()
            if let s = step.seconds {
                Text(String(format: "%.1f s", s))
                    .font(.system(.callout, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
    }
}

// MARK: - Result

struct ResultView: View {
    @Bindable var model: BuilderModel
    @Environment(\.lang) private var lang
    @State private var copied = false

    var body: some View {
        let r = model.result
        VStack(alignment: .leading, spacing: 18) {
            HStack(spacing: 14) {
                Image(systemName: "checkmark.seal.fill").font(.system(size: 40)).foregroundStyle(.green)
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Text(lang.t("Firmware Built and Verified Offline"))
                            .font(.title2.weight(.bold))
                    }
                    Text(lang.t("Offline verification is not a safety guarantee on camera. Review the known limits again before installing."))
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            if let r {
                VStack(alignment: .leading, spacing: 0) {
                    HStack(spacing: 12) {
                        Image(systemName: "memorychip.fill").font(.system(size: 26)).foregroundStyle(Color.accentColor)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(r.fileName).font(.headline)
                            Text(formattedBytes(r.bytes, lang)).font(.callout).foregroundStyle(.secondary)
                        }
                        Spacer()
                    }
                    .padding(16)
                    Divider().padding(.leading, 16)
                    VStack(alignment: .leading, spacing: 9) {
                        SummaryLine(label: lang.t("Identity"), value: r.identity, mono: true)
                        SummaryLine(label: lang.t("Groups"),
                                    value: r.features.map { Catalog.feature($0).name(lang) }.joined(separator: lang.t(LocalizedStringResource(", ", comment: "Separator between feature group names"))))
                        HStack(alignment: .firstTextBaseline, spacing: 10) {
                            Text(verbatim: "SHA-256").foregroundStyle(.secondary).frame(width: 74, alignment: .leading)
                            Text(String(r.sha256.prefix(32)) + "\n" + String(r.sha256.dropFirst(32)))
                                .font(.system(.callout, design: .monospaced))
                                .textSelection(.enabled)
                                .fixedSize(horizontal: false, vertical: true)
                            Spacer(minLength: 0)
                        }
                        .font(.callout)
                        SummaryLine(label: lang.t("Location"), value: abbreviatedPath(r.folder), mono: true)
                    }
                    .padding(16)
                }
                .card()
            }

            HStack(spacing: 8) {
                Button {
                    if let s = r?.sha256 {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(s, forType: .string)
                        copied = true
                    }
                } label: {
                    Label(copied ? lang.t("Copied") : lang.t("Copy SHA-256"),
                          systemImage: copied ? "checkmark" : "doc.on.doc")
                }
                .disabled(r == nil)
                Button(lang.t("View Manifest")) {
                    if let r { NSWorkspace.shared.open(r.folder.appendingPathComponent("manifest.json")) }
                }
                .disabled(r == nil)
                Spacer()
                Button(lang.t("Done")) { model.showFlow = false }
                Button(lang.t("Show in Finder")) {
                    if let r { NSWorkspace.shared.activateFileViewerSelecting([r.folder.appendingPathComponent(r.fileName)]) }
                }
                .keyboardShortcut(.defaultAction)
                .disabled(r == nil)
            }
            .controlSize(.large)
        }
        .padding(24)
    }
}
