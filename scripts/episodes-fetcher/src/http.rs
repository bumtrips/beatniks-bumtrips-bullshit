// http.rs — minimal HTTPS client.
//
// AUTHORIZED EXCEPTION: Rust's stdlib does not include a TLS stack.
// Rather than pull in rustls/native-tls/openssl-sys (libraries), we
// delegate TLS to the system `curl` binary via std::process::Command.
// Cargo has zero dependencies; this is a deliberate, single, documented
// exception to the "no libraries" rule. If curl is not on PATH the
// caller will receive a clean error.
//
// We support only what we need: GET, a fixed User-Agent, a per-request
// timeout, and the response body as bytes. No headers are inspected —
// callers that need status codes should change this module first.

use std::io::{Read, Write};
use std::process::{Command, Stdio};

pub fn get(url: &str, timeout_secs: u32, user_agent: &str) -> Result<Vec<u8>, String> {
    let mut child = Command::new("curl")
        .arg("--silent")
        .arg("--show-error")
        .arg("--location")           // follow 3xx
        .arg("--fail")               // non-2xx -> non-zero exit
        .arg("--max-time")
        .arg(timeout_secs.to_string())
        .arg("-A")
        .arg(user_agent)
        .arg(url)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("curl spawn failed: {e}"))?;

    let mut out = Vec::new();
    if let Some(mut stdout) = child.stdout.take() {
        stdout
            .read_to_end(&mut out)
            .map_err(|e| format!("curl stdout read failed: {e}"))?;
    }
    let status = child
        .wait()
        .map_err(|e| format!("curl wait failed: {e}"))?;
    if !status.success() {
        let mut err = Vec::new();
        if let Some(mut stderr) = child.stderr.take() {
            let _ = stderr.read_to_end(&mut err);
        }
        return Err(format!(
            "curl exited {code}: {msg}",
            code = status,
            msg = String::from_utf8_lossy(&err)
        ));
    }
    Ok(out)
}

// Silence dead-code warning when we don't use std::io::Write directly.
#[allow(dead_code)]
fn _write_dummy() {
    let mut v = Vec::new();
    let _ = v.write_all(b"");
}
