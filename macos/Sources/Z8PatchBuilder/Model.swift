import AppKit
import Foundation
import Observation
import SwiftUI

enum ToolCheck: Equatable {
    case running
    case passed(identity: String)
    case failed(String)
    case notRun
}

struct InputInfo {
    var url: URL
    var bytes: Int64
    var sha256: String
    var sizeOK: Bool
    var hashOK: Bool
    /// Result of `patch.py --check` (read-only).
    var toolkitCheck: ToolCheck

    var toolkitCheckOK: Bool { if case .passed = toolkitCheck { return true } else { return false } }
    var isValid: Bool { sizeOK && hashOK && toolkitCheckOK }
}

enum InputState {
    case empty
    case hashing(URL, Double)
    case checked(InputInfo)
}

enum StepState { case pending, running, done, failed }

struct BuildStep: Identifiable {
    let id: Int
    let title: LocalizedStringResource
    let detail: LocalizedStringResource
    var state: StepState = .pending
    var seconds: Double?
    var started: Date?
}

enum FlowStage { case confirm, running, succeeded, failed }

typealias BuildResult = BuildOutcome

@MainActor
@Observable
final class BuilderModel {
    // Toolkit
    let layout: ToolkitLayout?
    var toolkit = ToolkitStatus()
    var toolkitInspected = false

    var input: InputState = .empty
    var selected: Set<FeatureID> = []
    var focused: FeatureID? = .videoRecording
    var version: String { didSet { if version != oldValue { refreshOutputName() } } }
    var tag: String { didSet { if tag != oldValue { refreshOutputName() } } }
    var outputParent: URL? { didSet { refreshOutputName() } }
    var codeSource: CodeSource = .prebuilt { didSet { if codeSource == .source { checkCompiler() } } }
    var compiler = "clang"
    var compilerCheck: CompilerCheck?
    var checkingCompiler = false
    var showAdvanced = false

    var showInspector = true
    var requestOpenInput = false
    var requestChooseOutput = false

    // Build flow sheet
    var showFlow = false
    var stage: FlowStage = .confirm
    var acknowledged = false
    var showSelectedLimits = false
    var steps: [BuildStep] = []
    var log: [String] = []
    var showLog = false
    var result: BuildResult?
    var failure: LocalizedStringResource?
    var failureDetail: String?
    var cleanupNote: LocalizedStringResource?
    private(set) var outputFolderName = ""
    private var runner: ToolRunner?
    private var runTask: Task<Void, Never>?
    private var checkTask: Task<Void, Never>?

    /// Documentation renders (`-snapshotDir`) and the sheet probe (`-sheetProbe`) use a throwaway
    /// domain so they never touch real settings.
    private let defaults: UserDefaults

    init(layout: ToolkitLayout? = ToolkitLayout.locate()) {
        self.layout = layout
        let debugRun = ["snapshotDir", "sheetProbe", "languageProbe"].contains { UserDefaults.standard.string(forKey: $0) != nil }
        if debugRun, let scratch = UserDefaults(suiteName: "z8gui-snapshot-scratch") {
            scratch.removePersistentDomain(forName: "z8gui-snapshot-scratch")
            defaults = scratch
        } else {
            defaults = .standard
        }
        version = defaults.string(forKey: "lastVersion") ?? BuilderModel.defaultVersion
        tag = defaults.string(forKey: "lastTag") ?? "p0"
        outputParent = defaults.string(forKey: "lastOutputParent").map { URL(fileURLWithPath: $0, isDirectory: true) }
            ?? FileManager.default.urls(for: .desktopDirectory, in: .userDomainMask).first
        refreshOutputName()
        // Quitting during a build stops the child process instead of leaving it running.
        NotificationCenter.default.addObserver(forName: NSApplication.willTerminateNotification, object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated { self?.runner?.cancel() }
        }
    }

    /// Hashes the bundled toolkit against its release manifest and installs the feature catalog.
    func inspectToolkit() {
        let layout = layout
        Task.detached(priority: .userInitiated) {
            let (status, parsed) = Toolkit.inspect(layout)
            await MainActor.run {
                if let parsed { Catalog.install(parsed, tag: status.tag, commit: status.commit) }
                self.toolkit = status
                self.toolkitInspected = true
            }
        }
    }

    // MARK: Derived state

    var orderedSelection: [FeatureID] { FeatureID.allCases.filter { selected.contains($0) } }

    var isBuilding: Bool { showFlow && stage == .running }

    /// Opened firmware and selected groups live only in this run (a relaunch starts empty).
    var hasSessionChoices: Bool {
        if case .empty = input { return !selected.isEmpty }
        return true
    }

    var inputValid: Bool {
        if case .checked(let info) = input { return info.isValid }
        return false
    }

    /// The README example identity: each public release adds 0.01 (v0.4.0 used 04.06, v0.5.0 uses 04.07).
    static let defaultVersion = "04.07"

    var versionValid: Bool { version.range(of: #"^[0-9]{2}\.[0-9]{2}$"#, options: .regularExpression) != nil }
    var tagValid: Bool { tag.range(of: #"^[a-z][0-9]$"#, options: .regularExpression) != nil }
    var offlineOnlyVersion: Bool { versionValid && version.hasPrefix("00.") }
    var identity: String { "\(version).\(tag)" }

    /// Earlier builds of this identity with a different selection (stored per Mac).
    var identityReusedForOtherSelection: Bool {
        guard versionValid, tagValid, !selected.isEmpty,
              let earlier = (defaults.dictionary(forKey: "identityHistory") as? [String: String])?[identity] else { return false }
        return earlier != orderedSelection.map(\.rawValue).joined(separator: "+")
    }

    var outputFileName: String {
        "Z_8_" + (versionValid ? version.replacingOccurrences(of: ".", with: "") : "NNNN") + ".bin"
    }

    private var baseFolderName: String {
        let parts = orderedSelection.map(\.short)
        return "Z8-\(versionValid ? version : "NN.NN").\(tag)" + (parts.isEmpty ? "" : "-" + parts.joined(separator: "+"))
    }

    /// First free name: `Z8-04.07.p0-video`, then `… 2`, `… 3`; never an existing folder.
    func refreshOutputName() {
        let base = baseFolderName
        guard let parent = outputParent else { outputFolderName = base; return }
        var name = base
        var n = 2
        while FileManager.default.fileExists(atPath: parent.appendingPathComponent(name).path) {
            name = "\(base) \(n)"
            n += 1
        }
        outputFolderName = name
    }

    var outputFolder: URL? { outputParent?.appendingPathComponent(outputFolderName, isDirectory: true) }

    var canBuild: Bool {
        toolkit.ok && toolkitInspected && inputValid && !selected.isEmpty && versionValid && tagValid && outputParent != nil
            && (codeSource == .prebuilt || !compiler.trimmingCharacters(in: .whitespaces).isEmpty)
    }

    func readiness(_ lang: Lang) -> String {
        if toolkitInspected && !toolkit.ok { return lang.t("The bundled toolkit failed its self-check") }
        if !inputValid { return lang.t("Add the original C 3.11 firmware to begin") }
        if selected.isEmpty { return lang.t("Select at least one feature group") }
        if !versionValid || !tagValid { return lang.t("Enter the version and internal tag") }
        if outputParent == nil { return lang.t("Choose an export location") }
        return lang.t("Ready: \(selected.count) groups → \(outputFileName)")
    }

    var selectedLimitCount: Int { orderedSelection.reduce(0) { $0 + Catalog.feature($1).limits.count } }

    // MARK: Actions

    func toggle(_ id: FeatureID) {
        if selected.contains(id) { selected.remove(id) } else { selected.insert(id) }
        focused = id
        refreshOutputName()
    }

    func selectAll() { selected = Set(FeatureID.allCases); refreshOutputName() }
    func clearSelection() { selected.removeAll(); refreshOutputName() }

    func chooseOutput(_ url: URL) {
        outputParent = url
        defaults.set(url.path, forKey: "lastOutputParent")
    }

    func loadInput(_ url: URL) {
        checkTask?.cancel()
        input = .hashing(url, 0)
        let expected = toolkit.input
        checkTask = Task { [weak self] in
            let digest = await Task.detached(priority: .userInitiated) {
                sha256File(url) { fraction in
                    Task { @MainActor [weak self] in
                        if case .hashing(let u, _) = self?.input, u == url { self?.input = .hashing(url, fraction) }
                    }
                }
            }.value
            guard let self, !Task.isCancelled else { return }
            guard let digest else {
                self.input = .checked(InputInfo(url: url, bytes: 0, sha256: "", sizeOK: false, hashOK: false, toolkitCheck: .notRun))
                return
            }
            let sizeOK = digest.bytes == expected.bytes
            let hashOK = sizeOK && digest.sha256 == expected.sha256
            var info = InputInfo(url: url, bytes: digest.bytes, sha256: digest.sha256, sizeOK: sizeOK, hashOK: hashOK,
                                 toolkitCheck: hashOK ? .running : .notRun)
            self.input = .checked(info)
            guard hashOK, let layout = self.layout, self.toolkit.ok else { return }
            let runner = ToolRunner(layout: layout)
            let out = try? await runner.python("patch.py", [url.path, "--check"], onLine: { _ in })
            guard !Task.isCancelled else { return }
            if let out, out.status == 0, let j = out.json(), j["status"] as? String == "COMPATIBLE" {
                info.toolkitCheck = .passed(identity: j["identity"] as? String ?? "")
            } else {
                info.toolkitCheck = .failed(out?.errorLine ?? "patch.py --check failed to run")
            }
            if case .checked(let current) = self.input, current.url == url { self.input = .checked(info) }
        }
    }

    func checkCompiler() {
        checkingCompiler = true
        let compiler = compiler, reviewed = toolkit.reviewedCompiler
        Task {
            let result = await CompilerCheck.run(compiler, reviewed: reviewed)
            self.compilerCheck = result
            self.checkingCompiler = false
        }
    }

    // MARK: Build flow

    func beginBuild() {
        guard canBuild else { return }
        refreshOutputName()
        stage = .confirm
        acknowledged = false
        showSelectedLimits = false
        showFlow = true
    }

    static func makeSteps() -> [BuildStep] {
        [
            BuildStep(id: 1, title: "Check input",
                      detail: "Length, SHA-256, container and module CRC (patch.py --check)"),
            BuildStep(id: 2, title: "Build firmware",
                      detail: "Compose the selected groups from reviewed recipes and repackage (patch.py)"),
            BuildStep(id: 3, title: "Verify independently",
                      detail: "verify.py, which never imports the builder, checks the output in a separate process"),
            BuildStep(id: 4, title: "Read back",
                      detail: "Re-read the .bin and compare with manifest.json and SHA256SUMS.txt"),
        ]
    }

    func startBuild() {
        guard acknowledged, canBuild, let layout, case .checked(let info) = input, let folder = outputFolder else { return }
        steps = Self.makeSteps()
        log = []
        result = nil
        failure = nil
        failureDetail = nil
        cleanupNote = nil
        stage = .running
        let request = BuildRequest(input: info.url, features: orderedSelection, version: version, tag: tag,
                                   outputFolder: folder, codeSource: codeSource,
                                   compiler: compiler.trimmingCharacters(in: .whitespaces), expected: toolkit.input)
        let runner = ToolRunner(layout: layout)
        self.runner = runner
        let sink = MainSink(self)
        runTask = Task.detached {
            do {
                let outcome = try await BuildPipeline(runner: runner).run(request) { event in
                    sink.send { $0.apply(event) }
                }
                sink.send { $0.finish(outcome) }
            } catch let failure as BuildFailure {
                sink.send { $0.fail(failure, cancelled: runner.isCancelled) }
            } catch {
                let message = runner.isCancelled ? "Cancelled" : error.localizedDescription
                sink.send { $0.fail(BuildFailure(step: 1, message: message), cancelled: runner.isCancelled) }
            }
        }
    }

    func cancelBuild() {
        runner?.cancel()
    }

    private func apply(_ event: BuildPipeline.Event) {
        switch event {
        case .started(let n):
            steps[n - 1].state = .running
            steps[n - 1].started = Date()
        case .finished(let n):
            steps[n - 1].state = .done
            steps[n - 1].seconds = steps[n - 1].started.map { Date().timeIntervalSince($0) }
        case .log(let line):
            log.append(line)
        }
    }

    private func finish(_ outcome: BuildOutcome) {
        result = outcome
        stage = .succeeded
        defaults.set(version, forKey: "lastVersion")
        defaults.set(tag, forKey: "lastTag")
        var history = (defaults.dictionary(forKey: "identityHistory") as? [String: String]) ?? [:]
        history[identity] = outcome.features.map(\.rawValue).joined(separator: "+")
        defaults.set(history, forKey: "identityHistory")
        refreshOutputName()
        runner = nil
    }

    private func fail(_ f: BuildFailure, cancelled: Bool) {
        if let i = steps.firstIndex(where: { $0.state == .running }) ?? steps.firstIndex(where: { $0.state == .pending }) {
            steps[i].state = .failed
            steps[i].seconds = steps[i].started.map { Date().timeIntervalSince($0) }
        }
        failure = cancelled ? "The build was cancelled." : Self.explain(step: f.step)
        failureDetail = cancelled ? nil : f.message
        // No cleanup note means no output folder existed: the CLI creates it only after validation.
        cleanupNote = f.cleanup.map(Self.describeCleanup)
            ?? (cancelled || f.step == 2 ? "Nothing was written." : nil)
        if cancelled { log.append("Cancelled by user") } else { log.append("ERROR: " + f.message) }
        stage = .failed
        refreshOutputName()
        runner = nil
    }

    static func explain(step: Int) -> LocalizedStringResource {
        switch step {
        case 1: return "The input check failed. Nothing was written."
        case 2: return "The build did not complete."
        case 3: return "Independent verification failed; the result must not be installed."
        default: return "Read-back verification failed; the result must not be installed."
        }
    }

    static func describeCleanup(_ note: String) -> LocalizedStringResource {
        let path = abbreviatedPath(URL(fileURLWithPath: String(note.drop { $0 != ":" }.dropFirst())))
        if note.hasPrefix("removed:") { return "Removed the incomplete output folder \(path)." }
        if note.hasPrefix("renamed:") {
            return "The firmware file was renamed to \(path) so it cannot be installed by mistake; the manifest is kept for diagnosis."
        }
        return "Output kept at \(path) because it contains files from elsewhere; it was not removed. Do not install it."
    }

    // MARK: Documentation renders (Snapshotter)

#if DEBUG
    func mockValidInput() {
        let url = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Downloads/Z_8_0311.bin")
        input = .checked(InputInfo(url: url, bytes: toolkit.input.bytes, sha256: toolkit.input.sha256,
                                   sizeOK: true, hashOK: true, toolkitCheck: .passed(identity: "03.11.b0")))
    }

    func mockInvalidInput() {
        let url = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Downloads/Z_8_0407.bin")
        input = .checked(InputInfo(url: url, bytes: toolkit.input.bytes,
                                   sha256: "e084a43bfb37650ead5a55f2a0c582b4b0ff82513aca95da0d99144d3d576533",
                                   sizeOK: true, hashOK: false, toolkitCheck: .notRun))
    }

    func resetForSnapshots() {
        input = .empty
        selected = []
        focused = .videoRecording
        version = BuilderModel.defaultVersion
        tag = "p0"
        showFlow = false
        refreshOutputName()
    }
#endif
}

/// Delivers pipeline events to the model in order: the main queue is FIFO, separate Tasks are not.
final class MainSink: @unchecked Sendable {
    private weak var model: BuilderModel?

    @MainActor init(_ model: BuilderModel) { self.model = model }

    func send(_ work: @escaping @MainActor (BuilderModel) -> Void) {
        DispatchQueue.main.async {
            MainActor.assumeIsolated {
                if let model = self.model { work(model) }
            }
        }
    }
}
