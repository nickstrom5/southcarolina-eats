"""How often is a map listing a real, permitted food business? Measured against SCDA's statewide permit list -> data/sc/calibration*.json

Adapted from or-eats/pipeline/calibrate.py. South Carolina has one statewide list: every retail food establishment SCDA permits under
Regulation 61-25 (SC Food Grades' feature service, official.py). The test uses open Retail Food Establishment permits (PROG_CODE 206,
inspected since official.ACTIVE_SINCE; schools, hospitals, jails and caterers by name left out). Mobile units, institutions and grocery
stores are other programs.
- Match rate: the share of each listing group that matches an open retail-food permit. Bars that serve no food may hold no food permit,
  so "bar" listings undercount a little.
- Coverage: the share of open retail-food permits found among the open map listings. Those permits include convenience-store and
  grocery counters, hotel kitchens and clubs, so the share named like a place to eat (official.FOODY) is reported too.
- Google 2021 open: the share of each group also listed as open by Google in Sep 2021 (UCSD snapshot, web build only).
A match is the same business name nearby, or the same street address with a distinctive name word in common.
"""
import json
import numpy as np, pandas as pd
from shapely.geometry import shape, Point
from common import SC
from listings_util import official_match
import official

o = pd.read_pickle(f"{SC}/stage1.pkl")
F = pd.read_pickle(f"{SC}/official.pkl")
from shapely import STRtree
_CN = json.load(open(f"{SC}/sc_counties_detail.geojson"))
_NAMES = list(_CN)
_GEOMS = [shape(_CN[n]).buffer(0.0003) for n in _NAMES]
_TREE = STRtree(_GEOMS)


def county_of(la, lo):
    if la != la:
        return None
    p = Point(lo, la)
    for i in _TREE.query(p):
        if _GEOMS[i].contains(p):
            return _NAMES[i]
    return None


o["county"] = [county_of(la, lo) for la, lo in zip(o.lat, o.lon)]
# a permit carries its county in its number; a point outside every outline (a pier) keeps that, and so does a weak point (a street
# range or the Census geocoder's, geocode_official.py), which can land across a county line
F["county"] = [(None if w == True else county_of(la, lo)) or (c if isinstance(c, str) and c else None)
               for la, lo, c, w in zip(F.lat, F.lon, F.get("county", pd.Series([None] * len(F))), F.get("weak", pd.Series([False] * len(F))))]
o.to_pickle(f"{SC}/stage1.pkl")
F.to_pickle(f"{SC}/official.pkl")
base = ~o.j_junk & ~o.j_outside
print("listings with a county:", int(o.county.notna().sum()), "of", len(o))


def groups(L, app=False):
    s = L.src.fillna("none")
    if app:
        conf = L.confidence.fillna(0)
        return np.select([L.ov_closed | L.j_closedname, (s == "meta") & (conf >= 0.95), (s == "meta") & (conf >= 0.9),
                          s.isin(["AllThePlaces", "DAC"]), (s == "BrightQuery") & (conf >= 0.95), s == "meta"],
                         ["closed per Overture/name", "meta_high", "meta_mid", "brand_feed", "bq_high", "meta_low"], "other_sources")
    return np.select([L.closed21, L.ov_closed, (s == "meta") & L.in21, s == "meta", s.isin(["AllThePlaces", "DAC"]) & L.in21,
                      s.isin(["AllThePlaces", "DAC"]), L.in21, s == "Foursquare", s == "BrightQuery", s == "Microsoft"],
                     ["Google 2021 says closed", "Overture says closed", "Meta + open in Google 2021", "Meta only",
                      "brand feed + Google 2021", "brand feed only", "Foursquare/BrightQuery/Microsoft + Google 2021",
                      "Foursquare only", "BrightQuery only", "Microsoft only"], "other")


OPEN_FOOD = F.active & F.kind.eq("food")
foody = F["name"].fillna("").map(lambda n: bool(official.FOODY.search(n)))
AREAS = {"South Carolina (statewide)": None, "Charleston County": "Charleston County", "Greenville County": "Greenville County",
         "Richland County (Columbia)": "Richland County", "Horry County (Grand Strand)": "Horry County"}
res, app = {}, {}
PER = None
for label, cty in AREAS.items():
    L = o[base & (o.county.notna() if cty is None else o.county == cty)].reset_index(drop=True)
    R = F[OPEN_FOOD & (F.county.notna() if cty is None else F.county == cty)].reset_index(drop=True)
    Rfoody = foody[OPEN_FOOD & (F.county.notna() if cty is None else F.county == cty)].reset_index(drop=True)
    m = {}
    for c_, gl in L.groupby("county").groups.items():   # county by county: "100 Main St" exists in dozens of towns
        gr = R.index[R.county == c_]
        if not len(gr):
            continue
        for i_, j_ in official_match(L.loc[gl].reset_index(drop=True), R.loc[gr].reset_index(drop=True)).items():
            m[gl[i_]] = gr[j_]
    L["hit"] = L.index.map(lambda i: i in m)
    L["g_open"] = L.in21 & ~L.closed21
    for mode, store in ((False, res), (True, app)):
        L["grp"] = groups(L, mode)
        t = L.groupby("grp").agg(n=("id", "size"), scda=("hit", "mean"), g_open=("g_open", "mean")).sort_values("n", ascending=False)
        print(f"\n== {label} ({'app grouping' if mode else 'web grouping'}): {len(L)} listings, {len(R)} open retail-food permits")
        print(t.assign(scda=(t.scda * 100).round(1), g_open=(t.g_open * 100).round(1)).to_string())
        # the app ships no Google-derived number, so its copy leaves out google21_open (the web leaderboard keeps it)
        store[label] = {"listings": int(len(L)), "official_records": int(len(R)),
                        "groups": {g: {"n": int(r.n), "official": round(float(r.scda), 3)} | ({} if mode else {"google21_open": round(float(r.g_open), 3)})
                                   for g, r in t.iterrows()}}
    # the other direction: how many open permitted businesses do the (cleaned, open) map listings hold?
    keepish = ~(L.ov_closed | L.j_closedname | L.closed21)
    got = set(R.biz.iloc[[m[i] for i in L.index[keepish] if i in m]])
    Rb = R.drop_duplicates("biz")
    cover = float(np.mean([b in got for b in Rb.biz])) if len(Rb) else None
    Rf = R[Rfoody.values].drop_duplicates("biz")
    cover_f = float(np.mean([b in got for b in Rf.biz])) if len(Rf) else None
    print(f"{label}: open retail-food permits found among open map listings: {cover*100:.1f}% of {len(Rb)}; "
          f"named like a place to eat: {cover_f*100:.1f}% of {len(Rf)}")
    res[label].update({"coverage": round(cover, 3), "coverage_foodnamed": round(cover_f, 3), "official_food": int(len(Rb)),
                       "official_foodnamed": int(len(Rf))})
    if cty is None:
        per = L.groupby("county").agg(listings=("id", "size"), scda_match=("hit", "mean"))
        per["permits"] = Rb.groupby("county").size().reindex(per.index).fillna(0).astype(int)
        per["permits_found"] = [float(np.mean([b in got for b in Rb[Rb.county == c].biz])) if (Rb.county == c).any() else None for c in per.index]
        print("\n== per county\n" + per.sort_values("listings", ascending=False).round(3).to_string())
        PER = per

json.dump({"areas": res, "per_county": {c: {k: (round(float(v), 3) if isinstance(v, float) else int(v)) for k, v in r.items() if v == v}
                                          for c, r in PER.iterrows()},
           "unplaced_official_records": int(F.lat.isna().sum()), "scda_fetched": official.FETCHED, "scda_through": official.THROUGH,
           "scda_open_since": official.ACTIVE_SINCE},
          open(f"{SC}/calibration.json", "w"), indent=1)
json.dump(app, open(f"{SC}/calibration_app.json", "w"), indent=1)
