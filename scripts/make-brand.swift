// South Carolina Eats brand: the app icon (Nick's pick 2026-10-26, concept A of scripts/icon-concepts.swift: a curled Lowcountry shrimp
// on flag-inspired indigo), in the shared Eats Ranked style (../state-prompts/ICON-STYLE.md). Usage, from sc-eats/: swift scripts/make-brand.swift
// -> SouthCarolinaEats/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png, the website's icons (docs/icon-512.png, icon-192.png,
// apple-touch-icon.png, favicon-32.png) and share image (docs/og.png).
import AppKit
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

func rgb(_ hex: UInt32) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: 1)
}
let INDIGO: UInt32 = 0x1B2A57, MARSH: UInt32 = 0x2F5D3A, CREAM: UInt32 = 0xF6F1E7, CORAL: UInt32 = 0xE8836B

// MARK: A, shrimp. A thick C-shaped body (a round-cap stroke along an arc, open to the right), the head at the top end as a larger
// rounded block with two antennae sweeping back over it, a two-lobed tail fan at the bottom end. Lighter back plane on the outer edge, coral
// base, a darker belly band on the inner curve; four shell segments cut through to the ground; one eye. Drawn at 1.0 and scaled about
// the centre so the box is 0.72 wide. CoreGraphics y-up.
func shrimp(_ c: CGContext, _ s: CGFloat) {
    c.saveGState()
    c.translateBy(x: 0.555 * s, y: 0.5 * s); c.scaleBy(x: 1.075, y: 1.075); c.translateBy(x: -0.5 * s, y: -0.5 * s)
    func P(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: x * s, y: y * s) }
    func E(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat) -> CGRect { CGRect(x: (x - w / 2) * s, y: (y - h / 2) * s, width: w * s, height: h * s) }
    let base = rgb(CORAL), back = rgb(0xF2A48F), belly = rgb(0xC9634E), ground = rgb(INDIGO)
    let cx: CGFloat = 0.49, cy: CGFloat = 0.475, r: CGFloat = 0.205, w: CGFloat = 0.175
    c.setLineCap(.round); c.setLineJoin(.round)
    let a0: CGFloat = 55 * .pi / 180, a1: CGFloat = 300 * .pi / 180
    func arc(_ rad: CGFloat, _ width: CGFloat, _ color: CGColor, from: CGFloat = a0, to: CGFloat = a1) {
        let p = CGMutablePath(); p.addArc(center: P(cx, cy), radius: rad * s, startAngle: from, endAngle: to, clockwise: false)
        c.setStrokeColor(color); c.setLineWidth(width * s); c.addPath(p); c.strokePath()
    }
    // antennae first, behind the head: two long round-cap strokes sweeping up and back over the curl (30 px each before scaling)
    let hx = cx + r * cos(a0), hy = cy + r * sin(a0)
    c.setStrokeColor(base); c.setLineWidth(0.030 * s)
    for (ex, ey, kx, ky) in [(0.20, 0.80, 0.42, 0.86), (0.13, 0.70, 0.30, 0.84)] as [(CGFloat, CGFloat, CGFloat, CGFloat)] {
        c.move(to: P(hx + 0.07, hy + 0.06)); c.addQuadCurve(to: P(ex, ey), control: P(kx, ky)); c.strokePath()
    }
    arc(r, w, base)
    arc(r + w * 0.30, w * 0.40, back, from: a0 + 0.20, to: a1 - 0.30)       // the lighter back (outer edge)
    arc(r - w * 0.36, w * 0.28, belly, from: a0 + 0.35, to: a1 - 0.35)      // the darker belly on the inner curve
    // tail fan: two lobes splayed from the tail end, pointing right
    let tx = cx + r * cos(a1), ty = cy + r * sin(a1)
    c.setFillColor(base)
    for dy in [0.05, -0.05] as [CGFloat] {
        let fan = CGMutablePath()
        fan.move(to: P(tx - 0.02, ty)); fan.addQuadCurve(to: P(tx + 0.19, ty + dy * 2.5), control: P(tx + 0.08, ty + dy * 2.7))
        fan.addQuadCurve(to: P(tx - 0.02, ty), control: P(tx + 0.12, ty + dy * 0.2)); fan.closeSubpath()
        c.addPath(fan); c.fillPath()
    }
    // head: a rounded block at the upper end, a little wider than the body, with its own lighter top
    c.setFillColor(base); c.fillEllipse(in: E(hx + 0.035, hy + 0.01, 0.235, 0.20))
    c.setFillColor(back); c.fillEllipse(in: E(hx + 0.03, hy + 0.055, 0.19, 0.09))
    // eye (one dot cut to the ground) and four shell segments: full-width cuts across the body in the ground colour
    c.setFillColor(ground); c.fillEllipse(in: E(hx + 0.08, hy + 0.012, 0.045, 0.045))
    c.setStrokeColor(ground); c.setLineWidth(0.030 * s); c.setLineCap(.butt)
    for deg in [110.0, 152.0, 194.0, 236.0] as [CGFloat] {
        let a = deg * .pi / 180
        c.move(to: P(cx + (r + w * 0.56) * cos(a), cy + (r + w * 0.56) * sin(a)))
        c.addLine(to: P(cx + (r - w * 0.20) * cos(a), cy + (r - w * 0.20) * sin(a)))
        c.strokePath()
    }
    c.restoreGState()
}

func save(_ ctx: CGContext, _ path: String) {
    let d = CGImageDestinationCreateWithURL(URL(fileURLWithPath: path) as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(d, ctx.makeImage()!, nil)
    guard CGImageDestinationFinalize(d) else { fatalError("could not write \(path)") }
    print("wrote", path)
}

func render(_ n: Int, _ path: String) {
    let ctx = CGContext(data: nil, width: n, height: n, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setShouldAntialias(true)
    ctx.setFillColor(rgb(INDIGO)); ctx.fill(CGRect(x: 0, y: 0, width: n, height: n))
    shrimp(ctx, CGFloat(n))
    save(ctx, path)
}
render(1024, "SouthCarolinaEats/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png")
try? FileManager.default.createDirectory(atPath: "docs", withIntermediateDirectories: true)
for (n, name) in [(512, "icon-512.png"), (192, "icon-192.png"), (180, "apple-touch-icon.png"), (32, "favicon-32.png")] {
    render(n, "docs/" + name)
}

/// The share image (1200 x 630): indigo, the shrimp at the left, the name and tagline at the right, and the marsh band along the bottom
/// (a cream creek line and marsh-green grass blades).
func og(_ path: String) {
    let W = 1200, H = 630
    let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setShouldAntialias(true)
    ctx.setFillColor(rgb(INDIGO)); ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
    // the marsh band: a cream creek line, then grass blades standing on the bottom edge
    ctx.setFillColor(rgb(CREAM)); ctx.fill(CGRect(x: 0, y: 40, width: CGFloat(W), height: 6))
    ctx.setFillColor(rgb(MARSH))
    var x: CGFloat = 0, i = 0
    while x < CGFloat(W) {
        let h = CGFloat(22 + (i * 7) % 4 * 6)
        ctx.move(to: CGPoint(x: x, y: 0)); ctx.addLine(to: CGPoint(x: x + 5, y: h)); ctx.addLine(to: CGPoint(x: x + 10, y: 0)); ctx.fillPath()
        x += 14; i += 1
    }
    ctx.saveGState(); ctx.translateBy(x: 0, y: 60); shrimp(ctx, 540); ctx.restoreGState()
    let ns = NSGraphicsContext(cgContext: ctx, flipped: false)
    NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = ns
    let title = NSFont(name: "AvenirNextCondensed-Heavy", size: 104) ?? NSFont.boldSystemFont(ofSize: 96)
    let sub = NSFont(name: "AvenirNextCondensed-DemiBold", size: 44) ?? NSFont.boldSystemFont(ofSize: 40)
    NSAttributedString(string: "SOUTH CAROLINA", attributes: [.font: title, .foregroundColor: NSColor.white]).draw(at: NSPoint(x: 560, y: 390))
    NSAttributedString(string: "EATS", attributes: [.font: title, .foregroundColor: NSColor.white]).draw(at: NSPoint(x: 560, y: 285))
    NSAttributedString(string: "BBQ, SHRIMP & GRITS, OYSTERS", attributes: [.font: sub, .foregroundColor: NSColor(srgbRed: 0.91, green: 0.51, blue: 0.42, alpha: 1)]).draw(at: NSPoint(x: 564, y: 225))
    NSGraphicsContext.restoreGraphicsState()
    save(ctx, path)
}
og("docs/og.png")
