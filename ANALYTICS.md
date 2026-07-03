# Observabilidade & Economia — design detalhado

> Deep-dive do item que mais entrega valor ao usuário: **fazer a pessoa enxergar,
> de forma concreta e histórica, quanto token e dinheiro o ReduxToken economizou.**
> Inspirado em `rtk gain`/`discover`/`session` e no `headroom dashboard`/`perf`, mas
> desenhado para a **identidade do ReduxToken**: local-first, determinístico, auditável,
> sem servidor web nem telemetria remota.

## 1. Por que isso importa (valor pro usuário)

Economia invisível é economia que ninguém acredita. Hoje o usuário vê, no máximo, um
`— 320 tokens economizados (78%)` por chamada e some. Ele não consegue responder:

- *"Quanto economizei essa semana toda?"*
- *"Isso deu quanto em dólar?"*
- *"Que tipo de conteúdo (log? JSON? código?) me dá mais retorno?"*
- *"Estou deixando token na mesa em algum lugar?"*

Resolver isso é o que transforma o ReduxToken de "utilitário legal" em "ferramenta que
eu mantenho ligada porque vejo o ROI". É também o material que vende o projeto (prints de
economia acumulada valem mais que qualquer benchmark sintético).

## 2. Estado atual e a lacuna arquitetural

A compressão acontece hoje em **5 pontos independentes**, e cada um trata stats diferente:

| Ponto | Arquivo | O que registra hoje |
|---|---|---|
| Biblioteca | [redux_token/__init__.py](redux_token/__init__.py) | nada (só retorna `stats` ao chamador) |
| CLI | [redux_token/cli.py](redux_token/cli.py) | imprime na tela, não persiste |
| Proxy HTTP | [redux-token-proxy/src/stats.rs](redux-token-proxy/src/stats.rs) | `SessionStats` **em memória**, perde ao reiniciar |
| Hook PostToolUse | [redux_token/hook.py](redux_token/hook.py) | nada |
| MCP | [redux_token/mcp.py](redux_token/mcp.py) | nada |

**A lacuna:** não existe um registro **unificado e persistente** de eventos de compressão.
O `redux-token report` ([cli.py:104](redux_token/cli.py#L104)) só sabe do proxy, e mesmo
assim só o snapshot atual. Sem esse registro, `gain`/`discover`/`session` são impossíveis.

> **Decisão de arquitetura #1:** criar um *event log* único que **todos os 5 pontos**
> escrevem. Tudo o mais (gráficos, histórico, discover) é leitura em cima desse log.

## 3. Fundação — o event log (`~/.redux-token/events.jsonl`)

Um arquivo **JSONL** (uma linha JSON por evento), append-only, local. Escolha deliberada
vs. SQLite: zero dependência nova, inspecionável com `cat`, alinhado ao "auditável".

### Schema do evento
```json
{
  "ts": "2026-07-02T14:33:10Z",
  "source": "hook",            // lib | cli | proxy | hook | mcp
  "content_type": "log",       // log | json | code | text | mixed  (heurística)
  "original_tokens": 1166,
  "compressed_tokens": 47,
  "tokens_saved": 1119,
  "savings_pct": 95.9,
  "time_ms": 1.8,
  "from_cache": false,
  "session_id": "2026-07-02T14:30:01Z-a1b2"  // agrupa eventos de uma execução
}
```

- **`source`** — responde "de onde vem minha economia" (hook? proxy? uso manual?).
- **`content_type`** — chave do `discover`: mostra onde há mais retorno. Detectado por
  heurística barata (tem `[DEBUG]`→log; parseia como JSON→json; tem `//`/`def`/`fn`→code).
- **`session_id`** — carimbado uma vez por processo/execução, habilita o `session`.

### Instrumentação (onde escrever)
Um helper Python `redux_token/telemetry.py` com `record(stats, source, content_type)` que
faz append thread-safe (lock + `O_APPEND`). Chamado por lib, CLI, hook, MCP. O proxy (Rust)
escreve no **mesmo formato** via um pequeno módulo `events.rs` (serde → linha JSONL).

> **Decisão de arquitetura #2:** o registro é **opt-out**, não opt-in. Liga por padrão,
> mas 100% local. `REDUX_TOKEN_NO_STATS=1` ou `[stats] enabled=false` no config desliga.
> Nunca sai da máquina — esse é o nosso contraste explícito com telemetria de terceiros.

## 4. Os comandos

Mapeamento direto dos deles para a nossa CLI `typer`, sem inventar escopo demais.

### 4.1 `redux-token gain` — "quanto economizei" (histórico + gráfico)
Equivale ao `rtk gain`. Lê o event log e agrega.

```
$ redux-token gain --since 7d

  ReduxToken — economia (últimos 7 dias)
  ────────────────────────────────────────
  Tokens economizados   1.24M  (de 1.61M → 370K)
  Economia estimada     $3.71   (@ $0.003/1k)
  Redução média         77.0%
  Eventos               842     (cache hits: 231)

  Por dia
  Sáb ▁▁▂▃  118K
  Dom ▁▃▅▇  310K
  Seg ▇▇▆▅  402K   ← pico
  ...

  Por fonte              Por tipo de conteúdo
  proxy   58%  ███████   log    41%  █████
  hook    31%  ████      json   28%  ███
  cli      8%  █         code   19%  ██
  mcp      3%  ▏         text   12%  █
```

- Sparkline ASCII (blocos `▁▂▃▄▅▆▇█`) — zero dependência, funciona em qualquer terminal.
- Flags: `--since 7d|24h|30d|all`, `--price` (custo/1k), `--json` (saída p/ scripts).
- Fonte da verdade: o event log. `--json` habilita integração externa (ex.: um dashboard
  web *opcional* no futuro, sem acoplar a CLI a ele).

### 4.2 `redux-token discover` — "onde estou deixando token na mesa"
Equivale ao `rtk discover`. É o mais "inteligente" e o que mais encanta. Analisa padrões
e **sugere ação**:

```
$ redux-token discover

  Oportunidades detectadas
  ────────────────────────────────────────
  ⚠ 34% dos seus eventos vêm do 'cli' com savings_pct < 20%.
    → Esses conteúdos são majoritariamente 'text' curto. Considere pular
      compressão abaixo de 200 chars (já feito no hook, não na CLI).

  ⚠ Nenhum evento com source='proxy' nas últimas 48h.
    → O proxy pode ter caído. Rode 'redux-token doctor'.

  💡 Seus arquivos 'log' rendem 94% em média, mas só 12% do volume passa por aqui.
    → Ative o hook PostToolUse no seu agente para capturar mais logs automaticamente.
```

Regras iniciais (determinísticas, sem ML — fiel à nossa identidade):
1. Fonte com savings baixo consistente → conteúdo mal-ajustado ao filtro.
2. Ausência de eventos de uma fonte esperada → integração quebrada.
3. Tipo de conteúdo com alto savings mas baixo volume → oportunidade de captura.
4. Alta taxa de `from_cache=false` em conteúdo repetido → cache subutilizado.

### 4.3 `redux-token session` — "adoção ao longo do tempo"
Equivale ao `rtk session`. Lista as últimas execuções agrupadas por `session_id`:

```
$ redux-token session --last 5

  Sessão                     Fonte   Eventos  Economia   %
  2026-07-02 14:30  a1b2     hook    142      98.2K     81%
  2026-07-02 11:05  9f3c     proxy   67       210K      74%
  2026-07-01 18:44  7d10     cli     3        1.2K      52%
  ...
```

Serve para o usuário ver **frequência de uso** e provar consistência (não foi sorte de um
arquivo). Também é a base de um futuro `learn` (identificar sessões de baixo retorno).

### 4.4 `redux-token doctor` (bônus, do Headroom) — health check
Não é analytics, mas anda junto: confirma que os 5 pontos estão roteando/registrando.
Verifica: core Rust importável, proxy respondendo em `/_redux/stats`, hook configurado no
`.claude/settings.json`, MCP registrável, event log gravável. Reduz suporte drasticamente.

## 5. Como isto se compara — e por que ganhamos

| Recurso | RTK | Headroom | ReduxToken (proposto) |
|---|:---:|:---:|:---:|
| Histórico persistente | ✅ | ✅ | ✅ (JSONL local) |
| Gráfico de economia | ✅ | ✅ dashboard web | ✅ ASCII no terminal |
| Discover / oportunidades | ✅ | ⚠️ (via `learn`) | ✅ regras explicáveis |
| Adoção por sessão | ✅ | ✅ | ✅ |
| Breakdown por tipo de conteúdo | ⚠️ | ✅ | ✅ |
| Custo em $ | ⚠️ | ✅ | ✅ (já temos `estimate_cost`) |
| **100% local / sem telemetria remota** | ✅ | ⚠️ opcional | ✅ **por design** |
| **Sem servidor web / zero deps novas** | ✅ | ❌ | ✅ |

Nosso diferencial: **paridade de informação sem a complexidade deles**. Sem dashboard web
(fora de escopo, alinhado ao ROADMAP), sem ML opaco no `discover`, sem telemetria que sai
da máquina. É "o analytics que você entende e audita".

## 6. Plano de implementação incremental

Cada passo entrega valor sozinho e não quebra o anterior:

1. **Event log + telemetria** (`telemetry.py` + `events.rs`). Instrumentar os 5 pontos.
   Nada visível ainda, mas passa a acumular dados. *(fundação)*
2. **`redux-token gain`** — agregação + sparkline ASCII. Primeiro payoff visível.
3. **Migrar `redux-token report`** para ler do event log (hoje só lê o proxy), mantendo
   compat com `REDUXTOKEN_STATS.md`.
4. **`redux-token session`** — agrupamento por `session_id`.
5. **`redux-token discover`** — as 4 regras iniciais.
6. **`redux-token doctor`** — health check dos 5 pontos.
7. *(opcional, futuro)* dashboard web lendo `gain --json` — desacoplado, não bloqueia nada.

## 7. Riscos e decisões em aberto

- **Crescimento do log:** rotacionar por tamanho/idade (ex.: `events.jsonl` + `.1.gz`),
  ou compactar agregados diários e descartar eventos crus > 90 dias. Decidir no passo 1.
- **Concorrência de escrita** (proxy multi-thread + hook simultâneo): `O_APPEND` garante
  atomicidade por linha em POSIX; no Windows validar com lock de arquivo.
- **Preço do token:** default `$0.003/1k` (Sonnet). Deixar configurável por provider no
  `config` para o `$` fazer sentido em multi-modelo.
- **Detecção de `content_type`:** heurística pode errar em conteúdo misto → categoria
  `mixed`; não é crítico, é só para o breakdown.
