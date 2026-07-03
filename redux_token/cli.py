import sys
import time
import json
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
    since: str = typer.Option("all", "--since", "-s", help="Janela: 24h, 7d, 30d, all"),
    output: Path = typer.Option(
        Path("REDUXTOKEN_STATS.md"),
        "--output",
        "-o",
        help="Arquivo de relatório",
    ),
) -> None:
    """Salva snapshot da economia (todas as fontes) em REDUXTOKEN_STATS.md."""
    from redux_token import analytics

    try:
        delta = analytics.parse_since(since)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    events = analytics.filter_since(analytics.load_events(), delta)
    if not events:
        typer.echo("Nenhum evento registrado nessa janela — nada a reportar.", err=True)
        raise typer.Exit(1)

    agg = analytics.aggregate(events)
    by_source = analytics.by_field(events, "source")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"\n## {timestamp} (janela: {since})\n",
        "| Métrica | Valor |",
        "|---|---|",
        f"| Eventos | {agg['events']} |",
        f"| Cache hits | {agg['cache_hits']} |",
        f"| Tokens originais | {agg['original_tokens']} |",
        f"| Tokens comprimidos | {agg['compressed_tokens']} |",
        f"| Tokens economizados | {agg['tokens_saved']} |",
        f"| Redução | {agg['reduction_pct']:.1f}% |",
        "",
        "Economia por fonte:",
        "",
    ]
    for name, saved in by_source.items():
        lines.append(f"- **{name}**: {saved} tokens")
    entry = "\n".join(lines) + "\n"

    if output.exists():
        output.write_text(output.read_text(encoding="utf-8") + entry, encoding="utf-8")
    else:
        output.write_text(f"# ReduxToken — Relatório de Economia\n{entry}", encoding="utf-8")

    typer.echo(f"Relatório salvo em {output}")
    typer.echo(
        f"Acumulado ({since}): {agg['tokens_saved']} tokens economizados "
        f"({agg['reduction_pct']:.1f}%)"
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


@app.command()
def doctor(
    as_json: bool = typer.Option(False, "--json", help="Saída JSON para scripts"),
) -> None:
    """Verifica se os 5 pontos (core, event log, hook, proxy, MCP) estão roteando."""
    from redux_token import doctor as _doctor

    checks = _doctor.run_checks()

    if as_json:
        typer.echo(json.dumps(checks))
        raise typer.Exit(1 if any(c["status"] == "fail" for c in checks) else 0)

    icons = {"ok": "✓", "warn": "⚠", "fail": "✗"}
    typer.echo("\n  ReduxToken — diagnóstico")
    typer.echo("  " + "─" * 42)
    for c in checks:
        typer.echo(f"  {icons.get(c['status'], '?')} {c['name']:<18} {c['detail']}")

    fails = sum(1 for c in checks if c["status"] == "fail")
    warns = sum(1 for c in checks if c["status"] == "warn")
    if fails:
        typer.echo(f"\n  {fails} problema(s) crítico(s). Veja acima.\n")
    elif warns:
        typer.echo(f"\n  Tudo essencial ok — {warns} item(ns) opcional(is) inativo(s).\n")
    else:
        typer.echo("\n  Tudo em ordem. ✓\n")
    raise typer.Exit(1 if fails else 0)


@app.command()
def gc(
    ttl: float = typer.Option(24.0, help="Remove trechos com mais de N horas (0 = ignora idade)"),
    max_mb: float = typer.Option(0.0, help="Limite de tamanho do store em MB (0 = sem limite)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Só mostra o que seria removido"),
) -> None:
    """Limpa o store de compressão reversível (TTL e/ou tamanho máximo)."""
    from redux_token import reversible

    before = reversible.store_stats()
    result = reversible.gc(
        ttl_hours=(ttl if ttl > 0 else None),
        max_mb=(max_mb if max_mb > 0 else None),
        dry_run=dry_run,
    )
    freed_mb = result["freed_bytes"] / 1024 / 1024
    verb = "seriam removidos" if dry_run else "removidos"
    typer.echo(
        f"Store reversível: {before['files']} trechos "
        f"({before['bytes'] / 1024 / 1024:.2f} MB)."
    )
    typer.echo(
        f"{result['removed']} {verb} ({freed_mb:.2f} MB), "
        f"{result['remaining']} restante(s)."
    )


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
