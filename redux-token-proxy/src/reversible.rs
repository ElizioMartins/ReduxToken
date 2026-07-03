//! Store reversível do proxy — espelho Rust de `redux_token/reversible.py`.
//!
//! Grava os trechos removidos no MESMO diretório content-addressed
//! (`~/.redux-token/reversible/<ref>.txt`) para que a tool MCP `retrieve` os recupere.
//! O `ref` já vem calculado pelo core (`RevCollector`, sha256[:12]). Best-effort:
//! falhas de I/O são ignoradas, nunca entram no caminho de erro do proxy.

use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;

fn store_dir() -> Option<PathBuf> {
    Some(crate::events::home_dir()?.join("reversible"))
}

/// Guarda `span` sob `reference` (content-addressed: não reescreve se já existe).
pub fn put(reference: &str, span: &str) {
    let Some(dir) = store_dir() else { return };
    let _ = std::fs::create_dir_all(&dir);
    let path = dir.join(format!("{reference}.txt"));
    if !path.exists() {
        if let Ok(mut f) = OpenOptions::new().create(true).write(true).open(&path) {
            let _ = f.write_all(span.as_bytes());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn put_writes_span_file() {
        let tmp = std::env::temp_dir().join(format!("rdx_rev_test_{}", std::process::id()));
        std::env::set_var("REDUX_TOKEN_HOME", &tmp);
        put("abc123abc123", "conteúdo original");
        let path = tmp.join("reversible").join("abc123abc123.txt");
        assert_eq!(std::fs::read_to_string(&path).unwrap(), "conteúdo original");
        std::env::remove_var("REDUX_TOKEN_HOME");
        let _ = std::fs::remove_dir_all(&tmp);
    }
}
