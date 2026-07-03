# Estudo comparativo: ReduxToken × Headroom (headroomlabs-ai/headroom)

> Documento de estudo. Mesmo objetivo do [ESTUDO_RTK.md](ESTUDO_RTK.md): entender o que o
> [headroom](https://github.com/headroomlabs-ai/headroom) faz que o ReduxToken ainda **não**
> faz. Fecha com uma síntese "o melhor de cada" (ReduxToken + RTK + Headroom) para o nosso roadmap.

## 1. Diferença de filosofia

O Headroom é o mais próximo de nós em arquitetura (**Rust core + Python orquestração**),
mas muito mais avançado em técnica. Enquanto o ReduxToken remove ruído com **filtros
por regex/regra**, o Headroom usa **modelos de ML** e compressão **reversível**.

| | **ReduxToken** | **Headroom** |
|---|---|---|
| Técnica de compressão | Filtros determinísticos (regex/regra) | Compressores content-aware + **modelo ML** treinado (`Kompress-v2`) |
| Reversibilidade | ❌ compressão é destrutiva | ✅ **CCR** — original em cache, LLM recupera sob demanda |
| Escopo de otimização | Tokens de **entrada** (prompt) | Entrada **+ saída** (verbosity/effort steering) + imagem |
| Arquitetura | Rust core + Python (igual à nossa) | Rust (ONNX runtime) + Python (79%) + TS SDK |
| Cache | Cache simples no proxy | **CacheAligner** — estabiliza prefixo p/ KV cache nativo do provider |
| Memória | ❌ | ✅ store compartilhado cross-agente, auto-dedup |
| Integrações | Claude Code + MCP | ~13 agentes + LangChain, LiteLLM, Vercel AI, Agno, Strands, ASGI |

**Insight central do Headroom:** compressão **reversível** muda o jogo. Como o original
fica em cache e o LLM pode recuperar via `headroom_retrieve`, ele pode comprimir de forma
**muito mais agressiva** sem medo de perder informação — se o modelo precisar do detalhe,
ele pede. O ReduxToken, sendo destrutivo, precisa ser conservador para não apagar algo útil.

## 2. O que o Headroom tem e o ReduxToken não tem

### 2.1 Compressão reversível (CCR) — o maior diferencial
Original guardado em cache local (TTL configurável); o modelo recupera sob demanda via
tool `headroom_retrieve`. Permite compressão agressiva **sem perda real de informação**.
Nós somos 100% destrutivos hoje.

### 2.2 Compressores inteligentes (vs. nossos filtros regex)
- **SmartCrusher** — JSON universal: arrays de dicts, objetos aninhados, tipos mistos
  (nosso `JsonFilter` só remove chaves de uma allowlist).
- **CodeCompressor** — **AST-aware** para Python, JS/TS, Go, Rust, Java, C/C++
  (nosso `CodeFilter` só remove comentários `//` e `/* */` por regex).
- **Kompress-v2-base** — modelo HuggingFace treinado em traces de agentes.
- **Compressão de imagem** — 40–90% via roteamento ML.

### 2.3 Redução de tokens de **saída** (não só entrada)
Nós só mexemos no prompt. O Headroom também:
- **Verbosity steering** — system prompt "terse" para respostas mais curtas.
- **Effort routing** — menos "thinking" em tarefas rotineiras.

### 2.4 CacheAligner — otimização de KV cache do provider
Estabiliza o **prefixo** das mensagens para maximizar cache hits nativos da
Anthropic/OpenAI (desconto real de billing). Nosso proxy tem cache próprio, mas não
alinha prefixo para o cache do provider.

### 2.5 Memória cross-agente
Store compartilhado entre Claude/Codex/Gemini com auto-dedup. Não temos nada disso.

### 2.6 `headroom learn` — mineração de falhas
Analisa sessões que falharam e escreve correções em arquivos markdown (plugin-based).
Loop de auto-melhoria. Não temos.

### 2.7 Observabilidade rica
- `headroom dashboard` — visualização **ao vivo** de economia.
- `headroom perf` — métricas de performance.
- `headroom doctor` — health check que confirma se o roteamento funciona.
- `headroom learn` — ver acima.

### 2.8 Ergonomia de deployment
- `headroom wrap <agent>` / `unwrap` — embrulha o agente automaticamente
  (auto-inicia proxy, injeta config).
- `headroom update` — auto-atualização via pip/pipx/uv.
- `headroom mcp install` — instala o MCP server automaticamente.

### 2.9 Amplitude de integração de framework
LangChain, LiteLLM, Vercel AI SDK, Agno, Strands, ASGI middleware, `withHeadroom()`
para SDKs Anthropic/OpenAI. Nós temos só o proxy HTTP genérico e o MCP.

### 2.10 Benchmarks com preservação de acurácia
Publicam GSM8K (0.870→0.870), TruthfulQA (+0.030), SQuAD v2 (97%), BFCL (97%).
Nosso benchmark mede só % de tokens, não acurácia preservada.

## 3. O que o ReduxToken já tem no mesmo nível

Para não subestimar o que temos — estamos alinhados em vários pontos:

- **Proxy HTTP transparente** ✅ (Headroom também tem; conceito equivalente).
- **MCP server** ✅ (temos `compress`/`compress_file`/`estimate_cost`;
  Headroom tem `headroom_compress`/`retrieve`/`stats`).
- **Biblioteca Python** ✅ (`compress()`).
- **Core Rust + Python** ✅ (mesma arquitetura).
- **Filtros customizáveis** ✅ (`extra_filters` em Python).

Diferença é de **profundidade**, não de categoria: onde temos regex, eles têm ML/AST;
onde temos cache simples, eles têm CacheAligner + CCR.

## 4. Síntese — "o melhor de cada" para o ReduxToken

Combinando ReduxToken (base atual) + RTK + Headroom. Ordenado por valor/esforço.

### Nível 1 — ganhos rápidos, alinhados ao que já temos
1. **CCR / compressão reversível** (Headroom). *Maior alavanca.* Já temos cache no proxy
   ([cache.rs](redux-token-proxy/src/cache.rs)); estender para guardar o **original** e
   expor uma tool MCP `retrieve`. Permite comprimir muito mais agressivamente.
2. **Analytics persistente + dashboard** (RTK `gain` + Headroom `dashboard`). Já temos
   `SessionStats`; falta histórico e visualização. Baixo esforço, alta "prova de economia".
3. **`doctor`** (Headroom) — comando que confirma se proxy/hook/MCP estão roteando certo.
   Reduz suporte e fricção de setup.

### Nível 2 — mais técnica de compressão
4. **CodeCompressor AST-aware** (Headroom) substituindo o `CodeFilter` regex — começar
   por Python (linguagem que já dominamos) usando o crate `syn`/tree-sitter no core Rust.
5. **SmartCrusher para JSON** (Headroom) — `JsonFilter` inteligente que resume arrays de
   dicts e objetos aninhados, em vez de só remover chaves de allowlist.
6. **Hook PreToolUse** (RTK) para 2–3 comandos ruidosos (`git status`, `ls`, `grep`) —
   evitar gerar o ruído em vez de limpar depois.

### Nível 3 — diferenciais avançados
7. **CacheAligner** (Headroom) — estabilizar prefixo no proxy para o KV cache nativo do
   provider (desconto real de billing, além da redução de tokens).
8. **Redução de tokens de saída** (Headroom) — injetar system prompt "terse" opcional no proxy.
9. **Mais integrações** (ambos) — LiteLLM/LangChain wrappers e mais agentes via o MCP existente.
10. **Benchmark de acurácia** (Headroom) — medir que a compressão não degrada a resposta,
    não só a % de tokens. Credibilidade.

### Posicionamento sugerido
> ReduxToken pode se posicionar como **"o Headroom simples e auditável"**: mesma
> arquitetura Rust+Python, mas com filtros **determinísticos e explicáveis** (sem modelo
> ML opaco) + o passo reversível (CCR) para agressividade sem risco. Simplicidade e
> transparência como diferencial, adotando as *ideias* de CCR, analytics e AST sem a
> complexidade do modelo treinado.

## 5. Matriz resumida das três ferramentas

| Capacidade | ReduxToken | RTK | Headroom |
|---|:---:|:---:|:---:|
| Compressão de texto genérico | ✅ regex | ⚠️ por comando | ✅ ML/AST |
| Wrappers de comando (git/test/ls) | ❌ | ✅ ~100+ | ❌ |
| Proxy HTTP | ✅ | ❌ | ✅ |
| MCP server | ✅ | ❌ | ✅ |
| Biblioteca (Py/TS) | ✅ Py | ❌ | ✅ Py+TS |
| Hook PreToolUse | ❌ | ✅ | ✅ (wrap) |
| Hook PostToolUse | ✅ | ⚠️ | ✅ |
| Compressão **reversível** | ❌ | ❌ | ✅ CCR |
| Compressão AST de código | ❌ regex | ⚠️ resumo | ✅ |
| Redução de tokens de **saída** | ❌ | ❌ | ✅ |
| Otimização de KV cache do provider | ❌ | ❌ | ✅ |
| Memória cross-agente | ❌ | ❌ | ✅ |
| Analytics/dashboard/histórico | ⚠️ snapshot | ✅ gain/discover | ✅ dashboard/learn |
| Nº de agentes integrados | 1 | 14 | ~13 |
| Arquitetura | Rust+Py | Rust puro | Rust+Py+TS |

Legenda: ✅ completo · ⚠️ parcial · ❌ ausente
