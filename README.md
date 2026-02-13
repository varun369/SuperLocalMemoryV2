<p align="center">
  <img src="https://varun369.github.io/SuperLocalMemoryV2/assets/branding/icon-512.png" alt="SuperLocalMemory V2" width="200"/>
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
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.8+"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License"/></a>
  <a href="#"><img src="https://img.shields.io/badge/local--first-100%25-brightgreen?style=flat-square" alt="100% Local"/></a>
  <a href="#"><img src="https://img.shields.io/badge/setup-5%20min-orange?style=flat-square" alt="5 Min Setup"/></a>
  <a href="#"><img src="https://img.shields.io/badge/platform-Mac%20%7C%20Linux%20%7C%20Windows-blue?style=flat-square" alt="Cross Platform"/></a>
  <a href="https://github.com/varun369/SuperLocalMemoryV2/wiki"><img src="https://img.shields.io/badge/📚_Wiki-Documentation-blue?style=flat-square" alt="Wiki"/></a>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-why-superlocalemory">Why This?</a> •
  <a href="#-features">Features</a> •
  <a href="#-vs-alternatives">vs Alternatives</a> •
  <a href="#-documentation">Docs</a> •
  <a href="https://github.com/varun369/SuperLocalMemoryV2/issues">Issues</a>
</p>

<p align="center">
  <b>Created by <a href="https://github.com/varun369">Varun Pratap Bhardwaj</a></b> •
  <a href="https://github.com/sponsors/varun369">💖 Sponsor</a> •
  <a href="ATTRIBUTION.md">📜 Attribution Required</a>
</p>

---

## NEW: v2.5 — "Your AI Memory Has a Heartbeat"

> **SuperLocalMemory is no longer passive storage — it's a real-time coordination layer.**

| What's New | Why It Matters |
|------------|----------------|
| **Real-Time Event Stream** | See every memory operation live in the dashboard — no refresh needed. SSE-powered, cross-process. |
| **No More "Database Locked"** | WAL mode + serialized write queue. 50 concurrent agents writing? Zero errors. |
| **Agent Tracking** | Know exactly which AI tool wrote what. Claude, Cursor, Windsurf, CLI — all tracked automatically. |
| **Trust Scoring** | Bayesian trust signals detect spam, quick-deletes, and cross-agent validation. Silent in v2.5, enforced in v2.6. |
| **Memory Provenance** | Every memory records who created it, via which protocol, with full derivation lineage. |
| **Production-Grade Code** | 28 API endpoints across 8 modular route files. 13 modular JS files. 63 pytest tests. |

**Upgrade:** `npm install -g superlocalmemory@latest`

**Dashboard:** `python3 ~/.claude-memory/ui_server.py` then open `http://localhost:8765`

[Interactive Architecture Diagram](https://varun369.github.io/SuperLocalMemoryV2/architecture.html) | [Architecture Doc](docs/ARCHITECTURE-V2.5.md) | [Full Changelog](CHANGELOG.md)

---

## NEW: Framework Integrations (v2.5.1)

Use SuperLocalMemory as a memory backend in your LangChain and LlamaIndex applications — 100% local, zero cloud.

### LangChain

```bash
pip install langchain-superlocalmemory
```

```python
from langchain_superlocalmemory import SuperLocalMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

history = SuperLocalMemoryChatMessageHistory(session_id="my-session")
# Messages persist across sessions, stored locally in ~/.claude-memory/memory.db
```

### LlamaIndex

```bash
pip install llama-index-storage-chat-store-superlocalmemory
```

```python
from llama_index.storage.chat_store.superlocalmemory import SuperLocalMemoryChatStore
from llama_index.core.memory import ChatMemoryBuffer

chat_store = SuperLocalMemoryChatStore()
memory = ChatMemoryBuffer.from_defaults(chat_store=chat_store, chat_store_key="user-1")
```

[LangChain Guide](https://github.com/varun369/SuperLocalMemoryV2/wiki/LangChain-Integration) | [LlamaIndex Guide](https://github.com/varun369/SuperLocalMemoryV2/wiki/LlamaIndex-Integration)

---

## Install in One Command

```bash
npm install -g superlocalmemory
```

Or clone manually:
```bash
git clone https://github.com/varun369/SuperLocalMemoryV2.git && cd SuperLocalMemoryV2 && ./install.sh
```

Both methods auto-detect and configure **16+ IDEs and AI tools** — Cursor, VS Code/Copilot, Codex, Claude, Windsurf, Gemini CLI, JetBrains, and more.

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

### npm (Recommended — All Platforms)
```bash
npm install -g superlocalmemory
```

### Mac/Linux (Manual)
```bash
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2
./install.sh
```

### Windows (PowerShell)
```powershell
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2
.\install.ps1
```

### Verify Installation
```bash
superlocalmemoryv2:status
# ✓ Database: OK (0 memories)
# ✓ Graph: Ready
# ✓ Patterns: Ready
```

**That's it.** No Docker. No API keys. No cloud accounts. No configuration.

### Updating to Latest Version

**npm users:**
```bash
# Update to latest version
npm update -g superlocalmemory

# Or force latest
npm install -g superlocalmemory@latest

# Install specific version
npm install -g superlocalmemory@latest
```

**Manual install users:**
```bash
cd SuperLocalMemoryV2
git pull origin main
./install.sh  # Mac/Linux
# or
.\install.ps1  # Windows
```

**Your data is safe:** Updates preserve your database and all memories.

### Start the Visualization Dashboard

```bash
# Launch the interactive web UI
python3 ~/.claude-memory/ui_server.py

# Opens at http://localhost:8765
# Features: Timeline view, search explorer, graph visualization
```

---

## 🎨 Visualization Dashboard

**NEW in v2.2.0:** Interactive web-based dashboard for exploring your memories visually.

### Features

| Feature | Description |
|---------|-------------|
| **📈 Timeline View** | See your memories chronologically with importance indicators |
| **🔍 Search Explorer** | Real-time semantic search with score visualization |
| **🕸️ Graph Visualization** | Interactive knowledge graph with clusters and relationships |
| **📊 Statistics Dashboard** | Memory trends, tag clouds, pattern insights |
| **🎯 Advanced Filters** | Filter by tags, importance, date range, clusters |

### Quick Tour

```bash
# 1. Start dashboard
python ~/.claude-memory/ui_server.py

# 2. Navigate to http://localhost:8765

# 3. Explore your memories:
#    - Timeline: See memories over time
#    - Search: Find with semantic scoring
#    - Graph: Visualize relationships
#    - Stats: Analyze patterns
```

**[[Complete Dashboard Guide →|Visualization-Dashboard]]**

---

### New in v2.4.1: Hierarchical Clustering, Community Summaries & Auto-Backup

| Feature | Description |
|---------|-------------|
| **Hierarchical Leiden** | Recursive community detection — clusters within clusters up to 3 levels. "Python" → "FastAPI" → "Auth patterns" |
| **Community Summaries** | TF-IDF structured reports per cluster: key topics, projects, categories at a glance |
| **MACLA Confidence** | Bayesian Beta-Binomial scoring (arXiv:2512.18950) — calibrated confidence, not raw frequency |
| **Auto-Backup** | Configurable SQLite backups with retention policies, one-click restore from dashboard |
| **Profile UI** | Create, switch, delete profiles from the web dashboard — full isolation per context |
| **Profile Isolation** | All API endpoints (graph, clusters, patterns, timeline) scoped to active profile |

---

## 🔍 Advanced Search

SuperLocalMemory V2.2.0 implements **hybrid search** combining multiple strategies for maximum accuracy.

### Search Strategies

| Strategy | Method | Best For | Speed |
|----------|--------|----------|-------|
| **Semantic Search** | TF-IDF vectors + cosine similarity | Conceptual queries ("authentication patterns") | 45ms |
| **Full-Text Search** | SQLite FTS5 with ranking | Exact phrases ("JWT tokens expire") | 30ms |
| **Graph-Enhanced** | Knowledge graph traversal | Related concepts ("show auth-related") | 60ms |
| **Hybrid Mode** | All three combined | General queries | 80ms |

### Search Examples

```bash
# Semantic: finds conceptually similar
slm recall "security best practices"
# Matches: "JWT implementation", "OAuth flow", "CSRF protection"

# Exact: finds literal text
slm recall "PostgreSQL 15"
# Matches: exactly "PostgreSQL 15"

# Graph: finds related via clusters
slm recall "authentication" --use-graph
# Matches: JWT, OAuth, sessions (via "Auth & Security" cluster)

# Hybrid: best of all worlds (default)
slm recall "API design patterns"
# Combines semantic + exact + graph for optimal results
```

### Search Performance by Dataset Size

| Memories | Semantic | FTS5 | Graph | Hybrid |
|----------|----------|------|-------|--------|
| 100 | 35ms | 25ms | 50ms | 65ms |
| 500 | 45ms | 30ms | 60ms | 80ms |
| 1,000 | 55ms | 35ms | 70ms | 95ms |
| 5,000 | 85ms | 50ms | 110ms | 150ms |

**All search strategies remain sub-second even with 5,000+ memories.**

---

## ⚡ Performance

### Benchmarks (v2.2.0)

| Operation | Time | Comparison | Notes |
|-----------|------|------------|-------|
| **Add Memory** | < 10ms | - | Instant indexing |
| **Search (Hybrid)** | 80ms | 3.3x faster than v1 | 500 memories |
| **Graph Build** | < 2s | - | 100 memories |
| **Pattern Learning** | < 2s | - | Incremental |
| **Dashboard Load** | < 500ms | - | 1,000 memories |
| **Timeline Render** | < 300ms | - | All memories |

### Storage Efficiency

| Tier | Description | Compression | Savings |
|------|-------------|-------------|---------|
| **Tier 1** | Active memories (0-30 days) | None | - |
| **Tier 2** | Warm memories (30-90 days) | 60% | Progressive summarization |
| **Tier 3** | Cold storage (90+ days) | 96% | JSON archival |

**Example:** 1,000 memories with mixed ages = ~15MB (vs 380MB uncompressed)

### Scalability

| Dataset Size | Search Time | Graph Build | RAM Usage |
|--------------|-------------|-------------|-----------|
| 100 memories | 35ms | 0.5s | < 30MB |
| 500 memories | 45ms | 2s | < 50MB |
| 1,000 memories | 55ms | 5s | < 80MB |
| 5,000 memories | 85ms | 30s | < 150MB |

**Tested up to 10,000 memories** with linear scaling and no degradation.

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
| **OpenCode** | ✅ MCP | Native MCP tools |
| **Perplexity** | ✅ MCP | Native MCP tools |
| **Antigravity** | ✅ MCP + Skills | Native MCP tools |
| **ChatGPT** | ✅ MCP Connector | `search()` + `fetch()` via HTTP tunnel |
| **Aider** | ✅ Smart Wrapper | `aider-smart` with context |
| **Any Terminal** | ✅ Universal CLI | `slm remember "content"` |

### Three Ways to Access

1. **MCP (Model Context Protocol)** - Auto-configured for Cursor, Windsurf, Claude Desktop
   - AI assistants get natural access to your memory
   - No manual commands needed
   - "Remember that we use FastAPI" just works

2. **Skills & Commands** - For Claude Code, Continue.dev, Cody
   - `/superlocalmemoryv2:remember` in Claude Code
   - `/slm-remember` in Continue.dev and Cody
   - Familiar slash command interface

3. **Universal CLI** - Works in any terminal or script
   - `slm remember "content"` - Simple, clean syntax
   - `slm recall "query"` - Search from anywhere
   - `aider-smart` - Aider with auto-context injection

**All three methods use the SAME local database.** No data duplication, no conflicts.

### Auto-Detection

Installation automatically detects and configures:
- Existing IDEs (Cursor, Windsurf, VS Code)
- Installed tools (Aider, Continue, Cody)
- Shell environment (bash, zsh)

**Zero manual configuration required.** It just works.

### Manual Setup for Other Apps

Want to use SuperLocalMemory in ChatGPT, Perplexity, Zed, or other MCP-compatible tools?

**📘 Complete setup guide:** [docs/MCP-MANUAL-SETUP.md](docs/MCP-MANUAL-SETUP.md)

Covers:
- ChatGPT Desktop - Add via Settings → MCP
- Perplexity - Configure via app settings
- Zed Editor - JSON configuration
- Cody - VS Code/JetBrains setup
- Custom MCP clients - Python/HTTP integration

All tools connect to the **same local database** - no data duplication.

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

### Feature Comparison (What Actually Matters)

| Feature | Mem0 | Zep | Khoj | Letta | **SuperLocalMemory V2** |
|---------|------|-----|------|-------|------------------------|
| **Works in Cursor** | Cloud Only | ❌ | ❌ | ❌ | ✅ **Local** |
| **Works in Windsurf** | Cloud Only | ❌ | ❌ | ❌ | ✅ **Local** |
| **Works in VS Code** | 3rd Party | ❌ | Partial | ❌ | ✅ **Native** |
| **Works in Claude** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Works with Aider** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Universal CLI** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **7-Layer Universal Architecture** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Pattern Learning** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Multi-Profile Support** | ❌ | ❌ | ❌ | Partial | ✅ |
| **Knowledge Graphs** | ✅ | ✅ | ❌ | ❌ | ✅ |
| **100% Local** | ❌ | ❌ | Partial | Partial | ✅ |
| **Zero Setup** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Progressive Compression** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Completely Free** | Limited | Limited | Partial | ✅ | ✅ |

**SuperLocalMemory V2 is the ONLY solution that:**
- ✅ Works across 16+ IDEs and CLI tools
- ✅ Remains 100% local (no cloud dependencies)
- ✅ Completely free with unlimited memories

[See full competitive analysis →](docs/COMPETITIVE-ANALYSIS.md)

---

## ✨ Features

### Multi-Layer Memory Architecture

**[View Interactive Architecture Diagram](https://varun369.github.io/SuperLocalMemoryV2/architecture.html)** — Click any layer for details, research references, and file paths.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 9: VISUALIZATION (NEW v2.2.0)                        │
│  Interactive dashboard: timeline, search, graph explorer    │
│  Real-time analytics and visual insights                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 8: HYBRID SEARCH (NEW v2.2.0)                        │
│  Combines: Semantic + FTS5 + Graph traversal                │
│  80ms response time with maximum accuracy                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 7: UNIVERSAL ACCESS                                  │
│  MCP + Skills + CLI (works everywhere)                      │
│  16+ IDEs with single database                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 6: MCP INTEGRATION                                   │
│  Model Context Protocol: 6 tools, 4 resources, 2 prompts    │
│  Auto-configured for Cursor, Windsurf, Claude               │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: SKILLS LAYER                                      │
│  6 universal slash-commands for AI assistants               │
│  Compatible with Claude Code, Continue, Cody                │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: PATTERN LEARNING + MACLA (v2.4.0)                  │
│  Bayesian Beta-Binomial confidence (arXiv:2512.18950)       │
│  "You prefer React over Vue" (73% confidence)               │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: KNOWLEDGE GRAPH + HIERARCHICAL LEIDEN (v2.4.1)    │
│  Recursive clustering: "Python" → "FastAPI" → "Auth"        │
│  Community summaries + TF-IDF structured reports            │
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

### Knowledge Graph (It's Magic)

```bash
# Build the graph from your memories
python ~/.claude-memory/graph_engine.py build

# Output:
# ✓ Processed 47 memories
# ✓ Created 12 clusters:
#   - "Authentication & Tokens" (8 memories)
#   - "Performance Optimization" (6 memories)
#   - "React Components" (11 memories)
#   - "Database Queries" (5 memories)
#   ...
```

**The graph automatically discovers relationships.** Ask "what relates to auth?" and get JWT, session management, token refresh—even if you never tagged them together.

### Pattern Learning (It Knows You)

```bash
# Learn patterns from your memories
python ~/.claude-memory/pattern_learner.py update

# Get your coding identity
python ~/.claude-memory/pattern_learner.py context 0.5

# Output:
# Your Coding Identity:
# - Framework preference: React (73% confidence)
# - Style: Performance over readability (58% confidence)
# - Testing: Jest + React Testing Library (65% confidence)
# - API style: REST over GraphQL (81% confidence)
```

**Your AI assistant can now match your preferences automatically.**

**MACLA Confidence Scoring (v2.4.0):** Confidence uses a Bayesian Beta-Binomial posterior (Forouzandeh et al., [arXiv:2512.18950](https://arxiv.org/abs/2512.18950)). Pattern-specific priors, log-scaled competition, recency bonus. Range: 0.0–0.95 (hard cap prevents overconfidence).

### Multi-Profile Support

```bash
# Work profile
superlocalmemoryv2:profile create work --description "Day job"
superlocalmemoryv2:profile switch work

# Personal projects
superlocalmemoryv2:profile create personal
superlocalmemoryv2:profile switch personal

# Client projects (completely isolated)
superlocalmemoryv2:profile create client-acme
```

**Each profile has isolated memories, graphs, and patterns.** No context bleeding.

---

## 📖 Documentation

| Guide | Description |
|-------|-------------|
| [Quick Start](https://github.com/varun369/SuperLocalMemoryV2/wiki/Quick-Start-Tutorial) | Get running in 5 minutes |
| [Installation](https://github.com/varun369/SuperLocalMemoryV2/wiki/Installation) | Detailed setup instructions |
| [Visualization Dashboard](https://github.com/varun369/SuperLocalMemoryV2/wiki/Visualization-Dashboard) | Interactive web UI guide (NEW v2.2.0) |
| [CLI Reference](docs/CLI-COMMANDS-REFERENCE.md) | All commands explained |
| [Knowledge Graph](docs/GRAPH-ENGINE.md) | How clustering works |
| [Pattern Learning](docs/PATTERN-LEARNING.md) | Identity extraction |
| [Profiles Guide](docs/PROFILES-GUIDE.md) | Multi-context management |
| [API Reference](docs/API-REFERENCE.md) | Python API documentation |

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
python ~/.claude-memory/graph_engine.py build            # Build graph (+ hierarchical + summaries)
python ~/.claude-memory/graph_engine.py stats            # View clusters
python ~/.claude-memory/graph_engine.py related --id 5   # Find related
python ~/.claude-memory/graph_engine.py hierarchical     # Sub-cluster large communities
python ~/.claude-memory/graph_engine.py summaries        # Generate cluster summaries

# Pattern Learning
python ~/.claude-memory/pattern_learner.py update        # Learn patterns
python ~/.claude-memory/pattern_learner.py context 0.5   # Get identity

# Auto-Backup (v2.4.0)
python ~/.claude-memory/auto_backup.py backup            # Manual backup
python ~/.claude-memory/auto_backup.py list              # List backups
python ~/.claude-memory/auto_backup.py status            # Backup status

# Reset (Use with caution!)
superlocalmemoryv2:reset soft                            # Clear memories
superlocalmemoryv2:reset hard --confirm                  # Nuclear option
```

---

## 📊 Performance

**SEO:** Performance benchmarks, memory system speed, search latency, visualization dashboard performance

| Metric | Result | Notes |
|--------|--------|-------|
| **Hybrid search** | **80ms** | Semantic + FTS5 + Graph combined |
| **Semantic search** | **45ms** | 3.3x faster than v1 |
| **FTS5 search** | **30ms** | Exact phrase matching |
| **Graph build (100 memories)** | **< 2 seconds** | Leiden clustering |
| **Pattern learning** | **< 2 seconds** | Incremental updates |
| **Dashboard load** | **< 500ms** | 1,000 memories |
| **Timeline render** | **< 300ms** | All memories visualized |
| **Storage compression** | **60-96% reduction** | Progressive tiering |
| **Memory overhead** | **< 50MB RAM** | Lightweight |

**Tested up to 10,000 memories** with sub-second search times and linear scaling.

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas for contribution:**
- Additional pattern categories
- Graph visualization UI
- Integration with more AI assistants
- Performance optimizations
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
