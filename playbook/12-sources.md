# South Carolina sources (checked 2026-10-26)

Every host was robots-checked with `pipeline/check_sources.py` (RFC 9309 matcher, cache in `data/research/source_hosts.json`) before
any request beyond robots.txt. ArcGIS REST hosts answer 403 to `/robots.txt`; the documented REST API answers normally, so
`services5.arcgis.com` is an API host (Colorado, Connecticut and Arizona precedent).

## Official records

| Source | What | Terms / reuse | Cadence | Status |
|---|---|---|---|---|
| **SC Food Grades** map service: ArcGIS Online item `d9880f86d585460aac53f5b502fc2754` ("Restaurants", owner now `GIS_AGOL_Services`, created 2026-02-19), `services5.arcgis.com/G4BLIH7rTQoIjCFv/arcgis/rest/services/Restaurants/FeatureServer`. Read through the documented REST API, ≤2,000 rows a request, one request at a time (`pipeline/fetch_official.py`). | **Layer 0 "Restaurants"**: 24,244 permits with a point (UTM 17N; fetched as WGS84 with `outSR=4326`): PERMIT_ID, PROG_CODE, FACILITY, ADDRESS (150 chars), CITY (blank on 9,186), ZIPCODE, INSP_DATE, MAX_DATE. **Table 4 "Restaurants_Steton"**: 137,403 inspections, 2023-10-27 to 2026-10-22: PERMIT_ID, PROG_CODE, COUNTY code, ADDRESS (30 chars), CITY, ZIPCODE, **SCORE (empty on every row)**, POSTED_GRADE, FACILITY, INSP_DATE, AuditResultGlobalID (report PDF id), AuditTypeName, Insp_Num, Active. | Item: no license, no access terms, no description (licenseInfo and accessInformation empty); public; capabilities Query, Extract. The Food Grades web app's footer reads "© South Carolina Department of Agriculture. All Rights Reserved." Inspection results are facts and public records. **Reuse confirmation drafted** to scfoodgrades@scda.sc.gov (`playbook/records-requests.md`), not sent: Nick's call. | Edited daily (both layers last edited 2026-10-26 05:47); the web app said "Data current as of October 25, 2026". | **Used**: the permit list (calibration, "official" places, places the listings lack) and every posted grade. |
| **SC Food Grades** web app, apps.dhec.sc.gov/Environment/FoodGrades/ (maintained by SC DPH for SCDA) | Map search (last two inspections) and advanced search (three years). Facility types: 206 Retail Food Establishments, 204 Mobile Food Units, 208 Institutions, 211 Grocery Stores (the page's own option values) | robots.txt 404 (no rules) | daily | Linked (renders, 200). Never scraped. Its disclaimer is quoted verbatim in About (below). |
| Inspection report PDFs, `pubdoc.dhec.sc.gov/inspection/<AuditResultGlobalID>.pdf` | One PDF per inspection | robots.txt 404 | — | Linked per inspection (200, application/pdf). Three PDFs were read once to learn what the type codes mean (below); none are harvested and no score is taken from them. |
| SCDA "Understanding Restaurant Inspections", agriculture.sc.gov/permits-and-inspections/retail-food-safety/understanding-restaurant-inspections/ | The grade rules: A above 87, B 78–87, C below 78; 8-403.10(G): the posted grade can differ from the score; five inspection types (permit, routine, follow-up, food safety check, limited scope) | robots allow (Cloudflare answers plain curl 403; read in the browser pane) | — | Cited; linked from About. |
| SC Department of Revenue, Alcohol Beverage Licensing (dor.sc.gov/alcohol-beverage-licensing-abl/license-searches-abl-resources) | Licensed locations, suspended/revoked licenses: MyDORWAY search apps only, no bulk export | robots 404 | — | **Not used.** Bulk-list request drafted (`playbook/records-requests.md`), not sent. "Serves alcohol" shows "—". |
| County property values (Charleston, Greenville, Richland, Horry) | Per-county assessor sites | no statewide open set, no reuse license found | — | **Not used** (no building-value board). |
| scdhec.gov | DHEC's old site | — | — | **Never linked** (the state prompt: TLS certificate mismatch). |

### Schema facts that change what we may say (read before counting)
- **No score.** SCORE is empty on all 137,403 rows: the app and site show SCDA's **posted grade** and its date as official, and derive no
  score or grade. Boards rank by posted grade ("Latest grade B or C"; "Grade A, no B or C in 3 years").
- **POSTED_GRADE** is space-padded: A 126,017, B 8,286, C 3,083, **S 17** (no "N/A" left). The S rows are all type COMPL; the report
  for one (Chophouse 119, Hilton Head Island, 2026-09-09) is a "Retail Food Suspension Notification" ("Removed Letter Grade and applied
  Suspension Sticker"). A place whose latest record is S is left off (its permit isn't in force); S rows show in history as
  "S (suspension notice)".
- **AuditTypeName** changed vocabulary in mid-2024: `10_Routine Inspection` → `Routine`, `15_Follow-Up Inspection` → `Follow Up`,
  plus `COMPL` (pre-operational inspection, reason "05. Compliance", result "Permit Issued" or a suspension), `COO` (pre-operational,
  "04. Change of Ownership"), `11_Permit Issued Inspection-New Facility`, `01_...-Change of Ownership`, `14_Permit Reinstated`,
  `Complaint` (14), `Outbreak` (4). Labels in `official.ITYPE`.
- **Dates**: INSP_DATE is local time stored as UTC (visits cluster 8 am–4 pm "UTC"), so the UTC calendar date is the local date.
- **Active** is mixed-case text ("true", "True", "false", "False").
- **PROG_CODE** (confirmed by the web app's own facility-type options): 206 Retail Food Establishment (restaurants, plus c-store counters,
  grocery delis, hotels, clubs, offices), 204 Mobile Food Unit, 208 Institution, 211 Grocery Store.
- **The permit layer lags**: 3,627 retail-food permits SCDA inspected (2,257 last inspected in 2026, many new) aren't in layer 0, and it
  still holds permits replaced at a change of owner. `official.load()` joins both: the layer's point where it has one, else Overture
  address points (249) and the US Census batch geocoder (3,421); 2,040 permits (mostly mobile units and caterers) stay unplaced.
- **Open** = inspected since 2026-10-19 minus 18 months (2025-04-19), latest record not a suspension, Active true. Every establishment
  gets one to four routine inspections a year, and seasonal Grand Strand places are inspected each season. 20,014 open retail-food
  permits (schools, hospitals, jails and caterers by name left out), 2,405 open mobile units, 942 open grocery permits.
- **Records through** = fetch date minus 7 days (2026-10-19): the site warns that "an inspection report may not be immediately available
  online following an inspection".
- Change of owner = a new permit number at the same address. A place's history joins the permits of one business (same address, a
  name in common) whose names agree with the place.

### SCDA's disclaimer (quote verbatim in About)
> Information provided in the application is intended to be used for general reference. SCDA provides no warranty, expressed or implied,
> as to the accuracy, reliability or completeness of furnished data. This database includes all permitted retail food establishments,
> some of which are not open to the general public for dining.

## Map listings and calibration

- **Overture Maps places** 2026-10-21.0 (latest release): 24,612 eating and drinking listings with region SC (42,938 in the bounding box,
  which also holds Charlotte, Augusta and Savannah: clipped to the state outline; Fort Mill, North Augusta and Hardeeville stay).
  1,078 marked permanently closed by Overture. Divisions from Overture (state and 46 counties).
- **UCSD Google Local 2021** (`meta-South_Carolina.json.gz`, mcauleylab.ucsd.edu, 18.7 MB): 14,922 food listings (1,793 closed by 2021);
  11,300 matched to Overture listings. Web leaderboard only, never the app.
- **Calibration** (`pipeline/calibrate.py`, statewide, against the 20,014 open SCDA retail-food permits; county by county; a match is
  the same name nearby or the same street address with a distinctive word in common):

| Listing group | n | matched an open SCDA permit |
|---|---|---|
| Meta + open in Google 2021 | 8,055 | **83.8%** (Charleston Co. 81.5, Greenville Co. 88.2, Richland Co. 87.7, Horry Co. 82.0) |
| Meta only | 7,762 | 42.4% |
| Chain store list (AllThePlaces/DAC) + Google 2021 | 61 | 54.1% |
| Chain store list only | 406 | 48.3% |
| Foursquare/BrightQuery/Microsoft + Google 2021 | 2,111 | 27.6% |
| BrightQuery only | 1,887 | 15.7% |
| Microsoft only | 1,124 | 25.4% |
| **Foursquare only** | 1,435 | **9.7%** |
| Overture says closed | 916 | 5.2% |
| Google 2021 says closed | 718 | 5.3% |

App grouping (no Google): Meta ≥ 0.95 confidence **80.8%** (9,854), Meta 0.90–0.95 51.5% (2,664), Meta < 0.90 21.2% (3,401),
BrightQuery ≥ 0.95 27.5%, brand feeds 48.9%, other sources 16.5%.
Coverage the other way: the open map listings hold **58.0%** of 18,919 open retail-food permits (businesses) and **66.8%** of the
6,614 named like a place to eat (Greenville Co. 72.7%, Horry 66.9%, Richland 65.4%, Charleston 65.2%). Permit-only places named like a
restaurant or a restaurant chain are added from the list (1,811 rows, web build).
Measured 2026-10-28, after SCDA's ZIP-centroid and street-guess points were re-placed (geocode_official.py; before: Meta + Google
81.8%, app Meta ≥ 0.95 78.4%). These match rates are lower bounds: a permit can carry an owner's or old name, and a bar that serves no food may hold no food permit.
The keep rules follow the numbers: web keeps Meta and chain-feed listings (plus official and hand-checked); the app keeps official,
hand-checked, Meta ≥ 0.95, Meta ≥ 0.90 with a website, and chain feeds.

## Honors

- **MICHELIN Guide American South 2026** (revealed 2026-10-21): guide.michelin.com/us/en/south-carolina/restaurants lists **27**: 4 One
  Star (Scoundrel, Greenville; Vern's, Malagón Mercado y Taperia, Wild Common, Charleston), **4 Bib Gourmand** (Leon's Oyster Shop, Rivayat
  Creative Indian, Palmira, Charleston; Okàn, Bluffton), 19 Recommended (Charleston, Sullivan's Island, Hanahan, Greenville, Travelers
  Rest, Columbia, Myrtle Beach, Bluffton). No Green Star. Lewis Barbecue, a 2025 Bib Gourmand, is Recommended in 2026. guide.michelin.com
  answers curl with an empty 202 bot challenge (never retried); read with Claude's web fetcher, each restaurant page for its address
  (`data/research/michelin.json`). Shown as "1 MICHELIN Star" text with the trademark line. **Bib Gourmand filter applies** (BIB-GOURMAND-FILTER.md).
- **James Beard** (`pipeline/build_research.py` → `data/research/jbf.json`, 18 places): America's Classics Bowens Island (2006), Bertha's
  Kitchen (2017), Wade's (2024); wins FIG (Best Chef: Southeast 2015 Jason Stanhope; Outstanding Wine Program 2018), Rodney Scott's BBQ
  (Best Chef: Southeast 2018), Lula Drake Wine Parlour (Outstanding Wine and Other Beverages Program 2024); 2026 finalists Scoundrel
  (Joe Cash), Merci, Weltons Tiny Bakeshop (no wins); 2025-26 semifinalists Chubby Fish, Palmira Barbecue, Stems & Skins, Graft Wine
  Shop, Jianna, Renzo, Bintü Atelier, Hook & Barrel, City Limits Barbeque. Sources: jamesbeard.org stories (robots ok). Not listed:
  closed winners (Louis Osteen 2004, Hominy Grill 2008, McCrady's 2010) and Mike Lata's 2009 win (no usable source fetched yet).
- **Fresh on the Menu** (freshonthemenu.com, an SCDA program; robots ok): the member list is "All rights reserved". Not used; ask first.

## Research hosts (robots, 2026-10-26)
Usable: charlestoncitypaper.com, charlestonmag.com, charlestonlivingmag.com, discoversouthcarolina.com, scetv.org,
gullahgeecheecorridor.org, scbarbecue.com, wltx.com, wcnc.com, wsoctv.com, upstatebusinessjournal.com, follycurrent.com, islands.com,
southernfoodways.org, en.wikipedia.org, jamesbeard.org, archive.jamesbeard.org.
Blocked (robots or bot check): postandcourier.com, scbiz.com, wspa.com, greenvilleonline.com, eater.com, southernliving.com,
gardenandgun.com, live5news.com, counton2.com, wyff4.com, columbiabusinessreport.com, wistv.com, wmbfnews.com, wbtv.com, free-times.com
(bot check), sfexaminer.com, charlestonbusiness.com, guide.michelin.com (bot check: web fetcher only). Unreachable: thestate.com,
myrtlebeachonline.com, islandpacket.com, carolinaliving.com, berthaskitchensc.com.
