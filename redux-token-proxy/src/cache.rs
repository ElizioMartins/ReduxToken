use dashmap::DashMap;
use sha2::{Digest, Sha256};

pub struct CompressionCache {
    inner: DashMap<String, String>,
}

impl CompressionCache {
    pub fn new() -> Self {
        Self { inner: DashMap::new() }
    }

    pub fn key(text: &str) -> String {
        hex::encode(Sha256::digest(text.as_bytes()))
    }

    pub fn get(&self, key: &str) -> Option<String> {
        self.inner.get(key).map(|v| v.value().clone())
    }

    pub fn insert(&self, key: String, value: String) {
        self.inner.insert(key, value);
    }
}
