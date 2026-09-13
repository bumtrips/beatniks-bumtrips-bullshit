#!/usr/bin/env python3
"""Minify styles.css -> styles.min.css and rewrite index.html to load it
and strip safe HTML comments. Conservative: preserves <script> and <style>
contents verbatim; never touches conditional IE comments; collapses
whitespace between tags only.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS_IN = ROOT / "styles.css"
CSS_OUT = ROOT / "styles.min.css"
HTML_IN = ROOT / "index.html"
HTML_OUT = ROOT / "index.html"  # in-place

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

# Keep comments that affect browser behavior or parsing.
KEEP_PATTERNS = [
    re.compile(r"<!--\[if[\s\S]*?\]!>-->", re.I),  # IE downlevel-revealed
    re.compile(r"<!--\[endif\]-->", re.I),           # IE downlevel-hidden end
    re.compile(r"<!---->", re.I),                    # placeholder
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
    # Collapse runs of whitespace between `>` and `<` (safe: not in text nodes).
    # But do NOT touch whitespace inside <pre>, <code>, <textarea>.
    # Walk linearly with a tag-aware filter.
    out = []
    i = 0
    n = len(html)
    pre_open = re.compile(r"<\s*(pre|code|textarea)[^>]*>", re.I)
    pre_close = re.compile(r"</\s*(pre|code|textarea)\s*>", re.I)
    in_pre = False
    while i < n:
        if not in_pre:
            m = pre_open.match(html, i)
            if m:
                in_pre = True
                out.append(html[i:m.end()])
                i = m.end()
                continue
        else:
            m = pre_close.match(html, i)
            if m:
                in_pre = False
                out.append(html[i:m.end()])
                i = m.end()
                continue
        if not in_pre:
            # Between `>` and `<`: collapse whitespace.
            if html[i] == ">":
                out.append(">")
                j = i + 1
                while j < n and html[j] in " \t\r\n":
                    j += 1
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
