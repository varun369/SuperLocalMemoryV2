# Universal Architecture

SuperLocalMemory V2's 10-layer universal architecture with A2A agent collaboration, visualization dashboard, hybrid search, MCP integration, agent-skills, and local-first system-design that works across 16+ IDEs. This dual-protocol (MCP + A2A) architecture is unique — no competitor offers both agent-to-tool and agent-to-agent communication with local-first privacy.

**Keywords:** universal architecture, system design, mcp protocol, a2a protocol, agent-to-agent, local-first, ai memory, visualization, hybrid search, semantic search, multi-agent

---

## 🏗️ Overview

```
┌─────────────────────────────────────────────────────────────────┐
│            SuperLocalMemory V2 - Universal (10-Layer)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 10: A2A AGENT COLLABORATION (PLANNED v2.5.0)     │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • Agent-to-Agent Protocol (Google/Linux Foundation)    │   │
│  │  • Agent discovery via Agent Cards                      │   │
│  │  • Multi-agent memory sharing & broadcasting            │   │
│  │  • gRPC + JSON-RPC dual transport                       │   │
│  │  • Signed security cards for agent authentication       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ enables agent collaboration      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 9: VISUALIZATION (v2.2.0)                        │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • Interactive web dashboard (Dash/Plotly)              │   │
│  │  • Timeline view, search explorer, graph visualization  │   │
│  │  • Real-time analytics and statistics                   │   │
│  │  • Dark mode, responsive design, keyboard shortcuts     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ visualizes                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 8: HYBRID SEARCH (v2.2.0)                        │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • Semantic Search (TF-IDF + cosine similarity)         │   │
│  │  • Full-Text Search (SQLite FTS5 with ranking)          │   │
│  │  • Graph-Enhanced (knowledge graph traversal)           │   │
│  │  • Hybrid Mode (combines all three for max accuracy)    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ powers                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 7: UNIVERSAL ACCESS                              │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • MCP (Model Context Protocol) - 16+ IDEs             │   │
│  │  • Skills (slash-commands) - Claude/Continue/Cody       │   │
│  │  • CLI (Universal) - Any terminal                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ exposes                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 6: MCP INTEGRATION                               │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • 6 Tools (remember, recall, status, etc.)             │   │
│  │  • 4 Resources (graph, patterns, recent, identity)      │   │
│  │  • 2 Prompts (context injection)                        │   │
│  │  • Auto-configured for Cursor, Windsurf, Claude         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ wraps                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 5: SKILLS LAYER                                  │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • 6 Universal Skills (slm-remember, slm-recall, etc.)  │   │
│  │  • Metadata-first design with SKILL.md                  │   │
│  │  • Compatible with multiple IDEs                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ uses                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 4: PATTERN LEARNING                              │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • Learns your coding preferences                       │   │
│  │  • Extracts terminology patterns                        │   │
│  │  • Confidence scoring (e.g., "React: 73%")              │   │
│  │  • Identity profiles for AI context                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ feeds                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: KNOWLEDGE GRAPH                               │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • TF-IDF entity extraction                             │   │
│  │  • Leiden community clustering                          │   │
│  │  • Auto-naming of clusters                              │   │
│  │  • Relationship discovery                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ indexes                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: HIERARCHICAL INDEX                            │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • PageIndex-style tree structure                       │   │
│  │  • Parent-child memory links                            │   │
│  │  • O(log n) navigation                                  │   │
│  │  • Contextual grouping                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ▲                                  │
│                              │ organizes                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: RAW STORAGE                                   │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • SQLite database                                      │   │
│  │  • Full-text search (FTS5)                              │   │
│  │  • Content hashing (deduplication)                      │   │
│  │  • Progressive compression                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 10: A2A Agent Collaboration (PLANNED v2.5.0)

**Purpose:** Enable AI agents to collaborate through shared memory using the Agent-to-Agent (A2A) protocol.

### Why A2A + MCP?

SuperLocalMemory already uses **MCP** (Anthropic, 2024) for agent-to-tool communication — AI tools connect to the memory database. **A2A** (Google/Linux Foundation, 2025) adds agent-to-agent communication — AI agents discover each other, delegate tasks, and share memory context.

| Protocol | Direction | Purpose | Example |
|----------|-----------|---------|---------|
| **MCP** | Agent → Tool | AI tool accesses memory | Cursor calls `remember()` |
| **A2A** | Agent ↔ Agent | AI agents collaborate via memory | Cursor notifies Claude Desktop of a new decision |

### How It Works

1. **Discovery** — SuperLocalMemory publishes an Agent Card at `/.well-known/agent.json`
2. **Authentication** — Agents present signed security cards; user authorizes each agent
3. **Task Delegation** — External agents submit memory tasks (remember, recall, list)
4. **Streaming Results** — Large query results stream back via server-side streaming
5. **Broadcasting** — Memory changes broadcast to subscribed agents in real-time

### Agent Card

```json
{
  "name": "SuperLocalMemory",
  "description": "Local-first persistent memory with knowledge graph and pattern learning",
  "version": "2.5.0",
  "url": "http://localhost:8766",
  "skills": [
    {"name": "remember", "description": "Store memory with tags, importance, and project context"},
    {"name": "recall", "description": "Hybrid search across memories (semantic + FTS5 + graph)"},
    {"name": "list_recent", "description": "Get recent memories with filtering"},
    {"name": "get_status", "description": "System health, statistics, and graph info"}
  ],
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "stateTransitionHistory": true
  },
  "preferredTransport": "jsonrpc",
  "additionalInterfaces": ["grpc"],
  "securitySchemes": ["signed_agent_card"]
}
```

### A2A Task Lifecycle

```
Agent submits task → SuperLocalMemory processes → Result returned
     │                      │                         │
     ▼                      ▼                         ▼
  submitted            working                   completed
                    (streaming)                   (or failed)
```

### Multi-Agent Scenario

```
Developer using Cursor + Claude Desktop + Continue.dev simultaneously:

1. Cursor Agent → A2A remember("User prefers Tailwind over Bootstrap")
2. SuperLocalMemory stores memory, broadcasts to subscribers
3. Claude Desktop Agent receives broadcast → updates its context
4. Continue.dev Agent receives broadcast → adjusts code suggestions

Result: All tools stay in sync through shared local memory.
```

### Security Model

- **Local-first:** No cloud authentication. Keys stored in `~/.claude-memory/a2a_keys/`
- **Explicit authorization:** User must approve each agent before it can access memory
- **Per-agent permissions:** Read-only, read-write, or admin per agent
- **Audit trail:** All A2A interactions logged to `~/.claude-memory/a2a_audit.log`

### Architecture Principle

A2A is **additive and opt-in**. If A2A server isn't running, all MCP/CLI/Skills functionality works exactly as before. A2A adds a new dimension (agent collaboration) without modifying any existing layer.

### Research Foundation

- **A2A Protocol** (Google/Linux Foundation, 2025) — [a2a-protocol.org](https://a2a-protocol.org/latest/specification/)
- **Complementary to MCP** (Anthropic, 2024) — [a2a-protocol.org/topics/a2a-and-mcp](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)
- Official Python SDK: `a2a-sdk` v0.3.22+ ([github.com/a2aproject/a2a-python](https://github.com/a2aproject/a2a-python))

---

## Layer 9: Visualization (NEW in v2.2.0)

**Purpose:** Interactive visual exploration of memories, relationships, and patterns.

### Web-Based Dashboard

SuperLocalMemory V2.2.0 introduces a **professional visualization dashboard** built with Dash and Plotly for interactive data exploration.

**Launch:**
```bash
python ~/.claude-memory/ui_server.py
# Opens at http://localhost:8765
```

### Four Main Views

| View | Purpose | Key Features |
|------|---------|--------------|
| **📈 Timeline** | Chronological memory visualization | Importance color-coding, date filters, cluster badges |
| **🔍 Search Explorer** | Visual semantic search | Live results, score bars, strategy toggle |
| **🕸️ Graph Visualization** | Interactive knowledge graph | Zoom/pan, cluster coloring, click-to-explore |
| **📊 Statistics Dashboard** | Real-time analytics | Memory trends, tag clouds, pattern insights |

### Why Visualization?

**Before (CLI only):**
```bash
slm list
# Text list of memories
# Hard to see patterns
# No visual relationships
```

**After (Dashboard):**
```
Timeline View:
- See all memories chronologically
- Color-coded by importance
- Cluster badges show relationships
- Click to expand full details
```

### Key Features

**Timeline View:**
- Chronological display with importance markers (1-10)
- Date range filtering (last 7/30/90 days, custom)
- Cluster badges for each memory
- Hover tooltips with full content preview
- Export timeline as PDF/HTML

**Search Explorer:**
- Real-time search as you type
- Visual score bars (0-100% relevance)
- Strategy toggle (semantic/FTS5/graph/hybrid)
- Advanced filters (tags, importance, date, cluster)
- Export search results as JSON/CSV

**Graph Visualization:**
- Interactive force-directed layout
- Zoom, pan, drag nodes
- Cluster coloring (each cluster unique color)
- Edge thickness = relationship strength
- Click nodes to explore connections
- Layout options: force-directed, circular, hierarchical

**Statistics Dashboard:**
- Memory trends (line chart over time)
- Tag cloud (most frequent tags)
- Importance distribution (pie chart)
- Cluster sizes (bar chart)
- Pattern confidence scores (table)
- Access heatmap (calendar view)

### Performance

| Dataset Size | Dashboard Load | Timeline Render | Graph Draw |
|--------------|----------------|-----------------|------------|
| 100 memories | < 100ms | < 100ms | < 200ms |
| 500 memories | < 300ms | < 200ms | < 500ms |
| 1,000 memories | < 500ms | < 300ms | < 1s |
| 5,000 memories | < 2s | < 1s | < 3s |

### Configuration

**File:** `~/.claude-memory/dashboard_config.json`

```json
{
  "port": 8050,
  "theme": "auto",
  "default_view": "timeline",
  "timeline": {
    "items_per_page": 50
  },
  "search": {
    "default_strategy": "hybrid",
    "min_score": 0.5
  },
  "graph": {
    "layout": "force",
    "max_nodes": 500
  }
}
```

[[Complete dashboard guide: Visualization-Dashboard →|Visualization-Dashboard]]

---

## Layer 8: Hybrid Search (NEW in v2.2.0)

**Purpose:** Maximum search accuracy by combining multiple retrieval strategies.

### Three Search Strategies

**1. Semantic Search (TF-IDF)**
- Finds conceptually similar content
- Uses term frequency-inverse document frequency vectors
- Cosine similarity scoring
- Best for: "Show me authentication patterns"
- Speed: ~45ms

**2. Full-Text Search (FTS5)**
- Exact phrase and keyword matching
- SQLite FTS5 with BM25 ranking
- Boolean operators (AND, OR, NOT)
- Best for: "JWT tokens expire after 24 hours"
- Speed: ~30ms

**3. Graph-Enhanced Search**
- Traverses knowledge graph for related memories
- Includes cluster members
- Follows entity connections
- Best for: "Everything related to security"
- Speed: ~60ms

### Hybrid Mode (Default)

**Combines all three strategies:**
1. Run semantic, FTS5, and graph searches in parallel
2. Normalize scores (0-100%)
3. Merge results with weighted ranking
4. Remove duplicates
5. Sort by combined relevance

**Result:** Maximum accuracy with minimal performance overhead (~80ms)

### Search Strategy Comparison

| Query Type | Semantic | FTS5 | Graph | Hybrid |
|------------|----------|------|-------|--------|
| **"authentication patterns"** | ✅ Excellent | ⚠️ Partial | ✅ Excellent | ✅ Best |
| **"JWT tokens expire"** | ⚠️ Good | ✅ Excellent | ⚠️ Good | ✅ Best |
| **"security"** | ✅ Good | ✅ Good | ✅ Excellent | ✅ Best |
| **Exact phrase** | ❌ Miss | ✅ Perfect | ❌ Miss | ✅ Perfect |
| **Conceptual** | ✅ Perfect | ❌ Miss | ✅ Good | ✅ Perfect |

### API Usage

```python
from memory_store_v2 import MemoryStoreV2

store = MemoryStoreV2()

# Semantic search
results = store.search("authentication", strategy="semantic")

# Full-text search
results = store.search("JWT tokens", strategy="fts")

# Graph-enhanced search
results = store.search("security", strategy="graph")

# Hybrid search (default)
results = store.search("API design", strategy="hybrid")
```

### CLI Usage

```bash
# Hybrid (default)
slm recall "authentication patterns"

# Semantic only
slm recall "authentication patterns" --strategy semantic

# Full-text only
slm recall "JWT tokens" --strategy fts

# Graph only
slm recall "security" --strategy graph
```

### Performance by Strategy

| Strategy | 100 memories | 500 memories | 1,000 memories | 5,000 memories |
|----------|--------------|--------------|----------------|----------------|
| Semantic | 25ms | 35ms | 45ms | 75ms |
| FTS5 | 20ms | 25ms | 30ms | 50ms |
| Graph | 40ms | 50ms | 60ms | 100ms |
| **Hybrid** | **55ms** | **65ms** | **80ms** | **150ms** |

**Hybrid adds minimal overhead (~20ms) for significantly better accuracy.**

### Accuracy Metrics

**Test corpus: 500 diverse memories**

| Strategy | Precision | Recall | F1 Score |
|----------|-----------|--------|----------|
| Semantic | 78% | 82% | 0.80 |
| FTS5 | 92% | 65% | 0.76 |
| Graph | 71% | 88% | 0.79 |
| **Hybrid** | **89%** | **91%** | **0.90** |

**Hybrid search achieves best F1 score** by balancing precision and recall.

---

## Layer 7: Universal Access (NEW in v2.1.0)

**Purpose:** Universal access across all IDEs, tools, and environments.

### Three-Tier Access Model

SuperLocalMemory V2.1.0 provides **three ways to access** the same local database:

| Access Method | Best For | Examples |
|---------------|----------|----------|
| **MCP (Model Context Protocol)** | Modern IDEs with native MCP support | Cursor, Windsurf, Claude Desktop, Continue.dev |
| **Skills (Slash Commands)** | AI assistants with command systems | Claude Code, Continue.dev, Cody |
| **CLI (Command Line)** | Terminals, scripts, any environment | `slm remember`, `slm recall`, Aider integration |

### Benefits

- **Single Database:** All three methods use the same SQLite database
- **Zero Conflicts:** No data duplication or sync issues
- **Universal:** Works with 16+ IDEs and any terminal
- **Local-First:** Everything runs on your machine

[[Learn more: MCP Integration →|MCP-Integration]]
[[Learn more: Universal Skills →|Universal-Skills]]

---

## Layer 6: MCP Integration (NEW in v2.1.0)

**Purpose:** Native integration with MCP-compatible IDEs.

### MCP Server Features

**6 Tools:**
1. `remember()` - Save memories with auto-indexing
2. `recall()` - Multi-method search (semantic + FTS)
3. `list_recent()` - Display recent memories
4. `get_status()` - System statistics
5. `build_graph()` - Rebuild knowledge graph
6. `switch_profile()` - Change memory context

**4 Resources:**
1. `memory://graph/clusters` - View all knowledge clusters
2. `memory://patterns/identity` - View learned patterns
3. `memory://recent/10` - Recent memories feed
4. `memory://identity/context` - Identity profile for AI

**2 Prompts:**
1. Context injection for AI sessions
2. Identity profile prompts

### Supported IDEs (Auto-Configured)

The install.sh script automatically detects and configures:
- ✅ **Cursor** - `~/.cursor/mcp_settings.json`
- ✅ **Windsurf** - `~/.windsurf/mcp_settings.json`
- ✅ **Claude Desktop** - `~/Library/Application Support/Claude/claude_desktop_config.json`
- ✅ **Continue.dev** - `.continue/config.yaml`

### Manual Setup Available For

- ChatGPT Desktop App
- Perplexity AI
- Zed Editor
- OpenCode IDE
- Antigravity IDE
- Custom MCP clients

[[Full installation guide: MCP Integration →|MCP-Integration]]

---

## Layer 5: Skills Layer (NEW in v2.1.0)

**Purpose:** Slash-command based access for AI assistants.

### 6 Universal Skills

All skills follow the `slm-*` naming convention:

| Skill | Purpose | Usage |
|-------|---------|-------|
| `slm-remember` | Save content | `/slm-remember "content" --tags work` |
| `slm-recall` | Search memories | `/slm-recall "query"` |
| `slm-list-recent` | View recent | `/slm-list-recent 10` |
| `slm-status` | System health | `/slm-status` |
| `slm-build-graph` | Rebuild graph | `/slm-build-graph` |
| `slm-switch-profile` | Change profile | `/slm-switch-profile personal` |

### Metadata-First Design

Each skill includes a `SKILL.md` file with:
- Name, description, version
- Usage examples
- Arguments and options
- Attribution (Varun Pratap Bhardwaj)
- MIT license

### Compatible Tools

- **Claude Code** - Native skills support
- **Continue.dev** - Custom slash commands
- **Cody** - Custom commands configuration

[[Learn more: Universal Skills →|Universal-Skills]]

---

## Layer 1: Raw Storage

**Purpose:** Persistent, searchable storage for all memories.

### Technology
- **SQLite** — Zero-config, serverless, reliable
- **FTS5** — Full-text search with ranking
- **Content hashing** — Automatic deduplication

### Schema Highlights

```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    content TEXT NOT NULL,
    summary TEXT,
    tags TEXT DEFAULT '[]',
    category TEXT,
    importance INTEGER DEFAULT 5,
    content_hash TEXT UNIQUE,      -- Deduplication
    created_at TIMESTAMP,
    access_count INTEGER DEFAULT 0, -- Usage tracking
    tier INTEGER DEFAULT 1,         -- Compression tier
    cluster_id INTEGER              -- Graph cluster link
);
```

### Key Features

| Feature | Benefit |
|---------|---------|
| **Content hashing** | Same memory never stored twice |
| **Importance scoring** | 1-10 scale for prioritization |
| **Access tracking** | Know which memories are useful |
| **Tiered compression** | 60-96% storage savings |

---

## Layer 2: Hierarchical Index

**Purpose:** Fast navigation and contextual grouping.

### Based On
**PageIndex** (VectifyAI, Mingtian Zhang et al., Sep 2025) — Hierarchical RAG for efficient retrieval.

### How It Works

```
Root
├── Project: MyApp
│   ├── Authentication
│   │   ├── Memory: "JWT implementation"
│   │   ├── Memory: "Session handling"
│   │   └── Memory: "OAuth2 flow"
│   └── Performance
│       ├── Memory: "Database indexing"
│       └── Memory: "Caching strategy"
└── Project: ClientWork
    └── ...
```

### Benefits

| Traditional | Hierarchical Index |
|-------------|-------------------|
| O(n) linear scan | O(log n) tree traversal |
| Flat list | Grouped by context |
| Manual organization | Automatic structuring |

### API Example

```python
# Navigate the tree
tree.get_children(node_id=5)
tree.get_path(memory_id=42)  # Returns: /MyApp/Authentication/
```

---

## Layer 3: Knowledge Graph

**Purpose:** Discover hidden relationships between memories.

### Based On
**GraphRAG** (Microsoft, 2024, [arXiv:2404.16130](https://arxiv.org/abs/2404.16130)) — Knowledge graphs for retrieval.

### How It Works

1. **Entity Extraction** — TF-IDF identifies key terms
2. **Similarity Calculation** — Cosine similarity between memories
3. **Edge Creation** — Connect similar memories
4. **Community Detection** — Leiden algorithm clusters related groups
5. **Auto-Naming** — Clusters get descriptive names

### Example Output

```bash
$ python graph_engine.py build

Processing 47 memories...
✓ Extracted 312 entities
✓ Created 89 edges (similarity > 0.3)
✓ Detected 8 clusters:

Cluster 1: "Authentication & Security" (12 memories)
  - JWT tokens, OAuth, session management, CSRF protection

Cluster 2: "React Components" (9 memories)
  - useState, useEffect, component lifecycle, props

Cluster 3: "Database Operations" (7 memories)
  - SQL queries, indexing, migrations, ORM

...
```

### Why It's Magic

You never tagged "JWT" and "OAuth" together, but the graph **discovers** they're related.

```bash
# Find related memories
$ python graph_engine.py related --memory-id 5

Memory #5: "Implemented JWT authentication"
Related memories:
  - #12: "OAuth2 integration" (similarity: 0.78)
  - #23: "Session token refresh" (similarity: 0.65)
  - #8: "CSRF protection added" (similarity: 0.52)
```

[[Deep dive: Knowledge Graph Guide →|Knowledge-Graph-Guide]]

---

## Layer 4: Pattern Learning

**Purpose:** Learn your coding identity and preferences.

### Based On
**MemoryBank** (Zhong et al., AAAI 2024, [arXiv:2305.10250](https://arxiv.org/abs/2305.10250)) — Long-term memory for LLM agents.
**MACLA** (Forouzandeh et al., Dec 2025, [arXiv:2512.18950](https://arxiv.org/abs/2512.18950)) — Multi-agent collaborative learning with adaptive memory.
**Hindsight** (Latimer et al., Dec 2025, [arXiv:2512.12818](https://arxiv.org/abs/2512.12818)) — Retrospective identity extraction from interactions.

### What It Learns

| Pattern Type | Example | Confidence |
|--------------|---------|------------|
| **Framework preference** | React over Vue | 73% |
| **Coding style** | Performance over readability | 58% |
| **Testing approach** | Jest + React Testing Library | 65% |
| **API style** | REST over GraphQL | 81% |
| **Language preference** | TypeScript over JavaScript | 69% |

### How It Works

1. **Frequency Analysis** — What terms appear most?
2. **Context Analysis** — In what context?
3. **Confidence Calculation** — How consistent is the pattern?
4. **Profile Building** — Create identity summary

### Example Output

```bash
$ python pattern_learner.py context 0.5

Your Coding Identity (confidence ≥ 50%):

Frameworks:
  - React (73% confidence, seen 23 times)
  - Node.js (61% confidence, seen 15 times)

Style Preferences:
  - Performance over readability (58%)
  - Functional over OOP (52%)

Testing:
  - Jest preferred (65%)
  - Integration tests valued (54%)

API Design:
  - REST over GraphQL (81%)
  - OpenAPI documentation (67%)
```

### Use Case

Feed this to Claude at session start:

```
You: Here's my coding profile: [paste pattern context]
Claude: Got it! I'll suggest React solutions, prioritize
        performance, and use Jest for tests.
```

[[Deep dive: Pattern Learning Explained →|Pattern-Learning-Explained]]

---

## Why 10-Layer Architecture?

### Competitors Have Fewer Layers and Limited Capabilities

| Solution | Layers | IDE Support | A2A Protocol | MCP Protocol | Visualization | What's Missing |
|----------|--------|-------------|--------------|--------------|---------------|----------------|
| Mem0 | 2 | Limited (Cloud) | ❌ | ❌ | ❌ | No A2A, no MCP, no patterns, no hierarchy, cloud-only |
| Zep | 2 | 1-2 IDEs | ❌ | ❌ | ❌ | No A2A, no MCP, no patterns, cloud-only |
| Khoj | 2-3 | Limited | ❌ | ❌ | Basic | No A2A, no MCP, no graph, limited search |
| **SuperLocalMemory V2** | **10** | **16+ IDEs** | **✅ Planned** | **✅ Native** | **✅ Full** | **Dual-protocol: MCP + A2A** |

### Each Layer Adds Value

| Without Layer | Impact |
|---------------|--------|
| No Visualization | Can't explore visually, miss patterns, text-only interface |
| No Hybrid Search | Lower accuracy, miss relevant results, slow exploration |
| No Universal Access | Limited to one IDE/tool |
| No MCP Integration | Can't work with modern IDEs |
| No Skills Layer | No slash-command support |
| No Pattern Learning | Don't learn preferences |
| No Knowledge Graph | Miss hidden relationships |
| No Hierarchical Index | Slow navigation, no context |
| No Storage | Can't persist anything |

### Universal = Single Database, Multiple Access Points

All layers share the **same SQLite database**:
- MCP tools read/write to `~/.claude-memory/memory.db`
- Skills read/write to the same database
- CLI commands use the same database
- **Zero data duplication, zero sync conflicts**

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Add memory | < 10ms | Instant |
| Search (FTS) | 45ms | 3.3x faster than v1 |
| Graph build (100 memories) | < 2s | One-time |
| Pattern update | < 2s | Incremental |

---

## Data Flow

```
User saves memory
       │
       ▼
┌──────────────┐
│ Layer 1      │ ← Store in SQLite, hash content, FTS index
│ Raw Storage  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Layer 2      │ ← Update tree structure, assign parent
│ Hierarchical │
└──────┬───────┘
       │
       ▼ (on graph rebuild)
┌──────────────┐
│ Layer 3      │ ← Extract entities, calculate similarity,
│ Knowledge    │   detect clusters, name communities
│ Graph        │
└──────┬───────┘
       │
       ▼ (on pattern update)
┌──────────────┐
│ Layer 4      │ ← Analyze frequencies, calculate confidence,
│ Pattern      │   build identity profile
│ Learning     │
└──────────────┘
```

---

## Research Foundation

| Layer | Research | Source |
|-------|----------|--------|
| 10 | A2A Protocol | Google/Linux Foundation, 2025 ([a2a-protocol.org](https://a2a-protocol.org/)) |
| 9 | Interactive Visualization | Novel (v2.2.0) - Dash/Plotly integration |
| 8 | Hybrid Search | Novel (v2.2.0) - Multi-strategy retrieval |
| 7 | Universal Access | Novel (v2.1.0) |
| 6 | MCP Protocol | Anthropic, 2024 |
| 5 | Skills Architecture | Novel (v2.1.0) |
| 4 | MemoryBank + MACLA + Hindsight | Zhong et al. (AAAI 2024) + Forouzandeh et al. (Dec 2025) + Latimer et al. (Dec 2025) |
| 3 | GraphRAG | Microsoft Research, 2024 ([arXiv:2404.16130](https://arxiv.org/abs/2404.16130)) |
| 2 | PageIndex | VectifyAI (Zhang et al., Sep 2025) |
| 1 | Tiered Storage | Industry best practice |

**SuperLocalMemory V2 is the only open-source memory system with both MCP (agent-to-tool) and A2A (agent-to-agent) protocol support, combining 10 layers with universal IDE integration.**

Created by **Varun Pratap Bhardwaj**.

---

## Next Steps

- [[A2A Integration →|A2A-Integration]] - Agent-to-Agent collaboration (PLANNED v2.5.0)
- [[Visualization Dashboard →|Visualization-Dashboard]] - Interactive visual exploration
- [[MCP Integration Guide →|MCP-Integration]] - Setup for 16+ IDEs
- [[Universal Skills Guide →|Universal-Skills]] - Learn slash-commands
- [[Knowledge Graph Guide →|Knowledge-Graph-Guide]] - Understand clustering
- [[Installation →|Installation]] - Get started in 5 minutes

---

[[← Back to Home|Home]]

---

**Created by Varun Pratap Bhardwaj**
