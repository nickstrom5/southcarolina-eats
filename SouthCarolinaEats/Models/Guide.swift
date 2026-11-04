import Foundation
import CoreLocation

/// The lists the app is built around. Each is a filter plus an order; none uses ratings (the app only publishes data it may).
enum Guide: String, CaseIterable, Identifiable, Hashable {
    case bbq, seafood, gullah, meat3, honors, oldest, inspections, nearMe, all

    var id: String { rawValue }

    var title: String {
        switch self {
        case .bbq: "Whole-Hog & Mustard Barbecue"
        case .seafood: "Lowcountry & Grand Strand Seafood"
        case .gullah: "Gullah Geechee Cooking"
        case .meat3: "Meat-and-Threes & Drive-Ins"
        case .honors: "MICHELIN & James Beard"
        case .oldest: "Oldest Places"
        case .inspections: "SCDA Inspection Grades"
        case .nearMe: "Near Me"
        case .all: "All Restaurants"
        }
    }

    /// The list's large navigation title, which can't wrap: about 27 characters fit an iPhone 17 Pro Max and about 19 the iPad's list
    /// column, so the longer titles get a short form there (Home's cards, the iPad sidebar and the website keep the full title).
    func navTitle(iPadColumn: Bool) -> String {
        switch self {
        case .bbq: iPadColumn ? "Whole-Hog Barbecue" : "Whole-Hog & Mustard BBQ"
        case .seafood: "Lowcountry Seafood"
        case .gullah: iPadColumn ? "Gullah Geechee" : title
        case .meat3: iPadColumn ? "Meat-and-Threes" : title
        case .honors: iPadColumn ? "Honors" : title
        case .inspections: iPadColumn ? "SCDA Grades" : title
        default: title
        }
    }

    var subtitle: String {
        switch self {
        case .bbq: "Hand-checked whole-hog barbecue, mustard sauce, hash and rice"
        case .seafood: "Hand-checked shrimp and grits, she-crab soup and oyster roasts"
        case .gullah: "Hand-checked Gullah Geechee kitchens of the Lowcountry and Sea Islands"
        case .meat3: "Hand-checked steam-table plates, diners and drive-ins"
        case .honors: "The MICHELIN Guide American South and James Beard honors"
        case .oldest: "Founding years checked at the same address, oldest first"
        case .inspections: "The SC Department of Agriculture's posted grades"
        case .nearMe: "Everything around you, closest first"
        case .all: "Restaurants, cafés, bars and bakeries statewide"
        }
    }

    var systemImage: String {
        switch self {
        case .bbq: "flame"
        case .seafood: "fish"
        case .gullah: "leaf"
        case .meat3: "fork.knife.circle"
        case .honors: "star.circle"
        case .oldest: "clock.arrow.circlepath"
        case .inspections: "checkmark.seal"
        case .nearMe: "location"
        case .all: "fork.knife"
        }
    }

    /// The hand-checked South Carolina guides get the accent card on Home.
    var isStateGuide: Bool { tag != nil }

    /// Guides whose order is a ranking worth numbering.
    var isRanked: Bool { [.oldest].contains(self) }

    var sortOptions: [SortOrder] {
        switch self {
        case .bbq, .seafood, .gullah, .meat3: [.featured, .nearest, .name]
        case .honors: [.iconic, .nearest]
        case .oldest: [.oldest]
        case .inspections: [.recent, .highestScore, .lowestScore, .nearest]
        case .nearMe: [.nearest]
        case .all: [.name, .nearest]
        }
    }

    var defaultSort: SortOrder { sortOptions[0] }

    /// The tag behind a hand-checked guide.
    var tag: PlaceTags? {
        switch self {
        case .bbq: .bbq
        case .seafood: .seafood
        case .gullah: .gullah
        case .meat3: .meat3
        default: nil
        }
    }

    func includes(_ p: Place) -> Bool {
        if let tag {   // the guides that promise "hand-checked" list only places checked open with a 2025–26 source
            return p.handChecked && p.tags.contains(tag)
        }
        switch self {
        case .honors: return p.hasHonors
        case .oldest: return p.founded != nil && p.tags.contains(.oldest)
        case .inspections: return p.inspection != nil
        default: return true
        }
    }
}

enum SortOrder: String, CaseIterable, Identifiable {
    case featured, nearest, oldest, name, iconic, recent, highestScore, lowestScore
    var id: String { rawValue }
    var label: String {
        switch self {
        case .featured: "Featured first"
        case .nearest: "Nearest"
        case .oldest: "Oldest first"
        case .name: "A to Z"
        case .iconic: "MICHELIN, then James Beard"
        case .recent: "Latest inspection first"
        case .highestScore: "Grade A first"
        case .lowestScore: "Grade C and B first"
        }
    }
}

/// Filters shared by every list. Search text lives with each list.
struct Filters: Equatable, Codable {
    var town: String?
    var cuisine: String?
    var hideChains = false
    var confirmedOnly = false
    var includeNonRestaurants = false
    /// MICHELIN Bib Gourmand places only (BIB-GOURMAND-FILTER.md): a fact from the Guide, not a rating
    var bibGourmand = false

    var activeCount: Int {
        [town != nil, cuisine != nil, hideChains, confirmedOnly, includeNonRestaurants, bibGourmand].filter { $0 }.count
    }

    func allows(_ p: Place) -> Bool {
        if !includeNonRestaurants && p.isVenue { return false }
        if let town, p.city != town { return false }
        if let cuisine, p.cuisine != cuisine { return false }
        if hideChains && p.isChain { return false }
        if confirmedOnly && p.tier == .listing { return false }
        if bibGourmand && p.michelin != .bib { return false }
        return true
    }
}

extension Filters {
    /// Filters saved by an older build may lack a key: read what's there instead of dropping them all.
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.init(town: try c.decodeIfPresent(String.self, forKey: .town),
                  cuisine: try c.decodeIfPresent(String.self, forKey: .cuisine),
                  hideChains: try c.decodeIfPresent(Bool.self, forKey: .hideChains) ?? false,
                  confirmedOnly: try c.decodeIfPresent(Bool.self, forKey: .confirmedOnly) ?? false,
                  includeNonRestaurants: try c.decodeIfPresent(Bool.self, forKey: .includeNonRestaurants) ?? false,
                  bibGourmand: try c.decodeIfPresent(Bool.self, forKey: .bibGourmand) ?? false)
    }
}

enum Ranking {
    /// the posted-grade indexes that read as below A ("B", "C"); set at load
    nonisolated(unsafe) static var lowBands: Set<Int> = [1, 2]

    static func sort(_ places: [Place], by order: SortOrder, from here: CLLocation?) -> [Place] {
        // Keys come from fields made once at load: a localized compare, or a new CLLocation per comparison, made a 16,000-place
        // sort take most of a second (AR-13). sortKey is the normalized name, so case, accents and punctuation don't change the order.
        func name(_ a: Place, _ b: Place) -> Bool { a.sortKey != b.sortKey ? a.sortKey < b.sortKey : a.id < b.id }
        switch order {
        case .nearest where here != nil:
            // each distance once, not four times per comparison
            let from = here!
            return places.map { p in (p, p.location.map { $0.distance(from: from) } ?? .greatestFiniteMagnitude) }
                .sorted { $0.1 != $1.1 ? $0.1 < $1.1 : name($0.0, $1.0) }
                .map(\.0)
        case .featured, .nearest:
            // honored places first, then verified founding year, then name
            return places.sorted {
                let a = $0.iconicPoints ?? -1, b = $1.iconicPoints ?? -1
                if a != b { return a > b }
                let fa = $0.founded ?? 9999, fb = $1.founded ?? 9999
                return fa != fb ? fa < fb : name($0, $1)
            }
        case .oldest:
            return places.sorted { ($0.founded ?? 9999) != ($1.founded ?? 9999) ? ($0.founded ?? 9999) < ($1.founded ?? 9999) : name($0, $1) }
        case .name:
            return places.sorted(by: name)
        case .iconic:
            // an order anyone can check: the MICHELIN distinction (stars, Bib Gourmand, Recommended), then the James Beard honor
            // (America's Classic, winner, finalist, semifinalist), then name
            func jb(_ p: Place) -> Int { p.honorFlags & 1 != 0 ? 4 : p.honorFlags & 2 != 0 ? 3 : p.honorFlags & 4 != 0 ? 2 : p.honorFlags & 8 != 0 ? 1 : 0 }
            return places.sorted {
                if $0.michelin.rawValue != $1.michelin.rawValue { return $0.michelin.rawValue > $1.michelin.rawValue }
                if jb($0) != jb($1) { return jb($0) > jb($1) }
                return name($0, $1)
            }
        case .recent:
            return places.sorted {
                let a = $0.inspection?.d ?? "", b = $1.inspection?.d ?? ""
                return a != b ? a > b : name($0, $1)
            }
        case .highestScore, .lowestScore:
            // SCDA's posted grade as published (A, B, C), then the latest inspection first; places without a record go last either way
            let best = order == .highestScore
            return places.sorted {
                let a = $0.inspection?.band, b = $1.inspection?.band
                if (a == nil) != (b == nil) { return a != nil }
                let x = a ?? 0, y = b ?? 0
                if x != y { return best ? x < y : x > y }
                let da = $0.inspection?.d ?? "", db = $1.inspection?.d ?? ""
                return da != db ? da > db : name($0, $1)
            }
        }
    }
}
