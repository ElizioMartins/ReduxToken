"""Regressão: a compressão nunca deve descartar o sinal essencial (Fase 7.4)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmarks"))

import retention  # noqa: E402


def test_signal_fully_retained():
    results = retention.evaluate(retention.build_cases())
    for r in results:
        assert r["retention"] == 1.0, f"sinal perdido em {r['name']}: {r['missing']}"


def test_noise_is_removed():
    results = retention.evaluate(retention.build_cases())
    # em média, a maior parte do ruído deve sumir
    avg_noise = sum(r["noise_removed"] for r in results) / len(results)
    assert avg_noise >= 0.9, f"remoção de ruído baixa: {avg_noise:.2f}"


def test_real_savings():
    results = retention.evaluate(retention.build_cases())
    assert all(r["savings_pct"] > 0 for r in results)
