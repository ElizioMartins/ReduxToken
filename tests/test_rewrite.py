"""Testes do motor de reescrita e do PreToolUse hook (Fase 7.3)."""
import json
import subprocess
import sys

import pytest

from redux_token.rewrite import lean_command, known_commands


@pytest.mark.parametrize("cmd,expected", [
    ("git status", "git status --short --branch"),
    ("  git status  ", "git status --short --branch"),  # tolera espaços
    ("git log", "git log --oneline -30"),
    ("npm ls", "npm ls --depth=0"),
    ("npm list", "npm ls --depth=0"),
])
def test_lean_rewrites_known(cmd, expected):
    new, why = lean_command(cmd)
    assert new == expected and why


@pytest.mark.parametrize("cmd", [
    "git status --porcelain",  # já tem flags → não mexe
    "git status src/",          # tem argumento → não mexe
    "rm -rf /",                 # desconhecido
    "",
])
def test_lean_leaves_unknown(cmd):
    assert lean_command(cmd) == (None, "")


def test_lean_non_string():
    assert lean_command(None) == (None, "")


def test_known_commands_sorted():
    assert known_commands() == sorted(known_commands())


def _run_prehook(payload: dict) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "redux_token.prehook"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout


def test_prehook_rewrites_bash_command():
    code, out = _run_prehook({"tool_name": "Bash", "tool_input": {"command": "git status"}})
    assert code == 0
    data = json.loads(out)
    hso = data["hookSpecificOutput"]
    assert hso["updatedInput"]["command"] == "git status --short --branch"
    assert hso["permissionDecision"] == "allow"


def test_prehook_noop_on_unknown_command():
    code, out = _run_prehook({"tool_name": "Bash", "tool_input": {"command": "make build"}})
    assert code == 0 and out.strip() == ""


def test_prehook_ignores_non_bash():
    code, out = _run_prehook({"tool_name": "Read", "tool_input": {"file_path": "x"}})
    assert code == 0 and out.strip() == ""


def test_prehook_survives_garbage_input():
    proc = subprocess.run(
        [sys.executable, "-m", "redux_token.prehook"],
        input="not json",
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
