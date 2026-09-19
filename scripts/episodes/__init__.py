"""episodes package — auto-managed episode list for the BBB page.

Functional split (each under 256 lines):
  render.py  — HTML block + marquee string rendering
  regions.py — AUTO-* marker replace/extract helpers

Backend (RSS/iTunes fetch + Apple cache) lives in Rust at
scripts/episodes-fetcher/, invoked by scripts/refresh_episodes.py.
"""

# How many episodes to render in the on-page list.
N_EPISODES = 8

# AUTO-* region markers recognised inside index.src.html.
EPISODES_START = "<!-- AUTO-EPISODES-START -->"
EPISODES_END = "<!-- AUTO-EPISODES-END -->"
LASTREFRESH_OPEN = "<!-- AUTO-LASTREFRESH -->"
LASTREFRESH_CLOSE = "<!-- /AUTO-LASTREFRESH -->"
EPCOUNT_OPEN = "<!-- AUTO-EPCOUNT -->"
EPCOUNT_CLOSE = "<!-- /AUTO-EPCOUNT -->"
MARQUEE_OPEN = "<!-- AUTO-MARQUEE -->"
MARQUEE_CLOSE = "<!-- /AUTO-MARQUEE -->"
