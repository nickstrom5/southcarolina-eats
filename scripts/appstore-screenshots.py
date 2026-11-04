#!/usr/bin/env python3
"""Build the captioned App Store screenshots from simulator captures (the family's frame, from chi-eats/ios/scripts/appstore-screenshots.py).

Usage (from sc-eats/): .venv/bin/python scripts/appstore-screenshots.py
Reads playbook/app-store/raw/iphone/*.png (1320x2868, iPhone 17 Pro Max) and playbook/app-store/raw/ipad/*.png (2064x2752, iPad Pro 13"),
made with: OUT=$PWD/playbook/app-store/raw/<iphone|ipad> SLEEP=14 bash scripts/capture-screenshots.sh <udid> <screens>
(the map needs about 20 s on a busy Mac). Writes playbook/app-store/iphone/NN-name.png and .../ipad/NN-name.png at the same sizes.
Each frame: the oyster-cream page tint behind, a flag-indigo caption band with white condensed type and a short shrimp-coral rule
(Nick's flag & marsh palette), and the real capture below in a rounded frame.
Rules (STATE_EATS_PLAYBOOK.md "Screenshots"): real captures, home screen first, no negative board and no place whose latest SCDA
posted grade is B or C in any image (a unit test checks the screenshot picks), map zoomed in to individual pins; captions make no price claim ("free"), use no third-party marks (say "award winners", not James Beard) and no "best".
"""
import itertools
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
LAKE, SAND, BG, WHITE, INK = (27, 42, 87), (232, 131, 107), (246, 241, 231), (255, 255, 255), (20, 29, 59)   # flag indigo, shrimp coral, oyster cream
FONT = "/System/Library/Fonts/Avenir Next Condensed.ttc"   # Heavy face; the app itself uses the system compressed face

IPHONE = [("01-home", "home.png", "South Carolina's food, list by list"),
          ("02-bbq", "bbq.png", "Whole hog and hash, nearest first"),
          ("03-detail", "detail.png", "Each place, with notes checked by hand"),
          ("04-seafood", "seafood.png", "Shrimp and grits to oyster roasts"),
          ("05-gullah", "gullah.png", "Gullah Geechee kitchens"),
          ("06-map", "map.png", "Hand-checked places on the map"),
          ("07-honors", "honors.png", "Award winners and classics"),
          ("08-saved", "saved.png", "Keep your short list")]
IPAD = [("01-home", "home.png", "South Carolina's food, list by list"),
        ("02-bbq", "bbq.png", "Whole hog and hash, nearest first"),
        ("03-seafood", "seafood.png", "Shrimp and grits to oyster roasts"),
        ("04-gullah", "gullah.png", "Gullah Geechee kitchens"),
        ("05-map", "map.png", "Hand-checked places on the map"),
        ("06-honors", "honors.png", "Award winners and classics")]
BANNED = ("free", "best", "#1", "top ", "james beard", "michelin")   # price claims, rankings and others' marks stay out of captions
for _, _, cap in IPHONE + IPAD:
    assert not any(b in cap.lower() for b in BANNED), cap


def font(size):
    for index in (8, 0):                # Heavy, else Bold (upright faces of Avenir Next Condensed)
        try:
            return ImageFont.truetype(FONT, size, index=index)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_lines(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    lines += [cur]
    if len(lines) > 1:    # the same number of lines, split where the longest is shortest, so no word sits alone ("... LIST BY / LIST")
        cuts = [[" ".join(words[a:b]) for a, b in zip((0,) + c, c + (len(words),))]
                for c in itertools.combinations(range(1, len(words)), len(lines) - 1)]
        lines = min((c for c in cuts if max(d.textlength(x, font=f) for x in c) <= width),
                    key=lambda c: max(d.textlength(x, font=f) for x in c), default=lines)
    return lines


def frame(src, out, caption, W, H, band, fsize, radius):
    shot = Image.open(src).convert("RGB")
    assert shot.size == (W, H), f"{src}: {shot.size}, expected {(W, H)}"
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, W, band], fill=LAKE)
    f = font(fsize)
    lines = fit_lines(d, caption.upper(), f, W * 0.86)
    lh = int(fsize * 1.05)
    y = (band - lh * len(lines)) // 2 - int(fsize * 0.08)
    for line in lines:
        w = d.textlength(line, font=f)
        d.text(((W - w) / 2, y), line, font=f, fill=WHITE)
        y += lh
    d.rectangle([(W - 160) // 2, band - 34, (W + 160) // 2, band - 24], fill=SAND)
    top = band + int(H * 0.035)
    scale = min((H - top - int(H * 0.03)) / shot.height, (W * 0.9) / shot.width)
    sw, sh = int(shot.width * scale), int(shot.height * scale)
    x = (W - sw) // 2
    pad = int(W * 0.012)
    d.rounded_rectangle([x - pad, top - pad, x + sw + pad, top + sh + pad], radius=radius + pad, fill=INK)
    shot = shot.resize((sw, sh), Image.LANCZOS)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=radius, fill=255)
    canvas.paste(shot, (x, top), mask)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, optimize=True)
    print("wrote", out.relative_to(ROOT))


for d_ in ("iphone", "ipad"):   # a renamed or dropped shot must not linger in the upload folder
    for old in (ROOT / "playbook/app-store" / d_).glob("*.png"):
        old.unlink()
for name, cap, caption in IPHONE:
    frame(ROOT / "playbook/app-store/raw/iphone" / cap, ROOT / "playbook/app-store/iphone" / f"{name}.png", caption, 1320, 2868, 520, 118, 96)
for name, cap, caption in IPAD:
    frame(ROOT / "playbook/app-store/raw/ipad" / cap, ROOT / "playbook/app-store/ipad" / f"{name}.png", caption, 2064, 2752, 420, 120, 60)
