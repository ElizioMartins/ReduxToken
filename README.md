# ReduxToken

Compressor inteligente de tokens para LLMs. Reduz o custo e o consumo de tokens ao comprimir texto, JSON, código e logs antes de enviá-los para modelos como Claude e GPT.

## Objetivo

Implementar os melhores algoritmos de compressão de tokens, com um core de alta performance em Rust e interface acessível em Python.

## Como funciona

ReduxToken aplica filtros sequenciais ao conteúdo antes de enviá-lo ao LLM:

```
Entrada (texto / JSON / código / log)
  → JSONFilter    — remove campos desnecessários (id, uuid, timestamps)
  → CodeFilter    — remove comentários e espaço excessivo
  → TextFilter    — remove linhas vazias e boilerplate
  → SmartFilter   — deduplicação e normalização final
Saída (60–90% menos tokens)
```

## Uso rápido

```python
from redux_token import ReduxToken

rt = ReduxToken()
compressed, stats = rt.compress("seu texto aqui")

print(f"Tokens economizados: {stats.tokens_saved}")
print(f"Redução: {stats.savings_pct:.1f}%")
```

```bash
# Via CLI
redux-token compress "seu texto"
redux-token compress --file input.txt --output out.txt
redux-token stats
```

## Instalação (desenvolvimento)

Requer Rust + Python 3.10+.

```bash
git clone https://github.com/ElizioMartins/ReduxToken.git
cd ReduxToken

# Compila o core Rust e instala o pacote Python
pip install maturin
maturin develop

# Executa exemplos
python examples/basic.py
```

## Estrutura

```
ReduxToken/
├── redux-token-core/   # Core de compressão em Rust
├── redux_token/        # Bindings Python (PyO3) + CLI
├── examples/
└── tests/
```

Veja [ARCHITECTURE.md](ARCHITECTURE.md) para decisões técnicas e [ROADMAP.md](ROADMAP.md) para o plano de desenvolvimento.

## Licença

Apache 2.0
