<p align="center">
  <img src="https://superlocalmemory.com/assets/branding/icon-512.png" alt="SuperLocalMemory V2" width="200"/>
</p>

<h1 align="center">SuperLocalMemory V2</h1>
<p align="center"><strong>Your AI Finally Remembers You</strong></p>

<p align="center">
  <strong>⚡ Created & Architected by <a href="https://github.com/varun369">Varun Pratap Bhardwaj</a> ⚡</strong><br/>
  <em>Solution Architect • Original Creator • 2026</em>
</p>

<p align="center">
  <strong>Stop re-explaining your codebase every session. 100% local. Zero setup. Completely free.</strong>
</p>

<p align="center">
  <a href="https://superlocalmemory.com"><img src="https://img.shields.io/badge/🌐_Website-superlocalmemory.com-ff6b35?style=for-the-badge" alt="Official Website"/></a>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.8+"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License"/></a>
  <a href="#"><img src="https://img.shields.io/badge/local--first-100%25-brightgreen?style=flat-square" alt="100% Local"/></a>
  <a href="#"><img src="https://img.shields.io/badge/setup-5%20min-orange?style=flat-square" alt="5 Min Setup"/></a>
  <a href="#"><img src="https://img.shields.io/badge/platform-Mac%20%7C%20Linux%20%7C%20Windows-blue?style=flat-square" alt="Cross Platform"/></a>
  <a href="https://github.com/varun369/SuperLocalMemoryV2/wiki"><img src="https://img.shields.io/badge/📚_Wiki-Documentation-blue?style=flat-square" alt="Wiki"/></a>
</p>

<p align="center">
  <a href="https://superlocalmemory.com"><strong>superlocalmemory.com</strong></a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-why-superlocalmemory">Why This?</a> •
  <a href="#-features">Features</a> •
  <a href="#-documentation">Docs</a> •
  <a href="https://github.com/varun369/SuperLocalMemoryV2/issues">Issues</a>
</p>

<p align="center">
  <b>Created by <a href="https://github.com/varun369">Varun Pratap Bhardwaj</a></b> •
  <a href="https://github.com/sponsors/varun369">💖 Sponsor</a> •
  <a href="ATTRIBUTION.md">📜 Attribution Required</a>
</p>

---

## What's New in v2.6.5

**Interactive Knowledge Graph** — Your memories, visually connected. Powered by [Cytoscape.js](https://js.cytoscape.org/) (the same library behind Obsidian's graph plugins):

- 🔍 **Zoom, pan, explore** — Mouse wheel to zoom, drag to pan, smooth navigation
- 👆 **Click nodes** — Opens memory preview with "View Full Memory", "Expand Neighbors", "Filter to Cluster"
- 🎨 **6 layout algorithms** — Force-directed (physics-based), circular, grid, hierarchical, concentric, breadthfirst
- 🔗 **Smart filtering** — Click cluster cards or entity badges → graph instantly updates
- ⚡ **Performance** — 3-tier rendering strategy handles 10,000+ nodes smoothly

Launch the dashboard: `python3 ~/.claude-memory/ui_server.py` → `http://localhost:8765/graph.html`

**[[Complete Interactive Graph Guide →|Using-Interactive-Graph]]**

---

## What's New in v2.6

SuperLocalMemory is now **production-hardened** with security, performance, and scale improvements:

- **Trust Enforcement** — Bayesian scoring actively protects your memory. Agents with trust below 0.3 are blocked from write/delete operations.
- **Profile Isolation** — Memory profiles fully sandboxed. Zero cross-profile data leakage.
- **Rate Limiting** — Protects against memory flooding from misbehaving agents.
- **HNSW-Accelerated Graphs** — Knowledge graph edge building uses HNSW index for faster construction at scale.
- **Hybrid Search Engine** — Combined semantic + FTS5 + graph retrieval for maximum accuracy.

**v2.5 highlights (included):** Real-time event stream, WAL-mode concurrent writes, agent tracking, memory provenance, 28 API endpoints.

**Upgrade:** `npm install -g superlocalmemory@latest`

[Interactive Architecture Diagram](https://superlocalmemory.com/architecture.html) | [Architecture Doc](docs/ARCHITECTURE-V2.5.md) | [Full Changelog](CHANGELOG.md)

---

## The Problem

Every time you start a new Claude session:

```
You: "Remember that authentication bug we fixed last week?"
Claude: "I don't have access to previous conversations..."
You: *sighs and explains everything again*
```

**AI assistants forget everything between sessions.** You waste time re-explaining your:
- Project architecture
- Coding preferences
- Previous decisions
- Debugging history

---

## The Solution

```bash
# Install in one command
npm install -g superlocalmemory

# Save a memory
superlocalmemoryv2:remember "Fixed auth bug - JWT tokens were expiring too fast, increased to 24h"

# Later, in a new session...
superlocalmemoryv2:recall "auth bug"
# ✓ Found: "Fixed auth bug - JWT tokens were expiring too fast, increased to 24h"
```

**Your AI now remembers everything.** Forever. Locally. For free.

---

## 🚀 Quick Start

### Install (One Command)

```bash
npm install -g superlocalmemory
```

Or clone manually:
```bash
git clone https://github.com/varun369/SuperLocalMemoryV2.git && cd SuperLocalMemoryV2 && ./install.sh
```

Both methods auto-detect and configure **17+ IDEs and AI tools** — Cursor, VS Code/Copilot, Codex, Claude, Windsurf, Gemini CLI, JetBrains, and more.

### Verify Installation

```bash
superlocalmemoryv2:status
# ✓ Database: OK (0 memories)
# ✓ Graph: Ready
# ✓ Patterns: Ready
```

**That's it.** No Docker. No API keys. No cloud accounts. No configuration.

### Launch Dashboard

```bash
# Start the interactive web UI
python3 ~/.claude-memory/ui_server.py

# Opens at http://localhost:8765
# Features: Timeline, search, interactive graph, statistics
```

---

## 💡 Why SuperLocalMemory?

### For Developers Who Use AI Daily

| Scenario | Without Memory | With SuperLocalMemory |
|----------|---------------|----------------------|
| New Claude session | Re-explain entire project | `recall "project context"` → instant context |
| Debugging | "We tried X last week..." starts over | Knowledge graph shows related past fixes |
| Code preferences | "I prefer React..." every time | Pattern learning knows your style |
| Multi-project | Context constantly bleeds | Separate profiles per project |

### Built on 2026 Research

Not another simple key-value store. SuperLocalMemory implements **cutting-edge memory architecture**:

- **PageIndex** (Meta AI) → Hierarchical memory organization
- **GraphRAG** (Microsoft) → Knowledge graph with auto-clustering
- **xMemory** (Stanford) → Identity pattern learning
- **A-RAG** → Multi-level retrieval with context awareness

**The only open-source implementation combining all four approaches.**

[See research citations →](https://github.com/varun369/SuperLocalMemoryV2/wiki/Research-Foundations)

---

## ✨ Features

### Multi-Layer Memory Architecture

**[View Interactive Architecture Diagram](https://superlocalmemory.com/architecture.html)** — Click any layer for details, research references, and file paths.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 9: VISUALIZATION (v2.2+)                             │
│  Interactive dashboard: timeline, graph explorer, analytics │
├─────────────────────────────────────────────────────────────┤
│  Layer 8: HYBRID SEARCH (v2.2+)                             │
│  Combines: Semantic + FTS5 + Graph traversal                │
├─────────────────────────────────────────────────────────────┤
│  Layer 7: UNIVERSAL ACCESS                                  │
│  MCP + Skills + CLI (works everywhere)                      │
│  17+ IDEs with single database                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 6: MCP INTEGRATION                                   │
│  Model Context Protocol: 6 tools, 4 resources, 2 prompts    │
│  Auto-configured for Cursor, Windsurf, Claude               │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: SKILLS LAYER                                      │
│  6 universal slash-commands for AI assistants               │
│  Compatible with Claude Code, Continue, Cody                │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: PATTERN LEARNING + MACLA                          │
│  Bayesian confidence scoring (arXiv:2512.18950)             │
│  "You prefer React over Vue" (73% confidence)               │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: KNOWLEDGE GRAPH + HIERARCHICAL CLUSTERING         │
│  Recursive Leiden algorithm: "Python" → "FastAPI" → "Auth" │
│  Community summaries with TF-IDF structured reports         │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: HIERARCHICAL INDEX                                │
│  Tree structure for fast navigation                         │
│  O(log n) lookups instead of O(n) scans                     │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: RAW STORAGE                                       │
│  SQLite + Full-text search + TF-IDF vectors                 │
│  Compression: 60-96% space savings                          │
└─────────────────────────────────────────────────────────────┘
```

### Key Capabilities

- **[Knowledge Graphs](https://github.com/varun369/SuperLocalMemoryV2/wiki/Knowledge-Graph)** — Automatic relationship discovery. Interactive visualization with zoom, pan, click.
- **[Pattern Learning](https://github.com/varun369/SuperLocalMemoryV2/wiki/Pattern-Learning)** — Learns your coding preferences and style automatically.
- **[Multi-Profile Support](https://github.com/varun369/SuperLocalMemoryV2/wiki/Using-Memory-Profiles)** — Isolated contexts for work, personal, clients. Zero context bleeding.
- **[Hybrid Search](https://github.com/varun369/SuperLocalMemoryV2/wiki/Advanced-Search)** — Semantic + FTS5 + Graph retrieval combined for maximum accuracy.
- **[Visualization Dashboard](https://github.com/varun369/SuperLocalMemoryV2/wiki/Visualization-Dashboard)** — Web UI for timeline, search, graph exploration, analytics.
- **[Framework Integrations](docs/FRAMEWORK-INTEGRATIONS.md)** — Use with LangChain and LlamaIndex applications.
- **[Real-Time Events](https://github.com/varun369/SuperLocalMemoryV2/wiki/Real-Time-Event-System)** — Live notifications via SSE/WebSocket/Webhooks when memories change.

---

## 🌐 Works Everywhere

**SuperLocalMemory V2 is the ONLY memory system that works across ALL your tools:**

### Supported IDEs & Tools

| Tool | Integration | How It Works |
|------|-------------|--------------|
| **Claude Code** | ✅ Skills + MCP | `/superlocalmemoryv2:remember` |
| **Cursor** | ✅ MCP + Skills | AI uses memory tools natively |
| **Windsurf** | ✅ MCP + Skills | Native memory access |
| **Claude Desktop** | ✅ MCP | Built-in support |
| **OpenAI Codex** | ✅ MCP + Skills | Auto-configured (TOML) |
| **VS Code / Copilot** | ✅ MCP + Skills | `.vscode/mcp.json` |
| **Continue.dev** | ✅ MCP + Skills | `/slm-remember` |
| **Cody** | ✅ Custom Commands | `/slm-remember` |
| **Gemini CLI** | ✅ MCP + Skills | Native MCP + skills |
| **JetBrains IDEs** | ✅ MCP | Via AI Assistant settings |
| **Zed Editor** | ✅ MCP | Native MCP tools |
| **Aider** | ✅ Smart Wrapper | `aider-smart` with context |
| **Any Terminal** | ✅ Universal CLI | `slm remember "content"` |

### Three Ways to Access

1. **MCP (Model Context Protocol)** — Auto-configured for Cursor, Windsurf, Claude Desktop
   - AI assistants get natural access to your memory
   - No manual commands needed
   - "Remember that we use FastAPI" just works

2. **Skills & Commands** — For Claude Code, Continue.dev, Cody
   - `/superlocalmemoryv2:remember` in Claude Code
   - `/slm-remember` in Continue.dev and Cody
   - Familiar slash command interface

3. **Universal CLI** — Works in any terminal or script
   - `slm remember "content"` - Simple, clean syntax
   - `slm recall "query"` - Search from anywhere
   - `aider-smart` - Aider with auto-context injection

**All three methods use the SAME local database.** No data duplication, no conflicts.

[Complete setup guide for all tools →](docs/MCP-MANUAL-SETUP.md)

---

## 🆚 vs Alternatives

### The Hard Truth About "Free" Tiers

| Solution | Free Tier Limits | Paid Price | What's Missing |
|----------|-----------------|------------|----------------|
| **Mem0** | 10K memories, limited API | Usage-based | No pattern learning, not local |
| **Zep** | Limited credits | $50/month | Credit system, cloud-only |
| **Supermemory** | 1M tokens, 10K queries | $19-399/mo | Not local, no graphs |
| **Personal.AI** | ❌ No free tier | $33/month | Cloud-only, closed ecosystem |
| **Letta/MemGPT** | Self-hosted (complex) | TBD | Requires significant setup |
| **SuperLocalMemory V2** | **Unlimited** | **$0 forever** | **Nothing.** |

### What Actually Matters

| Feature | Mem0 | Zep | Khoj | Letta | **SuperLocalMemory V2** |
|---------|------|-----|------|-------|------------------------|
| **Works in Cursor** | Cloud Only | ❌ | ❌ | ❌ | ✅ **Local** |
| **Works in Windsurf** | Cloud Only | ❌ | ❌ | ❌ | ✅ **Local** |
| **Works in VS Code** | 3rd Party | ❌ | Partial | ❌ | ✅ **Native** |
| **Universal CLI** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Multi-Layer Architecture** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Pattern Learning** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Knowledge Graphs** | ✅ | ✅ | ❌ | ❌ | ✅ |
| **100% Local** | ❌ | ❌ | Partial | Partial | ✅ |
| **Zero Setup** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Completely Free** | Limited | Limited | Partial | ✅ | ✅ |

**SuperLocalMemory V2 is the ONLY solution that:**
- ✅ Works across 17+ IDEs and CLI tools
- ✅ Remains 100% local (no cloud dependencies)
- ✅ Completely free with unlimited memories

[See full competitive analysis →](docs/COMPETITIVE-ANALYSIS.md)

---

## ⚡ Measured Performance

All numbers measured on real hardware (Apple M4 Pro, 24GB RAM). No estimates — real benchmarks.

### Search Speed

| Database Size | Median Latency | P95 Latency |
|---------------|----------------|-------------|
| 100 memories | **10.6ms** | 14.9ms |
| 500 memories | **65.2ms** | 101.7ms |
| 1,000 memories | **124.3ms** | 190.1ms |

For typical personal use (under 500 memories), search results return faster than you blink.

### Concurrent Writes — Zero Errors

| Scenario | Writes/sec | Errors |
|----------|------------|--------|
| 1 AI tool writing | **204/sec** | 0 |
| 2 AI tools simultaneously | **220/sec** | 0 |
| 5 AI tools simultaneously | **130/sec** | 0 |

WAL mode + serialized write queue = zero "database is locked" errors, ever.

### Storage

10,000 memories = **13.6 MB** on disk (~1.9 KB per memory). Your entire AI memory history takes less space than a photo.

### Graph Construction

| Memories | Build Time |
|----------|-----------|
| 100 | 0.28s |
| 1,000 | 10.6s |

Leiden clustering discovers 6-7 natural topic communities automatically.

[Full benchmark details →](https://github.com/varun369/SuperLocalMemoryV2/wiki/Performance-Benchmarks)

---

## 🔧 CLI Commands

```bash
# Memory Operations
superlocalmemoryv2:remember "content" --tags tag1,tag2  # Save memory
superlocalmemoryv2:recall "search query"                 # Search
superlocalmemoryv2:list                                  # Recent memories
superlocalmemoryv2:status                                # System health

# Profile Management
superlocalmemoryv2:profile list                          # Show all profiles
superlocalmemoryv2:profile create <name>                 # New profile
superlocalmemoryv2:profile switch <name>                 # Switch context

# Knowledge Graph
python ~/.claude-memory/graph_engine.py build            # Build graph
python ~/.claude-memory/graph_engine.py stats            # View clusters

# Pattern Learning
python ~/.claude-memory/pattern_learner.py update        # Learn patterns
python ~/.claude-memory/pattern_learner.py context 0.5   # Get identity

# Visualization Dashboard
python ~/.claude-memory/ui_server.py                     # Launch web UI
```

[Complete CLI reference →](docs/CLI-COMMANDS-REFERENCE.md)

---

## 📖 Documentation

| Guide | Description |
|-------|-------------|
| [Quick Start](https://github.com/varun369/SuperLocalMemoryV2/wiki/Quick-Start-Tutorial) | Get running in 5 minutes |
| [Installation](https://github.com/varun369/SuperLocalMemoryV2/wiki/Installation) | Detailed setup instructions |
| [Visualization Dashboard](https://github.com/varun369/SuperLocalMemoryV2/wiki/Visualization-Dashboard) | Interactive web UI guide |
| [Interactive Graph](https://github.com/varun369/SuperLocalMemoryV2/wiki/Using-Interactive-Graph) | Graph exploration guide (NEW v2.6.5) |
| [Framework Integrations](docs/FRAMEWORK-INTEGRATIONS.md) | LangChain & LlamaIndex setup |
| [Knowledge Graph](docs/GRAPH-ENGINE.md) | How clustering works |
| [Pattern Learning](docs/PATTERN-LEARNING.md) | Identity extraction |
| [API Reference](docs/API-REFERENCE.md) | Python API documentation |

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas for contribution:**
- Additional pattern categories
- Performance optimizations
- Integration with more AI assistants
- Documentation improvements

---

## 💖 Support This Project

If SuperLocalMemory saves you time, consider supporting its development:

- ⭐ **Star this repo** — helps others discover it
- 🐛 **Report bugs** — [open an issue](https://github.com/varun369/SuperLocalMemoryV2/issues)
- 💡 **Suggest features** — [start a discussion](https://github.com/varun369/SuperLocalMemoryV2/discussions)
- ☕ **Buy me a coffee** — [buymeacoffee.com/varunpratah](https://buymeacoffee.com/varunpratah)
- 💸 **PayPal** — [paypal.me/varunpratapbhardwaj](https://paypal.me/varunpratapbhardwaj)
- 💖 **Sponsor** — [GitHub Sponsors](https://github.com/sponsors/varun369)

---

## 📜 License

MIT License — use freely, even commercially. Just include the license.

---

## 👨‍💻 Author

**Varun Pratap Bhardwaj** — Solution Architect

[![GitHub](https://img.shields.io/badge/GitHub-@varun369-181717?style=flat-square&logo=github)](https://github.com/varun369)

Building tools that make AI actually useful for developers.

---

<p align="center">
  <b>100% local. 100% private. 100% yours.</b>
</p>

<p align="center">
  <a href="https://github.com/varun369/SuperLocalMemoryV2">
    <img src="https://img.shields.io/badge/⭐_Star_on_GitHub-black?style=for-the-badge&logo=github" alt="Star on GitHub"/>
  </a>
</p>
