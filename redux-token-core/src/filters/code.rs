use super::Filter;
use crate::rev::RevCollector;
use regex::Regex;
use std::sync::OnceLock;

static BLOCK_COMMENT: OnceLock<Regex> = OnceLock::new();

fn block_re() -> &'static Regex {
    BLOCK_COMMENT.get_or_init(|| Regex::new(r"/\*[\s\S]*?\*/").unwrap())
}

pub struct CodeFilter;

impl Filter for CodeFilter {
    fn apply(&self, input: &str) -> String {
        let s = block_re().replace_all(input, "").to_string();
        let s = strip_line_comments(&s, None);
        collapse_blank_lines(&s)
    }

    fn apply_rev(&self, input: &str, rc: &mut RevCollector) -> String {
        // Troca cada comentário por um marcador recuperável em vez de apagá-lo.
        let s = block_re()
            .replace_all(input, |caps: &regex::Captures| rc.stash(&caps[0]))
            .to_string();
        let s = strip_line_comments(&s, Some(rc));
        collapse_blank_lines(&s)
    }
}

/// Remove (ou, em modo reversível, marca) comentários `//` de fim de linha,
/// **sem** confundir com URLs (`://`) nem com `//` dentro de strings.
fn strip_line_comments(s: &str, mut rc: Option<&mut RevCollector>) -> String {
    let mut out = String::with_capacity(s.len());
    for line in s.lines() {
        match find_line_comment(line) {
            Some(idx) => {
                out.push_str(line[..idx].trim_end());
                if let Some(rc) = rc.as_deref_mut() {
                    out.push_str(&rc.stash(line[idx..].trim_start()));
                }
            }
            None => out.push_str(line),
        }
        out.push('\n');
    }
    out.trim_end().to_string()
}

/// Índice do início de um comentário `//` "de verdade" na linha, se houver.
/// Ignora `//` dentro de aspas e `//` precedido por `:` (esquemas de URL).
fn find_line_comment(line: &str) -> Option<usize> {
    let bytes = line.as_bytes();
    let mut i = 0;
    let mut in_str: Option<u8> = None;
    let mut escaped = false;
    while i < bytes.len() {
        let c = bytes[i];
        if let Some(quote) = in_str {
            if escaped {
                escaped = false;
            } else if c == b'\\' {
                escaped = true;
            } else if c == quote {
                in_str = None;
            }
            i += 1;
            continue;
        }
        match c {
            b'"' | b'\'' => in_str = Some(c),
            b'/' if bytes.get(i + 1) == Some(&b'/') => {
                // `://` (URL) não é comentário — pula os dois `/` e segue.
                if i > 0 && bytes[i - 1] == b':' {
                    i += 2;
                    continue;
                }
                return Some(i);
            }
            _ => {}
        }
        i += 1;
    }
    None
}

fn collapse_blank_lines(s: &str) -> String {
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
    fn preserves_urls() {
        let f = CodeFilter;
        let input = "veja https://exemplo.com/api/v1 aqui";
        assert_eq!(f.apply(input), input);
    }

    #[test]
    fn preserves_url_but_strips_comment() {
        let f = CodeFilter;
        let input = r#"url = "http://a.b" // comentario"#;
        let out = f.apply(input);
        assert!(out.contains("http://a.b"));
        assert!(!out.contains("comentario"));
    }

    #[test]
    fn ignores_double_slash_inside_string() {
        let f = CodeFilter;
        let input = r#"let s = "a // b";"#;
        assert_eq!(f.apply(input), input);
    }

    #[test]
    fn full_line_comment_removed() {
        let f = CodeFilter;
        let out = f.apply("// só comentário\ncodigo();");
        assert!(!out.contains("comentário"));
        assert!(out.contains("codigo();"));
    }

    #[test]
    fn collapses_blank_lines() {
        let f = CodeFilter;
        let input = "a\n\n\n\nb";
        let out = f.apply(input);
        assert_eq!(out, "a\n\nb");
    }
}
