#!/usr/bin/env python3
"""
Generate the favicon and apple-touch-icon for the BBB marketing site.

The hero cover is an inline SVG (see index.html) that uses the 6-theme CSS
variable cascade, so it doesn't need raster variants. This script only
generates the small icon assets that browsers request directly.

Inputs:  (none — favicon SVG is hand-authored)
Outputs:
  assets/favicon.svg         (vector favicon, ~1 KB)
  assets/favicon-32.png      (32x32 favicon fallback, ~2 KB)
  assets/apple-touch-icon.png (180x180 touch icon, ~25 KB)

Designed to be called by a weekly GitHub Actions cron
(see .github/workflows/build-assets.yml) — that workflow is no longer
scheduled but is retained as a manual-dispatch entry-point if artwork
ever needs to be regenerated. The script is idempotent: it skips files
that are already up to date.

Usage:
    python3 scripts/build_assets.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# BBB-on-acid-green vector favicon — visible at every size, matches the
# brand-mark in styles.css and the inline cover SVG. Hand-tuned SVG so we
# don't depend on a font.
FAVICON_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="10" fill="#0b0b0b"/>
  <rect x="3" y="3" width="58" height="58" rx="8" fill="none" stroke="#c8ff00" stroke-width="3"/>
  <text x="32" y="42" text-anchor="middle" font-family="ui-monospace, 'Courier New', monospace"
        font-size="26" font-weight="900" fill="#c8ff00" letter-spacing="-1">BBB</text>
</svg>
"""


def _pngquant(out: Path) -> None:
    if shutil.which("pngquant") is None:
        return
    subprocess.run(
        ["pngquant", "--quality=70-85", "--force", "--skip-if-larger",
         "--output", str(out), str(out)],
        check=False,
    )


def _needs_build(src: Path | None, out: Path) -> bool:
    if not out.exists():
        return True
    if src is None:
        return False
    return src.stat().st_mtime > out.stat().st_mtime


def _render_brand_png(size: int, out: Path) -> None:
    """Render a square brand-mark at `size`×`size` PNG, matches favicon SVG."""
    img = Image.new("RGB", (size, size), (11, 11, 11))
    draw = ImageDraw.Draw(img)
    # Acid-green rounded border.
    border = max(2, size // 22)
    radius = size // 7
    draw.rounded_rectangle(
        [(border // 2 + 1, border // 2 + 1), (size - border // 2 - 2, size - border // 2 - 2)],
        radius=radius,
        outline=(200, 255, 0),
        width=border,
    )
    # "BBB" centered — fall back to Pillow default bitmap font for portability.
    text = "BBB"
    try:
        from PIL import ImageFont
        # Try a generic monospace bold if available.
        candidates = [
            "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Bold.ttf",
        ]
        font = None
        for c in candidates:
            if os.path.exists(c):
                font = ImageFont.truetype(c, int(size * 0.42))
                break
        if font is None:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((size - tw) // 2 - bbox[0], (size - th) // 2 - bbox[1] - size * 0.04),
            text, fill=(200, 255, 0), font=font,
        )
    except Exception:
        # If text rendering fails, the bordered square still reads as the brand mark.
        pass
    img.save(out, format="PNG", optimize=True)
    _pngquant(out)


def main() -> int:
    changed = []

    # favicon-32.png — fallback for browsers that don't honor SVG.
    out = ASSETS / "favicon-32.png"
    if _needs_build(None, out) or True:  # always regenerate, it's tiny
        _render_brand_png(32, out)
        kb = out.stat().st_size // 1024
        print(f"wrote favicon-32.png  ({kb} KB, 32x32)")
        changed.append("favicon-32.png")

    # apple-touch-icon.png — 180x180, full-bleed brand mark.
    out = ASSETS / "apple-touch-icon.png"
    if _needs_build(None, out) or True:
        _render_brand_png(180, out)
        kb = out.stat().st_size // 1024
        print(f"wrote apple-touch-icon.png  ({kb} KB, 180x180)")
        changed.append("apple-touch-icon.png")

    # favicon.svg — vector, never changes.
    out = ASSETS / "favicon.svg"
    if _needs_build(None, out):
        out.write_text(FAVICON_SVG, encoding="utf-8")
        kb = out.stat().st_size // 1024
        print(f"wrote favicon.svg  ({kb} KB)")
        changed.append("favicon.svg")

    if not changed:
        print("no change (all assets up to date)")
    else:
        print(f"updated: {len(changed)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
