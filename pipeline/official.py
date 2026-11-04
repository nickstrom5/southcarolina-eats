"""Official records for South Carolina -> one table of permitted food businesses, and their inspections.

One statewide inspector: since July 1, 2024 the SC Department of Agriculture (SCDA) Retail Food Safety program permits and inspects every
retail food establishment under Regulation 61-25 (DHEC did before). SC Food Grades (apps.dhec.sc.gov/Environment/FoodGrades/, run by SC DPH
for SCDA) publishes the last three years of inspections; its map reads a public ArcGIS Online feature service (fetch_official.py):
- layer 0 "Restaurants": one row per permit with a point (UTM 17N, fetched as WGS84). It lags: about 3,600 retail-food permits that SCDA
  inspected (many new in 2026) aren't in it, and it still holds permits replaced after a change of owner.
- table 4 "Restaurants_Steton": one row per inspection with the posted grade and date. SCORE is empty on every row, so no score is ever
  shown or derived: the posted grade is the official result (8-403.10(G): it can differ from the score).
PROG_CODE (the site's own facility types): 206 Retail Food Establishments, 204 Mobile Food Units, 208 Institutions, 211 Grocery Stores.

load() returns: jur, lic (the SCDA permit number), name, keys (name keys), addr, city, zip, num, street, lat, lon, kind, active, ltype,
county, status (latest posted grade).
kind: food (a retail food permit) | mobile | retail (grocery) | other (institutions; schools, jails, caterers by name).
"""
import os, re, json, datetime
import numpy as np, pandas as pd
from common import norm_name, RAW, name_sim, _stems, GENERIC, canon_city

OFF = os.path.join(RAW, "official")
DIRS = {"N": "N", "S": "S", "E": "E", "W": "W", "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}
TYPES = set("ST STREET AVE AV AVENUE BLVD BOULEVARD RD ROAD DR DRIVE LN LANE CT COURT PL PLACE PKWY PARKWAY TER TRL TRAIL WAY HWY CIR "
            "CIRCLE PLZ SQ MALL BND PASS XING RUN ROW WALK RDG LOOP FWY FREEWAY EXPY EXPRESSWAY".split())


def road(a):
    """One spelling for numbered roads: 'US HIGHWAY 17' = 'US-17' = 'HWY 17'; 'SC HIGHWAY 544' = 'SC-544' = 'SC 544' = 'HWY 544';
    'INTERSTATE 26' = 'I-26' = 'I 26'; 'STATE ROAD S-10-123' = 'S 10 123'. South Carolina doesn't give a state route a US route's
    number, so both are HWY."""
    a = re.sub(r"(\d)\s*&\s*(\d)", r"\1-\2", a.upper())
    a = re.sub(r"\b(US|SC|I)-(\w)", r"\1 \2", a)
    a = re.sub(r"\b(?:INTERSTATE(?: HIGHWAY| HWY)?|IH|I H)\s*(?=\d)", "I ", a)
    a = re.sub(r"\b(?:US|U S)(?:\s+(?:HIGHWAY|HWY|ROUTE|RTE|RT))?\s+(?=\d)", "HWY ", a)
    a = re.sub(r"\b(?:SC (?:HIGHWAY|HWY|ROUTE|RTE|RT)|STATE (?:HIGHWAY|HWY|ROUTE|RTE)|HWY SC|HIGHWAY SC|SC)\s+(?=\d)", "HWY ", a)
    a = re.sub(r"\bSTATE (?:ROAD|RD)\s+S\s*-?\s*", "S ", a)
    a = re.sub(r"\bHIGHWAY\b", "HWY", a)
    # "US-17 Bus" = "Highway 17 Business" (Murrells Inlet's business route), "Hwy 21 Byp" = "Hwy 21 Bypass"
    a = re.sub(r"\b(HWY \w+) (?:BUS|BUSN|BUSINESS)\b\.?", r"\1 BUSINESS", a)
    a = re.sub(r"\b(HWY \w+) (?:BYP|BYPASS|BY PASS)\b\.?", r"\1 BYPASS", a)
    return re.sub(r"\b(HWY|I) (\w+)\s*-\s*\w+", r"\1 \2", a)


ORD = {"FIRST": "1ST", "SECOND": "2ND", "THIRD": "3RD", "FOURTH": "4TH", "FIFTH": "5TH", "SIXTH": "6TH", "SEVENTH": "7TH",
       "EIGHTH": "8TH", "NINTH": "9TH", "TENTH": "10TH", "ELEVENTH": "11TH", "TWELFTH": "12TH"}


def street_key(a):
    """'2505 Monroe St' -> ('2505', 'MONROE'); '1000 OSAGE STREET' -> ('1000', 'OSAGE'); 'E Jefferson Ave' keeps 'JEFFERSON'."""
    if not isinstance(a, str):
        return None, None
    a = re.sub(r"[.,#]", " ", road(a))
    m = re.match(r"^\s*(\d+)[A-Z]?(?:\s*-\s*(?:\d+[A-Z]?|[A-Z]\b))?\s+(.*)$", a)   # "1635-A SPRINGDALE DRIVE" is number 1635
    if not m:
        return None, None
    words = [w for w in m.group(2).split() if w]
    # a lone unit letter before the street ("1635 A SPRINGDALE DR" = "1635-A SPRINGDALE DRIVE", "5335 B N KINGS HWY"), not a lettered
    # street ("100 A ST") or initials ("1748 J A COCHRAN BYPASS")
    if len(words) > 2 and len(words[0]) == 1 and words[0] not in DIRS and words[1] not in TYPES and (len(words[1]) > 1 or words[1] in DIRS):
        words = words[1:]
    if len(words) > 1 and words[0] in DIRS:
        words = words[1:]
    # a route's direction on its number or spelled out ("HWY 9E", "HWY 9 EAST") reads "HWY 9 E" (Taco Station, Longs, both ways)
    words = [x for w in words for x in (re.match(r"^(\d+)([NSEW])$", w).groups() if re.match(r"^(\d+)([NSEW])$", w) else (w,))]
    words = words[:1] + [DIRS.get(w, w) for w in words[1:]]
    core = []
    for w in words:
        if w in TYPES and core:
            break
        core.append(w)
    core = [ORD.get(w, w) for w in core]
    return m.group(1), " ".join(core[:3]) or None


def street_compat(a, b):
    """Same street, or one is a whole-word prefix of the other (a record that truncates "1206 CENTAUR" = Centaur Village Dr)."""
    if not isinstance(a, str) or not isinstance(b, str) or not a or not b:
        return False
    return a == b or a.startswith(b + " ") or b.startswith(a + " ")


def street_nums(a):
    """'157-159 W Main St' -> {'157', '159'}; '2505 Monroe St' -> {'2505'}."""
    if not isinstance(a, str):
        return set()
    a = road(a)
    m = re.match(r"^\s*(\d+)[A-Z]?(?:\s*-\s*(?:(\d+)[A-Z]?|[A-Z]\b))?\s", a.upper() + " ")
    if not m:
        return set()
    lo = int(m.group(1)); hi = int(m.group(2)) if m.group(2) else lo
    if hi < lo:   # "1500-02"
        hi = int(str(lo)[: len(str(lo)) - len(m.group(2))] + m.group(2)) if m.group(2) else lo
    return {str(x) for x in range(lo, hi + 1, 2 if (hi - lo) % 2 == 0 else 1)} if 0 <= hi - lo <= 12 else {str(lo)}


def _names(*vals):
    out = []
    for v in vals:
        if not isinstance(v, str):
            continue
        v = re.sub(r"\s*\((?:MOBILE|MOBILE UNIT|COMMISSARY|CATERING|SPECIAL EVENT|SPEC EVENT|TEMP(?:ORARY)? EVENT|CP|INSIDE [^)]*)\)\s*$", "", v, flags=re.I)
        for part in re.split(r"\s*/\s*|\s+\bdba\b\s+|\s+&\s+(?=[A-Z][a-z])|\s*\(\s*|\s*\)\s*", v, flags=re.I):
            k = norm_name(re.sub(r"\b(?:LLC|INC|CORP|CORPORATION|LTD|CO)\b\.?", "", part, flags=re.I))
            if k and k not in out:
                out.append(k)
    return out


def _fetched():
    try:
        return json.load(open(f"{OFF}/sc_inspections.json"))["fetched"]
    except (OSError, KeyError, ValueError):
        return None


FETCHED = _fetched()   # the day the feature service was read (it's edited daily)
# Records through: the fetch date minus 7 days. SC Food Grades: "an inspection report may not be immediately available online
# following an inspection", and the last days before a read hold fewer rows than the weeks before.
THROUGH = (datetime.date.fromisoformat(FETCHED) - datetime.timedelta(days=7)).isoformat() if FETCHED else None
# A permit counts as open when SCDA inspected it within 18 months of that date: every establishment gets a routine inspection one to
# four times a year (agriculture.sc.gov, "Understanding Restaurant Inspections"), and seasonal beach places are inspected each season.
ACTIVE_SINCE = (datetime.date.fromisoformat(THROUGH) - datetime.timedelta(days=548)).isoformat() if THROUGH else None
COUNTY = {"01": "Abbeville", "02": "Aiken", "03": "Allendale", "04": "Anderson", "05": "Bamberg", "06": "Barnwell", "07": "Beaufort",
          "08": "Berkeley", "09": "Calhoun", "10": "Charleston", "11": "Cherokee", "12": "Chester", "13": "Chesterfield", "14": "Clarendon",
          "15": "Colleton", "16": "Darlington", "17": "Dillon", "18": "Dorchester", "19": "Edgefield", "20": "Fairfield", "21": "Florence",
          "22": "Georgetown", "23": "Greenville", "24": "Greenwood", "25": "Hampton", "26": "Horry", "27": "Jasper", "28": "Kershaw",
          "29": "Lancaster", "30": "Laurens", "31": "Lee", "32": "Lexington", "33": "Marion", "34": "Marlboro", "35": "McCormick",
          "36": "Newberry", "37": "Oconee", "38": "Orangeburg", "39": "Pickens", "40": "Richland", "41": "Saluda", "42": "Spartanburg",
          "43": "Sumter", "44": "Union", "45": "Williamsburg", "46": "York"}
PROG = {"206": "Retail Food Establishment", "204": "Mobile Food Unit", "208": "Institution", "211": "Grocery Store"}
PROG_KIND = {"206": "food", "204": "mobile", "208": "other", "211": "retail"}
# Inspection types as the service names them (it changed vocabularies in mid-2024: "10_Routine Inspection" became "Routine"). COMPL and
# COO are SCDA pre-operational inspections (the reports read "PRE-OPERATIONAL INSPECTION FOR RETAIL FOOD", reason "05. Compliance" or
# "04. Change of Ownership", result "Permit Issued"); a COMPL row graded "S" is a "Retail Food Suspension Notification" (the report:
# "Removed Letter Grade and applied Suspension Sticker").
ITYPE = {"Routine": "Routine", "10_Routine Inspection": "Routine", "Follow Up": "Follow-up", "15_Follow-Up Inspection": "Follow-up",
         "COMPL": "Permit (compliance)", "COO": "Permit (change of owner)", "01_Permit Issued Inspection-Change of Ownership": "Permit (change of owner)",
         "11_Permit Issued Inspection-New Facility": "Permit (new)", "14_Permit Reinstated Inspection": "Permit reinstated",
         "Complaint": "Complaint", "Outbreak": "Outbreak"}
GRADES = ["A", "B", "C"]
REPORT_URL = "https://pubdoc.dhec.sc.gov/inspection/{}.pdf"


def _zip(z):
    z = re.sub(r"\D", "", str(z or ""))
    return z[:5] if len(z) >= 5 else ""


# school, hospital and institutional kitchens: never a restaurant, whatever else the name says
OTHER = re.compile(r"\((?:MOBILE|MOBILE UNIT|COMMISSARY|CATERING|SPECIAL EVENT|TEMP(?:ORARY)? EVENT)\)|\b(?:SCHOOLS?|ELEMENTARY|ELEM|MIDDLE SCHOOL|"
                   r"HIGH SCHOOL|ACADEMY|PRESCHOOL|CHILDCARE|CHILD CARE|CHILD DEVELOPMENT|DAYCARE|DAY CARE|HEADSTART|HEAD START|HOSPITAL|JAIL|"
                   r"DETENTION|CORRECTIONAL|DETENTION CENTER|FOOD BANK|SENIOR|NURSING|BOARD OF EDUCATION|PUBLIC SCHOOLS|PTA|PTO|"
                   r"PORTABLE|STAND \d+|FRATERNITY|SORORITY|APARTMENTS?|APTS|RECREATION CENTER|REC CENTER|BOAT RAMP|SWIM CLUB|"
                   r"SUMMER CAMP|DAY CAMP)\b", re.I)
# words that usually mean a truck, caterer or stand, unless the name also says it's a place to eat ("Mike's Pizza & Catering" is a pizzeria)
OTHER_SOFT = re.compile(r"\b(?:MOBILE|FOOD TRUCK|CATERING|CATERER|COMMISSARY|CONCESSIONS?|BOOSTERS?|LITTLE LEAGUE|ATHLETIC ASSOCIATION|"
                        r"SNACK SHACK|POOL)\b", re.I)
FOODY = re.compile(r"\b(?:RESTAURANT|CAFE|CAFFE|GRILL|GRILLE|KITCHEN|PIZZA|PIZZERIA|TAVERN|PUB|BAR|DINER|BISTRO|EATERY|BBQ|DELI|"
                   r"BAKERY|COFFEE|TACOS?|TAQUERIA|BURGERS?|WINGS|SUSHI|STEAK\w*|SALOON|INN|SPORTS BAR|BREWING|BREWERY|SEAFOOD|"
                   r"BARBECUE|BAR B Q)\b", re.I)


def _date(ms):
    """The service stores local times labeled UTC (inspections cluster 8am-4pm "UTC"), so the UTC calendar date is the local date."""
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.UTC).date().isoformat() if ms else None


def visits():
    """Every inspection row: lic, d (date), grade (A/B/C/S as posted), typ (our label for the service's type), raw type, report id.
    Rows after THROUGH are dropped (publication lag)."""
    rows = []
    for f in json.load(open(f"{OFF}/sc_inspections.json"))["features"]:
        a = f["attributes"]
        d = _date(a.get("INSP_DATE"))
        if not d or (THROUGH and d > THROUGH):
            continue
        g = (a.get("POSTED_GRADE") or "").strip().upper()
        t = (a.get("AuditTypeName") or "").strip()
        rows.append({"lic": (a.get("PERMIT_ID") or "").strip(), "d": d, "grade": g if g in ("A", "B", "C", "S") else None,
                     "typ": ITYPE.get(t, t or "Inspection"), "raw_typ": t, "rid": (a.get("AuditResultGlobalID") or "").strip() or None,
                     "prog": str(a.get("PROG_CODE") or "").strip(), "name": (a.get("FACILITY") or "").strip(),
                     "addr": (a.get("ADDRESS") or "").strip(), "city": (a.get("CITY") or "").strip(), "zip": _zip(a.get("ZIPCODE")),
                     "county": COUNTY.get((a.get("COUNTY") or "").strip()), "active": str(a.get("Active") or "").strip().lower() == "true"})
    v = pd.DataFrame(rows)
    return v.sort_values(["lic", "d"]).reset_index(drop=True)


def _row(jur, lic, name, addr, city, z, la, lo, kind, active=True, ltype=None, county=None, status=None):
    num, st = street_key(addr)
    if kind == "food" and (OTHER.search(name or "") or (OTHER_SOFT.search(name or "") and not FOODY.search(name or ""))):
        kind = "other"
    return {"jur": jur, "lic": lic, "name": name, "dba": name, "holder": None, "keys": _names(name), "addr": addr, "city": city,
            "zip": _zip(z), "num": num, "street": st, "lat": la, "lon": lo, "kind": kind, "active": active, "ltype": ltype,
            "county": county, "status": status}


# permits whose SCDA address isn't the restaurant's, checked by hand: permit -> (address, zip). The layer's point (at that address) is dropped.
# "WADE'S AT PINEWOOD": 964 S Pine St is Wade's corporate office (Overture lists both "Wade's Corporate Office" and "Wades Restaurant Inc"
# there); the restaurant is in the Pinewood Shopping Center at 1000 N Pine St (eatatwades.com/history).
ADDR_FIX = {"42-206-01952": ("1000 N PINE ST", "29303")}


def load(v=None):
    """One row per SCDA permit (the feature layer's permits plus the inspection table's): the latest name and address, the layer's
    point when it has one (loc = the layer's Loc_name, the locator that placed it), open when inspected since ACTIVE_SINCE, its latest
    record not a suspension, and not marked inactive."""
    v = visits() if v is None else v
    layer = {}
    for f in json.load(open(f"{OFF}/sc_permits.json"))["features"]:
        a, g = f["attributes"], f.get("geometry") or {}
        layer[(a.get("PERMIT_ID") or "").strip()] = (a, g)
    last = v.groupby("lic").tail(1).set_index("lic")
    rows = []
    for lic in sorted(set(layer) | set(last.index)):
        if not lic:
            continue
        a, g = layer.get(lic, ({}, {}))
        r = last.loc[lic] if lic in last.index else None
        prog = str(a.get("PROG_CODE") or (r.prog if r is not None else "") or "").strip()
        name = (r["name"] if r is not None and r["name"] else (a.get("FACILITY") or "")).strip()
        # the layer's ADDRESS holds up to 150 characters, the table's 30 ("2572 NORTH ROAD" vs a cut-off "1234 SOUTH CAROLINA HIGHWA")
        addr = (a.get("ADDRESS") or "").strip() or (r["addr"] if r is not None else "")
        city = canon_city((r["city"] if r is not None and r["city"] else None) or a.get("CITY"))
        z = a.get("ZIPCODE") or (r["zip"] if r is not None else "")
        la, lo = g.get("y"), g.get("x")
        la = la if isinstance(la, (int, float)) and la == la and 31 < la < 36 else np.nan
        lo = lo if isinstance(lo, (int, float)) and lo == lo and -84 < lo < -78 else np.nan
        loc = (a.get("Loc_name") or "").strip() or None
        if lic in ADDR_FIX:
            addr, z = ADDR_FIX[lic]
            la = lo = np.nan; loc = None
        cty = COUNTY.get(lic[:2])
        latest = r["d"] if r is not None else None
        active = bool(r is not None and r["active"] and latest and ACTIVE_SINCE and latest >= ACTIVE_SINCE and r["grade"] != "S")
        rows.append(_row("scda", lic, name, addr, city, z, la, lo, PROG_KIND.get(prog, "other"), active=active, ltype=PROG.get(prog),
                         county=cty + " County" if cty else None, status=r["grade"] if r is not None else None))
        rows[-1]["latest"] = latest
        rows[-1]["in_layer"] = lic in layer
        rows[-1]["loc"] = loc
    df = pd.DataFrame(rows)
    # one business can hold several permits (a new permit after a change of owner, a hotel's restaurant and bar): same address and a
    # name in common
    df["biz"] = np.arange(len(df))
    town = df.city.fillna("").str.upper().str.strip()
    for num, g in df[df.num.notna() & df.street.notna()].groupby("num"):
        idx = list(g.index)
        if len(idx) < 2 or len(idx) > 400:
            continue
        for x in range(len(idx)):
            for y in range(x + 1, len(idx)):
                a_, b_ = idx[x], idx[y]
                if not street_compat(df.at[a_, "street"], df.at[b_, "street"]):
                    continue
                if not ((df.at[a_, "zip"] and df.at[a_, "zip"] == df.at[b_, "zip"]) or (town[a_] and town[a_] == town[b_])):
                    continue
                ka, kb = df.at[a_, "keys"], df.at[b_, "keys"]
                if not ka or not kb:
                    continue
                if any(name_sim(p, q) >= 85 or ((_stems(p) - GENERIC) & (_stems(q) - GENERIC)) for p in ka for q in kb):
                    old, new = df.at[b_, "biz"], df.at[a_, "biz"]
                    df.loc[df.biz == old, "biz"] = new
    return df


if __name__ == "__main__":
    F = load()
    print(len(F), "permits | through", THROUGH, "| open since", ACTIVE_SINCE)
    print(F.groupby(["kind", "active"]).size())
    print("no point:", int(F.lat.isna().sum()), "| open retail-food permits without a point:", int((F.lat.isna() & F.active & (F.kind == "food")).sum()))
