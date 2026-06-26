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

## Documentação viva

Os arquivos `.md` evoluem junto com o código — não são criados uma vez e esquecidos. A regra é:

- Toda vez que uma estrutura de módulo mudar, atualizar a seção correspondente no `ARCHITECTURE.md`.
- Toda vez que uma fase do roadmap for concluída ou redefinida, atualizar o `ROADMAP.md` (marcar itens, ajustar escopo).
- Toda vez que uma nova convenção ou decisão de design surgir, registrar em `AGENTS.md` ou em `docs/adr/` se for uma decisão arquitetural importante.
- O `README.md` reflete o estado real de instalação e uso — se o comando mudou, o README muda junto no mesmo commit.

Isso facilita contribuidores entenderem o projeto sem precisar ler o histórico de commits.

## Convenções de código

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
