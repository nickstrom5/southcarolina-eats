"""Writes the public website in docs/ from the same data the app ships (data/app/places.json plus the data/app/detail-*.json files that
hold SCDA permits, phones, websites and SCDA inspection histories).

Pages: the landing page; a statewide page for each hand-checked guide with at least four places (whole-hog and mustard barbecue, Lowcountry
and Grand Strand seafood, Gullah Geechee cooking, meat-and-threes and drive-ins); MICHELIN and James Beard honors; an explainer of SCDA's
posted inspection grades (counts only, no place named); one page per town with enough hand-checked or honored places to say something
real, plus a cities index; the web app (/explore/); privacy; terms; 404; sitemap.xml, robots.txt, site.webmanifest and
playbook/site-numbers.json. Everything listed is hand-checked research or public records; nothing comes from Google, Yelp or any
ratings site, and nothing is ranked by ratings. Ported from oh-eats/scripts/make-site.py.

Rules the copy keeps (scripts/qa-site.py checks them):
- Every number is counted from the data here, never typed in. No sentence claims "every" or "all N" restaurants.
- "Checked" only for the hand-checked lists (`hc`, 2025-26 evidence for each place).
- The SC Department of Agriculture's posted grade (A, B or C) is shown as SC Food Grades publishes it, with its date; the service has
  no score, and we compute no grade or score of our own.
- A place whose latest posted grade is B or C is never named in a title, description, lede or other promotional spot. The inspections
  page names no place at all and has no "worst" list.
- Every page carries a hash-pinned Content-Security-Policy; inline scripts and styles are hashed after the page is final.

Usage (from sc-eats/): .venv/bin/python scripts/make-site.py           (github.io address, BASE /southcarolina-eats)
                       SC_DOMAIN=southcarolina.eatsranked.com .venv/bin/python scripts/make-site.py   (once Nick's CNAME resolves)
Re-run it after every data rebuild, then check the pages with scripts/qa-site.py. Never hand-edit docs/*.html.
"""
import base64
import datetime as dt
import glob
import gzip
import hashlib
import html
import json
import math
import os
import re
import struct
import urllib.parse
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = f"{ROOT}/docs"
# Where the site lives. Until Nick's Cloudflare record (CNAME southcarolina -> nickstrom5.github.io, DNS only) resolves, GitHub Pages serves
# the project address. When `dig southcarolina.eatsranked.com` shows the CNAME, run with SC_DOMAIN=southcarolina.eatsranked.com and push: this
# writes docs/CNAME, and GitHub then forwards the old github.io links (the ones inside shipped app builds).
CUSTOM_DOMAIN = os.environ.get("SC_DOMAIN", "").strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
REPO = "southcarolina-eats"
DOMAIN = f"https://{CUSTOM_DOMAIN}" if CUSTOM_DOMAIN else f"https://nickstrom5.github.io/{REPO}"
BASE = "" if CUSTOM_DOMAIN else f"/{REPO}"     # path prefix for root-relative links
BRAND = "South Carolina Eats"
APP_NAME = "South Carolina Eats"
TAGLINE = "BBQ, shrimp & grits, oysters"
EMAIL = "nick@eatsranked.com"   # Nick, 2026-10-12: the site's contact address (Cloudflare Email Routing)
PUBLISHED = "2026-10-26"        # the site's first publication (Article datePublished)
SITE_REV = "2026-10-26"         # the last change to this generator's own copy or code: bump it when you change the words
POLICY_UPDATED = "2026-10-26"   # privacy policy and terms: bump only when their text changes
PRIVACY_UPDATED = "2026-10-26"   # the privacy policy alone: the app’s data updates (OTA-DATA.md)
CHECKED = "fall 2026"
STORAGE_PREFIX = "sceats-"      # the web app's localStorage keys (other state sites share the nickstrom5.github.io origin)
# South Carolina Eats is one of the Eats Ranked state sites: the hub (eatsranked.com) lists it as a subOrganization, and every page says so
# from this side too (the footer line and the Organization's parentOrganization), in Wisconsin's words.
HUB = {"@type": "Organization", "@id": "https://eatsranked.com/#organization", "name": "Eats Ranked", "url": "https://eatsranked.com/"}
ORG_ID = f"{DOMAIN}/#org"
# the site's Organization as other pages name it (author, publisher): the same @id as the full node on the landing page
ORG_REF = {"@type": "Organization", "@id": ORG_ID, "name": BRAND, "url": f"{DOMAIN}/",
           "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png", "width": 512, "height": 512}, "parentOrganization": HUB}

# ---------------------------------------------------------------- data: the core file plus the region detail files
D = json.load(open(f"{ROOT}/data/app/places.json"))
assert D.get("generated"), "data/app/places.json has no 'generated' field: the pipeline hasn't finished writing it"
DETAIL_SRC = {}
for _f in sorted(glob.glob(f"{ROOT}/data/app/detail-*.json")):
    DETAIL_SRC.update(json.load(open(_f)))
assert DETAIL_SRC, "data/app/detail-*.json are missing"


def merged(r):
    """One place with its detail fields put back: the core's "in" is [source, grade, 0, date]; the detail's "in" is {n, h}, h being
    [date, grade (A/B/C, S for a suspension notice), type index, report id] latest first."""
    det = DETAIL_SRC.get(r["id"]) or {}
    out = dict(r)
    ins = r.get("in")
    if isinstance(ins, list) and len(ins) >= 4:
        out["in"] = {"j": ins[0], "b": ins[1], "s": ins[2], "d": ins[3]}
    for k, v in det.items():
        if k == "in" and isinstance(v, dict):
            out["in"] = {**(out.get("in") or {}), **v}
        else:
            out[k] = v
    return out


RECS = [merged(r) for r in D["places"]]
TODAY = max(str(D.get("generated") or SITE_REV)[:10], SITE_REV)   # sitemap lastmod and dateModified move with the data or the copy
INS_THROUGH = D.get("inspections_through") or {}
INS_PUBLISHED = (D.get("inspections_published") or {}).get("scda") or ""
N_SCDA_PERMITS = D.get("scda_open_food_permits") or 0
SCDA_OPEN_SINCE = D.get("scda_open_since") or ""
CITIES, CUISINES, COUNTIES = D["cities"], D["cuisines"], D["counties"]
RESULTS, ITYPES = D.get("results") or [], D.get("itypes") or []
BBQ, SEAFOOD, GULLAH, MEAT3, OLDEST = 1, 2, 4, 8, 16   # the app's PlaceTags bits (pipeline/southcarolina.py TAGS)
MI = ["", "MICHELIN Recommended", "Bib Gourmand", "1 MICHELIN Star", "2 MICHELIN Stars", "3 MICHELIN Stars"]
FOOD_GRADES = "https://apps.dhec.sc.gov/Environment/FoodGrades/"   # SC Food Grades: SCDA's inspections (never scdhec.gov)
SCDA_GRADES = "https://agriculture.sc.gov/permits-and-inspections/retail-food-safety/understanding-restaurant-inspections/"
REPORT_URL = "https://pubdoc.dhec.sc.gov/inspection/{}.pdf"
SCDA_NOTE = ("Information provided in the application is intended to be used for general reference. SCDA provides no warranty, expressed or "
             "implied, as to the accuracy, reliability or completeness of furnished data. This database includes all permitted retail food "
             "establishments, some of which are not open to the general public for dining.")
LOW_BANDS = {"B", "C"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
NUM_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def hdate(iso):
    """2026-09-24 -> September 24, 2026"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{MONTHS[int(m[2]) - 1]} {int(m[3])}, {m[1]}" if m else str(iso or "")


def hmonth(iso):
    m = re.match(r"(\d{4})-(\d{2})", str(iso or ""))
    return f"{MONTHS[int(m[2]) - 1]} {m[1]}" if m else str(iso or "")


def plural(n, one, many=None):
    return f"{n:,} {one if n == 1 else (many or one + 's')}"


def words_num(n):
    return NUM_WORDS[n] if 0 <= n < len(NUM_WORDS) else f"{n:,}"


def safe_url(u):
    """Only http(s) links leave the site; a bare host ("example.com/menu") gets https://. Anything else is dropped."""
    u = str(u or "").strip()
    if re.fullmatch(r"https?://[^\s\"'<>\\]+", u, re.I):
        return u
    if re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}(?:[/?#][^\s\"'<>\\]*)?", u, re.I):
        return "https://" + u
    return ""


# Websites we must not link (pipeline/website_blocklist.json): hacked, expired or another business's site. A blocked link is
# dropped, never the place. qa-site.py fails if a blocked domain or URL appears anywhere in docs/.
BLOCKLIST = json.load(open(f"{ROOT}/pipeline/website_blocklist.json"))
for _b in BLOCKLIST:
    assert _b.get("match", "domain") in ("domain", "url") and (_b.get("url") or _b.get("domain")), f"bad blocklist entry {_b}"
BLOCKED_LINKS = []   # (place, link) pairs the blocklist dropped from this build


def url_key(u):
    """A URL compared without its scheme, a leading www., a trailing slash or letter case."""
    return re.sub(r"^(?:https?:)?//(?:www\.)?", "", str(u or "").strip().lower()).rstrip("/")


def blocked_site(u):
    host = (urllib.parse.urlsplit(u).hostname or "").rstrip(".").removeprefix("www.")
    for b in BLOCKLIST:
        if b.get("match", "domain") == "url":
            if url_key(u) == url_key(b.get("url") or b["domain"]):
                return b
        else:
            d = b["domain"].strip().lower().rstrip(".").removeprefix("www.")
            if host == d or host.endswith("." + d):
                return b
    return None


class P:
    """One place, with the same meaning the app gives each field (SouthCarolinaEats/Models/Place.swift)."""

    def __init__(self, r):
        self.r = r
        self.name = str(r["n"])
        self.city = CITIES[r["c"]] if r.get("c") is not None else ""
        self.county = COUNTIES[r["co"]] if r.get("co") is not None else None
        self.cuisine = CUISINES[r["cu"]] if r.get("cu") is not None else ""
        self.addr = (r.get("a") or "").strip().rstrip(",").strip()
        self.zip = str(r.get("z") or "")
        self.lat, self.lon = r.get("la"), r.get("lo")
        self.tags = r.get("g") or 0
        self.chain = (r.get("ch") or 0) >= 5
        self.venue = r.get("v") == 1
        self.ip = r.get("ip")
        self.founded = r.get("f") if isinstance(r.get("f"), int) else None
        self.fn = r.get("fn") or ""
        self.dishes = (r.get("dish") or "").replace("; ", ", ")
        self.season = r.get("seas") or ""
        self.note = r.get("note") or ""
        self.site = safe_url(r.get("w"))
        if self.site and blocked_site(self.site):
            BLOCKED_LINKS.append((self.name, self.site))
            self.site = ""   # the link goes, the place stays
        self.jbf = r.get("jbf") or ""
        self.h = r.get("h") or 0
        self.mi = r.get("mi") if r.get("mi") in range(1, len(MI)) else 0
        self.hc = r.get("hc") == 1   # hand-checked against a 2025-26 source; the only places the themed guides list
        self.lic = r.get("lic") or []   # official records: [[source, license key or null, type]]
        ins = r.get("in")
        self.ins = ins if isinstance(ins, dict) and ins.get("d") else None
        self.band = RESULTS[self.ins["b"]] if self.ins and 0 <= self.ins.get("b", -1) < len(RESULTS) else None
        self.ins_city = self.ins["j"] if self.ins else None

    def featured_key(self):
        # the app's "Featured first": honored places, then documented founding year, then name
        return (-(self.ip if self.ip is not None else -1), self.founded or 9999, self.name.lower())

    def jb_label(self):
        return ("America's Classic" if self.h & 1 else "James Beard winner" if self.h & 2 else "James Beard finalist" if self.h & 4
                else "James Beard semifinalist" if self.h & 8 else None)

    def promo_ok(self):
        """Never name a place whose latest posted grade is B or C in a title, description, lede or other promotional spot."""
        return self.band not in LOW_BANDS

    def in_guide(self, tag):
        return self.hc and bool(self.tags & tag)


PLACES = [P(r) for r in RECS]
REST = [p for p in PLACES if not p.venue]

ALL_GUIDES = [("bbq", BBQ), ("seafood", SEAFOOD), ("gullah", GULLAH), ("meat3", MEAT3)]
MIN_GUIDE = 4   # a guide gets its own page once its research has this many places (Idaho's rule); until then it's only in the web app
L_ALL = {k: sorted([p for p in REST if p.in_guide(t)], key=P.featured_key) for k, t in ALL_GUIDES}
GUIDE_TAGS = [(k, t) for k, t in ALL_GUIDES if len(L_ALL[k]) >= MIN_GUIDE]
L = {k: L_ALL[k] for k, _ in GUIDE_TAGS}
def hon_key(p):
    """The app's honors order: the MICHELIN distinction (stars, Bib Gourmand, Recommended), then the James Beard honor (America's Classic,
    winner, finalist, semifinalist), then name."""
    jb = 4 if p.h & 1 else 3 if p.h & 2 else 2 if p.h & 4 else 1 if p.h & 8 else 0
    return (-p.mi, -jb, p.name.lower())


HON_L = sorted([p for p in REST if p.jbf or p.mi], key=hon_key)
OLD_L = sorted([p for p in REST if p.founded and p.in_guide(OLDEST)], key=lambda p: (p.founded, p.name.lower()))
HAS_OLD = len(OLD_L) >= MIN_GUIDE
HC_ANY = [p for p in REST if p.hc and (p.tags & (BBQ | SEAFOOD | GULLAH | MEAT3 | OLDEST))]   # on at least one hand-checked guide
INS_L = [p for p in REST if p.ins]

# ---------------------------------------------------------------- regions: the app's seven (each county to the nearest anchor point)
REGIONS = list(D.get("regions") or [])
REGION_NAME = {r: r for r in REGIONS}
REGION_ORDER = ["Charleston & Lowcountry", "Beaufort & Hilton Head", "Grand Strand", "Pee Dee", "Midlands", "Aiken & Savannah River", "Upstate"]
assert set(REGION_ORDER) == set(REGIONS), REGIONS
for p in PLACES:
    rg = p.r.get("rg")
    p.region = REGIONS[rg] if isinstance(rg, int) and 0 <= rg < len(REGIONS) else None


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- html helpers
e = html.escape


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "").replace("&", "and")).strip("-")


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def join_words(xs, conj="and"):
    xs = [x for x in xs if x]
    if len(xs) <= 1:
        return "".join(xs)
    return ", ".join(xs[:-1]) + f" {conj} " + xs[-1]


def fit(cands, lo, hi, what=""):
    seen = []
    # a description that misses the window by a few characters gets a fixed tail (state counts vary from build to build)
    more = [c.rstrip(".") + t for c in cands for t in (", with addresses and websites.", ". Free iPhone app coming soon.", ", with addresses.",
                                                         ". Free iPhone app.", ", with maps.")] if lo >= 100 else []
    for o in list(cands) + more:
        if lo <= len(o) <= hi:
            return o
        seen.append(o)
    raise ValueError(f"nothing fits {lo}-{hi} for {what}: {[(len(o), o) for o in seen[:12]]}")


# The app icon in miniature (scripts/make-brand.swift's shrimp, simplified for 30 px): a curled coral shrimp on flag indigo.
LOGO = ('<svg viewBox="0 0 64 64" width="30" height="30" aria-hidden="true"><defs><clipPath id="lg-r"><rect width="64" height="64" rx="14"/></clipPath></defs>'
        '<g clip-path="url(#lg-r)"><rect width="64" height="64" fill="#1B2A57"/>'
        '<path d="M40 19 A14 14 0 1 0 39 46" fill="none" stroke="#E8836B" stroke-width="11" stroke-linecap="round"/>'
        '<path d="M37 44 L51 38 L47 46 L51 54 Z" fill="#E8836B"/><ellipse cx="44" cy="20" rx="8" ry="6.5" fill="#E8836B"/>'
        '<circle cx="47" cy="19" r="1.6" fill="#1B2A57"/></g></svg>')
FAVICON = "data:image/svg+xml," + LOGO.replace('width="30" height="30" ', "").replace(' aria-hidden="true"', "").replace("<svg ", "<svg xmlns='http://www.w3.org/2000/svg' ").replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")

# Nick's palette (2026-10-26): flag & marsh. Flag-inspired indigo #1B2A57 for text, headings and accents (13.9:1 on white), marsh green
# #2F5D3A for secondary links (7.3:1), oyster cream #F6F1E7 as the page tint, and shrimp coral #E8836B only as a fill under indigo text
# (5.2:1), never as text on white and never under white text. The header band is a marsh-grass and tidal-creek strip. Lettering: condensed
# heavy system faces for headings, the system monospaced face for numbers; no web fonts are loaded (the CSP allows only this site).
CSS = """
  :root {
    --bg: #f6f1e7; --surface: #fff; --surface2: #ece3d2; --rule: #e4ddcf;
    --ink: #141d3b; --ink2: #1b2a57; --muted: #4f5874;
    --accent: #1b2a57; --accent2: #2f5d3a; --on-accent: #fff; --orange: #e8836b; --on-orange: #1b2a57; --lime: #e8836b; --soft: #fbe3da; --limesoft: #fbe3da;
    --focus: #2f5d3a;
    --radius: 16px;
    --display: "Avenir Next Condensed", "Helvetica Neue Condensed", "Roboto Condensed", "Arial Narrow", system-ui, sans-serif;
    --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0f1630; --surface: #18213f; --surface2: #222c4d; --rule: #323d61; --ink: #eef0f7; --ink2: #d6dbea; --muted: #a9b1c9; --accent: #f2b3a2; --accent2: #9fcfa9; --on-accent: #0f1630; --focus: #f2b3a2; }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  @media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
  body { margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
  a { color: var(--accent); text-underline-offset: 2px; }
  a:focus-visible, summary:focus-visible, button:focus-visible, select:focus-visible, input:focus-visible, [tabindex]:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; border-radius: 6px; }
  .skip { position: absolute; left: -9999px; top: 0; background: var(--orange); color: var(--on-orange); padding: 10px 14px; font-weight: 700; z-index: 10; }
  .skip:focus { left: 8px; top: 8px; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 0 20px; }
  header.site { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 0 14px; }
  .stripes { position: relative; height: 20px; margin: 0 0 4px; border-radius: 4px; overflow: hidden; background: #1b2a57; }
  .stripes::before { content: ""; position: absolute; left: 0; right: 0; top: 6px; height: 3px; background: #f6f1e7; }
  .stripes::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 12px; background: repeating-linear-gradient(90deg, transparent 0 2px, #2f5d3a 2px 5px, transparent 5px 9px); clip-path: polygon(0 100%, 0 30%, 100% 30%, 100% 100%); }
  .logo { display: flex; align-items: center; gap: 10px; font: 800 24px/1 var(--display); text-transform: uppercase; letter-spacing: .01em; color: var(--accent); text-decoration: none; }
  .logo svg { flex: 0 0 auto; border-radius: 7px; }
  header.site nav { display: flex; flex-wrap: wrap; gap: 4px 16px; justify-content: flex-end; }
  header.site nav a { color: var(--ink2); text-decoration: none; font-size: 15px; }
  header.site nav a:hover { color: var(--accent); text-decoration: underline; }
  h1, h2 { font-family: var(--display); font-weight: 800; color: var(--accent); letter-spacing: -.005em; }
  h1 { font-size: clamp(40px, 8.5vw, 64px); line-height: .95; margin: 0 0 18px; text-transform: uppercase; overflow-wrap: break-word; text-shadow: 3px 3px 0 var(--orange); }
  .kicker { font: 600 13px/1.4 var(--mono); letter-spacing: .04em; text-transform: uppercase; color: var(--accent); margin: 0 0 12px; }
  .kicker::before { content: ""; display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--orange); margin: 0 8px 1px 0; }
  h2 { font-size: 34px; line-height: 1.02; margin: 0 0 10px; text-transform: uppercase; }
  h3 { font-size: 18px; margin: 0; line-height: 1.3; }
  .lede { font-size: 19px; color: var(--ink2); margin: 0 0 26px; }
  .hero { padding: 44px 0 28px; }
  section { padding: 36px 0; border-top: 1px solid var(--rule); }
  section.hero { border: 0; }
  .sub { color: var(--ink2); margin: 0 0 22px; }
  .cta-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  .btn { display: inline-flex; align-items: center; gap: 10px; background: var(--orange); color: var(--on-orange); font-weight: 700; padding: 14px 20px; border-radius: 14px; text-decoration: none; font-size: 17px; }
  .btn-ghost { background: transparent; color: var(--accent); border: 2px solid var(--accent); }
  .pill { font-size: 14px; color: var(--muted); }
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 28px 0 0; padding: 0; list-style: none; }
  .stats li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px; }
  .stats b { display: block; font: 600 28px/1 var(--mono); color: var(--accent); }
  .stats span { font-size: 14px; color: var(--muted); }
  .steps { display: grid; gap: 12px; list-style: none; margin: 0; padding: 0; }
  .step { display: flex; gap: 14px; background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 18px; }
  .step .n { flex: 0 0 32px; height: 32px; border-radius: 50%; background: var(--orange); color: var(--on-orange); font-weight: 800; display: grid; place-items: center; }
  .step p { margin: 4px 0 0; color: var(--ink2); }
  .shots { display: flex; gap: 14px; overflow-x: auto; margin: 0 -20px; padding: 4px 20px 14px; scroll-snap-type: x proximity; list-style: none; }
  .shots li { flex: 0 0 auto; width: 210px; scroll-snap-align: start; }
  .shots img { display: block; width: 210px; height: auto; border-radius: 24px; border: 1px solid var(--rule); background: var(--surface2); }
  .shots p { font-size: 14px; color: var(--muted); margin: 8px 2px 0; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .card { background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 18px; }
  .card h3 { font: 800 21px/1.1 var(--display); text-transform: uppercase; letter-spacing: .01em; }
  a.card.gc { display: flex; flex-direction: column; gap: 6px; border: 0; border-radius: 18px; min-height: 150px; }
  a.card.gc b { font: 600 32px/1 var(--mono); margin-bottom: auto; }
  a.card.gc p, a.card.gc h3 { color: inherit; }
  a.card.gc p { opacity: .92; }
  a.card.gc.gc-bbq, a.card.gc.gc-seafood, a.card.gc.gc-gullah, a.card.gc.gc-meat3 { background: #e8836b; color: #1b2a57; }
  a.card.gc.gc-oldest, a.card.gc.gc-honors { background: #1b2a57; color: #fff; }
  .card p { margin: 6px 0 0; color: var(--ink2); }
  a.card { display: block; text-decoration: none; color: var(--ink); }
  a.card:hover h3 { text-decoration: underline; color: var(--accent); }
  .cities { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; padding: 0; margin: 0; }
  .cities a { display: inline-block; padding: 8px 12px; border-radius: 999px; border: 1px solid var(--rule); background: var(--surface); text-decoration: none; color: var(--ink); font-size: 15px; }
  .cities a:hover { border-color: var(--accent); }
  .cities a[aria-current] { border-color: var(--accent); font-weight: 700; }
  details { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 2px 18px; margin-bottom: 10px; }
  summary { cursor: pointer; padding: 14px 0; font-weight: 600; list-style: none; display: flex; justify-content: space-between; gap: 12px; }
  summary::-webkit-details-marker { display: none; }
  summary::after { content: "+"; color: var(--accent); font-weight: 800; }
  details[open] summary::after { content: "\\2013"; }
  details p { margin: 0 0 16px; color: var(--ink2); }
  .final { text-align: center; }
  .final .cta-row { justify-content: center; }
  nav.crumbs { font-size: 14px; color: var(--muted); padding: 16px 0 0; }
  nav.crumbs ol { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
  nav.crumbs li + li::before { content: "/"; margin-right: 6px; color: var(--rule); }
  nav.crumbs a { color: var(--muted); }
  .places { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }
  .places li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px 16px; min-width: 0; overflow-wrap: anywhere; scroll-margin-top: 12px; }
  .places li:target { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent); }
  .places .where { margin: 2px 0 0; font-size: 15px; color: var(--muted); }
  .places .facts { margin: 8px 0 0; font-size: 15px; color: var(--ink2); }
  .places .facts b { color: var(--ink); font-weight: 600; }
  .places .note { margin: 6px 0 0; font-size: 15px; color: var(--ink2); }
  .places .fine { margin: 6px 0 0; }
  .places .link { font-size: 14px; margin: 6px 0 0; }
  .tag { display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; background: var(--lime); color: #1b2a57; border-radius: 6px; padding: 1px 6px; margin: 0 4px 2px 0; }
  .tag-mi { background: #2f5d3a; color: #fff; }
  .tag-jb { background: #1b2a57; color: #fff; }
  .tag-plain { background: var(--soft); color: #1b2a57; }
  .toc { columns: 2; padding-left: 20px; margin: 0; }
  table { border-collapse: collapse; width: 100%; font-size: 15px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--rule); vertical-align: top; }
  td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
  .tbl { overflow-x: auto; }
  .res { display: inline-block; font: 800 12px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .04em; text-transform: uppercase; padding: 2px 6px; border-radius: 6px; }
  .res-ok { background: #ddefe3; color: #0e5a2b; } .res-mid { background: #ffe9c2; color: #6b3a00; } .res-low { background: #f9d5db; color: #7a0019; }
  .groups { list-style: none; padding: 0; margin: 0 0 18px; display: grid; gap: 12px; }
  .groups > li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px 16px; }
  .groups ul { margin: 8px 0 0; padding-left: 20px; color: var(--ink2); font-size: 15px; }
  .groups .count { margin: 8px 0 0; font-weight: 600; }
  .fine { font-size: 14px; color: var(--muted); }
  .legal h2 { font-size: 26px; margin-top: 28px; }
  .legal p, .legal li { color: var(--ink2); }
  footer { padding: 32px 0 56px; color: var(--muted); font-size: 14px; border-top: 1px solid var(--rule); margin-top: 20px; }
  footer nav { display: flex; flex-wrap: wrap; gap: 8px 16px; }
  footer a { color: var(--muted); }
  footer p { margin: 12px 0 0; }
  @media (max-width: 600px) {
    .grid2 { grid-template-columns: 1fr; }
    .stats { grid-template-columns: 1fr 1fr; }
    .toc { columns: 1; }
    .toc a { display: inline-block; padding: 3px 0; }
    header.site { flex-direction: column; align-items: flex-start; }
    header.site nav { justify-content: flex-start; }
    header.site nav a, footer nav a, nav.crumbs a { display: inline-block; padding: 10px 0; }
    footer nav { gap: 0 18px; }
    th, td { padding: 8px 4px; font-size: 14px; }
    .tbl th, .tbl td { padding: 8px 3px; font-size: 13px; }
    .res { font-size: 11px; letter-spacing: .02em; padding: 2px 4px; }
    nav.crumbs ol { align-items: center; }
  }
"""


def jsonld(obj):
    big = obj.get("@type") == "ItemList"
    raw = json.dumps(obj, ensure_ascii=False, indent=None if big else 1, separators=(",", ":") if big else None)
    return '<script type="application/ld+json">\n' + raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026") + "\n</script>"


def crumbs(trail):
    """trail: [(name, url)] ending with the current page."""
    items = "".join(f'<li><a href="{u}">{e(n)}</a></li>' if i < len(trail) - 1 else f'<li aria-current="page">{e(n)}</li>'
                    for i, (n, u) in enumerate(trail))
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(trail)]}
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{items}</ol></nav>', ld


def store_button(label="Ask for early access"):
    # A plain mailto button until launch: no Apple logo (Apple's marketing rules allow it only in the official badge). When
    # APP_STORE_URL is set in page() below, swap this for Apple's "Download on the App Store" badge artwork. Only Nick's internal
    # TestFlight group exists (2026-10-13): the mailto asks, and no page copy promises an invite or a link.
    return (f'<a class="btn store-btn" href="mailto:{EMAIL}?subject=South%20Carolina%20Eats%20early%20access&amp;body=Send%20me%20the%20TestFlight%20link.">'
            f'<span class="store-label">{label}</span></a>')


STORE_NOTE = "The free South Carolina Eats app for iPhone and iPad is on its way to the App Store."


def sha256_src(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode() + "'"


def csp_for(doc):
    """A strict policy for one finished page: only its own inline <script>/<style> blocks (by hash), same-origin data and images."""
    scripts = re.findall(r"<script>(.*?)</script>", doc, re.S)          # executable inline scripts (JSON-LD blocks are data, not run)
    styles = re.findall(r"<style>(.*?)</style>", doc, re.S)
    return ("default-src 'none'; "
            f"script-src {' '.join(sha256_src(s) for s in scripts) or chr(39) + 'none' + chr(39)}; "
            f"style-src {' '.join(sha256_src(s) for s in styles) or chr(39) + 'none' + chr(39)}; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'none'")


CSP_SLOT = "__CSP__"
written, noindexed = [], []
NAV = []   # set below, once the guide pages are known


def page(path, title, desc, body, lds=(), robots="index,follow,max-image-preview:large", og_alt=None, extra_css="", og_type="article"):
    assert 50 <= len(title) <= 60 or path == "404.html", (path, len(title), title)
    assert 140 <= len(desc) <= 160 or path == "404.html", (path, len(desc), desc)
    assert body.count("<h1") == 1, path
    assert 'style="' not in body, f"{path}: inline style attributes break the CSP"
    url = DOMAIN + "/" + ("" if path == "index.html" else path.removesuffix("index.html"))
    indexed = "noindex" not in robots
    if not any("parentOrganization" in json.dumps(x) for x in lds):   # every page names its publisher and the Eats Ranked parent
        lds = list(lds) + [{"@context": "https://schema.org", **ORG_REF}]
    og_alt = og_alt or f"{BRAND}: {TAGLINE}. South Carolina restaurants, with hand-checked barbecue, Lowcountry seafood and Gullah Geechee kitchens."
    ld = "\n".join(jsonld(x) for x in lds)
    canon = f'<link rel="canonical" href="{url}">\n' if indexed else ""
    og_url = f'<meta property="og:url" content="{url}">\n' if indexed else ""
    nav = "\n".join(f'      <a href="{u}">{t}</a>' for u, t in NAV)
    doc = f"""<!DOCTYPE html>
<html lang="en" data-base="{BASE}">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP_SLOT}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{canon}<meta name="robots" content="{robots}">
<meta name="theme-color" content="#1b2a57">
<!-- Smart App Banner: once the App Store Connect record exists, replace APP_ID with the numeric Apple ID and uncomment.
<meta name="apple-itunes-app" content="app-id=APP_ID">
-->
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
{og_url}<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:locale" content="en_US">
<meta property="og:image" content="{DOMAIN}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{DOMAIN}/og.png">
<link rel="icon" type="image/svg+xml" href="{FAVICON}">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<style>{CSS}{extra_css}</style>
{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="wrap">
  <header class="site">
    <a class="logo" href="/" aria-label="{BRAND} home">{LOGO}{BRAND}</a>
    <nav aria-label="Main">
{nav}
    </nav>
  </header>
  <div class="stripes" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
{body}
  <footer>
    <nav aria-label="Footer">
      <a href="/">{BRAND} app</a>
      <a href="/explore/">Search South Carolina restaurants</a>
{chr(10).join(f'      <a href="{u}">{e(t)}</a>' for u, t in GUIDE_LINKS)}
      <a href="/cities/">Cities and towns</a>
      <a href="/privacy.html">Privacy policy</a>
      <a href="/terms.html">Terms of use</a>
      <a href="mailto:{EMAIL}">Email us</a>
    </nav>
    <p>{SOURCES_LINE}</p>
    <p>© 2026 {BRAND}. Part of <a href="{HUB['url']}" rel="noopener">Eats Ranked</a>, restaurant apps state by state.</p>
    <p>Created by <a href="https://work-with-nick.com/" rel="author">Nick Soderstrom</a>.</p>
  </footer>
</div>
<script>
  // Once the App Store listing exists, paste its URL here (looks like https://apps.apple.com/app/id123456789).
  // Every button switches from "Ask for early access" to "Download on the App Store" automatically (then use Apple's badge artwork,
  // see store_button() in scripts/make-site.py). Also fill in the apple-itunes-app meta tag in <head> on every page, and put the
  // MobileApplication "offers" back in the landing page's JSON-LD (re-run scripts/make-site.py after editing it there).
  var APP_STORE_URL = "";
  if (APP_STORE_URL) {{
    document.querySelectorAll(".store-btn").forEach(function (b) {{ b.href = APP_STORE_URL; b.rel = "noopener"; }});
    document.querySelectorAll(".store-label").forEach(function (l) {{ l.textContent = "Download on the App Store"; }});
    document.querySelectorAll(".store-note").forEach(function (n) {{ n.textContent = "Free for iPhone and iPad."; }});
  }}
</script>
</body>
</html>
"""
    if BASE:   # served under /southcarolina-eats/: every root-relative link and asset gets the prefix
        doc = re.sub(r'(href|src|srcset)="/', rf'\1="{BASE}/', doc)
    doc = doc.replace(CSP_SLOT, csp_for(doc), 1)   # hashed last, over the exact bytes the browser will see
    os.makedirs(os.path.dirname(f"{DOCS}/{path}"), exist_ok=True)
    open(f"{DOCS}/{path}", "w").write(doc)
    (written if indexed else noindexed).append(path)
    return path


class Anchors:
    """Gives each place an id (name-zip) the first time it appears on a page, so ItemList items can point to page#id."""
    RESERVED = {"main", "about", "list", "honors", "oldest", "inspections", "cuisines", "more", "towns", "how", "what", "guides", "cities",
                "faq", "download", "screens", "pricing", "privacy", "groups", "counties", "lookup", "closures", "tiers", "lg-r", "lg-f", "lg-p",
                "cities-list", "inspections-col"} | {k for k, _ in ALL_GUIDES}

    def __init__(self, page_url):
        self.page_url, self.used, self.of = page_url, set(self.RESERVED), {}

    def take(self, p):
        if id(p) in self.of:
            return None
        base = slug(p.name + (" " + p.zip if p.zip else "")) or "place"
        a, n = base, 2
        while a in self.used:
            a, n = f"{base}-{n}", n + 1
        self.used.add(a)
        self.of[id(p)] = a
        return a

    def url(self, p):
        return f"{self.page_url}#{self.of[id(p)]}"


CHIPS = [(BBQ, "Whole-hog & mustard barbecue"), (SEAFOOD, "Lowcountry seafood"), (GULLAH, "Gullah Geechee cooking"), (MEAT3, "Meat-and-three")]


def place_item(p, anchors=None, show_fn=False, honors=False):
    facts = []
    if p.dishes:
        facts.append(f"<b>On the menu:</b> {e(p.dishes)}")
    if p.founded:
        facts.append(f"<b>Since</b> {e(str(p.founded))}")
    if p.season:
        facts.append(f"<b>Season:</b> {e(p.season)}")
    kinds = []
    if p.mi:
        kinds.append(('<span class="tag tag-mi">', e(MI[p.mi])))
    if p.jb_label():
        kinds.append(('<span class="tag tag-jb">', e(p.jb_label())))
    if p.hc:
        kinds += [('<span class="tag">', k) for t, k in CHIPS if p.tags & t]
    where = ", ".join(x for x in (p.addr, p.city) if x)
    aid = anchors.take(p) if anchors else None
    out = [f'<li id="{e(aid)}">' if aid else "<li>", f"<h3>{e(p.name)}</h3>", f'<p class="where">{e(where)}</p>']
    if kinds or facts:
        out.append('<p class="facts">' + "".join(f"{tag}{k}</span>" for tag, k in kinds) + (" " + " · ".join(facts) if facts else "") + "</p>")
    if p.note:
        out.append(f'<p class="note">{e(p.note)}</p>')
    if show_fn and p.fn:
        out.append(f'<p class="fine">{e(p.fn)}</p>')
    if honors and p.jbf:   # restaurateur-level honors have no chip, so say what the honor is
        out.append('<p class="fine">' + e("; ".join("James Beard: " + x for x in p.jbf.split("; "))) + "</p>")
    if p.site:
        host = re.sub(r"^https?://(www\.)?", "", p.site, flags=re.I).split("/")[0]
        out.append(f'<p class="link"><a href="{e(p.site)}" rel="noopener nofollow">{e(host)}</a></p>')
    out.append("</li>")
    return "".join(out)


def restaurant_ld(p, item_url):
    addr = {"@type": "PostalAddress"}
    if p.addr:
        addr["streetAddress"] = p.addr
    if p.city:
        addr["addressLocality"] = p.city
    addr["addressRegion"] = "SC"
    if p.zip:
        addr["postalCode"] = p.zip
    addr["addressCountry"] = "US"
    x = {"@type": "Restaurant", "name": p.name, "url": item_url, "address": addr}
    if p.lat is not None and p.lon is not None:
        x["geo"] = {"@type": "GeoCoordinates", "latitude": p.lat, "longitude": p.lon}
    if p.site:
        x["sameAs"] = p.site
    if p.founded:
        x["foundingDate"] = str(p.founded)
    if p.cuisine and p.cuisine not in ("Other", "Restaurant", "American & Other"):
        x["servesCuisine"] = p.cuisine
    return x


def item_list(name, places, url, anchors):
    """An all-on-one-page list: each item's url is its anchor on this page; the restaurant's own site goes in sameAs."""
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name, "url": url, "numberOfItems": len(places),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": restaurant_ld(p, anchors.url(p))} for i, p in enumerate(places)]}


def article_ld(url, headline, desc):
    return {"@context": "https://schema.org", "@type": "Article", "headline": headline, "description": desc,
            "datePublished": PUBLISHED, "dateModified": TODAY, "inLanguage": "en", "mainEntityOfPage": url,
            "image": f"{DOMAIN}/og.png", "author": ORG_REF, "publisher": ORG_REF}


# ---------------------------------------------------------------- counts shared by several pages
N_REST = len(REST)
N_TOWNS = len({p.city for p in REST if p.city})
N_COUNTIES = len({p.county for p in REST if p.county})
N_OFFICIAL = sum(1 for p in REST if p.r.get("t") == 2)
N_HC = len(HC_ANY)
N_JBF = sum(1 for p in HON_L if p.jbf)
N_MI = sum(1 for p in HON_L if p.mi)
N_STARS = sum(1 for p in HON_L if p.mi >= 3)
N_BIB = sum(1 for p in HON_L if p.mi == 2)
N_CLASSICS = sum(1 for p in HON_L if p.h & 1)
BAND_N = Counter(p.band for p in INS_L)
INS_PATH = "south-carolina-restaurant-inspection-grades.html"
HON_PATH = "south-carolina-michelin-james-beard-restaurants.html"
OLD_PATH = "south-carolina-oldest-restaurants.html"
GUIDE_PATH = {"bbq": "south-carolina-whole-hog-mustard-barbecue.html", "seafood": "lowcountry-grand-strand-seafood.html",
              "gullah": "gullah-geechee-restaurants.html", "meat3": "south-carolina-meat-and-three-drive-ins.html"}
GUIDE_NAME = {"bbq": "Whole-hog & mustard barbecue", "seafood": "Lowcountry & Grand Strand seafood", "gullah": "Gullah Geechee cooking",
              "meat3": "Meat-and-threes & drive-ins"}
GUIDE_SHORT = {"bbq": "Barbecue", "seafood": "Seafood", "gullah": "Gullah Geechee", "meat3": "Meat-and-threes"}
GUIDE_LINKS = ([("/" + GUIDE_PATH[k], GUIDE_NAME[k]) for k, _ in GUIDE_TAGS]
               + ([("/" + OLD_PATH, "Oldest restaurants")] if HAS_OLD else [])
               + [("/" + HON_PATH, "MICHELIN & James Beard"), ("/" + INS_PATH, "SCDA inspection grades")])
NAV[:] = [("/" + GUIDE_PATH[k], GUIDE_SHORT[k]) for k, _ in GUIDE_TAGS][:3] + [("/cities/", "Cities"), ("/explore/", "Search")]
INS_DATE = hdate(INS_THROUGH.get("scda", ""))

SOURCES_LINE = (f"Place data: hand-checked research by {BRAND} ({CHECKED}); retail food permits and posted inspection grades from the SC "
                "Department of Agriculture (SCDA), as SC Food Grades publishes them (maintained by the SC Department of Public Health for SCDA); "
                "Overture Maps Foundation places (CDLA Permissive 2.0); map outlines © OpenStreetMap contributors, Overture Maps Foundation (ODbL). "
                "Not affiliated with or endorsed by the State of South Carolina, SCDA, the SC Department of Public Health, any county or city, any "
                "restaurant or chain, the MICHELIN Guide or the James Beard Foundation. MICHELIN and the MICHELIN Guide are trademarks of Michelin; "
                "James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Places open and close, so check before you go.")


def by_region(places, key=lambda p: (p.city, p.name.lower())):
    groups = defaultdict(list)
    for p in places:
        groups[p.region or "Elsewhere"].append(p)
    order = REGION_ORDER + ["Elsewhere"]
    return [(REGION_NAME.get(r, "Elsewhere in South Carolina"), sorted(groups[r], key=key)) for r in order if groups.get(r)]


def region_sections(places, noun, plural_noun, anchors, **item_kw):
    toc = '<ul class="toc">' + "".join(f'<li><a href="#{slug(r)}">{e(r)}</a> ({len(ps)})</li>' for r, ps in by_region(places)) + "</ul>"
    secs = []
    for r, ps in by_region(places):
        anchors.used.update({slug(r), "h-" + slug(r)})
        secs.append(f'<section id="{slug(r)}" aria-labelledby="h-{slug(r)}"><h2 id="h-{slug(r)}">{e(r)}</h2>'
                    f'<p class="sub">{plural(len(ps), noun, plural_noun)}, by town.</p><ol class="places">'
                    + "".join(place_item(p, anchors, **item_kw) for p in ps) + "</ol></section>")
    return toc, "\n".join(secs)


# ---------------------------------------------------------------- city pages: which towns get one
CITY_WANTED = ["Charleston", "North Charleston", "Mount Pleasant", "Columbia", "West Columbia", "Greenville", "Spartanburg", "Myrtle Beach",
               "Murrells Inlet", "Hilton Head Island", "Bluffton", "Beaufort", "Florence", "Rock Hill", "Summerville", "Aiken", "Orangeburg"]
MIN_LISTED = 4   # hand-checked or honored places in the town itself (MIN_GUIDE's bar): fewer, and the town gets no page yet


def town_listed(c):
    return [p for p in REST if p.city == c and ((p.hc and p.tags) or p.mi or p.jbf)]


CITY_PAGES = [c for c in CITY_WANTED if any(p.city == c and p.lat is not None for p in REST) and len(town_listed(c)) >= MIN_LISTED]
CITY_SKIPPED = {c: len(town_listed(c)) for c in CITY_WANTED if c not in CITY_PAGES}


def city_url(c):
    return f"/cities/{slug(c)}.html"


def city_links(current=None):
    return '<ul class="cities">' + "".join(f'<li><a href="{city_url(c)}"{" aria-current=" + chr(34) + "page" + chr(34) if c == current else ""}>{e(c)}</a></li>'
                                           for c in CITY_PAGES) + "</ul>"


def other_guides(skip):
    return "Other guides: " + ", ".join(f'<a href="{u}">{e(t)}</a>' for u, t in GUIDE_LINKS if u != skip) + "."


def guide_page(path, h1, kicker, title_opts, desc_opts, lede, about_html, places, noun, plural_noun, list_name, region=True, **item_kw):
    url = f"{DOMAIN}/{path}"
    # counts are small or large enough that the written lengths can miss the 140-160 window: each option also gets fixed tails
    tails = (", with addresses and websites.", ", with each place's address and website.", ". Free iPhone app coming soon.", ", with addresses.",
             ". Free iPhone app.", ", with maps.")
    desc_opts = list(desc_opts) + [d.rstrip(".") + t for d in desc_opts for t in tails]
    title_opts = list(title_opts) + [t + f" | {BRAND}" for t in title_opts if BRAND not in t]
    title, desc = fit(title_opts, 50, 60, path + " title"), fit(desc_opts, 140, 160, path + " description")
    nav, bc = crumbs([("Home", "/"), (h1, "/" + path)])
    anchors = Anchors(url)
    if region:
        toc, secs = region_sections(places, noun, plural_noun, anchors, **item_kw)
        jump = f"<h2>Jump to a region</h2>\n    {toc}"
    else:
        secs = (f'<section id="list" aria-labelledby="h-list"><h2 id="h-list">Oldest first</h2><ol class="places">'
                f'{"".join(place_item(p, anchors, **item_kw) for p in places)}</ol></section>')
        jump = ""
    body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{kicker}</p>
    <h1>{e(h1)}</h1>
    <p class="lede">{lede}</p>
    <div class="cta-row">{store_button()}<span class="pill store-note">{STORE_NOTE}</span></div>
  </section>
  <section id="about">
    {about_html}
    <p class="fine">{other_guides("/" + path)} City pages: {", ".join(f'<a href="{city_url(c)}">{e(c)}</a>' for c in CITY_PAGES)}.</p>
    {jump}
  </section>
{secs}
  </main>"""
    page(path, title, desc, body, [article_ld(url, h1, desc), bc, item_list(list_name, places, url, anchors)])


def towns_text(places, k):
    return join_words([t for t, _ in Counter(p.city for p in places).most_common(k)])


def towns_counts(places, k=8):
    return ", ".join(f"{t} ({n})" for t, n in Counter(p.city for p in places).most_common(k))


def top_dishes(places, k=6, skip=()):
    c = Counter()
    for p in places:
        # sorted: a set's order changes from run to run, and ties in most_common() would reorder the copy on every rebuild
        for d in sorted({x.strip().lower() for x in re.split(r"[;,]", p.r.get("dish") or "") if x.strip()}):
            if d not in skip:
                c[d] += 1
    return ", ".join(f"{d} ({n})" for d, n in c.most_common(k) if n > 1)


HOW_BUILT = ("Our method: a place made the list only if a page names it for this food (the state tourism office's Discover South Carolina, "
             "local press or the place's own site) and something from 2025 or 2026 shows it's open: a dated page, the place's own site with "
             "its current hours when we looked, or a 2025–26 SC Department of Agriculture inspection. Its street address had to match our "
             "records. Review sites played no part, and places run by region and town rather than by anybody's score. Hours change, so check "
             "before you go.")
APP_LINE = (f"On your phone, {BRAND} orders this list by how far each place is from you, and a tap opens Apple Maps' live card with "
            "hours, photos and directions.")


def checked_kicker():
    return f"{BRAND} · checked by hand, {CHECKED}"


def seasonal_line(places):
    n = sum(1 for p in places if p.season)
    return f" {plural(n, 'place')} on this list {'notes a season' if n == 1 else 'note a season'}; seasonal is not closed." if n else ""


# ---------------------------------------------------------------- the five themed guides
assert all(len(v) > 1 for v in L.values()), "the guide copy writes plural nouns"


def guide(k, h1, titles, descs, lede, about, list_name, noun="place"):
    G = L[k]
    plural_noun = noun[:-1] + "ies" if noun.endswith("y") and noun[-2] not in "aeiou" else noun + "s"
    guide_page(GUIDE_PATH[k], h1, checked_kicker(), titles, descs, lede, about + f"""
    <h2>The list at a glance</h2>
    <p>Towns with the most: {e(towns_counts(G))}.{(" The dishes we found most often: " + e(top_dishes(G)) + ".") if top_dishes(G) else ""}</p>
    <p>{HOW_BUILT}</p>
    <p>{APP_LINE}</p>""", G, noun, plural_noun, list_name)


GUIDE_DEFS = {
    "bbq": ("South Carolina whole-hog & mustard barbecue",
            [lambda n: f"SC Whole-Hog & Mustard Barbecue: {n} Checked Joints", lambda n: f"South Carolina Barbecue: {n} Hand-Checked Pits | {BRAND}",
             lambda n: f"Whole Hog, Mustard Sauce & Hash: {n} SC Barbecue Joints"],
            [lambda n: f"{plural(n, 'South Carolina barbecue joint')} for whole hog, mustard sauce and hash and rice, each checked in {CHECKED} against a 2025–26 source, by region and town.",
             lambda n: f"South Carolina barbecue: {plural(n, 'pit')} for whole hog cooked over coals, Midlands mustard sauce and hash over rice, each checked in {CHECKED}."],
            lambda n: f"{plural(n, 'barbecue joint')} for South Carolina's own barbecue: whole hogs cooked over wood coals, the Midlands' yellow mustard sauce, and hash over rice, each checked in {CHECKED} against a 2025–26 source.",
            """<h2>Whole hog, four sauces and hash</h2>
    <p>South Carolina cooks the whole hog over wood coals and dresses it four ways, by region: vinegar and pepper along the coast and in the Pee Dee, a yellow mustard sauce through the Midlands, a light tomato sauce toward the west, and a heavier tomato sauce in the Upstate. The side is hash, a long-simmered stew of pork (or beef in the Upstate) served over rice. Barbecue is the State Picnic Cuisine by law. Many of the old pits open only a few days a week, so check the day before you drive.</p>""",
            "South Carolina whole-hog and mustard barbecue", "joint"),
    "seafood": ("Lowcountry & Grand Strand seafood",
                [lambda n: f"Lowcountry & Grand Strand Seafood: {n} Checked Places", lambda n: f"Shrimp & Grits, She-Crab Soup: {n} SC Seafood Spots",
                 lambda n: f"South Carolina Seafood: {n} Hand-Checked Places | {BRAND}"],
                [lambda n: f"{plural(n, 'place')} on the South Carolina coast for shrimp and grits, she-crab soup, oyster roasts and Calabash seafood, each checked in {CHECKED} against a 2025–26 source.",
                 lambda n: f"Lowcountry and Grand Strand seafood: {plural(n, 'restaurant')} for shrimp and grits, oysters and she-crab soup, each checked in {CHECKED}, by region and town."],
                lambda n: f"{plural(n, 'place')} for the coast's own cooking: shrimp and grits, she-crab soup, steam pots and oyster roasts, and Murrells Inlet's fried creek shrimp, each checked in {CHECKED} against a 2025–26 source.",
                """<h2>Shrimp, crab and oysters</h2>
    <p>From Hilton Head to Little River, the coast cooks what comes out of its creeks and sounds: shrimp over stone-ground grits, she-crab soup finished with a little sherry, oysters roasted over a fire and shoveled onto the table, steam pots, and the lightly fried Calabash-style shrimp of Murrells Inlet and the Grand Strand. We don't vouch for where any restaurant's shrimp comes from: ask. Under a state law in effect from October 28, 2026, South Carolina restaurants that serve imported shrimp must say so.</p>""",
                "Lowcountry and Grand Strand seafood", "place"),
    "gullah": ("Gullah Geechee restaurants",
               [lambda n: f"Gullah Geechee Restaurants in South Carolina ({n})", lambda n: f"Gullah Geechee Cooking: {n} Checked Kitchens | {BRAND}",
                lambda n: f"Gullah Geechee Cooking: {n} Hand-Checked SC Kitchens", lambda n: f"Gullah Geechee Restaurants: {n} Checked SC Kitchens"],
               [lambda n: f"{plural(n, 'kitchen')} for Gullah Geechee cooking in the Lowcountry and on the Sea Islands: okra soup, crab rice, garlic crabs and greens, each checked in {CHECKED}.",
                lambda n: f"Gullah Geechee cooking in South Carolina: {plural(n, 'place')} for okra soup, red rice, crab rice and garlic crabs, each checked in {CHECKED} against a 2025–26 source."],
               lambda n: f"{plural(n, 'kitchen')} for Gullah Geechee cooking, from St. Helena Island to Charleston's East Side, each checked in {CHECKED} against a 2025–26 source.",
               """<h2>The Sea Islands' table</h2>
    <p>The Gullah Geechee people, descendants of West and Central Africans enslaved on the rice and cotton plantations of the coast, kept a cooking tradition of their own: rice at the center of the meal, okra soup, red rice, crab and shrimp rice, lima beans, greens and the seafood of the creeks. These family kitchens, from the Sea Islands near Beaufort to Charleston and its neighbors, keep cooking it. The list is about the food each one serves; ask each kitchen about its own story.</p>""",
               "Gullah Geechee restaurants", "kitchen"),
    "meat3": ("South Carolina meat-and-threes & drive-ins",
              [lambda n: f"SC Meat-and-Threes & Drive-Ins: {n} Checked Places | {BRAND}", lambda n: f"Meat-and-Threes & Drive-Ins in South Carolina ({n})",
               lambda n: f"South Carolina Meat-and-Threes & Drive-Ins ({n} Checked)", lambda n: f"Meat-and-Threes & Old Drive-Ins: {n} Checked SC Places"],
              [lambda n: f"{plural(n, 'place')} for a meat and three sides from the steam table, soul food plates and the old drive-ins, each checked in {CHECKED} against a 2025–26 source."],
              lambda n: f"{plural(n, 'place')} for South Carolina's everyday table: a meat and three vegetables, soul food plates, and drive-ins that have served chili burgers since the 1940s and 1950s, each checked in {CHECKED}.",
              """<h2>A meat and three</h2>
    <p>Pick a meat, then three sides from the steam table: the lunch counter that feeds South Carolina's towns. The drive-ins on this list date from the 1940s through the 1960s. Hours vary, so check before you go.</p>""",
              "South Carolina meat-and-threes and drive-ins", "place"),
}
for k, _ in GUIDE_TAGS:
    h1, titles, descs, lede, about, list_name, noun = GUIDE_DEFS[k]
    n = len(L[k])
    guide(k, h1, [t(n) for t in titles], [d(n) for d in descs], lede(n), about, list_name, noun)

# ---------------------------------------------------------------- MICHELIN and James Beard
guide_page(HON_PATH, "South Carolina MICHELIN & James Beard restaurants", f"{BRAND} · honors current as of {CHECKED}",
           [f"South Carolina MICHELIN & James Beard Restaurants | {BRAND}", "MICHELIN & James Beard Restaurants in South Carolina",
            f"SC MICHELIN Stars, Bib Gourmands & James Beard | {BRAND}"],
           [f"{plural(len(HON_L), 'South Carolina restaurant')} honored by the MICHELIN Guide American South or the James Beard Foundation, from Greenville to Charleston, by region and town.",
            f"{plural(N_MI, 'restaurant')} in the MICHELIN Guide American South 2026 and {N_JBF} James Beard honorees in South Carolina, by region and town, with each honor named."],
           f"{plural(len(HON_L), 'South Carolina restaurant')} honored by the MICHELIN Guide American South ({N_MI}: {plural(N_STARS, 'star', 'stars')}, {plural(N_BIB, 'Bib Gourmand')} and the rest Recommended) or the James Beard Foundation ({N_JBF}, with {plural(N_CLASSICS, 'America’s Classic')}).",
           f"""<h2>What counts as an honor here</h2>
    <p>Two sources, reported as facts rather than scores: the MICHELIN Guide's American South selection for 2026 (One Star, Bib Gourmand and Recommended, each labeled as exactly that), and the James Beard Foundation's Restaurant and Chef Awards (winners from any year, and 2025 and 2026 semifinalists and finalists) with its America's Classics. Where an honor went to a chef, the line under the place names them. Reader polls, "best of" roundups and review-site stars don't count.</p>
    <p class="fine">MICHELIN and the MICHELIN Guide are trademarks of Michelin. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. {BRAND} is not affiliated with either.</p>""",
           HON_L, "restaurant", "restaurants", "South Carolina MICHELIN and James Beard restaurants", honors=True)

# ---------------------------------------------------------------- oldest
if HAS_OLD:
    oldest_named = next((p for p in OLD_L if p.promo_ok()), None)
    assert all(p.founded <= 1960 for p in OLD_L), "the oldest-places copy says 'since 1960 or earlier'"
    from_line = f" The oldest, {e(oldest_named.name)} in {e(oldest_named.city)}, goes back to {oldest_named.founded}." if oldest_named else ""
    guide_page(OLD_PATH, "South Carolina's oldest restaurants", checked_kicker(),
               [f"South Carolina's Oldest Restaurants: {len(OLD_L)} Places", f"Oldest Restaurants in South Carolina ({len(OLD_L)}) | {BRAND}"],
               [f"{plural(len(OLD_L), 'South Carolina restaurant')} open at the same address since 1960 or earlier, oldest first, each with a note on what its founding year rests on."],
               f"Places that have fed South Carolina from the same address since 1960 or before: {plural(len(OLD_L), 'place')} in all, oldest first.{from_line}",
               """<h2>Which year counts</h2>
    <p>We count from the year a place opened at its current address, going by the place's own history or a published one.</p>""",
               OLD_L, "place", "places", "South Carolina's oldest restaurants", region=False, show_fn=True)

# ---------------------------------------------------------------- the inspections explainer (counts only: no place is named here)
url = f"{DOMAIN}/{INS_PATH}"
n_ins = len(INS_L)
nav, bc = crumbs([("Home", "/"), ("SCDA inspection grades", "/" + INS_PATH)])
title = fit(["South Carolina Restaurant Inspection Grades, Explained", "SC Restaurant Grades: What A, B and C Mean | " + BRAND,
             "South Carolina Restaurant Grades: A, B and C Explained"], 50, 60, "inspections title")
desc = fit([f"What South Carolina's posted restaurant grades mean, how the SC Department of Agriculture inspects, and where {n_ins:,} places we list stood at their latest.",
            f"South Carolina's A, B and C restaurant grades explained: who inspects, what each grade means, and the latest posted grade for {n_ins:,} places we list."],
           140, 160, "inspections description")
assert set(BAND_N) <= {"A", "B", "C"}, BAND_N


def grade_items():
    cls = {"A": "ok", "B": "mid", "C": "low"}
    return "".join(f'<li><span class="res res-{cls[b]}">Grade {b}</span> {plural(BAND_N.get(b, 0), "place")}</li>' for b in ("A", "B", "C"))


body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} guide · state records</p>
    <h1>South Carolina restaurant inspection grades, explained</h1>
    <p class="lede">One agency inspects South Carolina's restaurants: since July 1, 2024, the SC Department of Agriculture (SCDA) permits and inspects retail food establishments statewide under Regulation 61-25, and it posts a letter grade after each inspection. Here is what the grades mean, and where the {n_ins:,} places we list stood at their latest.</p>
  </section>
  <section id="groups">
    <h2>What the grades mean</h2>
    <p class="sub">SCDA scores each inspection out of 100 and posts a letter grade at the establishment: A above 87 points, B from 78 to 87, C below 78. Under section 8-403.10(G) of the regulation, the posted grade can differ from that inspection's score, and SC Food Grades publishes the posted grade and its date, not the score. So we show the grade as posted and compute no grade or score of our own.</p>
    <ul class="groups">
      <li><h3>The latest posted grade, statewide</h3><p>For {plural(n_ins, "place")} we list, matched to their SCDA permit, as of the latest record through {e(INS_DATE)}:</p><ul>{grade_items()}</ul><p class="count"><a href="{e(SCDA_GRADES)}" rel="noopener">SCDA's explanation of the grades</a> · <a href="{e(FOOD_GRADES)}" rel="noopener">SC Food Grades</a>.</p></li>
      <li><h3>Kinds of inspection</h3><p>Routine inspections come one to four times a year, depending on a place's food processes and its record; a follow-up comes within ten days of a routine inspection that needs one. "Permit" visits are pre-operational inspections before a new permit or a change of owner. A permit suspension notice (posted as "S") takes the grade card down until SCDA reinstates the permit; we leave such a place off our lists.</p></li>
    </ul>
    <p>One inspection is a snapshot of one day. We don't list places by their grades here; the web search can sort its inspection list by grade, and each place shows its records for the last three years, with a link to each report.</p>
    <p class="fine">SCDA's note on its data: “{e(SCDA_NOTE)}”</p>
  </section>
  <section id="lookup">
    <h2>Look a place up</h2>
    <p>Open any place in the <a href="/explore/">{BRAND} web app</a> for its SCDA permit, its latest posted grade and its recent inspections, or search <a href="{e(FOOD_GRADES)}" rel="noopener">SC Food Grades</a>, which the SC Department of Public Health maintains for SCDA.</p>
    <p class="fine">{other_guides("/" + INS_PATH)}</p>
  </section>
  </main>"""
page(INS_PATH, title, desc, body, [article_ld(url, "South Carolina restaurant inspection grades, explained", desc), bc])

# ---------------------------------------------------------------- city pages
city_stats = {}
SEC_DEFS = [  # key, long title phrase, short title phrase, h1 phrase, description phrase builder (guides with a page only)
    d for d in [
    ("bbq", "Barbecue", "BBQ", "barbecue", lambda n: plural(n, "hand-checked barbecue joint")),
    ("seafood", "Lowcountry Seafood", "Seafood", "seafood", lambda n: plural(n, "place for Lowcountry seafood", "places for Lowcountry seafood")),
    ("gullah", "Gullah Geechee Cooking", "Gullah Geechee", "Gullah Geechee kitchens", lambda n: plural(n, "Gullah Geechee kitchen")),
    ("meat3", "Meat-and-Threes", "Meat & Three", "meat-and-threes", lambda n: plural(n, "meat-and-three or drive-in", "meat-and-threes and drive-ins")),
    ] if d[0] in L]
SEC_ORDER = [k for k, *_ in SEC_DEFS] + ["hon", "oldest"]
CITY_INFO = {}
for c in CITY_PAGES:
    here = [p for p in REST if p.city == c]
    info = {k: sorted([p for p in L[k] if p.city == c], key=P.featured_key) for k, _ in GUIDE_TAGS}
    info["hon"] = sorted([p for p in HON_L if p.city == c], key=hon_key)
    info["oldest"] = [p for p in OLD_L if p.city == c] if HAS_OLD else []
    info["insp"] = Counter(p.band for p in INS_L if p.city == c)
    info["n_ins"] = sum(1 for p in INS_L if p.city == c)
    info["cuis"] = Counter(p.cuisine for p in here if p.cuisine and p.cuisine not in ("Other", "American & Other")).most_common(10)
    info["n_town"] = len(here)
    listed, seen = [], set()
    for k in SEC_ORDER:
        for p in info[k]:
            if id(p) not in seen:
                seen.add(id(p)); listed.append(p)
    info["listed"] = listed
    CITY_INFO[c] = info
    city_stats[c] = {"restaurants": len(here), "listed": len(listed), **{k: len(info[k]) for k in SEC_ORDER},
                     "inspection_grades": info["n_ins"], "grade_counts": dict(info["insp"])}


def city_sections(info):
    """The sections a city page has, biggest first: (key, long, short, h1 phrase, description phrase)."""
    out = [(k, lt, st, h1p, dp(len(info[k]))) for k, lt, st, h1p, dp in SEC_DEFS if info[k]]
    if info["hon"]:
        out.append(("hon", "MICHELIN & James Beard", "MICHELIN", "MICHELIN and James Beard honorees",
                    plural(len(info["hon"]), "MICHELIN or James Beard honoree", "MICHELIN and James Beard honorees")))
    if info["oldest"]:
        k_old = len(info["oldest"])   # "1 of South Carolina's oldest restaurants", not "the oldest" (one place isn't the town's all)
        out.append(("oldest", "Oldest Restaurants", "Oldest Places", "oldest restaurants",
                    f"1 of South Carolina's oldest restaurants (from {info['oldest'][0].founded})" if k_old == 1
                    else f"{k_old} of South Carolina's oldest restaurants (back to {info['oldest'][0].founded})"))
    return sorted(out, key=lambda s: (-len(info[s[0]]), SEC_ORDER.index(s[0])))


def tjoin(xs):
    if len(xs) == 1:
        return xs[0]
    conj = " and " if any("&" in x for x in xs) else " & "
    return ", ".join(xs[:-1]) + conj + xs[-1]


def city_title(c, secs):
    cands = []
    for k in range(min(len(secs), 3), 0, -1):
        for col in (1, 2):
            J = tjoin([s[col] for s in secs[:k]])
            # "<town> restaurants" is what people search, so those forms come first
            forms = ([f"{c} Restaurants: {J}", f"{c}, SC Restaurants: {J}", f"{c} Restaurants: {J} | {BRAND}", f"{c}, SC Restaurants: {J} | {BRAND}"]
                     if "Restaurant" not in J else [])
            forms += [f"{c} {J} | {BRAND}", f"{c}, SC {J} | {BRAND}", f"{c}, South Carolina {J}", f"{c}, SC {J}", f"{c} {J}"]
            if "Restaurant" not in J:
                forms += [f"{c} {J} & Restaurants", f"{c} {J} & Restaurants | {BRAND}", f"{c}, SC {J} & Restaurants"]
            cands += forms
    cands += [f"{c} Restaurants: What {c} Eats | {BRAND}", f"{c}, SC Restaurants by Kind | {BRAND}", f"{c}, SC Restaurants, Cafés & Bars | {BRAND}",
              f"{c}, South Carolina Restaurants, Cafés and Bars", f"{c} Restaurants, Cafés & Bars | {BRAND}", f"{c}, SC: Restaurants, Cafés & More | {BRAND}",
              f"{c}, SC: Restaurants, Cafés & Bakeries | {BRAND}"]
    return fit(cands, 50, 60, c + " title")


def city_desc(c, info, secs):
    n_town = info["n_town"]
    leads = [f"In {c}, South Carolina", f"{c}, South Carolina", f"{c}, SC"]
    tails = [f". Search {n_town:,} {c} restaurants, cafés and bars", f". Search {n_town:,} local places to eat",
             f", plus {n_town:,} local places to eat on a searchable map", f", plus {n_town:,} more local places to eat", ""]
    extras = ["", f" Checked in {CHECKED}.", " Free iPhone app coming soon.", f" Checked in {CHECKED}. Free iPhone app coming soon."]

    def gen():
        for k in range(len(secs), 0, -1):
            J = join_words([s[4] for s in secs[:k]])
            for lead in leads:
                for tail in tails:
                    for x in extras:
                        yield f"{lead}: {J}{tail}.{x}"
    return fit(list(dict.fromkeys(s.replace("..", ".") for s in gen())), 140, 160, c + " description")


SEC_HEAD = {"bbq": ("Whole-hog & mustard barbecue", "bbq"), "seafood": ("Lowcountry seafood", "seafood"),
            "gullah": ("Gullah Geechee cooking", "gullah"), "meat3": ("Meat-and-threes & drive-ins", "meat3")}
GUIDE_COUNT_NOUN = {"bbq": "South Carolina barbecue joints", "seafood": "places for Lowcountry and Grand Strand seafood",
                    "gullah": "Gullah Geechee kitchens", "meat3": "meat-and-threes and drive-ins"}
SINGULAR = {"places for Lowcountry and Grand Strand seafood": "place for Lowcountry and Grand Strand seafood",
            "meat-and-threes and drive-ins": "meat-and-three or drive-in"}


def grade_bits(cnt):
    return join_words([f"{plural(cnt[b], 'place')} with an {b}" if b == "A" else f"{plural(cnt[b], 'place')} with a {b}"
                       for b in ("A", "B", "C") if cnt.get(b)])


for c in CITY_PAGES:
    info = CITY_INFO[c]
    path = f"cities/{slug(c)}.html"
    url = DOMAIN + "/" + path
    anchors = Anchors(url)
    secs = city_sections(info)
    title = city_title(c, secs)
    desc = city_desc(c, info, secs)
    k = 3
    while k > 1 and len(join_words([s[3] for s in secs[:k]])) > 48:   # a heading, not the whole table of contents
        k -= 1
    h1_bits = [s[3] for s in secs[:k]]
    h1 = f"{c} restaurants" + (": " + join_words(h1_bits + (["more"] if len(secs) > k else [])) if secs else "")
    nav, bc = crumbs([("Home", "/"), ("Cities", "/cities/"), (c, "/" + path)])
    counts = [s[4] for s in secs]
    n_hc = sum(1 for p in info["listed"] if p.hc and p.tags)
    lede = (f"What {e(c)} has on our lists: {e(join_words(counts))}. "
            + (f"Each hand-checked place had a 2025 or 2026 source when we looked in {CHECKED}. " if n_hc else "")
            + f"In all, {BRAND} maps {info['n_town']:,} restaurants, cafés, bars and bakeries in {e(c)}, nearest first on your phone.")
    parts = [f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} · {e(c)}, South Carolina</p>
    <h1>{e(h1)}</h1>
    <p class="lede">{lede}</p>
    <div class="cta-row">{store_button()}<span class="pill store-note">{STORE_NOTE}</span></div>
  </section>"""]
    for s in secs:
        key = s[0]
        if key in SEC_HEAD:
            head, gk = SEC_HEAD[key]
            parts.append(f'<section id="{key}" aria-labelledby="h-{key}"><h2 id="h-{key}">{e(head)} in {e(c)}</h2><p class="sub">Each one checked in {CHECKED} against a 2025–26 source. Statewide: <a href="/{GUIDE_PATH[gk]}">{plural(len(L[gk]), SINGULAR.get(GUIDE_COUNT_NOUN[gk], GUIDE_COUNT_NOUN[gk][:-1]), GUIDE_COUNT_NOUN[gk])}</a>.</p><ol class="places">'
                         + "".join(place_item(p, anchors) for p in info[key]) + "</ol></section>")
        elif key == "hon":
            parts.append(f'<section id="honors" aria-labelledby="h-honors"><h2 id="h-honors">MICHELIN and James Beard honorees in {e(c)}</h2><p class="sub">Restaurants in the MICHELIN Guide American South or named by the James Beard Foundation, reported as facts rather than scores. Statewide: <a href="/{HON_PATH}">{plural(len(HON_L), "honored South Carolina restaurant")}</a>.</p><ol class="places">'
                         + "".join(place_item(p, anchors, honors=True) for p in info["hon"]) + "</ol></section>")
        elif key == "oldest":
            parts.append(f'<section id="oldest" aria-labelledby="h-oldest"><h2 id="h-oldest">Oldest restaurants in {e(c)}</h2><p class="sub">In business at this address since 1960 or before, going by the place itself or a published history, listed from the oldest. Each note gives the source of the year. Statewide: <a href="/{OLD_PATH}">South Carolina\'s oldest restaurants</a>.</p><ol class="places">'
                         + "".join(place_item(p, anchors, show_fn=True) for p in info["oldest"]) + "</ol></section>")
    if info["n_ins"]:   # counts only, as on the grades page: no place is named by its grade
        parts.append(f'<section id="inspections" aria-labelledby="h-inspections"><h2 id="h-inspections">Inspection grades in {e(c)}</h2><p class="sub">'
                     f"The SC Department of Agriculture's latest posted grade for the {plural(info['n_ins'], 'place')} we list in {e(c)} that we matched to an SCDA permit: "
                     f"{e(grade_bits(info['insp']))}, from records through {e(INS_DATE)}. Each place's grade, with its recent inspections and reports, is in the "
                     f'<a href="/explore/#g=inspections&amp;town={e(urllib.parse.quote(c))}">web search</a>; what the grades mean: '
                     f'<a href="/{INS_PATH}">South Carolina restaurant inspection grades, explained</a>. We show each grade as posted and compute none.</p></section>')
    if info["cuis"]:
        rows = "".join(f'<tr><td>{e(k)}</td><td class="n">{n:,}</td></tr>' for k, n in info["cuis"])
        parts.append(f'<section id="cuisines" aria-labelledby="h-cuisines"><h2 id="h-cuisines">What {e(c)} eats</h2><p class="sub">Kinds of food among the {info["n_town"]:,} places we list in {e(c)}, counted from open map data and SCDA\'s permit list.</p><table><thead><tr><th scope="col">Kind of place</th><th scope="col" class="n">Places</th></tr></thead><tbody>{rows}</tbody></table></section>')
    parts.append(f'<section id="more" aria-labelledby="h-more"><h2 id="h-more">Other South Carolina towns with a page</h2>{city_links(current=c)}<p class="fine"><a href="/cities/">The cities and towns index</a></p></section>\n  </main>')
    lds = [article_ld(url, h1, desc), bc]
    if info["listed"]:
        lds.append(item_list(f"{c}: " + join_words([s[3] for s in secs]), info["listed"], url, anchors))
    page(path, title, desc, "\n".join(parts), lds)


# ---------------------------------------------------------------- cities index
url = f"{DOMAIN}/cities/"
nav, bc = crumbs([("Home", "/"), ("Cities", "/cities/")])
cards = []
for c in CITY_PAGES:
    info = CITY_INFO[c]
    bits = [f"{s[3]} ({len(info[s[0]])})" for s in city_sections(info)]
    line = (join_words(bits) + ". " if bits else "") + f"{info['n_town']:,} places to eat in all."
    cards.append(f'<a class="card" href="{city_url(c)}"><h3>{e(c)}</h3><p>{e(line[0].upper() + line[1:])}</p></a>')
title = fit([f"South Carolina Towns: Restaurant Guides | {BRAND}", f"SC City Restaurant Guides: {plural(len(CITY_PAGES), 'Town')} | {BRAND}",
             f"South Carolina Cities & Towns: Restaurant Guides", f"SC Towns: Barbecue, Seafood & Restaurant Guides | {BRAND}"], 50, 60, "cities title")
desc = fit([f"Restaurant guides for {plural(len(CITY_PAGES), 'South Carolina city and town', 'South Carolina cities and towns')}: barbecue joints, Lowcountry seafood, Gullah Geechee kitchens, MICHELIN and James Beard honors.",
            f"City-by-city South Carolina restaurant guides for {plural(len(CITY_PAGES), 'town')}: whole-hog barbecue, shrimp and grits, Gullah Geechee cooking and MICHELIN honors.",
            f"South Carolina restaurant guides for {plural(len(CITY_PAGES), 'town')}: hand-checked barbecue and seafood, Gullah Geechee kitchens, and MICHELIN and James Beard honors."],
           140, 160, "cities description")
skipped_line = (f" Other towns get a page once they have at least {MIN_LISTED} hand-checked or honored places; until then, "
                f'<a href="/explore/">search them</a>.')
body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} · cities and towns</p>
    <h1>South Carolina cities and towns</h1>
    <p class="lede">A page for South Carolina cities and towns that have enough hand-checked or honored places to say something real: the barbecue joints, seafood places and MICHELIN and James Beard honorees that are actually there, and how SCDA's latest posted grades fall in each.{skipped_line}</p>
  </section>
  <section id="cities-list">
    <h2>Pick a town</h2>
    <div class="grid2">{"".join(cards)}</div>
  </section>
  </main>"""
page("cities/index.html", title, desc, body, [bc], og_type="website")

# ---------------------------------------------------------------- web app (docs/explore/): data split + page
# The web app lists restaurants only (the venues the app hides by default, such as stadium stands and gas-station counters, stay out).
# Three kinds of file, to keep the first load small for ~25,000 places:
# - core.json: the list, search and map columns. Places are ordered by region, county, town, zip and street, so neighbouring rows
#   share their town, zip and street words and gzip well; coordinates are integer steps of 0.0001° from the previous row ("dla"/"dlo"),
#   and the latest posted grade is its source ("ij", 0 = SCDA) and grade index ("ib") plus a day number from 2000-01-01 ("idn").
# - ids.json: each place's stable id (the app's id), in core order. Fetched right after the list renders; saved places and shared
#   #p= links wait for it.
# - detail-<county>.json: phones, websites, notes, SCDA permits and inspection histories, keyed by core index, one file per county
#   (Greenville's is the biggest), fetched when someone opens (or points at) a place there.
os.makedirs(f"{DOCS}/data", exist_ok=True)
DFILES = [slug(c) for c in COUNTIES] + ["other"]   # detail file per county index; "other" for a place with no county
CAL = {a: {"groups": {g: {"n": v.get("n"), "official": v.get("official")} for g, v in (c.get("groups") or {}).items()}}
       for a, c in (D.get("calibration") or {}).items() if isinstance(c, dict)}
DAY0 = "2000-01-01"


def day_num(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return (dt.date(int(m[1]), int(m[2]), int(m[3])) - dt.date(2000, 1, 1)).days if m else None


def street_key(a):
    m = re.match(r"\s*(\d+)\s*(.*)", a or "")
    return (m[2].lower(), int(m[1]) if len(m[1]) < 9 else 0) if m else ((a or "").lower(), 0)


def web_order(p):
    rg = REGION_ORDER.index(p.region) if p.region else len(REGION_ORDER)
    return (rg, p.county or "", p.city or "", p.zip, street_key(p.addr), p.name.lower(), p.r["id"])


WEB = sorted(REST, key=web_order)
CORE_KEYS = ["n", "c", "co", "cu", "t", "s", "a", "z", "b", "ch", "g", "hc", "ip", "f", "h", "mi", "dish"]
cols = {k: [] for k in CORE_KEYS + ["dla", "dlo", "jb", "ij", "ib", "idn"]}
ids, shards = [], defaultdict(dict)
prev = [0, 0]
for i, p in enumerate(WEB):
    r = p.r
    ids.append(r["id"])
    for k in CORE_KEYS:
        v = r.get(k)
        if k == "a" and v:
            v = p.addr
        cols[k].append(v)
    for k, j, v in (("dla", 0, p.lat), ("dlo", 1, p.lon)):
        if v is None:
            cols[k].append(None)
        else:
            q = round(v * 10000)
            cols[k].append(q - prev[j])
            prev[j] = q
    dk = r["co"] if r.get("co") is not None else len(COUNTIES)   # the detail file this place's extras go in
    if r.get("co") is None:
        cols["co"][-1] = len(COUNTIES)
    cols["jb"].append(1 if r.get("jbf") else None)
    ins = p.ins or {}
    cols["ij"].append(ins.get("j"))
    cols["ib"].append(ins.get("b"))
    cols["idn"].append(day_num(ins.get("d")))
    d = {k: r[k] for k in ("ph", "note", "seas", "fn", "jbf", "lic") if r.get(k)}
    if p.site:
        d["w"] = p.site
    if ins.get("h"):
        d["in"] = {"n": ins.get("n"), "h": ins["h"]}
    if d:
        shards[dk][str(i)] = d
assert len(set(ids)) == len(ids), "place ids must be unique (saved places and #p= links use them)"
for f in glob.glob(f"{DOCS}/data/detail*.json"):   # files from an older layout or a region that emptied
    os.remove(f)
# columns that are mostly empty (hand-checked and honored facts) go as [[index, value], ...] instead of 25,000 nulls
sparse = {k: [[i, v] for i, v in enumerate(cols.pop(k)) if v is not None]
          for k in list(cols) if sum(v is not None for v in cols[k]) < len(WEB) * 0.05}
core = {"generated": D["generated"], "inspections_through": INS_THROUGH,
        "guides": [k for k, _ in ALL_GUIDES if L_ALL[k]], "day0": DAY0, "n": len(WEB), "cities": CITIES, "cuisines": CUISINES, "counties": COUNTIES + ["South Carolina"],
        "brands": D["brands"], "srcs": D["srcs"], "results": RESULTS, "itypes": ITYPES, "calibration": CAL, "cols": cols, "sparse": sparse,
        "dfiles": [f if dk in shards else None for dk, f in enumerate(DFILES)]}   # null: that county has no extras, so no file
assert all("," not in x for x in ids)
# ids and details are keyed by row, so a file from one build must never meet another build's core.json (a browser cache can outlive a
# deploy by GitHub's 10 minutes): every file carries the build's version, the page fetches with ?v=, and the web app refuses a mismatch
DATA_VER = hashlib.sha256(json.dumps([core, ids, shards], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
DETAIL_FILES = {}
for dk, d in sorted(shards.items()):
    fn = f"detail-{DFILES[dk]}.json"
    json.dump({"_v": DATA_VER, **d}, open(f"{DOCS}/data/{fn}", "w"), separators=(",", ":"), ensure_ascii=False)
    DETAIL_FILES[fn] = len(d)
json.dump({"ver": DATA_VER, **core}, open(f"{DOCS}/data/core.json", "w"), separators=(",", ":"), ensure_ascii=False)
json.dump({"v": DATA_VER, "ids": ",".join(ids)}, open(f"{DOCS}/data/ids.json", "w"), separators=(",", ":"))   # one string: smaller than an array
json.dump(json.load(open(f"{ROOT}/data/app/sc_shapes.json")), open(f"{DOCS}/data/sc_shapes.json", "w"), separators=(",", ":"))


def sizes(path):
    raw = open(path, "rb").read()
    return len(raw), len(gzip.compress(raw, 9))


SIZES = {os.path.relpath(f, DOCS): sizes(f) for f in sorted(glob.glob(f"{DOCS}/data/*.json"))}

EXPLORE_CSS = """
  [hidden] { display: none !important; }
  .ex-hero { padding: 28px 0 8px; }
  .ex-hero h1 { font-size: clamp(30px, 6vw, 44px); }
  .ex-controls { background: var(--bg); padding: 10px 0 8px; border-bottom: 1px solid var(--rule); }
  .ex-guides { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: none; }
  @media (min-width: 601px) { .ex-guides { flex-wrap: wrap; overflow: visible; } }
  @media (max-width: 600px) { .ex-guides { padding-right: 32px; -webkit-mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent); mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent); } }
  .ex-guides button, .ex-view button, .ex-small { flex: 0 0 auto; border: 1px solid var(--rule); background: var(--surface); color: var(--accent); border-radius: 999px; padding: 7px 12px; font: 600 14px/1.2 system-ui, sans-serif; font-family: inherit; cursor: pointer; }
  .ex-guides button[aria-pressed="true"], .ex-view button[aria-pressed="true"] { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
  .ex-row1 { display: flex; gap: 8px; align-items: center; }
  .ex-row1 input[type=search] { flex: 1; min-width: 0; font: 16px/1.3 system-ui, sans-serif; font-family: inherit; padding: 10px 12px; border: 2px solid var(--accent); border-radius: 12px; background: var(--surface); color: var(--ink); }
  .ex-row2 { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; font-size: 14px; }
  .ex-row2 select { font: 14px system-ui, sans-serif; font-family: inherit; padding: 6px 8px; border: 1px solid var(--rule); border-radius: 8px; background: var(--surface); color: var(--ink); max-width: 46vw; }
  .ex-view { margin-left: auto; display: flex; gap: 4px; }
  #ex-count { margin: 8px 0 0; font-size: 14px; color: var(--muted); }
  #ex-sub { margin: 4px 0 0; font-size: 14px; color: var(--ink2); }
  #ex-locmsg { font-size: 13px; color: var(--muted); margin: 4px 0 0; }
  .ex-list { list-style: none; padding: 0; margin: 10px 0; }
  .ex-list li + li { border-top: 1px solid var(--rule); }
  .ex-row { width: 100%; display: flex; gap: 12px; align-items: center; text-align: left; background: none; border: 0; padding: 12px 4px; cursor: pointer; color: var(--ink); font: inherit; }
  .ex-row:hover { background: var(--surface2); }
  .ex-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; overflow-wrap: anywhere; }
  .ex-main b { font-weight: 650; }
  .ex-town { font-size: 14px; color: var(--muted); }
  .tag-dash { background: transparent; color: var(--muted); border: 1px dashed var(--rule); }
  .ex-metric { text-align: right; display: flex; flex-direction: column; align-items: flex-end; max-width: 46%; }
  .ex-metric b { font: 800 22px/1 var(--display); color: var(--accent); }
  .ex-metric small { font-size: 11px; color: var(--muted); }
  .ex-rank { flex: 0 0 34px; height: 34px; display: grid; place-items: center; font: 800 20px var(--display); color: var(--accent); border-radius: 8px; }
  .ex-rank.top { background: var(--orange); color: var(--on-orange); }
  .ex-empty { padding: 24px 4px; color: var(--muted); }
  #ex-more { display: block; margin: 8px auto 24px; }
  #ex-mapwrap { position: relative; height: min(72vh, 720px); margin: 10px 0 20px; border: 1px solid var(--rule); border-radius: 16px; overflow: hidden; background: #eef0f5; }
  #ex-map { width: 100%; height: 100%; display: block; touch-action: none; cursor: grab; }
  .ex-zoom { position: absolute; right: 10px; top: 10px; display: flex; flex-direction: column; gap: 6px; }
  .ex-zoom button { width: 44px; height: 44px; border-radius: 10px; border: 1px solid #d7dbe6; background: #fff; color: #1b2a57; font: 700 22px/1 system-ui, sans-serif; cursor: pointer; }
  #ex-maphint { position: absolute; left: 10px; top: 10px; margin: 0; font-size: 13px; background: #fff; padding: 3px 8px; border-radius: 999px; color: #1b2a57; pointer-events: none; }
  #ex-mapattr { position: absolute; right: 0; bottom: 0; margin: 0; font-size: 11px; background: rgba(255,255,255,.85); padding: 2px 6px; border-radius: 6px 0 0 0; color: #1b2a57; pointer-events: none; }
  .ex-panel { position: fixed; z-index: 20; right: 0; top: 0; bottom: 0; width: min(440px, 100%); overflow-y: auto; background: var(--surface); border-left: 1px solid var(--rule); box-shadow: -8px 0 24px rgba(0,0,0,.12); padding: 18px 20px 40px; }
  @media (max-width: 600px) { .ex-panel { top: auto; height: 86vh; border-left: 0; border-top: 4px solid var(--orange); border-radius: 18px 18px 0 0; } }
  .ex-close { position: sticky; top: 0; float: right; width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--rule); background: var(--surface); font-size: 24px; line-height: 1; cursor: pointer; color: var(--ink); }
  .ex-kicker { margin: 0; font-size: 12px; font-weight: 700; letter-spacing: .1em; color: var(--accent2); }
  .ex-panel h2 { font-size: 34px; margin: 4px 0 6px; text-transform: uppercase; overflow-wrap: anywhere; }
  .ex-addr, .ex-dist { margin: 0 0 4px; color: var(--ink2); font-size: 15px; }
  .ex-actions { margin: 14px 0 8px; display: grid; gap: 8px; }
  .ex-apple { justify-content: center; }
  .ex-act-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .ex-act-row a, .ex-act-row button { flex: 1; min-width: 88px; text-align: center; padding: 10px; border: 1px solid var(--rule); border-radius: 12px; text-decoration: none; color: var(--accent); font: 600 14px system-ui, sans-serif; font-family: inherit; background: var(--surface); cursor: pointer; }
  .ex-act-row button[aria-pressed="true"] { background: var(--soft); color: #1b2a57; }
  .ex-sec { margin-top: 18px; }
  .ex-sec h3 { font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--rule); padding-bottom: 6px; margin-bottom: 8px; }
  .ex-sec p, .ex-sec li { font-size: 15px; color: var(--ink2); margin: 6px 0; }
  .ex-sec ul { padding-left: 18px; }
  .ex-kv { display: flex; justify-content: space-between; gap: 12px; font-size: 15px; padding: 3px 0; }
  .ex-kv span { color: var(--ink2); flex: 0 0 auto; max-width: 40%; }
  .ex-kv b { text-align: right; overflow-wrap: anywhere; }
  .ex-fine { font-size: 13px !important; color: var(--muted) !important; }
  .ex-result { display: flex; align-items: center; gap: 10px; font-weight: 600; flex-wrap: wrap; }
  .ex-app { margin-top: 22px; font-size: 14px; color: var(--muted); }
  body.ex-open { overflow: hidden; }
  .ex-backdrop { position: fixed; inset: 0; z-index: 19; background: rgba(15, 22, 48, .32); }
  /* phones: 16px or more in the search box and the selects, or iOS Safari zooms the page when one gets focus */
  @media (max-width: 600px) { .ex-row1 input[type=search], .ex-row2 select { font-size: 16px; } }
  /* the sort's longest choice ("Latest inspection first") at 16px: wider than 46vw, so on phones it may use the row */
  @media (max-width: 600px) { #ex-sort { max-width: calc(100vw - 100px); } }
  .ex-res { display: inline-block; font: 800 12px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .04em; text-transform: uppercase; padding: 3px 8px; border-radius: 6px; text-align: center; }
  .ex-res-ok { background: #ddefe3; color: #0e5a2b; } .ex-res-mid { background: #ffe9c2; color: #6b3a00; } .ex-res-low { background: #f9d5db; color: #7a0019; } .ex-res-x { background: var(--surface2); color: var(--ink2); }
"""
url = f"{DOMAIN}/explore/"
N_HC_GUIDES = len(HC_ANY)
title = fit(["South Carolina Restaurant Search: Map, BBQ & SCDA Grades", "Search South Carolina Restaurants: BBQ, Seafood & Grades",
             "Search SC Restaurants: Barbecue, Seafood & Inspection Grades"], 50, 60, "explore title")
desc = fit([f"Look up {N_REST:,} South Carolina restaurants by name, town, street or dish, map {N_HC_GUIDES} hand-checked places and see SCDA's posted grades.",
            f"Search {N_REST:,} South Carolina restaurants by name, town, street or dish, map {N_HC_GUIDES} hand-checked places, and see each SCDA inspection grade.",
            f"Search {N_REST:,} SC restaurants by name, town or dish, browse {N_HC_GUIDES} hand-checked places on a map and see SCDA's posted inspection grades."],
           140, 160, "explore description")
nav, bc = crumbs([("Home", "/"), ("Search", "/explore/")])
WEB_GUIDES = [(k, t) for k, t in (("bbq", "Barbecue"), ("seafood", "Lowcountry seafood"), ("gullah", "Gullah Geechee"), ("meat3", "Meat-and-threes"))
              if L_ALL[k]]
guide_buttons = "".join(f'<button type="button" data-g="{k}" aria-pressed="false">{e(t)}</button>' for k, t in
                        WEB_GUIDES + [("honors", "MICHELIN & James Beard")] + ([("oldest", "Oldest")] if OLD_L else [])
                        + [("inspections", "SCDA grades"), ("all", "All restaurants"), ("saved", "Saved")])
explore_js = open(f"{ROOT}/scripts/explore.js").read()
JS_KEYS = sorted(set(re.findall(r'store\.set\("([a-z]+)"', explore_js)))   # the keys the web app writes, each under STORAGE_PREFIX
assert JS_KEYS and "localStorage.setItem(PREFIX + k" in explore_js and len(re.findall(r"localStorage\.setItem", explore_js)) == 1
assert "</script" not in explore_js.lower()
assert f'"{STORAGE_PREFIX}"' in explore_js, "explore.js must keep its localStorage keys under " + STORAGE_PREFIX
body = f"""{nav}
  <main id="main">
  <section class="ex-hero">
    <p class="kicker">{BRAND} · on the web</p>
    <h1>Search South Carolina restaurants</h1>
    <p class="sub">Pick a list, or type a name, a town, a street or a dish. Behind the search: {N_REST:,} South Carolina restaurants, cafés, bars and bakeries; {N_HC_GUIDES} hand-checked places on the barbecue, Lowcountry seafood, Gullah Geechee and meat-and-three lists; {len(HON_L)} MICHELIN and James Beard honorees; and the SC Department of Agriculture's retail food permits and posted inspection grades. It's the data the iPhone and iPad app will ship with, and what you save stays in this browser.</p>
  </section>
  <p id="ex-loading" hidden>Loading the restaurant list…</p>
  <noscript><p>The search needs JavaScript. The guides work without it: {join_words([f'<a href="/{GUIDE_PATH[k]}">{e(GUIDE_NAME[k])}</a>' for k, _ in GUIDE_TAGS] + [f'<a href="/{HON_PATH}">MICHELIN and James Beard honors</a>', f'<a href="/{INS_PATH}">inspection grades explained</a>'])}.</p></noscript>
  <div id="ex-app" hidden data-ver="{DATA_VER}">
    <div class="ex-controls">
      <div class="ex-guides" role="group" aria-label="Guides">{guide_buttons}</div>
      <div class="ex-row1">
        <label class="skip" for="ex-q">Search</label>
        <input id="ex-q" type="search" placeholder="Name, town, street or dish" autocomplete="off" enterkeyhint="search">
        <button type="button" id="ex-locate" class="ex-small">Near me</button>
      </div>
      <div class="ex-row2">
        <label>Sort <select id="ex-sort" aria-label="Sort"></select></label>
        <select id="ex-town" aria-label="Town"></select>
        <select id="ex-cuisine" aria-label="Kind of place"></select>
        <label><input type="checkbox" id="ex-chains"> Hide chains</label>
        <label id="ex-bibwrap" hidden><input type="checkbox" id="ex-bib"> <span>Bib Gourmand <span id="ex-bibn"></span></span></label>
        <button type="button" id="ex-clear" class="ex-small" hidden>Clear filters</button>
        <div class="ex-view" role="group" aria-label="View"><button type="button" data-v="list" aria-pressed="true">List</button><button type="button" data-v="map" aria-pressed="false">Map</button></div>
      </div>
      <p id="ex-sub"></p>
      <p id="ex-count" aria-live="polite"></p>
      <p id="ex-locmsg"></p>
    </div>
    <div id="ex-listwrap"><ol id="ex-list" class="ex-list"></ol><button type="button" id="ex-more" class="ex-small" hidden></button></div>
    <div id="ex-mapwrap" hidden>
      <canvas id="ex-map" aria-label="Map of South Carolina with a dot for each place in the list. The list view has the same places."></canvas>
      <div class="ex-zoom"><button type="button" id="ex-zin" aria-label="Zoom in">+</button><button type="button" id="ex-zout" aria-label="Zoom out">−</button></div>
      <p id="ex-maphint"></p>
      <p id="ex-mapattr">Outlines © OpenStreetMap contributors, Overture Maps Foundation</p>
    </div>
  </div>
  <div id="ex-backdrop" class="ex-backdrop" hidden></div>
  <aside id="ex-panel" class="ex-panel" hidden aria-labelledby="ex-pname"></aside>
  </main>
<script>
{explore_js}
</script>"""
webapp_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": f"{BRAND} web app", "url": url,
             "applicationCategory": "TravelApplication", "operatingSystem": "Any", "browserRequirements": "Requires JavaScript",
             "description": desc, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
             "publisher": ORG_REF}
page("explore/index.html", title, desc, body, [webapp_ld, bc], extra_css=EXPLORE_CSS, og_type="website")

# ---------------------------------------------------------------- landing page
# alt text says what each capture shows (docs/screenshots, made by scripts/capture-screenshots.sh; copies by scripts/site-images.sh)
shots = [("home", "The South Carolina Eats home screen: a search box and guide cards for Whole-Hog & Mustard Barbecue, Lowcountry & Grand Strand Seafood, Gullah Geechee Cooking and Meat-and-Threes & Drive-Ins, each with its count of places.", "A guide for each South Carolina craving."),
         ("bbq", "The hand-checked barbecue list in South Carolina Eats, nearest first, with each place's town, kind and distance.", "Barbecue joints nearest you."),
         ("detail", "Bowens Island Restaurant in South Carolina Eats: its address, America's Classic and Lowcountry seafood tags, a button for Apple Maps' ratings, hours and photos, Directions and Call buttons, a small map and the hand-checked note.", "Each place, with a note checked by hand."),
         ("map", "The South Carolina Eats map around downtown Charleston, with pins for hand-checked and honored places and layer buttons for the guides.", "The map, by guide."),
         ("honors", "The MICHELIN and James Beard honors list in South Carolina Eats, with each place's town, kind and honor.", "MICHELIN and James Beard honorees.")]
shot_html = []
for i, (name, alt, cap) in enumerate(shots):
    png = f"{DOCS}/img/screen-{name}.png"
    if not os.path.exists(png):
        continue
    w, h = png_size(png)
    lazy = ' loading="lazy"'   # the section sits below the fold at every width
    webp = os.path.exists(f"{DOCS}/img/screen-{name}.webp")
    src = (f'<source srcset="/img/screen-{name}.webp" type="image/webp">' if webp else "")
    shot_html.append(f'<li><picture>{src}<img src="/img/screen-{name}.png" alt="{e(alt)}" width="{w}" height="{h}"{lazy} decoding="async"></picture><p>{e(cap)}</p></li>')

GUIDE_PHRASE = {"bbq": "whole-hog and mustard barbecue", "seafood": "Lowcountry and Grand Strand seafood", "gullah": "Gullah Geechee cooking",
                "meat3": "meat-and-threes and drive-ins"}
GUIDES_TEXT = join_words([GUIDE_PHRASE[k] for k, _ in GUIDE_TAGS])
GUIDE_TITLES = join_words([GUIDE_NAME[k] for k, _ in GUIDE_TAGS], "or")
BBQ_L = L_ALL["bbq"]
faq = [
    ("Is South Carolina Eats free?", "Completely: no price, no ads, no in-app purchases and no account to create. It's an iPhone and iPad app on its way to the App Store, with no Android version yet; until it's out, the web search here works in any browser."),
    ("Where do the lists come from?", f"Two kinds of source. The {GUIDES_TEXT} lists are our own research from {CHECKED}: a page that names each place for the food (Discover South Carolina, local press or the place's own site), and something from 2025 or 2026 that shows it's open. The wider directory of {N_REST:,} restaurants starts from Overture Maps' open place data, keeps the kinds of listing that proved reliable against the SC Department of Agriculture's statewide permit list, and adds permitted restaurants from that list."),
    ("Where can I get whole-hog barbecue?", f"Our barbecue list has {plural(len(BBQ_L), 'hand-checked joint')}, from whole hogs cooked over coals to the Midlands' mustard sauce and hash over rice. Many old pits open only a few days a week, so check before you drive. In the web search, the barbecue list puts the nearest first once you share your location."),
    ("How do I check a South Carolina restaurant's inspection grade?", "The SC Department of Agriculture inspects restaurants statewide and posts a letter grade, A, B or C, after each inspection. For each place we matched to an SCDA permit, the app and this site show its latest posted grade and date as SC Food Grades publishes them, with its recent inspections and a link to each report. We compute no grade or score of our own."),
    ("Does it show ratings and reviews?", "Not from us. Tapping a place opens Apple Maps' own card inside the app, with Apple's current ratings, hours, photos and directions. None of our lists is sorted by anyone's rating."),
    ("Does it need my location?", "No. Location only matters for putting the nearest places first. If you share it, it stays on your iPhone or iPad and never reaches us, and the app works fine without it. On this website, Near me reads your location inside your browser and nowhere else."),
    ("A place has closed, or something's wrong. How do I tell you?", f"Write to {EMAIL} with the place's name, its town and what changed. Corrections ship with the next data update."),
]
faq_html = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "@id": f"{DOMAIN}/#faq",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
app_ld = {"@context": "https://schema.org", "@graph": [
    # No "offers" until the app is on the App Store (put it back with the listing URL: price 0, USD).
    {"@type": "MobileApplication", "@id": f"{DOMAIN}/#app", "name": APP_NAME,
     "alternateName": ["SC Eats", "South Carolina Eats: BBQ, Shrimp & Grits, Oysters"],
     "description": f"A free guide to {N_REST:,} South Carolina restaurants, with hand-checked lists of {GUIDES_TEXT}, {len(HON_L)} MICHELIN and James Beard honorees, and the SC Department of Agriculture's posted inspection grades. Sort by distance, open Apple Maps' live place card for hours and photos, and save places for your next trip.",
     "url": f"{DOMAIN}/", "image": f"{DOMAIN}/og.png", "operatingSystem": "iOS, iPadOS", "applicationCategory": "TravelApplication",
     "applicationSubCategory": "Food & Drink", "inLanguage": "en", "publisher": {"@id": ORG_ID}},
    {"@type": "Organization", "@id": ORG_ID, "name": BRAND, "url": f"{DOMAIN}/",
     "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png", "width": 512, "height": 512}, "email": EMAIL,
     "contactPoint": {"@type": "ContactPoint", "contactType": "customer support", "email": EMAIL, "availableLanguage": "en"},
     # the Eats Ranked hub lists this site as a subOrganization; say so from this side too
     "parentOrganization": HUB},
    {"@type": "WebSite", "@id": f"{DOMAIN}/#website", "name": BRAND, "alternateName": ["SC Eats", "South Carolina Eats app"], "url": f"{DOMAIN}/",
     "inLanguage": "en", "publisher": {"@id": ORG_ID}}]}
if shot_html:
    app_ld["@graph"][0]["screenshot"] = f"{DOMAIN}/img/screen-{next(n for n, *_ in shots if os.path.exists(f'{DOCS}/img/screen-{n}.png'))}.png"
title = fit(["South Carolina Eats: BBQ, Shrimp & Grits & SC Restaurants", "South Carolina Eats: Barbecue, Seafood & SC Restaurant App",
             "South Carolina Eats: Free SC Restaurant App, BBQ to Seafood"], 50, 60, "landing title")
desc = fit([f"Whole-hog barbecue, shrimp and grits and Gullah Geechee cooking: a free iPhone and iPad guide to {N_REST:,} South Carolina restaurants, with SCDA grades.",
            f"A free iPhone and iPad guide to {N_REST:,} South Carolina restaurants, with hand-checked barbecue, Lowcountry seafood and Gullah Geechee kitchens.",
            f"Free iPhone and iPad guide to {N_REST:,} South Carolina restaurants: hand-checked barbecue and seafood, MICHELIN honorees and SCDA inspection grades."],
           140, 160, "landing description")
city_cards = "".join(f'<li><a href="{city_url(c)}">{e(c)}</a></li>' for c in CITY_PAGES)
screens = f"""
  <section id="screens">
    <h2>Inside the app</h2>
    <ul class="shots" tabindex="0" aria-label="South Carolina Eats app screenshots">
      {"".join(shot_html)}
    </ul>
  </section>""" if shot_html else ""
guide_cards = "".join(f'<a class="card gc gc-{k}" href="/{GUIDE_PATH[k]}"><b>{len(L[k])}</b><h3>{e(GUIDE_NAME[k])}</h3><p>{plural(len(L[k]), "hand-checked place")}{line}.</p></a>'
                      for k, line in (("bbq", ", whole hog to hash and rice"), ("seafood", ", from Little River to Hilton Head"),
                                      ("gullah", " on the Sea Islands and around Charleston"), ("meat3", ": soul food plates and old drive-ins")) if k in L)
body = f"""  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND}: {TAGLINE} for iPhone and iPad</p>
    <h1>South Carolina restaurants, whole hog to shrimp &amp; grits</h1>
    <p class="lede">Looking for whole hog with mustard sauce in the Midlands, shrimp and grits by the marsh, okra soup and red rice at a Gullah Geechee kitchen, or a meat and three at lunch? {BRAND} starts with lists we checked place by place, adds MICHELIN and James Beard honorees and the SC Department of Agriculture's posted inspection grades, and maps {N_REST:,} restaurants, cafés, bars and bakeries in {N_TOWNS:,} South Carolina towns.</p>
    <div class="cta-row">{store_button()}<a class="btn btn-ghost" href="/explore/">Search on the web</a><span class="pill store-note">No charge, no ads, no sign-in. The App Store release is on its way.</span></div>
    <ul class="stats" aria-label="What's in the app">
      <li><b>{N_HC_GUIDES}</b><span>hand-checked places</span></li>
      <li><b>{len(HON_L)}</b><span>MICHELIN and James Beard honorees</span></li>
      <li><b>{len(INS_L):,}</b><span>with an SCDA inspection grade</span></li>
      <li><b>{N_REST:,}</b><span>restaurants</span></li>
    </ul>
  </section>

  <section id="what">
    <h2>Built around how South Carolina eats</h2>
    <p class="sub">Star ratings won't tell you which pit still cooks whole hogs over coals, or where to find she-crab soup on a Tuesday. {BRAND} is organized the way people here eat: {GUIDES_TEXT}, each place checked in {CHECKED} against a 2025–26 source. Every place we matched to an SCDA permit shows its latest posted grade, never a grade from us, and Apple Maps' live card supplies ratings, hours and photos.</p>
  </section>

  <section id="how">
    <h2>How it works</h2>
    <ol class="steps">
      <li class="step"><div class="n" aria-hidden="true">1</div><div><h3>Start with a craving.</h3><p>{e(join_words([GUIDE_NAME[k] for k, _ in GUIDE_TAGS] + ["MICHELIN & James Beard", "SCDA inspection grades"], "or"))}. Or type a name, a town, a street or a dish to search the {N_REST:,} we list.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">2</div><div><h3>Find the closest one.</h3><p>Put the nearest first, narrow it to one town or one kind of food, or pan the map from the Upstate to the Grand Strand.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">3</div><div><h3>Head out.</h3><p>Check today's hours and photos on Apple Maps' card, call ahead, get directions, or save the place for the next beach trip.</p></div></li>
    </ol>
  </section>
{screens}
  <section id="guides">
    <h2>South Carolina food guides</h2>
    <p class="sub">Each of the app's lists has its own page here, free to read.</p>
    <div class="grid2">
      {guide_cards}
      {f'<a class="card gc gc-oldest" href="/{OLD_PATH}"><b>{len(OLD_L)}</b><h3>South Carolina&#39;s oldest restaurants</h3><p>{plural(len(OLD_L), "place")} open at the same address since 1960 or earlier.</p></a>' if HAS_OLD else ""}
      <a class="card gc gc-honors" href="/{HON_PATH}"><b>{len(HON_L)}</b><h3>MICHELIN &amp; James Beard</h3><p>{plural(len(HON_L), "honored South Carolina restaurant")}.</p></a>
      <a class="card" href="/{INS_PATH}"><h3>SCDA inspection grades, explained</h3><p>What A, B and C mean, and how the latest posted grades fall for {plural(len(INS_L), "place")}.</p></a>
    </div>
  </section>

  <section id="cities">
    <h2>Barbecue, seafood and more by city</h2>
    <p class="sub">The towns with enough hand-checked or honored places for a page of their own. The <a href="/cities/">cities and towns index</a> sums up what's on each.</p>
    <ul class="cities">{city_cards}</ul>
  </section>

  <section id="pricing">
    <h2>Free, with no catch</h2>
    <p class="sub">The app costs nothing, shows no ads and sells nothing inside, and there's no account to make. The lists ship inside the app, so they open right away and keep working when the signal drops out on a back road or a barrier island.</p>
  </section>

  <section id="privacy">
    <h2>What stays on your phone</h2>
    <p class="sub">{BRAND} collects nothing about you: no sign-in, no analytics, no ads. Location, if you turn it on, only puts the nearest places first, and your saved places are kept on the phone or iPad. The website has no cookies and no trackers. <a href="/privacy.html">The privacy policy</a> has the details.</p>
  </section>

  <section id="faq">
    <h2>Questions</h2>
    {faq_html}
  </section>

  <section id="download" class="final">
    <h2>Find your next barbecue stop</h2>
    <p class="sub">The iPhone and iPad app is almost here, and it's free. Ask for early access.</p>
    <div class="cta-row">{store_button()}</div>
  </section>
  </main>"""
page("index.html", title, desc, body, [app_ld, faq_ld], og_type="website")

# ---------------------------------------------------------------- privacy and terms
nav, bc = crumbs([("Home", "/"), ("Privacy policy", "/privacy.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Privacy policy</h1>
    <p class="lede">Short version: the {BRAND} app collects nothing about you, and this website doesn't track you. Last updated {PRIVACY_UPDATED}.</p>
  </section>
  <section>
    <h2>The app</h2>
    <ul>
      <li><b>No account, no analytics, no ads.</b> The app has no sign-in, no advertising and no analytics or crash-reporting code. We receive no data from it.</li>
      <li><b>Location.</b> If you allow it, your location is used on your device to sort places by distance and show where you are on the map. It is never sent to us. You can turn it off in Settings at any time.</li>
      <li><b>Saved places and filters</b> are stored only on your device and are deleted when you delete the app.</li>
      <li><b>Apple Maps.</b> When you open a place's ratings, hours and photos, or ask for directions, the app asks Apple Maps for that place. Apple handles that request under <a href="https://www.apple.com/legal/privacy/" rel="noopener">Apple's privacy policy</a>, as it does for any app that shows a map.</li>
      <li><b>Data updates.</b> When you open the app, it checks this website for newer restaurant data, at most once a day (or an hour later if a check didn't go through), and downloads it when there is some. These requests carry no location or identifiers. GitHub, which hosts this site, may keep standard server logs of them, as it does for any visit here.</li>
      <li><b>Spotlight.</b> The app adds its hand-checked and honored places to your device's search index so you can find them from Spotlight. That index stays on your device.</li>
      <li><b>Calls, websites and email</b> you start from a place open in the Phone app, your browser or Mail, and are handled by them.</li>
    </ul>
    <p>When the app is on the App Store, its privacy label will be "Data Not Collected".</p>
    <h2>This website</h2>
    <p>The site is static pages hosted on GitHub Pages. It sets no cookies and loads no analytics, fonts or scripts from anyone else.</p>
    <ul>
      <li><b>Saved places and your last guide.</b> The search page (<a href="/explore/">/explore/</a>) keeps the places you save and the last guide you opened in your browser's local storage, on this device only, under the keys {join_words([f"<code>{STORAGE_PREFIX}{k}</code>" for k in JS_KEYS])}. Nothing is sent to us. Clearing this site's data in your browser removes them.</li>
      <li><b>Location.</b> If you tap Near me or choose the Nearest sort, your browser asks whether to share your location. If you allow it, the location is used only inside your browser to sort places by distance and is never sent to us or anyone else.</li>
    </ul>
    <p>GitHub may keep standard server logs, such as IP addresses, for security; see <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" rel="noopener">GitHub's privacy statement</a>.</p>
    <h2>Email</h2>
    <p>If you email us, we use your message and address only to reply and to fix the listing you told us about. We don't add you to a mailing list or share your address. Mail to {EMAIL} reaches our inbox through Cloudflare Email Routing; see <a href="https://www.cloudflare.com/privacypolicy/" rel="noopener">Cloudflare's privacy policy</a>.</p>
    <h2>Children</h2>
    <p>The app collects no personal information from anyone, including children.</p>
    <h2>Changes and contact</h2>
    <p>If this policy changes, the new version will be posted here with a new date. Questions: <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
  </section>
  </main>"""
page("privacy.html", fit(["South Carolina Eats Privacy Policy: No Tracking, No Accounts", "South Carolina Eats Privacy Policy: No Tracking"], 50, 60, "privacy title"),
     fit(["How South Carolina Eats treats your data: the app collects none, your location and saved places stay on your device, and this site has no cookies.",
          "How South Carolina Eats treats your data: the iPhone app collects none, location and saved places stay on your device, and this site has no trackers."], 140, 160, "privacy description"),
     body, [bc])

nav, bc = crumbs([("Home", "/"), ("Terms of use", "/terms.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Terms of use</h1>
    <p class="lede">The plain-language terms for the {BRAND} app and this website. Last updated {POLICY_UPDATED}.</p>
  </section>
  <section>
    <h2>What the app is</h2>
    <p>{BRAND} is a free guide to restaurants in South Carolina. It is provided as is, for personal use, without charge and without warranties of any kind.</p>
    <h2>Check before you go</h2>
    <p>Restaurants open, close, change their hours and change their menus; many barbecue joints open only a few days a week, and beach places keep seasonal hours. Dishes and founding years are what each place or a named source said when we checked in {CHECKED}. We work to keep the lists right, but we can't promise that any listing is current or complete. Call the restaurant before you make the trip.</p>
    <h2>Inspection grades and public records</h2>
    <p>The app and this site show the SC Department of Agriculture's posted inspection grades (A, B or C) and dates as SC Food Grades publishes them, for places we matched to an SCDA retail food permit, with the place's recent inspections and links to SCDA's reports. SC Food Grades publishes the posted grade, not the inspection's score, and we compute no grade or score of our own. An inspection is a snapshot of one day. SCDA's note on its data: “{e(SCDA_NOTE)}” For official records, ask SCDA itself.</p>
    <h2>Other people's content</h2>
    <p>Ratings, reviews, hours and photos in each place card come from Apple Maps and are Apple's and its providers', under Apple's terms. Restaurant names and trademarks belong to their owners. MICHELIN and the MICHELIN Guide are trademarks of Michelin. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. {BRAND} is not affiliated with any restaurant, chain, award body or government agency.</p>
    <h2>Data sources and licenses</h2>
    <ul>
      <li>SC Department of Agriculture (SCDA), Retail Food Safety: retail food permits and posted inspection grades, from SC Food Grades' public map service, which the SC Department of Public Health maintains for SCDA. Provided by SCDA without warranty; shown as published.</li>
      <li>Overture Maps Foundation places data, under the Community Data License Agreement, Permissive 2.0, including data from Meta, Microsoft, DAC, BrightQuery, AllThePlaces (CC0 1.0) and Foursquare (Apache 2.0).</li>
      <li>Overture Maps Foundation divisions, used for the state and county outlines on the map, under the Open Database License: © OpenStreetMap contributors, Overture Maps Foundation.</li>
      <li>The MICHELIN Guide American South 2026 selection and the James Beard Foundation's awards, semifinalists, finalists and America's Classics: honors reported as facts.</li>
      <li>{e(GUIDES_TEXT[0].upper() + GUIDES_TEXT[1:])} and founding years: our own research, with a source recorded for every place.</li>
    </ul>
    <h2>Corrections</h2>
    <p>If a listing is wrong, or you own a restaurant and want something fixed, email <a href="mailto:{EMAIL}">{EMAIL}</a>. We fix mistakes in the next update.</p>
    <h2>Liability</h2>
    <p>To the extent the law allows, we are not liable for any loss arising from use of the app or site, including a wasted drive to a closed restaurant.</p>
    <h2>Changes</h2>
    <p>We may update these terms; the current version and its date are always on this page. See also the <a href="/privacy.html">privacy policy</a>.</p>
  </section>
  </main>"""
page("terms.html", fit(["South Carolina Eats Terms of Use: A Free Guide, As Is", "South Carolina Eats Terms of Use: Free and Provided As Is"], 50, 60, "terms title"),
     fit(["The terms for South Carolina Eats and this site: a free guide provided as is, SCDA's grades shown as published, and how to report a mistake.",
          "The terms for South Carolina Eats and this website: a free guide provided as is, state records shown as SCDA published them, and how to report a mistake."], 140, 160, "terms description"),
     body, [bc])

body = f"""  <main id="main">
  <section class="hero">
    <h1>Page not found</h1>
    <p class="lede">No page lives at this address. Head back to the <a href="/">{BRAND} home page</a>, the <a href="/{GUIDE_PATH['bbq']}">barbecue list</a> or the <a href="/explore/">South Carolina restaurant search</a>.</p>
  </section>
  </main>"""
page("404.html", f"Not found: {BRAND}", "No page lives at this address.", body, robots="noindex,follow")
noindexed.remove("404.html")


# ---------------------------------------------------------------- plumbing
for f in os.listdir(f"{DOCS}/cities"):   # a city the data lost: drop its old page instead of leaving it live and stale
    if f.endswith(".html") and f"cities/{f}" not in written + noindexed:
        os.remove(f"{DOCS}/cities/{f}")
        print("removed stale", f"cities/{f}")
urls = ["" if w == "index.html" else w.replace("index.html", "") for w in written]
urls.sort(key=lambda u: (u != "", u.startswith("cities/"), u))
open(f"{DOCS}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                       + "".join(f"  <url><loc>{DOMAIN}/{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) + "</urlset>\n")
open(f"{DOCS}/robots.txt", "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n")
json.dump({"name": BRAND, "short_name": "SC Eats", "description": f"{TAGLINE[0].upper() + TAGLINE[1:]}: a guide to {N_REST:,} South Carolina restaurants.",
           "start_url": f"{BASE}/", "display": "browser", "background_color": "#f6f1e7", "theme_color": "#1b2a57",
           "icons": [{"src": f"{BASE}/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": f"{BASE}/icon-512.png", "sizes": "512x512", "type": "image/png"}]},
          open(f"{DOCS}/site.webmanifest", "w"), indent=2)
if CUSTOM_DOMAIN:
    open(f"{DOCS}/CNAME", "w").write(CUSTOM_DOMAIN + "\n")
elif os.path.exists(f"{DOCS}/CNAME"):
    os.remove(f"{DOCS}/CNAME")   # no custom domain yet: GitHub serves the project address
open(f"{DOCS}/.nojekyll", "w").write("")
os.makedirs(f"{ROOT}/playbook", exist_ok=True)
json.dump({"generated": TODAY, "domain": DOMAIN, "restaurants": N_REST, "places_incl_hidden": len(PLACES), "towns": N_TOWNS, "counties": N_COUNTIES,
           "on_an_official_list": N_OFFICIAL, "scda_open_food_permits": N_SCDA_PERMITS, "scda_open_since": SCDA_OPEN_SINCE, "hand_checked_on_a_guide": N_HC,
           **{"guide_" + k: len(v) for k, v in L_ALL.items()}, "guide_pages": list(L), "oldest": len(OLD_L), "honors": len(HON_L), "james_beard": N_JBF,
           "michelin": N_MI, "michelin_stars": N_STARS, "bib_gourmand": N_BIB, "americas_classics": N_CLASSICS, "inspection_grades": len(INS_L),
           "grade_counts": dict(BAND_N), "inspections_through": INS_THROUGH,
           "city_pages": city_stats, "cities_without_a_page": CITY_SKIPPED, "noindex_pages": noindexed,
           "web_app_data_bytes": {k: {"raw": r, "gzip": g} for k, (r, g) in SIZES.items()}},
          open(f"{ROOT}/playbook/site-numbers.json", "w"), indent=1, ensure_ascii=False)
print("wrote", len(written) + len(noindexed) + 1, "pages:", ", ".join(written))
if noindexed:
    print("noindex:", ", ".join(noindexed))
print(f"restaurants {N_REST:,} in {N_TOWNS} towns | official {N_OFFICIAL:,} | hand-checked on a guide {N_HC} | "
      + " | ".join(f"{k} {len(v)}" for k, v in L_ALL.items()) + f" | oldest {len(OLD_L)} | honors {len(HON_L)} | SCDA grades {len(INS_L):,} {dict(BAND_N)}")
print("city pages:", ", ".join(CITY_PAGES), "| no page (listed places):", CITY_SKIPPED)
print(f"website blocklist: {len(BLOCKLIST)} entries, {len(BLOCKED_LINKS)} links dropped:", "; ".join(f"{n} {u}" for n, u in BLOCKED_LINKS) or "none")
for k, (r, g) in SIZES.items():
    print(f"  {k}: {r / 1024:,.0f} KB raw, {g / 1024:,.0f} KB gzip")
