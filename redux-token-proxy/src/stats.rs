use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use axum::{extract::State, response::IntoResponse};
use serde::Serialize;
use crate::AppState;

pub struct SessionStats {
    requests: AtomicU64,
    original_tokens: AtomicU64,
    compressed_tokens: AtomicU64,
    cache_hits: AtomicU64,
}

impl SessionStats {
    pub fn new() -> Self {
        Self {
            requests: AtomicU64::new(0),
            original_tokens: AtomicU64::new(0),
            compressed_tokens: AtomicU64::new(0),
            cache_hits: AtomicU64::new(0),
        }
    }

    pub fn inc_request(&self) {
        self.requests.fetch_add(1, Ordering::Relaxed);
    }

    pub fn add_tokens(&self, original: u64, compressed: u64, from_cache: bool) {
        self.original_tokens.fetch_add(original, Ordering::Relaxed);
        self.compressed_tokens.fetch_add(compressed, Ordering::Relaxed);
        if from_cache {
            self.cache_hits.fetch_add(1, Ordering::Relaxed);
        }
    }

    pub fn summary(&self) -> StatsSummary {
        let original = self.original_tokens.load(Ordering::Relaxed);
        let compressed = self.compressed_tokens.load(Ordering::Relaxed);
        let saved = original.saturating_sub(compressed);
        StatsSummary {
            requests: self.requests.load(Ordering::Relaxed),
            cache_hits: self.cache_hits.load(Ordering::Relaxed),
            original_tokens: original,
            compressed_tokens: compressed,
            tokens_saved: saved,
            savings_pct: if original > 0 {
                saved as f64 / original as f64 * 100.0
            } else {
                0.0
            },
        }
    }
}

#[derive(Serialize)]
pub struct StatsSummary {
    pub requests: u64,
    pub cache_hits: u64,
    pub original_tokens: u64,
    pub compressed_tokens: u64,
    pub tokens_saved: u64,
    pub savings_pct: f64,
}

pub async fn stats_handler(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    axum::Json(state.stats.summary())
}
