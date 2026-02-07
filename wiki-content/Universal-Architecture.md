# Universal Architecture

SuperLocalMemory V2.1.0's universal architecture with MCP integration, agent-skills, and local-first system-design that works across 11+ IDEs. This mcp-protocol based architecture is unique and no competitor offers this level of universal integration.

**Keywords:** universal architecture, system design, mcp protocol, local-first, ai memory

---

## 🏗️ Overview

```
┌─────────────────────────────────────────────────────────────────┐
│              SuperLocalMemory V2.1.0 - Universal                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LAYER 7: UNIVERSAL ACCESS                              │   │
│  │  ─────────────────────────────────────────────────────  │   │
│  │  • MCP (Model Context Protocol) - 11+ IDEs             │   │
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
- **Universal:** Works with 11+ IDEs and any terminal
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
**PageIndex** (Meta AI, 2024) — Hierarchical RAG for efficient retrieval.

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
**GraphRAG** (Microsoft, 2024) — Knowledge graphs for retrieval.

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
**xMemory** (Stanford, 2024) — Identity extraction from interactions.

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

## Why Universal Architecture?

### Competitors Have Fewer Layers and Limited IDE Support

| Solution | Layers | IDE Support | What's Missing |
|----------|--------|-------------|----------------|
| Mem0 | 2 | Limited (Cloud) | No patterns, no hierarchy, no universal access |
| Zep | 2 | 1-2 IDEs | No patterns, no MCP, cloud-only |
| Khoj | 1-2 | Limited | No graph, no patterns, no universal CLI |
| **SuperLocalMemory V2.1.0** | **7** | **11+ IDEs** | **Nothing - Complete** |

### Each Layer Adds Value

| Without Layer | Impact |
|---------------|--------|
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
| 7 | Universal Access | Novel (v2.1.0) |
| 6 | MCP Protocol | Anthropic, 2024 |
| 5 | Skills Architecture | Novel (v2.1.0) |
| 4 | xMemory | Stanford, 2024 |
| 3 | GraphRAG | Microsoft Research, 2024 |
| 2 | PageIndex | Meta AI, 2024 |
| 1 | Tiered Storage | Industry best practice |

**SuperLocalMemory V2.1.0 is the only open-source implementation combining all seven layers with universal IDE support.**

Created by **Varun Pratap Bhardwaj**.

---

## Next Steps

- [[MCP Integration Guide →|MCP-Integration]] - Setup for 11+ IDEs
- [[Universal Skills Guide →|Universal-Skills]] - Learn slash-commands
- [[Knowledge Graph Guide →|Knowledge-Graph-Guide]] - Understand clustering
- [[Installation →|Installation]] - Get started in 5 minutes

---

[[← Back to Home|Home]]

---

**Created by Varun Pratap Bhardwaj**
