//! Registro de eventos de compressão do proxy.
//!
//! Grava no MESMO arquivo e schema que o lado Python
//! (`~/.redux-token/events.jsonl`, ver `redux_token/telemetry.py`), para que
//! `redux-token gain`/`session`/`discover` agreguem proxy + lib + hook + mcp juntos.
//!
//! Princípios: local-first, opt-out via `REDUX_TOKEN_NO_STATS=1`, e nunca entra no
//! caminho de erro do proxy (falhas de I/O são ignoradas).

use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use std::sync::OnceLock;

use serde::Serialize;

static SESSION_ID: OnceLock<String> = OnceLock::new();

/// ID estável por processo do proxy. Agrupa todos os eventos desta execução.
pub fn session_id() -> &'static str {
    SESSION_ID.get_or_init(|| {
        let ts = chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ");
        format!("{ts}-{:04x}", std::process::id() & 0xffff)
    })
}

fn disabled() -> bool {
    std::env::var("REDUX_TOKEN_NO_STATS").as_deref() == Ok("1")
}

/// Diretório base do ReduxToken (`~/.redux-token` ou `REDUX_TOKEN_HOME`).
/// Compartilhado pelo event log e pelo store reversível.
pub fn home_dir() -> Option<PathBuf> {
    if let Ok(home) = std::env::var("REDUX_TOKEN_HOME") {
        return Some(PathBuf::from(home));
    }
    // HOME no Unix, USERPROFILE no Windows — evita depender do crate `dirs`.
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .ok()?;
    Some(PathBuf::from(home).join(".redux-token"))
}

fn log_path() -> Option<PathBuf> {
    Some(home_dir()?.join("events.jsonl"))
}

/// Heurística barata de tipo de conteúdo (espelha `telemetry.detect_content_type`).
fn detect_content_type(text: &str) -> &'static str {
    let sample: String = text.chars().take(4096).collect();
    let trimmed = sample.trim_start();
    if trimmed.starts_with('{') || trimmed.starts_with('[') {
        if serde_json::from_str::<serde_json::Value>(text).is_ok() {
            return "json";
        }
    }
    if sample.contains("[DEBUG]")
        || sample.contains("[TRACE]")
        || sample.contains("[INFO]")
        || sample.contains("[WARN]")
    {
        return "log";
    }
    for tok in ["//", "/*", "def ", "fn ", "function ", "class ", "import ", "#include"] {
        if sample.contains(tok) {
            return "code";
        }
    }
    "text"
}

#[derive(Serialize)]
struct Event<'a> {
    ts: String,
    source: &'a str,
    content_type: &'a str,
    original_tokens: u64,
    compressed_tokens: u64,
    tokens_saved: u64,
    savings_pct: f64,
    time_ms: f64,
    from_cache: bool,
    session_id: &'a str,
}

/// Anexa um evento de compressão do proxy ao event log. Nunca falha para o chamador.
pub fn record(
    text: &str,
    original_tokens: u64,
    compressed_tokens: u64,
    time_ms: f64,
    from_cache: bool,
) {
    if disabled() {
        return;
    }
    let Some(path) = log_path() else { return };

    let tokens_saved = original_tokens.saturating_sub(compressed_tokens);
    let savings_pct = if original_tokens > 0 {
        (tokens_saved as f64 / original_tokens as f64 * 100.0 * 100.0).round() / 100.0
    } else {
        0.0
    };

    let event = Event {
        ts: chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string(),
        source: "proxy",
        content_type: detect_content_type(text),
        original_tokens,
        compressed_tokens,
        tokens_saved,
        savings_pct,
        time_ms: (time_ms * 1000.0).round() / 1000.0,
        from_cache,
        session_id: session_id(),
    };

    let Ok(line) = serde_json::to_string(&event) else { return };

    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(&path) {
        let _ = writeln!(f, "{line}");
    }
}
