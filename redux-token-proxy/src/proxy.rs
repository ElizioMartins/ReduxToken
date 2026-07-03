use std::sync::Arc;
use axum::{
    body::Body,
    extract::State,
    http::{Request, Response, StatusCode},
    response::IntoResponse,
};
use serde_json::Value;

use crate::{cache::CompressionCache, stats::SessionStats, AppState};
use redux_token_core::{stats::count_tokens, Compressor};

pub async fn proxy_handler(
    State(state): State<Arc<AppState>>,
    req: Request<Body>,
) -> impl IntoResponse {
    match forward(state, req).await {
        Ok(r) => r,
        Err(e) => {
            tracing::error!("proxy error: {e:#}");
            Response::builder()
                .status(StatusCode::BAD_GATEWAY)
                .body(Body::from(format!("proxy error: {e}")))
                .unwrap()
        }
    }
}

async fn forward(state: Arc<AppState>, req: Request<Body>) -> anyhow::Result<Response<Body>> {
    let path = req.uri().path().to_string();
    let query = req.uri().query().map(|q| format!("?{q}")).unwrap_or_default();
    let method = req.method().clone();
    let headers = req.headers().clone();

    let provider = state
        .config
        .providers
        .iter()
        .find(|p| path.starts_with(&p.prefix))
        .ok_or_else(|| anyhow::anyhow!("no provider matches path '{path}'"))?;

    let target_path = &path[provider.prefix.len()..];
    let url = format!("{}{}{}", provider.target, target_path, query);
    tracing::info!("{} {}", method, url);

    let body_bytes = axum::body::to_bytes(req.into_body(), 10 * 1024 * 1024).await?;
    let body_bytes = maybe_compress(&state, &body_bytes);

    let mut upstream = state.client.request(method, &url).body(body_bytes);
    for (name, value) in &headers {
        let n = name.as_str();
        if n != "host" && n != "content-length" {
            upstream = upstream.header(name, value);
        }
    }

    let resp = upstream.send().await?;
    state.stats.inc_request();

    let status = resp.status();
    let resp_headers = resp.headers().clone();

    let mut builder = Response::builder().status(status);
    for (name, value) in &resp_headers {
        let n = name.as_str();
        // let reqwest/axum manage framing headers
        if n != "transfer-encoding" && n != "content-length" {
            builder = builder.header(name, value);
        }
    }

    Ok(builder.body(Body::from_stream(resp.bytes_stream()))?)
}

fn maybe_compress(state: &AppState, bytes: &[u8]) -> Vec<u8> {
    let Ok(mut json) = serde_json::from_slice::<Value>(bytes) else {
        return bytes.to_vec();
    };
    if compress_messages(&mut json, &state.compressor, &state.cache, &state.stats) {
        serde_json::to_vec(&json).unwrap_or_else(|_| bytes.to_vec())
    } else {
        bytes.to_vec()
    }
}

fn compress_messages(
    body: &mut Value,
    compressor: &Compressor,
    cache: &CompressionCache,
    stats: &SessionStats,
) -> bool {
    let Some(messages) = body.get_mut("messages").and_then(|m| m.as_array_mut()) else {
        return false;
    };
    let mut changed = false;
    for msg in messages.iter_mut() {
        match msg.get_mut("content") {
            Some(Value::String(s)) => {
                let compressed = do_compress(s, compressor, cache, stats);
                if compressed != *s {
                    *s = compressed;
                    changed = true;
                }
            }
            Some(Value::Array(parts)) => {
                for part in parts.iter_mut() {
                    if part.get("type").and_then(|t| t.as_str()) == Some("text") {
                        if let Some(Value::String(s)) = part.get_mut("text") {
                            let compressed = do_compress(s, compressor, cache, stats);
                            if compressed != *s {
                                *s = compressed;
                                changed = true;
                            }
                        }
                    }
                }
            }
            _ => {}
        }
    }
    changed
}

fn do_compress(
    text: &str,
    compressor: &Compressor,
    cache: &CompressionCache,
    stats: &SessionStats,
) -> String {
    let key = CompressionCache::key(text);
    if let Some(cached) = cache.get(&key) {
        let orig = count_tokens(text) as u64;
        let comp = count_tokens(&cached) as u64;
        stats.add_tokens(orig, comp, true);
        crate::events::record(text, orig, comp, 0.0, true);
        return cached;
    }
    let (compressed, cs) = compressor.compress(text);
    stats.add_tokens(cs.original_tokens as u64, cs.compressed_tokens as u64, false);
    crate::events::record(
        text,
        cs.original_tokens as u64,
        cs.compressed_tokens as u64,
        cs.time_ms,
        false,
    );
    cache.insert(key, compressed.clone());
    compressed
}
