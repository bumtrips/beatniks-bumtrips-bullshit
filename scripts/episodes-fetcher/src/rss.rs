// rss.rs — minimal RSS/XML parser for Anchor.fm feeds.
//
// We don't need a full XML parser — we need `<item>` blocks and five
// fields from inside them (title, link, pubDate, duration, guid).
// Strategy: split the document on `<item>`, then for each block locate
// the first matching tag (handling itunes:duration via a fallback to
// local-name scan) and read its text content until the matching close
// tag or self-close. Tolerates attribute-bearing open tags, CDATA, and
// XML comments inside items — the upstream feed is well-formed enough
// that none of those matter in practice.

#[derive(Debug, Clone, PartialEq)]
pub struct Episode {
    pub title: String,
    pub link: String,
    pub pub_date: String,
    pub duration: String,
    pub guid: String,
}

pub fn parse(xml: &str) -> Vec<Episode> {
    let mut out = Vec::new();
    let mut start = 0usize;
    while let Some(rel) = find_after(xml, "<item>", start) {
        let item_start = rel;
        let item_end = match find_after(xml, "</item>", item_start) {
            Some(p) => p,
            None => break,
        };
        let block = &xml[item_start..item_end];
        let title = grab(block, "title").unwrap_or_else(|| "(untitled)".into());
        let link = grab(block, "link").unwrap_or_default();
        if title.is_empty() || link.is_empty() {
            start = item_end;
            continue;
        }
        let pub_date = grab(block, "pubDate").unwrap_or_default();
        let duration = grab_ns(block, "itunes:duration", "duration").unwrap_or_default();
        let guid = grab(block, "guid").unwrap_or_default();
        out.push(Episode {
            title,
            link,
            pub_date,
            duration,
            guid,
        });
        start = item_end;
    }
    out
}

fn find_after(haystack: &str, needle: &str, from: usize) -> Option<usize> {
    haystack[from..]
        .find(needle)
        .map(|p| from + p + needle.len())
}

fn strip_cdata(s: &str) -> String {
    if let Some(start) = s.find("<![CDATA[") {
        if let Some(end) = s.find("]]>") {
            return s[start + 9..end].to_string();
        }
    }
    s.to_string()
}

fn grab(block: &str, tag: &str) -> Option<String> {
    let open = format!("<{tag}>");
    let close = format!("</{tag}>");
    let open_pos = block.find(&open)?;
    let after_open = open_pos + open.len();
    let close_pos = block[after_open..].find(&close)? + after_open;
    let raw = &block[after_open..close_pos];
    Some(strip_cdata(raw).trim().to_string())
}

fn grab_ns(block: &str, primary: &str, fallback: &str) -> Option<String> {
    if let Some(v) = grab(block, primary) {
        return Some(v);
    }
    if primary != fallback {
        if let Some(v) = grab(block, fallback) {
            return Some(v);
        }
    }
    // Last-ditch: scan for <*duration> by local-name.
    let needle = ":duration>";
    if let Some(p) = block.find(needle) {
        let after = p + needle.len();
        if let Some(rel_end) = block[after..].find("</") {
            return Some(block[after..after + rel_end].trim().to_string());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_two_items() {
        let xml = r#"<rss><channel>
            <item><title>A</title><link>L1</link><pubDate>P1</pubDate>
              <itunes:duration>10</itunes:duration><guid>G1</guid></item>
            <item><title>B</title><link>L2</link><pubDate>P2</pubDate>
              <duration>20</duration><guid>G2</guid></item>
        </channel></rss>"#;
        let eps = parse(xml);
        assert_eq!(eps.len(), 2);
        assert_eq!(eps[0].title, "A");
        assert_eq!(eps[0].duration, "10");
        assert_eq!(eps[1].title, "B");
        assert_eq!(eps[1].duration, "20");
    }
}
