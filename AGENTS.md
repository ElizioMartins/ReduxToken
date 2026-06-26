# AGENTS.md — ReduxToken

Contexto e convenções para ferramentas de IA trabalhando neste repositório.

## O que é este projeto

ReduxToken comprime texto, JSON, código e logs antes de enviá-los a LLMs, reduzindo consumo de tokens. O core é Rust; a interface é Python.

## Estrutura relevante

```
redux-token-core/   Rust — algoritmos de compressão (não modifique sem entender os filtros)
redux_token/        Python — bindings PyO3, CLI, utils
tests/              Testes unitários e de integração
examples/           Exemplos de uso real
```

## Convenções

- Filtros em Rust implementam o trait `Filter`. Ao criar um novo filtro, implemente o trait e registre no `Compressor::default()`.
- `CompressionStats` é retornado por toda compressão. Não remova campos — quebraria bindings Python.
- A CLI usa `typer`. Novos subcomandos seguem o padrão `@app.command()`.
- Testes de filtros ficam em `redux-token-core/tests/`. Testes de integração Python ficam em `tests/`.
- Não adicione dependências Rust pesadas sem justificativa no ARCHITECTURE.md.

## Linguagem

Código e comentários em inglês. Documentação pública (README, exemplos, mensagens de CLI) em português.

## O que não fazer

- Não reescrever filtros em Python — o ponto é ter o core em Rust.
- Não assumir que a compressão é lossless em todos os casos — o CodeFilter remove comentários, o que é intencional.
- Não adicionar heurísticas de tokenização complexas em Python — isso pertence ao Rust core.
