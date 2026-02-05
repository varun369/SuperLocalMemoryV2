# SuperLocalMemory V2

**Standalone intelligent memory system with knowledge graphs, pattern learning, and intelligent organization.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Local First](https://img.shields.io/badge/local--first-100%25-brightgreen)](https://github.com/varun369/SuperLocalMemoryV2)
[![Zero Setup](https://img.shields.io/badge/setup-5%20minutes-orange)](https://github.com/varun369/SuperLocalMemoryV2)

**Created by [Varun Pratap Bhardwaj](https://github.com/varun369)** | [Report Issues](https://github.com/varun369/SuperLocalMemoryV2/issues)

---

## Why SuperLocalMemory V2?

SuperLocalMemory V2 is a **standalone intelligent memory system** that builds a living knowledge graph from your work. It discovers relationships between memories, learns your preferences, and adapts to your coding style over time.

**Works with Claude CLI, other AI assistants, or standalone via terminal.**

**100% local. Zero external APIs. Complete privacy.**

**Independent system** built on 2026 cutting-edge research:
- **PageIndex** (hierarchical RAG)
- **GraphRAG** (knowledge graphs)
- **xMemory** (pattern learning)
- **A-RAG** (multi-level retrieval)

**Integration Options:**
- Works with Claude CLI via plugin skills
- Works with any AI assistant via API/CLI
- Works standalone via terminal commands
- No dependencies on external services

### Feature Comparison

| Feature | Mem0 | Zep | Khoj | MCP Servers | **SuperLocalMemory V2** |
|---------|------|-----|------|-------------|------------------------|
| Zero Setup Required | ❌ | ❌ | ❌ | ⚠️ | ✅ |
| 4-Layer Architecture | ❌ | ❌ | ❌ | ❌ | ✅ |
| Pattern Learning | ❌ | ❌ | ❌ | ❌ | ✅ |
| Multi-Profile Support | ❌ | ❌ | ❌ | ❌ | ✅ |
| Progressive Compression | ❌ | ❌ | ❌ | ❌ | ✅ |
| 100% Local | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ |
| Claude CLI Native | ❌ | ❌ | ❌ | MCP | ✅ Skills |

**SuperLocalMemory V2 is the only solution offering all these features together.**

---

## Key Features

### 4-Layer Memory Architecture
- **Layer 1: Raw Storage** - SQLite database with full-text search and embeddings
- **Layer 2: Hierarchical Index** - PageIndex-style tree structure for fast navigation
- **Layer 3: Knowledge Graph** - Auto-discovered relationships using TF-IDF + Leiden clustering
- **Layer 4: Pattern Learning** - Identity profiles extracted from your memories (coding preferences, terminology, style)

### Intelligent Organization
- **Knowledge Graph**: Auto-discovers thematic clusters (e.g., "Authentication & Tokens", "Performance & Code")
- **Pattern Learning**: Learns your preferences (frameworks, coding style, terminology) with confidence scoring
- **Progressive Summarization**: Tier-based compression (60-96% space savings) without losing information
- **Multi-Profile Support**: Separate memory contexts for different projects, clients, or AI personalities

### Production-Ready Features
- **Safe Reset System**: Soft/hard/layer-selective resets with automatic backups
- **CLI Commands**: User-friendly wrappers with safety warnings and confirmations
- **Fast Performance**: 3.3x faster search, sub-second graph builds for 100+ memories

---

## Quick Start

### Installation

**Mac/Linux:**
```bash
# Clone the repository
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2

# Run installation script
./install.sh

# Add CLI commands to your PATH (optional but recommended)
echo 'export PATH="${HOME}/.claude-memory/bin:${PATH}"' >> ~/.zshrc
source ~/.zshrc
```

**Windows (PowerShell):**
```powershell
# Clone the repository
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2

# Run installation script (right-click PowerShell > Run as Administrator)
.\install.ps1

# Add CLI commands to your PATH (add to PowerShell profile)
$env:PATH += ";$env:USERPROFILE\.claude-memory\bin"
```

**Requirements:**
- Python 3.8+ ([Download](https://python.org))
- SQLite3 (usually pre-installed)
- Standard library only (no external dependencies for core features)
- Works on: macOS, Linux, Windows 10/11

### 5-Minute Setup

```bash
# 1. Check system status
memory-status

# 2. Build knowledge graph from your memories
~/.claude-memory/venv/bin/python ~/.claude-memory/graph_engine.py build

# 3. Learn patterns from your coding history
~/.claude-memory/venv/bin/python ~/.claude-memory/pattern_learner.py update

# 4. View discovered patterns
~/.claude-memory/venv/bin/python ~/.claude-memory/pattern_learner.py list 0.1

# Done! Your memory system is now intelligent.
```

### Basic Usage

```bash
# Add a memory (via Python API)
python ~/.claude-memory/memory_store_v2.py add "Built authentication with JWT" --tags auth,security

# Search memories
python ~/.claude-memory/memory_store_v2.py search "authentication"

# Find related memories via knowledge graph
~/.claude-memory/venv/bin/python ~/.claude-memory/graph_engine.py related --memory-id 5

# View discovered clusters
~/.claude-memory/venv/bin/python ~/.claude-memory/graph_engine.py stats
```

### Claude CLI Integration (Optional)

**Want to use SuperLocalMemory V2 directly from Claude CLI?** Install optional skills for convenient slash commands.

```bash
# Install Claude CLI skills
cd SuperLocalMemoryV2-repo
./install-skills.sh

# Restart Claude CLI, then use:
/superlocalmemoryv2:remember "Built authentication with JWT" --tags auth,security
/superlocalmemoryv2:search "authentication"
/superlocalmemoryv2:graph-build
/superlocalmemoryv2:status
```

**Available Skills:**
- `/superlocalmemoryv2:remember` - Add memories
- `/superlocalmemoryv2:search` - Search memories
- `/superlocalmemoryv2:graph-build` - Build knowledge graph
- `/superlocalmemoryv2:graph-stats` - View statistics
- `/superlocalmemoryv2:patterns` - Learn coding patterns
- `/superlocalmemoryv2:status` - System status

**Important:** Claude CLI integration is **completely optional**. SuperLocalMemory V2 works as a standalone system via terminal commands, Python API, or with any AI assistant.

**Installation guide:** See [claude-skills/INSTALLATION.md](claude-skills/INSTALLATION.md)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│ SuperLocalMemory V2 - 4-Layer Architecture                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 4: Pattern Learning (Identity Profiles)              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Frequency Analysis · Context Analysis              │    │
│  │ Terminology Learning · Confidence Scoring          │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Layer 3: Knowledge Graph (GraphRAG)                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │ TF-IDF Entity Extraction · Leiden Clustering       │    │
│  │ Auto-naming · Relationship Discovery               │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Layer 2: Hierarchical Index (PageIndex)                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Tree Structure · Parent-Child Links                │    │
│  │ Fast Navigation · Contextual Grouping              │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Layer 1: Raw Storage (SQLite)                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Full-Text Search · Vector Embeddings               │    │
│  │ Tags · Metadata · Compression Archives             │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**For detailed architecture documentation, see:**
- [Complete Feature List](docs/COMPLETE-FEATURE-LIST.md)
- [Graph Engine Details](docs/GRAPH_ENGINE_README.md)
- [Pattern Learning System](docs/PATTERN_LEARNER_README.md)
- [Compression System](docs/COMPRESSION-README.md)

---

## CLI Command Reference

### Status & Information
```bash
# Check overall system status
memory-status
```

### Profile Management
```bash
# List all profiles
memory-profile list

# Create new profile
memory-profile create work --description "Work projects"

# Switch profile (requires CLI restart)
memory-profile switch work

# Delete profile (with confirmation)
memory-profile delete old-profile
```

### Reset Commands (Use with Caution)
```bash
# Soft reset (clear memories, keep schema)
memory-reset soft

# Hard reset (nuclear option - delete everything)
memory-reset hard --confirm

# Layer-specific reset
memory-reset layer --layers graph patterns
```

### Knowledge Graph Operations
```bash
# Build/rebuild graph
~/.claude-memory/venv/bin/python ~/.claude-memory/graph_engine.py build

# Show statistics
~/.claude-memory/venv/bin/python ~/.claude-memory/graph_engine.py stats

# Find related memories
~/.claude-memory/venv/bin/python ~/.claude-memory/graph_engine.py related --memory-id 5

# View cluster members
~/.claude-memory/venv/bin/python ~/.claude-memory/graph_engine.py cluster --cluster-id 1
```

### Pattern Learning
```bash
# Update patterns from memories
~/.claude-memory/venv/bin/python ~/.claude-memory/pattern_learner.py update

# List learned patterns (confidence >= 10%)
~/.claude-memory/venv/bin/python ~/.claude-memory/pattern_learner.py list 0.1

# Get Claude-formatted context (high-confidence patterns)
~/.claude-memory/venv/bin/python ~/.claude-memory/pattern_learner.py context 0.7

# Show statistics
~/.claude-memory/venv/bin/python ~/.claude-memory/pattern_learner.py stats
```

**Full command documentation: [CLI Commands Reference](docs/CLI-COMMANDS-REFERENCE.md)**

---

## Documentation

### Getting Started
- [Installation Guide](INSTALL.md)
- [Quick Start Guide](QUICKSTART.md)
- [Complete Feature List](docs/COMPLETE-FEATURE-LIST.md)
- [CLI Commands Reference](docs/CLI-COMMANDS-REFERENCE.md)

### Core Features
- [Knowledge Graph Engine](docs/GRAPH_ENGINE_README.md)
- [Pattern Learning System](docs/PATTERN_LEARNER_README.md)
- [Progressive Summarization](docs/COMPRESSION-README.md)
- [Profile Management](docs/PROFILES-GUIDE.md)
- [UI Server](docs/UI-SERVER.md)

### Advanced Topics
- [Reset System Guide](docs/RESET-GUIDE.md)
- [Architecture Details](ARCHITECTURE.md)

---

## Use Cases

### Knowledge Discovery
**"What memories relate to authentication?"**

The knowledge graph automatically clusters related memories. Just query the cluster:
```bash
~/.claude-memory/venv/bin/python ~/.claude-memory/graph_engine.py cluster --cluster-id 10
# Shows: JWT, React auth, token management (auto-discovered cluster)
```

### Pattern Recognition
**"What coding style have I shown?"**

The pattern learner analyzes your memories:
```bash
~/.claude-memory/venv/bin/python ~/.claude-memory/pattern_learner.py context 0.5
# Output: "Performance over readability" (53% confidence)
#         "Frontend preference: React" (27% confidence)
```

### Multi-Context Management
**"Work on different client projects with isolated memories"**

```bash
# Create client-specific profile
memory-profile create client-acme
memory-profile switch client-acme
# Isolated memories, patterns, and graph per client
```

---

## Performance

**Benchmarks (on 20-500 memories):**
- Search time: **150ms → 45ms** (3.3x faster)
- Graph build: **<0.03 seconds** (20 memories)
- Pattern learning: **<2 seconds** (20 memories)
- Database size: **60% reduction** with compression

**Scalability tested:**
- 20 memories: Instant
- 100 memories: <2 seconds
- 500 memories: ~15 seconds (acceptable for weekly rebuild)

---

## Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes** with clear commit messages
4. **Write or update tests** if applicable
5. **Submit a pull request**

### Development Guidelines
- Follow PEP 8 for Python code
- Add docstrings for new functions/classes
- Update documentation for new features
- Test on Python 3.8+ before submitting

### Areas for Contribution
- Additional pattern learning categories
- Graph visualization tools
- Performance optimizations
- Integration with other AI assistants
- UI/web interface improvements

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**TL;DR:** You can use, modify, and distribute this software freely, even for commercial purposes, as long as you include the original license.

---

## Support & Community

- **Issues**: [GitHub Issues](https://github.com/varun369/SuperLocalMemoryV2/issues)
- **Documentation**: [Full Docs](docs/)
- **Discussions**: [GitHub Discussions](https://github.com/varun369/SuperLocalMemoryV2/discussions)

---

## Author

**Varun Pratap Bhardwaj** - Solution Architect

- GitHub: [@varun369](https://github.com/varun369)
- Repository: [SuperLocalMemoryV2](https://github.com/varun369/SuperLocalMemoryV2)

If you find this project useful, please give it a star on GitHub!

---

## Acknowledgments

Built on research from:
- **GraphRAG** (Microsoft Research) - Knowledge graph construction
- **PageIndex** (Meta AI) - Hierarchical indexing
- **xMemory** (Stanford) - Identity pattern learning
- **A-RAG** - Multi-level retrieval architecture

---

**Ready to build intelligent memory for your AI assistant?**

```bash
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2-repo
./install.sh
memory-status
```

**100% local. 100% private. 100% yours.**
