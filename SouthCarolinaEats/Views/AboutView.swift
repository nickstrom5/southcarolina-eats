import SwiftUI

struct AboutView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("SOUTH CAROLINA EATS").displayFont(32).foregroundStyle(Theme.green)
                    Text("A free guide to \(model.restaurantCount.formatted()) South Carolina restaurants, with the SC Department of Agriculture's posted inspection grades, the MICHELIN Guide American South and James Beard honors, and hand-checked lists of South Carolina's own food as the research lands. No account, no ads, no tracking.")
                        .font(.subheadline).foregroundStyle(Theme.ink2)
                    Text("South Carolina Eats is an independent app by Nicholas Soderstrom. It is not affiliated with, endorsed by or operated by the State of South Carolina, the SC Department of Agriculture, the SC Department of Public Health, the SC Department of Revenue, any county or city, the MICHELIN Guide, the James Beard Foundation, Clemson University, the University of South Carolina, Apple, or any restaurant or chain. Other names are trademarks of their owners.")
                        .font(.footnote).foregroundStyle(Theme.muted)
                }
                .padding(.vertical, 4)
            }
            Section("How the lists are built") {
                Text("Hand-checked lists (and the oldest-places list) include only places checked against a 2025 or 2026 source (the place's own website or menu, local news, an official tourism listing or a 2025–26 SCDA inspection), with the address checked. Founding years mean the year it opened at this address.")
                Text("Honors are the MICHELIN Guide American South 2026 selection for South Carolina (stars, Bib Gourmands and Recommended) and James Beard Foundation awards and nominations, plus America's Classics.")
                Text("Places start from open map listings (Overture Maps), checked against the SC Department of Agriculture's statewide list of permitted retail food establishments: high-confidence listings matched an open permit \(rate("meta_high")) of the time, and the app keeps the kinds that proved reliable. Places matched to an open permit are marked official, and permitted restaurants the map data missed are added. Adult clubs are left out. Website links are checked, and any that no longer belong to the place are left out.")
                Text("Inspection grades are SCDA's own, as posted at each establishment: A above 87 points, B 78–87, C below 78. The posted grade can differ from the inspection's score (8-403.10(G) of Regulation 61-25), and SC Food Grades publishes the grade, not the score, so this app shows the grade as posted, with its date, and computes none.")
                Text("Ratings, reviews, hours and photos are Apple Maps' own, shown live in Apple's place card. This app doesn't store or rank by them.")
            }
            .font(.subheadline).foregroundStyle(Theme.ink2)
            Section("Sources") {
                source("SC Department of Agriculture", "Retail food permits and inspections under Regulation 61-25, from SC Food Grades (apps.dhec.sc.gov/Environment/FoodGrades/, maintained by the SC Department of Public Health for SCDA), read \(DayFormat.text(model.inspectionsPublished["scda"]) ?? ""); records through \(DayFormat.text(model.inspectionsThrough["scda"]) ?? ""), shown as published; modified for use in this app. SCDA's note: \u{201C}Information provided in the application is intended to be used for general reference. SCDA provides no warranty, expressed or implied, as to the accuracy, reliability or completeness of furnished data. This database includes all permitted retail food establishments, some of which are not open to the general public for dining.\u{201D}", Links.foodGrades.absoluteString)
                source("How SCDA grades", "SCDA's explanation of risk-based inspections and the A, B and C grades (agriculture.sc.gov).", Links.scdaGrades.absoluteString)
                source("Overture Maps Foundation", "Restaurant listings and websites come from Overture Maps Foundation places data (overturemaps.org)\(model.overtureRelease.map { ", release \($0)" } ?? ""), filtered and reformatted for this app.\n• Data from Meta, Microsoft, DAC and BrightQuery. Available under CDLA Permissive 2.0.\n• Data from Foursquare. \(foursquareCopyright) Available under Apache 2.0. Foursquare data was transformed to the Overture schema; this app further filtered and reformatted it. See the NOTICE below.\n• Data from AllThePlaces. Available under CC0 1.0.", "https://overturemaps.org")
                source("Honors", "MICHELIN Guide distinctions and James Beard Foundation awards, finalists and America's Classics are reported as facts and checked by hand against the Guide's and the Foundation's own announcements. MICHELIN and the MICHELIN Guide are trademarks of Michelin. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Other names belong to their owners.", "https://www.jamesbeard.org/awards")
                source("Maps", "Maps, place cards and directions by Apple Maps.", nil)
            }
            Section("Licenses") {
                NavigationLink("Community Data License Agreement – Permissive 2.0") { LicenseText(file: "CDLA-Permissive-2.0", title: "CDLA Permissive 2.0") }
                NavigationLink("Apache License 2.0") { LicenseText(file: "Apache-2.0", title: "Apache License 2.0") }
                NavigationLink("Foursquare OS Places NOTICE") { LicenseText(file: "Foursquare-NOTICE", title: "Foursquare NOTICE") }
            }
            Section("Privacy") {
                Text("The app collects nothing. Your location, if you allow it, only sorts lists by distance and shows where you are on the map, on this device. Saved places stay on this device.")
                    .font(.subheadline).foregroundStyle(Theme.ink2)
                DataUpdatesNote()
                    .font(.footnote).foregroundStyle(Theme.muted)
                Link("Privacy policy", destination: Links.privacy)
                Link("Terms of use", destination: Links.terms)
            }
            Section("Help") {
                Link("Report a missing or closed place", destination: Links.correctionEmail)
                Link("Email \(Links.supportEmail)", destination: URL(string: "mailto:\(Links.supportEmail)")!)
                Link("Website", destination: Links.site)
                Text("Data as of \(DayFormat.text(model.generated) ?? model.generated). Places open and close; check before you go. Version \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0")")
                    .font(.footnote).foregroundStyle(Theme.muted)
            }
        }
        .navigationTitle("About")
        .tint(Theme.green)
    }

    /// the copyright line exactly as the bundled Foursquare NOTICE has it, so the two can't disagree
    private var foursquareCopyright: String {
        guard let url = Bundle.main.url(forResource: "Foursquare-NOTICE", withExtension: "txt"),
              let text = try? String(contentsOf: url, encoding: .utf8),
              let line = text.split(separator: "\n").first(where: { $0.hasPrefix("©") }) else { return "© Foursquare Labs, Inc. All rights reserved." }
        return line.trimmingCharacters(in: .whitespaces)
    }

    private func rate(_ group: String) -> String {
        guard let v = model.calibration.areas[Calibration.statewide]?.groups[group]?.official else { return "most" }
        return "\(Int((v * 100).rounded()))%"
    }

    @ViewBuilder
    private func source(_ name: String, _ detail: String, _ url: String?) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            if let url, let u = URL(string: url) { Link(name, destination: u).font(.subheadline.weight(.semibold)) }
            else { Text(name).font(.subheadline.weight(.semibold)) }
            Text(detail).font(.caption).foregroundStyle(Theme.muted)
        }
    }
}

/// A bundled license text (Resources/Licenses), reflowed rather than shown as raw 80-column lines.
struct LicenseText: View {
    let file: String
    let title: String

    var body: some View {
        ScrollView {
            Text(text).font(.footnote).foregroundStyle(Theme.ink).textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading).padding()
        }
        .inlineTitle(title)
    }

    private var text: String {
        guard let url = Bundle.main.url(forResource: file, withExtension: "txt"),
              let raw = try? String(contentsOf: url, encoding: .utf8) else { return "License text missing." }
        // join hard-wrapped lines into paragraphs; keep blank lines and list items as breaks
        var out: [String] = []
        for para in raw.components(separatedBy: "\n\n") {
            let lines = para.components(separatedBy: "\n").map { $0.trimmingCharacters(in: .whitespaces) }
            var joined = ""
            for l in lines where !l.isEmpty {
                let startsItem = l.hasPrefix("–") || l.hasPrefix("-") || l.range(of: #"^\(?[a-z0-9]{1,3}[.)]\s"#, options: .regularExpression) != nil
                joined += joined.isEmpty ? l : (startsItem ? "\n" + l : " " + l)
            }
            if !joined.isEmpty { out.append(joined) }
        }
        return out.joined(separator: "\n\n")
    }
}
