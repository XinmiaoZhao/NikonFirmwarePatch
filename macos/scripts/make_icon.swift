// Draws the app icon into an .iconset folder: `swift make_icon.swift <out.iconset>`.
// Original artwork (no SF Symbols): a graphite squircle, a firmware chip outlined in the
// camera-menu yellow used by the guide animations, and 3:2 frame brackets.
import AppKit

let out = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
try? FileManager.default.removeItem(at: out)
try! FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)

let yellow = CGColor(red: 0xFB / 255, green: 0xD6 / 255, blue: 0x24 / 255, alpha: 1)

func draw(_ ctx: CGContext) {
    // macOS icon grid: 824 pt body centred on a 1024 canvas.
    let body = CGRect(x: 100, y: 100, width: 824, height: 824)
    let squircle = CGPath(roundedRect: body, cornerWidth: 186, cornerHeight: 186, transform: nil)
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -10), blur: 28, color: CGColor(gray: 0, alpha: 0.35))
    ctx.addPath(squircle)
    ctx.setFillColor(CGColor(gray: 0.12, alpha: 1))
    ctx.fillPath()
    ctx.restoreGState()

    ctx.saveGState()
    ctx.addPath(squircle)
    ctx.clip()
    let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(),
                              colors: [CGColor(red: 0.22, green: 0.235, blue: 0.27, alpha: 1),
                                       CGColor(red: 0.075, green: 0.08, blue: 0.095, alpha: 1)] as CFArray,
                              locations: [0, 1])!
    ctx.drawLinearGradient(gradient, start: CGPoint(x: 512, y: 924), end: CGPoint(x: 512, y: 100), options: [])
    // Soft top highlight.
    ctx.setFillColor(CGColor(gray: 1, alpha: 0.05))
    ctx.fillEllipse(in: CGRect(x: 60, y: 560, width: 904, height: 520))
    ctx.restoreGState()

    // 3:2 frame brackets.
    let frame = CGRect(x: 512 - 315, y: 512 - 210, width: 630, height: 420)
    ctx.setStrokeColor(CGColor(gray: 1, alpha: 0.55))
    ctx.setLineWidth(16)
    ctx.setLineCap(.round)
    let arm: CGFloat = 70
    for (x, y, dx, dy) in [(frame.minX, frame.minY, 1.0, 1.0), (frame.maxX, frame.minY, -1.0, 1.0),
                           (frame.minX, frame.maxY, 1.0, -1.0), (frame.maxX, frame.maxY, -1.0, -1.0)] {
        ctx.move(to: CGPoint(x: x + dx * arm, y: y))
        ctx.addLine(to: CGPoint(x: x, y: y))
        ctx.addLine(to: CGPoint(x: x, y: y + dy * arm))
    }
    ctx.strokePath()

    // Chip with pins.
    let chip = CGRect(x: 512 - 150, y: 512 - 150, width: 300, height: 300)
    ctx.setFillColor(yellow.copy(alpha: 0.85)!)
    let pin: CGFloat = 26, gap: CGFloat = 54
    for i in 0..<5 {
        let o = chip.minX + 42 + CGFloat(i) * gap
        ctx.fill(CGRect(x: o, y: chip.maxY + 6, width: pin, height: 44))
        ctx.fill(CGRect(x: o, y: chip.minY - 50, width: pin, height: 44))
        let p = chip.minY + 42 + CGFloat(i) * gap
        ctx.fill(CGRect(x: chip.minX - 50, y: p, width: 44, height: pin))
        ctx.fill(CGRect(x: chip.maxX + 6, y: p, width: 44, height: pin))
    }
    let chipPath = CGPath(roundedRect: chip, cornerWidth: 44, cornerHeight: 44, transform: nil)
    ctx.addPath(chipPath)
    ctx.setFillColor(CGColor(red: 0.10, green: 0.105, blue: 0.12, alpha: 1))
    ctx.fillPath()
    ctx.addPath(chipPath)
    ctx.setStrokeColor(yellow)
    ctx.setLineWidth(18)
    ctx.strokePath()

    // "Z8" label.
    let font = NSFont.systemFont(ofSize: 150, weight: .heavy)
    let text = NSAttributedString(string: "Z8", attributes: [.font: font, .foregroundColor: NSColor(cgColor: yellow)!, .kern: -4])
    let line = CTLineCreateWithAttributedString(text)
    let bounds = CTLineGetImageBounds(line, ctx)
    ctx.textPosition = CGPoint(x: 512 - bounds.width / 2 - bounds.minX, y: 512 - bounds.height / 2 - bounds.minY)
    CTLineDraw(line, ctx)
}

func render(_ px: Int) -> Data {
    let space = CGColorSpace(name: CGColorSpace.sRGB)!
    let ctx = CGContext(data: nil, width: px, height: px, bitsPerComponent: 8, bytesPerRow: 0, space: space,
                        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.interpolationQuality = .high
    ctx.scaleBy(x: CGFloat(px) / 1024, y: CGFloat(px) / 1024)
    draw(ctx)
    let rep = NSBitmapImageRep(cgImage: ctx.makeImage()!)
    return rep.representation(using: .png, properties: [:])!
}

for base in [16, 32, 128, 256, 512] {
    try! render(base).write(to: out.appendingPathComponent("icon_\(base)x\(base).png"))
    try! render(base * 2).write(to: out.appendingPathComponent("icon_\(base)x\(base)@2x.png"))
}
print(out.path)
