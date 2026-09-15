"""feed.py — RSS/iTunes fetch, Apple ID cache, episode parsing."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from xml.etree import ElementTree as ET

from . import APPLE_CACHE_PATH, ITUNES_LOOKUP_URL


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
