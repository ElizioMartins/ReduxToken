"""Registro de eventos de compressão — a fundação da Fase 5 (Observabilidade).

Todos os pontos de compressão em Python (biblioteca, CLI, hook, MCP) chamam
``record()`` para gravar uma linha JSONL em ``~/.redux-token/events.jsonl``. O proxy
Rust grava no mesmo arquivo e no mesmo schema (ver ``redux-token-proxy/src/events.rs``).

Princípios (ver ANALYTICS.md):
- **Local-first**: nunca sai da máquina.
- **Opt-out**: ligado por padrão; ``REDUX_TOKEN_NO_STATS=1`` desliga.
- **Nunca quebra o chamador**: qualquer erro é engolido silenciosamente.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_SESSION_ID: str | None = None

# Fontes válidas de um evento de compressão.
SOURCES = ("lib", "cli", "proxy", "hook", "mcp")


def _disabled() -> bool:
    return os.environ.get("REDUX_TOKEN_NO_STATS") == "1"


def log_path() -> Path:
    """Caminho do event log. Respeita ``REDUX_TOKEN_HOME`` (usado em testes)."""
    override = os.environ.get("REDUX_TOKEN_HOME")
    base = Path(override) if override else Path.home() / ".redux-token"
    return base / "events.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def session_id() -> str:
    """ID estável por processo. Agrupa eventos de uma mesma execução."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = f"{_now()}-{uuid.uuid4().hex[:4]}"
    return _SESSION_ID


def detect_content_type(text: str) -> str:
    """Heurística barata p/ o breakdown do ``discover``. Erra p/ ``mixed``/``text``
    sem prejuízo — é só rótulo, não afeta a compressão."""
    sample = text[:4096]
    stripped = sample.lstrip()
    if stripped[:1] in ("{", "["):
        try:
            json.loads(text)
            return "json"
        except (ValueError, TypeError):
            pass
    if "[DEBUG]" in sample or "[TRACE]" in sample or "[INFO]" in sample or "[WARN]" in sample:
        return "log"
    lowered = sample
    if any(tok in lowered for tok in ("//", "/*", "def ", "fn ", "function ", "class ", "import ", "#include")):
        return "code"
    return "text"


def record(source: str, stats: Any, text: str, from_cache: bool = False) -> None:
    """Anexa um evento ao log. ``stats`` é um ``CompressionStats`` do core Rust."""
    if _disabled():
        return
    try:
        event = {
            "ts": _now(),
            "source": source,
            "content_type": detect_content_type(text),
            "original_tokens": int(stats.original_tokens),
            "compressed_tokens": int(stats.compressed_tokens),
            "tokens_saved": int(stats.tokens_saved),
            "savings_pct": round(float(stats.savings_pct), 2),
            "time_ms": round(float(stats.time_ms), 3),
            "from_cache": bool(from_cache),
            "session_id": session_id(),
        }
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with _LOCK:
            # 'a' + escrita de uma linha curta é atômica o suficiente p/ nosso caso.
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        # Telemetria nunca pode quebrar a compressão (especialmente no hook).
        pass
