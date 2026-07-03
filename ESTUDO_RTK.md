# Estudo comparativo: ReduxToken × RTK (rtk-ai/rtk)

> Documento de estudo. Objetivo: entender o que o [rtk](https://github.com/rtk-ai/rtk)
> faz que o ReduxToken ainda **não** faz, e decidir o que vale trazer para o roadmap.
> Não é uma lista de bugs — o README do ReduxToken está 100% implementado
> (ver tabela no final). É uma lista de *capacidades a estudar*.

## 1. Diferença de filosofia

As duas ferramentas atacam o mesmo problema (reduzir tokens enviados a LLMs),
mas por ângulos opostos:

| | **ReduxToken** | **RTK (Rust Token Killer)** |
|---|---|---|
| Unidade de trabalho | **Texto** (string / arquivo) | **Comandos de dev** (`ls`, `git`, `grep`, `test`…) |
| Como age | Filtra ruído de um conteúdo já produzido | Envolve (*wraps*) o comando e otimiza a **saída** dele |
| Ponto de entrada | `compress()`, CLI, proxy HTTP, MCP, hook PostToolUse | `rtk <comando>`, hook **PreToolUse** que reescreve o comando |
| Escopo | Genérico (qualquer texto) | ~100+ comandos com conhecimento específico de cada um |
| Integrações de agente | Claude Code (1) | 14 agentes (Claude, Copilot, Cursor, Gemini, Codex, Windsurf, Cline…) |

**Insight central do RTK:** ele intercepta **antes** de o comando rodar (PreToolUse) e
troca `git status` por `rtk git status`, que já produz saída enxuta. O ReduxToken
intercepta **depois** (PostToolUse) e comprime o texto que o comando cuspiu. O RTK
economiza mais porque nem gera o ruído; o ReduxToken é mais genérico porque não
precisa conhecer o comando.

## 2. O que o RTK tem e o ReduxToken não tem

### 2.1 Wrappers de comando com conhecimento de domínio (o grande diferencial)
O RTK tem lógica dedicada por comando. Nada disso existe no ReduxToken:

- **Arquivos:** `rtk ls` (árvore compacta), `rtk read` (modos de compressão agressiva),
  `rtk smart` (resumo de 2 linhas de código), `rtk find`, `rtk grep` (agrupado), `rtk diff`.
- **Git:** `status/log/diff/add/commit/push/pull` comprimidos.
- **Testes:** Jest, Vitest, Playwright, pytest, Go, Cargo, RSpec — modo **só-falhas**.
- **Lint/build:** ESLint agrupado por regra, tsc, Biome, Prettier, Ruff, golangci-lint.
- **Cloud/infra:** AWS (EC2, Lambda, S3, CloudWatch…), Docker, Kubernetes, Pulumi.
- **Pacotes:** pnpm, uv, pip, bundler, prisma.

### 2.2 Hook PreToolUse (reescrita de comando)
O ReduxToken só tem PostToolUse (comprime saída). O RTK reescreve o comando *antes*
de executar. É a diferença entre "limpar depois" e "não sujar".

### 2.3 Analytics / observabilidade
- `rtk gain` — estatísticas de economia com **gráficos e histórico**.
- `rtk discover` — aponta oportunidades de otimização **não aproveitadas**.
- `rtk session` — rastreia adoção ao longo das sessões recentes.

O ReduxToken tem apenas o snapshot do proxy (`redux-token report`) — sem histórico
persistente, sem gráfico, sem "descoberta".

### 2.4 Amplitude de integração
14 agentes suportados vs. 1. Mecanismos: PreToolUse (Claude/Copilot/Cursor),
BeforeTool (Gemini), plugins (Hermes/OpenCode), arquivos de regra (.windsurfrules, .clinerules).

### 2.5 Ergonomia de saída
- `-u/--ultra-compact` — ícones ASCII em formato inline.
- `-v/--verbose` — níveis de verbosidade.
- **Tee mode** — salva a saída não filtrada para recuperação em caso de falha.
- Lista de exclusão de comandos por config.

### 2.6 Distribuição
Binário Rust único, zero dependências, `<10ms` de overhead, install via Homebrew/cargo/script.
O ReduxToken depende de Python + wheel do core.

## 3. O que o ReduxToken tem e o RTK não parece ter

Para não perder de vista nossas vantagens:

- **Proxy HTTP transparente** — intercepta chamadas OpenAI/Claude e comprime o corpo
  das `messages` sem tocar no código da aplicação. O RTK é focado em CLI, não em rede.
- **Cache de compressão** no proxy ([cache.rs](redux-token-proxy/src/cache.rs)).
- **API Python de biblioteca** (`from redux_token import ReduxToken`) + `extra_filters`
  customizáveis em Python — extensível sem recompilar Rust.
- **MCP server** — qualquer cliente MCP usa como ferramenta (o RTK usa hooks, não MCP).
- Compressão genérica de **qualquer texto**, não só saída de comandos conhecidos.

## 4. Candidatos ao roadmap (a priorizar)

Ordenado por relação valor/esforço, para discutir:

1. **Analytics persistente** (`gain`/`discover` do RTK). Já temos `SessionStats` no proxy;
   falta persistir histórico e um `redux-token gain` com histórico/gráfico ASCII.
   → baixo esforço, alto valor de "prova de economia".
2. **Hook PreToolUse experimental** para comandos comuns (`git status`, `ls`, `grep`) —
   começar com 2–3 comandos de alto ruído em vez dos 100+ do RTK.
3. **Wrapper `read`/`smart`** — resumo agressivo de arquivos de código (hoje só removemos
   comentários; o RTK resume a assinatura).
4. **Modo `--ultra-compact`** na CLI e no MCP.
5. **Mais integrações de agente** (Cursor/Copilot) — reaproveitando o MCP que já temos.

> ⚠️ Antes de copiar o RTK: nosso diferencial é o **proxy HTTP + MCP + biblioteca Python**.
> Vale adotar as *ideias* de analytics e PreToolUse sem virar um clone do RTK, que é
> essencialmente um "wrapper de 100 comandos de CLI".

## 5. Verificação README ↔ implementação (feita em 2026-07-02)

Todo o README do ReduxToken tem correspondência real no código — **nenhum gap**:

| Afirmação | Onde está | OK |
|---|---|---|
| `ReduxToken().compress()` + `extra_filters` + `stats` | [redux_token/__init__.py](redux_token/__init__.py) | ✅ |
| Cadeia Json→Code→Text→Smart | [compressor.rs](redux-token-core/src/compressor.rs) | ✅ |
| CLI `compress`/`watch`/`cost`/`report` | [cli.py](redux_token/cli.py) | ✅ |
| Proxy HTTP + `/_redux/stats` | [main.rs](redux-token-proxy/src/main.rs), [stats.rs](redux-token-proxy/src/stats.rs) | ✅ |
| Hook `python -m redux_token.hook` | [hook.py](redux_token/hook.py) | ✅ |
| MCP com 3 tools | [mcp.py](redux_token/mcp.py) | ✅ |
| Wheels Linux/macOS/Windows · 3.10–3.13 | [release.yml](.github/workflows/release.yml) | ✅ |
