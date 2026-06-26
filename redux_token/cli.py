import typer
from pathlib import Path
from redux_token import ReduxToken
from redux_token.utils import estimate_cost_savings

app = typer.Typer(help="ReduxToken — compressor de tokens para LLMs")
_rt = None


def get_rt() -> ReduxToken:
    global _rt
    if _rt is None:
        _rt = ReduxToken()
    return _rt


@app.command()
def compress(
    text: str = typer.Argument(None, help="Texto a comprimir"),
    file: Path = typer.Option(None, "--file", "-f", help="Arquivo de entrada"),
    output: Path = typer.Option(None, "--output", "-o", help="Arquivo de saída"),
) -> None:
    """Comprime texto, JSON, código ou log."""
    if file:
        content = file.read_text(encoding="utf-8")
    elif text:
        content = text
    else:
        typer.echo("Forneça texto ou --file.", err=True)
        raise typer.Exit(1)

    compressed, stats = get_rt().compress(content)

    if output:
        output.write_text(compressed, encoding="utf-8")
        typer.echo(f"Salvo em {output}")
    else:
        typer.echo(compressed)

    typer.echo(
        f"\n— {stats.tokens_saved} tokens economizados ({stats.savings_pct:.1f}%) "
        f"em {stats.time_ms:.2f}ms",
        err=True,
    )


@app.command()
def cost(
    original: int = typer.Argument(..., help="Tokens originais"),
    compressed: int = typer.Argument(..., help="Tokens comprimidos"),
    price: float = typer.Option(0.003, help="Custo por 1k tokens (USD)"),
) -> None:
    """Estima economia financeira entre dois contagens de tokens."""
    result = estimate_cost_savings(original, compressed, price)
    typer.echo(f"Custo original:     ${result['original_cost']:.4f}")
    typer.echo(f"Custo comprimido:   ${result['compressed_cost']:.4f}")
    typer.echo(f"Economia:           ${result['savings']:.4f} ({result['savings_pct']:.1f}%)")


def main() -> None:
    app()
