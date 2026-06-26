"""Exemplo básico de uso do ReduxToken."""
from redux_token import ReduxToken
from redux_token.utils import estimate_cost_savings

rt = ReduxToken()

# --- Exemplo 1: log com ruído ---
log = """
[DEBUG] loading configuration file
[DEBUG] connecting to database
[TRACE] query: SELECT * FROM users
[INFO] Server started on port 8000
==============================
[DEBUG] health check passed
[DEBUG] health check passed
[INFO] Ready to accept connections
==============================
"""

compressed, stats = rt.compress(log)
print("=== Log ===")
print(f"Original:   {stats.original_tokens} tokens")
print(f"Comprimido: {stats.compressed_tokens} tokens ({stats.savings_pct:.1f}% menos)")
print(f"\n{compressed}\n")

# --- Exemplo 2: JSON com campos irrelevantes ---
import json

payload = json.dumps({
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "metadata": {"source": "api", "version": 3},
    "name": "Maria Silva",
    "email": "maria@exemplo.com",
    "role": "admin",
})

compressed, stats = rt.compress(payload)
print("=== JSON ===")
print(f"Original:   {stats.original_tokens} tokens")
print(f"Comprimido: {stats.compressed_tokens} tokens ({stats.savings_pct:.1f}% menos)")
print(f"\n{compressed}\n")

# --- Exemplo 3: estimativa de custo ---
costs = estimate_cost_savings(
    original_tokens=stats.original_tokens,
    compressed_tokens=stats.compressed_tokens,
    cost_per_1k=0.003,
)
print(f"Economia estimada: ${costs['savings']:.6f} USD ({costs['savings_pct']:.1f}%)")
