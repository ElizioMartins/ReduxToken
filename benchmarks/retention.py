"""
Benchmark de informação preservada — mede que a compressão remove ruído SEM
descartar o conteúdo essencial. 100% determinístico (sem LLM).

Para cada caso definimos:
  - keep: trechos que DEVEM sobreviver (o sinal). Retenção alvo = 100%.
  - drop: ruído que DEVE sumir. Quanto maior a remoção, melhor.

Uso: python benchmarks/retention.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from redux_token import ReduxToken


def build_cases() -> list[dict]:
    log = (
        "[DEBUG] 2024-01-15 10:00:01 - Loading configuration from /etc/app/config.yaml\n"
        "[TRACE] 2024-01-15 10:00:01 - Query: SELECT * FROM users WHERE active = true\n"
        "[DEBUG] 2024-01-15 10:00:02 - Cache miss for key: user_profile_123\n"
        "[INFO]  2024-01-15 10:00:02 - Server initialized successfully\n"
        "[INFO]  2024-01-15 10:00:03 - Ready to accept connections on port 8080\n"
        "[TRACE] 2024-01-15 10:00:04 - JWT token validated for user_id=42\n"
        "[INFO]  2024-01-15 10:00:04 - Response 200 OK sent in 14ms\n"
    )

    payload = json.dumps({
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "created_at": "2024-01-15T10:30:00Z",
        "metadata": {"source": "api", "env": "prod"},
        "name": "Maria Silva",
        "email": "maria@exemplo.com",
        "role": "admin",
        "department": "Engineering",
    })

    code = (
        "/**\n * UserService - handles user logic.\n * @author Engineering Team\n */\n"
        "class UserService {\n"
        "    private static final int MAX_RETRIES = 3; // retry budget\n"
        "    public User getUserById(String userId) {\n"
        "        // Validate input before querying\n"
        "        if (userId == null) return null;\n"
        "        return repository.findById(userId); // Query database\n"
        "    }\n"
        "}\n"
    )

    big_array = json.dumps({
        "users": [{"name": f"user{i}", "role": "member"} for i in range(100)]
    })

    return [
        {
            "name": "Log (app noise)",
            "content": log,
            "keep": [
                "Server initialized successfully",
                "Ready to accept connections",
                "Response 200 OK",
            ],
            "drop": [
                "Loading configuration",
                "Cache miss",
                "JWT token validated",
            ],
        },
        {
            "name": "JSON (metadata-heavy)",
            "content": payload,
            "keep": ["Maria Silva", "maria@exemplo.com", "Engineering", "admin"],
            "drop": ["550e8400", "created_at", "metadata"],
        },
        {
            "name": "Code (comments)",
            "content": code,
            "keep": ["getUserById", "MAX_RETRIES", "repository.findById"],
            "drop": ["Validate input before querying", "Query database", "@author"],
        },
        {
            "name": "JSON (large array)",
            "content": big_array,
            "keep": ['"name"', '"role"', "user0"],
            "drop": ["user99", "user50"],
        },
    ]


def evaluate(cases: list[dict]) -> list[dict]:
    rt = ReduxToken()
    results = []
    for c in cases:
        compressed, stats = rt.compress(c["content"])
        keep = c.get("keep", [])
        drop = c.get("drop", [])
        missing = [k for k in keep if k not in compressed]
        not_removed = [d for d in drop if d in compressed]
        results.append({
            "name": c["name"],
            "retention": (len(keep) - len(missing)) / len(keep) if keep else 1.0,
            "noise_removed": (len(drop) - len(not_removed)) / len(drop) if drop else 1.0,
            "savings_pct": stats.savings_pct,
            "missing": missing,
            "not_removed": not_removed,
        })
    return results


def main() -> None:
    results = evaluate(build_cases())
    header = f"{'Cenario':<24} {'Retencao':>9} {'Ruido rem.':>11} {'Economia':>9}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['name']:<24} {r['retention'] * 100:>8.0f}% "
            f"{r['noise_removed'] * 100:>10.0f}% {r['savings_pct']:>8.1f}%"
        )
    print("-" * len(header))
    avg_ret = sum(r["retention"] for r in results) / len(results)
    avg_noise = sum(r["noise_removed"] for r in results) / len(results)
    print(f"{'MEDIA':<24} {avg_ret * 100:>8.0f}% {avg_noise * 100:>10.0f}%")
    if avg_ret < 1.0:
        print("\nATENCAO: sinal perdido em algum cenario:")
        for r in results:
            if r["missing"]:
                print(f"  {r['name']}: {r['missing']}")


if __name__ == "__main__":
    main()
