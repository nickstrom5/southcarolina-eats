"""Official South Carolina records -> data/raw/official/ (git-ignored). Every host was robots-checked first (check_sources.py).

SC Department of Agriculture (SCDA) Retail Food Safety inspects retail food establishments statewide under Regulation 61-25 (since
July 1, 2024; DHEC before). SC Food Grades (apps.dhec.sc.gov/Environment/FoodGrades/, run by SC DPH for SCDA) draws its map from a public
ArcGIS Online feature service, read here through its documented REST API: at most 2,000 rows a request, one request at a time.

- Layer 0 "Restaurants": one row per permit (name, address, city, zip, program code, latest inspection date), points in UTM 17N, so
  outSR=4326 is requested.
- Table 4 "Restaurants_Steton": one row per inspection for the last three years: posted grade, date, inspection type, report id
  (AuditResultGlobalID, the report PDF at pubdoc.dhec.sc.gov/inspection/<id>.pdf). SCORE is empty on every row, so no score is used.
"""
import json, os, sys, time
import requests

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "official")
UA = {"User-Agent": "SouthCarolinaEatsBuild/1.0 (+nick@eatsranked.com)"}
BASE = "https://services5.arcgis.com/G4BLIH7rTQoIjCFv/arcgis/rest/services/Restaurants/FeatureServer"
os.makedirs(OUT, exist_ok=True)


def page(layer, extra):
    """Every row of one layer, 2,000 a request, serially (the service's maxRecordCount)."""
    rows, off = [], 0
    while True:
        params = {"where": "1=1", "outFields": "*", "f": "json", "resultOffset": off, "resultRecordCount": 2000,
                  "orderByFields": "OBJECTID", **extra}
        for attempt in range(4):
            try:
                r = requests.get(f"{BASE}/{layer}/query", params=params, headers=UA, timeout=120)
                r.raise_for_status()
                d = r.json()
                if "error" in d:
                    raise RuntimeError(d["error"])
                break
            except (requests.RequestException, RuntimeError, ValueError) as e:
                if attempt == 3:
                    raise
                print("retry", layer, off, e, flush=True)
                time.sleep(10 * (attempt + 1))
        got = d.get("features", [])
        rows += got
        print(layer, off, len(got), flush=True)
        if not got or not d.get("exceededTransferLimit"):
            break
        off += len(got)
        time.sleep(1)
    return rows


def permits():
    feats = page(0, {"outSR": 4326, "returnGeometry": "true"})
    json.dump({"fetched": time.strftime("%Y-%m-%d"), "source": f"{BASE}/0", "features": feats},
              open(f"{OUT}/sc_permits.json", "w"))
    print("permits", len(feats))


def inspections():
    feats = page(4, {"returnGeometry": "false"})
    json.dump({"fetched": time.strftime("%Y-%m-%d"), "source": f"{BASE}/4", "features": feats},
              open(f"{OUT}/sc_inspections.json", "w"))
    print("inspections", len(feats))


if __name__ == "__main__":
    for w in sys.argv[1:] or ["permits", "inspections"]:
        globals()[w]()
