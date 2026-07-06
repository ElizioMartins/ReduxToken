use super::Filter;
use serde_json::Value;

// Fields that carry no semantic value for LLM processing
const IGNORED_KEYS: &[&str] = &[
    "id", "uuid", "_id", "__v",
    "created_at", "updated_at", "deleted_at",
    "created_by", "updated_by",
    "timestamp", "timestamps",
    "metadata", "deprecated", "version",
];

// Arrays maiores que isto, se homogêneos (objetos com as mesmas chaves), são
// resumidos: mantemos algumas amostras e sinalizamos quantos foram omitidos.
const ARRAY_SUMMARIZE_THRESHOLD: usize = 5;
const ARRAY_SAMPLE_COUNT: usize = 2;

pub struct JsonFilter;

impl Filter for JsonFilter {
    fn apply(&self, input: &str) -> String {
        let trimmed = input.trim();

        // Try as a single JSON value
        if let Ok(value) = serde_json::from_str::<Value>(trimmed) {
            return serde_json::to_string(&clean_value(value))
                .unwrap_or_else(|_| input.to_string());
        }

        // Try as JSONL (one JSON object per line)
        let lines: Vec<&str> = trimmed.lines().collect();
        let mut cleaned: Vec<String> = Vec::with_capacity(lines.len());
        for line in &lines {
            let line = line.trim();
            if line.is_empty() {
                cleaned.push(String::new());
                continue;
            }
            match serde_json::from_str::<Value>(line) {
                Ok(v) => cleaned.push(
                    serde_json::to_string(&clean_value(v))
                        .unwrap_or_else(|_| line.to_string()),
                ),
                Err(_) => return input.to_string(), // not JSONL, skip
            }
        }

        if cleaned.iter().any(|l| !l.is_empty()) {
            cleaned.join("\n")
        } else {
            input.to_string()
        }
    }
}

fn clean_value(value: Value) -> Value {
    match value {
        Value::Object(map) => {
            let cleaned = map
                .into_iter()
                .filter(|(k, _)| !IGNORED_KEYS.contains(&k.as_str()))
                .map(|(k, v)| (k, clean_value(v)))
                .collect();
            Value::Object(cleaned)
        }
        Value::Array(arr) => {
            let cleaned: Vec<Value> = arr.into_iter().map(clean_value).collect();
            Value::Array(summarize_array(cleaned))
        }
        other => other,
    }
}

/// Chaves de um objeto (ordenadas) para comparar formato entre elementos.
fn object_keys(v: &Value) -> Option<Vec<&str>> {
    v.as_object().map(|m| {
        let mut keys: Vec<&str> = m.keys().map(|k| k.as_str()).collect();
        keys.sort_unstable();
        keys
    })
}

/// Colapsa arrays grandes de objetos homogêneos em: amostras + marcador de omissão.
/// Mantém o resultado como um array JSON válido (o marcador é uma string).
fn summarize_array(items: Vec<Value>) -> Vec<Value> {
    if items.len() <= ARRAY_SUMMARIZE_THRESHOLD {
        return items;
    }
    let reference = match object_keys(&items[0]) {
        Some(k) => k,
        None => return items, // não é array de objetos
    };
    let homogeneous = items
        .iter()
        .all(|v| object_keys(v).as_deref() == Some(reference.as_slice()));
    if !homogeneous {
        return items;
    }

    let omitted = items.len() - ARRAY_SAMPLE_COUNT;
    let mut out: Vec<Value> = items.into_iter().take(ARRAY_SAMPLE_COUNT).collect();
    out.push(Value::String(format!(
        "⟦+{omitted} itens semelhantes omitidos⟧"
    )));
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn removes_ignored_fields() {
        let f = JsonFilter;
        let input = r#"{"id":"abc","name":"John","email":"j@j.com","created_at":"2024"}"#;
        let out = f.apply(input);
        assert!(!out.contains(r#""id""#));
        assert!(!out.contains(r#""created_at""#));
        assert!(out.contains(r#""name""#));
        assert!(out.contains(r#""email""#));
    }

    #[test]
    fn non_json_passthrough() {
        let f = JsonFilter;
        let input = "just some plain text";
        assert_eq!(f.apply(input), input);
    }

    #[test]
    fn handles_nested_objects() {
        let f = JsonFilter;
        let input = r#"{"metadata":{"x":1},"data":{"value":42}}"#;
        let out = f.apply(input);
        assert!(!out.contains(r#""metadata""#));
        assert!(out.contains(r#""data""#));
    }

    #[test]
    fn summarizes_large_homogeneous_array() {
        let f = JsonFilter;
        let items: Vec<String> = (0..50).map(|i| format!(r#"{{"name":"u{i}","age":{i}}}"#)).collect();
        let input = format!("[{}]", items.join(","));
        let out = f.apply(&input);
        // continua sendo JSON válido
        let parsed: Value = serde_json::from_str(&out).unwrap();
        let arr = parsed.as_array().unwrap();
        assert_eq!(arr.len(), 3); // 2 amostras + 1 marcador
        assert!(out.contains("omitidos"));
        assert!(out.contains("u0") && out.contains("u1"));
        assert!(!out.contains("u49"));
    }

    #[test]
    fn keeps_small_array() {
        let f = JsonFilter;
        let input = r#"[{"a":1},{"a":2},{"a":3}]"#;
        let out = f.apply(input);
        assert!(!out.contains("omitidos"));
        assert!(out.contains(r#""a":3"#) || out.contains(r#""a": 3"#));
    }

    #[test]
    fn keeps_heterogeneous_array() {
        let f = JsonFilter;
        let items: Vec<String> = (0..20).map(|i| {
            if i % 2 == 0 { format!(r#"{{"a":{i}}}"#) } else { format!(r#"{{"b":{i}}}"#) }
        }).collect();
        let input = format!("[{}]", items.join(","));
        let out = f.apply(&input);
        assert!(!out.contains("omitidos")); // formatos diferentes → não colapsa
    }

    #[test]
    fn keeps_array_of_scalars() {
        let f = JsonFilter;
        let input = "[1,2,3,4,5,6,7,8,9,10]";
        let out = f.apply(input);
        assert!(!out.contains("omitidos"));
    }
}
