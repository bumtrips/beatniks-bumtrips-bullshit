#!/usr/bin/env python3
"""
Generate responsive artwork variants, favicon, and apple-touch-icon
for the BBB marketing site.

Inputs:  assets/artwork.jpg (1200x1200 JPEG, baseline)
Outputs:
  assets/artwork-600.jpg           (mobile JPEG, ~30 KB)
  assets/artwork-1200.jpg          (desktop JPEG, ~120 KB)
  assets/artwork-600.webp          (mobile WebP, ~18 KB)
  assets/artwork-1200.webp         (desktop WebP, ~70 KB)
  assets/favicon-32.png            (32x32 favicon fallback, ~1 KB)
  assets/apple-touch-icon.png      (180x180 touch icon, ~25 KB)
  assets/favicon.svg               (vector favicon, ~1 KB)

Designed to be called by a weekly GitHub Actions cron
(see .github/workflows/build-assets.yml). Idempotent: skips if every
output exists and is newer than the input.

Usage:
    python3 scripts/build_assets.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SRC = ASSETS / "artwork.jpg"

# (suffix, width, height, format, quality, optimize_args)
JPEG_VARIANTS = [
    ("artwork-600.jpg",   600,  600,  "JPEG", 82, {"optimize": True, "progressive": True}),
    ("artwork-1200.jpg",  1200, 1200, "JPEG", 82, {"optimize": True, "progressive": True}),
]
WEBP_VARIANTS = [
    ("artwork-600.webp",  600,  600,  "WEBP", 80, {"method": 6}),
    ("artwork-1200.webp", 1200, 1200, "WEBP", 80, {"method": 6}),
]

# Tiny BBB-on-acid-green vector favicon — visible at every size, matches the
# brand-mark in styles.css. Hand-tuned SVG so we don't depend on a font.
FAVICON_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="10" fill="#0b0b0b"/>
  <rect x="3" y="3" width="58" height="58" rx="8" fill="none" stroke="#c8ff00" stroke-width="3"/>
  <text x="32" y="42" text-anchor="middle" font-family="ui-monospace, 'Courier New', monospace"
        font-size="26" font-weight="900" fill="#c8ff00" letter-spacing="-1">BBB</text>
</svg>
"""


def _pngquant_available() -> bool:
    return shutil.which("pngquant") is not None


def _pngquant(out: Path) -> None:
    if not _pngquant_available():
        return
    subprocess.run(
        ["pngquant", "--quality=70-85", "--force", "--skip-if-larger",
         "--output", str(out), str(out)],
        check=False,
    )


def _needs_build(src: Path, out: Path) -> bool:
    if not out.exists():
        return True
    return src.stat().st_mtime > out.stat().st_mtime


def _save(img: Image.Image, out: Path, fmt: str, quality: int, extra: dict) -> None:
    if fmt == "JPEG":
        img.save(out, format="JPEG", quality=quality, **extra)
    elif fmt == "WEBP":
        img.save(out, format="WEBP", quality=quality, **extra)
    elif fmt == "PNG":
        img.save(out, format="PNG", optimize=True, **extra)
    else:
        raise ValueError(f"unsupported format: {fmt}")


def main() -> int:
    if not SRC.exists():
        print(f"error: {SRC} not found", file=sys.stderr)
        return 2

    src = Image.open(SRC).convert("RGB")
    print(f"source: {SRC.name} {src.size}")

    changed = []

    # JPEG + WebP variants.
    for suffix, w, h, fmt, q, extra in JPEG_VARIANTS + WEBP_VARIANTS:
        out = ASSETS / suffix
        if not _needs_build(SRC, out):
            print(f"skip  {suffix} (up to date)")
            continue
        resized = src.resize((w, h), Image.LANCZOS)
        _save(resized, out, fmt, q, extra)
        kb = out.stat().st_size // 1024
        print(f"wrote {suffix}  ({kb} KB, {w}x{h}, {fmt})")
        changed.append(suffix)

    # favicon-32.png — fallback for browsers that don't honor SVG.
    out = ASSETS / "favicon-32.png"
    if _needs_build(SRC, out):
        small = src.resize((32, 32), Image.LANCZOS)
        _save(small, out, "PNG", 0, {})
        _pngquant(out)
        kb = out.stat().st_size // 1024
        print(f"wrote favicon-32.png  ({kb} KB, 32x32)")
        changed.append("favicon-32.png")

    # apple-touch-icon.png — 180x180, no transparency, full-bleed artwork.
    out = ASSETS / "apple-touch-icon.png"
    if _needs_build(SRC, out):
        big = src.resize((180, 180), Image.LANCZOS)
        _save(big, out, "PNG", 0, {})
        _pngquant(out)
        kb = out.stat().st_size // 1024
        print(f"wrote apple-touch-icon.png  ({kb} KB, 180x180)")
        changed.append("apple-touch-icon.png")

    # favicon.svg — vector, hand-tuned, never changes from source.
    out = ASSETS / "favicon.svg"
    if _needs_build(SRC, out):
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
