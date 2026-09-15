"""render.py — HTML block + marquee string rendering for episodes."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


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
        f'          {total} episodes and counting. <a href="https://anchor.fm/s/4431c4ac/podcast/rss">Subscribe via RSS</a> for the full archive, or browse the <a href="https://open.spotify.com/show/43GiaQy9E5rkp6LfzXrvAM">Spotify archive</a>.\n'
        f'        </p>'
    )
    return block


def render_marquee_items(eps: list[dict]) -> str:
    # Doubled so the CSS marquee loops seamlessly.
    titles = [html.escape(ep["title"]) for ep in eps]
    doubled = titles + titles
    return " · ".join(doubled)
