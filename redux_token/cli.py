import sys
import time
import json
import urllib.request
from pathlib import Path

import typer
from redux_token import ReduxToken
from redux_token.utils import estimate_cost_savings

app = typer.Typer(help="ReduxToken — compressor de tokens para LLMs")
_rt = None


def get_rt() -> ReduxToken:
    global _rt
    if _rt is None:
        _rt = ReduxToken(source="cli")
    return _rt


@app.command()
def compress(
    text: str = typer.Argument(None, help="Texto a comprimir"),
    file: Path = typer.Option(None, "--file", "-f", help="Arquivo de entrada"),
    output: Path = typer.Option(None, "--output", "-o", help="Arquivo de saída"),
) -> None:
    """Comprime texto, JSON, código ou log. Aceita stdin quando não há argumento."""
    if file:
        content = file.read_text(encoding="utf-8")
    elif text:
        content = text
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        typer.echo("Forneça texto, --file, ou pipe de stdin.", err=True)
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


@app.command()
def watch(
    file: Path = typer.Argument(..., help="Arquivo a monitorar"),
    output: Path = typer.Option(None, "--output", "-o", help="Saída (padrão: <nome>.compressed<ext>)"),
    interval: float = typer.Option(1.0, "--interval", "-i", help="Intervalo de verificação em segundos"),
) -> None:
    """Monitora um arquivo e comprime automaticamente ao detectar mudanças."""
    out = output or file.with_name(file.stem + ".compressed" + file.suffix)
    rt = get_rt()
    last_mtime: float | None = None

    typer.echo(f"Monitorando: {file}")
    typer.echo(f"Saída:       {out}")
    typer.echo("Ctrl+C para encerrar.\n")

    while True:
        try:
            mtime = file.stat().st_mtime
            if mtime != last_mtime:
                last_mtime = mtime
                content = file.read_text(encoding="utf-8")
                compressed, stats = rt.compress(content)
                out.write_text(compressed, encoding="utf-8")
                typer.echo(
                    f"[{time.strftime('%H:%M:%S')}] "
                    f"{stats.tokens_saved} tokens economizados "
                    f"({stats.savings_pct:.1f}%) em {stats.time_ms:.1f}ms"
                )
            time.sleep(interval)
        except KeyboardInterrupt:
            typer.echo("\nEncerrado.")
            break
        except FileNotFoundError:
            typer.echo(f"Aguardando {file}...", err=True)
            time.sleep(interval)


@app.command()
def report(
    stats_url: str = typer.Option(
        "http://localhost:8080/_redux/stats",
        help="URL do endpoint de stats do proxy",
    ),
    output: Path = typer.Option(
        Path("REDUXTOKEN_STATS.md"),
        "--output",
        "-o",
        help="Arquivo de relatório",
    ),
) -> None:
    """Salva snapshot das estatísticas do proxy em REDUXTOKEN_STATS.md."""
    try:
        with urllib.request.urlopen(stats_url, timeout=3) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        typer.echo(f"Erro ao conectar ao proxy ({stats_url}): {e}", err=True)
        raise typer.Exit(1)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"\n## {timestamp}\n\n"
        f"| Métrica | Valor |\n"
        f"|---|---|\n"
        f"| Requests | {data['requests']} |\n"
        f"| Cache hits | {data['cache_hits']} |\n"
        f"| Tokens originais | {data['original_tokens']} |\n"
        f"| Tokens comprimidos | {data['compressed_tokens']} |\n"
        f"| Tokens economizados | {data['tokens_saved']} |\n"
        f"| Economia | {data['savings_pct']:.1f}% |\n"
    )

    if output.exists():
        output.write_text(output.read_text(encoding="utf-8") + entry, encoding="utf-8")
    else:
        output.write_text(f"# ReduxToken — Relatório de Economia\n{entry}", encoding="utf-8")

    typer.echo(f"Relatório salvo em {output}")
    typer.echo(
        f"Acumulado: {data['tokens_saved']} tokens economizados ({data['savings_pct']:.1f}%)"
    )


def main() -> None:
    app()
