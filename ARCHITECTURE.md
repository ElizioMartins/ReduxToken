# Arquitetura — ReduxToken

## Decisão: Rust + Python

O core de compressão é escrito em Rust por três razões concretas:

1. **Performance** — filtros rodam em microssegundos; importante para uso em hooks e proxies de alta frequência.
2. **Segurança de memória** — sem GIL, sem vazamentos; adequado para um servidor proxy HTTP.
3. **Bindings fáceis** — PyO3 + maturin geram um pacote Python instalável via `pip` sem nenhuma dependência nativa extra.

A interface Python existe para facilitar adoção: bibliotecas, CLI e integrações com agentes ficam em Python.

## Módulos principais

### `redux-token-core` (Rust)

Crate lib com os algoritmos de compressão.

```
redux-token-core/src/
├── lib.rs              # Exports PyO3 para Python
├── compressor.rs       # Orquestra filtros em sequência
├── filters/
│   ├── json.rs         # Remove campos irrelevantes de JSON
│   ├── code.rs         # Remove comentários e espaço morto
│   ├── text.rs         # Normaliza boilerplate e linhas vazias
│   └── smart.rs        # Deduplicação e compactação final
└── stats.rs            # CompressionStats struct
```

**Decisão de filtros**: cada filtro é um trait `Filter { fn apply(&self, input: &str) -> String }`. O `Compressor` recebe um `Vec<Box<dyn Filter>>` e os aplica em ordem. Isso permite configurar e testar filtros individualmente.

### `redux_token` (Python)

Pacote Python que importa o módulo compilado (`redux_token_core`) e expõe uma API limpa.

```
redux_token/
├── __init__.py         # ReduxToken class, exports
├── cli.py              # CLI (typer)
└── utils.py            # estimate_cost_savings, formatação
```

**Decisão de CLI**: usar `typer` (wrapper sobre Click) — mais simples de manter e gera help automático.

## Fluxo de dados

```
Usuário / Agente
    │
    ▼
redux_token.ReduxToken.compress(text)   ← Python
    │
    ▼
redux_token_core.Compressor.compress()  ← Rust (via PyO3)
    │
    ├── json::JsonFilter.apply()
    ├── code::CodeFilter.apply()
    ├── text::TextFilter.apply()
    └── smart::SmartFilter.apply()
    │
    ▼
(compressed: String, stats: CompressionStats)
    │
    ▼
Retorna para Python como (str, CompressionStats)
```

## Próxima camada: Proxy HTTP

Quando implementado (Fase 2), o proxy será um servidor `axum` (Rust) que intercepta requests para APIs de LLM e comprime o campo `content` antes de repassar. O binário Rust roda standalone, sem dependência do Python.

```
Cliente → axum proxy (Rust) → compressor.rs → LLM API
```

## Decisões arquiteturais registradas

| Decisão | Escolha | Motivo |
|---|---|---|
| Linguagem core | Rust | Performance + segurança de memória |
| Bindings | PyO3 + maturin | Pacote Python nativo sem deps extras |
| CLI | typer | Simples, help gerado automaticamente |
| Proxy (futuro) | axum | Async nativo em Rust, mesma base do core |
| Filtros | trait `Filter` | Composição e testabilidade independente |

Quando uma decisão mudar ou tiver consequências não óbvias, um ADR vai em `docs/adr/`.
