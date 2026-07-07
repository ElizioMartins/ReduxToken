"""Testes do PostToolUse hook — extração da saída da ferramenta."""
from redux_token.hook import _extract_text


def test_extract_bash_stdout():
    # Formato real do Claude Code para a ferramenta Bash.
    tr = {"stdout": "saída do comando", "stderr": "", "interrupted": False}
    assert _extract_text(tr) == "saída do comando"


def test_extract_plain_string():
    assert _extract_text("texto direto") == "texto direto"


def test_extract_alternate_keys():
    assert _extract_text({"content": "conteúdo"}) == "conteúdo"
    assert _extract_text({"text": "abc"}) == "abc"


def test_extract_prefers_stdout():
    tr = {"stdout": "principal", "content": "secundário"}
    assert _extract_text(tr) == "principal"


def test_extract_empty_or_unknown():
    assert _extract_text({}) is None
    assert _extract_text({"stderr": "erro"}) is None
    assert _extract_text(None) is None
    assert _extract_text(123) is None
    assert _extract_text({"stdout": ""}) is None  # string vazia não conta
