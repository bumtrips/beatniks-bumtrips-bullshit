#!/usr/bin/env python3
"""
Refresh the auto-managed episode list on the BBB marketing page.

What this does
--------------
1. Invokes the Rust `episodes-fetcher` binary (scripts/episodes-fetcher/),
   which fetches the live Anchor.fm RSS + iTunes Lookup API and writes:
     - data/parsed_episodes.json   (latest + total episodes)
     - data/apple_episode_ids.json (merged Apple Podcasts cache)
2. Renders an HTML block (ordered list + an "ep-count / archive" footer).
3. Updates whichever marker regions exist inside `index.src.html`:
   - <!-- AUTO-EPISODES-START --> ... <!-- AUTO-EPISODES-END -->
       -> ordered list of latest N episodes
   - <!-- AUTO-MARQUEE -->...<!-- /AUTO-MARQUEE -->
       -> " . "-joined latest titles for the scrolling marquee
   - <!-- AUTO-LASTREFRESH -->...<!-- /AUTO-LASTREFRESH -->
       -> current ISO 8601 UTC timestamp
   - <!-- AUTO-EPCOUNT -->N<!-- /AUTO-EPCOUNT -->
       -> integer episode count from the feed

   Regions whose markers are absent from the file are skipped -- they
   may have been removed deliberately from the page (e.g. the old
   footer ticker's AUTO-EPCOUNT / AUTO-LASTREFRESH spans).

`index.src.html` is the source of truth; `index.html` is generated from
it by `scripts/minify.py` (which preserves the markers). Always run
this script against the source file, then re-run minify.py.

Designed to be called by a daily GitHub Actions cron (see
.github/workflows/refresh-episodes.yml). Idempotent: if the rendered
output equals what's already in the file, it exits 0 without rewriting.

Rust backend (no libraries, stdlib only) lives in
scripts/episodes-fetcher/. The build pipeline is:
    cargo build --release --manifest-path scripts/episodes-fetcher/Cargo.toml
and the binary is invoked as either
    scripts/episodes-fetcher/target/release/episodes-fetcher <repo-root>
or, if not yet built, via
    cargo run --release --quiet --manifest-path ... -- <repo-root>

Usage
-----
    python3 scripts/refresh_episodes.py [INDEX_SRC_PATH]

Defaults to `index.src.html` in the repo root when run from CI.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from episodes import (
    EPCOUNT_CLOSE,
    EPCOUNT_OPEN,
    EPISODES_END,
    EPISODES_START,
    LASTREFRESH_CLOSE,
    LASTREFRESH_OPEN,
    MARQUEE_CLOSE,
    MARQUEE_OPEN,
    N_EPISODES,
)
from episodes.regions import (
    _norm,
    extract_inline,
    extract_region,
    replace_inline,
    replace_region,
)
from episodes.render import render_episodes_block, render_marquee_items


REPO_ROOT = Path(__file__).resolve().parent.parent
FETCHER_DIR = REPO_ROOT / "scripts" / "episodes-fetcher"
FETCHER_BIN = FETCHER_DIR / "target" / "release" / "episodes-fetcher"
PARSED_PATH = REPO_ROOT / "data" / "parsed_episodes.json"
APPLE_PATH = REPO_ROOT / "data" / "apple_episode_ids.json"


def run_fetcher() -> None:
    """Invoke the Rust backend. Prefer the prebuilt binary, fall back
    to `cargo run` so first-time dev setups work without a build step."""
    if FETCHER_BIN.exists() and os.access(FETCHER_BIN, os.X_OK):
        cmd = [str(FETCHER_BIN), str(REPO_ROOT)]
    else:
        cmd = [
            "cargo", "run", "--release", "--quiet",
            "--manifest-path", str(FETCHER_DIR / "Cargo.toml"),
            "--", str(REPO_ROOT),
        ]
    r = subprocess.run(cmd, check=False)
    if r.returncode != 0:
        sys.stderr.write("error: episodes-fetcher (Rust) failed\n")
        sys.exit(r.returncode or 1)


def load_json(path: Path) -> object:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    index_path = sys.argv[1] if len(sys.argv) > 1 else "index.src.html"
    if not os.path.exists(index_path):
        print(f"error: {index_path} not found", file=sys.stderr)
        return 2

    run_fetcher()

    if not PARSED_PATH.exists():
        print("error: data/parsed_episodes.json missing after fetch", file=sys.stderr)
        return 3

    parsed = load_json(PARSED_PATH)
    eps = parsed.get("episodes") or []
    if not eps:
        print("error: feed parsed but no episodes found", file=sys.stderr)
        return 3
    total = len(eps)
    latest = eps[:N_EPISODES]
    cached = load_json(APPLE_PATH) if APPLE_PATH.exists() else {}

    with open(index_path, "r", encoding="utf-8") as f:
        original = f.read()

    new_ep_block = render_episodes_block(latest, total, cached)
    new_marquee = render_marquee_items(eps[:12])
    new_epcount = str(total)
    new_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cur_ep_block = _norm(extract_region(original, EPISODES_START, EPISODES_END)) if EPISODES_START in original else None
    cur_marquee  = _norm(extract_inline(original, MARQUEE_OPEN, MARQUEE_CLOSE)) if MARQUEE_OPEN in original else None
    cur_epcount  = _norm(extract_inline(original, EPCOUNT_OPEN, EPCOUNT_CLOSE)) if EPCOUNT_OPEN in original else None

    content_changed = (
        (cur_ep_block is not None and _norm(new_ep_block) != cur_ep_block) or
        (cur_marquee  is not None and _norm(new_marquee)  != cur_marquee) or
        (cur_epcount  is not None and _norm(new_epcount)  != cur_epcount)
    )

    if not content_changed:
        print(f"no change ({total} episodes; content unchanged since last refresh)")
        return 0

    new_text = replace_region(original, EPISODES_START, EPISODES_END, new_ep_block)
    new_text = replace_inline(new_text, LASTREFRESH_OPEN, LASTREFRESH_CLOSE, new_ts)
    new_text = replace_inline(new_text, EPCOUNT_OPEN, EPCOUNT_CLOSE, new_epcount)
    new_text = replace_inline(new_text, MARQUEE_OPEN, MARQUEE_CLOSE, new_marquee)

    if new_text == original:
        print(f"no change ({total} episodes; content unchanged since last refresh)")
        return 0

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print(f"updated: {total} episodes, {len(latest)} shown, refresh={new_ts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
