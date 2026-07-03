"""Health check dos pontos de integração do ReduxToken (Fase 5).

``redux-token doctor`` confirma que os 5 pontos de compressão estão instaláveis e
roteando/gravando. Reduz suporte: em vez de "não funciona", o usuário vê exatamente
qual peça está fora do lugar.

Cada verificação retorna ``{"name", "status", "detail"}`` com status
``ok`` | ``warn`` | ``fail``. ``warn`` = opcional/ausente (ex.: proxy desligado);
``fail`` = algo que deveria funcionar e não funciona (ex.: core Rust não importa).
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from redux_token import telemetry


def check_core() -> dict:
    """O core Rust (PyO3) importa e comprime?"""
    try:
        from redux_token import ReduxToken

        _, stats = ReduxToken().compress("teste [DEBUG] x\nteste")
        return {"name": "core Rust", "status": "ok", "detail": f"compressão ok ({stats.time_ms:.2f}ms)"}
    except Exception as e:  # pragma: no cover - caminho de falha de build
        return {"name": "core Rust", "status": "fail", "detail": f"não importou: {e}"}


def check_event_log() -> dict:
    """O event log é gravável (ou desligado explicitamente)?"""
    if os.environ.get("REDUX_TOKEN_NO_STATS") == "1":
        return {"name": "event log", "status": "warn", "detail": "desligado (REDUX_TOKEN_NO_STATS=1)"}
    path = telemetry.log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(path.parent, os.W_OK):
            return {"name": "event log", "status": "fail", "detail": f"sem permissão de escrita em {path.parent}"}
        return {"name": "event log", "status": "ok", "detail": str(path)}
    except Exception as e:
        return {"name": "event log", "status": "fail", "detail": f"{path.parent} inacessível: {e}"}


def check_hook(project_dir: Path | None = None) -> dict:
    """O hook PostToolUse está configurado no .claude/settings.json do projeto?"""
    project_dir = project_dir or Path.cwd()
    settings = project_dir / ".claude" / "settings.json"
    if not settings.exists():
        return {"name": "hook Claude Code", "status": "warn", "detail": "sem .claude/settings.json neste projeto"}
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        return {"name": "hook Claude Code", "status": "warn", "detail": f"settings.json ilegível: {e}"}
    if "redux_token.hook" in json.dumps(data):
        return {"name": "hook Claude Code", "status": "ok", "detail": "PostToolUse configurado"}
    return {"name": "hook Claude Code", "status": "warn", "detail": "hook não referenciado no settings.json"}


def _proxy_port(project_dir: Path) -> int:
    toml = project_dir / "proxy.toml"
    if toml.exists():
        try:
            import tomllib

            data = tomllib.loads(toml.read_text(encoding="utf-8"))
            return int(data.get("server", {}).get("port", 8080))
        except Exception:
            pass
    return 8080


def check_proxy(project_dir: Path | None = None) -> dict:
    """O proxy está no ar respondendo em /_redux/stats? (opcional)"""
    project_dir = project_dir or Path.cwd()
    port = _proxy_port(project_dir)
    url = f"http://localhost:{port}/_redux/stats"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read())
        return {"name": "proxy HTTP", "status": "ok", "detail": f"no ar :{port} ({data.get('requests', 0)} requests)"}
    except Exception:
        return {"name": "proxy HTTP", "status": "warn", "detail": f"não está rodando em :{port} (opcional)"}


def check_mcp() -> dict:
    """O MCP server é importável (dependência 'mcp' instalada)?"""
    try:
        import redux_token.mcp  # noqa: F401

        return {"name": "MCP server", "status": "ok", "detail": "importável (redux_token.mcp)"}
    except Exception as e:
        return {"name": "MCP server", "status": "warn", "detail": f"indisponível: {e}"}


def run_checks(project_dir: Path | None = None) -> list[dict]:
    return [
        check_core(),
        check_event_log(),
        check_hook(project_dir),
        check_proxy(project_dir),
        check_mcp(),
    ]
