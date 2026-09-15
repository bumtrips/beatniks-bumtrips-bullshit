"""regions.py — AUTO-* marker replace/extract helpers."""

from __future__ import annotations

import re
import subprocess


def replace_region(text: str, start: str, end: str, new_content: str) -> str:
    # Build a regex that matches from `start` to `end` (inclusive) on its own line(s).
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end),
        re.DOTALL,
    )
    # Lambda replacement: new_content may contain backslashes (episode
    # titles are user-authored) which re.sub would misinterpret as escapes.
    return pattern.sub(lambda _: f"{start}\n{new_content}\n{end}", text, count=1)


def replace_inline(text: str, open_marker: str, close_marker: str, new_content: str) -> str:
    pattern = re.compile(
        re.escape(open_marker) + r".*?" + re.escape(close_marker),
        re.DOTALL,
    )
    return pattern.sub(lambda _: f"{open_marker}{new_content}{close_marker}", text, count=1)


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
