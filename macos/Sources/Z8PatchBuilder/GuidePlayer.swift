import SwiftUI

private struct GuideFixedTimeKey: EnvironmentKey {
    static let defaultValue: Double? = nil
}

extension EnvironmentValues {
    /// Freezes guide animations at a given time (documentation renders).
    var guideFixedTime: Double? {
        get { self[GuideFixedTimeKey.self] }
        set { self[GuideFixedTimeKey.self] = newValue }
    }
}

/// Looping camera-operation guide with step segments, play/pause and a caption.
/// Honors Reduce Motion: starts paused on the first step's key frame.
struct GuidePlayer: View {
    let guide: FeatureGuide
    var large = false
    var onExpand: (() -> Void)? = nil
    @Environment(\.lang) private var lang
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.guideFixedTime) private var fixedTime
    @State private var origin = Date()
    @State private var pausedAt: Double?

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30, paused: pausedAt != nil || fixedTime != nil)) { context in
            let t = time(at: context.date)
            let index = guide.stepIndex(at: t)
            if large {
                HStack(alignment: .top, spacing: 22) {
                    VStack(alignment: .leading, spacing: 12) {
                        screen(t: t, index: index)
                        controls(t: t, index: index)
                    }
                    .frame(width: 520)
                    StepList(guide: guide, current: index, onSelect: jump)
                        .frame(width: 290, alignment: .leading)
                }
            } else {
                VStack(alignment: .leading, spacing: 9) {
                    screen(t: t, index: index)
                    controls(t: t, index: index)
                    caption(index: index)
                }
            }
        }
        .onAppear {
            if reduceMotion && pausedAt == nil { pausedAt = guide.steps[0].keyTime }
        }
    }

    private func screen(t: Double, index: Int) -> some View {
        CamBezel { GuideScene(id: guide.id, t: t) }
            .accessibilityElement()
            .accessibilityLabel(lang.t("Operation guide animation"))
            .accessibilityValue(guide.steps[index].caption(lang))
    }

    private func time(at date: Date) -> Double {
        if let fixedTime { return fixedTime }
        if let pausedAt { return pausedAt }
        return date.timeIntervalSince(origin).truncatingRemainder(dividingBy: guide.duration)
    }

    private func controls(t: Double, index: Int) -> some View {
        HStack(spacing: 8) {
            Button {
                if let p = pausedAt {
                    origin = Date().addingTimeInterval(-p)
                    pausedAt = nil
                } else {
                    pausedAt = t
                }
            } label: {
                Image(systemName: (pausedAt != nil || fixedTime != nil) ? "play.fill" : "pause.fill")
                    .frame(width: 14)
            }
            .buttonStyle(.borderless)
            .help(pausedAt != nil ? lang.t("Play") : lang.t("Pause"))
            HStack(spacing: 4) {
                ForEach(guide.steps) { step in
                    let fill = clamp01((t - step.start) / (step.end - step.start))
                    Button {
                        jump(to: step)
                    } label: {
                        GeometryReader { g in
                            ZStack(alignment: .leading) {
                                Capsule().fill(Color.secondary.opacity(0.22))
                                Capsule().fill(Color.accentColor).frame(width: g.size.width * CGFloat(fill))
                            }
                        }
                        .frame(height: 5)
                        .contentShape(Rectangle().inset(by: -6))
                    }
                    .buttonStyle(.plain)
                    .help(lang.t("Step \(step.id + 1)"))
                }
            }
            Text(verbatim: "\(index + 1)/\(guide.steps.count)")
                .font(.caption.monospacedDigit())
                .foregroundStyle(.secondary)
            if let onExpand {
                Button(action: onExpand) {
                    Image(systemName: "arrow.up.left.and.arrow.down.right")
                }
                .buttonStyle(.borderless)
                .help(lang.t("Open larger"))
            }
        }
    }

    private func caption(index: Int) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(lang.t("Step \(index + 1)"))
                .font(.caption.weight(.semibold))
                .foregroundStyle(Color.accentColor)
            Text(guide.steps[index].caption(lang))
                .font(.callout)
                .fixedSize(horizontal: false, vertical: true)
                .frame(minHeight: 54, alignment: .topLeading)
                .animation(nil, value: index)
        }
    }

    private func jump(to step: GuideStep) {
        if pausedAt != nil || reduceMotion {
            pausedAt = step.keyTime
        } else {
            origin = Date().addingTimeInterval(-step.start)
        }
    }
}

/// Larger guide with the full step list; opened from the inspector.
struct GuideSheet: View {
    let feature: Feature
    var onClose: () -> Void = {}
    @Environment(\.lang) private var lang

    var body: some View {
        let guide = FeatureGuide.of(feature.id)
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 12) {
                FeatureIcon(feature: feature, size: 34)
                VStack(alignment: .leading, spacing: 1) {
                    Text(lang.t("Operation Guide") + " · " + feature.name(lang)).font(.title3.weight(.semibold))
                    Text(lang.t("Illustrative animation; camera menus are redrawn in the camera’s own wording."))
                        .font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
            }
            GuidePlayer(guide: guide, large: true)
            HStack {
                Spacer()
                Button(lang.t("Done"), action: onClose).keyboardShortcut(.defaultAction)
            }
        }
        .padding(22)
    }
}

/// All steps of a guide; the current one is highlighted and each row jumps to its step.
struct StepList: View {
    let guide: FeatureGuide
    var current: Int
    var onSelect: (GuideStep) -> Void
    @Environment(\.lang) private var lang

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(guide.steps) { step in
                let on = step.id == current
                Button { onSelect(step) } label: {
                    HStack(alignment: .top, spacing: 10) {
                        Text(verbatim: "\(step.id + 1)")
                            .font(.system(size: 12, weight: .bold, design: .rounded))
                            .foregroundStyle(on ? Color.white : Color.secondary)
                            .frame(width: 20, height: 20)
                            .background(Circle().fill(on ? Color.accentColor : Color.secondary.opacity(0.18)))
                        Text(step.caption(lang))
                            .font(.callout)
                            .foregroundStyle(on ? Color.primary : Color.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .padding(8)
                    .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(on ? Color.accentColor.opacity(0.10) : Color.clear))
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
        }
    }
}
