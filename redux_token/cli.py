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


@app.command()
def gain(
    since: str = typer.Option("7d", "--since", "-s", help="Janela: 24h, 7d, 30d, all"),
    price: float = typer.Option(0.003, help="Custo por 1k tokens (USD)"),
    as_json: bool = typer.Option(False, "--json", help="Saída JSON para scripts"),
) -> None:
    """Mostra a economia acumulada (tokens + $) com histórico e breakdown."""
    from redux_token import analytics

    try:
        delta = analytics.parse_since(since)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    events = analytics.filter_since(analytics.load_events(), delta)
    agg = analytics.aggregate(events)
    savings_usd = agg["tokens_saved"] * price / 1000

    if as_json:
        typer.echo(json.dumps({**agg, "savings_usd": savings_usd, "since": since}))
        return

    if agg["events"] == 0:
        typer.echo("Nenhum evento registrado nessa janela ainda.")
        typer.echo("Use o ReduxToken (CLI, hook, proxy ou MCP) e volte aqui.")
        return

    label = "todo o período" if delta is None else f"últimos {since}"
    hn = analytics.human_number
    typer.echo(f"\n  ReduxToken — economia ({label})")
    typer.echo("  " + "─" * 42)
    typer.echo(
        f"  Tokens economizados   {hn(agg['tokens_saved']):>7}  "
        f"(de {hn(agg['original_tokens'])} → {hn(agg['compressed_tokens'])})"
    )
    typer.echo(f"  Economia estimada     ${savings_usd:>6.2f}   (@ ${price}/1k)")
    typer.echo(f"  Redução média         {agg['reduction_pct']:>5.1f}%")
    typer.echo(f"  Eventos               {agg['events']:>7}  (cache hits: {agg['cache_hits']})")

    days = analytics.by_day(events)
    if len(days) > 1:
        spark = analytics.sparkline(list(days.values()))
        typer.echo(f"\n  Por dia  {spark}  ({next(iter(days))} → {next(reversed(days))})")

    _echo_breakdown("Por fonte", analytics.by_field(events, "source"), agg["tokens_saved"])
    _echo_breakdown("Por tipo", analytics.by_field(events, "content_type"), agg["tokens_saved"])
    typer.echo("")


@app.command()
def session(
    last: int = typer.Option(10, "--last", "-n", help="Quantas sessões mostrar"),
    as_json: bool = typer.Option(False, "--json", help="Saída JSON para scripts"),
) -> None:
    """Lista as últimas execuções (adoção ao longo do tempo), agrupadas por sessão."""
    from redux_token import analytics

    sessions = analytics.session_summaries(analytics.load_events())[:last]

    if as_json:
        payload = [
            {k: s[k] for k in ("session_id", "start_str", "source", "events", "tokens_saved", "reduction_pct")}
            for s in sessions
        ]
        typer.echo(json.dumps(payload))
        return

    if not sessions:
        typer.echo("Nenhuma sessão registrada ainda.")
        return

    hn = analytics.human_number
    typer.echo(f"\n  Sessão                    Fonte   Eventos  Economia    %")
    typer.echo("  " + "─" * 54)
    for s in sessions:
        typer.echo(
            f"  {s['start_str']:<16}  {s['short_id']:<6}{s['source']:<7} "
            f"{s['events']:>6}  {hn(s['tokens_saved']):>7}  {s['reduction_pct']:>4.0f}%"
        )
    typer.echo("")


@app.command()
def discover(
    as_json: bool = typer.Option(False, "--json", help="Saída JSON para scripts"),
) -> None:
    """Aponta oportunidades de otimização não aproveitadas (regras explicáveis)."""
    from redux_token import analytics

    events = analytics.load_events()
    findings = analytics.discover(events)

    if as_json:
        typer.echo(json.dumps(findings))
        return

    if not events:
        typer.echo("Nenhum evento registrado ainda — nada a analisar.")
        return
    if not findings:
        typer.echo("\n  ✓ Nenhuma oportunidade óbvia — tudo rodando bem.\n")
        return

    typer.echo("\n  Oportunidades detectadas")
    typer.echo("  " + "─" * 42)
    for f in findings:
        icon = "⚠" if f["level"] == "warn" else "💡"
        typer.echo(f"  {icon} {f['title']}")
        typer.echo(f"    → {f['detail']}\n")


def _echo_breakdown(title: str, buckets: dict, total: int) -> None:
    if not buckets or total <= 0:
        return
    typer.echo(f"\n  {title}")
    for name, saved in list(buckets.items())[:6]:
        pct = saved / total * 100
        bar = "█" * max(1, round(pct / 5))
        typer.echo(f"    {name:<8} {pct:>4.0f}%  {bar}")


def main() -> None:
    # Terminais Windows costumam usar cp1252 e quebram nos blocos unicode do 'gain'.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    app()


if __name__ == "__main__":
    main()
