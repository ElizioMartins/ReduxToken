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
        Value::Array(arr) => Value::Array(arr.into_iter().map(clean_value).collect()),
        other => other,
    }
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
}
