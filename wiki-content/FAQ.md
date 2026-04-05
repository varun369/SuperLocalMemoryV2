# FAQ

Frequently asked questions about SuperLocalMemory V3.

## General

### What is SuperLocalMemory?

SuperLocalMemory is a persistent memory system for AI assistants. It stores your decisions, bug fixes, project context, and preferences locally, then automatically provides them to your AI in future sessions. Your AI stops forgetting you.

### Is it really free?

Yes. SuperLocalMemory is open-source (Elastic License 2.0) and completely free. No usage limits, no credit system, no subscription. Forever.

### Where is my data stored?

All data is stored locally in a SQLite database at `~/.superlocalmemory/memory.db`. In Mode A and Mode B, your data never leaves your machine. In Mode C, query data is sent to your configured cloud LLM provider.

### Which IDEs are supported?

17+ IDEs including Claude Code, Cursor, VS Code (with MCP extension), Windsurf, Gemini CLI, JetBrains IDEs (IntelliJ, PyCharm, WebStorm), Continue.dev, Zed, and any IDE that supports the Model Context Protocol.

### Does it work offline?

Mode A and Mode B work fully offline. Mode C requires internet for the cloud LLM.

## Installation

### What are the requirements?

- **Python** 3.11+ (required for V3 engine)
- **Node.js** 14+ (if installing via npm)
- Any supported IDE
- For Mode B: Ollama with a pulled model
- For Mode C: API key for your cloud LLM provider

### How do I install it?

```bash
# npm (recommended)
npm install -g superlocalmemory
slm setup
slm warmup    # Optional — pre-download embedding model

# or pip
pip install superlocalmemory
slm setup
```

### How do I update?

```bash
npm install -g superlocalmemory@latest
# or: pip install --upgrade superlocalmemory
```

### I am upgrading from V2. Will I lose my data?

No. Run `slm migrate` after updating. All memories, profiles, and settings are preserved. A backup is created automatically. See [Migration from V2](Migration-from-V2) for details.

## Usage

### How does auto-recall work?

When you start a conversation in your IDE, SuperLocalMemory automatically retrieves relevant memories and injects them into your AI's context. You do not need to call "recall" explicitly — it happens in the background via the MCP server.

### How do I store a memory?

```bash
slm remember "The deploy script needs AWS_REGION set to us-east-1"
```

### How do I search memories?

```bash
slm recall "deploy configuration"
```

### How do I see which retrieval channels found what?

```bash
slm trace "deploy configuration"
```

This shows per-channel scores (Semantic, BM25, Entity Graph, Temporal) for each result.

### How do I delete a memory?

```bash
slm forget "search query"     # Delete matching memories (with confirmation)
```

## Modes

### Which mode should I use?

- **Mode A** if you need privacy, compliance, or offline operation
- **Mode B** if you want composed answers and have a capable machine (16GB+ RAM)
- **Mode C** if you want maximum accuracy and cloud access is acceptable

### Can I switch modes after setup?

Yes: `slm mode a`, `slm mode b`, or `slm mode c`. Your memories are shared across all modes.

### What are the accuracy differences?

On the LoCoMo benchmark:
- **Mode A:** 74.8% retrieval accuracy (zero cloud, highest local-first score reported)
- **Mode C:** 87.7% (cloud LLM, competitive with funded systems)
- Mathematical layers contribute +12.7pp average improvement

## Privacy and Security

### Can anyone else see my memories?

No. Your database is a local file on your machine. It is not synced, uploaded, or shared with anyone — including us.

### Is it EU AI Act compliant?

Mode A and Mode B are compliant by architecture — data never leaves your device during any memory operation. Mode C requires a Data Processing Agreement with your cloud provider.

### Can I export my data?

The database is a standard SQLite file at `~/.superlocalmemory/memory.db`. You can copy it, back it up, or query it directly.

### Can I delete all my data?

`slm forget "query"` deletes matching memories. To delete everything, remove the database: `rm ~/.superlocalmemory/memory.db`.

## Troubleshooting

### My AI does not seem to remember anything.

1. Check that SuperLocalMemory is running: `slm status`
2. Check that you have stored memories: `slm recall "test"`
3. Verify your IDE connection: restart the IDE after configuring MCP
4. Check the active profile: `slm profile list`

### Recall returns irrelevant results.

Try more specific queries. Use `slm trace "query"` to see which channels contribute — this helps diagnose whether the issue is semantic, keyword, or entity matching.

### The setup wizard does not detect my IDE.

Use manual configuration. See [IDE Setup](IDE-Setup) for per-IDE config paths.

### Where can I report bugs?

Open an issue at [github.com/qualixar/superlocalmemory/issues](https://github.com/qualixar/superlocalmemory/issues).

---
*Part of [Qualixar](https://qualixar.com) | Created by [Varun Pratap Bhardwaj](https://varunpratap.com)*
