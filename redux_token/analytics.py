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


def session_summaries(events: list[dict]) -> list[dict]:
    """Uma linha por ``session_id``, mais recente primeiro. Base do comando ``session``."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        groups[str(e.get("session_id", "?"))].append(e)

    summaries = []
    for sid, evs in groups.items():
        agg = aggregate(evs)
        starts = [ts for ts in (_parse_ts(e.get("ts", "")) for e in evs) if ts is not None]
        start = min(starts) if starts else None
        # fonte dominante (a que mais aparece na sessão)
        source = by_field_count(evs, "source")
        top_source = next(iter(source), "?")
        summaries.append({
            "session_id": sid,
            "short_id": sid.rsplit("-", 1)[-1] if "-" in sid else sid[:8],
            "start": start,
            "start_str": start.strftime("%Y-%m-%d %H:%M") if start else "?",
            "source": top_source,
            "events": agg["events"],
            "tokens_saved": agg["tokens_saved"],
            "reduction_pct": agg["reduction_pct"],
        })
    _floor = datetime.min.replace(tzinfo=timezone.utc)
    summaries.sort(key=lambda s: s["start"] or _floor, reverse=True)
    return summaries


def by_field_count(events: list[dict], field: str) -> "OrderedDict[str, int]":
    """Contagem de eventos por valor de um campo, desc (≠ by_field, que soma tokens)."""
    buckets: dict[str, int] = defaultdict(int)
    for e in events:
        buckets[str(e.get(field, "?"))] += 1
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


# Limiares das regras do 'discover' (constantes p/ facilitar teste/calibração).
LOW_RETURN_PCT = 20.0       # abaixo disso, a compressão quase não compensa
LOW_RETURN_SHARE = 0.15     # ...e a fonte representa parcela relevante dos eventos
SILENT_HOURS = 48           # fonte que sumiu nas últimas N horas
HIGH_YIELD_PCT = 80.0       # tipo de conteúdo com ótimo retorno
LOW_VOLUME_SHARE = 0.20     # ...mas pouco volume — oportunidade de captura
CACHE_MIN_EVENTS = 30       # só avalia cache do proxy com volume mínimo
CACHE_LOW_RATIO = 0.10      # taxa de cache hit considerada baixa


def discover(events: list[dict], now: datetime | None = None) -> list[dict]:
    """Regras determinísticas que apontam oportunidades perdidas. Base do ``discover``.

    Cada achado é ``{"level": "warn"|"tip", "title": str, "detail": str}``.
    """
    now = now or datetime.now(timezone.utc)
    findings: list[dict] = []
    if not events:
        return findings

    total_events = len(events)
    total_saved = sum(int(e.get("tokens_saved", 0)) for e in events)

    by_src: dict[str, list[dict]] = defaultdict(list)
    by_type: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        by_src[str(e.get("source", "?"))].append(e)
        by_type[str(e.get("content_type", "?"))].append(e)

    # Regra 1 — fonte com retorno consistentemente baixo.
    for src, evs in by_src.items():
        share = len(evs) / total_events
        agg = aggregate(evs)
        if len(evs) >= 5 and share >= LOW_RETURN_SHARE and agg["reduction_pct"] < LOW_RETURN_PCT:
            findings.append({
                "level": "warn",
                "title": f"{share * 100:.0f}% dos eventos vêm de '{src}' com economia < {LOW_RETURN_PCT:.0f}%.",
                "detail": "Esse conteúdo casa mal com os filtros; considere pular compressão de trechos curtos.",
            })

    # Regra 2 — fonte que parou de reportar (tinha eventos antigos, nenhum recente).
    cutoff = now - timedelta(hours=SILENT_HOURS)
    for src, evs in by_src.items():
        ts_list = [ts for ts in (_parse_ts(e.get("ts", "")) for e in evs) if ts is not None]
        if len(evs) >= 5 and ts_list and max(ts_list) < cutoff:
            findings.append({
                "level": "warn",
                "title": f"Nenhum evento de '{src}' nas últimas {SILENT_HOURS}h.",
                "detail": "Essa integração pode ter caído. Rode 'redux-token doctor'.",
            })

    # Regra 3 — tipo de alto retorno mas baixo volume (vale capturar mais).
    for ctype, evs in by_type.items():
        agg = aggregate(evs)
        share = (agg["tokens_saved"] / total_saved) if total_saved else 0.0
        if len(evs) >= 3 and agg["reduction_pct"] >= HIGH_YIELD_PCT and share < LOW_VOLUME_SHARE:
            findings.append({
                "level": "tip",
                "title": f"'{ctype}' rende {agg['reduction_pct']:.0f}% mas é só {share * 100:.0f}% do volume.",
                "detail": "Ative o hook no seu agente para capturar mais desse conteúdo automaticamente.",
            })

    # Regra 4 — cache do proxy subutilizado.
    proxy_evs = by_src.get("proxy", [])
    if len(proxy_evs) >= CACHE_MIN_EVENTS:
        hits = sum(1 for e in proxy_evs if e.get("from_cache"))
        ratio = hits / len(proxy_evs)
        if ratio < CACHE_LOW_RATIO:
            findings.append({
                "level": "tip",
                "title": f"Cache do proxy em {ratio * 100:.0f}% de hits ({len(proxy_evs)} requests).",
                "detail": "Conteúdo repetido não está reaproveitando o cache — verifique variação nos prompts.",
            })

    return findings


def human_number(n: float) -> str:
    """1234567 → '1.23M', 3700 → '3.70K'."""
    n = float(n)
    for threshold, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= threshold:
            return f"{n / threshold:.2f}{suffix}"
    return f"{int(n)}"
