pub mod code;
pub mod json;
pub mod smart;
pub mod text;

use crate::rev::RevCollector;

pub trait Filter: Send + Sync {
    fn apply(&self, input: &str) -> String;

    /// Versão reversível: em vez de descartar o trecho, troca-o por um marcador
    /// `⟦rdx:ref⟧` e o registra em `rc`. Padrão: sem reversibilidade (== `apply`).
    fn apply_rev(&self, input: &str, _rc: &mut RevCollector) -> String {
        self.apply(input)
    }
}
