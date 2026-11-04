"""Place official records that have no coordinates on Overture address points (SCDA permits missing from the Food Grades map layer).

Match: same house number and street key, then the same zip (else the same town, else a single unambiguous point cluster).
-> data/sc/official.pkl (official.load() plus lat/lon/geo columns), data/sc/ap_index.pkl (address-point index, cached)
"""
import os, re, time, pickle, math
import numpy as np, pandas as pd
from common import SC, canon_city
import official
from official import street_key

t = time.time()
idx_path = f"{SC}/ap_index.pkl"
if os.path.exists(idx_path):
    AP = pd.read_pickle(idx_path)
else:
    AP = pd.read_parquet(f"{SC}/addresses_sc.parquet", columns=["number", "street", "postcode", "postal_city", "state", "muni", "lat", "lon"])
    AP = AP[AP.state.isin(["SC", None]) | AP.state.isna()]
    keys = [street_key(f"{n} {s}") for n, s in zip(AP.number.astype(str), AP.street.fillna(""))]
    AP["num"] = [k[0] for k in keys]
    AP["key"] = [k[1] for k in keys]
    AP["zip"] = AP.postcode.fillna("").astype(str).str[:5]
    AP["town"] = [(canon_city(re.sub(r"^(?:City|Town) of ", "", m)) or "").lower() if isinstance(m, str) else "" for m in AP.muni]
    AP["ptown"] = AP.postal_city.map(lambda c: (canon_city(c) or "").lower() if isinstance(c, str) else "")
    AP = AP[AP.num.notna() & AP.key.notna()][["num", "key", "zip", "town", "ptown", "lat", "lon"]].reset_index(drop=True)
    AP.to_pickle(idx_path)
print("address points:", len(AP), round(time.time() - t), "s", flush=True)
F = official.load()
# Texas had 11.5M address points (South Carolina 1.4M in the box): group only those at a house number and street some record needs (millions of tiny groups
# took longer than the whole build)
need = set(zip(F.num, F.street))
APn = AP[pd.Series(list(zip(AP.num, AP.key))).isin(need).values]
by = {k: g for k, g in APn.groupby(["num", "key"])}
print("indexed", len(by), "of", len(need), "needed addresses", round(time.time() - t), "s", flush=True)


def place(num, key, zip5, city):
    g = by.get((num, key))
    if g is None:
        return None
    town = (canon_city(city) or "").lower() if isinstance(city, str) else ""
    for sel, how in ((g.zip == zip5, "zip"), ((g.town == town) | (g.ptown == town), "town")):
        h = g[sel] if (zip5 if how == "zip" else town) else g.iloc[0:0]
        if len(h) and (h.lat.max() - h.lat.min()) < 0.01 and (h.lon.max() - h.lon.min()) < 0.013:
            return float(h.lat.median()), float(h.lon.median()), how
    return None


# SCDA's layer says which locator placed each point (official.py: loc). A ZIP-code, city or state centroid isn't the place: it's dropped
# and placed again below (address points, then the Census geocoder), else the permit stays off the map (Panera, 1321 Roberts Branch Pkwy,
# sat on the 29203 centroid with four other permits, 10 km from its listing). A point from a street centerline or an interpolated range
# can land on the wrong stretch of road (Five Guys, 29 Robert Smalls Pkwy, 8 km west): an address point at the same number and street
# wins when they disagree by more than 150 m. What stays on such a locator, or on the Census geocoder's, is "weak": official_match lets
# a same-address match reach past its 2 km limit for those.
CENTROID = {"SCZipcode", "SC_ZipCode", "US_Cities", "US_State", "US_CityState"}
RANGE = {"Street_Address", "ORS_Centerline", "ORSCenterline", "Google:RangeInterpolated", "Google:GeometricCenter", "Google:Approximate",
         "QAS_Corrected"}
cent = F["loc"].isin(CENTROID)
F.loc[cent, ["lat", "lon"]] = np.nan
print("ZIP, city or state centroid points dropped:", int(cent.sum()))


def street_guesses(sel):
    """Points that three or more different house numbers share: the locator found the street, not the number, and put every one at
    the same spot (15 Hwy 17 Business addresses in Murrells Inlet on one Street_Address point)."""
    pt = pd.Series(list(zip(F.lat.round(4), F.lon.round(4))), index=F.index)
    nums = F[sel].groupby(pt[sel]).apply(lambda g: len(set(zip(g.num, g.street))))
    return sel & pt.isin(set(nums[nums >= 3].index))


g3 = street_guesses(F["loc"].isin(RANGE) & F.lat.notna())
F.loc[g3, ["lat", "lon"]] = np.nan
print("street-range points shared by three or more house numbers, dropped:", int(g3.sum()))
F["geo"] = np.where(F.lat.notna(), "source", None)
rng = F["loc"].isin(RANGE) & F.lat.notna() & F.num.notna() & F.street.notna()
moved = 0
for i in F.index[rng]:
    h = place(F.at[i, "num"], F.at[i, "street"], F.at[i, "zip"], F.at[i, "city"])
    if h and math.hypot((h[0] - F.at[i, "lat"]) * 111000, (h[1] - F.at[i, "lon"]) * 92000) > 150:
        F.at[i, "lat"], F.at[i, "lon"], F.at[i, "geo"] = h
        moved += 1
print("street-range points moved to their address point:", moved, "of", int(rng.sum()))
miss = F.lat.isna() & F.num.notna() & F.street.notna()
hits = [place(n, k, z, c) for n, k, z, c in zip(F.loc[miss, "num"], F.loc[miss, "street"], F.loc[miss, "zip"], F.loc[miss, "city"])]
for i, h in zip(F.index[miss], hits):
    if h:
        F.at[i, "lat"], F.at[i, "lon"], F.at[i, "geo"] = h
# then the US Census geocoder's cached matches (geocode_census.py writes them; run it, then this script again)
import json
GC = json.load(open(f"{SC}/geocode_census.json")) if os.path.exists(f"{SC}/geocode_census.json") else {}
miss = F.lat.isna() & F.addr.fillna("").str.strip().ne("")
for i in F.index[miss]:
    q = f"{F.at[i, 'addr'].strip()}, {(F.at[i, 'city'] or '').strip().title() if isinstance(F.at[i, 'city'], str) else ''}, SC {F.at[i, 'zip'] or ''}".strip()
    h = GC.get(q)
    if isinstance(h, dict) and h.get("lat"):
        F.at[i, "lat"], F.at[i, "lon"], F.at[i, "geo"] = h["lat"], h["lon"], "census"
g3 = street_guesses(F.geo.eq("census"))
F.loc[g3, ["lat", "lon"]] = np.nan; F.loc[g3, "geo"] = None
print("Census points shared by three or more house numbers, dropped:", int(g3.sum()))
F["weak"] = (F["loc"].isin(RANGE) & F.geo.eq("source")) | F.geo.eq("census")
F.to_pickle(f"{SC}/official.pkl")
print("placed:", F.geo.value_counts(dropna=False).to_dict(), "| by source still without a point:",
      F[F.lat.isna()].groupby("jur").size().to_dict(), round(time.time() - t), "s")
