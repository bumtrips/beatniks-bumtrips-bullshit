// main.rs — CLI entrypoint for the episodes-fetcher binary.
//
// Usage:
//   episodes-fetcher [<repo-root>]
//
// Defaults to the current working directory if no path is given. On
// success prints a one-line summary to stdout and exits 0; on any
// failure prints to stderr and exits non-zero.

mod apple_cache;
mod episodes;
mod http;
mod itunes;
mod json;
mod rss;

use std::path::PathBuf;
use std::process::ExitCode;

fn main() -> ExitCode {
    let repo_root = match arg_repo_root() {
        Ok(p) => p,
        Err(e) => {
            eprintln!("error: {e}");
            return ExitCode::from(2);
        }
    };
    match episodes::fetch_all(&repo_root) {
        Ok(out) => {
            println!(
                "fetched {} episodes; apple cache: {} total ({} fresh)",
                out.episodes.len(),
                out.apple_total,
                out.apple_fresh
            );
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::from(3)
        }
    }
}

fn arg_repo_root() -> Result<PathBuf, String> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() > 2 {
        return Err(format!("usage: {} [<repo-root>]", args[0]));
    }
    if args.len() == 2 {
        Ok(PathBuf::from(&args[1]))
    } else {
        Ok(std::env::current_dir()
            .map_err(|e| format!("current_dir failed: {e}"))?)
    }
}
