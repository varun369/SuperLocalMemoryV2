# 4-Layer Architecture

SuperLocalMemory V2's unique architecture that no competitor offers.

---

## 🏗️ Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SuperLocalMemory V2                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
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

## Why 4 Layers?

### Competitors Have Fewer

| Solution | Layers | What's Missing |
|----------|--------|----------------|
| Mem0 | 2 | No patterns, no hierarchy |
| Zep | 2 | No patterns |
| Khoj | 1-2 | No graph, no patterns |
| **SuperLocalMemory** | **4** | **Complete** |

### Each Layer Adds Value

| Without Layer | Impact |
|---------------|--------|
| No Storage | Can't persist anything |
| No Index | Slow navigation, no context |
| No Graph | Miss hidden relationships |
| No Patterns | Don't learn preferences |

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
| 1 | Tiered Storage | Industry best practice |
| 2 | PageIndex | Meta AI, 2024 |
| 3 | GraphRAG | Microsoft Research, 2024 |
| 4 | xMemory | Stanford, 2024 |

**SuperLocalMemory is the only open-source implementation combining all four.**

---

[[← Back to Home|Home]] | [[Next: Knowledge Graph Guide →|Knowledge-Graph-Guide]]
