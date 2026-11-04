import SwiftUI
import UIKit
import CoreText

/// Flag & marsh palette (Nick's pick, 2026-10-26), light only: flag-inspired indigo #1B2A57 (13.9:1 on white; the state color is
/// indigo blue by law with no legal hex) for titles, tint and accents; marsh green #2F5D3A (7.3:1 on white) for links and the
/// hand-checked pins; oyster cream #F6F1E7 surfaces; shrimp coral #E8836B only ever as a fill under indigo text (5.2:1), never as text
/// on white and never under white text (2.7:1). No Clemson orange/purple or Gamecock garnet/black. The names `green`/`gold`/`red` are
/// kept from Wisconsin Eats so the shared views read the same: here `green` is indigo, `gold` coral and `red` marsh green.
enum Theme {
    static let green = Color(hex: 0x1B2A57)      // flag indigo: titles, tint, primary text accents, cards under white text
    static let green2 = Color(hex: 0x2F5D3A)     // marsh green: links
    static let gold = Color(hex: 0xE8836B)       // shrimp coral: fills under indigo text (guide cards, top ranks)
    static let goldSoft = Color(hex: 0xFBE3DA)
    static let lime = Color(hex: 0x2F5D3A)       // marsh green: the grass blades in the marsh band, fills only
    static let limeSoft = Color(hex: 0xF6F1E7)
    static let sand = Color(hex: 0xF6F1E7)       // oyster cream
    static let red = Color(hex: 0x2F5D3A)        // marsh green: hand-checked pins, chips under white text, swipe actions
    static let ink = Color(hex: 0x141D3B)
    static let ink2 = Color(hex: 0x1B2A57)
    static let muted = Color(hex: 0x4F5874)
    static let surface = Color.white
    static let surface2 = Color(hex: 0xF6F1E7)
    static let surface3 = Color(hex: 0xECE3D2)
    static let rule = Color(hex: 0xE4DDCF)
    static let rule2 = Color(hex: 0xC5BBA6)
}

extension Color {
    init(hex: UInt32) {
        self.init(red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255, blue: Double(hex & 0xFF) / 255)
    }
}

/// A small uppercase label: "STONE CRAB", "1 MICHELIN STAR".
struct Chip: View {
    enum Style { case gold, green, red, plain, dashed }
    let text: String
    var style: Style = .plain

    var body: some View {
        Text(text.uppercased())
            .font(.caption2.weight(.bold))
            .tracking(0.4)
            .padding(.horizontal, 7).padding(.vertical, 3)
            .foregroundStyle(style == .green || style == .red ? Color.white : style == .dashed ? Theme.muted : style == .gold ? Theme.ink : Theme.green)
            .background {
                RoundedRectangle(cornerRadius: 5).fill(style == .gold ? Theme.goldSoft : style == .green ? Theme.green : style == .red ? Theme.red
                                                       : style == .dashed ? .clear : Theme.surface2)
            }
            .overlay {
                if style == .dashed { RoundedRectangle(cornerRadius: 5).strokeBorder(Theme.rule2, style: StrokeStyle(lineWidth: 1, dash: [3, 2])) }
            }
            .accessibilityLabel(text)
    }
}

/// SCDA's posted grade, as published: "SCDA · Grade A". The service publishes no score, and the app computes none.
struct BandBadge: View {
    let city: InspectionSource
    let band: InspectionBand
    var score: Int? = nil
    var large = false

    var body: some View {
        Text("\(city.name) · \(band.title)".uppercased())
            .font(large ? .footnote.weight(.heavy) : .caption2.weight(.heavy))
            .tracking(0.4)
            .multilineTextAlignment(.leading)
            .padding(.horizontal, large ? 10 : 7).padding(.vertical, large ? 6 : 3)
            .foregroundStyle(band.ink)
            .background(RoundedRectangle(cornerRadius: 6).fill(band.fill))
            .accessibilityLabel("\(city.agency) posted grade: \(band.label.isEmpty ? "none" : band.label)")
    }
}

/// South Carolina Eats' lettering: the system face drawn compressed and heavy for titles and guide names (like a seafood shack's sign), and the
/// system monospaced face for numbers, dates and small labels. No bundled fonts.
struct DisplayFont: ViewModifier {
    let size: CGFloat
    var weight: Font.Weight = .black
    @ScaledMetric(relativeTo: .body) private var scale: CGFloat = 1

    func body(content: Content) -> some View {
        content.font(.system(size: size * min(scale, 1.6), weight: weight).width(.compressed))
    }
}

/// Numbers, dates and small labels in the system monospaced face, scaled like DisplayFont.
struct MonoFont: ViewModifier {
    let size: CGFloat
    var weight: Font.Weight = .semibold
    @ScaledMetric(relativeTo: .body) private var scale: CGFloat = 1

    func body(content: Content) -> some View {
        content.font(.system(size: size * min(scale, 1.6), weight: weight, design: .monospaced))
    }
}

extension View {
    func displayFont(_ size: CGFloat, weight: Font.Weight = .black) -> some View {
        modifier(DisplayFont(size: size, weight: weight))
    }

    func monoFont(_ size: CGFloat, weight: Font.Weight = .semibold) -> some View {
        modifier(MonoFont(size: size, weight: weight))
    }
}

/// A marsh-grass and tidal-creek band under the Home title (Nick's pick, 2026-10-26): indigo water, a cream creek line and
/// marsh-green grass blades along the bank. No palmetto, seal or team mark.
struct Stripes: View {
    var height: CGFloat = 6

    var body: some View {
        ZStack {
            Rectangle().fill(Theme.green)
            Creek().fill(Theme.sand)
            Grass().fill(Theme.lime)
        }
        .frame(height: height * 3.5)
        .clipped()
        .accessibilityHidden(true)
    }

    /// the creek: a thin cream band that rises and falls along the middle
    private struct Creek: Shape {
        func path(in r: CGRect) -> Path {
            var p = Path()
            let y = r.midY - r.height * 0.12, t = max(1.5, r.height * 0.12), w = r.width
            p.move(to: CGPoint(x: 0, y: y))
            p.addCurve(to: CGPoint(x: w / 2, y: y), control1: CGPoint(x: w * 0.15, y: y - t), control2: CGPoint(x: w * 0.35, y: y + t))
            p.addCurve(to: CGPoint(x: w, y: y), control1: CGPoint(x: w * 0.65, y: y - t), control2: CGPoint(x: w * 0.85, y: y + t))
            p.addLine(to: CGPoint(x: w, y: y + t))
            p.addCurve(to: CGPoint(x: w / 2, y: y + t), control1: CGPoint(x: w * 0.85, y: y + 2 * t), control2: CGPoint(x: w * 0.65, y: y))
            p.addCurve(to: CGPoint(x: 0, y: y + t), control1: CGPoint(x: w * 0.35, y: y + 2 * t), control2: CGPoint(x: w * 0.15, y: y))
            p.closeSubpath()
            return p
        }
    }

    /// marsh grass: narrow blades of a few heights standing on the bottom edge
    private struct Grass: Shape {
        func path(in r: CGRect) -> Path {
            var p = Path()
            let step = max(4, r.height * 0.42)
            var x = r.minX, i = 0
            while x < r.maxX {
                let h = r.height * (0.38 + 0.08 * Double((i * 7) % 4))
                p.move(to: CGPoint(x: x, y: r.maxY))
                p.addLine(to: CGPoint(x: x + step * 0.3, y: r.maxY - h))
                p.addLine(to: CGPoint(x: x + step * 0.55, y: r.maxY))
                p.closeSubpath()
                x += step; i += 1
            }
            return p
        }
    }
}

extension View {
    /// An inline navigation title in the display type. UINavigationBar.appearance() didn't reach every SwiftUI bar on iOS 27
    /// (the Map title went from compressed blue to plain black after a push and pop; place titles were always plain), so the
    /// title is our own view in the bar. The navigation title is still set, for the back button and VoiceOver.
    func inlineTitle(_ title: String) -> some View {
        navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text(title).displayFont(19, weight: .heavy).foregroundStyle(Theme.green)
                        .lineLimit(1).minimumScaleFactor(0.7)
                        .accessibilityAddTraits(.isHeader)
                }
            }
    }
}
