#!/usr/bin/env python3
"""
Refresh the auto-managed episode list on the BBB marketing page.

What this does
--------------
1. Fetches the live Anchor.fm RSS feed for the show.
2. Parses the latest N episodes (title, pubDate, duration, link).
3. Renders an HTML block (ordered list + an "ep-count / archive" footer).
4. Updates whichever marker regions exist inside `index.src.html`:
   - <!-- AUTO-EPISODES-START --> ... <!-- AUTO-EPISODES-END -->
       → ordered list of latest N episodes
   - <!-- AUTO-MARQUEE -->...<!-- /AUTO-MARQUEE -->
       → " · "-joined latest titles for the scrolling marquee
   - <!-- AUTO-LASTREFRESH -->...<!-- /AUTO-LASTREFRESH -->
       → current ISO 8601 UTC timestamp
   - <!-- AUTO-EPCOUNT -->N<!-- /AUTO-EPCOUNT -->
       → integer episode count from the feed

   Regions whose markers are absent from the file are skipped — they may
   have been removed deliberately from the page (e.g. the old footer
   ticker's AUTO-EPCOUNT / AUTO-LASTREFRESH spans).

`index.src.html` is the source of truth; `index.html` is generated from
it by `scripts/minify.py` (which preserves the markers). Always run this
script against the source file, then re-run minify.py.

Designed to be called by a daily GitHub Actions cron (see
.github/workflows/refresh-episodes.yml). Idempotent: if the rendered
output equals what's already in the file, it exits 0 without rewriting.

Implementation lives in the episodes package (scripts/episodes/) —
this file is just the driver.

Usage
-----
    python3 scripts/refresh_episodes.py [INDEX_SRC_PATH]

Defaults to `index.src.html` in the repo root when run from CI.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

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
    RSS_URL,
)
from episodes.feed import (
    fetch_apple_episode_ids,
    fetch_rss,
    load_apple_cache,
    parse_episodes,
    save_apple_cache,
)
from episodes.regions import (
    _norm,
    extract_inline,
    extract_region,
    replace_inline,
    replace_region,
)
from episodes.render import render_episodes_block, render_marquee_items


def main() -> int:
    index_path = sys.argv[1] if len(sys.argv) > 1 else "index.src.html"
    if not os.path.exists(index_path):
        print(f"error: {index_path} not found", file=sys.stderr)
        return 2

    with open(index_path, "r", encoding="utf-8") as f:
        original = f.read()

    xml = fetch_rss(RSS_URL)
    eps = parse_episodes(xml)
    if not eps:
        print("error: feed parsed but no episodes found", file=sys.stderr)
        return 3

    # Latest N episodes (newest first).
    latest = eps[:N_EPISODES]
    total = len(eps)

    # Apple Podcasts per-episode IDs: load persisted cache, merge with
    # any fresh data from the iTunes Lookup API, write back if merged.
    cached = load_apple_cache()
    fresh = fetch_apple_episode_ids()
    if fresh:
        merged = {**cached, **fresh}  # fresh wins
        if merged != cached:
            save_apple_cache(merged)
            cached = merged
        print(f"apple: {len(merged)} total ({len(fresh)} fresh)")
    else:
        print(f"apple: {len(cached)} from cache (API unreachable or empty)")

    # Compute new content for each auto-managed region.
    new_ep_block = render_episodes_block(latest, total, cached)
    new_marquee = render_marquee_items(eps[:12])
    new_epcount = str(total)
    new_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Read current content from each region that exists in the file
    # (whitespace-normalised for a stable comparison that ignores
    # incidental formatting drift). Absent markers → region skipped.
    cur_ep_block = _norm(extract_region(original, EPISODES_START, EPISODES_END)) if EPISODES_START in original else None
    cur_marquee  = _norm(extract_inline(original, MARQUEE_OPEN, MARQUEE_CLOSE)) if MARQUEE_OPEN in original else None
    cur_epcount  = _norm(extract_inline(original, EPCOUNT_OPEN, EPCOUNT_CLOSE)) if EPCOUNT_OPEN in original else None

    content_changed = (
        (cur_ep_block is not None and _norm(new_ep_block) != cur_ep_block) or
        (cur_marquee  is not None and _norm(new_marquee)  != cur_marquee) or
        (cur_epcount  is not None and _norm(new_epcount)  != cur_epcount)
    )

    # If nothing actually changed, leave the file alone — including the
    # timestamp. The CI workflow will see no diff and skip the commit.
    if not content_changed:
        print(f"no change ({total} episodes; content unchanged since last refresh)")
        return 0

    # Otherwise, write all four regions.
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
