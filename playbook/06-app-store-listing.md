# App Store listing (ASO)

Written by `scripts/make-listing.py` from `site-numbers.json` (2026-10-28); re-run it after every data refresh, never hand-edit.
The machine copy is `app-store/listing.json` (read by `../scripts/asc_listing.py` once Nick creates the App Store Connect record and
adds `"com.southcarolinaeats.ios": "sc-eats"` to its FOLDERS). The URLs assume southcarolina.eatsranked.com is live; until Nick's
CNAME resolves, use https://nickstrom5.github.io/southcarolina-eats/.

## Name (30 max)
`South Carolina Eats` (19)

## Subtitle (30 max)
`BBQ, Shrimp & Grits, Oysters` (28)

Together they index: south, carolina, eats, bbq, shrimp, grits, oysters. Home Screen name: SC Eats.

## Keywords (100 max)
`charleston,myrtle beach,greenville,columbia,hilton head,lowcountry,gullah,barbecue,seafood,beaufort` (99)

- No word repeats the name or subtitle; no trademarks (no chain or team names: not Clemson, Gamecocks or Palmetto Bluff), no "best", "top" or "#1".
- Towns are the biggest win; Spartanburg, Rock Hill, Florence, Aiken and Murrells Inlet didn't fit. Rotate them in after a month of App
  Store Connect search-term data. Apple's public search can't be used for this research (itunes.apple.com's robots.txt blocks Claude).

## Promotional text (170 max, editable any time without review)
`17 barbecue joints, 18 Lowcountry seafood places and Gullah Geechee kitchens, each checked by hand. Plus 15,000+ South Carolina restaurants near you.` (149)

## Description (3196 of 4,000)
```
South Carolina's restaurants, from whole hog with mustard sauce to shrimp and grits by the marsh.

South Carolina Eats is a free guide to eating in South Carolina: 17 barbecue joints for whole hog, mustard sauce and hash over rice, 18 places for Lowcountry and Grand Strand seafood, 4 Gullah Geechee kitchens and 6 meat-and-threes and old drive-ins, all checked by hand, plus 15,178 restaurants, cafés, bars and bakeries in 318 towns, from Greenville and Spartanburg to Columbia, Charleston, Myrtle Beach and Hilton Head. 12,622 of them are matched to the SC Department of Agriculture's retail food permits. No account, no ads.

SOUTH CAROLINA GUIDES
• Whole-Hog & Mustard Barbecue: pits that cook whole hogs over coals, the Midlands' mustard sauce, and hash and rice.
• Lowcountry & Grand Strand Seafood: shrimp and grits, she-crab soup, oyster roasts and Murrells Inlet's fried shrimp.
• Gullah Geechee Cooking: okra soup, red rice, crab rice and greens, from St. Helena Island to Charleston.
• Meat-and-Threes & Drive-Ins: steam-table plates and drive-ins that date back to the 1940s.
• Award winners: 39 places in the MICHELIN Guide American South or honored by the James Beard Foundation, with a switch for the Bib Gourmands.
• SCDA Inspection Grades: the SC Department of Agriculture's latest posted grade (A, B or C) and date for 12,564 places, with recent inspections and links to SCDA's reports.

FIND IT FAST
• Sort by distance, or browse the map by guide.
• Search by name, town, street or dish: "shrimp and grits charleston", "whole hog florence".
• Filter by town or cuisine, or hide chains.
• Save places, and find hand-checked places from iPhone search (Spotlight).

LIVE DETAILS FROM APPLE MAPS
Tap "Ratings, hours & photos" on any place to open Apple Maps' own place card, with current hours, photos, ratings and directions.

HOW THE LISTS ARE BUILT
Every guide place was checked by hand in October 2026: a page names it for the food (Discover South Carolina, local news or the place's own site), and a 2025 or 2026 source shows it's open. The rest come from Overture Maps open data, checked against SCDA's statewide permit list. Website links are checked too. Nothing is ranked by star ratings, and the app computes no grades: each grade is SCDA's own, as posted.

FRESH DATA
The app checks its website for newer restaurant data at most once a day and uses it from the next launch.

PRIVATE BY DESIGN
No account, no tracking, no ads. Your location, if you share it, only sorts lists on your device. Saved places stay on your device.

Places open and close, so check before you go. Spot a mistake? Email nick@eatsranked.com.

An independent app, not affiliated with any restaurant, chain or government agency (including the State of South Carolina, the SC Department of Agriculture, the SC Department of Public Health and the SC Department of Revenue), or with the MICHELIN Guide or the James Beard Foundation. MICHELIN and the MICHELIN Guide are trademarks of Michelin. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Place data from Overture Maps Foundation (CDLA Permissive 2.0) and others; sources and licenses are on the About tab.
```

## What's New (1.0)
`First release: whole-hog barbecue, Lowcountry seafood, Gullah Geechee cooking and 15,000+ South Carolina restaurants.`

## Screenshots
Framed by `scripts/appstore-screenshots.py`: `app-store/iphone/` (8, 1320x2868, the 6.9" slot) and `app-store/ipad/` (6, 2064x2752, the
13" slot). Upload one file at a time in file order and check the order after a reload. No negative board and no place whose latest
SCDA posted grade is B or C appears in any image.

## Category and age rating
Primary Food & Drink, secondary Travel. Age rating: alcohol references "Infrequent" (bars, taverns) → 13+; everything else None/No.
Pricing $0.00, available in the United States. Content rights: yes, third-party content, with the rights (open data, public records,
Apple's place card). Untick "Sign-in required".

## App Review
Reply and recording script: `13-app-review-reply.md`. Put the reply in App Review Information → Notes from the start.
