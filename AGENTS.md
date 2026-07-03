# AGENTS.md — ReduxToken

Contexto e convenções para ferramentas de IA trabalhando neste repositório.

## O que é este projeto

ReduxToken comprime texto, JSON, código e logs antes de enviá-los a LLMs, reduzindo consumo de tokens. O core é Rust; a interface é Python.

## Estrutura relevante

```
redux-token-core/   Rust — algoritmos de compressão (não modifique sem entender os filtros)
redux-token-proxy/  Rust — proxy HTTP axum (binário redux-proxy)
redux_token/        Python — bindings PyO3, CLI, hook, utils
tests/              Testes de integração Python
benchmarks/         Scripts de benchmark por tipo de conteúdo
examples/           Exemplos de uso real
proxy.toml          Configuração de providers do proxy
```

## Documentação viva

Os arquivos `.md` evoluem junto com o código — não são criados uma vez e esquecidos. A regra é:

- Toda vez que uma estrutura de módulo mudar, atualizar a seção correspondente no `ARCHITECTURE.md`.
- Toda vez que uma fase do roadmap for concluída ou redefinida, atualizar o `ROADMAP.md` (marcar itens, ajustar escopo).
- Toda vez que uma nova convenção ou decisão de design surgir, registrar em `AGENTS.md` ou em `docs/adr/` se for uma decisão arquitetural importante.
- O `README.md` reflete o estado real de instalação e uso — se o comando mudou, o README muda junto no mesmo commit.

Isso facilita contribuidores entenderem o projeto sem precisar ler o histórico de commits.

**Docs internos (privados):** o repositório é **público**. Documentos de planejamento,
estudo de concorrentes e notas de design ficam em `docs/internal/`, que é um **submodule**
apontando para o repo **privado** `ReduxToken-internal`. Numa máquina nova, traga-os com
`git clone --recursive` ou `git submodule update --init`. Escreva/edite esses docs dentro
de `docs/internal/` e **commite/push no submodule** (repo privado); depois, se o ponteiro
mudou, commite o gitlink no repo principal. Nunca crie links públicos (README/ROADMAP)
apontando para esse conteúdo — vazariam estratégia.

## Convenções de código

- Filtros em Rust implementam o trait `Filter`. Ao criar um novo filtro, implemente o trait e registre no `Compressor::default()`.
- `CompressionStats` é retornado por toda compressão. Não remova campos — quebraria bindings Python.
- A CLI usa `typer`. Comandos disponíveis: `compress`, `cost`, `watch`, `report`, `gain`, `session`, `discover`, `doctor`, `gc`. Novos subcomandos seguem o padrão `@app.command()`.
- `hook.py` é o PostToolUse hook para Claude Code — nunca levante exceções sem capturar; falha silenciosa é o comportamento correto.
- `ReduxToken(extra_filters=[...])` aceita funções Python `str -> str` que rodam após o core Rust.
- Testes unitários dos filtros Rust ficam inline (`#[cfg(test)]` em cada arquivo). Testes de integração Python ficam em `tests/`.
- Não adicione dependências Rust pesadas sem justificativa no ARCHITECTURE.md.

## Git e commits

- **Commits pequenos e focados.** Cada commit deve conter uma mudança lógica coesa —
  facilita identificar a origem de possíveis erros (`git bisect`, revisão) e reverter algo
  sem arrastar código não relacionado. Prefira vários commits pequenos a um grande.
- Separe por natureza: docs num commit, implementação em outro; uma feature por commit.
- Rode os testes (`pytest -q`) antes de commitar; o commit deve deixar a árvore verde.
- Mensagens no padrão `tipo(escopo): resumo` (ex.: `feat(cli):`, `fix:`, `docs:`).

## Linguagem

Código e comentários em inglês. Documentação pública (README, exemplos, mensagens de CLI) em português.

## O que não fazer

- Não reescrever filtros em Python — o ponto é ter o core em Rust.
- Não assumir que a compressão é lossless em todos os casos — o CodeFilter remove comentários, o que é intencional.
- Não adicionar heurísticas de tokenização complexas em Python — isso pertence ao Rust core.
