"""Testes do health check (redux-token doctor)."""
import json

import pytest

from redux_token import doctor


def test_check_core_ok():
    r = doctor.check_core()
    assert r["status"] == "ok"


def test_check_event_log_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("REDUX_TOKEN_HOME", str(tmp_path))
    monkeypatch.delenv("REDUX_TOKEN_NO_STATS", raising=False)
    r = doctor.check_event_log()
    assert r["status"] == "ok"


def test_check_event_log_disabled(monkeypatch):
    monkeypatch.setenv("REDUX_TOKEN_NO_STATS", "1")
    r = doctor.check_event_log()
    assert r["status"] == "warn" and "desligado" in r["detail"]


def test_check_hook_missing(tmp_path):
    r = doctor.check_hook(project_dir=tmp_path)
    assert r["status"] == "warn"


def test_check_hook_configured(tmp_path):
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text(
        json.dumps({"hooks": {"PostToolUse": [{"hooks": [{"command": "python -m redux_token.hook"}]}]}}),
        encoding="utf-8",
    )
    r = doctor.check_hook(project_dir=tmp_path)
    assert r["status"] == "ok"


def test_check_proxy_down(tmp_path):
    # Sem proxy rodando → warn (opcional), nunca fail.
    r = doctor.check_proxy(project_dir=tmp_path)
    assert r["status"] == "warn"


def test_check_mcp():
    r = doctor.check_mcp()
    assert r["status"] in ("ok", "warn")  # depende de 'mcp' estar instalado


def test_run_checks_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("REDUX_TOKEN_HOME", str(tmp_path))
    checks = doctor.run_checks(project_dir=tmp_path)
    assert len(checks) == 5
    assert all({"name", "status", "detail"} <= set(c) for c in checks)
