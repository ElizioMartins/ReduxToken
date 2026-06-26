def estimate_cost_savings(
    original_tokens: int,
    compressed_tokens: int,
    cost_per_1k: float = 0.003,
) -> dict:
    original_cost = original_tokens * cost_per_1k / 1000
    compressed_cost = compressed_tokens * cost_per_1k / 1000
    savings = original_cost - compressed_cost
    savings_pct = (savings / original_cost * 100) if original_cost > 0 else 0.0
    return {
        "original_cost": original_cost,
        "compressed_cost": compressed_cost,
        "savings": savings,
        "savings_pct": savings_pct,
    }
