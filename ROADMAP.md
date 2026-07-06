# Roadmap — ReduxToken

## Fase 1 — Fundação Rust + Python

Objetivo: projeto estruturado, core Rust funcionando, bindings Python instaláveis.

- [x] Criar crate `redux-token-core` com trait `Filter`
- [x] Implementar `JsonFilter`, `CodeFilter`, `TextFilter`, `SmartFilter` em Rust
- [x] `CompressionStats` struct (tokens originais, comprimidos, % economia, tempo)
- [x] Expor via PyO3: `compress(text) -> (str, stats)`
- [x] Pacote Python `redux_token` com `ReduxToken` class e `utils.py`
- [x] CLI básica com `typer`: `compress`, `cost`
- [x] Configurar `maturin` para build e instalação local (`pyproject.toml`)
- [x] Testes unitários dos filtros em Rust (inline `#[cfg(test)]`)
- [x] Exemplos em `examples/basic.py`
- [x] Testes de integração em Python
- [x] Validar build: `maturin develop && python examples/basic.py`

## Fase 2 — Proxy HTTP (Rust)

Objetivo: interceptar requests para APIs de LLM e comprimir transparentemente.

- [x] Servidor `axum` standalone
- [x] Comprime campo `content` de requests OpenAI/Claude antes de repassar
- [x] Suporte a múltiplos providers via config
- [x] Cache de resultados de compressão (hash do input)
- [x] Estatísticas por sessão

## Fase 3 — Integrações com agentes

Objetivo: funcionar como hook dentro de ferramentas de dev.

- [x] Hook `PostToolUse` para Claude Code (comprime output de Bash e Read)
- [x] Suporte a `.cursorrules` para Cursor
- [x] Modo `watch`: monitora arquivo e comprime ao salvar
- [x] Relatório de economia acumulada em `REDUXTOKEN_STATS.md` (`redux-token report`)

## Fase 4 — Publicação e ecossistema

- [x] Publicar no PyPI como `redux-token` (`pip install redux-token`)
- [x] Wheels multi-plataforma via CI (Linux, macOS, Windows — Python 3.10–3.13)
- [x] Benchmarks por tipo de conteúdo (`benchmarks/compare.py`)
- [x] API para filtros customizados (`ReduxToken(extra_filters=[...])`)
- [x] Documentação de extensão (README — seção Filtros customizados)
- [x] MCP Server com tools `compress`, `compress_file`, `estimate_cost`
- [x] Compatível com Claude Desktop, Cursor, Zed e qualquer cliente MCP

## Fase 5 — Observabilidade & Economia  ⭐ prioridade

Objetivo: fazer o usuário **enxergar** a economia (tokens + $) com histórico, não só por
chamada. Fecha a maior lacuna vs. RTK (`gain`/`discover`/`session`) e Headroom (`dashboard`).

- [x] Event log unificado `~/.redux-token/events.jsonl` (append-only, local)
- [x] `telemetry.py` (lib/CLI/hook/MCP) + `events.rs` (proxy) escrevendo o mesmo schema
- [x] Instrumentar os 5 pontos de compressão (lib, CLI, proxy, hook, MCP)
- [x] `redux-token gain` — histórico + gráfico ASCII (sparkline) + breakdown por fonte/tipo
- [x] `redux-token session` — adoção agrupada por `session_id`
- [x] `redux-token discover` — regras determinísticas de oportunidade perdida
- [x] `redux-token doctor` — health check dos 5 pontos (do Headroom)
- [x] Migrar `redux-token report` para ler do event log
- [x] Opt-out via `REDUX_TOKEN_NO_STATS`; nunca sai da máquina

## Fase 6 — Compressão reversível (CCR)

Objetivo: comprimir de forma agressiva **sem perder informação** — trechos removidos vão
para um store local e o modelo recupera sob demanda. Maior alavanca técnica vinda do Headroom.

- [x] Store reversível content-addressed em disco (`~/.redux-token/reversible/`, `ref=sha256[:12]`)
- [x] Marcadores `⟦rdx:ref⟧` no lugar exato do trecho removido (a nível de filtro)
- [x] `ReduxToken(reversible=True)` + tool MCP `retrieve` + proxy reversível (config `[reversible]`)
- [x] TTL / tamanho máximo via `redux-token gc`
- [ ] Adiado p/ Fase 7: `JsonFilter`/`SmartFilter` reversíveis; comentários `#` (Python)

## Fase 7 — Filtros de nova geração

Objetivo: subir de regex para compressão com consciência de estrutura, mantendo a
identidade determinística/auditável (sem modelo ML opaco).

- [x] `CodeFilter` mais seguro: scanner de `//` ciente de strings e URLs (`://`) — corrige
      destruição de URLs. (Spike descartou tree-sitter: peso desproporcional; `#` global é
      inseguro p/ markdown/shebang. AST-aware fica como item futuro se houver demanda real.)
- [x] `JsonFilter` inteligente (resumir arrays de dicts / objetos aninhados)
- [x] Hook `PreToolUse` experimental — reescreve comandos ruidosos (`git status`, `git log`,
      `npm ls`…) via `rewrite.py`; também exposto como `redux-token lean`
- [x] Benchmark de **informação preservada** (`benchmarks/retention.py`) — 100% de retenção
      do sinal, com teste de regressão

## Fora do escopo por ora

- Dashboard web (a CLI expõe `gain --json`; um dashboard fica desacoplado e opcional)
- Modelo ML de compressão treinado (nosso diferencial é ser determinístico/auditável)
- Otimização de KV cache nativo do provider (CacheAligner) — avaliar após Fase 6
- Suporte a streaming de tokens
- Memória cross-agente

---

Regra: uma fase só começa quando a anterior tiver testes passando e documentação mínima atualizada.
