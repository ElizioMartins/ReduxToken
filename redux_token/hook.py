"""
Claude Code PostToolUse hook.

Lê o payload JSON do stdin, comprime tool_response se for grande o suficiente,
e escreve o payload modificado no stdout.

Configuração em .claude/settings.json:
  "command": "python -m redux_token.hook"
"""
import json
import sys

# Abaixo deste limite a compressão não compensa o overhead
_MIN_CHARS = 200


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    response = payload.get("tool_response")
    if not isinstance(response, str) or len(response) < _MIN_CHARS:
        sys.exit(0)

    try:
        from redux_token import ReduxToken
        compressed, stats = ReduxToken().compress(response)
        if stats.tokens_saved > 0:
            print(json.dumps({"tool_response": compressed}))
    except Exception:
        # Nunca quebrar o Claude Code — falha silenciosa
        sys.exit(0)


if __name__ == "__main__":
    main()
