import CoreLocation
import Observation
import UIKit

/// "Near me" sorting. Asks for when-in-use permission only when a list is sorted by distance or "My location" is tapped; the location never leaves the device.
@MainActor
@Observable
final class LocationService: NSObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    private(set) var location: CLLocation?
    private(set) var status: CLAuthorizationStatus = .notDetermined
    /// no fix within 12 seconds, or Core Location reported an error
    private(set) var failed = false
    private var timeout: Task<Void, Never>?
    /// when the current request started: a fix from before it is a cached one (from launch, or before a drive) and doesn't count
    private var askedAt = Date.distantPast

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        status = manager.authorizationStatus
    }

    var isDenied: Bool { status == .denied || status == .restricted }

    /// Every place is in South Carolina, so a reader elsewhere (an App Reviewer in California, say) gets told rather than an empty
    /// map. A coarse outline of the state (Idaho's lesson: a bounding box would count Charlotte's suburbs), drawn a little outside the
    /// line so the barrier islands and border towns count as inside.
    var isOutsideState: Bool {
        guard let c = location?.coordinate else { return false }
        return !StateOutline.contains(c)
    }

    /// Once location is off for the app, iOS won't ask again; the app's page in Settings is the only way back.
    static func openSettings() {
        if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) }
    }

    func request() {
        switch manager.authorizationStatus {
        case .notDetermined: manager.requestWhenInUseAuthorization()
        case .authorizedWhenInUse, .authorizedAlways: locate()
        default: break
        }
    }

    private func locate() {
        failed = false
        let asked = Date()
        askedAt = asked
        manager.requestLocation()
        timeout?.cancel()
        timeout = Task { [weak self] in
            try? await Task.sleep(for: .seconds(12))
            guard let self, !Task.isCancelled else { return }
            if (self.location?.timestamp ?? .distantPast) < asked { self.failed = true }
        }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ m: CLLocationManager) {
        let s = m.authorizationStatus
        Task { @MainActor in
            self.status = s
            if s == .authorizedWhenInUse || s == .authorizedAlways { self.locate() }
        }
    }

    nonisolated func locationManager(_ m: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let l = locations.last else { return }
        Task { @MainActor in
            // "My location" needs a fresh fix on every tap: a cached one from before the request would put you back where you were
            guard l.timestamp >= self.askedAt.addingTimeInterval(-2) else { return }
            self.location = l; self.failed = false; self.timeout?.cancel()
        }
    }

    nonisolated func locationManager(_ m: CLLocationManager, didFailWithError error: Error) {
        Task { @MainActor in if self.location == nil { self.failed = true } }
    }
}

extension CLLocation {
    /// "0.4 mi", "12 mi", "1,012 mi" (an App Reviewer in California is a thousand miles out)
    func milesText(to other: CLLocation) -> String {
        let mi = distance(from: other) / 1609.344
        return (mi < 10 ? mi.formatted(.number.precision(.fractionLength(1))) : Int(mi.rounded()).formatted()) + " mi"
    }
}

/// A coarse South Carolina outline (longitude, latitude), 35 points, drawn about 4 km outside the line (from Overture's state division,
/// buffered and simplified; pipeline/fetch_overture.py writes the full outline), so the barrier islands (Hilton Head, Daufuskie, Fripp,
/// Edisto, Folly, Sullivan's) and the border towns (Fort Mill, North Augusta, Hardeeville, Little River) count as inside.
enum StateOutline {
    static let ring: [(Double, Double)] = [
        (-83.39, 34.71), (-83.34, 34.84), (-83.13, 35.04), (-82.40, 35.25), (-81.03, 35.19), (-80.99, 35.12), (-80.91, 35.14), (-80.75, 34.96),
        (-80.75, 34.86), (-79.66, 34.84), (-78.50, 33.84), (-78.91, 33.61), (-79.10, 33.38), (-79.16, 33.15), (-79.34, 32.98), (-79.55, 32.98),
        (-79.55, 32.88), (-79.86, 32.65), (-80.40, 32.43), (-80.43, 32.29), (-80.63, 32.22), (-80.83, 32.00), (-80.92, 32.00), (-81.15, 32.10),
        (-81.25, 32.46), (-81.45, 32.61), (-81.55, 33.00), (-81.78, 33.12), (-81.97, 33.32), (-81.97, 33.44), (-82.21, 33.59), (-82.35, 33.79),
        (-82.59, 33.92), (-82.91, 34.44), (-83.09, 34.47)]

    /// Ray casting: a point is inside when a ray east of it crosses the outline an odd number of times.
    static func contains(_ c: CLLocationCoordinate2D) -> Bool {
        var inside = false
        var j = ring.count - 1
        for i in 0..<ring.count {
            let (xi, yi) = ring[i], (xj, yj) = ring[j]
            if (yi > c.latitude) != (yj > c.latitude) && c.longitude < (xj - xi) * (c.latitude - yi) / (yj - yi) + xi { inside.toggle() }
            j = i
        }
        return inside
    }
}
