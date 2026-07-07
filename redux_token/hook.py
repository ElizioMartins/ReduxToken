"""
Claude Code PostToolUse hook.

Lê o payload JSON do stdin e, se a saída da ferramenta for grande o suficiente,
comprime para medir/registrar a economia no event log (fonte ``hook``), alimentando
``redux-token gain``/``discover``.

O campo ``tool_response`` varia por ferramenta: no Bash é um objeto
(``{"stdout": ...}``); em outras pode ser string. ``_extract_text`` normaliza isso.

Configuração em .claude/settings.json:
  "command": "python -m redux_token.hook"
"""
import json
import sys

# Abaixo deste limite a compressão não compensa o overhead
_MIN_CHARS = 200


def _extract_text(tool_response) -> str | None:
    """Extrai o texto da saída da ferramenta, cobrindo os formatos conhecidos."""
    if isinstance(tool_response, str):
        return tool_response
    if isinstance(tool_response, dict):
        for key in ("stdout", "content", "text", "output", "result", "file"):
            value = tool_response.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    text = _extract_text(payload.get("tool_response"))
    if not text or len(text) < _MIN_CHARS:
        sys.exit(0)

    try:
        from redux_token import ReduxToken

        # Registra a economia potencial no event log (fonte 'hook').
        ReduxToken(source="hook").compress(text)
    except Exception:
        # Nunca quebrar o Claude Code — falha silenciosa
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
