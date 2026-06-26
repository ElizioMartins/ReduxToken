use super::Filter;
use std::collections::HashSet;

pub struct SmartFilter;

impl Filter for SmartFilter {
    fn apply(&self, input: &str) -> String {
        let mut seen: HashSet<String> = HashSet::new();
        let mut out = String::with_capacity(input.len());

        for line in input.lines() {
            let trimmed = line.trim();

            if is_separator(trimmed) {
                continue;
            }

            if !trimmed.is_empty() {
                if seen.contains(trimmed) {
                    continue;
                }
                seen.insert(trimmed.to_string());
            }

            out.push_str(trimmed);
            out.push('\n');
        }

        out.trim().to_string()
    }
}

// A separator is a line made entirely of one repeated char from the set =-*_
fn is_separator(line: &str) -> bool {
    if line.len() < 3 {
        return false;
    }
    let mut chars = line.chars();
    let first = match chars.next() {
        Some(c) => c,
        None => return false,
    };
    "=-*_".contains(first) && line.chars().all(|c| c == first)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn removes_separators() {
        let f = SmartFilter;
        let out = f.apply("title\n======\ncontent");
        assert!(!out.contains("======"));
        assert!(out.contains("title"));
        assert!(out.contains("content"));
    }

    #[test]
    fn deduplicates_lines() {
        let f = SmartFilter;
        let out = f.apply("line one\nline one\nline two");
        assert_eq!(out.lines().count(), 2);
    }

    #[test]
    fn preserves_order() {
        let f = SmartFilter;
        let out = f.apply("alpha\nbeta\ngamma");
        let lines: Vec<&str> = out.lines().collect();
        assert_eq!(lines, ["alpha", "beta", "gamma"]);
    }
}
