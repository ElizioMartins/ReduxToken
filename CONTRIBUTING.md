# Contribuindo com o ReduxToken

Obrigado por querer ajudar! 🎉 Toda contribuição é bem-vinda — código, documentação,
benchmarks, exemplos ou simplesmente testar e abrir uma issue com feedback.

## Por onde começar

- Procure issues com a label **[`good first issue`](https://github.com/ElizioMartins/ReduxToken/labels/good%20first%20issue)** — são tarefas pequenas e bem descritas.
- Não achou nada que te sirva? **Abra uma issue** propondo a ideia antes de codar, para alinharmos.
- Dúvida, sugestão ou achou um bug? Issues são sempre bem-vindas.

## Preparar o ambiente

Requer **Rust** + **Python 3.10+**.

```bash
git clone https://github.com/ElizioMartins/ReduxToken.git
cd ReduxToken

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install maturin pytest
maturin develop                  # compila o core Rust e instala o pacote (editável)

python examples/basic.py         # smoke test rápido
```

> ℹ️ O repositório referencia um submódulo `docs/internal` que é **privado** (notas internas
> de planejamento) e **não é necessário** para contribuir. Clone normalmente, **sem**
> `--recursive`; se aparecer um aviso sobre o submódulo, pode ignorar.

## Rodar os testes

Antes de abrir um PR, deixe a árvore verde:

```bash
pytest                                   # testes Python (integração, CLI, filtros)
cargo test --package redux-token-core    # testes do core Rust
cargo test --package redux-token-proxy   # testes do proxy
```

Se você mudou o core Rust, rode `maturin develop` de novo antes do `pytest` para o
Python enxergar a nova versão.

## Padrões do projeto

- **Commits pequenos e focados** — uma mudança lógica por commit (docs separado de
  feature). Facilita revisão e `git bisect`. Mensagens no formato `tipo(escopo): resumo`
  (ex.: `feat(cli):`, `fix:`, `docs:`).
- **Documentação viva** — se você muda um comportamento, atualize o `README.md`/`ROADMAP.md`
  no mesmo PR.
- **O core é Rust** — a lógica de compressão (filtros, tokenização) fica no Rust; Python é a
  interface. Novos filtros implementam o trait `Filter` e entram no `Compressor::default()`.
- **Nunca quebre `CompressionStats`** — remover campos quebra os bindings Python.
- **Linguagem:** código e comentários em inglês; documentação pública e mensagens de CLI em
  português.

Mais detalhes de arquitetura e convenções em [AGENTS.md](AGENTS.md) e [ARCHITECTURE.md](ARCHITECTURE.md).

## Abrindo um Pull Request

1. Faça um fork e crie uma branch a partir da `main` (ex.: `feat/novo-filtro`).
2. Faça a mudança em commits pequenos, com testes passando.
3. Abra o PR contra a `main` descrevendo **o quê** e **por quê**.
4. Reviso, conversamos se precisar, e mergeamos. 🚀

## Código de conduta

Seja gentil e respeitoso. Estamos aqui para construir algo útil juntos.
