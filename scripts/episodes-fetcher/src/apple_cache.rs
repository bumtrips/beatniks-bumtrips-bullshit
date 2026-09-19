// apple_cache.rs — read/write data/apple_episode_ids.json.
//
// The on-disk cache is a JSON object keyed by episodeGuid:
//   { "<guid>": { "apple_id": <int>, "slug": <string|null> }, ... }
// Sort-keyed + 2-space indented for stable diffs (matches Python).
//
// We delegate all JSON encode/decode to crate::json (no serde).

use crate::itunes::AppleEntry;
use crate::json::{self, Value};
use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::Path;

pub type Cache = BTreeMap<String, AppleEntry>;

pub fn load(path: &Path) -> Cache {
    let bytes = match std::fs::read(path) {
        Ok(b) => b,
        Err(_) => return Cache::new(),
    };
    let text = match std::str::from_utf8(&bytes) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("warn: apple cache not utf-8: {e}");
            return Cache::new();
        }
    };
    let val = match json::parse(text) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("warn: apple cache unreadable, ignoring: {e}");
            return Cache::new();
        }
    };
    from_value(&val)
}

pub fn save(path: &Path, cache: &Cache) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("create_dir_all failed: {e}"))?;
    }
    let val = to_value(cache);
    // Match Python's json.dump(..., indent=2, sort_keys=True). Our Value's
    // Display already sorts by virtue of BTreeMap, so 2-space indent
    // means "newline + two spaces after every '{', '[', ',', and ':'".
    // Hand-rolled formatter below is short and keeps us under 256 lines.
    let mut out = String::new();
    pretty(&val, 0, &mut out);
    out.push('\n');
    std::fs::write(path, out).map_err(|e| format!("write failed: {e}"))
}

fn from_value(v: &Value) -> Cache {
    let mut out = Cache::new();
    let obj = match v {
        Value::Obj(o) => o,
        _ => return out,
    };
    for (k, inner) in obj {
        let m = match inner {
            Value::Obj(m) => m,
            _ => continue,
        };
        let apple_id = match m.get("apple_id") {
            Some(Value::Int(n)) => *n,
            _ => continue,
        };
        let slug = match m.get("slug") {
            Some(Value::Str(s)) => Some(s.clone()),
            _ => None,
        };
        out.insert(k.clone(), AppleEntry { apple_id, slug });
    }
    out
}

fn to_value(cache: &Cache) -> Value {
    let mut obj = BTreeMap::new();
    for (k, v) in cache {
        let mut inner = BTreeMap::new();
        inner.insert("apple_id".to_string(), Value::Int(v.apple_id));
        match &v.slug {
            Some(s) => {
                inner.insert("slug".to_string(), Value::Str(s.clone()));
            }
            None => {
                inner.insert("slug".to_string(), Value::Null);
            }
        }
        obj.insert(k.clone(), Value::Obj(inner));
    }
    Value::Obj(obj)
}

fn pretty(v: &Value, depth: usize, out: &mut String) {
    let pad = "  ".repeat(depth);
    let pad1 = "  ".repeat(depth + 1);
    match v {
        Value::Obj(o) => {
            if o.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push_str("{\n");
            for (i, (k, vv)) in o.iter().enumerate() {
                if i > 0 {
                    out.push_str(",\n");
                }
                out.push_str(&pad1);
                crate::json::value::quote_into(k, out);
                out.push_str(": ");
                pretty(vv, depth + 1, out);
            }
            out.push('\n');
            out.push_str(&pad);
            out.push('}');
        }
        Value::Arr(a) => {
            if a.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push_str("[\n");
            for (i, vv) in a.iter().enumerate() {
                if i > 0 {
                    out.push_str(",\n");
                }
                out.push_str(&pad1);
                pretty(vv, depth + 1, out);
            }
            out.push('\n');
            out.push_str(&pad);
            out.push(']');
        }
        _ => {
            let _ = write!(out, "{v}");
        }
    }
}

