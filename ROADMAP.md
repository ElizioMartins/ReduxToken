# Roadmap — ReduxToken

## Fase 1 — Fundação Rust + Python (atual)

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

- [ ] Publicar no PyPI como `redux-token` (wheel pronta: `maturin publish`)
- [x] Benchmarks por tipo de conteúdo (`benchmarks/compare.py`)
- [x] API para filtros customizados (`ReduxToken(extra_filters=[...])`)
- [x] Documentação de extensão (README — seção Filtros customizados)

## Fora do escopo por ora

- Dashboard web
- Modelo ML de compressão (pode virar projeto separado)
- Suporte a streaming de tokens

---

Regra: uma fase só começa quando a anterior tiver testes passando e documentação mínima atualizada.
