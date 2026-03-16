# Modes Explained

SuperLocalMemory V3 offers three operating modes. Choose based on your privacy requirements and accuracy needs.

## Mode A: Local Guardian

**Zero cloud. Maximum privacy.**

- All memory operations run locally on your machine
- No API calls, no cloud services, no data transmission
- Retrieval uses 4-channel hybrid search: semantic similarity, keyword matching, entity graph traversal, and temporal relevance
- Mathematical foundations enhance accuracy without any LLM
- EU AI Act compliant by architecture — data never leaves your device

**Who it's for:** Privacy-conscious developers, enterprise environments with strict data policies, EU-regulated industries, air-gapped systems.

**Limitations:** No LLM-powered answer synthesis. Returns ranked memory excerpts rather than composed answers. Best accuracy on factual and entity-based queries.

**Benchmark:** 62.3% on LoCoMo (highest zero-LLM score reported).

## Mode B: Smart Local

**Local LLM for answer synthesis. Still fully private.**

- Everything in Mode A, plus a local LLM via Ollama
- The LLM synthesizes retrieved memories into coherent answers
- All processing stays on your machine — nothing sent to the cloud
- Requires Ollama installed with a model (e.g., `llama3`, `mistral`, `phi3`)

**Who it's for:** Developers who want composed answers but need data to stay local. Teams that can run Ollama on their machines.

**Requirements:**
- [Ollama](https://ollama.com/) installed
- At least one model pulled: `ollama pull llama3`
- 8GB+ RAM recommended for good model performance

**Limitations:** Answer quality depends on the local model's capabilities. Smaller models may produce less accurate synthesis.

## Mode C: Full Power

**Maximum accuracy. Cloud LLM optional.**

- Everything in Mode B, plus cloud LLM support
- Cross-encoder reranking for precise result ordering
- Agentic retrieval with multi-round refinement
- Supports Azure OpenAI, OpenAI, Anthropic, and other providers

**Who it's for:** Developers who prioritize accuracy over privacy. Teams with approved cloud AI policies. Research and benchmarking.

**Benchmark:** 87.7% on LoCoMo conv-30 (competitive with funded systems like EverMemOS 92.3%).

**Note:** Data is sent to the cloud provider you configure. Ensure your organization's policies allow this.

## Switching Modes

Check your current mode:

```bash
slm mode
```

Switch modes:

```bash
slm mode a    # Switch to Local Guardian
slm mode b    # Switch to Smart Local
slm mode c    # Switch to Full Power
```

Mode changes take effect immediately. Your stored memories are not affected — all modes use the same database.

## Comparison Table

| Feature | Mode A | Mode B | Mode C |
|---------|:------:|:------:|:------:|
| Semantic search | Yes | Yes | Yes |
| Keyword search (BM25) | Yes | Yes | Yes |
| Entity graph | Yes | Yes | Yes |
| Temporal retrieval | Yes | Yes | Yes |
| Mathematical scoring | Yes | Yes | Yes |
| LLM answer synthesis | No | Local | Cloud |
| Cross-encoder reranking | No | No | Yes |
| Agentic retrieval | No | No | Yes |
| Data leaves device | Never | Never | Yes |
| EU AI Act compliant | Yes | Yes | Partial |
| Internet required | No | No | Yes |

## Recommendations

- **Start with Mode A** if you are unsure. You can always upgrade later.
- **Use Mode B** if you have a capable machine (16GB+ RAM) and want composed answers locally.
- **Use Mode C** for maximum accuracy when cloud access is acceptable.

---
*Part of [Qualixar](https://qualixar.com) | Created by [Varun Pratap Bhardwaj](https://varunpratap.com)*
