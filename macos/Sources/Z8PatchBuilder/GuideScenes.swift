import SwiftUI

// Camera-operation guide animations, one per feature group.
// Visual language follows the v0.4.0 intro storyboard (promo_v040_20261109/storyboard.src.html,
// scenes S3–S6): camera menu colours sampled from emulator screenshots, the stylised landscape,
// the 16:9 → 3:2 morph, desqueeze, pre-capture timeline and pixel-shift merge. v0.5.0 adds the
// 4.1K 3:2 rows, SDR HEIF, the still crops and the stock footer keys of the pixel-shift page.
// Camera wording follows the UI language through CamText: stock C 3.11 strings and the patch’s own
// strings in English, Simplified and Traditional Chinese, checked against emulator screenshots.
// Every scene is a pure function of t (seconds), drawn on a 480 × 320 logical camera screen.

// MARK: - Timing

func clamp01(_ x: Double) -> Double { min(1, max(0, x)) }
func easeIO(_ x: Double) -> Double { x < 0.5 ? 4 * x * x * x : 1 - pow(-2 * x + 2, 3) / 2 }
/// Eased 0→1 progress of t across [a, b].
func prog(_ t: Double, _ a: Double, _ b: Double) -> Double { easeIO(clamp01((t - a) / (b - a))) }
/// Cursor-style stepping: hold each value, glide to the next at its key time.
func stepped(_ t: Double, _ keys: [(Double, Double)], glide: Double = 0.3) -> Double {
    var v = keys[0].1
    for k in keys.dropFirst() { v += (k.1 - v) * prog(t, k.0, k.0 + glide) }
    return v
}
/// 1 inside [a, b) with short fades at both ends.
func window(_ t: Double, _ a: Double, _ b: Double, fade: Double = 0.25) -> Double {
    min(prog(t, a, a + fade), 1 - prog(t, b - fade, b))
}

// MARK: - Guide model

struct GuideStep: Identifiable {
    let id: Int
    let start: Double
    let end: Double
    let caption: L
    /// Representative frame for paused / reduced-motion display and screenshots.
    var keyTime: Double { end - 0.45 }
}

struct FeatureGuide {
    let id: FeatureID
    let duration: Double
    let steps: [GuideStep]

    func stepIndex(at t: Double) -> Int { steps.lastIndex { t >= $0.start } ?? 0 }

    /// Step timing belongs to the scenes below; captions come from resources/gui-catalog.json
    /// (the catalog check refuses a toolkit whose caption count differs).
    static let timing: [FeatureID: (duration: Double, bounds: [(Double, Double)])] = [
        .videoRecording: (24, [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 24)]),
        .logColour: (12, [(0, 4), (4, 8), (8, 12)]),
        .stillPhotoTools: (24, [(0, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 24)]),
        .rawPrecapture: (12, [(0, 4), (4, 8), (8, 12)]),
    ]

    static func of(_ id: FeatureID) -> FeatureGuide {
        let t = timing[id]!
        let captions = Catalog.feature(id).guide
        return FeatureGuide(id: id, duration: t.duration, steps: t.bounds.enumerated().map { i, b in
            GuideStep(id: i, start: b.0, end: b.1, caption: captions[i])
        })
    }
}

// MARK: - Camera palette and primitives

enum Cam {
    static let yellow = Color(red: 0xFB / 255, green: 0xD6 / 255, blue: 0x24 / 255)
    static let green = Color(red: 0x58 / 255, green: 0x70 / 255, blue: 0)
    static let row = Color(white: 0x22 / 255)
    static let head = Color(white: 0x15 / 255)
    static let text = Color(white: 0.95)
    static let cursorEdge = Color(red: 0.23, green: 0.19, blue: 0)
    static let w: CGFloat = 480
    static let h: CGFloat = 320

    static func font(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
        .system(size: size, weight: weight).width(.condensed)
    }
}

/// LCD-like frame; content is laid out at 480 × 320 and scaled to the available width.
struct CamBezel<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        GeometryReader { geo in
            content
                .frame(width: Cam.w, height: Cam.h, alignment: .topLeading)
                .background(Color.black)
                .clipped()
                .scaleEffect(geo.size.width / Cam.w, anchor: .topLeading)
        }
        .aspectRatio(Cam.w / Cam.h, contentMode: .fit)
        // An ideal-size proposal (nil width) would otherwise collapse the GeometryReader.
        .frame(minWidth: 120, idealWidth: 320, maxWidth: .infinity)
        // Height always follows the width (a short height proposal must not squeeze it).
        .fixedSize(horizontal: false, vertical: true)
        .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
        .padding(7)
        .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(Color(white: 0.09)))
        .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).strokeBorder(Color.white.opacity(0.10)))
        .environment(\.colorScheme, .dark)
    }
}

struct CamRail: View {
    let active: Int   // 0 photo shooting, 1 video recording
    private let icons = ["camera.fill", "video.fill", "pencil", "play.rectangle.fill", "wrench.fill", "network", "list.bullet.indent"]

    var body: some View {
        VStack(spacing: 2) {
            ForEach(icons.indices, id: \.self) { i in
                ZStack {
                    if i == active { RoundedRectangle(cornerRadius: 4).fill(Cam.green).padding(2) }
                    Image(systemName: icons[i])
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundStyle(Color(white: 0.86))
                }
                .frame(width: 44, height: 40)
            }
            Spacer(minLength: 0)
        }
        .padding(.top, 4)
        .frame(width: 48)
        .background(Color(white: 0.06))
    }
}

struct CamRow {
    var text: String
    var value: String? = nil
    var checked: Bool? = nil
    /// false for a plain value column without the sub-page arrow (e.g. the tone on Video file type).
    var chevron = true
    /// Small outlined icon before the text, e.g. the image-area marks "FX", "4:3", "2.39".
    var badge: String? = nil
}

struct CamMenu: View {
    var title: String
    var centeredTitle = false
    var counter: String? = nil
    var header: String? = nil
    var rows: [CamRow]
    var cursor: Double
    var press: Double = 0          // 0…1 flash on OK
    var rail: Int? = 1
    var back = true
    var footer = false
    /// Footer key pairs, e.g. [("MENU", "Cancel"), ("OK", "OK")] (the stock button group).
    var keys: [(String, String)] = [("OK", "Select"), ("MENU", "Back")]
    var mono = false
    /// Rows scrolled off the top (fractional while gliding).
    var scroll: Double = 0
    private let rowH: CGFloat = 36

    var body: some View {
        HStack(spacing: 0) {
            if let rail { CamRail(active: rail) }
            VStack(alignment: .leading, spacing: 0) {
                titleBar
                if let header {
                    Text(header).font(Cam.font(20)).foregroundStyle(Cam.text)
                        .padding(.horizontal, 8)
                        .frame(height: 32, alignment: .leading)
                }
                ZStack(alignment: .topLeading) {
                    VStack(spacing: 2) {
                        ForEach(rows.indices, id: \.self) { _ in Cam.row.frame(height: rowH - 2) }
                    }
                    Rectangle()
                        .fill(Cam.yellow)
                        .overlay(Rectangle().strokeBorder(Cam.cursorEdge, lineWidth: 1.5).padding(3))
                        .overlay(Color.white.opacity(0.45 * press))
                        .frame(height: rowH - 2)
                        .offset(y: CGFloat(cursor) * rowH)
                    VStack(spacing: 2) {
                        ForEach(rows.indices, id: \.self) { i in
                            label(rows[i], selected: abs(cursor - Double(i)) < 0.5).frame(height: rowH - 2)
                        }
                    }
                }
                .offset(y: -CGFloat(scroll) * rowH)
                .frame(maxHeight: .infinity, alignment: .topLeading)
                .clipped()
                .padding(.top, 3)
                if footer { footerBar }
            }
        }
    }

    private var titleBar: some View {
        HStack(spacing: 6) {
            if centeredTitle { Spacer() }
            Text(title).font(Cam.font(centeredTitle ? 21 : 23)).foregroundStyle(Cam.text)
            Spacer()
            if let counter { Text(counter).font(Cam.font(22)).foregroundStyle(Cam.text) }
            if back {
                Image(systemName: "arrow.uturn.backward")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(Cam.text)
                    .frame(width: 36, height: 24)
                    .overlay(RoundedRectangle(cornerRadius: 4).strokeBorder(Color(white: 0.75), lineWidth: 1.5))
            }
        }
        .padding(.horizontal, 8)
        .frame(height: 38)
        .background(Cam.head)
    }

    private func label(_ r: CamRow, selected: Bool) -> some View {
        let c = selected ? Color.black : Cam.text
        return HStack(spacing: 6) {
            if let checked = r.checked {
                RoundedRectangle(cornerRadius: 2).strokeBorder(c, lineWidth: 1.5)
                    .frame(width: 18, height: 18)
                    .overlay(checked ? Image(systemName: "checkmark").font(.system(size: 12, weight: .heavy)).foregroundStyle(c) : nil)
                Text(verbatim: "SD").font(.system(size: 9, weight: .bold)).foregroundStyle(c)
                    .padding(.horizontal, 2)
                    .overlay(RoundedRectangle(cornerRadius: 2).strokeBorder(c, lineWidth: 1))
            }
            if let b = r.badge {
                Text(verbatim: b).font(.system(size: 10, weight: .bold).width(.condensed)).foregroundStyle(c)
                    .frame(width: 30, height: 18)
                    .overlay(RoundedRectangle(cornerRadius: 2).strokeBorder(c, lineWidth: 1.2))
                    .padding(.trailing, 6)
            }
            Text(r.text)
                .font(mono ? .system(size: 16, design: .monospaced) : Cam.font(21))
                .foregroundStyle(c)
                .lineLimit(1)
            Spacer(minLength: 4)
            if let v = r.value {
                Text(r.chevron ? v + " ›" : v).font(Cam.font(18)).foregroundStyle(selected ? Color.black : Color(white: 0.8))
            }
        }
        .padding(.horizontal, 8)
    }

    /// Stock button-group bar (emulator screenshot of the pixel-shift page): grey strip, outlined keys.
    private var footerBar: some View {
        HStack(spacing: 6) {
            Spacer()
            ForEach(keys.indices, id: \.self) { i in key(keys[i].0, keys[i].1) }
        }
        .padding(.horizontal, 8)
        .frame(height: 36)
        .background(Color(white: 0x2B / 255))
    }

    /// `k` is a key cap ("OK", "MENU") or, prefixed "sf:", a symbol such as the multi selector.
    private func key(_ k: String, _ s: String) -> some View {
        HStack(spacing: 3) {
            if k.hasPrefix("sf:") {
                Image(systemName: String(k.dropFirst(3))).font(.system(size: 17, weight: .semibold)).foregroundStyle(Cam.text)
            } else {
                Text(k).font(.system(size: 12, weight: .heavy).width(.condensed)).foregroundStyle(.black)
                    .padding(.horizontal, 3).padding(.vertical, 1)
                    .background(RoundedRectangle(cornerRadius: 3).fill(Color(white: 0.9)))
            }
            Text(s).font(Cam.font(20)).foregroundStyle(Cam.text)
        }
        .padding(.horizontal, 5).padding(.vertical, 2)
        .overlay(RoundedRectangle(cornerRadius: 4).strokeBorder(Color(white: 0.6), lineWidth: 1.5))
    }
}

/// Stylised landscape from the storyboard's land(): `trueAspect` keeps circles round when the
/// drawn rect has that aspect; any other aspect shows the squeeze.
struct Landscape: View {
    var trueAspect: Double = 1.5
    /// 0 = display look, 1 = flat Log-like look (lifted, low contrast, desaturated).
    var flat: Double = 0

    var body: some View {
        Canvas { ctx, size in
            let W = size.width, H = size.height
            func X(_ u: Double) -> CGFloat { CGFloat(u) * W }
            func Y(_ v: Double) -> CGFloat { CGFloat(v) * H }
            func RX(_ r: Double) -> CGFloat { CGFloat(r / trueAspect) * W }
            func RY(_ r: Double) -> CGFloat { CGFloat(r) * H }
            let k = clamp01(flat)
            func hex(_ v: UInt32) -> Color {
                var c = [Double((v >> 16) & 0xFF) / 255, Double((v >> 8) & 0xFF) / 255, Double(v & 0xFF) / 255]
                let y = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
                c = c.map { ch in
                    let desat = ch + (y - ch) * 0.7 * k
                    return 0.40 + (desat - 0.40) * (1 - 0.6 * k)
                }
                return Color(red: c[0], green: c[1], blue: c[2])
            }
            ctx.fill(Path(CGRect(x: 0, y: 0, width: W, height: H)), with: .color(hex(0x13202B)))
            ctx.fill(Path(CGRect(x: 0, y: Y(0.46), width: W, height: H * 0.26)), with: .color(hex(0x1A2A36)))
            ctx.fill(Path(ellipseIn: CGRect(x: X(0.3) - RX(0.17), y: Y(0.36) - RY(0.17), width: 2 * RX(0.17), height: 2 * RY(0.17))), with: .color(hex(0xE8A33C)))
            ctx.stroke(Path(ellipseIn: CGRect(x: X(0.74) - RX(0.08), y: Y(0.3) - RY(0.08), width: 2 * RX(0.08), height: 2 * RY(0.08))), with: .color(hex(0xD9D9D9)), lineWidth: max(1.5, H * 0.012))
            for m in [[0, 0.16, 0.3, 0.5], [0.4, 0.6, 0.82, 0.4], [0.7, 0.88, 1, 0.55]] {
                var p = Path()
                p.move(to: CGPoint(x: X(m[0]), y: Y(0.72)))
                p.addLine(to: CGPoint(x: X(m[1]), y: Y(m[3])))
                p.addLine(to: CGPoint(x: X(m[2]), y: Y(0.72)))
                p.closeSubpath()
                ctx.fill(p, with: .color(hex(0x2C3A46)))
            }
            ctx.fill(Path(CGRect(x: 0, y: Y(0.72), width: W, height: H * 0.28)), with: .color(hex(0x1C2219)))
            for k in 0..<6 {
                let cx = X(0.1 + Double(k) * 0.16), cy = Y(0.86)
                ctx.fill(Path(ellipseIn: CGRect(x: cx - RX(0.05), y: cy - RY(0.05), width: 2 * RX(0.05), height: 2 * RY(0.05))), with: .color(hex(0x3D4A2F)))
            }
        }
    }
}

struct Chip: View {
    let text: String
    var on = true
    var accent = false

    var body: some View {
        Text(text)
            .font(Cam.font(17, .semibold))
            .foregroundStyle(accent ? Color.black : Cam.text)
            .padding(.horizontal, 6).padding(.vertical, 2)
            .background(RoundedRectangle(cornerRadius: 3).fill(accent ? Cam.yellow : Color.black.opacity(0.55)))
            .opacity(on ? 1 : 0)
    }
}

/// Crossfade between two pages at time `at`.
struct Pages<A: View, B: View>: View {
    let t: Double
    let at: Double
    @ViewBuilder var first: A
    @ViewBuilder var second: B

    var body: some View {
        let k = prog(t, at, at + 0.3)
        ZStack {
            if k < 1 { first.opacity(1 - k) }
            if k > 0 { second.opacity(k) }
        }
    }
}

// MARK: - Camera text

/// Camera wording in the three UI languages, as the camera shows it: stock C 3.11 strings (menu
/// language slots 1, 8 and 9) and the patch's own strings, read back from a v0.5.0 image composed in
/// memory from the stock EG. Chinese frame sizes use the stock "x" and spacing.
struct CamText {
    let en: String, hans: String, hant: String
    init(_ en: String, _ hans: String, _ hant: String) { (self.en, self.hans, self.hant) = (en, hans, hant) }
    init(_ same: String) { (en, hans, hant) = (same, same, same) }
    func callAsFunction(_ lang: Lang) -> String {
        switch lang {
        case .en: return en
        case .zhHans: return hans
        case .zhHant: return hant
        }
    }
}

enum CamStr {
    // Stock strings (id in the C 3.11 table).
    static let videoMenu = CamText("VIDEO RECORDING MENU", "视频拍摄菜单", "短片記錄選單")                 // 1106
    static let photoMenu = CamText("PHOTO SHOOTING MENU", "照片拍摄菜单", "相片拍攝選單")                  // 1105
    static let storageFolder = CamText("Storage folder", "存储文件夹", "儲存檔案夾")                        // 346
    static let fileNaming = CamText("File naming", "文件命名", "檔案名稱")                                // 757
    static let destination = CamText("Destination", "目标位置", "儲存目的地")                             // 479
    static let videoFileType = CamText("Video file type", "视频文件类型", "短片檔案類型")                   // 1268
    static let frameSize = CamText("Frame size/frame rate", "画面尺寸/帧频", "畫面大小/每秒幅數")          // 955
    static let qualityNRAW = CamText("Video quality (N-RAW)", "视频品质(N-RAW)", "短片品質(N-RAW)")       // 2214
    static let nraw = CamText("N-RAW 12-bit (NEV)", "N-RAW 12位(NEV)", "N-RAW 12-bit(NEV)")              // 2030
    static let proresRAW = CamText("ProRes RAW HQ 12-bit (MOV)", "ProRes RAW HQ 12位(MOV)", "ProRes RAW HQ 12-bit(MOV)") // 2031
    static let h265_10 = CamText("H.265 10-bit (MOV)", "H.265 10位(MOV)", "H.265 10-bit(MOV)")           // 1957
    static let h265_8 = CamText("H.265 8-bit (MOV)", "H.265 8位(MOV)", "H.265 8-bit(MOV)")               // 1789
    static let h264 = CamText("H.264 8-bit (MP4)", "H.264 8位(MP4)", "H.264 8-bit(MP4)")                 // 1790
    static let highQuality = CamText("High quality", "高品质", "高品質")                                  // 862
    static let normal = CamText("Normal", "标准", "標準")                                                 // 373
    static let off = CamText("Off", "关闭", "關閉")                                                       // 375
    static let viewAssist = CamText("VIEW ASSIST", "色彩显示辅助", "顯示輔助")                             // 1504 (chip)
    static let primarySlot = CamText("Primary slot selection", "主插槽选择", "主插槽選擇")                  // 1013
    static let secondarySlot = CamText("Secondary slot function", "第二插槽的功能", "副插槽功能")            // 1014
    static let imageArea = CamText("Image area", "图像区域", "影像區域")                                    // 772
    static let chooseImageArea = CamText("Choose image area", "选择图像区域", "選擇影像區域")                // 775
    static let toneMode = CamText("Tone mode", "色调模式", "色調模式")                                      // 1800
    static let qualitySettings = CamText("Image quality settings", "图像品质设定", "影像品質設定")           // 2417
    static let sizeSettings = CamText("Image size settings", "图像尺寸设定", "影像大小設定")                 // 2297
    static let rawRecording = CamText("RAW recording", "RAW录制", "RAW 記錄")                              // 351
    static let ok = CamText("OK", "确定", "OK")                                                            // 1554
    static let cancel = CamText("Cancel", "取消", "取消")                                                  // 332
    // Patch strings (id in the v0.5.0 four-group image).
    static let nraw32 = CamText("N-RAW 12-bit 3:2 (NEV)", "N-RAW 12位 3:2(NEV)", "N-RAW 12-bit 3:2(NEV)") // 3232
    static let prores422 = CamText("ProRes 422 10-bit (MOV)", "ProRes 422 10位(MOV)", "ProRes 422 10-bit(MOV)") // 3152
    static let fine = CamText("Fine", "精细", "精細")                                                      // 3140
    static let basic = CamText("Basic", "基本", "基本")                                                    // 3141
    static let qualityProRes = CamText("Video quality (ProRes)", "视频品质(ProRes)", "短片品質(ProRes)")  // 3147
    static let qualityH265 = CamText("Video quality (H.265)", "视频品质(H.265)", "短片品質(H.265)")       // 3161
    static let desqueeze = CamText("Anamorphic desqueeze", "变形镜头还原显示", "變形鏡頭拉伸顯示")            // 3153
    static let logSettings = CamText("Log settings", "Log设定", "Log設定")                                // 3218
    static let sdrFileFormat = CamText("SDR file format", "SDR文件格式", "SDR檔案格式")                    // 3236
    static let fileFormat = CamText("File format", "文件格式", "檔案格式")                                 // 3237 (after the ◇ glyph)
    static let psMerge = CamText("Pixel shift merge", "像素变化合成", "像素位移合成")                        // 3142 / ui_strings.h
    // Pixel-shift page text (z8pixelshift/src/ui_strings.h).
    static func psSelected(_ n: Int) -> CamText { CamText("Merge selected (\(n))", "合成所选组 (\(n))", "合成所選組 (\(n))") }
    static let psAll = CamText("Select all unmerged", "选择全部未合成", "選擇全部未合成")
    static let psNew = CamText("new", "未合成", "未合成")
    static let psMerged = CamText("merged", "已合成", "已合成")
    static let psShots = CamText(" shots ", "张", "張")
}

/// Frame size labels: English "×" with three spaces before a two-digit rate, Chinese "x" with two.
private func sizeLabel(_ size: String, _ rate: String, _ lang: Lang) -> String {
    let pad = rate.count > 3 ? " " : (lang == .en ? "   " : "  ")
    return "[FX] " + (lang == .en ? size : size.replacingOccurrences(of: "×", with: "x")) + ";" + pad + rate
}

private func videoMenuRows(_ lang: Lang, fileType: String = "N-RAW 3:2", log: String = "N-Log", size: String = "4.1K 120p") -> [CamRow] {
    [CamRow(text: CamStr.storageFolder(lang), value: "NCZ_8"),
     CamRow(text: CamStr.fileNaming(lang), value: "DSC"),
     CamRow(text: CamStr.destination(lang), value: "CFe"),
     CamRow(text: CamStr.videoFileType(lang), value: fileType),
     CamRow(text: CamStr.logSettings(lang), value: log),
     CamRow(text: CamStr.frameSize(lang), value: size),
     CamRow(text: CamStr.qualityNRAW(lang), value: "HIGH")]
}

/// Video file type with the added N-RAW 3:2 row (open-gate E1+) and the ProRes row as the video
/// group relabels it; the right column is each type's tone.
private func fileTypes(_ lang: Lang) -> [CamRow] {
    [CamStr.nraw, CamStr.nraw32, CamStr.proresRAW, CamStr.prores422, CamStr.h265_10, CamStr.h265_8, CamStr.h264]
        .map { CamRow(text: $0(lang), value: "SDR", chevron: false) }
}

/// Frame size/frame rate of N-RAW 3:2: the stock [FX] labels with the 3:2 heights.
private func frameSizes(_ lang: Lang) -> [CamRow] {
    (["30p", "25p", "24p"].map { sizeLabel("8256×5504", $0, lang) }
        + ["120p", "100p", "60p", "50p", "30p", "25p", "24p"].map { sizeLabel("4128×2752", $0, lang) }).map { CamRow(text: $0) }
}

/// PHOTO SHOOTING MENU from Primary slot selection down (stock C 3.11 order); `tone` is the
/// patched Tone mode value, SDR-J or SDR-H.
private func photoMenuRows(_ lang: Lang, tone: String) -> [CamRow] {
    [CamRow(text: CamStr.primarySlot(lang), value: "CFe"),
     CamRow(text: CamStr.secondarySlot(lang), value: ""),
     CamRow(text: CamStr.imageArea(lang), value: ""),
     CamRow(text: CamStr.toneMode(lang), value: tone),
     CamRow(text: CamStr.qualitySettings(lang), value: ""),
     CamRow(text: CamStr.sizeSettings(lang), value: ""),
     CamRow(text: CamStr.rawRecording(lang), value: "ON")]
}

/// Tone mode page: the SDR row names its file format; ◇ (right) opens SDR file format.
private func toneRows(_ format: String) -> [CamRow] {
    [CamRow(text: "SDR", value: format, chevron: false), CamRow(text: "HLG")]
}

/// Choose image area with the three added still crops (row order and labels from the patch).
private func imageAreas(_ lang: Lang) -> [CamRow] {
    let en = ["FX    (36×24)", "DX   (24×16)", "4:3   (32×24)", "1:1   (24×24)", "16:9 (36×20)", "2.39:1 (36×15)", "65:24 (36×13)"]
    let zh = ["FX   (36x24)", "DX   (24x16)", "4:3  (32x24)", "1:1  (24x24)", "16:9 (36x20)", "2.39:1 (36x15)", "65:24 (36x13)"]
    return zip(["FX", "DX", "4:3", "1:1", "16:9", "2.39", "XPan"], lang == .en ? en : zh).map { CamRow(text: $0.1, badge: $0.0) }
}

/// A pixel-shift group row: English puts count and state in the row, Chinese in a right-hand column.
private func psGroup(_ lang: Lang, _ path: String, _ shots: Int, merged: Bool, checked: Bool) -> CamRow {
    let state = (merged ? CamStr.psMerged : CamStr.psNew)(lang)
    if lang == .en { return CamRow(text: "\(path) \(shots) shots \(state)", checked: checked) }
    return CamRow(text: path, value: "\(shots)\(CamStr.psShots(lang))\(state)", checked: checked, chevron: false)
}

/// OK-press flash centred at time `at`.
func flash(_ t: Double, _ at: Double) -> Double { max(0, 1 - abs(t - at) / 0.18) }

// MARK: - Scenes

struct GuideScene: View {
    let id: FeatureID
    let t: Double
    @Environment(\.lang) private var lang

    var body: some View {
        switch id {
        case .videoRecording: video
        case .logColour: log
        case .stillPhotoTools: photo
        case .rawPrecapture: precapture
        }
    }

    // Video recording: file type N-RAW 3:2 → its own frame size list → 4.1K 3:2 live view →
    // N-RAW tiers → desqueeze → ProRes and H.265 grades.
    @ViewBuilder private var video: some View {
        if t < 4 {
            Pages(t: t, at: 1.5) {
                CamMenu(title: CamStr.videoMenu(lang), centeredTitle: true, rows: videoMenuRows(lang, fileType: "N-RAW", size: "4.1K 60p"),
                        cursor: stepped(t, [(0, 1), (0.4, 3)]), press: flash(t, 1.2), back: false)
            } second: {
                CamMenu(title: CamStr.videoFileType(lang), rows: fileTypes(lang),
                        cursor: stepped(t, [(0, 0), (2.3, 1)]), press: flash(t, 3.4))
            }
        } else if t < 8 {
            Pages(t: t, at: 5.4) {
                CamMenu(title: CamStr.videoMenu(lang), centeredTitle: true, rows: videoMenuRows(lang, size: "4.1K 60p"),
                        cursor: stepped(t, [(0, 3), (4.3, 5)]), press: flash(t, 5.1), back: false)
            } second: {
                CamMenu(title: CamStr.frameSize(lang), header: CamStr.nraw32(lang), rows: frameSizes(lang),
                        cursor: stepped(t, [(0, 0), (6.0, 3)], glide: 0.6), press: flash(t, 7.5),
                        scroll: stepped(t, [(0, 0), (6.0, 3)], glide: 0.6))
            }
        } else if t < 12 {
            let k = prog(t, 8.8, 10.0)
            aspectMorph(k: k, from: "16:9 · 4128×2322", to: "3:2 · 4128×2752",
                        chips: ["4.1K 120p", "FX", k < 0.5 ? "N-RAW" : "N-RAW 3:2"])
        } else if t < 16 {
            CamMenu(title: CamStr.qualityNRAW(lang),
                    rows: [CamStr.highQuality, CamStr.fine, CamStr.normal, CamStr.basic].map { CamRow(text: $0(lang)) },
                    cursor: stepped(t, [(0, 0), (13.0, 1), (14.0, 2), (15.0, 3)]))
        } else if t < 20 {
            Pages(t: t, at: 17.6) {
                CamMenu(title: CamStr.desqueeze(lang),
                        rows: [CamStr.off(lang), "1.25x", "1.30x", "1.33x", "1.50x", "1.60x", "1.80x"].map { CamRow(text: $0) },
                        cursor: stepped(t, [(0, 0), (16.4, 3)], glide: 0.6), press: flash(t, 17.3))
            } second: {
                desqueezeView(d: 1 + 0.33 * prog(t, 18.1, 19.0))
            }
        } else {
            Pages(t: t, at: 22.0) {
                CamMenu(title: CamStr.qualityProRes(lang),
                        rows: ["ProRes 422 HQ", "ProRes 422", "ProRes 422 LT", "ProRes 422 Proxy"].map { CamRow(text: $0) },
                        cursor: stepped(t, [(0, 0), (20.7, 2)], glide: 0.45))
            } second: {
                CamMenu(title: CamStr.qualityH265(lang),
                        rows: ["100%  150 Mbps", "60%  90 Mbps", "45%  68 Mbps", "30%  45 Mbps", "20%  30 Mbps"].map { CamRow(text: $0) },
                        cursor: stepped(t, [(0, 0), (22.8, 1)]))
            }
        }
    }

    private func aspectMorph(k: Double, from: String, to: String, chips: [String]) -> some View {
        let W = Cam.w, H32 = Cam.h
        let h = (W * 9 / 16) + (H32 - W * 9 / 16) * CGFloat(k)
        return ZStack {
            Landscape(trueAspect: 1.5).opacity(0.22)
            Landscape(trueAspect: 1.5).mask(Rectangle().frame(width: W, height: h))
            Rectangle().strokeBorder(Cam.yellow, lineWidth: 3).frame(width: W - 4, height: h - 4)
            VStack {
                HStack(spacing: 6) {
                    Text(verbatim: k < 0.5 ? from : to)
                        .font(.system(size: 16, weight: .semibold, design: .monospaced))
                        .foregroundStyle(Cam.yellow)
                    Spacer()
                    ForEach(chips, id: \.self) { Chip(text: $0) }
                }
                Spacer()
            }
            .padding(10)
            .offset(y: (Cam.h - h) / 2)
        }
    }

    private func desqueezeView(d: Double) -> some View {
        let W = Cam.w, H = W / CGFloat(16.0 / 9.0 * d)
        return ZStack {
            Landscape(trueAspect: 16.0 / 9.0 * 1.33).frame(width: W, height: H)
            cornerBrackets.frame(width: W, height: H)
            VStack {
                HStack {
                    Spacer()
                    Text(String(format: "%.2f×", d)).font(.system(size: 18, weight: .semibold, design: .monospaced)).foregroundStyle(Cam.yellow)
                }
                Spacer()
            }
            .padding(10)
        }
        .frame(width: Cam.w, height: Cam.h)
    }

    private var cornerBrackets: some View {
        GeometryReader { g in
            let w = g.size.width, h = g.size.height
            Path { p in
                let ax = w * 0.3 - w * 0.075, ay = h * 0.36 - h * 0.16, aw = w * 0.15, ah = h * 0.32, L: CGFloat = 12
                p.move(to: CGPoint(x: ax, y: ay + L)); p.addLine(to: CGPoint(x: ax, y: ay)); p.addLine(to: CGPoint(x: ax + L, y: ay))
                p.move(to: CGPoint(x: ax + aw - L, y: ay)); p.addLine(to: CGPoint(x: ax + aw, y: ay)); p.addLine(to: CGPoint(x: ax + aw, y: ay + L))
                p.move(to: CGPoint(x: ax + aw, y: ay + ah - L)); p.addLine(to: CGPoint(x: ax + aw, y: ay + ah)); p.addLine(to: CGPoint(x: ax + aw - L, y: ay + ah))
                p.move(to: CGPoint(x: ax + L, y: ay + ah)); p.addLine(to: CGPoint(x: ax, y: ay + ah)); p.addLine(to: CGPoint(x: ax, y: ay + ah - L))
            }
            .stroke(Color.white, lineWidth: 2.5)
        }
    }

    // Log colour: Log settings → view assist → per-clip playback names.
    @ViewBuilder private var log: some View {
        if t < 4 {
            Pages(t: t, at: 1.4) {
                CamMenu(title: CamStr.videoMenu(lang), centeredTitle: true, rows: videoMenuRows(lang, log: "Log3G10"),
                        cursor: stepped(t, [(0, 3), (0.45, 4)]), press: flash(t, 1.15), back: false)
            } second: {
                CamMenu(title: CamStr.logSettings(lang),
                        rows: ["N-Log / BT.2020", "S-Log3 / S-Gamut3.Cine", "Log3G10 / REDWideGamutRGB"].map { CamRow(text: $0) },
                        cursor: stepped(t, [(0, 0), (2.1, 1), (3.0, 2)]))
            }
        } else if t < 8 {
            logView(name: "Log3G10", assist: prog(t, 5.3, 6.1), playback: false)
        } else {
            let second = prog(t, 9.9, 10.4)
            ZStack {
                logView(name: "S-Log3", assist: 1, playback: true).offset(x: -Cam.w * CGFloat(second))
                logView(name: "Log3G10", assist: 1, playback: true).offset(x: Cam.w * CGFloat(1 - second))
            }
            .clipped()
        }
    }

    private func logView(name: String, assist: Double, playback: Bool) -> some View {
        ZStack(alignment: .topLeading) {
            Landscape(trueAspect: 16.0 / 9.0, flat: 1 - assist)
            .frame(width: Cam.w, height: Cam.w * 9 / 16)
            .offset(y: (Cam.h - Cam.w * 9 / 16) / 2)
            HStack(spacing: 6) {
                if playback {
                    Image(systemName: "play.fill").font(.system(size: 14)).foregroundStyle(Cam.text)
                    Text(verbatim: name == "S-Log3" ? "DSC_0001.NEV" : "DSC_0002.NEV").font(.system(size: 14, design: .monospaced)).foregroundStyle(Cam.text)
                }
                Spacer()
                Chip(text: name, accent: true)
                Chip(text: CamStr.viewAssist(lang), accent: assist > 0.5)
            }
            .padding(10)
        }
        .frame(width: Cam.w, height: Cam.h)
    }

    // Photo tools: Tone mode → SDR file format HEIF → SDR-H shot and .HIF playback → Choose image
    // area 2.39:1 → 2.39:1 and 65:24 framing → pixel-shift group list (stock keys) → merge to NEFX.
    @ViewBuilder private var photo: some View {
        if t < 4 {
            Pages(t: t, at: 1.3) {
                CamMenu(title: CamStr.photoMenu(lang), centeredTitle: true, rows: photoMenuRows(lang, tone: "SDR-J"),
                        cursor: stepped(t, [(0, 2), (0.4, 3)]), press: flash(t, 1.0), rail: 0, back: false)
            } second: {
                Pages(t: t, at: 2.3) {
                    CamMenu(title: CamStr.toneMode(lang), rows: toneRows("JPEG"), cursor: 0, press: flash(t, 2.0), rail: 0,
                            footer: true, keys: toneKeys)
                } second: {
                    CamMenu(title: CamStr.sdrFileFormat(lang), rows: [CamRow(text: "JPEG"), CamRow(text: "HEIF")],
                            cursor: stepped(t, [(0, 0), (2.8, 1)]), press: flash(t, 3.5), rail: 0)
                }
            }
        } else if t < 8 {
            Pages(t: t, at: 5.4) {
                Pages(t: t, at: 4.6) {
                    CamMenu(title: CamStr.toneMode(lang), rows: toneRows("HEIF"), cursor: 0, press: flash(t, 4.35), rail: 0,
                            footer: true, keys: toneKeys)
                } second: {
                    CamMenu(title: CamStr.photoMenu(lang), centeredTitle: true, rows: photoMenuRows(lang, tone: "SDR-H"),
                            cursor: 3, rail: 0, back: false)
                }
            } second: {
                heifView(shot: 6.1, playback: 6.8)
            }
        } else if t < 12 {
            CamMenu(title: CamStr.imageArea(lang), header: CamStr.chooseImageArea(lang), rows: imageAreas(lang),
                    cursor: stepped(t, [(0, 0), (8.6, 5)], glide: 0.8), press: flash(t, 11.0), rail: 0,
                    scroll: stepped(t, [(0, 0), (8.6, 1)], glide: 0.8))
        } else if t < 16 {
            let r = 1.5 + (2.39 - 1.5) * prog(t, 12.4, 13.4) + (65.0 / 24 - 2.39) * prog(t, 14.4, 15.2)
            let crop = r < 1.95 ? ("FX · 8256×5504", "FX") : r < 2.55 ? ("2.39:1 · 8256×3456", "2.39") : ("65:24 · 8256×3048", "XPan")
            cropView(ratio: r, label: crop.0, badge: crop.1)
        } else if t < 20 {
            let ticked = t >= 17.35
            CamMenu(title: CamStr.psMerge(lang), counter: "1/1",
                    rows: [CamRow(text: CamStr.psSelected(ticked ? 1 : 0)(lang)), CamRow(text: CamStr.psAll(lang)),
                           psGroup(lang, "300NCZ_8/DSC_4660", 16, merged: false, checked: ticked),
                           psGroup(lang, "300NCZ_8/DSC_4676", 4, merged: true, checked: false)],
                    cursor: stepped(t, [(0, 2), (18.2, 0)], glide: 0.5), press: max(flash(t, 17.3), flash(t, 19.3)),
                    rail: nil, back: false, footer: true, keys: [("MENU", CamStr.cancel(lang)), ("OK", CamStr.ok(lang))])
        } else {
            mergeView(start: 20)
        }
    }

    private var toneKeys: [(String, String)] { [("sf:dpad", CamStr.fileFormat(lang)), ("OK", CamStr.ok(lang))] }

    /// Shooting display with SDR HEIF, the shutter flash, then playback of the .HIF file.
    private func heifView(shot: Double, playback at: Double) -> some View {
        let playback = prog(t, at, at + 0.3)
        return ZStack(alignment: .topLeading) {
            Landscape(trueAspect: 1.5)
            Color.white.opacity(0.8 * flash(t, shot))
            HStack(spacing: 6) {
                if playback > 0.5 {
                    Image(systemName: "play.fill").font(.system(size: 14)).foregroundStyle(Cam.text)
                    Text(verbatim: "DSC_0001.HIF").font(.system(size: 14, design: .monospaced)).foregroundStyle(Cam.text)
                }
                Spacer()
                Chip(text: "SDR-H", accent: playback < 0.5)
                Chip(text: "HEIF", accent: playback > 0.5)
                Chip(text: "FINE★")
            }
            .padding(10)
        }
        .frame(width: Cam.w, height: Cam.h)
    }

    /// 3:2 sensor view with the outside of a wider still crop masked.
    private func cropView(ratio: Double, label: String, badge: String) -> some View {
        let W = Cam.w, H = Cam.h
        let cw = ratio >= 1.5 ? W : H * CGFloat(ratio)
        let ch = ratio >= 1.5 ? W / CGFloat(ratio) : H
        return ZStack(alignment: .topLeading) {
            Landscape(trueAspect: 1.5)
            Path { p in
                p.addRect(CGRect(x: 0, y: 0, width: W, height: H))
                p.addRect(CGRect(x: (W - cw) / 2, y: (H - ch) / 2, width: cw, height: ch))
            }
            .fill(Color.black.opacity(0.72), style: FillStyle(eoFill: true))
            Rectangle().strokeBorder(Cam.yellow, lineWidth: 2.5).frame(width: cw, height: ch)
                .position(x: W / 2, y: H / 2)
                .opacity(prog(t, 12.2, 12.6))
            VStack(alignment: .leading) {
                HStack(spacing: 6) {
                    Text(verbatim: label)
                        .font(.system(size: 16, weight: .semibold, design: .monospaced))
                        .foregroundStyle(Cam.yellow)
                    Spacer()
                    Text(verbatim: badge).font(.system(size: 13, weight: .bold).width(.condensed)).foregroundStyle(Cam.text)
                        .frame(width: 40, height: 24)
                        .overlay(RoundedRectangle(cornerRadius: 3).strokeBorder(Cam.text, lineWidth: 1.5))
                    Chip(text: "HEIF")
                }
                Spacer()
            }
            .padding(10)
        }
        .frame(width: W, height: H)
    }

    // RAW pre-capture: C30 · RAW · HE★ and DX → half-press buffering → full press keeps earlier frames.
    @ViewBuilder private var precapture: some View {
        precaptureView(press: 8.0)
    }

    private func precaptureView(press: Double) -> some View {
        let dx = prog(t, 2.4, 3.2)
        return ZStack(alignment: .topLeading) {
            Landscape(trueAspect: 1.5)
            // DX crop: darken outside the 2/3 central area.
            let cw = Cam.w * (1 - CGFloat(dx) / 3), ch = Cam.h * (1 - CGFloat(dx) / 3)
            Path { p in
                p.addRect(CGRect(x: 0, y: 0, width: Cam.w, height: Cam.h))
                p.addRect(CGRect(x: (Cam.w - cw) / 2, y: (Cam.h - ch) / 2, width: cw, height: ch))
            }
            .fill(Color.black.opacity(0.6 * dx), style: FillStyle(eoFill: true))
            Rectangle().strokeBorder(Cam.yellow, lineWidth: 2.5).frame(width: cw, height: ch)
                .position(x: Cam.w / 2, y: Cam.h / 2).opacity(dx)
            HStack(spacing: 6) {
                if t > 0.4 { Chip(text: "C30", accent: t < 1.0) }
                if t > 1.0 { Chip(text: "RAW", accent: t < 1.6) }
                if t > 1.6 { Chip(text: "HE★", accent: t < 2.3) }
                Chip(text: dx > 0.5 ? "DX" : "FX", accent: dx > 0.1 && t < 3.6)
                Spacer()
            }
            .padding(10)
            if t >= 4 { timeline(press: press) }
        }
        .frame(width: Cam.w, height: Cam.h)
    }

    private func timeline(press: Double) -> some View {
        let shift = CGFloat((min(t, press) - 4) * 90).truncatingRemainder(dividingBy: 24)
        let marker: CGFloat = 330
        return ZStack(alignment: .topLeading) {
            Rectangle().fill(Color.black.opacity(0.72)).frame(width: Cam.w, height: 74)
            ForEach(0..<24, id: \.self) { j in
                let x = Cam.w - 24 - CGFloat(j) * 24 - shift + 24
                let saved = t > press && x < marker && (marker - x) < CGFloat(t - press) * 520
                RoundedRectangle(cornerRadius: 2)
                    .fill(saved ? Color.white : Color(white: 0.3))
                    .frame(width: 16, height: 26)
                    .offset(x: x, y: 14)
                    .opacity(t > 4.2 ? 1 : 0)
            }
            Rectangle().fill(Cam.yellow).frame(width: 3, height: 50).offset(x: marker, y: 6).opacity(prog(t, press - 0.1, press + 0.1))
            Text(lang.t("Half-press: buffering")).font(.system(size: 13, weight: .medium)).foregroundStyle(Color(white: 0.75))
                .offset(x: 12, y: 48).opacity(prog(t, 4.2, 4.6) * (1 - prog(t, press, press + 0.2)))
            Text(lang.t("Full press: earlier frames saved")).font(.system(size: 13, weight: .semibold)).foregroundStyle(Cam.yellow)
                .offset(x: 12, y: 48).opacity(prog(t, press, press + 0.3))
        }
        .frame(width: Cam.w, height: 74)
        .clipped()
        .offset(y: Cam.h - 74)
    }

    private func mergeView(start: Double) -> some View {
        let k = prog(t, start + 0.3, start + 1.6)
        let done = prog(t, start + 1.8, start + 2.3)
        return ZStack {
            Color.black
            ForEach(0..<4, id: \.self) { i in
                let off = CGFloat(i) * 22 * CGFloat(1 - k)
                Landscape(trueAspect: 1.5)
                    .frame(width: 210, height: 140)
                    .overlay(Rectangle().strokeBorder(Color(white: 0.35), lineWidth: 1.5))
                    .offset(x: -70 + off + 35 * CGFloat(k), y: -40 + off * 0.6 + 20 * CGFloat(k))
                    .opacity(i == 0 ? 1 : 1 - k * 0.9)
            }
            VStack(spacing: 6) {
                Spacer()
                ZStack(alignment: .leading) {
                    Capsule().fill(Color(white: 0.25)).frame(width: 300, height: 8)
                    Capsule().fill(Cam.yellow).frame(width: 300 * CGFloat(prog(t, start + 0.2, start + 1.8)), height: 8)
                }
                .opacity(1 - done)
                HStack(spacing: 8) {
                    Text(verbatim: "NEFX").font(.system(size: 18, weight: .bold, design: .monospaced)).foregroundStyle(.black)
                        .padding(.horizontal, 6).background(RoundedRectangle(cornerRadius: 3).fill(Cam.yellow))
                    Text(verbatim: "16512×11008").font(.system(size: 18, weight: .semibold, design: .monospaced)).foregroundStyle(Cam.text)
                }
                .opacity(done)
            }
            .padding(.bottom, 26)
        }
        .frame(width: Cam.w, height: Cam.h)
    }
}
