"""Testes do event log (Fase 5 — Observabilidade)."""
import json

import pytest

from redux_token import ReduxToken
from redux_token import telemetry


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Redireciona o event log para um diretório temporário."""
    monkeypatch.setenv("REDUX_TOKEN_HOME", str(tmp_path))
    monkeypatch.delenv("REDUX_TOKEN_NO_STATS", raising=False)
    # Reseta o session_id em cache entre os testes.
    telemetry._SESSION_ID = None
    return tmp_path


def _read_events(home):
    path = home / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_compress_records_event(isolated_home):
    rt = ReduxToken(source="lib")
    rt.compress("[DEBUG] a\n[DEBUG] b\nreal line\n=====\nreal line")

    events = _read_events(isolated_home)
    assert len(events) == 1
    ev = events[0]
    assert ev["source"] == "lib"
    assert ev["content_type"] == "log"
    assert ev["original_tokens"] >= ev["compressed_tokens"]
    assert ev["tokens_saved"] == ev["original_tokens"] - ev["compressed_tokens"]
    assert set(ev) == {
        "ts", "source", "content_type", "original_tokens", "compressed_tokens",
        "tokens_saved", "savings_pct", "time_ms", "from_cache", "session_id",
    }


def test_source_is_propagated(isolated_home):
    ReduxToken(source="hook").compress("some text to compress " * 20)
    events = _read_events(isolated_home)
    assert events and events[0]["source"] == "hook"


def test_session_id_is_stable_within_process(isolated_home):
    rt = ReduxToken()
    rt.compress("first payload " * 10)
    rt.compress("second payload " * 10)
    events = _read_events(isolated_home)
    assert len(events) == 2
    assert events[0]["session_id"] == events[1]["session_id"]


def test_opt_out_disables_logging(isolated_home, monkeypatch):
    monkeypatch.setenv("REDUX_TOKEN_NO_STATS", "1")
    ReduxToken().compress("anything at all " * 10)
    assert _read_events(isolated_home) == []


@pytest.mark.parametrize(
    "text,expected",
    [
        ('{"a": 1, "b": [1,2,3]}', "json"),
        ("[DEBUG] loading module", "log"),
        ("def foo():\n    return 1  # comment", "code"),
        ("just a plain sentence with words", "text"),
    ],
)
def test_detect_content_type(text, expected):
    assert telemetry.detect_content_type(text) == expected
