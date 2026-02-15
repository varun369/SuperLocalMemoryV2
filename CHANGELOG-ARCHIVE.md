# Changelog Archive

This file contains detailed release notes for SuperLocalMemory V2 versions 2.0.0 through 2.4.x.

For recent releases, see [CHANGELOG.md](CHANGELOG.md).

---

## [2.4.2] - 2026-02-11

**Release Type:** Bug Fix Release
**Backward Compatible:** Yes

### Fixed
- **Profile isolation bug in UI dashboard**: Graph nodes and connections were displaying global counts instead of profile-filtered counts. New/empty profiles incorrectly showed data from other profiles. Fixed by adding `JOIN memories` and `WHERE m.profile = ?` filter to graph stats queries in `ui_server.py` (`/api/stats` endpoint, lines 986-990).

---

## [2.4.1] - 2026-02-11

**Release Type:** Hierarchical Clustering & Documentation Release
**Backward Compatible:** Yes (additive schema changes only)

### Added
- **Hierarchical Leiden clustering** (`graph_engine.py`): Recursive community detection — large clusters (≥10 members) are automatically sub-divided up to 3 levels deep. E.g., "Python" → "FastAPI" → "Authentication patterns". New `parent_cluster_id` and `depth` columns in `graph_clusters` table
- **Community summaries** (`graph_engine.py`): TF-IDF structured reports for every cluster — key topics, projects, categories, hierarchy context. Stored in `graph_clusters.summary` column, surfaced in `/api/clusters` endpoint and web dashboard
- **CLI commands**: `python3 graph_engine.py hierarchical` and `python3 graph_engine.py summaries` for manual runs
- **Schema migration**: Safe `ALTER TABLE` additions for `summary`, `parent_cluster_id`, `depth` columns — backward compatible with existing databases

### Changed
- `build_graph()` now automatically runs hierarchical sub-clustering and summary generation after flat Leiden
- `/api/clusters` endpoint returns `summary`, `parent_cluster_id`, `depth` fields
- `get_stats()` includes `max_depth` and per-cluster summary/hierarchy data
- `setup_validator.py` schema updated to include new columns

### Documentation
- **README.md**: v2.4.0→v2.4.1, added Hierarchical Leiden, Community Summaries, MACLA, Auto-Backup sections
- **Wiki**: Updated Roadmap, Pattern-Learning-Explained, Knowledge-Graph-Guide, Configuration, Visualization-Dashboard, Footer
- **Website**: Updated features.astro, comparison.astro, index.astro for v2.4.1 features
- **`.npmignore`**: Recursive `__pycache__` exclusion patterns

---

## [2.4.0] - 2026-02-11

**Release Type:** Profile System & Intelligence Release
**Backward Compatible:** Yes (additive schema changes only)

### Added
- **Column-based memory profiles**: Single `memory.db` with `profile` column — all memories, clusters, patterns, and graph data are profile-scoped. Switch profiles from any IDE/CLI and it takes effect everywhere instantly via shared `profiles.json`
- **Auto-backup system** (`src/auto_backup.py`): SQLite backup API with configurable interval (daily/weekly), retention policy, and one-click backup from UI
- **MACLA confidence scorer**: Research-grounded Beta-Binomial Bayesian posterior (arXiv:2512.18950) replaces ad-hoc log2 formula. Pattern-specific priors: preference(1,4), style(1,5), terminology(2,3). Log-scaled competition prevents over-dilution from sparse signals
- **UI: Profile Management**: Create, switch, and delete profiles from the web dashboard. "+" button in navbar for quick creation, full management table in Settings tab
- **UI: Settings tab**: Auto-backup status, configuration (interval, max backups, enable toggle), backup history, profile management — all in one place
- **UI: Column sorting**: Click any column header in the Memories table to sort asc/desc
- **UI: Enhanced Patterns view**: DOM-based rendering with confidence bars, color coding, type icons
- **API: Profile isolation on all endpoints**: `/api/graph`, `/api/clusters`, `/api/patterns`, `/api/timeline` now filter by active profile (previously showed all profiles)
- **API: `get_active_profile()` helper**: Shared function in `ui_server.py` replaces 4 duplicate inline profile-reading blocks
- **API: Profile CRUD endpoints**: `POST /api/profiles/create`, `DELETE /api/profiles/{name}` with validation and safety (can't delete default or active profile)

### Fixed
- **Profile switching ValueError**: Rewrote from directory-based to column-based profiles — no more file copy errors on switch
- **Pattern learner schema validation**: Safe column addition with try/except for `profile` column on `identity_patterns` table
- **Graph engine schema validation**: Safe column check before profile-filtered queries
- **Research references**: PageIndex correctly attributed to VectifyAI (not Meta AI), removed fabricated xMemory/Stanford citation, replaced with MemoryBank (AAAI 2024) across wiki and website
- **Graph tooltip**: Shows project name or Memory ID instead of "Uncategorized" when category is null

### Changed
- All 4 core layers (storage, tree, graph, patterns) are now profile-aware
- `memory_store_v2.py`: Every query filters by `WHERE profile = ?` from `_get_active_profile()`
- `graph_engine.py`: `build_graph()` and `get_stats()` scoped to active profile
- `pattern_learner.py`: Pattern learning and retrieval scoped to active profile
- `ui_server.py`: Refactored profile code into shared helper, eliminated 4 duplicate blocks

### Technical Details
- Schema: `ALTER TABLE memories ADD COLUMN profile TEXT DEFAULT 'default'`
- Schema: `ALTER TABLE identity_patterns ADD COLUMN profile TEXT DEFAULT 'default'`
- MACLA formula: `posterior = (alpha + evidence) / (alpha + beta + evidence + log2(total_memories))`
- Confidence range: 0.0 to 0.95 (capped), with recency and distribution bonuses
- Backup: Uses SQLite `backup()` API for safe concurrent backup
- 17 API endpoint tests, 5 core module tests — all passing

---

## [2.3.7] - 2026-02-09

### Added
- **--full flag**: Show complete memory content without truncation in search/list/recent/cluster commands
- **Smart truncation**: Memories <5000 chars shown in full, ≥5000 chars truncated to 2000 chars (previously always truncated at 200 chars)
- **Help text**: Added --full flag documentation to CLI help output

### Fixed
- **CLI bug**: Fixed `get` command error - `get_memory()` → `get_by_id()` method call
- **Content display**: Recall now shows full content for short/medium memories instead of always truncating at 200 chars
- **User experience**: Agents and users can now see complete memory content by default for most memories

### Changed
- **Truncation logic**: 200 char limit → 2000 char preview for memories ≥5000 chars
- **Node.js wrappers**: memory-recall-skill.js and memory-list-skill.js updated to pass --full flag through

### Technical Details
- Added `format_content()` helper function in memory_store_v2.py (line 918)
- Updated search/list/recent/cluster commands to use smart truncation
- Backward compatible: same output structure, MCP/API calls unaffected
- All 74+ existing memories tested: short memories show full, long memories truncate intelligently

---

## [2.3.5] - 2026-02-09

### Added
- **ChatGPT Connector Support**: `search(query)` and `fetch(id)` MCP tools per OpenAI spec
- **Streamable HTTP transport**: `slm serve --transport streamable-http` for ChatGPT 2026+
- **UI: Memory detail modal**: Click any memory row to see full content, tags, metadata
- **UI: Dark mode toggle**: Sun/moon icon in navbar, saved to localStorage, respects system preference
- **UI: Export buttons**: Export All (JSON/JSONL), Export Search Results, Export individual memory as Markdown
- **UI: Search score bars**: Color-coded relevance bars (red/yellow/green) in search results
- **UI: Animated stat counters**: Numbers animate up on page load with ease-out cubic
- **UI: Loading spinners and empty states**: Professional feedback across all tabs
- npm keywords: chatgpt, chatgpt-connector, openai, deep-research

### Fixed
- **XSS vulnerability**: Replaced inline onclick with JSON injection with safe event delegation
- **UI: Content preview**: Increased from 80 to 100 characters

### Changed
- npm package now includes `ui/`, `ui_server.py`, `api_server.py`

---

## [2.3.0] - 2026-02-08

**Release Type:** Universal Integration Release
**Release Date:** February 8, 2026
**Version Code:** 2.3.0-universal
**Git Tag:** v2.3.0
**Backward Compatible:** ✅ Yes (100%)

### 🌐 Universal Integration — MAJOR UPDATE

**SuperLocalMemory now works across 16+ IDEs and CLI tools!**

This release fixes the Claude-first distribution gap by adding proper configs, detection, and integration for the tools where most non-Claude developers live.

**Root Cause:** The architecture was always universal (SQLite + MCP + Skills), but the distribution (configs, installer, docs, npm) was Claude-first with bolted-on support for others. This release fixes that.

### ✨ Added — New Integrations

**New Config Templates:**
- ✅ `configs/codex-mcp.toml` — OpenAI Codex CLI (TOML format, not JSON)
- ✅ `configs/vscode-copilot-mcp.json` — VS Code / GitHub Copilot (`"servers"` format)
- ✅ `configs/gemini-cli-mcp.json` — Google Gemini CLI
- ✅ `configs/jetbrains-mcp.json` — JetBrains IDEs (IntelliJ, PyCharm, WebStorm)

**New install.sh Detections:**
- ✅ OpenAI Codex CLI — Auto-configures via `codex mcp add` or TOML fallback
- ✅ VS Code / GitHub Copilot — Creates `~/.vscode/mcp.json`
- ✅ Gemini CLI — Merges into `~/.gemini/settings.json`
- ✅ JetBrains IDEs — Prints manual setup instructions (GUI-based)

**New CLI Command:**
- ✅ `slm serve [PORT]` — Start MCP HTTP server for ChatGPT/remote access
  - Default port: 8001
  - Documents ngrok/cloudflared tunnel workflow
  - Enables ChatGPT integration (previously broken)

**Universal Symlink:**
- ✅ `~/.superlocalmemory` → `~/.claude-memory` — Non-Claude users see universal branding
  - Zero breaking changes (real directory unchanged)
  - Additive only (removing symlink doesn't break anything)

**MCP Tool Annotations:**
- ✅ All 6 tools annotated with `readOnlyHint`, `destructiveHint`, `openWorldHint`
  - Required by ChatGPT and VS Code Copilot for tool classification
  - Uses `ToolAnnotations` from MCP SDK

**Skills Installer Expansion:**
- ✅ Added Cursor to `install-skills.sh`
- ✅ Added VS Code/Copilot to `install-skills.sh`
- ✅ Added `--auto` flag for non-interactive mode
- ✅ `install.sh` now calls `install-skills.sh --auto` automatically

### 🔧 Fixed

**ChatGPT Integration (was broken):**
- Old config used stdio — ChatGPT only supports HTTP transport
- New: `slm serve` + tunnel workflow documented
- Config file replaced with setup instructions

### 📝 Documentation Updates

**docs/MCP-MANUAL-SETUP.md:**
- Added: OpenAI Codex CLI section
- Added: VS Code / GitHub Copilot section
- Added: Gemini CLI section
- Added: JetBrains IDEs section
- Added: HTTP Transport section
- Fixed: ChatGPT section (HTTP workflow replaces broken stdio instructions)

**README.md:**
- Expanded IDE table from 8 to 17 rows
- Updated "11+ IDEs" → "16+ IDEs" everywhere

### 🔢 Version Bumps

| File | Old | New |
|------|-----|-----|
| `package.json` | 2.1.0 | 2.3.0 |
| `mcp_server.py` | 2.1.0-universal | 2.3.0-universal |
| `bin/slm` | 2.1.0-universal | 2.3.0-universal |
| `CLAUDE.md` | 2.1.0-universal | 2.3.0-universal |
| `postinstall.js` | "11+ AI tools" | "16+ AI tools" |

### 🔒 Backward Compatibility

**100% backward compatible — nothing breaks:**
- ✅ Existing `~/.claude-memory/` data untouched
- ✅ Existing MCP configs (Claude, Cursor, etc.) untouched
- ✅ Existing skills untouched
- ✅ Existing `slm` commands untouched (`serve` is NEW)
- ✅ npm reinstall safe (backs up before overwriting)
- ✅ `git pull && ./install.sh` safe for existing users

### 🎊 Credits

**Philosophy:** The architecture was already universal. This release makes the distribution universal too.

**Author:** Varun Pratap Bhardwaj (Solution Architect)

---

## [2.2.0] - 2026-02-07

**Release Type:** Feature Release (Optional Search Components)
**Release Date:** February 7, 2026
**Version Code:** 2.2.0
**Git Tag:** v2.2.0
**Backward Compatible:** ✅ Yes (100%)

### 🚀 Core Search Engine Components (Tasks #17 & #20)

**Production-Grade BM25 and Hybrid Search:**
- ✅ **BM25 Search Engine** (`src/search_engine_v2.py`) - Industry-standard keyword ranking
  - Pure Python implementation (no external dependencies for algorithm)
  - Okapi BM25 with configurable parameters (k1=1.5, b=0.75)
  - <30ms search for 1K memories (target met)
  - Inverted index with efficient postings
  - Full tokenization and stopword filtering
  - CLI interface for testing and demos

- ✅ **Query Optimizer** (`src/query_optimizer.py`) - Intelligent query enhancement
  - Spell correction using Levenshtein edit distance (max distance: 2)
  - Query expansion based on term co-occurrence
  - Boolean operator parsing (AND, OR, NOT, phrase queries)
  - Technical term preservation (API, SQL, JWT, etc.)
  - Vocabulary-based correction with graceful fallback

- ✅ **Cache Manager** (`src/cache_manager.py`) - LRU cache for search results
  - Least Recently Used (LRU) eviction policy
  - Time-to-live (TTL) support for cache expiration
  - Thread-safe operations (optional)
  - Size-based eviction with configurable max entries
  - Performance tracking (hit rate, evictions, access counts)
  - <0.1ms cache hit overhead

- ✅ **Hybrid Search System** (`src/hybrid_search.py`) - Multi-method retrieval fusion
  - Combines BM25 + TF-IDF + Graph traversal
  - Weighted score fusion with configurable weights
  - Reciprocal Rank Fusion (RRF) support
  - <50ms hybrid search for 1K memories (target met)
  - Automatic integration with MemoryStoreV2
  - Backward compatible with existing search API

**Key Features:**
- 🎯 **3x faster search** - BM25 optimized vs basic FTS
- 📈 **Better relevance** - 15-20% precision improvement over TF-IDF
- 🧠 **Query intelligence** - Auto-corrects typos, expands terms
- 🔄 **Multi-method fusion** - Best of keyword, semantic, and graph
- ⚡ **Production caching** - 30-50% cache hit rates reduce load
- 📊 **Complete test suite** - `test_search_engine.py` with 8 test cases

**Performance Benchmarks:**
| Component | Target | Actual | Status |
|-----------|--------|--------|--------|
| BM25 Index 1K | <500ms | 247ms | ✅ |
| BM25 Search 1K | <30ms | 18ms | ✅ |
| Query Optimizer | <5ms | 2ms | ✅ |
| Cache Get/Put | <0.5ms | 0.12ms | ✅ |
| Hybrid Search | <50ms | 35ms | ✅ |

**Attribution:**
- Copyright headers on all new files
- MIT License compliance
- Created by Varun Pratap Bhardwaj
- Comprehensive documentation: `docs/SEARCH-ENGINE-V2.2.0.md`

### 🚀 Optional Search Components (Tasks #18 & #19)

**New High-Performance Search Infrastructure:**
- ✅ **HNSW Index** (`src/hnsw_index.py`) - Fast approximate nearest neighbor search
  - Sub-10ms search for 10K memories
  - Sub-50ms search for 100K memories
  - Incremental updates without full rebuild
  - Disk persistence for instant startup
  - Graceful fallback to linear search if hnswlib unavailable
  - Optional dependency: `pip install hnswlib`

- ✅ **Embedding Engine** (`src/embedding_engine.py`) - Local semantic embedding generation
  - all-MiniLM-L6-v2 model (384 dimensions, 80MB)
  - GPU acceleration (CUDA/Apple Silicon MPS) with auto-detection
  - Batch processing: 100-1000 texts/sec (GPU)
  - LRU cache for 10K embeddings (<1ms cache hits)
  - Graceful fallback to TF-IDF if sentence-transformers unavailable
  - Optional dependency: `pip install sentence-transformers`

**Key Features:**
- 🔄 **Zero breaking changes** - All dependencies optional with graceful fallback
- ⚡ **10-20x faster search** with HNSW vs linear search
- 🧠 **True semantic search** with local embeddings (no API calls)
- 🔒 **Security limits** - MAX_BATCH_SIZE, MAX_TEXT_LENGTH, input validation
- 📊 **CLI interfaces** - Test and manage both components
- 📚 **Complete documentation** - `docs/V2.2.0-OPTIONAL-SEARCH.md`

**Performance Benchmarks:**
| Component | Without Optional Deps | With Optional Deps | Speedup |
|-----------|----------------------|-------------------|---------|
| Search (10K) | ~100ms (TF-IDF) | <10ms (HNSW) | 10x |
| Embeddings | ~50ms (TF-IDF) | 10-100ms (GPU) | Semantic |
| Cache hit | N/A | <0.001ms | 100,000x |

**Attribution:**
- Copyright headers on all new files
- MIT License compliance
- Created by Varun Pratap Bhardwaj

### 📦 Installation & Dependencies Overhaul

**Better Dependency Management:**

This release reorganizes optional dependencies into modular requirement files, giving users precise control over what features they install.

**Key Improvements:**
- ✅ **Modular Requirements:** Separate files for different feature sets
- ✅ **Interactive Installation:** Clear menu with download sizes and install times
- ✅ **Installation Verification:** Comprehensive health check script
- ✅ **Zero Breaking Changes:** Existing installations work unchanged
- ✅ **Better Documentation:** Clear feature isolation and migration guide

### ✨ New Files

**Requirements Structure:**
- `requirements.txt` - Core requirements (empty - zero dependencies)
- `requirements-full.txt` - All optional features (~1.5GB)
- `requirements-ui.txt` - Web dashboard only (~50MB)
- `requirements-search.txt` - Advanced search only (~1.5GB)

**Installation Tools:**
- `verify-install.sh` - Comprehensive installation verification
  - Checks Python version, core files, CLI wrappers, PATH configuration
  - Verifies optional features (search, UI)
  - Performance quick test (init + query timing)
  - Clear status reporting with ✓/○/✗ indicators
  - Exit codes for CI/CD integration

**Documentation:**
- `MIGRATION-V2.2.0.md` - Complete migration guide from v2.1.0
  - 100% backward compatibility confirmation
  - Step-by-step upgrade instructions
  - Dependency comparison tables
  - Troubleshooting section
  - FAQ

---

## [2.1.0-universal] - 2026-02-07

**Release Type:** Major Feature Release
**Release Date:** February 7, 2026
**Version Code:** 2.1.0-universal
**Git Tag:** v2.1.0-universal
**Commits Since v2.0.0:** 18 commits
**Lines Changed:** +3,375 lines, -320 lines (net: +3,055)
**New Files:** 22 files
**Backward Compatible:** ✅ Yes (100%)

### 🌐 Universal Integration - MAJOR UPDATE

**SuperLocalMemory now works across ALL IDEs and CLI tools!**

This release transforms SuperLocalMemory from Claude-Code-only to a universal memory system that integrates with 11+ tools while maintaining 100% backward compatibility.

**Key Highlights:**
- 🌐 **11+ IDE Support:** Cursor, Windsurf, Claude Desktop, Continue.dev, Cody, Aider, ChatGPT, Perplexity, Zed, OpenCode, Antigravity
- 🔧 **Three-Tier Access:** MCP + Skills + CLI (all use same database)
- 🤖 **6 Universal Skills:** remember, recall, list-recent, status, build-graph, switch-profile
- 🛠️ **MCP Server:** 6 tools, 4 resources, 2 prompts
- 🔒 **Attribution Protection:** 6-layer protection system with legal compliance
- 📊 **Knowledge Graph:** Leiden clustering with TF-IDF entity extraction
- 🧠 **Pattern Learning:** Multi-dimensional identity extraction with confidence scoring
- 🚀 **Zero Config:** Auto-detection and configuration during installation
- 📝 **Comprehensive Docs:** 1,400+ lines of new documentation

### 🔧 Post-Release Enhancements (Same Day)

**Documentation Additions:**
- ✅ `docs/MCP-MANUAL-SETUP.md` - Comprehensive manual setup guide for 8+ additional tools
  - ChatGPT Desktop App integration
  - Perplexity AI integration
  - Zed Editor configuration
  - OpenCode setup instructions
  - Antigravity IDE configuration
  - Custom MCP client examples (Python/HTTP)
- ✅ `docs/UNIVERSAL-INTEGRATION.md` - Complete universal strategy documentation (15,000+ words)
- ✅ `docs/MCP-TROUBLESHOOTING.md` - Debugging guide with 20+ common issues and solutions

**Enhanced Documentation:**
- ✅ `ARCHITECTURE.md` - Added universal integration architecture section
- ✅ `QUICKSTART.md` - Improved three-tier access method documentation
- ✅ `docs/CLI-COMMANDS-REFERENCE.md` - Enhanced with new `slm` wrapper commands
- ✅ `README.md` - Added V3 cross-reference and version comparison

**Critical Bug Fixes:**
- ✅ Fixed MCP server method calls to match actual API:
  - `store.list_memories()` → `store.list_all()`
  - `engine.get_clusters()` → `engine.get_stats()`
  - `learner.get_context()` → `learner.get_identity_context()`
- ✅ Enhanced MCP server startup banner with version info
- ✅ Improved config file formatting for better readability

**Total IDE Support:** 11+ tools (Cursor, Windsurf, Claude Desktop, Continue.dev, Cody, Aider, ChatGPT, Perplexity, Zed, OpenCode, Antigravity, plus any terminal)

---

## [2.0.0] - 2026-02-05

### Initial Release - Complete Rewrite

SuperLocalMemory V2 represents a complete architectural rewrite with intelligent knowledge graphs, pattern learning, and enhanced organization capabilities.

### Added - New Features

#### 4-Layer Architecture

**Layer 1: Enhanced Storage**
- SQLite database with FTS5 full-text search
- Tag management system
- Metadata support for extensibility
- Parent-child memory relationships
- Compression tiers (1-3) for space optimization

**Layer 2: Hierarchical Index (PageIndex-inspired)**
- Tree structure for memory organization
- Parent-child relationship management
- Breadcrumb navigation paths
- Contextual grouping capabilities
- Fast ancestor/descendant queries

**Layer 3: Knowledge Graph (GraphRAG)**
- TF-IDF entity extraction from memories
- Leiden clustering algorithm for relationship discovery
- Auto-naming of thematic clusters
- Similarity-based memory connections
- Graph statistics and visualization data
- Related memory suggestions

**Layer 4: Pattern Learning (xMemory-inspired)**
- Frequency analysis across memories
- Context extraction for user preferences
- Multi-category pattern recognition:
  - Framework preferences (React, Vue, Angular, etc.)
  - Language preferences (Python, JavaScript, etc.)
  - Architecture patterns (microservices, monolith, etc.)
  - Security approaches (JWT, OAuth, etc.)
  - Coding style priorities
- Confidence scoring (0.0-1.0 scale)
- Identity profile generation for AI context

### Performance Benchmarks

**Search Performance:**
| Memories | V1 Search | V2 Search | Improvement |
|----------|-----------|-----------|-------------|
| 20       | 120ms     | 30ms      | 4.0x        |
| 100      | 150ms     | 45ms      | 3.3x        |
| 500      | 200ms     | 60ms      | 3.3x        |

**Graph Building:**
| Memories | Build Time | Clusters | Entities |
|----------|-----------|----------|----------|
| 20       | 0.03s     | 3-5      | 10-15    |
| 100      | 2.0s      | 10-15    | 40-60    |
| 500      | 15s       | 30-50    | 150-250  |

**Storage Efficiency:**
| Tier | Description | Compression | Use Case |
|------|-------------|-------------|----------|
| 1    | Full content | 0%         | Recent memories |
| 2    | Summarized   | 60%        | 30-90 days old |
| 3    | Archived     | 96%        | 90+ days old |

### Research Foundation

Built on cutting-edge 2026 research:

**GraphRAG (Microsoft Research):**
- Knowledge graph construction from unstructured text
- Community detection for clustering
- Entity extraction and relationship mapping

**PageIndex (VectifyAI):**
- Hierarchical indexing for fast navigation
- Tree-based memory organization
- Contextual grouping strategies

**MemoryBank (AAAI 2024):**
- Identity pattern learning from interactions
- Preference extraction with confidence scoring
- Adaptive context generation

**A-RAG (Multi-level Retrieval):**
- Layer-based retrieval architecture
- Progressive information density
- Context-aware search

---

**For more detailed information on earlier releases, see the full release notes above.**

---

## Links

- **Homepage:** [superlocalmemory.com](https://superlocalmemory.com)
- **Repository:** [GitHub](https://github.com/varun369/SuperLocalMemoryV2)
- **Main Changelog:** [CHANGELOG.md](CHANGELOG.md)

---

**100% local. 100% private. 100% yours.**
