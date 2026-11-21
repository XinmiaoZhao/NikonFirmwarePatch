// Draws the disk-image window background:
//   swift make_dmg_background.swift <out dir> <width> <height> <app x> <Applications x> <icon y> <tag>
// Writes background.tiff (1x and 2x, LZW); build_app.py passes the window size and the icon
// centres it gives Finder (points, origin top left), so the panels and the trace always line up.
// Original artwork in the app icon's palette: graphite, the camera-menu yellow and viewfinder brackets.
//
// Finder draws icon labels over the picture, in black in light mode and in white in dark mode.
// Each label sits on a plate of #6F7781 (relative luminance 0.18), where both reach about 4.5:1.
import AppKit

let args = CommandLine.arguments
let out = URL(fileURLWithPath: args[1], isDirectory: true)
let width = CGFloat(Double(args[2])!), height = CGFloat(Double(args[3])!)
let appX = CGFloat(Double(args[4])!), appsX = CGFloat(Double(args[5])!), iconY = CGFloat(Double(args[6])!)
let tag = args[7]
try! FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)

// Same constructor as make_icon.swift, so the yellow matches the icon.
let yellow = CGColor(red: 0xFB / 255, green: 0xD6 / 255, blue: 0x24 / 255, alpha: 1)
/// Other colours are sRGB values: CGColor(red:green:blue:) is Generic RGB, which lands lighter in the
/// sRGB image and would break the label-plate contrast.
func rgb(_ hex: Int, _ alpha: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat(hex >> 16 & 0xFF) / 255, green: CGFloat(hex >> 8 & 0xFF) / 255, blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
}
let space = CGColorSpace(name: CGColorSpace.sRGB)!
let plate = rgb(0x6F7781)

// Geometry (points, origin top left). Finder's 128-point icons are centred on (x, iconY); their
// labels start a few points below the icon, so the plate runs from 2 to 38 points under it.
let half: CGFloat = 64
let plateTop = iconY + half + 2, plateBottom = iconY + half + 38
func panel(_ x: CGFloat) -> CGRect { CGRect(x: x - 94, y: iconY - 100, width: 188, height: plateBottom - (iconY - 100)) }

func draw(_ ctx: CGContext) {
    ctx.translateBy(x: 0, y: height)
    ctx.scaleBy(x: 1, y: -1)

    // Backdrop: deep graphite, a faint slate glow behind the panels.
    let base = CGGradient(colorsSpace: space, colors: [rgb(0x121519), rgb(0x1A1E23)] as CFArray, locations: [0, 1])!
    ctx.drawLinearGradient(base, start: .zero, end: CGPoint(x: 0, y: height), options: [])
    let glow = CGGradient(colorsSpace: space, colors: [rgb(0x3A4656, 0.55), rgb(0x3A4656, 0)] as CFArray, locations: [0, 1])!
    ctx.drawRadialGradient(glow, startCenter: CGPoint(x: width / 2, y: iconY), startRadius: 0,
                           endCenter: CGPoint(x: width / 2, y: iconY), endRadius: width * 0.55, options: [])

    // Measurement grid, minor every 16 points and major every 64, fading towards the edges.
    ctx.saveGState()
    ctx.setLineWidth(0.5)
    for (step, alpha) in [(16, 0.035), (64, 0.07)] as [(CGFloat, CGFloat)] {
        ctx.setStrokeColor(CGColor(gray: 1, alpha: alpha))
        var x = (width / 2).truncatingRemainder(dividingBy: step)
        while x < width { ctx.move(to: CGPoint(x: x, y: 0)); ctx.addLine(to: CGPoint(x: x, y: height)); x += step }
        var y = iconY.truncatingRemainder(dividingBy: step)
        while y < height { ctx.move(to: CGPoint(x: 0, y: y)); ctx.addLine(to: CGPoint(x: width, y: y)); y += step }
        ctx.strokePath()
    }
    ctx.restoreGState()
    let vignette = CGGradient(colorsSpace: space, colors: [rgb(0x0B0D10, 0), rgb(0x0B0D10, 0.85)] as CFArray, locations: [0.35, 1])!
    ctx.drawRadialGradient(vignette, startCenter: CGPoint(x: width / 2, y: height * 0.55), startRadius: 0,
                           endCenter: CGPoint(x: width / 2, y: height * 0.55), endRadius: width * 0.62, options: [.drawsAfterEndLocation])

    // Viewfinder frame marks in the window corners.
    corners(CGRect(x: 14, y: 14, width: width - 28, height: height - 28), arm: 14, color: CGColor(gray: 1, alpha: 0.22), line: 1.5, ctx)

    // Heading.
    text("拖到 Applications", font: NSFont.systemFont(ofSize: 24, weight: .semibold), color: CGColor(gray: 1, alpha: 1),
         highlight: ("Applications", yellow), centreY: 52, ctx)
    text("DRAG  TO  APPLICATIONS  TO  INSTALL", font: NSFont.monospacedSystemFont(ofSize: 10, weight: .medium),
         color: rgb(0x8C96A3), kern: 1.6, centreY: 82, ctx)
    small("Z8 PATCH BUILDER", x: 34, alignRight: false, ctx)
    small(tag.uppercased(), x: width - 34, alignRight: true, ctx)

    // Panels with label plates and focus brackets.
    for (x, caption) in [(appX, "01  APP"), (appsX, "02  INSTALL")] {
        let rect = panel(x)
        let shape = CGPath(roundedRect: rect, cornerWidth: 14, cornerHeight: 14, transform: nil)
        ctx.saveGState()
        ctx.setShadow(offset: CGSize(width: 0, height: 6), blur: 18, color: CGColor(gray: 0, alpha: 0.5))
        ctx.addPath(shape)
        ctx.setFillColor(rgb(0x1F242A, 0.96))
        ctx.fillPath()
        ctx.restoreGState()
        ctx.saveGState()
        ctx.addPath(shape)
        ctx.clip()
        let sheen = CGGradient(colorsSpace: space, colors: [CGColor(gray: 1, alpha: 0.06), CGColor(gray: 1, alpha: 0)] as CFArray, locations: [0, 1])!
        ctx.drawLinearGradient(sheen, start: CGPoint(x: 0, y: rect.minY), end: CGPoint(x: 0, y: iconY), options: [])
        ctx.setFillColor(plate)
        ctx.fill(CGRect(x: rect.minX, y: plateTop, width: rect.width, height: plateBottom - plateTop + 20))
        ctx.restoreGState()
        ctx.addPath(shape)
        ctx.setStrokeColor(CGColor(gray: 1, alpha: 0.13))
        ctx.setLineWidth(1)
        ctx.strokePath()
        // A yellow hairline where the plate meets the panel.
        ctx.setFillColor(yellow.copy(alpha: 0.7)!)
        ctx.fill(CGRect(x: rect.minX, y: plateTop - 1, width: rect.width, height: 1))
        // Icon artwork fills about ±52 points of the 128-point icon; the brackets end above the plate.
        corners(CGRect(x: x - 62, y: iconY - 62, width: 124, height: 124), arm: 14, color: yellow, line: 2.5, ctx)
        small(caption, x: rect.minX + 12, y: rect.minY + 13, alignRight: false, ctx)
    }

    // Trace from the app's panel to Applications: a node, a line that brightens towards the target,
    // and an arrowhead, all with a soft glow.
    let from = appX + 94, to = appsX - 94
    ctx.saveGState()
    ctx.setShadow(offset: .zero, blur: 10, color: yellow.copy(alpha: 0.8)!)
    ctx.beginTransparencyLayer(auxiliaryInfo: nil)
    ctx.setLineCap(.round)
    ctx.setLineJoin(.round)
    ctx.setLineWidth(3)
    ctx.move(to: CGPoint(x: from + 6, y: iconY))
    ctx.addLine(to: CGPoint(x: to - 3, y: iconY))
    ctx.move(to: CGPoint(x: to - 16, y: iconY - 14))
    ctx.addLine(to: CGPoint(x: to - 2, y: iconY))
    ctx.addLine(to: CGPoint(x: to - 16, y: iconY + 14))
    ctx.replacePathWithStrokedPath()
    ctx.addEllipse(in: CGRect(x: from - 4.5, y: iconY - 4.5, width: 9, height: 9))
    ctx.clip()
    let ramp = CGGradient(colorsSpace: space, colors: [yellow.copy(alpha: 0.35)!, yellow] as CFArray, locations: [0, 0.75])!
    ctx.drawLinearGradient(ramp, start: CGPoint(x: from + 8, y: 0), end: CGPoint(x: to, y: 0), options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
    ctx.endTransparencyLayer()
    ctx.restoreGState()
}

func corners(_ r: CGRect, arm: CGFloat, color: CGColor, line: CGFloat, _ ctx: CGContext) {
    ctx.setStrokeColor(color)
    ctx.setLineWidth(line)
    ctx.setLineCap(.square)
    for (x, y, dx, dy) in [(r.minX, r.minY, 1.0, 1.0), (r.maxX, r.minY, -1.0, 1.0), (r.minX, r.maxY, 1.0, -1.0), (r.maxX, r.maxY, -1.0, -1.0)] {
        ctx.move(to: CGPoint(x: x + dx * arm, y: y))
        ctx.addLine(to: CGPoint(x: x, y: y))
        ctx.addLine(to: CGPoint(x: x, y: y + dy * arm))
    }
    ctx.strokePath()
}

func small(_ string: String, x: CGFloat, y: CGFloat = 30, alignRight: Bool, _ ctx: CGContext) {
    let font = NSFont.monospacedSystemFont(ofSize: 8.5, weight: .medium)
    text(string, font: font, color: rgb(0x8C96A3, 0.75), kern: 1.2, centreY: y, anchorX: x, alignRight: alignRight, ctx)
}

/// Draws one line of text with its bounds centred vertically on centreY, centred horizontally on the
/// window (or starting / ending at anchorX), in the flipped context.
func text(_ string: String, font: NSFont, color: CGColor, kern: CGFloat = 0, highlight: (String, CGColor)? = nil,
          centreY: CGFloat, anchorX: CGFloat? = nil, alignRight: Bool = false, _ ctx: CGContext) {
    let attributed = NSMutableAttributedString(string: string, attributes: [.font: font, .foregroundColor: NSColor(cgColor: color)!, .kern: kern])
    if let (part, colour) = highlight, let range = string.range(of: part) {
        attributed.addAttribute(.foregroundColor, value: NSColor(cgColor: colour)!, range: NSRange(range, in: string))
    }
    let line = CTLineCreateWithAttributedString(attributed)
    let bounds = CTLineGetBoundsWithOptions(line, [])
    let x: CGFloat
    if let anchorX { x = alignRight ? anchorX - bounds.width - bounds.minX : anchorX - bounds.minX } else { x = width / 2 - bounds.width / 2 - bounds.minX }
    ctx.saveGState()
    ctx.translateBy(x: x, y: centreY + bounds.height / 2 + bounds.minY)
    ctx.scaleBy(x: 1, y: -1)
    ctx.textPosition = .zero
    CTLineDraw(line, ctx)
    ctx.restoreGState()
}

func render(scale: Int) -> NSBitmapImageRep {
    // Opaque: no alpha channel to store.
    let ctx = CGContext(data: nil, width: Int(width) * scale, height: Int(height) * scale, bitsPerComponent: 8, bytesPerRow: 0,
                        space: space, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.interpolationQuality = .high
    ctx.scaleBy(x: CGFloat(scale), y: CGFloat(scale))
    draw(ctx)
    let rep = NSBitmapImageRep(cgImage: ctx.makeImage()!)
    rep.size = NSSize(width: width, height: height)   // 72 dpi at 1x, 144 dpi at 2x
    return rep
}

// One LZW-compressed TIFF with both resolutions; Finder picks the one matching the display.
let reps = [render(scale: 1), render(scale: 2)]
try! NSBitmapImageRep.tiffRepresentationOfImageReps(in: reps, using: .lzw, factor: 0)!
    .write(to: out.appendingPathComponent("background.tiff"))
if args.count > 8 {  // preview PNGs for checking the artwork: pass "png" as an eighth argument
    for (rep, name) in zip(reps, ["background.png", "background@2x.png"]) {
        try! rep.representation(using: .png, properties: [:])!.write(to: out.appendingPathComponent(name))
    }
}
print(out.path)
