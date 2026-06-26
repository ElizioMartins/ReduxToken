# Roadmap — ReduxToken

## Fase 1 — Fundação Rust + Python (atual)

Objetivo: projeto estruturado, core Rust funcionando, bindings Python instaláveis.

- [ ] Criar crate `redux-token-core` com trait `Filter`
- [ ] Implementar `JsonFilter`, `CodeFilter`, `TextFilter`, `SmartFilter` em Rust
- [ ] `CompressionStats` struct (tokens originais, comprimidos, % economia, tempo)
- [ ] Expor via PyO3: `compress(text) -> (str, stats)`
- [ ] Pacote Python `redux_token` com `ReduxToken` class e `utils.py`
- [ ] CLI básica com `typer`: `compress`, `stats`
- [ ] Configurar `maturin` para build e instalação local
- [ ] Testes unitários dos filtros em Rust
- [ ] Testes de integração em Python
- [ ] Exemplos em `examples/`

## Fase 2 — Proxy HTTP (Rust)

Objetivo: interceptar requests para APIs de LLM e comprimir transparentemente.

- [ ] Servidor `axum` standalone
- [ ] Comprime campo `content` de requests OpenAI/Claude antes de repassar
- [ ] Suporte a múltiplos providers via config
- [ ] Cache de resultados de compressão (hash do input)
- [ ] Estatísticas por sessão

## Fase 3 — Integrações com agentes

Objetivo: funcionar como hook dentro de ferramentas de dev.

- [ ] Hook `PreToolUse` para Claude Code (comprime output de comandos)
- [ ] Suporte a `.cursorrules` para Cursor
- [ ] Modo `watch`: monitora arquivo e comprime ao salvar
- [ ] Relatório de economia acumulada em `REDUXTOKEN_STATS.md`

## Fase 4 — Publicação e ecossistema

- [ ] Publicar no PyPI como `redux-token`
- [ ] Benchmarks públicos contra Headroom e RTK
- [ ] API para filtros customizados (plugin de terceiros)
- [ ] Documentação de extensão

## Fora do escopo por ora

- Dashboard web
- Modelo ML de compressão (pode virar projeto separado)
- Suporte a streaming de tokens

---

Regra: uma fase só começa quando a anterior tiver testes passando e documentação mínima atualizada.
