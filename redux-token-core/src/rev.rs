//! Coleta de trechos removidos para compressão reversível (CCR, Fase 6.2).
//!
//! Quando um filtro roda em modo reversível, em vez de descartar o trecho ele o
//! entrega ao `RevCollector`, que devolve um marcador `⟦rdx:<ref>⟧` para inserir no
//! lugar e guarda o par (ref, original). O `ref` é `sha256(trecho)[:12]` — idêntico ao
//! lado Python (`reversible.ref_for`), garantindo que o `retrieve` encontre o conteúdo.

use sha2::{Digest, Sha256};

/// Acumula os trechos extraídos durante uma compressão reversível.
pub struct RevCollector {
    spans: Vec<(String, String)>,
}

impl RevCollector {
    pub fn new() -> Self {
        Self { spans: Vec::new() }
    }

    /// Registra um trecho e devolve o marcador a ser inserido no texto comprimido.
    pub fn stash(&mut self, span: &str) -> String {
        let r = ref_of(span);
        self.spans.push((r.clone(), span.to_string()));
        format!("⟦rdx:{r}⟧")
    }

    pub fn is_empty(&self) -> bool {
        self.spans.is_empty()
    }

    pub fn into_spans(self) -> Vec<(String, String)> {
        self.spans
    }
}

impl Default for RevCollector {
    fn default() -> Self {
        Self::new()
    }
}

/// `sha256(s)[:12]` em hex (6 bytes) — casa com `hexdigest()[:12]` do Python.
fn ref_of(s: &str) -> String {
    let digest = Sha256::digest(s.as_bytes());
    digest[..6].iter().map(|b| format!("{b:02x}")).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stash_returns_marker_and_records() {
        let mut rc = RevCollector::new();
        let marker = rc.stash("// segredo");
        assert!(marker.starts_with("⟦rdx:") && marker.ends_with('⟧'));
        let spans = rc.into_spans();
        assert_eq!(spans.len(), 1);
        assert_eq!(spans[0].1, "// segredo");
    }

    #[test]
    fn ref_is_deterministic_and_12_hex() {
        let r = ref_of("abc");
        assert_eq!(r.len(), 12);
        assert_eq!(r, ref_of("abc"));
        assert!(r.chars().all(|c| c.is_ascii_hexdigit()));
    }
}
