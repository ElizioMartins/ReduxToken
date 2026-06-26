"""
Testes de integração — validam a cadeia completa Python → Rust → Python.
Requerem `maturin develop` executado antes.
"""
import json
import pytest
from redux_token import ReduxToken, CompressionStats
from redux_token.utils import estimate_cost_savings


@pytest.fixture(scope="module")
def rt() -> ReduxToken:
    return ReduxToken()


# ---------------------------------------------------------------------------
# Contrato da interface Python
# ---------------------------------------------------------------------------

class TestInterface:
    def test_compress_returns_tuple(self, rt):
        result = rt.compress("hello world")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_compress_returns_string_and_stats(self, rt):
        text, stats = rt.compress("hello world")
        assert isinstance(text, str)
        assert isinstance(stats, CompressionStats)

    def test_stats_fields_exist(self, rt):
        _, stats = rt.compress("hello world")
        assert hasattr(stats, "original_tokens")
        assert hasattr(stats, "compressed_tokens")
        assert hasattr(stats, "tokens_saved")
        assert hasattr(stats, "savings_pct")
        assert hasattr(stats, "time_ms")

    def test_stats_types(self, rt):
        _, stats = rt.compress("hello world")
        assert isinstance(stats.original_tokens, int)
        assert isinstance(stats.compressed_tokens, int)
        assert isinstance(stats.tokens_saved, int)
        assert isinstance(stats.savings_pct, float)
        assert isinstance(stats.time_ms, float)

    def test_empty_string_does_not_crash(self, rt):
        text, stats = rt.compress("")
        assert isinstance(text, str)
        assert stats.original_tokens >= 0


# ---------------------------------------------------------------------------
# TextFilter — remove DEBUG/TRACE
# ---------------------------------------------------------------------------

class TestTextFilter:
    def test_removes_debug_lines(self, rt):
        log = "[DEBUG] loading config\n[INFO] server started\n"
        compressed, _ = rt.compress(log)
        assert "[DEBUG]" not in compressed
        assert "[INFO]" in compressed

    def test_removes_trace_lines(self, rt):
        log = "[TRACE] query executed\n[INFO] done\n"
        compressed, _ = rt.compress(log)
        assert "[TRACE]" not in compressed

    def test_reduces_token_count(self, rt):
        noisy = "\n".join(["[DEBUG] noise"] * 20 + ["[INFO] signal"])
        _, stats = rt.compress(noisy)
        assert stats.compressed_tokens < stats.original_tokens


# ---------------------------------------------------------------------------
# CodeFilter — remove comentários
# ---------------------------------------------------------------------------

class TestCodeFilter:
    def test_removes_line_comments(self, rt):
        code = "x = 1  // increment x\ny = 2\n"
        compressed, _ = rt.compress(code)
        assert "increment x" not in compressed
        assert "y = 2" in compressed

    def test_removes_block_comments(self, rt):
        code = "fn foo() {\n    /* setup */\n    return 1;\n}\n"
        compressed, _ = rt.compress(code)
        assert "setup" not in compressed
        assert "return 1" in compressed


# ---------------------------------------------------------------------------
# JsonFilter — remove campos irrelevantes
# ---------------------------------------------------------------------------

class TestJsonFilter:
    def test_removes_id_field(self, rt):
        payload = json.dumps({"id": "abc-123", "name": "Alice"})
        compressed, _ = rt.compress(payload)
        data = json.loads(compressed)
        assert "id" not in data
        assert data["name"] == "Alice"

    def test_removes_timestamps(self, rt):
        payload = json.dumps({
            "created_at": "2024-01-01",
            "updated_at": "2024-01-02",
            "title": "hello",
        })
        compressed, _ = rt.compress(payload)
        data = json.loads(compressed)
        assert "created_at" not in data
        assert "updated_at" not in data
        assert data["title"] == "hello"

    def test_removes_metadata(self, rt):
        payload = json.dumps({"metadata": {"source": "api"}, "value": 42})
        compressed, _ = rt.compress(payload)
        data = json.loads(compressed)
        assert "metadata" not in data
        assert data["value"] == 42

    def test_passthrough_non_json(self, rt):
        text = "this is plain text, not json"
        compressed, _ = rt.compress(text)
        assert "plain text" in compressed

    def test_jsonl_each_line_processed(self, rt):
        lines = [
            json.dumps({"id": "1", "msg": "a"}),
            json.dumps({"id": "2", "msg": "b"}),
        ]
        jsonl = "\n".join(lines)
        compressed, _ = rt.compress(jsonl)
        for line in compressed.strip().splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            assert "id" not in data
            assert "msg" in data


# ---------------------------------------------------------------------------
# SmartFilter — separadores e deduplicação
# ---------------------------------------------------------------------------

class TestSmartFilter:
    def test_removes_separator_lines(self, rt):
        text = "header\n==============================\ncontent\n"
        compressed, _ = rt.compress(text)
        assert "===" not in compressed
        assert "content" in compressed

    def test_deduplicates_lines(self, rt):
        text = "status: ok\nstatus: ok\nstatus: ok\ndone\n"
        compressed, _ = rt.compress(text)
        lines = [l for l in compressed.splitlines() if l.strip()]
        assert lines.count("status: ok") == 1
        assert "done" in compressed


# ---------------------------------------------------------------------------
# CompressionStats — invariantes matemáticos
# ---------------------------------------------------------------------------

class TestStats:
    def test_tokens_saved_is_consistent(self, rt):
        _, stats = rt.compress("[DEBUG] x\n" * 50)
        assert stats.tokens_saved == stats.original_tokens - stats.compressed_tokens

    def test_savings_pct_range(self, rt):
        _, stats = rt.compress("[DEBUG] noise\n" * 30 + "[INFO] signal\n")
        assert 0.0 <= stats.savings_pct <= 100.0

    def test_time_ms_positive(self, rt):
        _, stats = rt.compress("some text")
        assert stats.time_ms >= 0.0


# ---------------------------------------------------------------------------
# utils — estimate_cost_savings
# ---------------------------------------------------------------------------

class TestEstimateCostSavings:
    def test_basic_calculation(self):
        result = estimate_cost_savings(1000, 800, cost_per_1k=0.01)
        assert result["original_cost"] == pytest.approx(0.01)
        assert result["compressed_cost"] == pytest.approx(0.008)
        assert result["savings"] == pytest.approx(0.002)
        assert result["savings_pct"] == pytest.approx(20.0)

    def test_zero_original_tokens(self):
        result = estimate_cost_savings(0, 0)
        assert result["savings_pct"] == 0.0

    def test_no_compression(self):
        result = estimate_cost_savings(500, 500)
        assert result["savings"] == pytest.approx(0.0)
        assert result["savings_pct"] == pytest.approx(0.0)

    def test_full_compression(self):
        result = estimate_cost_savings(1000, 0)
        assert result["savings_pct"] == pytest.approx(100.0)
