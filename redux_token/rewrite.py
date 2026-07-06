"""Reescrita de comandos ruidosos para versões de menor saída (Fase 7.3).

Em vez de comprimir a saída depois (PostToolUse), a ideia aqui é evitar gerar o ruído:
trocar um comando por uma variante equivalente que já produz saída enxuta.

Filosofia deliberadamente **conservadora**: só reescrevemos comandos que batem
exatamente com um padrão conhecido, para nunca alterar a intenção do usuário. Escopo
pequeno de propósito — não é para virar um wrapper de 100 comandos.
"""
from __future__ import annotations

# (comando exato) -> (versão enxuta, motivo). Match exato após strip.
_RULES: dict[str, tuple[str, str]] = {
    "git status": ("git status --short --branch", "formato curto, mesma informação"),
    "git log": ("git log --oneline -30", "uma linha por commit, últimos 30"),
    "npm ls": ("npm ls --depth=0", "só dependências de topo"),
    "npm list": ("npm ls --depth=0", "só dependências de topo"),
    "pip freeze": ("pip list --format=columns", "tabela enxuta"),
}


def lean_command(command: str) -> tuple[str | None, str]:
    """Devolve (comando_enxuto, motivo) ou (None, "") se não houver reescrita segura."""
    if not isinstance(command, str):
        return None, ""
    key = command.strip()
    if key in _RULES:
        lean, why = _RULES[key]
        return lean, why
    return None, ""


def known_commands() -> list[str]:
    return sorted(_RULES)
