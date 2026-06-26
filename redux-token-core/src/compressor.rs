use crate::filters::{Filter, code::CodeFilter, json::JsonFilter, smart::SmartFilter, text::TextFilter};
use crate::stats::{CompressionStats, Timer, count_tokens};

pub struct Compressor {
    filters: Vec<Box<dyn Filter>>,
}

impl Compressor {
    pub fn new(filters: Vec<Box<dyn Filter>>) -> Self {
        Self { filters }
    }

    pub fn compress(&self, input: &str) -> (String, CompressionStats) {
        let timer = Timer::start();
        let original_tokens = count_tokens(input);

        let mut text = input.to_string();
        for filter in &self.filters {
            text = filter.apply(&text);
        }

        let compressed_tokens = count_tokens(&text);
        let tokens_saved = original_tokens.saturating_sub(compressed_tokens);
        let savings_pct = if original_tokens > 0 {
            tokens_saved as f64 / original_tokens as f64 * 100.0
        } else {
            0.0
        };

        let stats = CompressionStats {
            original_tokens,
            compressed_tokens,
            tokens_saved,
            savings_pct,
            time_ms: timer.elapsed_ms(),
        };

        (text, stats)
    }
}

impl Default for Compressor {
    fn default() -> Self {
        Self::new(vec![
            Box::new(JsonFilter),
            Box::new(CodeFilter),
            Box::new(TextFilter),
            Box::new(SmartFilter),
        ])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn compresses_log_output() {
        let c = Compressor::default();
        let input = "[DEBUG] loading\n[DEBUG] done\nServer ready\n======\nServer ready";
        let (out, stats) = c.compress(input);
        assert!(out.contains("Server ready"));
        assert!(!out.contains("[DEBUG]"));
        assert!(!out.contains("======"));
        assert!(stats.tokens_saved > 0);
    }

    #[test]
    fn stats_are_consistent() {
        let c = Compressor::default();
        let (_, stats) = c.compress("hello world");
        assert_eq!(
            stats.tokens_saved,
            stats.original_tokens.saturating_sub(stats.compressed_tokens)
        );
    }
}
