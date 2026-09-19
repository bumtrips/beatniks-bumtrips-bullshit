// itunes.rs — Apple Podcasts iTunes Lookup API fetcher.
//
// Returns a map { episodeGuid -> { apple_id, slug } } for every entry
// the API returns with wrapperType == "podcastEpisode". Slug is
// extracted from the trackViewUrl by regex (Apple Podcasts URL shape:
//   https://podcasts.apple.com/us/podcast/<slug>/id<show-id>?i=<trackId>).
//
// On network or parse failure we log to stderr and return an empty map
// — callers are expected to fall back to the on-disk cache in that
// case.

use crate::http;
use crate::json::{self, Value};
use std::collections::BTreeMap;

pub const URL: &str = "https://itunes.apple.com/lookup?id=1663479533&entity=podcastEpisode&limit=200";
pub const USER_AGENT: &str = "bbb-marketing/1.0";

#[derive(Debug, Clone, PartialEq)]
pub struct AppleEntry {
    pub apple_id: i64,
    pub slug: Option<String>,
}

pub fn fetch() -> BTreeMap<String, AppleEntry> {
    let body = match http::get(URL, 20, USER_AGENT) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("warn: iTunes lookup failed: {e}");
            return BTreeMap::new();
        }
    };
    let text = match std::str::from_utf8(&body) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("warn: iTunes lookup not utf-8: {e}");
            return BTreeMap::new();
        }
    };
    let val = match json::parse(text) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("warn: iTunes lookup json parse failed: {e}");
            return BTreeMap::new();
        }
    };
    parse_value(&val)
}

fn parse_value(val: &Value) -> BTreeMap<String, AppleEntry> {
    let mut out = BTreeMap::new();
    let obj = match val {
        Value::Obj(o) => o,
        _ => return out,
    };
    let results = match obj.get("results") {
        Some(Value::Arr(a)) => a,
        _ => return out,
    };
    for ep in results {
        let m = match ep {
            Value::Obj(o) => o,
            _ => continue,
        };
        let wrapper = str_field(m, "wrapperType");
        if wrapper.as_deref() != Some("podcastEpisode") {
            continue;
        }
        let guid = match str_field(m, "episodeGuid") {
            Some(g) if !g.is_empty() => g,
            _ => continue,
        };
        let track_id = match int_field(m, "trackId") {
            Some(n) => n,
            None => continue,
        };
        let view_url = str_field(m, "trackViewUrl").unwrap_or_default();
        let slug = extract_slug(&view_url);
        out.insert(
            guid,
            AppleEntry {
                apple_id: track_id,
                slug,
            },
        );
    }
    out
}

fn str_field(m: &std::collections::BTreeMap<String, Value>, k: &str) -> Option<String> {
    match m.get(k) {
        Some(Value::Str(s)) => Some(s.clone()),
        _ => None,
    }
}

fn int_field(m: &std::collections::BTreeMap<String, Value>, k: &str) -> Option<i64> {
    match m.get(k) {
        Some(Value::Int(n)) => Some(*n),
        _ => None,
    }
}

fn extract_slug(url: &str) -> Option<String> {
    // Match /podcast/<slug>/id<digits>?i=<digits>
    let needle = "/podcast/";
    let p = url.find(needle)? + needle.len();
    let rest = &url[p..];
    let end = rest.find("/id")?;
    if end == 0 {
        return None;
    }
    Some(rest[..end].to_string())
}
