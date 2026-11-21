import SwiftUI
import UniformTypeIdentifiers

struct MainView: View {
    @Bindable var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        ScrollView {
            MainPageContent(model: model)
        }
        .background(Color.pageBackground)
        .safeAreaInset(edge: .bottom, spacing: 0) { BottomBar(model: model) }
        .inspector(isPresented: $model.showInspector) {
            InspectorView(model: model)
                .inspectorColumnWidth(min: 300, ideal: 350, max: 440)
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                SettingsLink {
                    Label(lang.t("Settings"), systemImage: "gearshape")
                }
                .help(lang.t("Settings (language, appearance, bundled toolkit)"))
            }
            ToolbarItem(placement: .primaryAction) {
                Button {
                    withAnimation { model.showInspector.toggle() }
                } label: {
                    Label(lang.t("Inspector"), systemImage: "sidebar.trailing")
                }
                .help(lang.t("Show or hide feature details"))
            }
        }
        .navigationTitle(lang.t("Z8 Patch Builder"))
        .navigationSubtitle(lang.t("Toolkit \(Catalog.toolkitTag) · Original C 3.11"))
        .fileImporter(isPresented: $model.requestOpenInput, allowedContentTypes: [.data]) { result in
            if case .success(let url) = result { model.loadInput(url) }
        }
        .sheet(isPresented: $model.showFlow) {
            BuildFlowSheet(model: model)
                .environment(\.lang, lang)
        }
    }
}

struct MainPageContent: View {
    var model: BuilderModel

    var body: some View {
        VStack(alignment: .leading, spacing: 26) {
            HeroHeader(model: model)
            if !model.toolkit.ok { ToolkitProblemBanner(model: model) }
            InputSection(model: model)
            FeatureSection(model: model)
            ExportSection(model: model)
        }
        .padding(.horizontal, 36)
        .padding(.top, 26)
        .padding(.bottom, 30)
        .frame(maxWidth: 880)
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Header

struct AppGlyph: View {
    var size: CGFloat = 64

    var body: some View {
        if Bundle.main.object(forInfoDictionaryKey: "CFBundleIconFile") != nil {
            Image(nsImage: NSApp.applicationIconImage)
                .resizable()
                .frame(width: size * 1.16, height: size * 1.16)
        } else {
            fallback
        }
    }

    private var fallback: some View {
        RoundedRectangle(cornerRadius: size * 0.235, style: .continuous)
            .fill(LinearGradient(colors: [Color(red: 0.20, green: 0.48, blue: 1.0), Color(red: 0.42, green: 0.28, blue: 0.96)],
                                 startPoint: .topLeading, endPoint: .bottomTrailing))
            .overlay(
                Image(systemName: "memorychip")
                    .font(.system(size: size * 0.46, weight: .semibold))
                    .foregroundStyle(.white)
            )
            .overlay(RoundedRectangle(cornerRadius: size * 0.235, style: .continuous).strokeBorder(.white.opacity(0.18)))
            .frame(width: size, height: size)
            .shadow(color: .black.opacity(0.18), radius: 6, y: 3)
    }
}

struct ToolkitProblemBanner: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: "exclamationmark.octagon.fill").font(.title2).foregroundStyle(.red)
            VStack(alignment: .leading, spacing: 4) {
                Text(lang.t("The bundled toolkit failed its self-check; building is disabled"))
                    .font(.headline)
                Text(lang.t("Files inside the app differ from the release manifest. Download the app again from the GitHub release."))
                    .foregroundStyle(.secondary)
                Text(model.toolkit.problems.prefix(4).joined(separator: "\n"))
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
            }
            Spacer(minLength: 0)
        }
        .padding(16)
        .card(highlighted: true, tint: .red)
    }
}

struct HeroHeader: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack(alignment: .center, spacing: 18) {
                AppGlyph(size: 62)
                VStack(alignment: .leading, spacing: 5) {
                    HStack(spacing: 10) {
                        Text(lang.t("Build Modified Firmware"))
                            .font(.system(size: 27, weight: .bold))
                    }
                    Text(lang.t("Start from the original Z8 C 3.11 firmware, choose feature groups, then check, build and verify in one pass."))
                        .font(.title3)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            StepIndicator(model: model)
        }
    }
}

struct StepIndicator: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        let done = [model.inputValid, !model.selected.isEmpty, model.versionValid && model.tagValid && model.outputParent != nil]
        let titles = [lang.t("Original firmware"), lang.t("Feature groups"), lang.t(LocalizedStringResource("steps.export", defaultValue: "Export"))]
        let current = done.firstIndex(of: false) ?? 3
        HStack(spacing: 10) {
            ForEach(0..<3, id: \.self) { i in
                HStack(spacing: 7) {
                    ZStack {
                        Circle().fill(done[i] ? Color.green : (i == current ? Color.accentColor : Color.secondary.opacity(0.25)))
                        if done[i] {
                            Image(systemName: "checkmark").font(.system(size: 10, weight: .bold)).foregroundStyle(.white)
                        } else {
                            Text(verbatim: "\(i + 1)").font(.system(size: 11, weight: .bold)).foregroundStyle(i == current ? .white : .secondary)
                        }
                    }
                    .frame(width: 20, height: 20)
                    Text(titles[i])
                        .font(.callout.weight(i == current ? .semibold : .regular))
                        .foregroundStyle(done[i] || i == current ? .primary : .secondary)
                }
                if i < 2 {
                    Capsule().fill(done[i] ? Color.green.opacity(0.5) : Color.secondary.opacity(0.2)).frame(height: 2).frame(maxWidth: 80)
                }
            }
            Spacer(minLength: 0)
        }
    }
}

// MARK: - Section chrome

struct SectionHeader: View {
    let number: Int
    let title: String
    var subtitle: String? = nil
    var accessory: AnyView? = nil

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(verbatim: "\(number)")
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .foregroundStyle(.secondary)
                .frame(width: 22, height: 22)
                .background(Circle().fill(Color.subtleFill))
                .alignmentGuide(.firstTextBaseline) { d in d[VerticalAlignment.center] + 5 }
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.title2.weight(.semibold))
                if let subtitle {
                    Text(subtitle).font(.callout).foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            Spacer(minLength: 12)
            if let accessory { accessory }
        }
    }
}

struct CardBackground: ViewModifier {
    var highlighted = false
    var tint: Color = .accentColor

    func body(content: Content) -> some View {
        content
            .background(RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(highlighted ? AnyShapeStyle(tint.opacity(0.07)) : AnyShapeStyle(Color.cardBackground)))
            .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(highlighted ? tint.opacity(0.85) : Color.cardStroke, lineWidth: highlighted ? 1.6 : 1))
    }
}

extension View {
    func card(highlighted: Bool = false, tint: Color = .accentColor) -> some View {
        modifier(CardBackground(highlighted: highlighted, tint: tint))
    }
}

// MARK: - 1 Input

struct InputSection: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang
    @State private var targeted = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(number: 1, title: lang.t("Original Firmware"),
                          subtitle: lang.t("Only the complete original Nikon Z8 C 3.11 (Z_8_0311.bin) is accepted; patched firmware cannot be patched again."))
            content
                .dropDestination(for: URL.self) { urls, _ in
                    guard let url = urls.first else { return false }
                    model.loadInput(url)
                    return true
                } isTargeted: { targeted = $0 }
        }
    }

    @ViewBuilder private var content: some View {
        switch model.input {
        case .empty:
            DropZone(targeted: targeted) { model.requestOpenInput = true }
        case .hashing(let url, let fraction):
            VStack(alignment: .leading, spacing: 12) {
                FileRow(url: url, detail: lang.t("Computing SHA-256…"), symbolTint: .secondary) { EmptyView() }
                ProgressView(value: fraction).progressViewStyle(.linear)
            }
            .padding(18)
            .card()
        case .checked(let info):
            VStack(alignment: .leading, spacing: 0) {
                FileRow(url: info.url,
                        detail: formattedBytes(info.bytes, lang) + " · " + abbreviatedPath(info.url.deletingLastPathComponent()),
                        symbolTint: info.isValid ? .green : .red) {
                    Button(lang.t("Replace…")) { model.requestOpenInput = true }
                }
                .padding(18)
                Divider().padding(.leading, 18)
                VStack(alignment: .leading, spacing: 10) {
                    CheckRow(ok: info.sizeOK,
                             title: lang.t("File length"),
                             detail: info.sizeOK ? formattedBytes(info.bytes, lang)
                                                 : lang.t("Expected \(formattedBytes(model.toolkit.input.bytes, lang))"))
                    CheckRow(ok: info.hashOK,
                             title: "SHA-256",
                             detail: info.hashOK ? lang.t("Matches original C 3.11")
                                                 : lang.t("Does not match original C 3.11"),
                             mono: shortHash(info.sha256),
                             help: info.sha256)
                    CheckRow(ok: toolkitCheckState(info.toolkitCheck),
                             title: lang.t("Toolkit check"),
                             detail: toolkitCheckText(info.toolkitCheck))
                }
                .padding(18)
                if !info.isValid && info.toolkitCheck != .running {
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: "info.circle.fill").foregroundStyle(.secondary)
                        Text(lang.t("This may be C 3.12, an incomplete download or already-patched firmware. Use the official C 3.11 file; to recover, reinstall a complete package that previously worked."))
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(.horizontal, 18)
                    .padding(.bottom, 16)
                }
            }
            .card()
        }
    }

    private func toolkitCheckState(_ c: ToolCheck) -> Bool? {
        switch c {
        case .running: return nil
        case .passed: return true
        case .failed, .notRun: return false
        }
    }

    private func toolkitCheckText(_ c: ToolCheck) -> String {
        switch c {
        case .running: return lang.t("Running patch.py --check…")
        case .passed(let id): return lang.t("Container, modules and CRC pass · identity \(id)")
        case .failed(let message): return message
        case .notRun: return lang.t("Not run: input is not original C 3.11")
        }
    }

    private func shortHash(_ s: String) -> String {
        s.count > 20 ? String(s.prefix(10)) + "…" + String(s.suffix(8)) : s
    }
}

struct DropZone: View {
    let targeted: Bool
    let choose: () -> Void
    @Environment(\.lang) private var lang

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: "arrow.down.doc")
                .font(.system(size: 34, weight: .light))
                .foregroundStyle(targeted ? Color.accentColor : .secondary)
            Text(lang.t("Drop Z_8_0311.bin here"))
                .font(.headline)
            HStack(spacing: 12) {
                Button(lang.t("Choose File…"), action: choose)
                Link(lang.t("Getting official C 3.11"),
                     destination: URL(string: "https://github.com/XinmiaoZhao/NikonFirmwarePatch#readme")!)
                    .font(.callout)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 30)
        .background(RoundedRectangle(cornerRadius: 14, style: .continuous)
            .fill(targeted ? Color.accentColor.opacity(0.08) : Color.cardBackground))
        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous)
            .strokeBorder(targeted ? Color.accentColor : Color.secondary.opacity(0.35), style: StrokeStyle(lineWidth: 1.5, dash: [6, 5])))
    }
}

struct FileRow<Trailing: View>: View {
    let url: URL
    let detail: String
    let symbolTint: Color
    @ViewBuilder var trailing: Trailing

    var body: some View {
        HStack(spacing: 14) {
            ZStack(alignment: .bottomTrailing) {
                Image(systemName: "doc.fill")
                    .font(.system(size: 30))
                    .foregroundStyle(.secondary.opacity(0.55))
                Circle().fill(symbolTint).frame(width: 11, height: 11)
                    .overlay(Circle().strokeBorder(Color.cardBackground, lineWidth: 2))
                    .offset(x: 3, y: 2)
            }
            .frame(width: 34)
            VStack(alignment: .leading, spacing: 3) {
                Text(url.lastPathComponent).font(.headline)
                Text(detail).font(.callout).foregroundStyle(.secondary)
            }
            Spacer()
            trailing
        }
    }
}

struct CheckRow: View {
    /// nil while the check is still running.
    let ok: Bool?
    let title: String
    let detail: String
    var mono: String? = nil
    var help: String? = nil

    var body: some View {
        HStack(spacing: 10) {
            Group {
                if let ok {
                    Image(systemName: ok ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .foregroundStyle(ok ? .green : .red)
                } else {
                    ProgressView().controlSize(.mini)
                }
            }
            .frame(width: 16)
            Text(title).frame(width: 150, alignment: .leading)
            HStack(spacing: 6) {
                Text(detail).lineLimit(2)
                if let mono { Text(mono).font(.system(.callout, design: .monospaced)) }
            }
            .foregroundStyle(.secondary)
            .textSelection(.enabled)
            .help(help ?? detail)
            Spacer(minLength: 0)
        }
        .font(.callout)
    }
}

// MARK: - 2 Features

struct FeatureSection: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(number: 2, title: lang.t("Feature Groups"),
                          accessory: AnyView(HStack(spacing: 6) {
                              Button(lang.t("Select All")) { model.selectAll() }
                              Button(lang.t("Clear")) { model.clearSelection() }
                                  .disabled(model.selected.isEmpty)
                          }.controlSize(.small)))
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 14), GridItem(.flexible(), spacing: 14)], spacing: 14) {
                ForEach(Catalog.features) { feature in
                    FeatureCard(feature: feature,
                                selected: model.selected.contains(feature.id),
                                focused: model.focused == feature.id && model.showInspector,
                                toggle: { withAnimation(.snappy(duration: 0.18)) { model.toggle(feature.id) } },
                                showDetails: { model.focused = feature.id; withAnimation { model.showInspector = true } })
                }
            }
            CombinationFooter(model: model)
        }
    }
}

struct FeatureIcon: View {
    let feature: Feature
    var size: CGFloat = 38

    var body: some View {
        RoundedRectangle(cornerRadius: size * 0.27, style: .continuous)
            .fill(feature.tint.gradient)
            .overlay(Image(systemName: feature.symbol)
                .font(.system(size: size * 0.48, weight: .medium))
                .foregroundStyle(.white))
            .frame(width: size, height: size)
    }
}

struct FeatureCard: View {
    let feature: Feature
    let selected: Bool
    let focused: Bool
    let toggle: () -> Void
    let showDetails: () -> Void
    @Environment(\.lang) private var lang
    @State private var hovering = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .top, spacing: 13) {
                FeatureIcon(feature: feature, size: 42)
                VStack(alignment: .leading, spacing: 2) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(feature.name(lang)).font(.title3.weight(.semibold))
                        Spacer()
                        Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                            .font(.system(size: 20))
                            .foregroundStyle(selected ? Color.accentColor : Color.secondary.opacity(0.5))
                            .accessibilityHidden(true)
                    }
                    Text(feature.id.rawValue)
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(.secondary)
                    Text(feature.summary(lang))
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .lineLimit(2, reservesSpace: true)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.top, 5)
                }
            }
            Divider().padding(.vertical, 12)
            HStack {
                Label(lang.t("\(feature.limits.count) known limits"),
                      systemImage: "exclamationmark.triangle.fill")
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.orange)
                    .labelStyle(.titleAndIcon)
                Spacer()
                Button(action: showDetails) {
                    HStack(spacing: 2) {
                        Text(lang.t("Details"))
                        Image(systemName: "chevron.right").font(.caption2.weight(.semibold))
                    }
                    .font(.caption.weight(.medium))
                }
                .buttonStyle(.link)
            }
        }
        .padding(16)
        .card(highlighted: selected, tint: .accentColor)
        .overlay(RoundedRectangle(cornerRadius: 17, style: .continuous)
            .strokeBorder(Color.accentColor.opacity(focused ? 0.22 : 0), lineWidth: 3)
            .padding(-3))
        .scaleEffect(hovering ? 1.004 : 1)
        .contentShape(RoundedRectangle(cornerRadius: 14))
        .onTapGesture(perform: toggle)
        .onHover { hovering = $0 }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isButton)
        .accessibilityValue(selected ? lang.t("Selected") : lang.t("Not selected"))
        .accessibilityAction(named: lang.t("Show details"), showDetails)
    }
}

struct CombinationFooter: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        HStack(spacing: 8) {
            if model.selected.isEmpty {
                Image(systemName: "circle.dashed").foregroundStyle(.secondary)
                Text(lang.t("No feature group selected")).foregroundStyle(.secondary)
            } else {
                Image(systemName: "checkmark.seal.fill").foregroundStyle(.green)
                Text(lang.t("\(model.selected.count) of 4 selected"))
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
        }
        .font(.callout)
        .padding(.horizontal, 4)
    }
}

// MARK: - 3 Export

struct ExportSection: View {
    @Bindable var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionHeader(number: 3, title: lang.t("Export"))
            VStack(alignment: .leading, spacing: 0) {
                Grid(alignment: .leadingFirstTextBaseline, horizontalSpacing: 18, verticalSpacing: 16) {
                    GridRow {
                        fieldLabel(lang.t(LocalizedStringResource("export.version", defaultValue: "Version")))
                        HStack(spacing: 10) {
                            TextField("" as String, text: $model.version, prompt: Text(verbatim: BuilderModel.defaultVersion))
                                .textFieldStyle(.roundedBorder)
                                .font(.system(.body, design: .monospaced))
                                .frame(width: 84)
                            if model.version.isEmpty {
                                hint(lang.t("Enter NN.NN, e.g. 04.07. Give different selections different versions so they are distinguishable on the camera."))
                            } else {
                                validation(ok: model.versionValid,
                                           good: lang.t("Format NN.NN. Give different selections different versions so they are distinguishable on the camera."),
                                           bad: lang.t("Use two digits, a dot and two digits, e.g. 04.07"))
                            }
                        }
                    }
                    if model.identityReusedForOtherSelection {
                        GridRow {
                            Color.clear.gridCellUnsizedAxes([.horizontal, .vertical])
                            Label(lang.t("\(model.identity) was used on this Mac for a different selection. Choose another version so two different packages do not show the same version on the camera."),
                                  systemImage: "exclamationmark.triangle.fill")
                                .font(.callout)
                                .foregroundStyle(.orange)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    if model.offlineOnlyVersion {
                        GridRow {
                            Color.clear.gridCellUnsizedAxes([.horizontal, .vertical])
                            Label(lang.t("00.xx is reserved for offline tests and must not be installed."),
                                  systemImage: "exclamationmark.triangle.fill")
                                .font(.callout)
                                .foregroundStyle(.orange)
                        }
                    }
                    GridRow {
                        fieldLabel(lang.t("Internal tag"))
                        HStack(spacing: 10) {
                            TextField("p0" as String, text: $model.tag)
                                .textFieldStyle(.roundedBorder)
                                .font(.system(.body, design: .monospaced))
                                .frame(width: 84)
                            validation(ok: model.tagValid,
                                       good: lang.t("One lowercase letter and one digit, written as identity \(model.versionValid ? model.version : "NN.NN").\(model.tag)"),
                                       bad: lang.t("Use one lowercase letter and one digit, e.g. p0"))
                        }
                    }
                    GridRow {
                        fieldLabel(lang.t(LocalizedStringResource("export.location", defaultValue: "Location")))
                        HStack(spacing: 10) {
                            HStack(spacing: 6) {
                                Image(systemName: "folder.fill").foregroundStyle(Color.accentColor)
                                Text(model.outputParent.map(abbreviatedPath) ?? lang.t("Not chosen"))
                                    .lineLimit(1)
                                    .truncationMode(.middle)
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(RoundedRectangle(cornerRadius: 6).fill(Color.subtleFill))
                            Button(lang.t("Choose…")) { model.requestChooseOutput = true }
                        }
                    }
                    GridRow {
                        fieldLabel(lang.t("Creates"))
                        VStack(alignment: .leading, spacing: 6) {
                            Text(model.outputFolderName + "/")
                                .font(.system(.callout, design: .monospaced).weight(.medium))
                                .textSelection(.enabled)
                            HStack(spacing: 6) {
                                FileChip(name: model.outputFileName, symbol: "memorychip")
                                FileChip(name: "manifest.json", symbol: "doc.text")
                                FileChip(name: "SHA256SUMS.txt", symbol: "number")
                            }
                        }
                    }
                }
                .padding(18)
                Divider().padding(.leading, 18)
                DisclosureGroup(isExpanded: $model.showAdvanced) {
                    VStack(alignment: .leading, spacing: 10) {
                        Picker(lang.t("Patch code"), selection: $model.codeSource) {
                            Text(lang.t("Prebuilt units (recommended)")).tag(CodeSource.prebuilt)
                            Text(lang.t("Compile from source")).tag(CodeSource.source)
                        }
                        .pickerStyle(.radioGroup)
                        Text(model.codeSource == .prebuilt
                             ? lang.t("Uses the reviewed prebuilt units in the toolkit; no compiler needed.")
                             : lang.t("Reviewed with \(model.toolkit.reviewedCompiler ?? "Apple clang"); any other compiler must reproduce the same bytes, symbols and entry points or the build stops."))
                            .font(.callout)
                            .foregroundStyle(.secondary)
                        if model.codeSource == .source {
                            HStack {
                                Text(lang.t("Compiler"))
                                TextField("clang" as String, text: $model.compiler)
                                    .textFieldStyle(.roundedBorder)
                                    .font(.system(.body, design: .monospaced))
                                    .frame(width: 220)
                                    .onSubmit { model.checkCompiler() }
                                Button(lang.t("Check")) { model.checkCompiler() }
                                    .disabled(model.checkingCompiler)
                            }
                            CompilerStatus(model: model)
                        }
                    }
                    // Without a full-width frame the disclosure content is centred when it is narrower
                    // than the row (the short prebuilt hint) and left-aligned when a long hint wraps.
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 10)
                    .padding(.leading, 4)
                } label: {
                    Text(lang.t("Advanced")).font(.callout.weight(.medium))
                }
                .padding(.horizontal, 18)
                .padding(.vertical, 12)
            }
            .card()
        }
        .fileImporter(isPresented: $model.requestChooseOutput, allowedContentTypes: [.folder]) { result in
            if case .success(let url) = result { model.chooseOutput(url) }
        }
    }

    private func hint(_ text: String) -> some View {
        Text(text).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
    }

    private func fieldLabel(_ s: String) -> some View {
        Text(s).foregroundStyle(.secondary).gridColumnAlignment(.trailing)
    }

    private func validation(ok: Bool, good: String, bad: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 5) {
            Image(systemName: ok ? "checkmark.circle.fill" : "exclamationmark.circle.fill")
                .foregroundStyle(ok ? .green : .red)
            Text(ok ? good : bad)
                .foregroundStyle(ok ? .secondary : Color.red)
                .fixedSize(horizontal: false, vertical: true)
        }
        .font(.callout)
    }
}

struct CompilerStatus: View {
    var model: BuilderModel
    @Environment(\.lang) private var lang

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            if model.checkingCompiler {
                ProgressView().controlSize(.mini)
                Text(lang.t("Checking the compiler…")).foregroundStyle(.secondary)
            } else if let c = model.compilerCheck {
                switch c.verdict {
                case .reviewed:
                    Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                    Text(lang.t("Same compiler as the review: \(c.versionLine)")).foregroundStyle(.secondary)
                case .different:
                    Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
                    Text(lang.t("Differs from the reviewed compiler (\(c.versionLine)). The toolkit stops if the bytes differ."))
                        .foregroundStyle(.orange)
                case .missing:
                    Image(systemName: "xmark.circle.fill").foregroundStyle(.red)
                    Text(lang.t("No usable compiler found. Install Xcode or the Command Line Tools, or use the prebuilt units."))
                        .foregroundStyle(.red)
                }
            }
        }
        .font(.callout)
        .fixedSize(horizontal: false, vertical: true)
    }
}

struct FileChip: View {
    let name: String
    let symbol: String

    var body: some View {
        Label(name, systemImage: symbol)
            .font(.caption)
            .padding(.horizontal, 7)
            .padding(.vertical, 3)
            .background(Capsule().fill(Color.subtleFill))
            .overlay(Capsule().strokeBorder(Color.cardStroke))
    }
}

// MARK: - Bottom bar

struct BottomBar: View {
    var model: BuilderModel
    var solid = false
    @Environment(\.lang) private var lang

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: model.canBuild ? "checkmark.circle.fill" : "circle.dashed")
                .font(.title2)
                .foregroundStyle(model.canBuild ? .green : .secondary)
            VStack(alignment: .leading, spacing: 2) {
                Text(model.readiness(lang)).font(.headline)
                Label(lang.t("Experimental firmware: installing it can cause data loss, card corruption or camera malfunction."),
                      systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
            Spacer()
            Button {
                model.beginBuild()
            } label: {
                Label(lang.t("Build Firmware…"), systemImage: "hammer.fill")
                    .padding(.horizontal, 6)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(!model.canBuild)
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 12)
        .background(solid ? AnyShapeStyle(Color.cardBackground) : AnyShapeStyle(.bar))
        .overlay(alignment: .top) { Divider() }
    }
}
