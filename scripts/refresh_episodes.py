#!/usr/bin/env python3
"""
Refresh the auto-managed episode list on the BBB marketing page.

What this does
--------------
1. Fetches the live Anchor.fm RSS feed for the show.
2. Parses the latest N episodes (title, pubDate, duration, link).
3. Renders an HTML block (ordered list + an "ep-count / archive" footer).
4. Updates four marker regions inside `index.src.html`:
   - <!-- AUTO-EPISODES-START --> ... <!-- AUTO-EPISODES-END -->
       → ordered list of latest N episodes
   - <!-- AUTO-MARQUEE -->...<!-- /AUTO-MARQUEE -->
       → " · "-joined latest titles for the scrolling marquee
   - <!-- AUTO-LASTREFRESH -->...<!-- /AUTO-LASTREFRESH -->
       → current ISO 8601 UTC timestamp
   - <!-- AUTO-EPCOUNT -->N<!-- /AUTO-EPCOUNT -->
       → integer episode count from the feed

`index.src.html` is the source of truth; `index.html` is generated from
it by `scripts/minify.py` (which preserves the markers). Always run this
script against the source file, then re-run minify.py.

Designed to be called by a daily GitHub Actions cron (see
.github/workflows/refresh-episodes.yml). Idempotent: if the rendered
output equals what's already in the file, it exits 0 without rewriting.

Usage
-----
    python3 scripts/refresh_episodes.py [INDEX_SRC_PATH]

Defaults to `index.src.html` in the repo root when run from CI.
"""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

RSS_URL = "https://anchor.fm/s/4431c4ac/podcast/rss"
ITUNES_LOOKUP_URL = (
    "https://itunes.apple.com/lookup"
    "?id=1663479533&entity=podcastEpisode&limit=200"
)
N_EPISODES = 8  # how many to render in the on-page list

REPO_ROOT = Path(__file__).resolve().parent.parent
APPLE_CACHE_PATH = REPO_ROOT / "data" / "apple_episode_ids.json"

EPISODES_START = "<!-- AUTO-EPISODES-START -->"
EPISODES_END = "<!-- AUTO-EPISODES-END -->"
LASTREFRESH_OPEN = "<!-- AUTO-LASTREFRESH -->"
LASTREFRESH_CLOSE = "<!-- /AUTO-LASTREFRESH -->"
EPCOUNT_OPEN = "<!-- AUTO-EPCOUNT -->"
EPCOUNT_CLOSE = "<!-- /AUTO-EPCOUNT -->"
MARQUEE_OPEN = "<!-- AUTO-MARQUEE -->"
MARQUEE_CLOSE = "<!-- /AUTO-MARQUEE -->"


def fetch_rss(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "bbb-marketing/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def fetch_apple_episode_ids() -> dict[str, dict]:
    """Fetch per-episode Apple Podcasts IDs from the iTunes Lookup API.

    Returns {guid: {"apple_id": int, "slug": str}} for each episode
    we can map. Gracefully returns an empty dict if the API is
    unreachable or returns an error — the caller is expected to
    fall back to the on-disk cache in that case.
    """
    try:
        req = urllib.request.Request(
            ITUNES_LOOKUP_URL,
            headers={"User-Agent": "bbb-marketing/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            payload = json.loads(r.read())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        print(f"warn: iTunes lookup failed: {exc}", file=sys.stderr)
        return {}

    if payload.get("resultCount", 0) == 0:
        return {}

    out: dict[str, dict] = {}
    for ep in payload.get("results", []):
        if ep.get("wrapperType") != "podcastEpisode":
            continue
        guid = ep.get("episodeGuid")
        track_id = ep.get("trackId")
        view_url = ep.get("trackViewUrl", "")
        if not guid or not track_id:
            continue
        # Apple Podcasts URL shape:
        #   https://podcasts.apple.com/us/podcast/<slug>/id<show-id>?i=<trackId>
        m = re.search(r"/podcast/([^/]+)/id\d+\?i=\d+", view_url)
        slug = m.group(1) if m else None
        out[guid] = {"apple_id": int(track_id), "slug": slug}
    return out


def load_apple_cache() -> dict[str, dict]:
    """Load the persisted Apple Podcasts mapping from disk."""
    if not APPLE_CACHE_PATH.exists():
        return {}
    try:
        with open(APPLE_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        print(f"warn: apple cache unreadable, ignoring: {exc}", file=sys.stderr)
        return {}


def save_apple_cache(mapping: dict[str, dict]) -> None:
    """Persist the Apple Podcasts mapping to disk."""
    APPLE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(APPLE_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, sort_keys=True)


def anchor_url_from_spotify(spotify_url: str) -> str | None:
    """Derive an Anchor.fm per-episode URL from a Spotify for Creators URL.

    Spotify for Creators episode URLs have the shape
        https://podcasters.spotify.com/pod/show/<host>/episodes/<Slug>-e<id>
    Anchor.fm episode URLs have the shape
        https://anchor.fm/<host>/episodes/<Slug>-e<id>
    We swap the host portion.
    """
    m = re.match(
        r"^https?://podcasters\.spotify\.com/pod/show/([^/]+)/episodes/(.+)$",
        spotify_url,
    )
    if not m:
        return None
    host, slug_id = m.group(1), m.group(2)
    return f"https://anchor.fm/{host}/episodes/{slug_id}"


def parse_episodes(xml_bytes: bytes) -> list[dict]:
    # Anchor publishes the iTunes namespace as http (not https). Use http
    # here so the ElementTree find matches; we also fall back to a
    # local-name scan in case the upstream changes the URI again.
    ns_http = "http://www.itunes.com/dtds/podcast-1.0.dtd"
    ns_map = {"itunes": ns_http}
    root = ET.fromstring(xml_bytes)
    items = root.findall("./channel/item")
    out: list[dict] = []
    for item in items:
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        dur_el = item.find("itunes:duration", ns_map)
        guid_el = item.find("guid")
        if dur_el is None:
            # Fallback: walk children and match by local name.
            for child in item:
                if child.tag.endswith("}duration") or child.tag == "duration":
                    dur_el = child
                    break
        title = (title_el.text or "").strip() if title_el is not None else "(untitled)"
        link = (link_el.text or "").strip() if link_el is not None else ""
        pub = (pub_el.text or "").strip() if pub_el is not None else ""
        dur = (dur_el.text or "").strip() if dur_el is not None else ""
        guid = (guid_el.text or "").strip() if guid_el is not None else ""
        if not title or not link:
            continue
        out.append({
            "title": title,
            "link": link,
            "pub": pub,
            "duration": dur,
            "guid": guid,
        })
    return out


def fmt_date(pub: str) -> str:
    if not pub:
        return "—"
    try:
        dt = parsedate_to_datetime(pub).astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return pub[:10] or "—"


def fmt_duration(dur: str) -> str:
    # Anchor emits either "HH:MM:SS" or "MM:SS". Normalise to "Hh MMm" or "MM:SS".
    if not dur:
        return "—"
    parts = dur.split(":")
    try:
        if len(parts) == 3:
            h, m, _ = (int(p) for p in parts)
            return f"{h}h {m:02d}m"
        if len(parts) == 2:
            m, s = (int(p) for p in parts)
            return f"{m}:{s:02d}"
    except ValueError:
        pass
    return dur


def render_episodes_block(eps: list[dict], total: int, apple_map: dict[str, dict]) -> str:
    rows = []
    for i, ep in enumerate(eps, start=1):
        apple = apple_map.get(ep.get("guid") or "")
        spotify_url = ep["link"]
        anchor_url = anchor_url_from_spotify(spotify_url)

        # Build the platforms <ul>. Apple is conditional on having the ID.
        platforms = []
        if apple and apple.get("apple_id") and apple.get("slug"):
            apple_url = (
                f"https://podcasts.apple.com/us/podcast/"
                f"{apple['slug']}/id1663479533"
                f"?i={apple['apple_id']}&uo=4"
            )
            platforms.append(
                f'        <li><a href="{html.escape(apple_url)}" '
                f'aria-label="Listen on Apple Podcasts" rel="noopener">'
                f'<span aria-hidden="true">&#9635;</span>'
                f'<span class="sr-only">Apple Podcasts</span></a></li>'
            )
        if spotify_url:
            platforms.append(
                f'        <li><a href="{html.escape(spotify_url)}" '
                f'aria-label="Listen on Spotify" rel="noopener">'
                f'<span aria-hidden="true">&#9673;</span>'
                f'<span class="sr-only">Spotify</span></a></li>'
            )
        if anchor_url:
            platforms.append(
                f'        <li><a href="{html.escape(anchor_url)}" '
                f'aria-label="Listen on Anchor" rel="noopener">'
                f'<span aria-hidden="true">&#9680;</span>'
                f'<span class="sr-only">Anchor</span></a></li>'
            )
        platforms_html = (
            f'\n              <ul class="ep-platforms" aria-label="Listen on">'
            + "\n" + "\n".join(platforms) + "\n              </ul>"
            if platforms else ""
        )

        rows.append(
            f'          <li class="episode">\n'
            f'            <span class="ep-no">№&nbsp;{total - i + 1:03d}</span>\n'
            f'            <div class="ep-body">\n'
            f'              <h3 class="ep-title">{html.escape(ep["title"])}</h3>\n'
            f'              <p class="ep-meta">{html.escape(fmt_date(ep["pub"]))} · {html.escape(fmt_duration(ep["duration"]))}</p>\n'
            f'{platforms_html}\n'
            f'            </div>\n'
            f'          </li>'
        )
    items = "\n".join(rows)
    block = (
        f'        <ol class="episode-list" role="list">\n'
        f'{items}\n'
        f'        </ol>\n\n'
        f'        <p class="ep-more">\n'
        f'          {total} episodes and counting. <a href="https://anchor.fm/s/4431c4ac/podcast/rss">Subscribe via RSS</a> for the full archive, or browse the <a href="https://podcasters.spotify.com/pod/show/jedidiah-jackson">Spotify archive</a>.\n'
        f'        </p>'
    )
    return block


def render_marquee_items(eps: list[dict]) -> str:
    # Doubled so the CSS marquee loops seamlessly.
    titles = [html.escape(ep["title"]) for ep in eps]
    doubled = titles + titles
    return " · ".join(doubled)


def replace_region(text: str, start: str, end: str, new_content: str) -> str:
    # Build a regex that matches from `start` to `end` (inclusive) on its own line(s).
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end),
        re.DOTALL,
    )
    return pattern.sub(f"{start}\n{new_content}\n{end}", text, count=1)


def replace_inline(text: str, open_marker: str, close_marker: str, new_content: str) -> str:
    pattern = re.compile(
        re.escape(open_marker) + r".*?" + re.escape(close_marker),
        re.DOTALL,
    )
    return pattern.sub(f"{open_marker}{new_content}{close_marker}", text, count=1)


def extract_region(text: str, start: str, end: str) -> str | None:
    """Return the inner content between start/end markers, or None if absent."""
    pattern = re.compile(
        re.escape(start) + r"(.*?)" + re.escape(end),
        re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1) if m else None


def extract_inline(text: str, open_marker: str, close_marker: str) -> str | None:
    """Return the inner content between inline open/close markers, or None."""
    pattern = re.compile(
        re.escape(open_marker) + r"(.*?)" + re.escape(close_marker),
        re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1) if m else None


def _norm(s: str | None) -> str:
    """Strip + collapse whitespace for a stable content comparison."""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def current_head_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return None


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

    # Read current content from each region (whitespace-normalised for
    # a stable comparison that ignores incidental formatting drift).
    cur_ep_block = _norm(extract_region(original, EPISODES_START, EPISODES_END))
    cur_marquee  = _norm(extract_inline(original, MARQUEE_OPEN, MARQUEE_CLOSE))
    cur_epcount  = _norm(extract_inline(original, EPCOUNT_OPEN, EPCOUNT_CLOSE))

    content_changed = (
        _norm(new_ep_block) != cur_ep_block or
        _norm(new_marquee)  != cur_marquee or
        _norm(new_epcount)  != cur_epcount
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
