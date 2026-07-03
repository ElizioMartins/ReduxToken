"""Store reversível de compressão — CCR (Fase 6.1).

Compressão destrutiva perde o conteúdo removido. Com CCR guardamos o original num
store local **content-addressed** e deixamos um marcador ``⟦rdx:<ref>⟧`` no texto
comprimido. Se o modelo precisar do detalhe, recupera via ``retrieve(ref)``.

- Store em disco (``~/.redux-token/reversible/<ref>.txt``), compartilhado entre o proxy
  (Rust) e a lib/MCP (Python) — processos separados sem memória comum.
- ``ref = sha256(original)[:12]`` → dedup automático e **determinístico/auditável**.
- Nunca quebra o chamador: falhas de I/O são engolidas (retorno ``None``/best-effort).

Limite honesto: o ``retrieve`` só é acionável onde há canal de tool (MCP/agente). No
modo proxy puro o marcador é apenas um sinal de que havia conteúdo ali.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from redux_token import telemetry

_REF_LEN = 12
_HEX_RE = re.compile(r"[0-9a-f]{6,64}")
_MARKER_RE = re.compile(r"⟦rdx:([0-9a-f]{6,64})⟧")


def store_dir() -> Path:
    return telemetry.home_dir() / "reversible"


def _dir() -> Path:
    return store_dir()


def ref_for(text: str) -> str:
    """Referência determinística (content-addressed) de um texto."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:_REF_LEN]


def make_marker(ref: str) -> str:
    return f"⟦rdx:{ref}⟧"


def parse_ref(s: str) -> str:
    """Extrai o ref de um marcador ``⟦rdx:ref⟧`` ou devolve a string limpa."""
    m = _MARKER_RE.search(s)
    return m.group(1) if m else s.strip()


def find_refs(text: str) -> list[str]:
    """Todos os refs de marcadores presentes num texto comprimido."""
    return _MARKER_RE.findall(text)


def put(text: str) -> str:
    """Guarda ``text`` no store e devolve o ref. Best-effort (não levanta)."""
    ref = ref_for(text)
    try:
        d = _dir()
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{ref}.txt"
        if not path.exists():  # content-addressed: mesmo conteúdo, mesmo arquivo
            path.write_text(text, encoding="utf-8")
    except Exception:
        pass
    return ref


def get(ref: str) -> str | None:
    """Recupera o original de um ref (ou marcador). ``None`` se não existir."""
    ref = parse_ref(ref)
    if not _HEX_RE.fullmatch(ref):
        return None
    try:
        path = _dir() / f"{ref}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    return None


# Alias semântico usado pela tool MCP e pela API pública.
retrieve = get


def store_stats() -> dict:
    """Contagem e tamanho total do store reversível."""
    d = store_dir()
    files = list(d.glob("*.txt")) if d.exists() else []
    total = 0
    for f in files:
        try:
            total += f.stat().st_size
        except OSError:
            pass
    return {"files": len(files), "bytes": total}


def gc(
    ttl_hours: float | None = 24.0,
    max_mb: float | None = None,
    dry_run: bool = False,
) -> dict:
    """Limpa o store reversível.

    Remove trechos com mais de ``ttl_hours`` (por mtime) e, se ``max_mb`` for dado,
    remove os mais antigos até o store caber no limite. ``dry_run`` só simula.
    """
    import time

    d = store_dir()
    if not d.exists():
        return {"removed": 0, "freed_bytes": 0, "remaining": 0}

    now = time.time()
    files: list[tuple[Path, float, int]] = []  # (path, mtime, size)
    for f in d.glob("*.txt"):
        try:
            st = f.stat()
            files.append((f, st.st_mtime, st.st_size))
        except OSError:
            continue

    doomed: set[Path] = set()

    if ttl_hours is not None:
        cutoff = now - ttl_hours * 3600
        doomed.update(f for f, mtime, _ in files if mtime < cutoff)

    if max_mb is not None:
        limit = max_mb * 1024 * 1024
        survivors = [(f, mtime, size) for f, mtime, size in files if f not in doomed]
        total = sum(size for _, _, size in survivors)
        survivors.sort(key=lambda x: x[1])  # mais antigos primeiro
        i = 0
        while total > limit and i < len(survivors):
            f, _, size = survivors[i]
            doomed.add(f)
            total -= size
            i += 1

    removed = 0
    freed = 0
    for f, _, size in files:
        if f in doomed:
            freed += size
            removed += 1
            if not dry_run:
                try:
                    f.unlink()
                except OSError:
                    freed -= size
                    removed -= 1

    return {"removed": removed, "freed_bytes": freed, "remaining": len(files) - removed}
