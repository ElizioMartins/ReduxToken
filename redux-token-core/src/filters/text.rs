use super::Filter;
use crate::rev::RevCollector;

// Log prefixes that add no semantic content for LLM consumption
const LOG_PREFIXES: &[&str] = &[
    "[DEBUG]", "[TRACE]", "DEBUG:", "TRACE:",
    "DEBUG -", "TRACE -",
];

fn is_noise(trimmed: &str) -> bool {
    LOG_PREFIXES.iter().any(|p| trimmed.starts_with(p))
}

pub struct TextFilter;

impl Filter for TextFilter {
    fn apply(&self, input: &str) -> String {
        let mut out = String::with_capacity(input.len());
        let mut blank_count = 0usize;

        for line in input.lines() {
            let trimmed = line.trim();

            if trimmed.is_empty() {
                blank_count += 1;
                if blank_count == 1 {
                    out.push('\n');
                }
                continue;
            }
            blank_count = 0;

            if is_noise(trimmed) {
                continue;
            }

            out.push_str(trimmed);
            out.push('\n');
        }

        out.trim().to_string()
    }

    fn apply_rev(&self, input: &str, rc: &mut RevCollector) -> String {
        // Linhas de log consecutivas viram UM marcador (evita explodir a contagem).
        let mut out = String::with_capacity(input.len());
        let mut pending: Vec<&str> = Vec::new();
        let mut blank_count = 0usize;

        let flush = |pending: &mut Vec<&str>, out: &mut String, rc: &mut RevCollector| {
            if !pending.is_empty() {
                let block = pending.join("\n");
                out.push_str(&rc.stash(&block));
                out.push('\n');
                pending.clear();
            }
        };

        for line in input.lines() {
            let trimmed = line.trim();

            if trimmed.is_empty() {
                flush(&mut pending, &mut out, rc);
                blank_count += 1;
                if blank_count == 1 {
                    out.push('\n');
                }
                continue;
            }
            blank_count = 0;

            if is_noise(trimmed) {
                pending.push(trimmed);
                continue;
            }

            flush(&mut pending, &mut out, rc);
            out.push_str(trimmed);
            out.push('\n');
        }
        flush(&mut pending, &mut out, rc);

        out.trim().to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn collapses_blank_lines() {
        let f = TextFilter;
        let out = f.apply("a\n\n\n\nb");
        assert_eq!(out, "a\n\nb");
    }

    #[test]
    fn removes_debug_lines() {
        let f = TextFilter;
        let out = f.apply("[DEBUG] loading config\nServer started");
        assert!(!out.contains("loading config"));
        assert!(out.contains("Server started"));
    }

    #[test]
    fn trims_trailing_whitespace() {
        let f = TextFilter;
        let out = f.apply("  hello world   ");
        assert_eq!(out, "hello world");
    }
}
