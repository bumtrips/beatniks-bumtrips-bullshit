#!/usr/bin/env python3
"""Minify styles.css -> styles.min.css and index.src.html -> index.html
(strip safe HTML comments, collapse inter-tag whitespace, point the
stylesheet link at the minified CSS).

index.src.html is the source of truth — edit that file, never index.html.
AUTO-* marker comments are preserved in the output so
scripts/refresh_episodes.py can locate its managed regions in either file.

Conservative: preserves <script> and <style> contents verbatim; never
touches conditional IE comments; collapses whitespace between tags only.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS_IN = ROOT / "styles.css"
CSS_OUT = ROOT / "styles.min.css"
HTML_IN = ROOT / "index.src.html"
HTML_OUT = ROOT / "index.html"

def minify_css(src: str) -> str:
    # 1. Strip /* ... */ comments (no nested /*, CSS has no strings with /).
    out = re.sub(r"/\*[\s\S]*?\*/", "", src)
    # 2. Collapse runs of whitespace to one space.
    out = re.sub(r"\s+", " ", out)
    # 3. Trim around punctuation that doesn't need a space.
    out = re.sub(r"\s*([{};,:>])\s*", r"\1", out)
    # 4. Restore a single space after `;` and before `{` for readability
    #    and to avoid `font:14px/1.5{...}` parse errors.
    out = out.replace("{", " {").replace("}", "} ")
    # 5. Drop the leading space before `}` and trailing spaces.
    out = re.sub(r" *\{ *", "{", out)
    out = re.sub(r" *\} *", "}", out)
    out = re.sub(r";\}", "}", out)
    # 6. Final collapse of stray double spaces.
    out = re.sub(r" {2,}", " ", out)
    # 7. Trim trailing/leading.
    return out.strip()

# Keep comments that affect browser behavior or parsing, plus the
# AUTO-* region markers that refresh_episodes.py searches for.
KEEP_PATTERNS = [
    re.compile(r"<!--\[if[\s\S]*?\]!>-->", re.I),  # IE downlevel-revealed
    re.compile(r"<!--\[endif\]-->", re.I),           # IE downlevel-hidden end
    re.compile(r"<!---->", re.I),                    # placeholder
    re.compile(r"<!--\s*/?AUTO-[\w-]*\s*-->", re.I), # refresh_episodes markers
]

def strip_html_comments(html: str) -> tuple[str, int]:
    removed = 0
    out_chunks = []
    cursor = 0
    # Standard HTML comments <!-- ... --> (non-greedy, dotall).
    pat = re.compile(r"<!--(?!\[if)[\s\S]*?-->", re.I)
    for m in pat.finditer(html):
        chunk = html[cursor:m.start()]
        # If any keep-pattern overlaps this match, keep as-is.
        keep = False
        for kp in KEEP_PATTERNS:
            if kp.match(m.group(0)):
                keep = True
                break
        if keep:
            out_chunks.append(chunk + m.group(0))
        else:
            out_chunks.append(chunk)
            removed += 1
        cursor = m.end()
    out_chunks.append(html[cursor:])
    return "".join(out_chunks), removed

def collapse_tag_whitespace(html: str) -> str:
    # Collapse runs of whitespace between `>` and `<` only — whitespace
    # before a text node is significant (it renders as a space), so emit a
    # single space there instead of dropping it. Whitespace-sensitivity
    # applies inside <pre>, <code>, <textarea>, <script>, and <style>;
    # their contents pass through verbatim.
    out = []
    i = 0
    n = len(html)
    verbatim_open = re.compile(r"<\s*(pre|code|textarea|script|style)[^>]*>", re.I)
    verbatim_close = re.compile(r"</\s*(pre|code|textarea|script|style)\s*>", re.I)
    in_verbatim = False
    while i < n:
        if not in_verbatim:
            m = verbatim_open.match(html, i)
            if m:
                in_verbatim = True
                out.append(html[i:m.end()])
                i = m.end()
                continue
        else:
            m = verbatim_close.match(html, i)
            if m:
                in_verbatim = False
                out.append(html[i:m.end()])
                i = m.end()
                continue
        if not in_verbatim and html[i] == ">":
            out.append(">")
            j = i + 1
            while j < n and html[j] in " \t\r\n":
                j += 1
            if j < n and html[j] == "<":
                i = j  # whitespace between tags: drop it
            else:
                if j > i + 1:
                    out.append(" ")  # whitespace before text: keep one space
                i = j
            continue
        out.append(html[i])
        i += 1
    return "".join(out)

def main() -> int:
    css_src = CSS_IN.read_text(encoding="utf-8")
    css_min = minify_css(css_src)
    CSS_OUT.write_text(css_min, encoding="utf-8")
    print(f"css: {len(css_src)} -> {len(css_min)} bytes ({100*len(css_min)/len(css_src):.1f}%)")
    html_src = HTML_IN.read_text(encoding="utf-8")
    html_no_comments, n = strip_html_comments(html_src)
    print(f"html comments stripped: {n}")
    html_collapsed = collapse_tag_whitespace(html_no_comments)
    # Swap styles.css link to styles.min.css if present.
    html_collapsed = html_collapsed.replace(
        'href="styles.css"', 'href="styles.min.css"'
    )
    HTML_OUT.write_text(html_collapsed, encoding="utf-8")
    print(f"html: {len(html_src)} -> {len(html_collapsed)} bytes ({100*len(html_collapsed)/len(html_src):.1f}%)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
