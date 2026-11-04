import XCTest
import CoreLocation
@testable import SouthCarolinaEats

@MainActor
final class SouthCarolinaEatsTests: XCTestCase {

    /// A tiny core file and two region detail files with the same shape as Resources/places.json and Resources/detail-*.json.
    private func sampleModel() async throws -> AppModel {
        let json = """
        {"v":1,"generated":"2026-10-26","overture_release":"2026-10-21.0","scda_open_food_permits":20014,"scda_open_since":"2025-04-19",
         "inspections_through":{"scda":"2026-10-19"},"inspections_published":{"scda":"2026-10-26"},
         "cities":["Charleston","Columbia","Spartanburg","North Charleston","Greenville","St. Helena Island"],
         "cuisines":["BBQ","Seafood","Soul & Southern","Chicken & Wings","American & Other","Bar & Pub"],
         "brands":["Bojangles"],"counties":["Charleston County","Richland County","Spartanburg County","Greenville County","Beaufort County"],
         "regions":["Upstate","Midlands","Pee Dee","Grand Strand","Charleston & Lowcountry","Beaufort & Hilton Head","Aiken & Savannah River"],
         "srcs":["official","meta","AllThePlaces","DAC","research"],
         "results":["A","B","C"],
         "itypes":["Follow-up","Permit (change of owner)","Routine"],
         "count":10,"count_restaurants":9,
         "calibration":{"South Carolina (statewide)":{"listings":24515,"groups":{"meta_high":{"n":9854,"official":0.784}}},"Charleston County":{"groups":{"meta_high":{"n":1000,"official":0.70}}}},
         "places":[
          {"id":"a","n":"Bowens Island Restaurant","c":0,"co":0,"rg":4,"cu":1,"t":2,"s":1,"hc":1,"g":18,"f":1946,"a":"1870 Bowens Island Rd","z":"29412","la":32.676,"lo":-79.963,
           "h":1,"jbf":"America's Classics 2006","ip":60,"dish":"oyster roast; fried shrimp","in":[0,0,0,"2026-05-08"]},
          {"id":"b","n":"Whole Hog Place","c":1,"co":1,"rg":1,"cu":0,"t":1,"s":1,"hc":1,"g":1,"a":"100 Main St","la":34.0,"lo":-81.03},
          {"id":"c","n":"Bojangles","c":1,"co":1,"rg":1,"cu":3,"t":2,"s":0,"b":0,"ch":120,"la":34.01,"lo":-81.04,"in":[0,1,0,"2026-08-05"]},
          {"id":"d","n":"Some Grill","c":1,"co":1,"rg":1,"cu":4,"t":0,"s":1,"a":"200 Gervais St","la":34.0,"lo":-81.035,"in":[0,2,0,"2026-02-11"]},
          {"id":"e","n":"Spinx","c":1,"co":1,"rg":1,"cu":4,"t":1,"s":1,"v":1,"la":34.02,"lo":-81.05},
          {"id":"f","n":"Wade's Restaurant","c":2,"co":2,"rg":0,"cu":2,"t":1,"s":1,"hc":1,"g":8,"a":"1000 N Pine St","la":34.969,"lo":-81.934,"h":1,"jbf":"America's Classics 2024"},
          {"id":"g","n":"Gullah Kitchen","c":5,"co":4,"rg":5,"cu":2,"t":1,"s":1,"hc":1,"g":4,"a":"5 Sea Island Pkwy","la":32.38,"lo":-80.57},
          {"id":"h","n":"Leon's Oyster Shop","c":0,"co":0,"rg":4,"cu":1,"t":2,"s":1,"hc":1,"mi":2,"h":0,"la":32.80,"lo":-79.95,"in":[0,0,0,"2026-10-01"]},
          {"id":"i","n":"Scoundrel","c":4,"co":3,"rg":0,"cu":4,"t":2,"s":1,"hc":1,"mi":3,"h":4,"jbf":"Best Chef: Southeast finalist 2026 (Joe Cash)","la":34.85,"lo":-82.40,"in":[0,0,0,"2026-01-15"]},
          {"id":"j","n":"Corner Diner","c":3,"co":0,"rg":4,"cu":4,"t":1,"s":1,"la":32.88,"lo":-79.99}
         ]}
        """
        let lowcountry = """
        {"a":{"lic":[["SCDA retail food permit","10-206-00001","Retail Food Establishment"]],
              "ph":"(843) 795-2757","w":"bowensisland.com","in":{"n":12,"h":[["2026-05-08","A",2,"57639b0a-2cf7-4afc-aabe-f6dee464a00f"],["2025-11-25","A",0,null],["2024-11-12","S",1,"622ddf29-2984-402f-a6c9-b4ec52fb0de5"],["2024-11-05","B",2,"bad id!"]]}},
         "h":{"w":"javascript:alert(1)","in":{"n":1,"h":[["2026-10-01","A",2,null]]}}}
        """
        let midlands = """
        {"c":{"lic":[["SCDA retail food permit","40-206-01234","Retail Food Establishment"]],"in":{"n":2,"h":[["2026-08-05","B",2,null]]}},
         "d":{"in":{"n":1,"h":[["2026-02-11","C",2,null]]}}}
        """
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("sc-test-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let url = dir.appendingPathComponent("places.json")
        try json.data(using: .utf8)!.write(to: url)
        try lowcountry.data(using: .utf8)!.write(to: dir.appendingPathComponent("detail-charleston-lowcountry.json"))
        try midlands.data(using: .utf8)!.write(to: dir.appendingPathComponent("detail-midlands.json"))
        let model = AppModel(defaults: UserDefaults(suiteName: "test-\(UUID().uuidString)")!)
        await model.load(from: url, detailFolder: dir)
        XCTAssertTrue(model.isLoaded, model.loadError ?? "")
        return model
    }

    func testDecodesAndHidesNonRestaurantsByDefault() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.places.count, 10)
        XCTAssertEqual(m.restaurantCount, 9)
        XCTAssertFalse(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Spinx" }, "a gas-station counter is hidden by default")
        m.filters.includeNonRestaurants = true
        XCTAssertTrue(m.list(.all, sort: .name, search: "", here: nil).contains { $0.name == "Spinx" })
    }

    /// A large navigation title can't wrap: an iPhone 17 Pro Max shows about 27 characters, the iPad's list column about 19
    /// (captures 2026-10-28: "Whole-Hog & Mustard Barbe…" and, on iPad, "Gullah Geechee Cooki…").
    func testGuideNavTitlesFit() {
        for g in Guide.allCases {
            XCTAssertLessThanOrEqual(g.navTitle(iPadColumn: false).count, 27, "\(g) on iPhone")
            XCTAssertLessThanOrEqual(g.navTitle(iPadColumn: true).count, 19, "\(g) on iPad")
        }
    }

    func testGuidesListOnlyWhatTheyPromise() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.list(.bbq, sort: .name, search: "", here: nil).map(\.name), ["Whole Hog Place"], "the chain isn't hand-checked")
        XCTAssertEqual(m.list(.seafood, sort: .name, search: "", here: nil).map(\.name), ["Bowens Island Restaurant"])
        XCTAssertEqual(m.list(.gullah, sort: .name, search: "", here: nil).map(\.name), ["Gullah Kitchen"])
        XCTAssertEqual(m.list(.meat3, sort: .name, search: "", here: nil).map(\.name), ["Wade's Restaurant"])
        XCTAssertEqual(m.list(.oldest, sort: .oldest, search: "", here: nil).map(\.name), ["Bowens Island Restaurant"])
        XCTAssertEqual(m.list(.honors, sort: .iconic, search: "", here: nil).map(\.name),
                       ["Scoundrel", "Leon's Oyster Shop", "Bowens Island Restaurant", "Wade's Restaurant"], "MICHELIN first (star, then Bib), then James Beard")
    }

    func testInspectionGradesAreSCDAsOwn() async throws {
        let m = try await sampleModel()
        let worst = m.list(.inspections, sort: .lowestScore, search: "", here: nil)
        XCTAssertEqual(worst.prefix(2).map(\.name), ["Some Grill", "Bojangles"], "C first, then B")
        let t = try XCTUnwrap(worst.first?.inspection)
        XCTAssertEqual(t.city, .scda); XCTAssertEqual(m.band(t.band).label, "C"); XCTAssertEqual(m.band(t.band).title, "Grade C")
        XCTAssertTrue(m.band(t.band).isLow); XCTAssertTrue(m.band(1).isLow); XCTAssertFalse(m.band(0).isLow)
        XCTAssertEqual(t.score, 0, "SC Food Grades publishes no score, so none is shown")
        XCTAssertEqual(m.list(.inspections, sort: .highestScore, search: "", here: nil).first.map { m.band($0.inspection!.band).label }, "A")
        XCTAssertEqual(m.list(.inspections, sort: .recent, search: "", here: nil).first?.name, "Leon's Oyster Shop")
        XCTAssertFalse(m.list(.inspections, sort: .recent, search: "", here: nil).contains { $0.name == "Whole Hog Place" }, "no grade, not listed")
    }

    func testDatesAreCalendarDays() {
        var utc = Calendar(identifier: .gregorian)
        utc.timeZone = TimeZone(identifier: "UTC")!
        let d = DayFormat.date("2026-06-16")!
        XCTAssertEqual(utc.dateComponents([.year, .month, .day], from: d), DateComponents(year: 2026, month: 6, day: 16))
        XCTAssertTrue(DayFormat.monthYear("2025-09-01")!.contains("2025"))
        XCTAssertNil(DayFormat.date("2026-13-01"))
        XCTAssertEqual(DayFormat.text("soon"), "soon", "a value that isn't a date is shown as it is")
    }

    func testRegionDetailsLoadOnDemand() async throws {
        let m = try await sampleModel()
        let v = await m.detail(for: m.place(id: "a")!)
        XCTAssertEqual(v?.licenses.first?.source, "SCDA retail food permit")
        XCTAssertEqual(v?.licenses.first?.id, "10-206-00001")
        XCTAssertEqual(v?.website?.absoluteString, "https://bowensisland.com", "a bare host gets https://")
        let visits = try XCTUnwrap(v?.inspection?.visits)
        XCTAssertEqual(visits.count, 4)
        XCTAssertEqual(visits[0].gradeText, "Grade A")
        XCTAssertEqual(visits[0].reportURL?.absoluteString, "https://pubdoc.dhec.sc.gov/inspection/57639b0a-2cf7-4afc-aabe-f6dee464a00f.pdf")
        XCTAssertNil(visits[1].reportURL, "no report id, no link")
        XCTAssertEqual(visits[2].gradeText, "Suspension notice", "an S is SCDA's suspension notice, not a grade")
        XCTAssertNil(visits[3].reportURL, "an id that isn't a report id never becomes a link")
        XCTAssertEqual(m.visitType(visits[0].t), "Routine")
        let leon = await m.detail(for: m.place(id: "h")!)
        XCTAssertNil(leon?.website, "a javascript: link never becomes a website button")
        let bo = await m.detail(for: m.place(id: "c")!)
        XCTAssertEqual(bo?.licenses.first?.id, "40-206-01234", "the Midlands file is read on its own")
        XCTAssertEqual(AppModel.regionSlug("Charleston & Lowcountry"), "charleston-lowcountry")
        XCTAssertEqual(AppModel.regionSlug("Aiken & Savannah River"), "aiken-savannah-river")
        let missing = await m.detail(for: m.place(id: "g")!)
        XCTAssertNil(missing, "a region with no detail file reads as no detail, not a crash")
    }

    func testSearchWordStartsTownsAndGuides() async throws {
        let m = try await sampleModel()
        XCTAssertEqual(m.list(.all, sort: .name, search: "bowens isl", here: nil).map(\.name), ["Bowens Island Restaurant"])
        XCTAssertEqual(m.list(.all, sort: .name, search: "spartanburg", here: nil).map(\.name), ["Wade's Restaurant"], "a town narrows to it")
        XCTAssertEqual(m.list(.all, sort: .name, search: "north charleston", here: nil).map(\.name), ["Corner Diner"], "the longest town wins")
        XCTAssertEqual(m.list(.all, sort: .name, search: "fried shrimp", here: nil).map(\.name), ["Bowens Island Restaurant"], "a dish finds who serves it")
        XCTAssertEqual(m.list(.all, sort: .name, search: "🍕", here: nil), [], "an emoji finds nothing, not everything")
        XCTAssertEqual(m.list(.all, sort: .name, search: "whole hog", here: nil).map(\.name), ["Whole Hog Place"], "a guide phrase means the guide")
        XCTAssertEqual(m.list(.all, sort: .name, search: "gullah", here: nil).map(\.name), ["Gullah Kitchen"])
        XCTAssertEqual(m.list(.all, sort: .name, search: "saint helena island", here: nil).map(\.name), ["Gullah Kitchen"], "St. and Saint are one town")
    }

    /// South Carolina has a town called North: "north main" is a street direction (N Main St), not the town, while "north" alone is
    /// the town and "north charleston" is North Charleston.
    func testDirectionWordIsNotTheTownOfNorth() {
        let towns = ["n": "North", "n charleston": "North Charleston", "columbia": "Columbia"]
        let q = Search.parse("north main", towns: towns)
        XCTAssertNil(q.town, "a direction before another word isn't the town")
        XCTAssertEqual(q.tokens.first, [" n ", " north"])
        XCTAssertEqual(Search.parse("north", towns: towns).town, "North")
        XCTAssertEqual(Search.parse("north charleston", towns: towns).town, "North Charleston")
        XCTAssertEqual(Search.parse("n main columbia", towns: towns).town, "Columbia")
    }

    /// Letters folding can't strip an accent from still match their plain spelling: "orchard" finds Ørchard Bar & Table.
    func testSearchFoldsLettersWithoutAccents() {
        XCTAssertEqual(Search.normalize("Ørchard Bar & Table"), "orchard bar and table")
        XCTAssertEqual(Search.normalize("Brutø Æble Phở Đô Łódź Straße"), "bruto aeble pho do lodz strasse")
        XCTAssertEqual(Search.normalize("Okàn · Bintü Atelier"), "okan bintu atelier")
    }

    func testOutsideStateUsesTheOutline() {
        func inside(_ la: Double, _ lo: Double) -> Bool { StateOutline.contains(CLLocationCoordinate2D(latitude: la, longitude: lo)) }
        XCTAssertTrue(inside(32.78, -79.93), "Charleston"); XCTAssertTrue(inside(34.00, -81.03), "Columbia"); XCTAssertTrue(inside(34.85, -82.40), "Greenville")
        XCTAssertTrue(inside(32.135, -80.75), "Hilton Head's south end"); XCTAssertTrue(inside(32.655, -79.94), "Folly Beach"); XCTAssertTrue(inside(32.12, -80.87), "Daufuskie")
        XCTAssertTrue(inside(35.01, -80.94), "Fort Mill"); XCTAssertTrue(inside(33.50, -81.97), "North Augusta"); XCTAssertTrue(inside(33.87, -78.61), "Little River")
        XCTAssertFalse(inside(35.23, -80.84), "Charlotte"); XCTAssertFalse(inside(34.23, -77.94), "Wilmington, N.C."); XCTAssertFalse(inside(33.75, -84.39), "Atlanta")
        XCTAssertFalse(inside(35.60, -82.55), "Asheville"); XCTAssertFalse(inside(37.33, -122.03), "Cupertino")
    }

    func testMatchRatesComeFromTheStatewideList() async throws {
        let m = try await sampleModel()
        XCTAssertNil(m.matchRate(for: m.place(id: "a")!), "an official record needs no listing rate")
        XCTAssertEqual(m.matchRate(for: m.place(id: "b")!), "78%", "the statewide rate, not a county's")
    }

    func testBundledData() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "bundle-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        XCTAssertGreaterThan(m.restaurantCount, 12_000)
        XCTAssertGreaterThan(m.count(.inspections), 9_000)
        XCTAssertGreaterThan(m.licensedCount, 9_000, "restaurants matched to an open SCDA permit")
        XCTAssertEqual(Set(m.places.map(\.id)).count, m.places.count, "ids are unique")
        for g in Guide.allCases where g.tag != nil {
            XCTAssertTrue(m.places.filter(g.includes).allSatisfy(\.handChecked), "\(g.title) lists only hand-checked places")
        }
        // SCDA's grades only: A, B or C, a date in the three years published, never a score
        XCTAssertEqual(m.results, ["A", "B", "C"])
        let through = try XCTUnwrap(m.inspectionsThrough["scda"])
        XCTAssertTrue(m.places.allSatisfy { p in p.inspection.map { $0.score == 0 && $0.band >= 0 && $0.band <= 2 && $0.d <= through && $0.d >= "2023-01-01" } ?? true },
                      "every grade is A, B or C, dated within the records, with no score")
        XCTAssertGreaterThanOrEqual(m.places.filter { $0.michelin != .none }.count, 25, "the MICHELIN Guide American South 2026 lists 27 South Carolina places")
        XCTAssertEqual(m.places.filter { $0.michelin == .oneStar }.map(\.name).count, 4)
        // no Google-derived data: the data file has no rating, review or price fields at all
        let raw = try String(contentsOf: Bundle.main.url(forResource: "places", withExtension: "json")!, encoding: .utf8)
        for key in ["\"rating\"", "\"reviews\"", "\"price\"", "\"gmap_id\""] { XCTAssertFalse(raw.contains(key), "\(key) must not ship") }
    }

    /// App Store rule: no screenshot shows a place whose latest SCDA grade is B or C, and the iPad's place column (every record) shows
    /// no B, C or suspension notice.
    func testScreenshotPicksPass() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "shots-\(UUID().uuidString)")!)
        await m.load()
        for (n, town) in ScreenshotMode.allPicks {
            let p = try XCTUnwrap(m.places.first { $0.name == n && $0.city == town }, "\(n) is in the data")
            XCTAssertFalse(p.inspection.map { m.band($0.band).isLow } ?? false, "\(n)'s latest grade isn't A")
        }
        for (n, town) in [ScreenshotMode.detailPick, ScreenshotMode.padPick] {
            let p = try XCTUnwrap(m.places.first { $0.name == n && $0.city == town })
            let visits = await m.detail(for: p)?.inspection?.visits ?? []
            XCTAssertFalse(visits.contains { ["B", "C", "S"].contains($0.grade) }, "\(n) has a record that isn't an A, and the iPad shows it")
        }
    }

    /// Stable ids: md5(name + ~100 m cell)[:12], never a row number; every bundled region detail file decodes and its ids are core ids.
    func testIdsAndBundledDetailFiles() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "ids-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.places.allSatisfy { $0.id.count >= 12 && $0.id.prefix(12).allSatisfy(\.isHexDigit) && $0.id.dropFirst(12).allSatisfy { $0 == "x" } })
        let ids = Set(m.places.map(\.id))
        var licensed = 0
        for region in Set(m.places.compactMap(\.region)) {
            let url = try XCTUnwrap(Bundle.main.url(forResource: "detail-" + AppModel.regionSlug(region), withExtension: "json"), region)
            let d = try JSONDecoder().decode([String: PlaceDetail].self, from: Data(contentsOf: url))
            XCTAssertTrue(Set(d.keys).isSubset(of: ids), "\(region) detail ids are core ids")
            licensed += d.values.filter { $0.licenses.contains { $0.source == "SCDA retail food permit" } }.count
        }
        XCTAssertGreaterThan(licensed, 9_000, "permitted places carry their SCDA permit")
    }

    func testBundledDataGuards() async throws {
        let m = AppModel(defaults: UserDefaults(suiteName: "guards-\(UUID().uuidString)")!)
        await m.load()
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        XCTAssertEqual(DataGuards.adultVenues(m.places), [], "no strip club under its name")
        XCTAssertEqual(DataGuards.badWebsites(try DataGuards.bundledLinks(m.places)), [], "no directory, Google or news page as a restaurant's website")
        XCTAssertEqual(DataGuards.badNames(m.places), [], "no visible name ending in \u{201C} the\u{201D} or \u{201C} of\u{201D}, or just \u{201C}The\u{201D}")
        XCTAssertEqual(DataGuards.legalNames(m.places), [], "no license holder entity name (\u{201C}… LLC\u{201D}) shown as a place's name")
        XCTAssertEqual(DataGuards.nonRestaurants(m.places), [], "no nail salon, senior home, gun store or gas station among the restaurants")
        XCTAssertEqual(DataGuards.listedTwice(m.places), [], "no place listed twice under one name and street address, pins apart")
        XCTAssertEqual(DataGuards.guessedPins(m.places), [], "no pin shared by house numbers a block or more apart (a geocoder's guess)")
        let sites = try DataGuards.bundledWebsites()
        XCTAssertGreaterThan(sites.count, 5_000, "the detail files carry websites")
        XCTAssertEqual(DataGuards.notOneURL(sites), [], "every website is one URL, with no text after it")
    }

    /// Each guard above fires on a copy of the bundled data broken the way QA found it elsewhere: a guard that can't fail guards nothing.
    func testGuardsCatchABrokenCopy() async throws {
        let raw = try Data(contentsOf: Bundle.main.url(forResource: "places", withExtension: "json")!)
        var file = try XCTUnwrap(JSONSerialization.jsonObject(with: raw) as? [String: Any])
        var places = try XCTUnwrap(file["places"] as? [[String: Any]])
        let idx = places.indices.filter { places[$0]["v"] == nil && places[$0]["la"] != nil && places[$0]["a"] != nil }.prefix(9).map { $0 }
        places[idx[2]]["n"] = "Larry Flynt's Hustler Club"
        places[idx[3]]["n"] = "Kitchen the"
        places[idx[4]]["n"] = "PALMETTO HOSPITALITY GROUP LLC"
        places[idx[5]]["n"] = "Tipsy Nails & Spa"
        // a permit-only twin of a place 5.5 km north, and three permits stacked on one ZIP-centroid pin
        var twin = places[idx[0]]
        twin["id"] = "ffffffffffff"; twin["la"] = (twin["la"] as? Double ?? 0) + 0.05
        places.append(twin)
        for (k, n) in [(6, "100 Test Rd"), (7, "1300 Test Rd"), (8, "2900 Test Rd")] {
            places[idx[k]]["a"] = n; places[idx[k]]["la"] = 34.0687; places[idx[k]]["lo"] = -81.0277
        }
        file["places"] = places
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("places-broken.json")
        try JSONSerialization.data(withJSONObject: file).write(to: url)
        let m = AppModel(defaults: UserDefaults(suiteName: "broken-\(UUID().uuidString)")!)
        await m.load(from: url)
        XCTAssertTrue(m.isLoaded, m.loadError ?? "")
        let id = idx.map { places[$0]["id"] as? String }
        func caught(_ found: [String], _ i: Int, _ what: String) {
            XCTAssertTrue(found.contains { $0.contains("[\(id[i] ?? "?")]") }, "the guard missed \(what)")
        }
        let links = [(name: "A", id: "x1", url: "https://www.yelp.com/biz/some-place"), (name: "B", id: "x2", url: "https://www.postandcourier.com/food/"),
                     (name: "C", id: "x3", url: "https://smart.com/menu")]
        XCTAssertEqual(DataGuards.badWebsites(links).count, 2, "the guard catches a Yelp page and a news story, and not smart.com")
        caught(DataGuards.adultVenues(m.places), 2, "a strip club")
        caught(DataGuards.badNames(m.places), 3, "\u{201C}Kitchen the\u{201D}")
        caught(DataGuards.legalNames(m.places), 4, "a license holder's entity name")
        caught(DataGuards.nonRestaurants(m.places), 5, "a nail salon shown as a restaurant")
        caught(DataGuards.listedTwice(m.places), 0, "a place listed twice with pins 5.5 km apart")
        caught(DataGuards.guessedPins(m.places), 6, "three addresses stacked on one ZIP-centroid pin")
        let sites = [(id: "a", url: "https://togoorder.com/web/1754#/ (Order Online)"), (id: "b", url: "https://bubbakoos.com/a,https://bubbakoos.com/b"),
                     (id: "c", url: "https://togoorder.com/web/1754#/"), (id: "d", url: "https://x.example/menu?a=1&b=2#top")]
        XCTAssertEqual(DataGuards.notOneURL(sites).count, 2, "the guard catches a label after a link and two links run together, and nothing else")
    }
}

/// Checks on the bundled data, written as functions so testGuardsCatchABrokenCopy can prove each one fires.
enum DataGuards {
    /// directories, Google and news sites: matched on the link's host, so "smart.com" isn't "rt.com"
    static let badHosts = #"^https?://([^/?#]*\.)?(yelp\.com|business\.site|google\.com|groupon\.com|yellowpages\.com|tripadvisor\.com|postandcourier\.com|thestate\.com|greenvilleonline\.com|myrtlebeachonline\.com|islandpacket\.com|charlestoncitypaper\.com|live5news\.com|wistv\.com|eater\.com|rt\.com)([:/?#]|$)"#

    static func badWebsites(_ links: [(name: String, id: String, url: String)]) -> [String] {
        links.compactMap { l in
            guard l.url.range(of: badHosts, options: [.regularExpression, .caseInsensitive]) != nil else { return nil }
            return "\(l.name) [\(l.id)]: \(l.url)"
        }
    }

    /// every website link in the bundled region detail files, with its place's name
    static func bundledLinks(_ places: [Place]) throws -> [(name: String, id: String, url: String)] {
        let names = Dictionary(places.map { ($0.id, $0.name) }, uniquingKeysWith: { a, _ in a })
        var out: [(name: String, id: String, url: String)] = []
        for region in Set(places.compactMap(\.region)) {
            guard let url = Bundle.main.url(forResource: "detail-" + AppModel.regionSlug(region), withExtension: "json") else { continue }
            for (id, d) in try JSONDecoder().decode([String: PlaceDetail].self, from: Data(contentsOf: url)) {
                if let w = d.website?.absoluteString { out.append((names[id] ?? "?", id, w)) }
            }
        }
        return out
    }

    static let adultNames = #"gentlem[ae]n['’]?s club|strip club|exotic dancer|\bmen['’]?s club|rick['’]?s cabaret|xtc cabaret|baby dolls|spearmint rhino|bikini bar|pt['’]?s showclub|showgirls|centerfolds|treasures? gentlem|deja ?vu showgirls|hustler club|penthouse club|thee doll ?house"#

    /// every license key in the bundled region detail files, by place id
    static func bundledLicenses(_ places: [Place]) throws -> [String: [String]] {
        var out: [String: [String]] = [:]
        for region in Set(places.compactMap(\.region)) {
            guard let url = Bundle.main.url(forResource: "detail-" + AppModel.regionSlug(region), withExtension: "json") else { continue }
            for (id, d) in try JSONDecoder().decode([String: PlaceDetail].self, from: Data(contentsOf: url)) where !d.licenses.isEmpty {
                out[id] = d.licenses.compactMap(\.id)
            }
        }
        return out
    }

    static func adultVenues(_ places: [Place]) -> [String] {
        places.filter { $0.name.range(of: adultNames, options: [.regularExpression, .caseInsensitive]) != nil }.map { "\($0.name) [\($0.id)]" }
    }

    /// a name cut off after "the" or "of" ("Kitchen the", "Wines of") or nothing but "The", among the places shown by default
    static func badNames(_ places: [Place]) -> [String] {
        places.filter { p in
            let n = p.name.trimmingCharacters(in: .whitespaces).lowercased()
            return !p.isVenue && (n.hasSuffix(" the") || n.hasSuffix(" of") || n == "the")
        }.map { "\($0.name) [\($0.id)]" }
    }

    /// a license holder is never shown; a business name that's still a legal entity shouldn't be either
    static let legalSuffix = #"\b(llc|l\.l\.c|inc|corp|corporation)\.?$"#

    static func legalNames(_ places: [Place]) -> [String] {
        places.filter { !$0.isVenue && $0.name.range(of: legalSuffix, options: [.regularExpression, .caseInsensitive]) != nil }
            .map { "\($0.name) [\($0.id)]" }
    }

    /// businesses that aren't places to eat, among the places shown by default
    static let nonRestaurantNames = #"\bnails?\b|assisted living|gun (?:club|range|shop|store)|shooting range|firearms|petroleum|\bauto (?:repair|parts)\b"#

    static func nonRestaurants(_ places: [Place]) -> [String] {
        places.filter { !$0.isVenue && $0.name.range(of: nonRestaurantNames, options: [.regularExpression, .caseInsensitive]) != nil }
            .map { "\($0.name) [\($0.id)]" }
    }

    /// every website string in the bundled region detail files, as written (decoding to URL can quietly percent-encode a space)
    static func bundledWebsites() throws -> [(id: String, url: String)] {
        let files = (Bundle.main.urls(forResourcesWithExtension: "json", subdirectory: nil) ?? []).filter { $0.lastPathComponent.hasPrefix("detail-") }
        return try files.flatMap { url -> [(id: String, url: String)] in
            let d = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any] ?? [:]
            return d.compactMap { id, v in ((v as? [String: Any])?["w"] as? String).map { (id, $0) } }
        }
    }

    /// a website that isn't one link: text after it ("https://togoorder.com/web/1754#/ (Order Online)") or two links run together
    /// (QA 2026-10-28, P1 #7)
    static func notOneURL(_ links: [(id: String, url: String)]) -> [String] {
        links.filter { l in
            l.url.rangeOfCharacter(from: .whitespacesAndNewlines) != nil
                || l.url.range(of: #"(?i).[,;|]\s*(?:https?://|www\.)"#, options: .regularExpression) != nil
                || URL(string: l.url.contains("://") ? l.url : "https://" + l.url)?.host == nil   // as PlaceDetail.website reads it
        }.map { "[\($0.id)] \($0.url)" }
    }

    /// the same place twice: one name at one street address in one town, with pins a kilometre or more apart (QA 2026-10-28 found 17:
    /// an SCDA permit's ZIP-centroid or wrong-stretch point kept it from matching its own map listing)
    static func listedTwice(_ places: [Place]) -> [String] {
        let located = places.filter { $0.address != nil && $0.coordinate != nil }
        return Dictionary(grouping: located) { "\($0.name.lowercased())|\($0.address!.lowercased())|\($0.city ?? "")" }.values.flatMap { g -> [String] in
            let pins = g.map { CLLocation(latitude: $0.coordinate!.latitude, longitude: $0.coordinate!.longitude) }
            let apart = pins.indices.contains { i in pins.indices.contains { j in j > i && pins[i].distance(from: pins[j]) >= 1000 } }
            return apart ? g.map { "\($0.name) [\($0.id)]" } : []
        }
    }

    /// one pin for three or more house numbers a block or more apart: a geocoder's ZIP-code or street guess, not a place (Panera and four
    /// other permits sat on the 29203 centroid). A plaza's neighbors (11885, 11887 and 11891 Highway 707) can share a pin.
    static func guessedPins(_ places: [Place]) -> [String] {
        let located = places.filter { $0.coordinate != nil }
        return Dictionary(grouping: located) { p in
            "\(Int((p.coordinate!.latitude * 1e4).rounded())),\(Int((p.coordinate!.longitude * 1e4).rounded()))"
        }.values.flatMap { g -> [String] in
            let nums = Set(g.compactMap { p in p.address.flatMap { Int($0.prefix { $0.isNumber }) } })
            return nums.count >= 3 && nums.max()! - nums.min()! >= 100 ? g.map { "\($0.name) [\($0.id)]" } : []
        }
    }
}

/// pipeline/website_blocklist.json (hacked, taken-over, expired or another business's sites, confirmed by hand in the link sweeps):
/// no link on it may ship in any field of any JSON file the app bundles. The 2026-10-19 QA found the export had only filtered the
/// website field, or nothing, so hijacked links were still in the bundle. Read from the repo, so a new entry needs no code change.
final class LinkBlocklistTests: XCTestCase {
    func testNoBlocklistedLinkInBundledData() throws {
        let entries = try LinkBlocklist.entries()
        XCTAssertFalse(entries.isEmpty, "the blocklist is missing or empty")
        let files = LinkBlocklist.bundledJSON()
        XCTAssertFalse(files.isEmpty, "no bundled JSON found")
        var hits: [String] = []
        for url in files {
            let text = try String(contentsOf: url, encoding: .utf8)
            hits += LinkBlocklist.hits(in: text, entries).map { "\(url.lastPathComponent): \($0)" }
        }
        XCTAssertEqual(hits, [], "blocklisted links in the app's bundled data")
    }

    /// The guard fires on a copy of the bundled data broken three ways: a blocklisted domain, its subdomain, and a "url" entry.
    func testBlocklistGuardCatchesABrokenCopy() throws {
        let entries = try LinkBlocklist.entries()
        let file = try XCTUnwrap(LinkBlocklist.bundledJSON().max { (try? $0.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0) ?? 0 < (try? $1.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0) ?? 0 })
        let text = try String(contentsOf: file, encoding: .utf8)
        let domain = try XCTUnwrap(entries.first { ($0["match"] as? String ?? "domain") == "domain" }?["domain"] as? String)
        let fake: [[String: Any]] = entries + [["match": "url", "url": "https://example.org/hacked-page"]]
        let before = LinkBlocklist.hits(in: text, fake).count
        let broken = text + "{\"w\":\"https://www.\(domain)/menu\"}{\"src\":\"http://shop.\(domain)/\"}{\"w\":\"https://example.org/hacked-page/\"}"
        XCTAssertEqual(LinkBlocklist.hits(in: broken, fake).count, before + 3, "a domain, a subdomain and a url entry are all caught")
        XCTAssertEqual(LinkBlocklist.hits(in: "{\"w\":\"https://not\(domain)/\"}", entries), [], "a host that only ends with the domain's letters isn't it")
    }
}

enum LinkBlocklist {
    static func entries() throws -> [[String: Any]] {
        let url = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("pipeline/website_blocklist.json")
        return try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [[String: Any]])
    }

    /// every .json file in the app bundle, subfolders included
    static func bundledJSON() -> [URL] {
        let root = Bundle.main.bundleURL
        let all = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { $0.pathExtension == "json" && !$0.path.contains("/PlugIns/") }
    }

    private static func host(_ u: URLComponents) -> String {
        var h = (u.host ?? "").lowercased()
        if h.hasSuffix(".") { h.removeLast() }
        return h.hasPrefix("www.") ? String(h.dropFirst(4)) : h
    }

    private static func trimmedPath(_ p: String) -> String { p.hasSuffix("/") ? String(p.dropLast()) : p }

    /// the links in a JSON text that an entry covers: a "domain" entry its domain and subdomains, a "url" entry that page only
    static func hits(in text: String, _ entries: [[String: Any]]) -> [String] {
        let t = text.replacingOccurrences(of: "\\/", with: "/")
        let rx = try! NSRegularExpression(pattern: #"https?://[^"\s\\]+"#, options: [.caseInsensitive])
        return rx.matches(in: t, range: NSRange(t.startIndex..., in: t)).compactMap { m -> String? in
            let s = String(t[Range(m.range, in: t)!])
            guard let u = URLComponents(string: s) else { return nil }
            let h = host(u)
            for e in entries {
                if (e["match"] as? String ?? "domain") == "url" {
                    guard let v = URLComponents(string: e["url"] as? String ?? "") else { continue }
                    if !h.isEmpty && h == host(v) && trimmedPath(u.path) == trimmedPath(v.path) { return s }
                } else {
                    var d = (e["domain"] as? String ?? "").lowercased()
                    if let r = d.range(of: "://") { d = String(d[r.upperBound...]) }
                    d = String(d.split(separator: "/").first ?? "")
                    if d.hasPrefix("www.") { d = String(d.dropFirst(4)) }
                    if !d.isEmpty && (h == d || h.hasSuffix("." + d)) { return s }
                }
            }
            return nil
        }
    }
}

/// QA 2026-10-19, P1 3a: the support address is nick@eatsranked.com (Nick, 2026-10-12). The old Gmail address must not come back
/// anywhere in the app's source or bundled files.
final class SupportEmailTests: XCTestCase {
    func testSupportEmailIsEatsRanked() {
        XCTAssertEqual(Links.supportEmail, "nick@eatsranked.com")
    }

    func testNoGmailInAppSource() throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("SouthCarolinaEats")
        XCTAssertGreaterThan(SupportEmailScan.textFiles(under: root).count, 5, "the app's source folder wasn't found")
        XCTAssertEqual(SupportEmailScan.hits(under: root), [], "the app's source still has a Gmail address")
    }

    /// The guard fires on a broken copy: a folder with one planted Gmail address.
    func testGmailGuardCatchesABrokenCopy() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir.appendingPathComponent("App"), withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        try "static let supportEmail = \"someone@GMAIL.com\"\n".write(to: dir.appendingPathComponent("App/Links.swift"), atomically: true, encoding: .utf8)
        try "{\"ok\": \"nick@eatsranked.com\"}".write(to: dir.appendingPathComponent("App/data.json"), atomically: true, encoding: .utf8)
        XCTAssertEqual(SupportEmailScan.hits(under: dir), ["App/Links.swift"])
    }
}

enum SupportEmailScan {
    static let textExtensions: Set<String> = ["swift", "plist", "json", "strings", "xcstrings", "xcprivacy", "md", "txt", "html", "entitlements"]

    static func textFiles(under root: URL) -> [URL] {
        let all = FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { textExtensions.contains($0.pathExtension.lowercased()) }
    }

    /// paths (relative to root) of text files that mention gmail.com, in any case
    static func hits(under root: URL) -> [String] {
        let base = root.resolvingSymlinksInPath().path + "/"
        return textFiles(under: root).compactMap { url in
            guard let text = try? String(contentsOf: url, encoding: .utf8),
                  text.range(of: "gmail.com", options: .caseInsensitive) != nil else { return nil }
            return url.resolvingSymlinksInPath().path.replacingOccurrences(of: base, with: "")
        }.sorted()
    }
}

/// QA 2026-10-19, P1 #13: outbound links ship without tracking tags (ref=google, referrer=google_food_ordering, cn_channel, utm_* …).
/// pipeline/tracking_params.py strips them in the export; these are the same rules.
final class TrackingParamTests: XCTestCase {
    func testNoTrackingParametersInBundledLinks() throws {
        let files = TrackingParams.bundledJSON()
        XCTAssertFalse(files.isEmpty, "no bundled JSON found")
        var hits: [String] = []
        for url in files {
            let text = try String(contentsOf: url, encoding: .utf8)
            hits += TrackingParams.tracked(in: text).map { "\(url.lastPathComponent): \($0)" }
        }
        XCTAssertEqual(hits, [], "links with tracking parameters in the app's bundled data")
    }

    /// The guard fires on a broken copy (nine kinds of tracking tag, two in escaped JSON) and leaves a store's own parameters, page
    /// anchors and single-page routes alone.
    func testTrackingGuardCatchesABrokenCopy() {
        let broken = #"[{"w":"https:\/\/places.example.com\/menu?ref=google"},{"w":"https://a.example/?utm_source=gmb&store=4"},"#
            + #"{"w":"https://b.example/x?referrer=google_food_ordering"},{"w":"https://c.example/order/1?cn_channel=cn_google"}]"#
        XCTAssertEqual(TrackingParams.tracked(in: broken).count, 4)
        // QA 2026-10-28: after "#" (Hard Rock Myrtle Beach's Yext tag), a route's own query, written into the path, a link without a
        // scheme, and Klaviyo's _kx
        let more = #"[{"w":"https:\/\/cafe.hardrock.com\/myrtle-beach\/#utm_source=rest_of_network&utm_medium=Yext"},"#
            + #"{"w":"https://order.example.com/#/menu?utm_source=fb&table=4"},"#
            + #"{"w":"https://www.snoozeeatery.com/restaurant/georgia/alpharetta/utm_source=Facebook&utm_medium=BusinessListing"},"#
            + #"{"w":"instagram.com\/sharks1413_macon?igshid=NjNlMDhmYTc%3D"},{"w":"https://shop.example.com/pages/event?_kx=aSsBlo5n7gs8"}]"#
        XCTAssertEqual(TrackingParams.tracked(in: more).count, 5)
        let clean = #"[{"w":"https://order.example.com/menu?restaurantId=51&location=7"},{"w":"https://shop.example.com/?cid=12&ref=gs"},"#
            + #"{"w":"https://togoorder.com/web/1754#/"},{"w":"https://order.example.com/#/store?id=9"},{"w":"https://example.com/p/id=5"},"#
            + #"{"w":"www.example.com/menu?page=2"},{"w":"https://example.com/#menu"}]"#
        XCTAssertEqual(TrackingParams.tracked(in: clean), [])
    }
}

enum TrackingParams {
    /// tracking by name, whatever the value
    static let keys = try! NSRegularExpression(pattern: #"^(?:utm[_-].*|gclid|gbraid|wbraid|dclid|fbclid|msclkid|mc_cid|mc_eid|_ga|_gl|_kx|igsh|"#
        + #"igshid|mibextid|srsltid|cn_channel|y_source|rwg_token|olonwp|ost_redirect_attribution|cmpid|yext_?.*)$"#, options: [.caseInsensitive])
    /// tracking only with these values
    static let values: [String: String] = ["ref": #"^(?:google|gmb|gbp|yext|bookmarks)\b"#, "referrer": "^google",
                                           "source": #"^(?:google|gmb|gbp|yext)\b"#, "cid": "^RF:YXT", "cmp": "^OKC-"]

    /// every .json file in the app bundle, subfolders included
    static func bundledJSON() -> [URL] {
        let all = FileManager.default.enumerator(at: Bundle.main.bundleURL, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
        return all.filter { $0.pathExtension == "json" && !$0.path.contains("/PlugIns/") }
    }

    static func isTracking(_ key: String, _ value: String) -> Bool {
        let k = key.trimmingCharacters(in: .whitespaces)
        if keys.firstMatch(in: k, range: NSRange(k.startIndex..., in: k)) != nil { return true }
        guard let pattern = values[k.lowercased()] else { return false }
        return value.trimmingCharacters(in: .whitespaces).range(of: pattern, options: [.regularExpression, .caseInsensitive]) != nil
    }

    /// links in a JSON text that carry a tracking parameter: in the query, after "#" (Yext's "…/#utm_source=…", or a route's own
    /// "#/menu?utm_source=…"), written into the path ("…/alpharetta/utm_source=Facebook&…"), or on a link stored without a scheme
    /// ("instagram.com/x?igshid=…"); the rules of pipeline/tracking_params.py since QA 2026-10-28
    static func tracked(in text: String) -> [String] {
        let t = text.replacingOccurrences(of: "\\/", with: "/").replacingOccurrences(of: "&amp;", with: "&")
        let rx = try! NSRegularExpression(pattern: #"(?i)https?://[^\s"'<>\\]+|(?<![\w/.:@-])(?:[a-z0-9-]+\.)+[a-z]{2,}/[^\s"'<>\\]*"#)
        return rx.matches(in: t, range: NSRange(t.startIndex..., in: t)).compactMap { m -> String? in
            let s = String(t[Range(m.range, in: t)!])
            let bare = s.replacingOccurrences(of: #"^(?i)https?://"#, with: "", options: .regularExpression)
            let (beforeHash, fragment) = cut(bare, at: "#")
            let (path, query) = cut(beforeHash, at: "?")
            var groups = [query]
            if fragment.contains("=") { groups.append(fragment.components(separatedBy: "?").last ?? "") }
            groups += path.split(separator: "/").dropFirst().map(String.init).filter { $0.contains("=") }   // the host comes first
            return groups.contains(where: carriesTracking) ? s : nil
        }
    }

    private static func cut(_ s: String, at sep: Character) -> (String, String) {
        guard let i = s.firstIndex(of: sep) else { return (s, "") }
        return (String(s[..<i]), String(s[s.index(after: i)...]))
    }

    private static func carriesTracking(_ params: String) -> Bool {
        params.split(separator: "&").contains { part in
            let kv = part.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
            let k = String(kv[0]).replacingOccurrences(of: "+", with: " ").removingPercentEncoding ?? String(kv[0])
            let v = kv.count > 1 ? (String(kv[1]).replacingOccurrences(of: "+", with: " ").removingPercentEncoding ?? String(kv[1])) : ""
            return isTracking(k, v)
        }
    }
}

/// The app ships no Google-derived data at all (STATE_EATS_PLAYBOOK.md): no ratings, review counts or price levels, and no number
/// computed from them either. Oregon's and South Carolina's first app exports still carried calibration's "google21_open" (the share of
/// a listing group Google's 2021 snapshot showed as open), so every key in every bundled JSON file is checked, at any depth.
final class NoGoogleDataTests: XCTestCase {
    /// a key that names Google or something only Google's snapshot supplies
    static let googleKey = try! NSRegularExpression(pattern: "google|rating|review|gmap|price|in21|closed21", options: [.caseInsensitive])

    /// every Google-derived key in a decoded JSON value, as "path.key"
    static func googleKeys(in value: Any, path: String = "") -> [String] {
        if let d = value as? [String: Any] {
            return d.flatMap { k, v -> [String] in
                let here = path.isEmpty ? k : path + "." + k
                let hit = googleKey.firstMatch(in: k, range: NSRange(k.startIndex..., in: k)) != nil ? [here] : []
                return hit + googleKeys(in: v, path: here)
            }
        }
        if let a = value as? [Any] { return a.flatMap { googleKeys(in: $0, path: path + "[]") } }
        return []
    }

    func testNoGoogleDerivedKeyInBundledData() throws {
        let files = Bundle.main.urls(forResourcesWithExtension: "json", subdirectory: nil) ?? []
        XCTAssertFalse(files.isEmpty, "no bundled JSON found")
        var hits = Set<String>()
        for url in files {
            let value = try JSONSerialization.jsonObject(with: Data(contentsOf: url))
            for k in Self.googleKeys(in: value) { hits.insert(url.lastPathComponent + ": " + k) }
        }
        XCTAssertEqual(hits.sorted(), [], "Google-derived data in the app bundle")
    }

    /// The guard fires on a copy broken the way the first export was (a calibration group with google21_open) and on a place rating.
    func testGuardCatchesABrokenCopy() {
        let broken: [String: Any] = ["calibration": ["South Carolina (statewide)": ["groups": ["meta_high": ["n": 9854, "official": 0.784, "google21_open": 0.699]]]],
                                     "places": [["id": "x", "n": "Somewhere", "rating": 4.5]]]
        XCTAssertEqual(Set(Self.googleKeys(in: broken).map { $0.components(separatedBy: ".").last! }), ["google21_open", "rating"])
        XCTAssertEqual(Self.googleKeys(in: ["calibration": ["South Carolina (statewide)": ["groups": ["meta_high": ["n": 1, "official": 0.8]]]]]), [],
                       "the calibration the app needs passes")
    }
}
