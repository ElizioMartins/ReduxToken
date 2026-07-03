"""Testes do store reversível / CCR (Fase 6.1)."""
import pytest

from redux_token import ReduxToken, reversible


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("REDUX_TOKEN_HOME", str(tmp_path))
    monkeypatch.delenv("REDUX_TOKEN_NO_STATS", raising=False)
    return tmp_path


def test_ref_is_deterministic():
    assert reversible.ref_for("olá mundo") == reversible.ref_for("olá mundo")
    assert reversible.ref_for("a") != reversible.ref_for("b")


def test_put_get_roundtrip(isolated_home):
    original = "// comentário importante\nlinha de código"
    ref = reversible.put(original)
    assert reversible.get(ref) == original


def test_get_unknown_ref_is_none(isolated_home):
    assert reversible.get("deadbeefcafe") is None


def test_get_invalid_ref_is_none(isolated_home):
    assert reversible.get("não-é-hex") is None


def test_marker_roundtrip():
    ref = "a1b2c3d4e5f6"
    marker = reversible.make_marker(ref)
    assert marker == "⟦rdx:a1b2c3d4e5f6⟧"
    assert reversible.parse_ref(marker) == ref
    assert reversible.parse_ref(f"texto antes {marker} depois") == ref


def test_find_refs():
    text = "a ⟦rdx:aaaaaa⟧ b ⟦rdx:bbbbbb⟧"
    assert reversible.find_refs(text) == ["aaaaaa", "bbbbbb"]


def test_dedup_same_content_same_file(isolated_home):
    r1 = reversible.put("mesmo conteúdo")
    r2 = reversible.put("mesmo conteúdo")
    assert r1 == r2
    files = list((isolated_home / "reversible").glob("*.txt"))
    assert len(files) == 1


def test_retrieve_alias(isolated_home):
    ref = reversible.put("conteúdo x")
    assert reversible.retrieve(ref) == "conteúdo x"


def test_reversible_compress_appends_marker_and_roundtrips(isolated_home):
    rt = ReduxToken(reversible=True)
    original = "[DEBUG] x\n" * 20 + "linha real que fica"
    compressed, stats = rt.compress(original)
    assert stats.tokens_saved > 0
    refs = reversible.find_refs(compressed)
    assert len(refs) == 1
    # o marcador recupera exatamente o texto original passado ao compress
    assert reversible.get(refs[0]) == original


def test_non_reversible_compress_has_no_marker(isolated_home):
    rt = ReduxToken(reversible=False)
    compressed, _ = rt.compress("[DEBUG] x\n" * 20 + "fica")
    assert reversible.find_refs(compressed) == []
