import Foundation
import CoreLocation
import SwiftUI

// MARK: - The bundled data (Resources/places.json + Resources/detail-<region>.json), written by pipeline/southcarolina.py with SC_APP=1
// places.json is the statewide core every screen needs at launch (about 18,000 places); a region's detail file (SCDA inspection
// history, permits, phone, website) is read only when one of its places opens.

/// The core file's header (everything but the places). Read with JSONSerialization, not Codable: tens of thousands of keyed records
/// through JSONDecoder made launch slow (Florida's lesson).
struct DataFile {
    let generated: String
    /// the Overture Maps release the listings come from ("2026-10-21.0")
    let overture_release: String?
    /// open SCDA Retail Food Establishment permits (inspected since `scda_open_since`)
    let scda_open_food_permits: Int?
    let scda_open_since: String?
    /// the last day of SCDA inspection records shown ("scda")
    let inspections_through: [String: String]
    /// the day the SC Food Grades service was read ("scda")
    let inspections_published: [String: String]
    let cities: [String]
    let cuisines: [String]
    let brands: [String]
    let counties: [String]
    /// the regions the detail files are split by ("Charleston & Lowcountry", ...); a place's `rg` indexes this
    let regions: [String]
    let srcs: [String]
    /// SCDA's posted grades: "A", "B", "C"
    let results: [String]
    /// inspection types, our plain labels for the service's ("Routine", "Follow-up", "Permit (new)", ...)
    let itypes: [String]
    let count_restaurants: Int
    let calibration: Calibration

    struct Malformed: LocalizedError { let field: String; var errorDescription: String? { "the data file is missing \(field)" } }

    init(json r: [String: Any]) throws {
        func str(_ k: String) throws -> String { guard let v = r[k] as? String else { throw Malformed(field: k) }; return v }
        func list(_ k: String) throws -> [String] { guard let v = r[k] as? [String] else { throw Malformed(field: k) }; return v }
        generated = try str("generated")
        overture_release = r["overture_release"] as? String
        scda_open_food_permits = r["scda_open_food_permits"] as? Int
        scda_open_since = r["scda_open_since"] as? String
        inspections_through = (r["inspections_through"] as? [String: String]) ?? [:]
        inspections_published = (r["inspections_published"] as? [String: String]) ?? [:]
        cities = try list("cities"); cuisines = try list("cuisines"); brands = try list("brands"); counties = try list("counties")
        regions = (r["regions"] as? [String]) ?? []
        srcs = try list("srcs"); results = try list("results"); itypes = (r["itypes"] as? [String]) ?? []
        guard let n = r["count_restaurants"] as? Int else { throw Malformed(field: "count_restaurants") }
        count_restaurants = n
        let cal = (r["calibration"] as? [String: Any]).flatMap { try? JSONSerialization.data(withJSONObject: $0) }
        calibration = cal.flatMap { try? JSONDecoder().decode(Calibration.self, from: $0) } ?? Calibration(areas: [:])
    }
}

/// How often listings of one kind matched an open SCDA retail-food permit (pipeline/calibrate.py):
/// {"South Carolina (statewide)": {"groups": {"meta_high": {"n": 9854, "official": 0.784}, ...}}, "Charleston County": {...}}
struct Calibration: Decodable, Hashable {
    let areas: [String: CalibrationScope]

    init(areas: [String: CalibrationScope]) { self.areas = areas }
    init(from decoder: Decoder) throws {
        areas = try decoder.singleValueContainer().decode([String: CalibrationScope].self)
    }

    static let statewide = "South Carolina (statewide)"
}

struct CalibrationScope: Decodable, Hashable {
    let groups: [String: CalibrationGroup]
}

struct CalibrationGroup: Decodable, Hashable {
    let n: Int
    let official: Double
}

/// Who publishes the inspection result: the SC Department of Agriculture (SCDA), the one statewide inspector.
enum InspectionSource: Int, Hashable, CaseIterable {
    case scda = 0

    var name: String { "SCDA" }
    var key: String { "scda" }
    var agency: String { "SC Department of Agriculture" }
    /// how SCDA's posted grade reads, in plain words
    var scale: String {
        "SCDA posts a letter grade at each establishment after an inspection: A above 87 points, B 78–87, C below 78. Under 8-403.10(G) of Regulation 61-25 the posted grade can differ from the inspection's score, and SC Food Grades publishes the posted grade, not the score, so the grade is shown as posted and this app computes none. \u{201C}Permit\u{201D} visits are pre-operational inspections (a new permit, a change of owner, a compliance visit)."
    }
    /// SC Food Grades, which opens and shows SCDA's own records (checked with curl)
    var sourceURL: URL { Links.foodGrades }
}

/// SCDA's posted grade for an inspection (index into DataFile.results: "A", "B", "C"). Never computed by us.
struct InspectionBand: Hashable {
    let index: Int
    let label: String

    /// B or C: shown amber or rose
    var isLow: Bool { label == "B" || label == "C" }
    var isMiddle: Bool { label == "B" }
    var fill: Color { label == "C" ? Color(hex: 0xF9D5DB) : label == "B" ? Color(hex: 0xFFE9C2) : Color(hex: 0xDDEFE3) }
    var ink: Color { label == "C" ? Color(hex: 0x7A0019) : label == "B" ? Color(hex: 0x6B3A00) : Color(hex: 0x0E5A2B) }
    /// "Grade A"
    var title: String { label.isEmpty ? "No grade" : "Grade " + label }
}

/// What a list row shows and sorts by (core file): [source, posted grade, 0, date] of the latest SCDA record with a letter grade.
/// `score` is unused (SC Food Grades publishes no score) and is always 0.
struct InspectionRecord: Hashable {
    let city: InspectionSource
    let band: Int
    let score: Int
    let d: String

    /// From the JSONSerialization array (the launch path); nil when a field is missing.
    init?(array a: [Any]) {
        guard a.count >= 4, let c = (a[0] as? Int).flatMap(InspectionSource.init(rawValue:)), let b = a[1] as? Int, let s = a[2] as? Int,
              let d = a[3] as? String else { return nil }
        city = c; band = b; score = s; self.d = d
    }

    init(city: InspectionSource, band: Int, score: Int, d: String) { self.city = city; self.band = band; self.score = score; self.d = d }
}

/// One SCDA record: [date, posted grade ("A", "B", "C", "S" for a suspension notice, or "" when none was posted), type index,
/// report id (the PDF at pubdoc.dhec.sc.gov/inspection/<id>.pdf)].
struct InspectionVisit: Decodable, Hashable {
    let d: String
    let grade: String
    let t: Int
    let report: String?

    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        d = try c.decode(String.self)
        grade = try c.decode(String.self)
        t = try c.decode(Int.self)
        report = try c.decodeIfPresent(String.self)
    }

    /// the inspection report SC Food Grades links (a PDF that opens; checked with curl)
    var reportURL: URL? {
        guard let report, report.range(of: "^[0-9a-fA-F-]{20,64}$", options: .regularExpression) != nil else { return nil }
        return URL(string: "https://pubdoc.dhec.sc.gov/inspection/\(report).pdf")
    }
    var gradeText: String { grade == "S" ? "Suspension notice" : grade.isEmpty ? "No grade posted" : "Grade " + grade }
}

/// The place's inspection record (detail file): SCDA's records for three years, latest first (the newest ten).
struct InspectionDetail: Decodable, Hashable {
    let n: Int?               // SCDA records in the three years SC Food Grades publishes
    let h: [InspectionVisit]?

    var visits: [InspectionVisit] { h ?? [] }
}

/// An official record on the place: [source ("SCDA retail food permit"), permit number, facility type ("Retail Food Establishment")].
/// SCDA publishes no expiration dates.
struct License: Decodable, Hashable {
    let source: String
    let id: String?
    let type: String

    init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        source = try c.decode(String.self)
        id = try c.decodeIfPresent(String.self)
        type = try c.decode(String.self)
    }
}

/// A place's detail record, from its region's detail file.
struct PlaceDetail: Decodable, Hashable {
    let lic: [License]?
    let ph: String?
    let w: String?
    let inspection: InspectionDetail?

    enum CodingKeys: String, CodingKey {
        case lic, ph, w
        case inspection = "in"
    }

    /// web links only: a bare host gets https://, and any other scheme (javascript:, tel:, a custom app URL) is dropped
    var website: URL? {
        w.flatMap { URL(string: $0.contains("://") ? $0 : "https://" + $0) }
            .flatMap { ["http", "https"].contains($0.scheme?.lowercased() ?? "") && $0.host != nil ? $0 : nil }
    }
    var licenses: [License] { lic ?? [] }
}

struct PlaceRecord {
    // the memberwise initializer is used by init?(_ d:) below
    let id: String
    let n: String
    let c: Int?
    let cu: Int
    let t: Int
    let s: Int
    let co: Int?
    let rg: Int?
    let a: String?
    let z: String?
    let la: Double?
    let lo: Double?
    let b: Int?
    let ch: Int?
    let v: Int?
    let bar: Int?
    let liq: Int?
    let g: Int?
    let hc: Int?
    let h: Int?
    let mi: Int?
    let jbf: String?
    let ip: Double?
    let f: Int?
    let fn: String?
    let note: String?
    let dish: String?
    let seas: String?
    /// the listing's other name when a hand-checked place shows its verified one ("Cafe Versailles Calle 8"): searchable, shown small
    let aka: String?
    let inspection: InspectionRecord?
}

extension PlaceRecord {
    /// From one JSONSerialization dictionary (the fast path); nil when the required fields are missing.
    init?(_ d: [String: Any]) {
        guard let id = d["id"] as? String, let n = d["n"] as? String, let cu = d["cu"] as? Int, let t = d["t"] as? Int, let s = d["s"] as? Int else { return nil }
        func i(_ k: String) -> Int? { d[k] as? Int }
        func str(_ k: String) -> String? { d[k] as? String }
        self.init(id: id, n: n, c: i("c"), cu: cu, t: t, s: s, co: i("co"), rg: i("rg"), a: str("a"), z: str("z"), la: d["la"] as? Double,
                  lo: d["lo"] as? Double, b: i("b"), ch: i("ch"), v: i("v"), bar: i("bar"), liq: i("liq"), g: i("g"), hc: i("hc"), h: i("h"),
                  mi: i("mi"), jbf: str("jbf"), ip: d["ip"] as? Double, f: i("f"), fn: str("fn"), note: str("note"), dish: str("dish"),
                  seas: str("seas"), aka: str("aka"),
                  inspection: (d["in"] as? [Any]).flatMap { InspectionRecord(array: $0) })
    }
}

// MARK: - The model the views use

struct PlaceTags: OptionSet, Hashable {
    let rawValue: Int
    // the bits pipeline/southcarolina.py writes (TAGS there, in this order)
    static let bbq = PlaceTags(rawValue: 1)         // hand-checked whole-hog and mustard barbecue
    static let seafood = PlaceTags(rawValue: 2)     // hand-checked Lowcountry and Grand Strand seafood
    static let gullah = PlaceTags(rawValue: 4)      // hand-checked Gullah Geechee cooking
    static let meat3 = PlaceTags(rawValue: 8)       // hand-checked meat-and-threes and drive-ins
    static let oldest = PlaceTags(rawValue: 16)     // hand-checked, open at this address since 1960 or earlier

    /// the chips and Spotlight words for the hand-checked guides
    static let labels: [(PlaceTags, String)] = [(.bbq, "Whole-hog & mustard barbecue"), (.seafood, "Lowcountry seafood"),
                                                (.gullah, "Gullah Geechee cooking"), (.meat3, "Meat-and-three")]
}

/// How a place got on the list. The share that matched a license comes from calibration.
enum Tier: Int, Comparable {
    case listing = 0        // one map listing
    case confirmed = 1      // a high-confidence Meta listing, or a hand-checked place
    case licensed = 2       // matched to an open SCDA retail food permit

    static func < (a: Tier, b: Tier) -> Bool { a.rawValue < b.rawValue }

    var label: String {
        switch self {
        case .licensed: "On SCDA's permit list"
        case .confirmed: "High-confidence listing"
        case .listing: "Listing only"
        }
    }
}

enum Michelin: Int {
    case none = 0, recommended = 1, bib = 2, oneStar = 3, twoStars = 4, threeStars = 5
    var label: String? {
        switch self {
        case .none: nil
        case .recommended: "MICHELIN Recommended"
        case .bib: "Bib Gourmand"
        case .oneStar: "1 MICHELIN Star"
        case .twoStars: "2 MICHELIN Stars"
        case .threeStars: "3 MICHELIN Stars"
        }
    }
}

struct Place: Identifiable, Hashable {
    let id: String
    let name: String
    let address: String?
    let city: String?
    let county: String?
    /// the region whose detail file holds this place's inspection history, license, phone and website
    let region: String?
    let zip: String?
    let coordinate: CLLocationCoordinate2D?
    let cuisine: String
    let brand: String?
    let chainCount: Int
    let tier: Tier
    let source: String
    let isVenue: Bool
    let isBar: Bool
    let tags: PlaceTags
    /// On our hand-checked list (data/research): confirmed open with a 2025–26 source.
    let handChecked: Bool
    let honorFlags: Int
    let michelin: Michelin
    let iconicPoints: Double?
    let jamesBeard: String?
    let founded: Int?
    let foundedNote: String?
    let note: String?
    let dishes: String?
    let seasonal: String?
    let inspection: InspectionRecord?
    /// normalized text for search: name, town, county, zip, cuisine, brand, dishes, then the address with street words abbreviated
    let searchText: String
    let nameText: String
    /// the A-to-Z key, worked out once at load: the normalized name ("por wine house" for "/pôr/ Wine House"), so case, accents
    /// and leading punctuation don't change the order, and a sort never runs a localized compare per comparison
    let sortKey: String
    /// made once at load: a new CLLocation per comparison made a Nearest sort of 16,000 places take seconds
    let location: CLLocation?

    static func == (a: Place, b: Place) -> Bool { a.id == b.id }
    func hash(into h: inout Hasher) { h.combine(id) }

    /// MICHELIN, James Beard or a verified founding year: what the map and Spotlight put first
    var isHonored: Bool { honorFlags != 0 || michelin != .none }
    /// what the Honors section lists: a MICHELIN distinction or a James Beard honor ("oldest" alone isn't an honor)
    var hasHonors: Bool { michelin != .none || jamesBeard != nil }
    var isChain: Bool { chainCount >= 5 }
    var jamesBeardLabel: String? {
        if honorFlags & 1 != 0 { return "America's Classic" }
        if honorFlags & 2 != 0 { return "James Beard winner" }
        if honorFlags & 4 != 0 { return "James Beard finalist" }
        if honorFlags & 8 != 0 { return "James Beard semifinalist" }
        return nil
    }
    /// The chip for a James Beard line: the place's own honor, or a restaurateur (group) honor when that's the only one.
    var jamesBeardChip: String? { jamesBeardLabel ?? (jamesBeard != nil ? "James Beard (restaurateur)" : nil) }
    /// a hand-checked South Carolina pick: the accent pins
    var isClassic: Bool { handChecked && !tags.isEmpty }
    var townLine: String { [city, cuisine].compactMap { $0 }.joined(separator: " · ") }
    var fullAddress: String {
        [address, [city, zip].compactMap { $0 }.joined(separator: " ")].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: ", ")
    }

    /// Every place in the core file, built on all cores at once (each place's search text takes four normalizations).
    static func build(_ raw: [[String: Any]], file: DataFile) -> [Place] {
        var out = [Place?](repeating: nil, count: raw.count)
        let chunk = 2_000, chunks = (raw.count + chunk - 1) / chunk
        out.withUnsafeMutableBufferPointer { buf in
            let base = buf   // each chunk writes only its own slots
            DispatchQueue.concurrentPerform(iterations: chunks) { c in
                for k in (c * chunk)..<min(raw.count, (c + 1) * chunk) {
                    base[k] = PlaceRecord(raw[k]).map { Place($0, file: file) }
                }
            }
        }
        return out.compactMap { $0 }
    }

    init(_ r: PlaceRecord, file: DataFile) {
        let city = r.c.flatMap { $0 < file.cities.count ? file.cities[$0] : nil }
        let cuisine = r.cu < file.cuisines.count ? file.cuisines[r.cu] : "American & Other"
        let brand = r.b.flatMap { $0 < file.brands.count ? file.brands[$0] : nil }
        let county = r.co.flatMap { $0 < file.counties.count ? file.counties[$0] : nil }
        id = r.id
        name = r.n
        address = r.a
        self.city = city
        self.county = county
        region = r.rg.flatMap { $0 < file.regions.count ? file.regions[$0] : nil }
        zip = r.z
        if let la = r.la, let lo = r.lo { coordinate = CLLocationCoordinate2D(latitude: la, longitude: lo) } else { coordinate = nil }
        self.cuisine = cuisine
        self.brand = brand
        chainCount = r.ch ?? 1
        tier = Tier(rawValue: r.t) ?? .listing
        source = r.s < file.srcs.count ? file.srcs[r.s] : "meta"
        isVenue = r.v == 1
        isBar = r.bar == 1
        tags = PlaceTags(rawValue: r.g ?? 0)
        handChecked = r.hc == 1
        honorFlags = r.h ?? 0
        michelin = Michelin(rawValue: r.mi ?? 0) ?? .none
        iconicPoints = r.ip
        jamesBeard = r.jbf
        founded = r.f
        foundedNote = r.fn
        note = r.note
        dishes = r.dish
        seasonal = r.seas
        inspection = r.inspection
        // the dishes a hand-checked place serves are searchable too: "shrimp and grits beaufort", "hash and rice west columbia"
        searchText = " " + Search.normalize([r.n, r.aka, city, county, r.z, cuisine, brand, r.dish].compactMap { $0 }.joined(separator: " ")) + " "
            + Search.normalizeAddress(r.a ?? "") + " "
        nameText = " " + Search.normalize([r.n, brand].compactMap { $0 }.joined(separator: " ")) + " "
        sortKey = Search.normalize(r.n)
        location = coordinate.map { CLLocation(latitude: $0.latitude, longitude: $0.longitude) }
    }
}

/// The data's dates are calendar days ("2026-06-16"), not moments: read and shown in UTC, so no time zone can move one a day.
enum DayFormat {
    private static let utc = TimeZone(identifier: "UTC")!

    static func date(_ s: String?) -> Date? {
        guard let s, s.count >= 10 else { return nil }
        let parts = s.prefix(10).split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3, (1...12).contains(parts[1]), (1...31).contains(parts[2]) else { return nil }
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = utc
        return cal.date(from: DateComponents(year: parts[0], month: parts[1], day: parts[2]))
    }

    /// "Jun 16, 2026" (in the reader's language); anything that isn't a date is shown as it is
    static func text(_ s: String?) -> String? {
        guard let s else { return nil }
        guard let d = date(s) else { return s }
        return d.formatted(Date.FormatStyle(date: .abbreviated, time: .omitted, timeZone: utc))
    }

    /// "Sep 2025"
    static func monthYear(_ s: String?) -> String? {
        guard let s else { return nil }
        guard let d = date(s) else { return s }
        return d.formatted(Date.FormatStyle(timeZone: utc).month(.abbreviated).year())
    }
}
