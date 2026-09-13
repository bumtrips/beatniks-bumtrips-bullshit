#!/usr/bin/env python3
"""
Refresh the auto-managed episode list on the BBB marketing page.

What this does
--------------
1. Fetches the live Anchor.fm RSS feed for the show.
2. Parses the latest N episodes (title, pubDate, duration, link).
3. Renders an HTML block (ordered list + an "ep-count / archive" footer).
4. Updates three marker regions inside `index.html`:
   - <!-- AUTO-EPISODES-START --> ... <!-- AUTO-EPISODES-END -->
       → ordered list of latest N episodes
   - <!-- AUTO-LASTREFRESH -->...<!-- /AUTO-LASTREFRESH -->
       → current ISO 8601 UTC timestamp
   - <!-- AUTO-EPCOUNT -->N<!-- /AUTO-EPCOUNT -->
       → integer episode count from the feed

Designed to be called by a weekly GitHub Actions cron (see
.github/workflows/refresh-episodes.yml). Idempotent: if the rendered
output equals what's already in the file, it exits 0 without rewriting.

Usage
-----
    python3 scripts/refresh_episodes.py [INDEX_HTML_PATH]

Defaults to `index.html` in the repo root when run from CI.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

RSS_URL = "https://anchor.fm/s/4431c4ac/podcast/rss"
N_EPISODES = 8  # how many to render in the on-page list

EPISODES_START = "<!-- AUTO-EPISODES-START -->"
EPISODES_END = "<!-- AUTO-EPISODES-END -->"
LASTREFRESH_OPEN = "<!-- AUTO-LASTREFRESH -->"
LASTREFRESH_CLOSE = "<!-- /AUTO-LASTREFRESH -->"
EPCOUNT_OPEN = "<!-- AUTO-EPCOUNT -->"
EPCOUNT_CLOSE = "<!-- /AUTO-EPCOUNT -->"


def fetch_rss(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "bbb-marketing/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


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
        if not title or not link:
            continue
        out.append({
            "title": title,
            "link": link,
            "pub": pub,
            "duration": dur,
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


def render_episodes_block(eps: list[dict], total: int) -> str:
    rows = []
    for i, ep in enumerate(eps, start=1):
        rows.append(
            f'          <li class="episode">\n'
            f'            <span class="ep-no">№&nbsp;{total - i + 1:03d}</span>\n'
            f'            <div class="ep-body">\n'
            f'              <h3 class="ep-title">{html.escape(ep["title"])}</h3>\n'
            f'              <p class="ep-meta">{html.escape(fmt_date(ep["pub"]))} · {html.escape(fmt_duration(ep["duration"]))} · <a href="{html.escape(ep["link"])}" rel="noopener">listen</a></p>\n'
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


def current_head_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return None


def main() -> int:
    index_path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
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

    # 1. Episodes block.
    ep_block = render_episodes_block(latest, total)
    new_text = replace_region(original, EPISODES_START, EPISODES_END, ep_block)

    # 2. Last-refresh timestamp.
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_text = replace_inline(new_text, LASTREFRESH_OPEN, LASTREFRESH_CLOSE, ts)

    # 3. Episode count.
    new_text = replace_inline(new_text, EPCOUNT_OPEN, EPCOUNT_CLOSE, str(total))

    # 4. Marquee items (latest 12 for the scrolling strip).
    marquee_titles = render_marquee_items(eps[:12])
    MARQUEE_OPEN = "<!-- AUTO-MARQUEE -->"
    MARQUEE_CLOSE = "<!-- /AUTO-MARQUEE -->"
    new_text = replace_inline(new_text, MARQUEE_OPEN, MARQUEE_CLOSE, marquee_titles)

    if new_text == original:
        print(f"no change ({total} episodes; {ts})")
        return 0

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print(f"updated: {total} episodes, {len(latest)} shown, refresh={ts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
