use pyo3::prelude::*;
use std::time::Instant;

#[pyclass]
#[derive(Debug, Clone)]
pub struct CompressionStats {
    #[pyo3(get)]
    pub original_tokens: usize,
    #[pyo3(get)]
    pub compressed_tokens: usize,
    #[pyo3(get)]
    pub tokens_saved: usize,
    #[pyo3(get)]
    pub savings_pct: f64,
    #[pyo3(get)]
    pub time_ms: f64,
}

#[pymethods]
impl CompressionStats {
    fn __repr__(&self) -> String {
        format!(
            "CompressionStats(saved={}, {:.1}%, {:.2}ms)",
            self.tokens_saved, self.savings_pct, self.time_ms
        )
    }
}

// Simple heuristic: ~4 chars per token (approximates GPT-family tokenizers)
pub fn count_tokens(text: &str) -> usize {
    (text.len() / 4).max(1)
}

pub struct Timer(Instant);

impl Timer {
    pub fn start() -> Self {
        Self(Instant::now())
    }

    pub fn elapsed_ms(&self) -> f64 {
        self.0.elapsed().as_secs_f64() * 1000.0
    }
}
