import Foundation

/// Every outside link the app opens, in one place. Each official page was checked to render (2026-10-26: SC Food Grades and the
/// report PDFs with curl, agriculture.sc.gov in the browser pane, since it answers plain curl with a Cloudflare 403). Never scdhec.gov.
/// The site is GitHub Pages at the project address until southcarolina.eatsranked.com resolves (Nick adds a Cloudflare CNAME
/// southcarolina -> nickstrom5.github.io, DNS only; then scripts/make-site.py sets CUSTOM_DOMAIN). GitHub forwards these github.io
/// addresses to the custom domain once it's set, so a build with them keeps working.
enum Links {
    static let site = URL(string: "https://nickstrom5.github.io/southcarolina-eats/")!
    /// The app's data updates: scripts/publish_app_data.py writes docs/data/app/ (OTA-DATA.md).
    static let appData = URL(string: site.absoluteString + "data/app/")!
    static let privacy = URL(string: "https://nickstrom5.github.io/southcarolina-eats/privacy.html")!
    static let terms = URL(string: "https://nickstrom5.github.io/southcarolina-eats/terms.html")!
    /// SC Food Grades (maintained by the SC Department of Public Health for SCDA): SCDA's inspections, searchable
    static let foodGrades = URL(string: "https://apps.dhec.sc.gov/Environment/FoodGrades/")!
    /// SCDA's own explanation of the grades (A above 87, B 78-87, C below 78; 8-403.10(G))
    static let scdaGrades = URL(string: "https://agriculture.sc.gov/permits-and-inspections/retail-food-safety/understanding-restaurant-inspections/")!
    static let supportEmail = "nick@eatsranked.com"
    static var correctionEmail: URL {
        URL(string: "mailto:\(supportEmail)?subject=South%20Carolina%20Eats%20correction")!
    }

    // MARK: Share

    /// The web app. It opens a place's panel from the hash, explore/#p=<id> (readHash in scripts/explore.js), using the app's ids.
    static let explore = URL(string: site.absoluteString + "explore/")!

    /// Whether the web app lists the place: make-site.py's rule (restaurants only; the venues the app hides by default, such as
    /// stadium stands and gas-station counters, stay out).
    static func onWeb(_ place: Place) -> Bool { !place.isVenue }

    /// What Share sends: the place's own page in the web app, never an Apple Maps or Google link (Apple Maps has its own button).
    /// The id is escaped the way the page's encodeURIComponent would escape it. A place the web app leaves out gets the web app's
    /// front page, never a #p= link that opens nothing (a unit test checks the ids against docs/data).
    static func share(_ place: Place) -> URL {
        guard onWeb(place), let id = place.id.addingPercentEncoding(withAllowedCharacters: uriComponent),
              let url = URL(string: explore.absoluteString + "#p=" + id) else { return explore }
        return url
    }

    /// The text that goes with the link: the place, its town and the app. No street address, which Messages turns into a Maps link.
    static func shareMessage(_ place: Place) -> String {
        [place.name, place.city ?? ""].filter { !$0.isEmpty }.joined(separator: ", ") + ", on South Carolina Eats"
    }

    /// What encodeURIComponent leaves as is.
    private static let uriComponent = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~*'()")
}
