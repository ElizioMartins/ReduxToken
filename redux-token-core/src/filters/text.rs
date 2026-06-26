use super::Filter;

// Log prefixes that add no semantic content for LLM consumption
const LOG_PREFIXES: &[&str] = &[
    "[DEBUG]", "[TRACE]", "DEBUG:", "TRACE:",
    "DEBUG -", "TRACE -",
];

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

            if LOG_PREFIXES.iter().any(|p| trimmed.starts_with(p)) {
                continue;
            }

            out.push_str(trimmed);
            out.push('\n');
        }

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
