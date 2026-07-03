"""Testes da camada de leitura/agregação do event log (redux-token gain)."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from redux_token import analytics


def _ev(ts: datetime, source="cli", ctype="log", orig=100, comp=20, cache=False) -> dict:
    return {
        "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "content_type": ctype,
        "original_tokens": orig,
        "compressed_tokens": comp,
        "tokens_saved": orig - comp,
        "savings_pct": (orig - comp) / orig * 100,
        "time_ms": 1.0,
        "from_cache": cache,
        "session_id": "s1",
    }


@pytest.fixture
def log(tmp_path):
    def _write(events):
        p = tmp_path / "events.jsonl"
        p.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
        return p
    return _write


def test_load_ignores_corrupt_lines(tmp_path):
    p = tmp_path / "events.jsonl"
    p.write_text('{"a":1}\nnot json\n{"b":2}\n', encoding="utf-8")
    assert analytics.load_events(p) == [{"a": 1}, {"b": 2}]


def test_load_missing_file_is_empty(tmp_path):
    assert analytics.load_events(tmp_path / "nope.jsonl") == []


@pytest.mark.parametrize("spec,seconds", [("24h", 86400), ("7d", 604800), ("30m", 1800), ("2w", 1209600)])
def test_parse_since(spec, seconds):
    assert analytics.parse_since(spec) == timedelta(seconds=seconds)


def test_parse_since_all_is_none():
    assert analytics.parse_since("all") is None


def test_parse_since_invalid():
    with pytest.raises(ValueError):
        analytics.parse_since("banana")


def test_filter_since():
    now = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
    events = [
        _ev(now - timedelta(days=1)),
        _ev(now - timedelta(days=10)),
    ]
    kept = analytics.filter_since(events, timedelta(days=7), now=now)
    assert len(kept) == 1


def test_aggregate():
    events = [_ev(datetime.now(timezone.utc), orig=100, comp=20, cache=True),
              _ev(datetime.now(timezone.utc), orig=200, comp=50)]
    agg = analytics.aggregate(events)
    assert agg["events"] == 2
    assert agg["original_tokens"] == 300
    assert agg["tokens_saved"] == 230
    assert agg["cache_hits"] == 1
    assert round(agg["reduction_pct"], 1) == round(230 / 300 * 100, 1)


def test_by_day_is_chronological():
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    events = [_ev(base + timedelta(days=2)), _ev(base), _ev(base + timedelta(days=1))]
    days = analytics.by_day(events)
    assert list(days.keys()) == ["2026-07-01", "2026-07-02", "2026-07-03"]


def test_by_field_sorted_desc():
    events = [_ev(datetime.now(timezone.utc), source="cli", orig=100, comp=90),
              _ev(datetime.now(timezone.utc), source="proxy", orig=1000, comp=100)]
    ranked = analytics.by_field(events, "source")
    assert list(ranked.keys())[0] == "proxy"  # maior economia primeiro


def test_aggregate_empty():
    agg = analytics.aggregate([])
    assert agg["events"] == 0 and agg["reduction_pct"] == 0.0


@pytest.mark.parametrize("values,expected_len", [([], 0), ([5], 1), ([1, 2, 3, 4], 4)])
def test_sparkline_length(values, expected_len):
    assert len(analytics.sparkline(values)) == expected_len


def test_sparkline_flat():
    assert analytics.sparkline([7, 7, 7]) == "▅▅▅"


@pytest.mark.parametrize("n,expected", [(1234567, "1.23M"), (3700, "3.70K"), (500, "500")])
def test_human_number(n, expected):
    assert analytics.human_number(n) == expected


def _evs(sid, ts, source, n):
    return [
        {**_ev(ts, source=source), "session_id": sid}
        for _ in range(n)
    ]


def test_session_summaries_most_recent_first():
    old = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    new = datetime(2026, 7, 3, 15, 30, tzinfo=timezone.utc)
    events = (
        _evs("2026-07-01T10:00:00Z-aaaa", old, "cli", 2)
        + _evs("2026-07-03T15:30:00Z-bbbb", new, "hook", 5)
    )
    sessions = analytics.session_summaries(events)
    assert [s["short_id"] for s in sessions] == ["bbbb", "aaaa"]
    assert sessions[0]["events"] == 5
    assert sessions[0]["source"] == "hook"
    assert sessions[0]["start_str"] == "2026-07-03 15:30"


def test_session_dominant_source():
    ts = datetime(2026, 7, 3, tzinfo=timezone.utc)
    events = _evs("s-cccc", ts, "proxy", 3) + _evs("s-cccc", ts, "cli", 1)
    sessions = analytics.session_summaries(events)
    assert len(sessions) == 1
    assert sessions[0]["source"] == "proxy"  # dominante
    assert sessions[0]["events"] == 4


def test_by_field_count():
    ts = datetime(2026, 7, 3, tzinfo=timezone.utc)
    events = _evs("s", ts, "cli", 3) + _evs("s", ts, "hook", 1)
    counts = analytics.by_field_count(events, "source")
    assert list(counts.items())[0] == ("cli", 3)


# --- discover ---------------------------------------------------------------

def test_discover_empty():
    assert analytics.discover([]) == []


def test_discover_low_return_source():
    now = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
    # 10 eventos 'cli' com economia baixa (100→95 = 5%)
    events = [{**_ev(now, source="cli", orig=100, comp=95), "session_id": "s"} for _ in range(10)]
    findings = analytics.discover(events, now=now)
    assert any(f["level"] == "warn" and "'cli'" in f["title"] for f in findings)


def test_discover_silent_source():
    now = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
    old = now - timedelta(hours=72)  # além das 48h
    events = [{**_ev(old, source="proxy", orig=100, comp=20), "session_id": "s"} for _ in range(6)]
    findings = analytics.discover(events, now=now)
    assert any(f["level"] == "warn" and "48h" in f["title"] for f in findings)


def test_discover_high_yield_low_volume():
    now = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
    # 'text' domina o volume; 'log' rende muito mas é pouco volume
    bulk = [{**_ev(now, source="cli", ctype="text", orig=1000, comp=300), "session_id": "s"} for _ in range(10)]
    logs = [{**_ev(now, source="hook", ctype="log", orig=100, comp=3), "session_id": "s"} for _ in range(4)]
    findings = analytics.discover(bulk + logs, now=now)
    assert any(f["level"] == "tip" and "'log'" in f["title"] for f in findings)


def test_discover_cache_underused():
    now = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
    events = [{**_ev(now, source="proxy", orig=100, comp=20, cache=False), "session_id": "s"} for _ in range(40)]
    findings = analytics.discover(events, now=now)
    assert any(f["level"] == "tip" and "Cache" in f["title"] for f in findings)


def test_report_reads_event_log(tmp_path, monkeypatch):
    monkeypatch.setenv("REDUX_TOKEN_HOME", str(tmp_path))
    ts = datetime.now(timezone.utc)
    log = tmp_path / "events.jsonl"
    log.write_text(
        "\n".join(json.dumps({**_ev(ts, source=s), "session_id": "s"}) for s in ("proxy", "hook")) + "\n",
        encoding="utf-8",
    )
    from typer.testing import CliRunner
    from redux_token.cli import app

    out = tmp_path / "STATS.md"
    result = CliRunner().invoke(app, ["report", "--output", str(out)])
    assert result.exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "Economia por fonte" in content
    assert "**proxy**" in content and "**hook**" in content


def test_discover_healthy_data_no_false_positives():
    now = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
    # boa economia, recente, cache saudável, volume equilibrado
    events = [{**_ev(now, source="proxy", ctype="json", orig=1000, comp=300, cache=True), "session_id": "s"} for _ in range(20)]
    findings = analytics.discover(events, now=now)
    assert findings == []
