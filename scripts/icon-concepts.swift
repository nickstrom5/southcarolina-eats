// South Carolina Eats icon concepts for Nick's pick, in the shared Eats Ranked icon style (state-prompts/ICON-STYLE.md v1):
// one flat, level, centred food on a plain background; no scenery, tilt, texture, gloss or gradients.
// Usage (from sc-eats/): swift scripts/icon-concepts.swift   -> playbook/brand/concept-{a,b,c}-1024.png and -512, -180, -60 copies
//   A  a curled Lowcountry shrimp, cooked coral, in side view, on flag-inspired indigo
//   B  an oyster on the half shell, in plan view (recognised from above), on marsh green
//   C  a boiled peanut in the shell (by law the official state snack food), in side view, on flag-inspired indigo
// Palette (the state prompt's proposal; Nick's call): flag-inspired indigo #1B2A57, marsh green #2F5D3A, oyster cream #F6F1E7, shrimp
// coral #E8836B. Food-only tones are listed per concept.
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

// MARK: B, oyster on the half shell (plan view). A broad shell, hinge to the left, in shell grey with a darker rim band; the pearly
// inside in oyster cream; the oyster itself in a grey-tan with a darker mantle edge.
func oyster(_ c: CGContext, _ s: CGFloat) {
    func P(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: x * s, y: y * s) }
    let shell = rgb(0x9E978A), rim = rgb(0x7A7468), inside = rgb(CREAM), meat = rgb(0xC9BC9C), mantle = rgb(0xA89A78)
    // a teardrop: the hinge point at the left, the broad round lip at the right
    func tear(_ x0: CGFloat, _ x1: CGFloat, _ yc: CGFloat, _ h: CGFloat) -> CGPath {
        let p = CGMutablePath()
        p.move(to: P(x0, yc))
        p.addCurve(to: P(x1 - h * 0.45, yc + h / 2), control1: P(x0 + (x1 - x0) * 0.20, yc + h * 0.40), control2: P(x1 - h * 0.95, yc + h / 2))
        p.addCurve(to: P(x1 - h * 0.45, yc - h / 2), control1: P(x1 + h * 0.15, yc + h / 2), control2: P(x1 + h * 0.15, yc - h / 2))
        p.addCurve(to: P(x0, yc), control1: P(x1 - h * 0.95, yc - h / 2), control2: P(x0 + (x1 - x0) * 0.20, yc - h * 0.40))
        p.closeSubpath()
        return p
    }
    let yc: CGFloat = 0.48
    c.setFillColor(rim); c.addPath(tear(0.14, 0.86, yc - 0.012, 0.50)); c.fillPath()        // the darker underside rim, offset down
    c.setFillColor(shell); c.addPath(tear(0.14, 0.86, yc, 0.50)); c.fillPath()
    c.setFillColor(inside); c.addPath(tear(0.22, 0.81, yc + 0.005, 0.39)); c.fillPath()
    c.setFillColor(mantle); c.addPath(tear(0.31, 0.76, yc + 0.0, 0.29)); c.fillPath()
    c.setFillColor(meat); c.addPath(tear(0.34, 0.74, yc + 0.012, 0.23)); c.fillPath()
}

// MARK: C, boiled peanut in the shell (side view): two lobes with a waist, the shell's lighter top plane and darker underside, and
// six dimples (the shell's net) in the underside tone.
func peanut(_ c: CGContext, _ s: CGFloat) {
    func P(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: x * s, y: y * s) }
    func E(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat) -> CGRect { CGRect(x: (x - w / 2) * s, y: (y - h / 2) * s, width: w * s, height: h * s) }
    let shell = rgb(0xC69A5E), top = rgb(0xDDB97E), under = rgb(0x9F7340)
    // outline: left lobe, waist, right lobe (a smooth closed path of four curves)
    let y: CGFloat = 0.475
    let body = CGMutablePath()
    body.move(to: P(0.50, y + 0.115))                                                                // waist, top
    body.addCurve(to: P(0.14, y + 0.0), control1: P(0.40, y + 0.215), control2: P(0.14, y + 0.215))
    body.addCurve(to: P(0.50, y - 0.11), control1: P(0.14, y - 0.215), control2: P(0.40, y - 0.215))
    body.addCurve(to: P(0.86, y - 0.0), control1: P(0.60, y - 0.225), control2: P(0.86, y - 0.225))
    body.addCurve(to: P(0.50, y + 0.115), control1: P(0.86, y + 0.225), control2: P(0.60, y + 0.225))
    body.closeSubpath()
    c.saveGState(); c.addPath(body); c.clip()
    c.setFillColor(shell); c.fill(CGRect(x: 0, y: 0, width: s, height: s))
    c.setFillColor(top); c.fill(CGRect(x: 0, y: (y + 0.085) * s, width: s, height: s))                 // the lighter top plane
    c.setFillColor(under); c.fill(CGRect(x: 0, y: 0, width: s, height: (y - 0.12) * s))                // the darker underside
    c.restoreGState()
    // dimples: 6 soft ovals in the underside tone, three on each lobe
    c.setFillColor(under)
    for (x, yy) in [(0.25, 0.47), (0.34, 0.54), (0.33, 0.41), (0.66, 0.53), (0.75, 0.46), (0.66, 0.40)] as [(CGFloat, CGFloat)] {
        c.fillEllipse(in: E(x, yy, 0.06, 0.042))
    }
}

// MARK: - main
let root = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent().deletingLastPathComponent().path
let out = root + "/playbook/brand"
try? FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)
func canvas(_ n: Int) -> CGContext {
    let c = CGContext(data: nil, width: n, height: n, bitsPerComponent: 8, bytesPerRow: 0,
                      space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    c.setAllowsAntialiasing(true); c.setShouldAntialias(true); c.interpolationQuality = .high
    return c
}
func save(_ img: CGImage, _ name: String) {
    let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: out + "/" + name) as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, img, nil)
    guard CGImageDestinationFinalize(dest) else { fatalError("could not write \(name)") }
}
for (key, bg, draw) in [("a", INDIGO, shrimp), ("b", MARSH, oyster), ("c", INDIGO, peanut)] as [(String, UInt32, (CGContext, CGFloat) -> Void)] {
    let c = canvas(1024)
    c.setFillColor(rgb(bg)); c.fill(CGRect(x: 0, y: 0, width: 1024, height: 1024))
    draw(c, 1024)
    let full = c.makeImage()!
    save(full, "concept-\(key)-1024.png")
    for n in [512, 180, 60] {
        let sm = canvas(n); sm.draw(full, in: CGRect(x: 0, y: 0, width: n, height: n)); save(sm.makeImage()!, "concept-\(key)-\(n).png")
    }
    print("wrote concept-\(key)")
}
