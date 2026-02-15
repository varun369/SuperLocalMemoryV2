# Changelog

All notable changes to SuperLocalMemory V2 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Author

**Varun Pratap Bhardwaj**
*Solution Architect*

SuperLocalMemory V2 - Intelligent local memory system for AI coding assistants.

---

## [2.6.5] - 2026-02-16

### Added
- **Interactive Knowledge Graph** - Fully interactive visualization with zoom, pan, and click-to-explore capabilities
- **Mobile & Accessibility Support** - Touch gestures, keyboard navigation, and screen reader compatibility

---

## [2.6.0] - 2026-02-15

**Release Type:** Security Hardening & Scalability — "Battle-Tested"

### Added
- **Rate Limiting** - 100 writes/min and 300 reads/min per IP (stdlib-only, no dependencies)
- **API Key Authentication** - Optional API key auth via `~/.claude-memory/api_key` file
- **CI Workflow** - GitHub Actions test pipeline across Python 3.8, 3.10, and 3.12
- **Trust Enforcement** - Agents below 0.3 trust score blocked from write/delete
- **HNSW Vector Index** - O(log n) search with graceful TF-IDF fallback
- **Hybrid Search** - BM25 + Graph + TF-IDF fusion via `SLM_HYBRID_SEARCH=true`
- **SSRF Protection** - Webhook URLs validated against private IP ranges

### Changed
- **Graph cap raised to 10,000 memories** (was 5,000) with intelligent random sampling
- **Profile isolation hardened** - All queries enforce `WHERE profile = ?` filtering
- **Bounded write queue** - Max 1,000 pending operations (was unbounded)
- **TF-IDF optimization** - Skip rebuild when memory count changes <5%
- **Error sanitization** - Internal paths and table names stripped from 15 error sites
- **Connection pool capped** - Max 50 read connections

### Fixed
- Replaced bare `except:` clauses with specific exception types in hybrid_search.py and cache_manager.py

### Performance
See [wiki Performance Benchmarks](https://superlocalmemory.com/wiki/Performance-Benchmarks) for measured data.

---

## [2.5.1] - 2026-02-13

**Release Type:** Framework Integration — "Plugged Into the Ecosystem"

SuperLocalMemory is now a first-class memory backend for LangChain and LlamaIndex — the two largest AI/LLM frameworks.

### Added
- **LangChain Integration** - `langchain-superlocalmemory` package for persistent chat history
- **LlamaIndex Integration** - `llama-index-storage-chat-store-superlocalmemory` for ChatMemoryBuffer
- **Session isolation** - Framework memories tagged separately, never appear in normal `slm recall`

---

## [2.5.0] - 2026-02-12

**Release Type:** Major Feature Release — "Your AI Memory Has a Heartbeat"

SuperLocalMemory transforms from passive storage to active coordination layer. Every memory operation now triggers real-time events.

### Added
- **DbConnectionManager** - SQLite WAL mode, write queue, connection pool (fixes "database is locked")
- **Event Bus** - Real-time SSE/WebSocket/Webhook broadcasting with tiered retention (48h/14d/30d)
- **Subscription Manager** - Durable + ephemeral subscriptions with event filters
- **Webhook Dispatcher** - HTTP POST delivery with exponential backoff retry
- **Agent Registry** - Track connected AI agents (protocol, write/recall counters, last seen)
- **Provenance Tracker** - Track memory origin (created_by, source_protocol, trust_score, lineage)
- **Trust Scorer** - Bayesian trust signal collection (silent in v2.5, enforced in v2.6)
- **Dashboard: Live Events tab** - Real-time event stream with filters and stats
- **Dashboard: Agents tab** - Connected agents table with trust scores and protocol badges

### Changed
- **memory_store_v2.py** - Replaced 15 direct `sqlite3.connect()` calls with DbConnectionManager
- **mcp_server.py** - Replaced 9 per-call instantiations with shared singleton
- **ui_server.py** - Refactored from 2008-line monolith to 194-line app shell + 9 route modules
- **ui/app.js** - Split from 1588-line monolith to 13 modular files

### Testing
- 63 pytest tests + 27 e2e tests + 15 fresh-DB edge cases + 17 backward-compat tests

---

## [2.4.2] - 2026-02-11

**Release Type:** Bug Fix

### Fixed
- Profile isolation bug in UI dashboard - Graph stats now filter by active profile

---

## [2.4.1] - 2026-02-11

**Release Type:** Hierarchical Clustering & Documentation

### Added
- **Hierarchical Leiden clustering** - Large clusters auto-subdivided up to 3 levels deep
- **Community summaries** - TF-IDF structured reports for every cluster
- Schema migration for `summary`, `parent_cluster_id`, `depth` columns

---

## [2.4.0] - 2026-02-11

**Release Type:** Profile System & Intelligence

### Added
- **Column-based memory profiles** - Single DB with `profile` column, instant switching via `profiles.json`
- **Auto-backup system** - Configurable interval, retention policy, one-click backup from UI
- **MACLA confidence scorer** - Beta-Binomial Bayesian posterior (arXiv:2512.18950)
- **UI: Profile Management** - Create, switch, delete profiles from dashboard
- **UI: Settings tab** - Auto-backup config, history, profile management
- **UI: Column sorting** - Click headers in Memories table

---

## [2.3.7] - 2026-02-09

### Added
- `--full` flag to show complete memory content without truncation
- Smart truncation: <5000 chars shown in full, ≥5000 chars truncated to 2000 chars

### Fixed
- CLI bug: `get` command now uses correct `get_by_id()` method

---

## [2.3.5] - 2026-02-09

### Added
- **ChatGPT Connector Support** - `search(query)` and `fetch(id)` MCP tools
- **Streamable HTTP transport** - `slm serve --transport streamable-http`
- **UI enhancements** - Memory detail modal, dark mode, export buttons, search score bars

### Fixed
- XSS vulnerability via inline onclick replaced with safe event delegation

---

## [2.3.0] - 2026-02-08

**Release Type:** Universal Integration

SuperLocalMemory now works across 16+ IDEs and CLI tools.

### Added
- **MCP configs** - Auto-detection for Cursor, Windsurf, Claude Desktop, Continue.dev, Codex, Copilot, Gemini, JetBrains
- **Universal CLI wrapper** - `slm` command works in any terminal
- **Skills installer expansion** - Cursor, VS Code/Copilot auto-configured
- **Tool annotations** - `readOnlyHint`, `destructiveHint`, `openWorldHint` for all MCP tools

---

## [2.2.0] - 2026-02-07

**Release Type:** Feature Release (Optional Search Components)

### Added
- **BM25 Search Engine** - Okapi BM25 with <30ms search for 1K memories
- **Query Optimizer** - Spell correction, query expansion, technical term preservation
- **Cache Manager** - LRU cache with TTL, <0.1ms cache hit overhead
- **Hybrid Search System** - BM25 + TF-IDF + Graph fusion, <50ms for 1K memories
- **HNSW Index** - Sub-10ms search for 10K memories (optional: `pip install hnswlib`)
- **Embedding Engine** - Local semantic embeddings with GPU acceleration (optional: `pip install sentence-transformers`)
- **Modular Requirements** - Separate files: `requirements-ui.txt`, `requirements-search.txt`, `requirements-full.txt`
- **Installation Verification** - `verify-install.sh` script for comprehensive health checks

---

## [2.1.0-universal] - 2026-02-07

**Release Type:** Major Feature Release - Universal Integration

### Added
- **6 Universal Skills** - remember, recall, list-recent, status, build-graph, switch-profile
- **MCP Server** - 6 tools, 4 resources, 2 prompts for native IDE integration
- **6-layer Attribution Protection** - Source headers, docs, database metadata, runtime banners, license, digital signature
- **11+ IDE Support** - Cursor, Windsurf, Claude Desktop, Continue.dev, Cody, Aider, ChatGPT, Perplexity, Zed, OpenCode, Antigravity

### Documentation
- `docs/MCP-MANUAL-SETUP.md` - Manual setup guide for 8+ additional IDEs
- `docs/MCP-TROUBLESHOOTING.md` - Debugging guide with 20+ common issues
- `docs/UNIVERSAL-INTEGRATION.md` - Complete universal strategy (15,000+ words)

---

## [2.0.0] - 2026-02-05

### Initial Release - Complete Rewrite

SuperLocalMemory V2 represents a complete architectural rewrite with intelligent knowledge graphs, pattern learning, and enhanced organization.

### Added
- **4-Layer Architecture** - Enhanced Storage, Hierarchical Index, Knowledge Graph, Pattern Learning
- **TF-IDF Entity Extraction** - Automatic entity discovery with frequency weighting
- **Leiden Clustering** - Community detection for automatic thematic grouping
- **Pattern Learning** - Multi-dimensional analysis (frameworks, languages, architecture, security, coding style)
- **Compression System** - Progressive summarization (Tier 1: 0%, Tier 2: 60%, Tier 3: 96%)
- **Profile Management** - Multi-profile support with isolated databases

### Performance
- 3.3x faster search (45ms vs 150ms in V1)
- 60-96% storage reduction with compression

### Research Foundation
Built on GraphRAG (Microsoft), PageIndex (VectifyAI), MemoryBank (AAAI 2024), A-RAG

---

## Archive

See [CHANGELOG-ARCHIVE.md](CHANGELOG-ARCHIVE.md) for detailed release notes from v2.0.0 through v2.4.x.

---

## Versioning

We use [Semantic Versioning](https://semver.org/):
- **MAJOR:** Breaking changes (e.g., 2.0.0 → 3.0.0)
- **MINOR:** New features (backward compatible, e.g., 2.0.0 → 2.1.0)
- **PATCH:** Bug fixes (backward compatible, e.g., 2.1.0 → 2.1.1)

**Current Version:** v2.6.5
**Website:** [superlocalmemory.com](https://superlocalmemory.com)
**npm:** `npm install -g superlocalmemory`

---

## License

SuperLocalMemory V2 is released under the [MIT License](LICENSE).

---

**100% local. 100% private. 100% yours.**
