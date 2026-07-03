"""Leitura e agregação do event log (Fase 5 — Observabilidade).

Camada de *leitura* sobre ``~/.redux-token/events.jsonl`` (escrito por
``telemetry.py`` e pelo proxy). Alimenta os comandos ``gain``/``session``/``discover``.
Puro Python, sem dependências — inclui um sparkline ASCII e formatação humana.
"""
from __future__ import annotations

import json
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from redux_token import telemetry

_BLOCKS = "▁▂▃▄▅▆▇█"


def load_events(path: Path | None = None) -> list[dict]:
    """Carrega todos os eventos válidos do log. Ignora linhas corrompidas."""
    path = path or telemetry.log_path()
    if not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except (ValueError, TypeError):
            continue
    return events


def parse_since(spec: str) -> timedelta | None:
    """Converte '24h' / '7d' / '30m' / 'all' em timedelta. 'all' → None (sem corte)."""
    spec = spec.strip().lower()
    if spec in ("all", "todos", ""):
        return None
    unit = spec[-1]
    factor = {"m": 60, "h": 3600, "d": 86400, "w": 604800}.get(unit)
    if factor is None:
        raise ValueError(f"intervalo inválido: {spec!r} (use ex.: 24h, 7d, 30d, all)")
    try:
        value = float(spec[:-1])
    except ValueError as e:
        raise ValueError(f"intervalo inválido: {spec!r}") from e
    return timedelta(seconds=value * factor)


def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def filter_since(events: list[dict], since: timedelta | None, now: datetime | None = None) -> list[dict]:
    if since is None:
        return events
    now = now or datetime.now(timezone.utc)
    cutoff = now - since
    out = []
    for ev in events:
        ts = _parse_ts(ev.get("ts", ""))
        if ts is not None and ts >= cutoff:
            out.append(ev)
    return out


def aggregate(events: list[dict]) -> dict:
    """Totais gerais sobre uma lista de eventos."""
    original = sum(int(e.get("original_tokens", 0)) for e in events)
    compressed = sum(int(e.get("compressed_tokens", 0)) for e in events)
    saved = sum(int(e.get("tokens_saved", 0)) for e in events)
    cache_hits = sum(1 for e in events if e.get("from_cache"))
    reduction = (saved / original * 100) if original > 0 else 0.0
    return {
        "events": len(events),
        "cache_hits": cache_hits,
        "original_tokens": original,
        "compressed_tokens": compressed,
        "tokens_saved": saved,
        "reduction_pct": reduction,
    }


def by_day(events: list[dict]) -> "OrderedDict[str, int]":
    """tokens economizados por dia (YYYY-MM-DD), ordenado cronologicamente."""
    buckets: dict[str, int] = defaultdict(int)
    for e in events:
        ts = _parse_ts(e.get("ts", ""))
        if ts is None:
            continue
        buckets[ts.strftime("%Y-%m-%d")] += int(e.get("tokens_saved", 0))
    return OrderedDict(sorted(buckets.items()))


def by_field(events: list[dict], field: str) -> "OrderedDict[str, int]":
    """tokens economizados agrupados por um campo (source/content_type), desc."""
    buckets: dict[str, int] = defaultdict(int)
    for e in events:
        buckets[str(e.get(field, "?"))] += int(e.get("tokens_saved", 0))
    return OrderedDict(sorted(buckets.items(), key=lambda kv: kv[1], reverse=True))


def sparkline(values: list[int]) -> str:
    """Mini-gráfico ASCII usando blocos unicode."""
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return _BLOCKS[len(_BLOCKS) // 2] * len(values)
    span = hi - lo
    return "".join(_BLOCKS[int((v - lo) / span * (len(_BLOCKS) - 1))] for v in values)


def human_number(n: float) -> str:
    """1234567 → '1.23M', 3700 → '3.70K'."""
    n = float(n)
    for threshold, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= threshold:
            return f"{n / threshold:.2f}{suffix}"
    return f"{int(n)}"
