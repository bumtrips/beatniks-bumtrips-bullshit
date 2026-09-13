#!/usr/bin/env python3
"""
Build the Open Graph preview card for the BBB marketing site.

Output: assets/og-card.png  (1200 x 630, PNG)

Layout (left | right):
  - Left: brand mark, title, tagline, source URL
  - Right: square artwork

Colours are tuned for the default cyber theme; the card itself is
static (it does not change per page-theme — OG previews render in
isolated social-card viewers where theming is not visible).

Re-run when the artwork changes:
    python3 scripts/build_og_card.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ARTWORK = ROOT / "assets" / "artwork.jpg"
OUTPUT = ROOT / "assets" / "og-card.png"

W, H = 1200, 630

# Cyber-theme palette (matches default :root in styles.css).
BG = (11, 11, 11)
BG_PANEL = (24, 24, 24)
FG = (245, 245, 240)
FG_MUTE = (168, 168, 158)
ACID = (200, 255, 0)
MAGENTA = (255, 62, 165)
LINE = (60, 60, 60)

# Local font candidates — fall back gracefully.
FONT_CANDIDATES = {
    "display": [
        "/usr/share/fonts/abattis-cantarell-vf-fonts/Cantarell-VF.ttf",
        "/usr/share/fonts/google-carlito-fonts/Carlito-Bold.ttf",
        "/usr/share/fonts/abattis-cantarell-fonts/Cantarell-Bold.otf",
        "/usr/share/fonts/aajohan-comfortaa-fonts/Comfortaa-SemiBold.otf",
        "/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Bold.ttf",
    ],
    "mono": [
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Bold.ttf",
        "/usr/share/fonts/adwaita-mono-fonts/AdwaitaMono-Bold.ttf",
    ],
}


def load_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES[kind]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    # Last resort — Pillow's default bitmap font.
    return ImageFont.load_default()


def main() -> int:
    if not ARTWORK.exists():
        print(f"error: artwork not found at {ARTWORK}", file=sys.stderr)
        return 2

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Subtle scanlines overlay (cyber theme identity).
    for y in range(0, H, 3):
        draw.line([(0, y), (W, y)], fill=(255, 255, 255, 8), width=1)

    # Acid green accent bar at the top — 6 px.
    draw.rectangle([(0, 0), (W, 6)], fill=ACID)

    # Layout split: 600 px left text, 600 px right artwork.
    LEFT_PAD = 64
    RIGHT_INSET = 80
    ART_SIZE = 470
    ART_X = W - RIGHT_INSET - ART_SIZE
    ART_Y = (H - ART_SIZE) // 2

    # ---- Right: artwork square with thin acid-green border.
    artwork = Image.open(ARTWORK).convert("RGB")
    artwork = artwork.resize((ART_SIZE, ART_SIZE), Image.LANCZOS)
    img.paste(artwork, (ART_X, ART_Y))
    draw.rectangle([(ART_X - 2, ART_Y - 2), (ART_X + ART_SIZE + 1, ART_Y + ART_SIZE + 1)],
                   outline=ACID, width=3)

    # Small "2026" caption overlay (matches figcaption on the live page).
    caption_font = load_font("mono", 18)
    draw.rectangle([(ART_X + 12, ART_Y + ART_SIZE - 38), (ART_X + 110, ART_Y + ART_SIZE - 12)],
                   fill=(0, 0, 0, 200))
    draw.text((ART_X + 18, ART_Y + ART_SIZE - 34), "COVER · 2026",
              fill=ACID, font=caption_font)

    # ---- Left: brand mark + title + tagline + source.
    # Brand mark (BBB in a box) — matches .brand-mark in styles.css.
    brand_font = load_font("display", 36)
    mark_x, mark_y = LEFT_PAD, 70
    mark_size = 56
    draw.rounded_rectangle([(mark_x, mark_y), (mark_x + mark_size, mark_y + mark_size)],
                           radius=10, outline=ACID, width=3)
    bbox = draw.textbbox((0, 0), "BBB", font=brand_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((mark_x + (mark_size - tw) // 2 - bbox[0],
               mark_y + (mark_size - th) // 2 - bbox[1]),
              "BBB", fill=ACID, font=brand_font)

    # Brand name to the right of the mark.
    brand_name_font = load_font("mono", 24)
    draw.text((mark_x + mark_size + 18, mark_y + (mark_size - 24) // 2),
              "BEATNIKS · BUMTRIPS · BULLSHIT",
              fill=FG, font=brand_name_font)

    # Eyebrow label.
    eyebrow_font = load_font("mono", 20)
    draw.text((LEFT_PAD, 175),
              "A FIELD-RECORDED JOURNEY",
              fill=FG_MUTE, font=eyebrow_font)

    # Title — three lines, mixed accents (matches the page hero).
    title_font = load_font("display", 110)
    line_y = 220
    for line, accent in [
        ("BEATNIKS,", FG),
        ("BUMTRIPS,", ACID),
        ("BULLSHIT.", MAGENTA),
    ]:
        draw.text((LEFT_PAD, line_y), line, fill=accent, font=title_font)
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_y += bbox[3] - bbox[1] + 6

    # Tagline.
    tagline_font = load_font("mono", 28)
    draw.text((LEFT_PAD, line_y + 14),
              "your secret audio dose of acid.",
              fill=ACID, font=tagline_font)

    # Source URL pinned to the bottom-left.
    src_font = load_font("mono", 20)
    draw.text((LEFT_PAD, H - 64),
              "anchor.fm/s/4431c4ac/podcast/rss",
              fill=FG_MUTE, font=src_font)

    # Bottom divider line.
    draw.line([(0, H - 24), (W, H - 24)], fill=LINE, width=1)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT, format="PNG", optimize=True)
    print(f"wrote {OUTPUT}  ({OUTPUT.stat().st_size // 1024} KB, {W}x{H})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
