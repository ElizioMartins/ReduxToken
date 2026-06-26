pub mod code;
pub mod json;
pub mod smart;
pub mod text;

pub trait Filter: Send + Sync {
    fn apply(&self, input: &str) -> String;
}
