use std::{path::Path, sync::Arc};
use axum::{routing::get, Router};
use tokio::net::TcpListener;

mod cache;
mod config;
mod events;
mod proxy;
mod reversible;
mod stats;

use cache::CompressionCache;
use config::Config;
use proxy::proxy_handler;
use redux_token_core::Compressor;
use stats::SessionStats;

pub struct AppState {
    pub config: Config,
    pub compressor: Compressor,
    pub cache: CompressionCache,
    pub stats: SessionStats,
    pub client: reqwest::Client,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("redux_proxy=info".parse()?),
        )
        .init();

    let config = if Path::new("proxy.toml").exists() {
        Config::load(Path::new("proxy.toml"))?
    } else {
        Config::default()
    };

    let port = config.server.port;
    let state = Arc::new(AppState {
        config,
        compressor: Compressor::default(),
        cache: CompressionCache::new(),
        stats: SessionStats::new(),
        client: reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(120))
            .build()?,
    });

    let app = Router::new()
        .route("/_redux/stats", get(stats::stats_handler))
        .fallback(axum::routing::any(proxy_handler))
        .with_state(state);

    let addr = format!("0.0.0.0:{port}");
    tracing::info!("ReduxToken proxy → http://{addr}");
    tracing::info!("Stats            → http://localhost:{port}/_redux/stats");

    let listener = TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}
