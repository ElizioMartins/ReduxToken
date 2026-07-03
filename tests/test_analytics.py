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
