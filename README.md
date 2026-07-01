# ReduxToken

Compressor inteligente de tokens para LLMs. Reduz o custo e o consumo de tokens ao comprimir texto, JSON, código e logs antes de enviá-los para modelos como Claude e GPT-4.

Core de alta performance em **Rust**, interface acessível em **Python**.

## Benchmark

| Conteúdo | Tokens antes | Tokens depois | Economia |
|---|---|---|---|
| Log com DEBUG/TRACE | 1 166 | 47 | **96%** |
| JSON com metadados | 522 | 155 | **70%** |
| Código com comentários | 844 | 60 | **93%** |
| Texto repetitivo | 367 | 12 | **97%** |
| **Média** | | | **~90%** |

## Instalação

```bash
pip install redux-token
```

> **Nota:** O pacote contém código Rust compilado. Wheel atual: Windows x86_64 / Python 3.13. Para outras plataformas, instale Rust e o pip compilará a partir do source: `pip install redux-token`.

## Uso rápido

```python
from redux_token import ReduxToken

rt = ReduxToken()
compressed, stats = rt.compress("seu texto aqui")

print(f"Tokens economizados: {stats.tokens_saved} ({stats.savings_pct:.1f}%)")
```

## Como funciona

ReduxToken aplica filtros sequenciais ao conteúdo antes de enviá-lo ao LLM:

```
Entrada (texto / JSON / código / log)
  -> JsonFilter   — remove campos irrelevantes (id, uuid, timestamps, metadata)
  -> CodeFilter   — remove comentários // e /* */
  -> TextFilter   — remove linhas [DEBUG] e [TRACE]
  -> SmartFilter  — elimina separadores e linhas duplicadas
Saída (60–97% menos tokens)
```

## CLI

```bash
# Comprimir texto ou arquivo
redux-token compress "seu texto"
redux-token compress --file input.log
cat big_output.log | redux-token compress

# Monitorar arquivo e comprimir ao salvar
redux-token watch arquivo.log

# Estimar custo
redux-token cost 10000 800 --price 0.003

# Salvar relatório de economia do proxy
redux-token report
```

## Filtros customizados

```python
import re
from redux_token import ReduxToken

def remove_urls(text: str) -> str:
    return re.sub(r'https?://\S+', '[url]', text)

def remove_emails(text: str) -> str:
    return re.sub(r'[\w.+-]+@[\w-]+\.\w+', '[email]', text)

rt = ReduxToken(extra_filters=[remove_urls, remove_emails])
compressed, stats = rt.compress(text)
```

## Proxy HTTP (transparente)

Intercepta requests para OpenAI/Claude e comprime automaticamente sem alterar o código da aplicação:

```bash
# Iniciar o proxy
cargo run --release --package redux-token-proxy

# Configurar a aplicação para usar o proxy
# Antes: https://api.openai.com/v1/chat/completions
# Depois: http://localhost:8080/openai/v1/chat/completions

# Ver estatísticas acumuladas
curl http://localhost:8080/_redux/stats
```

Configuração em `proxy.toml` (criado automaticamente com valores padrão).

## Hook para Claude Code

Com o projeto clonado, o hook já está ativo via `.claude/settings.json`. Ele comprime automaticamente outputs grandes de Bash e Read antes que entrem no contexto do modelo.

Para projetos externos, adicione ao `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python -m redux_token.hook" }]
      }
    ]
  }
}
```

## Instalação para desenvolvimento

Requer Rust + Python 3.10+.

```bash
git clone https://github.com/ElizioMartins/ReduxToken.git
cd ReduxToken
pip install maturin
maturin develop
python examples/basic.py
```

Veja [ARCHITECTURE.md](ARCHITECTURE.md) para decisões técnicas e [ROADMAP.md](ROADMAP.md) para o plano de desenvolvimento.

## Licença

Apache 2.0
