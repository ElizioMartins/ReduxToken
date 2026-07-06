"""
Claude Code PreToolUse hook (experimental) — enxuga comandos Bash ruidosos.

Lê o payload da PreToolUse do stdin; se o comando Bash tiver uma reescrita conhecida
(ver ``rewrite.lean_command``), emite ``updatedInput`` para trocá-lo pela versão de
menor saída, além de um contexto explicativo. Nunca bloqueia: se não houver reescrita,
sai em silêncio permitindo o comando original.

Experimental: a troca efetiva do comando depende de o Claude Code em uso suportar
``updatedInput`` no PreToolUse; caso contrário, é um no-op inofensivo.

Configuração em .claude/settings.json:
  "PreToolUse": [{ "matcher": "Bash",
    "hooks": [{ "type": "command", "command": "python -m redux_token.prehook" }] }]
"""
import json
import sys


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str):
        sys.exit(0)

    try:
        from redux_token.rewrite import lean_command

        lean, why = lean_command(command)
    except Exception:
        sys.exit(0)

    if not lean or lean == command:
        sys.exit(0)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {"command": lean},
            "additionalContext": f"[redux-token] '{command}' → '{lean}' ({why})",
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
