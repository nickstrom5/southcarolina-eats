"""Writes data/research/app/*.json (hand-checked South Carolina guides), data/research/jbf.json and data/research/closed.json from the
compact lists below.

Every entry needs two things, both on robots-checked hosts (check_sources.py):
- a page that names it for the guide (any date: a tourism board, SCETV, Charleston Magazine, local press, the place's own site), and
- 2025-26 evidence that it operates: a dated 2025-26 page ("dated"), its own live site showing current hours or ordering when we
  fetched it ("site", recorded with the fetch date), or an SCDA inspection in 2025 or 2026 ("scda": the place's own posted grade on SC
  Food Grades, which reaches every county).
The address comes from the official record or map listing we already hold for that name in that town (site/southcarolina.json), never
from memory; a name that isn't found once in its town is left out and listed in data/research/app/LEADS.md. A founding year is set only
when a source says the place opened at this address; a brand's or a family's founding year goes in the note.
Usage: ../.venv/bin/python build_research.py   (then southcarolina.py)"""
import json, os, re
ROOT = os.path.join(os.path.dirname(__file__), "..")
R = os.path.join(ROOT, "data", "research")
os.makedirs(f"{R}/app", exist_ok=True)
d = json.load(open(os.path.join(ROOT, "site", "southcarolina.json")))
C, M = d["cols"], d["meta"]
INSP = {sp[0]: sp for sp in d["sparse"]["insp"]}
import unicodedata
# accents fold to their letters ("Bintü" = "Bintu"), as the app's search does
norm = lambda s: re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", unicodedata.normalize("NFKD", (s or "").lower().replace("'", "").replace("’", "")).encode("ascii", "ignore").decode())).strip()
FETCHED = "2026-10-26"   # the day the places' own sites were read
SCDA = "https://apps.dhec.sc.gov/Environment/FoodGrades/"
DATED = set()

# sources (robots-checked; Discover South Carolina is the state tourism office's site; its articles carry no date, so each place's
# 2025-26 evidence is its own SCDA inspection)
DSC = "https://discoversouthcarolina.com/articles/"
D_HOG = DSC + "go-whole-hog-at-these-barbecue-joints"
D_BLUE = DSC + "south-carolina-home-of-blue-ribbon-barbecue"
D_HASH = DSC + "enjoy-sc-barbecue-with-a-side-of-hash"
D_PIT = DSC + "pit-stops-roadside-barbecue-worth-pulling-over-for"
D_GRITS = DSC + "seeking-shrimp-and-grits"
D_CHS = DSC + "lowcountry-dining-is-timeless-at-these-charleston-classics"
D_MB = DSC + "iconic-eats-myrtle-beach"
D_STYLES = DSC + "southern-lowcountry-gullah-or-soul-whats-the-difference-between-these-sc-cooking-styles"
D_GULLAH = DSC + "best-ways-to-experience-the-lowcountrys-gullahgeechee-culture"
D_BEAUFORT = DSC + "from-kazoos-to-gullah-eats-beaufort-is-filled-with-hidden-gems"
D_DRIVEIN = DSC + "drive-in-restaurants-that-dish-up-nostalgia"
D_BEACON = DSC + "beacon-drive-in-shines-on-as-a-spartanburg-landmark"
CP_GULLAH = "https://charlestoncitypaper.com/2015/08/26/your-guide-to-tracking-down-the-best-gullah-eats/"
FOLLY_75 = "https://www.follycurrent.com/?p=9837"   # Aug 6, 2021: Bowens Island's 75th year
JBF_AC24 = "https://www.jamesbeard.org/stories/announcing-the-2024-restaurant-and-chef-americas-classics-winners"

# guide -> rows of (name as our data writes it, town (None: anywhere), street number, note (our words), founded (at this address),
#                   founded note, [sources], evidence: "dated" | "site" | "scda")
GUIDES = {
 "bbq": [
  ("Hite's Bar-B-Que", "West Columbia", "240", "Family-run whole-hog pit cooked over hickory and oak, served with a yellow mustard sauce and hash; open Fridays and Saturdays.",
   None, None, [D_HOG, D_BLUE], "scda"),
  ("Scott's Bar-B-Que", "Hemingway", "2734", "The Scott family's roadside pit on Hemingway Highway: whole hog mopped with vinegar and pepper; cash only, Wednesday to Saturday.",
   None, None, [D_HOG, D_BLUE, D_PIT], "scda"),
  ("Rodney Scott's BBQ", "Charleston", "1011", "Whole hogs cooked over wood coals overnight and mopped with Rodney Scott's vinegar-pepper sauce, on upper King Street.",
   None, None, [D_HOG, D_BLUE, D_PIT], "scda"),
  ("Martin's Bar-B-Que Joint", "Charleston", "1622", "Whole hog on James Island, started the day before it's served.", None, None, [D_HOG], "scda"),
  ("Swig & Swine", "Charleston", "1217", "West Ashley's whole hog, smoked for up to 16 hours and basted with a vinegar-mustard sauce; served Thursdays.",
   None, None, [D_HOG], "scda"),
  ("Sweatman's Barbeque", "Holly Hill", "1427", "Hogs cooked overnight over oak and hickory coals, with liver hash, rice and a mustard sauce; open Fridays and Saturdays.",
   None, None, [D_HOG, D_HASH], "scda"),
  ("Seminar Brewing & Elliott's BBQ Lounge", "Florence", "551", "Pee Dee whole hog smoked over pecan wood, in the Seminar Brewing taproom.",
   None, None, [D_HOG, D_BLUE], "scda"),
  ("McCabe's Bar-B-Q", "Manning", "480", "An old-school whole-hog buffet: picked pork in vinegar and pepper, with hash and ribs; cash only, Thursday to Saturday.",
   None, None, [D_HOG, D_BLUE], "scda"),
  ("Melvin's Legendary Barbecue", "Mount Pleasant", "925", "The Bessinger family's mustard-sauce barbecue, cooked over wood coals; Melvin's hash is made with the same mustard sauce.",
   None, None, [D_BLUE, D_HASH], "scda"),
  ("True BBQ", "West Columbia", "1237", "Known for its red, beefy, mustardy hash over rice.", None, None, [D_HASH], "scda"),
  ("Midway BBQ", "Buffalo", "811", "Union County's last hash house: a thick, buttery beef hash made since 1941.", None, None, [D_HASH], "scda"),
  ("Dukes Barbecue", "Walterboro", "949", "A stew-like hash of ground pork and potatoes is the side everyone orders.", None, None, [D_HASH], "scda"),
  ("Duke's Bar-B-Que", "Orangeburg", "1298", "An old-time barbecue buffet on Whitman Street, one of several Duke's run by the family around Orangeburg.",
   None, None, [D_PIT], "scda"),
  ("Roger's BBQ House", "Florence", "2004", "A barbecue buffet whose liver hash is the draw.", None, None, [D_HASH], "scda"),
  ("Shuler's BBQ", None, "419", "A barbecue buffet on SC-38 near Latta, with smoked meats and Southern sides.", None, None, [D_PIT], "scda"),
  ("Lee's Barbecue & Catering Service", "Waterloo", "16994", "A barbecue buffet of smoked meats and country sides on SC-72.", None, None, [D_PIT], "scda"),
  ("Palmira", "Charleston", "2366", "Carolina whole hog with Puerto Rican roots, basted with sofrito; a MICHELIN Bib Gourmand.", None, None, [D_BLUE], "scda"),
 ],
 "seafood": [
  ("Bowens Island Restaurant", "Charleston", "1870", "Oysters roasted and shoveled onto the table at the family's creekside spot on Bowens Island; a James Beard America's Classic.",
   1946, "The Bowen family's island restaurant marked its 75th year in 2021 (Folly Current). Its first building burned in 2006; the new one opened on the same site in 2010.",
   ["https://www.islands.com/2150019/bowens-island-restaurant-charleston-south-carolina-seafood-overlooking-scenic-marsh-james-beard-winner-fresh-caught-eats/", FOLLY_75], "scda"),
  ("Poogan's Porch", "Charleston", "72", "A Queen Street house since 1976, known for shrimp and grits and crab soup.", None, None, [D_CHS], "scda"),
  ("Slightly North of Broad", "Charleston", "192", "S.N.O.B. on East Bay: shrimp and grits, steamed clams and cream of crab soup.", None, None, [D_CHS], "scda"),
  ("High Cotton Charleston Restaurant", "Charleston", "199", "East Bay Street dining room serving crab soup and shrimp and grits.", None, None, [D_CHS], "scda"),
  ("Hank's Seafood Restaurant", "Charleston", "10", "A seafood house in an old Hayne Street warehouse: seafood towers, oyster stew and seafood à la Wando.", None, None, [D_CHS], "scda"),
  ("Anson Restaurant", "Charleston", "12", "Crab soup, fried green tomatoes and house-ground grits.", None, None, [D_CHS], "scda"),
  ("Acme Lowcountry Kitchen", "Isle of Palms", "31", "Several takes on shrimp and grits by the beach on Isle of Palms.", None, None, [D_GRITS], "scda"),
  ("Page's Okra Grill", "Mount Pleasant", "302", "Shrimp over fried cheddar grits with an andouille cream sauce.", None, None, [D_GRITS], "scda"),
  ("Grace & Grit", "Mount Pleasant", "320", "Local shrimp over smoked gouda grits with tasso ham and red-eye gravy.", None, None, [D_GRITS], "scda"),
  ("Skull Creek Boathouse", "Hilton Head Island", "397", "Carolina shrimp and grits with tasso ham gravy, on Skull Creek.", None, None, [D_GRITS], "scda"),
  ("Tubb's Shrimp & Fish", "Florence", "1500", "A New Orleans-leaning shrimp and grits with étouffée and andouille.", None, None, [D_GRITS], "scda"),
  ("The Flipside Restaurant", "Rock Hill", "129", "Shrimp and grits with andouille, spinach and charred peppers.", None, None, [D_GRITS], "scda"),
  ("Lee's Inlet Kitchen", "Murrells Inlet", "4460", "Calabash-style fried creek shrimp in the seafood village of Murrells Inlet.", None, None, [D_MB], "scda"),
  ("Nance's Creekfront", "Murrells Inlet", "4883", "Steam pots of oysters, clams, shrimp and crab, and roasted oysters, served since 1967.", None, None, [D_MB], "scda"),
  ("Chesapeake House", "Myrtle Beach", "9918", "A seafood house since 1971, known for its flounder-and-bacon fish stew.", None, None, [D_MB], "scda"),
  ("Sea Captain's House", "Myrtle Beach", "3002", "Oceanfront Lowcountry seafood in a 1950s beach house, best known for she-crab soup.", None, None, [D_MB], "scda"),
  ("Bimini's Oyster Bar & Seafood Market", "Myrtle Beach", "930", "A casual oyster bar for oyster roasts with slaw and hush puppies.", None, None, [D_MB], "scda"),
  ("Wahoo's Fish House", "Murrells Inlet", "3993", "Shrimp and grits and fresh oysters on the Murrells Inlet waterfront.", None, None, ["https://discoversouthcarolina.com/articles/dock-and-dine-grand-strand"], "scda"),
 ],
 "gullah": [
  ("Gullah Grub Restaurant", "St. Helena Island", "877", "Chef Bill Green's family kitchen on St. Helena Island: seafood gumbo, crab rice, greens and seasonal, local Gullah cooking.",
   None, None, [D_STYLES, D_GULLAH, D_BEAUFORT], "scda"),
  ("Hannibal's Kitchen", "Charleston", "16", "An East Side kitchen known for crab and shrimp rice, whole whiting and okra soup.", None, None, [D_STYLES, CP_GULLAH], "scda"),
  ("Bertha's Kitchen", "North Charleston", "2332", "Okra soup, lima beans and collards on Meeting Street Road; a James Beard America's Classic.", None, None, [D_STYLES, CP_GULLAH], "scda"),
  ("Ravenel Fresh Seafood", "Ravenel", "5925", "The Brown family's seafood market and kitchen: garlic crabs and conch stew.", None, None, [D_STYLES, CP_GULLAH], "scda"),
  ("Charlie Brown Seafood", "North Charleston", "4726", "A seafood market on Rivers Avenue cooking crabs, shrimp and clams, and fried garlic crab.", None, None, [CP_GULLAH], "scda"),
 ],
 "meat3": [
  ("Wade's Restaurant", "Spartanburg", "1000", "Spartanburg's meat-and-three since 1947: vegetables, pies and the family's barbecue hash; a James Beard America's Classic.",
   None, None, [JBF_AC24, "https://www.eatatwades.com/history"], "scda"),
  ("The Beacon Drive-in", "Spartanburg", "255", "The landmark drive-in serving since Thanksgiving Day 1946: chili cheeseburgers \"a-plenty\", onion rings and sweet tea.",
   None, None, [D_DRIVEIN, D_BEACON], "scda"),
  ("Dixie Drive In", "Greenwood", "600", "A 1959 drive-in for chili burgers, corn dogs, fried chicken and cherry colas.", None, None, [D_DRIVEIN], "scda"),
  ("Sno-Cap Drive in", "North Augusta", "618", "Burgers and root beer floats since 1965; you order inside now.", None, None, [D_DRIVEIN], "scda"),
  ("The Drive In", "Florence", "135", "The old 301 Drive-In, from 1957, now in a new building next to the first: fried chicken, gyros and cherry lemonade.",
   None, None, [D_DRIVEIN], "scda"),
  ("Big Mike's Soul Food", "Myrtle Beach", "504", "Soul food plates: field peas, collards, fried chicken, mac and cheese and cornbread.", None, None, [D_STYLES, D_MB], "scda"),
 ],
 "oldest": [
  ("Bowens Island Restaurant", "Charleston", "1870", "On the Bowen family's island since the mid-1940s.", 1946,
   "The Bowen family's island restaurant marked its 75th year in 2021 (Folly Current). Its first building burned in 2006; the new one opened on the same site in 2010.",
   [FOLLY_75], "scda"),
  ("Peaches Corner", "Myrtle Beach", "900", "A beachfront hot dog counter on the corner of Ocean Boulevard and 9th Avenue North since 1937.", 1937,
   "Discover South Carolina: one corner location, at 9th Avenue North and Ocean Boulevard, since 1937.", [D_MB], "scda"),
 ],
}
# kinds as southcarolina.py's tag rules read them
KIND = {"bbq": "whole-hog barbecue", "seafood": "lowcountry seafood", "gullah": "gullah geechee", "meat3": "meat and three", "oldest": "oldest"}
# places the map data doesn't hold as a place to eat (a hotel's dining room): placed from the street address the source gives
ADDR = {}
# a chain the guide lists everywhere it's found in our data (its own site lists the locations)
EVERY = set()

JBF_2025 = "https://www.jamesbeard.org/stories/the-2025-james-beard-award-semifinalists"
JBF_2026 = "https://www.jamesbeard.org/stories/james-beard-award-semifinalists-2026"
JBF_NOM_2026 = "https://www.jamesbeard.org/stories/james-beard-awards-restaurant-and-chef-nominees-2026"
JBF_W_2024 = "https://www.jamesbeard.org/stories/the-2024-james-beard-award-winners"
JBF_W_2018 = "https://www.jamesbeard.org/stories/the-2018-james-beard-award-winners"
JBF_W_2015 = "https://www.jamesbeard.org/stories/the-2015-james-beard-award-winners"
JBF_AC_2024 = "https://www.jamesbeard.org/stories/announcing-the-2024-restaurant-and-chef-americas-classics-winners"
JBF_AC_2017 = "https://www.jamesbeard.org/stories/2017-americas-classic-berthas-kitchen"
# (name, town, street number or None, honors, sources); a name found more than once in its town needs the street number
JBF = [
 ("Scoundrel", "Greenville", None, ["Best Chef: Southeast finalist 2026 (Joe Cash)", "Best Chef: Southeast semifinalist 2026 (Joe Cash)"], [JBF_NOM_2026, JBF_2026]),
 ("Merci", "Charleston", None, ["Best New Restaurant finalist 2026"], [JBF_NOM_2026, JBF_2026]),
 ("Weltons Tiny Bakeshop", "Charleston", None, ["Outstanding Bakery finalist 2026"], [JBF_NOM_2026, JBF_2026]),
 ("Chubby Fish", "Charleston", None, ["Outstanding Restaurant semifinalist 2025 and 2026"], [JBF_2026, JBF_2025]),
 ("Palmira Barbecue", "Charleston", None, ["Emerging Chef semifinalist 2026 (Hector Garate)"], [JBF_2026]),
 ("Stems & Skins", None, None, ["Outstanding Wine and Other Beverages Program semifinalist 2026"], [JBF_2026]),
 ("Graft Wine Shop", "Charleston", None, ["Outstanding Bar semifinalist 2026", "Outstanding Professional in Beverage Service semifinalist 2025 (Femi Oyediran and Miles White)"], [JBF_2026, JBF_2025]),
 ("Jianna", "Greenville", None, ["Outstanding Professional in Beverage Service semifinalist 2026 (Andrea Royko)"], [JBF_2026]),
 ("Renzo", "Charleston", None, ["Best Chef: Southeast semifinalist 2026 (Colin Marcelli)"], [JBF_2026]),
 ("Bintü Atelier", "Charleston", None, ["Best Chef: Southeast semifinalist 2026 (Bintou N'Daw)"], [JBF_2026]),
 ("Hook & Barrel", "Myrtle Beach", None, ["Best Chef: Southeast semifinalist 2026 (Heidi Vukov)"], [JBF_2026]),
 ("City Limits Barbeque", "West Columbia", None, ["Best Chef: Southeast semifinalist 2025 (Robbie Robinson)"], [JBF_2025]),
 ("Lula Drake Wine Parlour", "Columbia", None, ["Outstanding Wine and Other Beverages Program winner 2024"], [JBF_W_2024]),
 ("FIG", "Charleston", None, ["Best Chef: Southeast winner 2015 (Jason Stanhope)", "Outstanding Wine Program winner 2018"], [JBF_W_2015, JBF_W_2018]),
 ("Rodney Scott's BBQ", "Charleston", None, ["Best Chef: Southeast winner 2018 (Rodney Scott)"], [JBF_W_2018]),
 # Wade's is at 1000 N Pine St (Pinewood Shopping Center since 1985, eatatwades.com/history); a second Wade's-named permit sits at 964 S Pine St
 ("Wade's Restaurant", "Spartanburg", "1000", ["America's Classics 2024"], [JBF_AC_2024, "https://www.eatatwades.com/history"]),
 ("Bertha's Kitchen", "North Charleston", None, ["America's Classics 2017"], [JBF_AC_2017]),
 ("Bowens Island Restaurant", "Charleston", None, ["America's Classics 2006"],
  ["https://www.islands.com/2150019/bowens-island-restaurant-charleston-south-carolina-seafood-overlooking-scenic-marsh-james-beard-winner-fresh-caught-eats/",
   "https://charlestonlivingmag.com/salt-life-from-the-salt-marsh-to-the-table"]),
]

# verified closed (with a source we may use): they come off the list whatever the map data says
CLOSED = [
]


# The checked name, shown whatever our data calls the place: the restaurant's own (Nance's, not its SCDA permit's "Rest/Oyster"; a
# shown name is fed back into site/southcarolina.json, so without this a permit's spelling sticks). ALIAS: another name our data knows
# the place by at the same address. Wahoo's Fish House (formerly Divine Fish House) holds the site's one SCDA permit, which matches the
# map listing of its raw bar next door (Wahoo's Raw Bar & Marina).
DISPLAY = {"Nance's Creekfront": "Nance's Creekfront Restaurant", "Wahoo's Fish House": "Wahoo's Fish House"}
ALIAS = {"Wahoo's Fish House": "Wahoo's Raw Bar & Marina"}


def find(name, town, num):
    k = norm(name)
    hits = [i for i, n in enumerate(C["name"]) if (town is None or (C["city"][i] is not None and M["cities"][C["city"][i]] == town))
            and (norm(n) == k or norm(n).startswith(k + " ") or k.startswith(norm(n) + " ") or norm(n).replace(" ", "") == k.replace(" ", ""))]
    if num:
        hits = [i for i in hits if (C["addr"][i] or "").split(" ")[0] == num]
    return hits


def evidence_ok(ev, srcs, i):
    if ev == "dated":
        return any(s in DATED for s in srcs)
    if ev == "site":
        return True   # its own site, read on FETCHED, showed current hours or ordering
    insp = INSP.get(i)   # "scda": an SCDA inspection record in 2025 or 2026
    return bool(insp) and (insp[3] or "") >= "2025-01-01"


leads, n_out = [], {}
for kind, rows in GUIDES.items():
    out = []
    for name, town, num, note, founded, fnote, srcs, ev in rows:
        hits = find(name, town, num) or (find(ALIAS[name], town, num) if name in ALIAS else [])
        if len(hits) > 1 and name not in EVERY:
            lic = [i for i in hits if C["tier"][i] == 2]
            hits = lic if len(lic) == 1 else hits
        if not hits and name in ADDR and ev == "dated":
            a_, z_ = ADDR[name]
            out.append({"name": name, "address": a_, "city": town, "zip": z_, "kinds": [KIND[kind]], "dishes": [], "note": note, "founded": founded,
                        "founded_note": fnote, "website": None, "open": True, "evidence_date": "2026", "sources": srcs, "match_names": []})
            continue
        if not hits or (len(hits) > 1 and name not in EVERY):
            leads.append(f"- {kind}: {name} ({town or 'every location'}{', ' + num if num else ''}) — {len(hits)} matches in our data; not added"); continue
        for i in hits:
            if not evidence_ok(ev, srcs, i):
                leads.append(f"- {kind}: {name} ({town}) — no 2025-26 evidence it operates ({ev}); not added"); continue
            city = M["cities"][C["city"][i]]
            out.append({"name": C["name"][i], "address": C["addr"][i], "city": city, "zip": str(C["zip"][i]) if C["zip"][i] else None,
                        "kinds": [KIND[kind]], "dishes": [], "note": note, "founded": founded, "founded_note": fnote, "website": None,
                        "open": True, "evidence_date": FETCHED if ev == "site" else ("2026" if ev == "dated" else "2025-26 SCDA inspection"),
                        "sources": srcs + ([SCDA] if ev == "scda" else []), "match_names": ([name.upper()] if norm(name) != norm(C["name"][i]) else []) + ([ALIAS[name].upper()] if name in ALIAS else []),
                        **({"display": DISPLAY[name]} if name in DISPLAY else {})})
    fn = re.sub(r"[^a-z]+", "_", kind).strip("_")
    json.dump(out, open(f"{R}/app/{fn}.json", "w"), indent=1, ensure_ascii=False)
    n_out[kind] = len(out)
jb = []
for name, town, num, honors, src in JBF:
    hits = find(name, town, num)
    if len(hits) != 1:
        leads.append(f"- James Beard: {name} ({town}) — {len(hits)} matches; not added"); continue
    i = hits[0]
    jb.append({"name": C["name"][i], "address": C["addr"][i], "city": town or M["cities"][C["city"][i]], "zip": None, "honors": honors, "open": True,
               "sources": src, "match_names": [name.upper()]})
json.dump(jb, open(f"{R}/jbf.json", "w"), indent=1, ensure_ascii=False)
json.dump(CLOSED, open(f"{R}/closed.json", "w"), indent=1, ensure_ascii=False)
open(f"{R}/app/LEADS.md", "w").write("# South Carolina research leads (not yet verified)\n\nWritten by pipeline/build_research.py.\n\n" + "\n".join(leads) + "\n")
print(n_out, "| James Beard:", len(jb), "| leads:", len(leads))
