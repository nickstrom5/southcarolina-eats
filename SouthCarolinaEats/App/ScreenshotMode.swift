import Foundation
import CoreLocation
import UIKit

/// `-screenshot <name>` opens one screen with fixed state for App Store screenshots (scripts/capture-screenshots.sh).
/// Names: home, bbq, seafood, gullah, meat3, honors, oldest, detail, map, saved, about (a guide's screen needs its research to have landed).
enum ScreenshotMode {
    /// Debug builds only: an App Store build ignores the launch argument, so no one can reach seeded screens or fake locations.
    static var name: String? {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        guard let i = args.firstIndex(of: "-screenshot"), i + 1 < args.count else { return nil }
        return args[i + 1]
        #else
        return nil
        #endif
    }
    static var isActive: Bool { name != nil }

    @MainActor
    static func apply(to model: AppModel) {
        guard let name, model.isLoaded else { return }
        model.filters = Filters()
        // downtown Charleston (Marion Square), so "nearest" lists have distances without a permission prompt
        model.screenshotLocation = CLLocation(latitude: 32.7876, longitude: -79.9366)
        // by name and town, ignoring case, so a rebuild with a slightly different casing still finds the place; the hand-checked one first.
        // App Store rule: no screenshot shows a place whose latest SCDA grade is B or C (a unit test checks these picks)
        let pick = { (n: String, town: String?) -> Place? in
            let hits = model.places.filter { $0.name.caseInsensitiveCompare(n) == .orderedSame && (town == nil || $0.city == town) }
            return hits.first(where: \.handChecked) ?? hits.first
        }
        for p in Self.savedPicks.compactMap({ pick($0.0, $0.1) }) where !model.isSaved(p) {
            model.toggleSaved(p)
        }
        let open = { (g: Guide) in model.tab = .guides; model.selectedGuide = g; model.guidesPath = [.guide(g)] }
        switch name {
        case "bbq": open(.bbq)
        case "seafood": open(.seafood)
        case "gullah": open(.gullah)
        case "meat3": open(.meat3)
        case "honors": open(.honors)
        case "oldest": open(.oldest)
        case "detail":
            open(.honors)
            if let p = pick(Self.detailPick.0, Self.detailPick.1) ?? model.places.first { model.selectedPlace = p; model.guidesPath.append(.place(p)) }
        case "map": model.tab = .map
        case "saved": model.tab = .saved
        case "about": model.tab = .about
        default: model.tab = .guides; model.selectedGuide = nil
        }
        // iPad shows the place column next to every list, so give each shot a place instead of "Pick a place": an honored one whose
        // whole SCDA history is grade A (that column shows every record; a unit test checks).
        guard UIDevice.current.userInterfaceIdiom == .pad, model.selectedPlace == nil else { return }
        let place: Place? = switch name {
        case "about": nil
        case "saved", "oldest", "honors": pick(Self.padPick.0, Self.padPick.1)
        default: pick(Self.detailPick.0, Self.detailPick.1)
        }
        model.selectedPlace = place
    }

    /// the places the screenshots open and save (name, town)
    static let detailPick = ("Bowens Island Restaurant", "Charleston")
    // Lewis Barbecue: MICHELIN-listed with five SCDA inspections, all grade A (Wade's permit doesn't match its listing, so its column
    // showed "SCDA permit (none matched)")
    static let padPick = ("Lewis Barbecue", "Charleston")
    static let savedPicks = [("Bowens Island Restaurant", "Charleston"), ("Wade's Restaurant", "Spartanburg"), ("Bertha's Kitchen", "North Charleston")]
    /// every place a screenshot opens or saves, for the unit test that keeps B and C grades out of App Store images
    static var allPicks: [(String, String)] { [detailPick, padPick] + savedPicks }
}
