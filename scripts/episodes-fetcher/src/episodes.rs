// episodes.rs — top-level orchestration.
//
// 1. Fetch the live RSS feed.
// 2. Parse out episode records.
// 3. Hit iTunes Lookup API; merge results into the on-disk Apple cache.
// 4. Write data/parsed_episodes.json (consumed by the Python driver).
// 5. Write a one-line summary to stdout for the caller to log.
//
// Stdlib only. URLs, paths, and the show id are constants; if they
// need to change, edit them here rather than threading them through.

use crate::apple_cache::{self, Cache};
use crate::http;
use crate::itunes::{self, AppleEntry};
use crate::json::Value;
use crate::rss::{self, Episode};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

pub const RSS_URL: &str = "https://anchor.fm/s/4431c4ac/podcast/rss";
pub const USER_AGENT: &str = "bbb-marketing/1.0";

#[derive(Debug)]
pub struct FetchOutcome {
    pub episodes: Vec<Episode>,
    pub apple_fresh: usize,
    pub apple_total: usize,
}

pub fn fetch_all(repo_root: &Path) -> Result<FetchOutcome, String> {
    let body = http::get(RSS_URL, 20, USER_AGENT)
        .map_err(|e| format!("rss fetch failed: {e}"))?;
    let xml = std::str::from_utf8(&body)
        .map_err(|e| format!("rss not utf-8: {e}"))?;
    let episodes = rss::parse(xml);
    if episodes.is_empty() {
        return Err("feed parsed but no episodes found".into());
    }

    let cache_path = repo_root.join("data/apple_episode_ids.json");
    let mut cache = apple_cache::load(&cache_path);
    let fresh: Cache = itunes::fetch();
    let apple_fresh = fresh.len();
    let merged = merge_caches(&cache, &fresh);
    if merged != cache {
        apple_cache::save(&cache_path, &merged)
            .map_err(|e| format!("apple cache save failed: {e}"))?;
        cache = merged;
    }
    let apple_total = cache.len();

    let out_path = repo_root.join("data/parsed_episodes.json");
    write_episodes_json(&out_path, &episodes)?;

    Ok(FetchOutcome {
        episodes,
        apple_fresh,
        apple_total,
    })
}

// Fresh entries win; existing entries are kept otherwise.
fn merge_caches(prev: &Cache, fresh: &Cache) -> Cache {
    let mut out: Cache = prev.clone();
    for (k, v) in fresh {
        out.insert(k.clone(), v.clone());
    }
    out
}

fn write_episodes_json(path: &PathBuf, episodes: &[Episode]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("create_dir_all failed: {e}"))?;
    }
    let mut arr = Vec::with_capacity(episodes.len());
    for ep in episodes {
        let mut obj = BTreeMap::new();
        obj.insert("title".to_string(), Value::Str(ep.title.clone()));
        obj.insert("link".to_string(), Value::Str(ep.link.clone()));
        obj.insert("pub".to_string(), Value::Str(ep.pub_date.clone()));
        obj.insert("duration".to_string(), Value::Str(ep.duration.clone()));
        obj.insert("guid".to_string(), Value::Str(ep.guid.clone()));
        arr.push(Value::Obj(obj));
    }
    let mut root = BTreeMap::new();
    root.insert("episodes".to_string(), Value::Arr(arr));
    root.insert(
        "total".to_string(),
        Value::Int(episodes.len() as i64),
    );
    let val = Value::Obj(root);
    std::fs::write(path, format!("{val}")).map_err(|e| format!("write failed: {e}"))
}

// Suppress unused-import warning when apple_cache::AppleEntry alias is
// only referenced indirectly via Cache.
#[allow(dead_code)]
fn _typecheck(_: AppleEntry) {}
