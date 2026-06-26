use super::Filter;
use regex::Regex;
use std::sync::OnceLock;

static BLOCK_COMMENT: OnceLock<Regex> = OnceLock::new();
static LINE_COMMENT: OnceLock<Regex> = OnceLock::new();

fn block_re() -> &'static Regex {
    BLOCK_COMMENT.get_or_init(|| Regex::new(r"/\*[\s\S]*?\*/").unwrap())
}

fn line_re() -> &'static Regex {
    LINE_COMMENT.get_or_init(|| Regex::new(r"[ \t]*//[^\n]*").unwrap())
}

pub struct CodeFilter;

impl Filter for CodeFilter {
    fn apply(&self, input: &str) -> String {
        // Remove /* ... */ block comments
        let s = block_re().replace_all(input, "").to_string();
        // Remove // line comments
        let s = line_re().replace_all(&s, "").to_string();

        // Collapse multiple blank lines into one
        let mut out = String::with_capacity(s.len());
        let mut prev_blank = false;
        for line in s.lines() {
            let blank = line.trim().is_empty();
            if blank && prev_blank {
                continue;
            }
            out.push_str(line);
            out.push('\n');
            prev_blank = blank;
        }

        out.trim_end().to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn removes_block_comments() {
        let f = CodeFilter;
        let input = "int x = /* a block */ 5;";
        assert!(!f.apply(input).contains("block"));
    }

    #[test]
    fn removes_line_comments() {
        let f = CodeFilter;
        let input = "let x = 1; // this is a comment\nlet y = 2;";
        let out = f.apply(input);
        assert!(!out.contains("this is a comment"));
        assert!(out.contains("let y = 2"));
    }

    #[test]
    fn collapses_blank_lines() {
        let f = CodeFilter;
        let input = "a\n\n\n\nb";
        let out = f.apply(input);
        assert_eq!(out, "a\n\nb");
    }
}
