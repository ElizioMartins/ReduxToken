use serde::Deserialize;
use std::path::Path;

#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    pub server: ServerConfig,
    pub providers: Vec<ProviderConfig>,
    #[serde(default)]
    pub reversible: ReversibleConfig,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ServerConfig {
    pub port: u16,
}

/// Compressão reversível (CCR): guarda trechos removidos e insere marcadores
/// `⟦rdx:ref⟧` recuperáveis via a tool MCP `retrieve` (store compartilhado em disco).
#[derive(Debug, Clone, Deserialize, Default)]
pub struct ReversibleConfig {
    #[serde(default)]
    pub enabled: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ProviderConfig {
    pub name: String,
    pub target: String,
    pub prefix: String,
}

impl Config {
    pub fn load(path: &Path) -> anyhow::Result<Self> {
        let content = std::fs::read_to_string(path)?;
        Ok(toml::from_str(&content)?)
    }
}

impl Default for Config {
    fn default() -> Self {
        Config {
            server: ServerConfig { port: 8080 },
            reversible: ReversibleConfig::default(),
            providers: vec![
                ProviderConfig {
                    name: "openai".to_string(),
                    target: "https://api.openai.com".to_string(),
                    prefix: "/openai".to_string(),
                },
                ProviderConfig {
                    name: "claude".to_string(),
                    target: "https://api.anthropic.com".to_string(),
                    prefix: "/claude".to_string(),
                },
            ],
        }
    }
}
