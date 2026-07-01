from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from redux_token import ReduxToken
from redux_token.utils import estimate_cost_savings

mcp = FastMCP(
    "redux-token",
    instructions=(
        "Compressor inteligente de tokens para LLMs. "
        "Use 'compress' para reduzir texto antes de incluir no contexto, "
        "'compress_file' para comprimir arquivos grandes, "
        "e 'estimate_cost' para calcular economia financeira."
    ),
)

_rt = ReduxToken()


@mcp.tool()
def compress(text: str) -> str:
    """Comprime texto removendo ruído (linhas DEBUG/TRACE, comentários, metadados JSON,
    duplicatas) antes de incluir no contexto do modelo. Economiza 60-97% de tokens."""
    compressed, stats = _rt.compress(text)
    lines = [compressed]
    if stats.tokens_saved > 0:
        lines.append(f"\n[redux-token] {stats.tokens_saved} tokens economizados ({stats.savings_pct:.1f}%)")
    return "\n".join(lines)


@mcp.tool()
def compress_file(path: str) -> str:
    """Lê um arquivo do disco e comprime seu conteúdo. Útil para logs, JSONs e
    código-fonte grandes antes de incluir no contexto."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        return f"Erro ao ler arquivo: {e}"
    compressed, stats = _rt.compress(text)
    lines = [compressed]
    if stats.tokens_saved > 0:
        lines.append(f"\n[redux-token] {stats.tokens_saved} tokens economizados ({stats.savings_pct:.1f}%) — arquivo: {path}")
    return "\n".join(lines)


@mcp.tool()
def estimate_cost(
    original_tokens: int,
    compressed_tokens: int,
    price_per_1k: float = 0.003,
) -> str:
    """Calcula a economia financeira entre dois volumes de tokens.
    price_per_1k é o custo por 1000 tokens em USD (padrão: $0.003, equivalente ao Claude Sonnet)."""
    if original_tokens <= 0:
        return "original_tokens deve ser maior que zero."
    result = estimate_cost_savings(original_tokens, compressed_tokens, price_per_1k)
    return (
        f"Tokens originais:   {original_tokens:,}\n"
        f"Tokens comprimidos: {compressed_tokens:,}\n"
        f"Custo original:     ${result['original_cost']:.4f}\n"
        f"Custo comprimido:   ${result['compressed_cost']:.4f}\n"
        f"Economia:           ${result['savings']:.4f} ({result['savings_pct']:.1f}%)"
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
