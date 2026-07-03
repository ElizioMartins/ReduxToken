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


def _dir() -> Path:
    return telemetry.home_dir() / "reversible"


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
