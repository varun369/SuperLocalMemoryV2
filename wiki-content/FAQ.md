# Frequently Asked Questions

Common questions about SuperLocalMemory V2, answered.

---

## General Questions

### What is SuperLocalMemory V2?

SuperLocalMemory V2 is an **intelligent local memory system** for AI assistants. It stores your conversations, code decisions, and project context locally, so AI assistants like Claude can remember everything about you and your projects.

### Is it really free?

**Yes, 100% free.** MIT license. No usage limits. No credit systems. No "free tier" restrictions. Use it commercially if you want.

### Does it only work with Claude?

No! While optimized for Claude CLI, SuperLocalMemory works with:
- **Any AI assistant** via CLI commands or Python API
- **Standalone** via terminal
- **Custom integrations** via the Python module

### Where is my data stored?

**100% on your local machine** at `~/.claude-memory/`. Nothing is ever sent to any cloud service. No telemetry, no analytics, no data collection.

---

## Privacy & Security

### Is my data safe?

Yes. Your data:
- Never leaves your computer
- Is stored in a local SQLite database
- Has no network connectivity
- Requires no API keys or accounts

### Is it GDPR/HIPAA compliant?

**Yes, by default.** Since no data leaves your machine, there's no third-party data processing to worry about. You have complete control over your data.

### Can my employer use this for sensitive projects?

Yes. SuperLocalMemory is ideal for:
- Enterprise environments
- Classified projects
- Healthcare (HIPAA)
- Financial services
- Air-gapped systems

### What about the pattern learning? Does it phone home?

No. Pattern learning happens entirely locally using basic frequency analysis. No external AI services, no API calls, no internet required.

---

## Technical Questions

### What's the 4-layer architecture?

1. **Layer 1: Raw Storage** — SQLite + full-text search
2. **Layer 2: Hierarchical Index** — Tree structure for navigation
3. **Layer 3: Knowledge Graph** — Auto-discovers relationships
4. **Layer 4: Pattern Learning** — Learns your preferences

[[Full architecture explanation →|4-Layer-Architecture]]

### How does the knowledge graph work?

1. Extracts key terms from your memories (TF-IDF)
2. Calculates similarity between memories
3. Groups similar memories into clusters (Leiden algorithm)
4. Auto-names clusters based on content

Example: It discovers "JWT", "OAuth", and "session tokens" are all related to "Authentication" — even if you never tagged them.

### What's pattern learning?

Pattern learning analyzes your memories to detect:
- Framework preferences ("React: 73% confidence")
- Coding style ("Performance over readability: 58%")
- Testing approaches ("Jest preferred: 65%")

You can feed this to Claude to get personalized suggestions.

### Can I use multiple profiles?

Yes! Create isolated contexts:

```bash
superlocalmemoryv2:profile create work
superlocalmemoryv2:profile create personal
superlocalmemoryv2:profile create client-acme
superlocalmemoryv2:profile switch work
```

Each profile has completely separate memories, graphs, and patterns.

### What databases does it support?

SQLite only (by design). Benefits:
- Zero configuration
- No server to run
- Portable (single file)
- Reliable and fast
- Works everywhere

### Can I export my data?

Yes. Your data is in `~/.claude-memory/memory.db`. You can:
- Copy the SQLite file
- Query it with any SQLite tool
- Write custom export scripts

---

## Comparison Questions

### How is this different from Mem0?

| Aspect | Mem0 | SuperLocalMemory |
|--------|------|------------------|
| **Price** | Usage-based | Free forever |
| **Data location** | Cloud | 100% local |
| **Pattern learning** | No | Yes |
| **Setup** | API keys, accounts | `./install.sh` |

### How is this different from Zep?

| Aspect | Zep | SuperLocalMemory |
|--------|-----|------------------|
| **Price** | $50/month | Free forever |
| **Data location** | Cloud | 100% local |
| **4-layer architecture** | No | Yes |
| **Credit limits** | Yes | No limits |

### Why not just use ChatGPT memory?

ChatGPT memory:
- Is cloud-based (privacy concerns)
- Has limited capacity
- Doesn't work with Claude
- No knowledge graphs
- No pattern learning
- No multi-profile

### Is this like Obsidian or Notion?

No. Those are note-taking apps. SuperLocalMemory is specifically designed for:
- AI assistant context
- Automatic relationship discovery
- Pattern learning
- Code/development workflows

---

## Usage Questions

### How many memories can it store?

**Unlimited.** Tested up to 5,000+ memories with no issues. The graph engine has a configurable limit (default 5,000) for performance.

### How fast is search?

- **Full-text search:** ~45ms (3.3x faster than v1)
- **Graph queries:** <100ms
- **Pattern lookup:** <50ms

### Do I need to manually tag everything?

No! The knowledge graph **automatically discovers relationships**. Tags are optional for additional organization.

### How often should I rebuild the graph?

- **After adding 10+ new memories** — rebuild for best results
- **Weekly** — if you add memories regularly
- **It's fast** — <2 seconds for 100 memories

```bash
python ~/.claude-memory/graph_engine.py build
```

### Can I use this offline?

**Yes, 100% offline.** No internet connection required for any feature.

---

## Troubleshooting

### "command not found: superlocalmemoryv2"

Add to PATH:
```bash
export PATH="${HOME}/.claude-memory/bin:${PATH}"
```

### Graph build fails with "sklearn not found"

Install optional dependency:
```bash
pip install scikit-learn
```

### Memories not showing up in search

1. Check if memory was added: `superlocalmemoryv2:list`
2. Try exact phrase search
3. Rebuild FTS index (rare): restart the app

[[More troubleshooting →|Troubleshooting]]

---

## Contributing

### How can I contribute?

See [[Contributing]] for guidelines. Areas we need help:
- Performance optimizations
- Graph visualization UI
- Additional pattern categories
- Documentation improvements

### Is there a roadmap?

Yes! See [[Roadmap]] for upcoming features.

---

## Support

### Where do I report bugs?

[GitHub Issues](https://github.com/varun369/SuperLocalMemoryV2/issues)

### Where can I ask questions?

[GitHub Discussions](https://github.com/varun369/SuperLocalMemoryV2/discussions)

### How can I support the project?

- ⭐ [Star on GitHub](https://github.com/varun369/SuperLocalMemoryV2)
- ☕ [Buy Me a Coffee](https://buymeacoffee.com/varunpratah)
- 💸 [PayPal](https://paypal.me/varunpratapbhardwaj)
- 💖 [GitHub Sponsors](https://github.com/sponsors/varun369)

---

[[← Back to Home|Home]]
