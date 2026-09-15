"""episodes package — auto-managed episode list for the BBB page.

Split from scripts/refresh_episodes.py (256-line cap):
  feed.py    — RSS/iTunes fetch, Apple ID cache, episode parsing
  render.py  — HTML block + marquee string rendering
  regions.py — AUTO-* marker replace/extract helpers
"""

from pathlib import Path

RSS_URL = "https://anchor.fm/s/4431c4ac/podcast/rss"
ITUNES_LOOKUP_URL = (
    "https://itunes.apple.com/lookup"
    "?id=1663479533&entity=podcastEpisode&limit=200"
)
N_EPISODES = 8  # how many to render in the on-page list

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APPLE_CACHE_PATH = REPO_ROOT / "data" / "apple_episode_ids.json"

EPISODES_START = "<!-- AUTO-EPISODES-START -->"
EPISODES_END = "<!-- AUTO-EPISODES-END -->"
LASTREFRESH_OPEN = "<!-- AUTO-LASTREFRESH -->"
LASTREFRESH_CLOSE = "<!-- /AUTO-LASTREFRESH -->"
EPCOUNT_OPEN = "<!-- AUTO-EPCOUNT -->"
EPCOUNT_CLOSE = "<!-- /AUTO-EPCOUNT -->"
MARQUEE_OPEN = "<!-- AUTO-MARQUEE -->"
MARQUEE_CLOSE = "<!-- /AUTO-MARQUEE -->"
