<p align="center">
  <img src="https://img.shields.io/badge/🧠_SuperLocalMemory-V2-blueviolet?style=for-the-badge" alt="SuperLocalMemory V2"/>
</p>

<h1 align="center">Your AI Finally Remembers You</h1>

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
  <a href="https://github.com/sponsors/varun369">💖 Sponsor</a>
</p>

---

> **📢 Coming Soon:** [SuperLocalMemory V3](https://github.com/varun369/SuperLocalMemoryV3) with `npm install -g superlocalmemory` for even easier installation!
> **Using V2?** You're in the right place. V2 remains fully supported with all features.

## Choose Your Version

| Version | Installation | Best For |
|---------|--------------|----------|
| **[V3 (Coming Soon)](https://github.com/varun369/SuperLocalMemoryV3)** | `npm install -g superlocalmemory` | Most users - One-command install |
| **V2 (Current)** | `git clone` + `./install.sh` | Advanced users - Manual control |

Both versions have identical features and performance. V3 adds professional npm distribution.

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
# Install in 5 minutes
git clone https://github.com/varun369/SuperLocalMemoryV2.git && cd SuperLocalMemoryV2 && ./install.sh

# Save a memory
superlocalmemoryv2:remember "Fixed auth bug - JWT tokens were expiring too fast, increased to 24h"

# Later, in a new session...
superlocalmemoryv2:recall "auth bug"
# ✓ Found: "Fixed auth bug - JWT tokens were expiring too fast, increased to 24h"
```

**Your AI now remembers everything.** Forever. Locally. For free.

---

## 🚀 Quick Start

### Mac/Linux
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

---

## 🌐 Works Everywhere

**SuperLocalMemory V2 is the ONLY memory system that works across ALL your tools:**

### Supported IDEs & Tools

| Tool | Integration | How It Works |
|------|-------------|--------------|
| **Claude Code** | ✅ Native Skills | `/superlocalmemoryv2:remember` |
| **Cursor** | ✅ MCP Integration | AI automatically uses memory tools |
| **Windsurf** | ✅ MCP Integration | Native memory access |
| **Claude Desktop** | ✅ MCP Integration | Built-in support |
| **VS Code + Continue** | ✅ MCP + Skills | `/slm-remember` or AI tools |
| **VS Code + Cody** | ✅ Custom Commands | `/slm-remember` commands |
| **Aider** | ✅ Smart Wrapper | `aider-smart` with auto-context |
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
| **4-Layer Architecture** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Pattern Learning** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Multi-Profile Support** | ❌ | ❌ | ❌ | Partial | ✅ |
| **Knowledge Graphs** | ✅ | ✅ | ❌ | ❌ | ✅ |
| **100% Local** | ❌ | ❌ | Partial | Partial | ✅ |
| **Zero Setup** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Progressive Compression** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Completely Free** | Limited | Limited | Partial | ✅ | ✅ |

**SuperLocalMemory V2 is the ONLY solution that:**
- ✅ Works across 8+ IDEs and CLI tools
- ✅ Remains 100% local (no cloud dependencies)
- ✅ Completely free with unlimited memories

[See full competitive analysis →](docs/COMPETITIVE-ANALYSIS.md)

---

## ✨ Features

### 4-Layer Memory Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: PATTERN LEARNING                                  │
│  Learns: coding style, preferences, terminology             │
│  "You prefer React over Vue" (73% confidence)               │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: KNOWLEDGE GRAPH                                   │
│  Auto-clusters: "Auth & Tokens", "Performance", "Testing"   │
│  Discovers relationships you didn't know existed            │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: HIERARCHICAL INDEX                                │
│  Tree structure for fast navigation                         │
│  O(log n) lookups instead of O(n) scans                     │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: RAW STORAGE                                       │
│  SQLite + Full-text search + Embeddings                     │
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
| [Quick Start](QUICKSTART.md) | Get running in 5 minutes |
| [Installation](INSTALL.md) | Detailed setup instructions |
| [CLI Reference](docs/CLI-COMMANDS-REFERENCE.md) | All commands explained |
| [Knowledge Graph](docs/GRAPH_ENGINE_README.md) | How clustering works |
| [Pattern Learning](docs/PATTERN_LEARNER_README.md) | Identity extraction |
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
python ~/.claude-memory/graph_engine.py build            # Build graph
python ~/.claude-memory/graph_engine.py stats            # View clusters
python ~/.claude-memory/graph_engine.py related --id 5   # Find related

# Pattern Learning
python ~/.claude-memory/pattern_learner.py update        # Learn patterns
python ~/.claude-memory/pattern_learner.py context 0.5   # Get identity

# Reset (Use with caution!)
superlocalmemoryv2:reset soft                            # Clear memories
superlocalmemoryv2:reset hard --confirm                  # Nuclear option
```

---

## 📊 Performance

| Metric | Result |
|--------|--------|
| Search latency | **45ms** (3.3x faster than v1) |
| Graph build (100 memories) | **< 2 seconds** |
| Pattern learning | **< 2 seconds** |
| Storage compression | **60-96% reduction** |
| Memory overhead | **< 50MB RAM** |

Tested up to 5,000 memories with sub-second search times.

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
