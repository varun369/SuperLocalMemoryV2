# Architecture Documentation

## SuperLocalMemory V2 - Technical Architecture

This document provides a comprehensive technical overview of SuperLocalMemory V2's architecture, design decisions, and implementation details.

---

## Table of Contents

- [System Overview](#system-overview)
- [4-Layer Architecture](#4-layer-architecture)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Design Decisions](#design-decisions)
- [Performance Characteristics](#performance-characteristics)
- [Security & Privacy](#security--privacy)
- [Scalability](#scalability)

---

## System Overview

SuperLocalMemory V2 is a **standalone, local-first, intelligent memory system** that transforms flat memory storage into a living knowledge graph with pattern learning capabilities.

Works independently or integrates with Claude CLI, GPT, local LLMs, or any AI assistant.

### Core Principles

1. **Local-First:** All data stored locally, zero external API calls
2. **Privacy-First:** No telemetry, no tracking, complete user control
3. **Intelligence:** Auto-discovery of relationships and patterns
4. **Modularity:** Independent layers with clear interfaces
5. **Performance:** Sub-second operations for typical workloads (< 500 memories)

### Architecture Philosophy

```
Simple Storage → Intelligent Organization → Adaptive Learning
     (SQLite)     (Graphs + Indexes)         (Pattern Recognition)
```

---

## 4-Layer Architecture

SuperLocalMemory V2 uses a hierarchical, additive architecture where each layer builds on the previous without replacing it.

```
┌─────────────────────────────────────────────────────────────────┐
│                   SuperLocalMemory V2                           │
│                   4-Layer Architecture                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Layer 4: Pattern Learning (Identity Profiles)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  Frequency        │  │  Context         │                   │
│  │  Analysis         │  │  Analysis        │                   │
│  └──────────────────┘  └──────────────────┘                   │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  Terminology      │  │  Confidence      │                   │
│  │  Learning         │  │  Scoring         │                   │
│  └──────────────────┘  └──────────────────┘                   │
│                                                                 │
│  Output: Identity profiles with confidence scores              │
└─────────────────────────────────────────────────────────────────┘
                            ↑
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: Knowledge Graph (GraphRAG)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  TF-IDF Entity   │  │  Leiden          │                   │
│  │  Extraction      │  │  Clustering      │                   │
│  └──────────────────┘  └──────────────────┘                   │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  Auto-naming     │  │  Relationship    │                   │
│  │  Clusters        │  │  Discovery       │                   │
│  └──────────────────┘  └──────────────────┘                   │
│                                                                 │
│  Output: Clusters of related memories, entity relationships    │
└─────────────────────────────────────────────────────────────────┘
                            ↑
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: Hierarchical Index (PageIndex-inspired)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  Tree Structure  │  │  Parent-Child    │                   │
│  │  Management      │  │  Relationships   │                   │
│  └──────────────────┘  └──────────────────┘                   │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  Fast Navigation │  │  Contextual      │                   │
│  │  Paths           │  │  Grouping        │                   │
│  └──────────────────┘  └──────────────────┘                   │
│                                                                 │
│  Output: Hierarchical organization, breadcrumb navigation      │
└─────────────────────────────────────────────────────────────────┘
                            ↑
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Raw Storage (SQLite Foundation)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  Full-Text       │  │  Vector          │                   │
│  │  Search (FTS5)   │  │  Embeddings      │                   │
│  └──────────────────┘  └──────────────────┘                   │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  Tags &          │  │  Compression     │                   │
│  │  Metadata        │  │  Archives        │                   │
│  └──────────────────┘  └──────────────────┘                   │
│                                                                 │
│  Output: Persistent storage, fast search, metadata             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### Layer 1: Raw Storage (SQLite)

**Responsibility:** Persistent storage, basic search, metadata management

**Components:**

1. **memory_store_v2.py** - Core CRUD operations
   - Add, update, delete memories
   - Tag management
   - Search interface

2. **SQLite Schema:**
   ```sql
   -- Main memories table
   CREATE TABLE memories (
       id INTEGER PRIMARY KEY,
       content TEXT NOT NULL,
       timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
       tags TEXT,  -- JSON array
       metadata TEXT,  -- JSON object
       tier INTEGER DEFAULT 1,  -- Compression tier
       parent_id INTEGER,  -- For tree structure
       FOREIGN KEY (parent_id) REFERENCES memories(id)
   );

   -- Full-text search index
   CREATE VIRTUAL TABLE memories_fts USING fts5(
       content, tags,
       content=memories,
       content_rowid=id
   );

   -- Graph tables
   CREATE TABLE graph_clusters (
       id INTEGER PRIMARY KEY,
       name TEXT,
       description TEXT
   );

   CREATE TABLE graph_cluster_members (
       cluster_id INTEGER,
       memory_id INTEGER,
       FOREIGN KEY (cluster_id) REFERENCES graph_clusters(id),
       FOREIGN KEY (memory_id) REFERENCES memories(id)
   );

   -- Pattern learning tables
   CREATE TABLE learned_patterns (
       id INTEGER PRIMARY KEY,
       category TEXT,
       subcategory TEXT,
       pattern_text TEXT,
       confidence REAL,
       frequency INTEGER,
       last_seen DATETIME
   );
   ```

3. **Compression System** (memory_compression.py)
   - Progressive summarization
   - Tier-based compression (Tier 1→2→3)
   - Cold storage archival

**Performance:**
- Full-text search: ~45ms (avg)
- Insert: <10ms
- Tag search: ~30ms

---

### Layer 2: Hierarchical Index (PageIndex)

**Responsibility:** Tree-based organization, contextual grouping

**Components:**

1. **tree_manager.py** - Tree structure operations
   - Parent-child relationship management
   - Breadcrumb generation
   - Subtree queries

**Key Features:**
- Fast navigation through related memories
- Contextual grouping (e.g., "Project Alpha" → subtasks)
- Efficient ancestor/descendant queries

**Schema Integration:**
```sql
-- Parent-child relationships
parent_id INTEGER FOREIGN KEY → memories(id)

-- Query: Get all children
SELECT * FROM memories WHERE parent_id = ?

-- Query: Get breadcrumb path
WITH RECURSIVE ancestors AS (...)
```

**Use Cases:**
- Project hierarchies
- Conversation threading
- Multi-step task tracking

---

### Layer 3: Knowledge Graph (GraphRAG)

**Responsibility:** Relationship discovery, auto-clustering, entity extraction

**Components:**

1. **graph_engine.py** - Graph construction and queries
   - TF-IDF entity extraction
   - Leiden clustering algorithm
   - Cluster naming via LLM patterns
   - Relationship discovery

**Algorithm Pipeline:**

```
Memories → TF-IDF → Entity Extraction → Similarity Matrix → Leiden Clustering → Named Clusters
```

**Step-by-Step:**

1. **Entity Extraction (TF-IDF):**
   ```python
   # Extract top terms from each memory
   tfidf_vectorizer = TfidfVectorizer(
       max_features=20,
       stop_words='english',
       ngram_range=(1, 2)
   )
   entities = tfidf_vectorizer.fit_transform(memories)
   ```

2. **Similarity Calculation:**
   ```python
   # Cosine similarity between memories
   similarity_matrix = cosine_similarity(entities)
   ```

3. **Leiden Clustering:**
   ```python
   # Community detection in similarity graph
   import leidenalg
   communities = leidenalg.find_partition(graph, resolution=1.0)
   ```

4. **Auto-Naming:**
   ```python
   # Extract common terms from cluster members
   cluster_name = most_frequent_terms(cluster_memories)
   # Example: "Authentication & Security"
   ```

**Performance:**
- Build time: <30ms (20 memories)
- Build time: ~2s (100 memories)
- Query time: <10ms (related memories)

**Output:**
- Clusters with auto-generated names
- Entity relationships
- Related memory suggestions

---

### Layer 4: Pattern Learning (xMemory-inspired)

**Responsibility:** Learn user preferences, coding style, terminology

**Components:**

1. **pattern_learner.py** - Pattern extraction and scoring
   - Frequency analysis
   - Context analysis
   - Confidence scoring
   - Identity profile generation

**Analysis Categories:**

```python
CATEGORIES = {
    "preferences": {
        "framework": ["React", "Vue", "Angular", ...],
        "language": ["Python", "JavaScript", "Go", ...],
        "architecture": ["microservices", "monolith", ...],
        "security": ["JWT", "OAuth", "API keys", ...]
    },
    "style": {
        "code_preferences": ["functional", "OOP", ...],
        "priorities": ["performance", "readability", ...]
    },
    "terminology": {
        "common_terms": [...],
        "technical_vocabulary": [...]
    }
}
```

**Confidence Scoring:**

```python
confidence = frequency / total_memories

# Example:
# "React" appears in 6/10 memories → 60% confidence
# "Vue" appears in 1/10 memories → 10% confidence
```

**Output Format:**

```json
{
  "preferences": {
    "framework": {
      "React": 0.60,
      "Angular": 0.20
    },
    "language": {
      "Python": 0.50,
      "JavaScript": 0.40
    }
  },
  "style": {
    "priorities": {
      "performance": 0.53,
      "readability": 0.30
    }
  }
}
```

**Use Cases:**
- Personalized AI assistant context
- Style guide generation
- Skill tracking
- Learning trajectory analysis

---

## Data Flow

### Write Path (Adding Memory)

```
User Input
    ↓
memory_store_v2.py: add()
    ↓
SQLite: INSERT into memories table
    ↓
FTS5: Update full-text index
    ↓
[Optional] tree_manager: Set parent_id
    ↓
[Async] graph_engine: Rebuild trigger
    ↓
[Async] pattern_learner: Update trigger
```

### Read Path (Search)

```
User Query
    ↓
memory_store_v2.py: search()
    ↓
SQLite FTS5: Full-text search
    ↓
Results + Metadata
    ↓
[Optional] graph_engine: Enrich with related memories
    ↓
[Optional] pattern_learner: Add context suggestions
    ↓
User Output
```

### Graph Build Path

```
Trigger: Manual or scheduled
    ↓
graph_engine.py: build()
    ↓
Fetch all memories from SQLite
    ↓
TF-IDF: Extract entities
    ↓
Cosine Similarity: Calculate relationships
    ↓
Leiden Algorithm: Detect communities
    ↓
Auto-naming: Generate cluster names
    ↓
SQLite: INSERT into graph_clusters, graph_cluster_members
    ↓
Statistics output
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Database | SQLite | 3.35+ | Persistent storage |
| Search | FTS5 | Built-in | Full-text search |
| Language | Python | 3.8+ | Core implementation |
| Clustering | Leiden Algorithm | Custom impl | Community detection |
| Entity Extraction | TF-IDF | scikit-learn-style | Term importance |
| CLI | Bash scripts | - | User commands |

### Python Standard Library Only

**No external dependencies required for core features:**
- `sqlite3` - Database
- `json` - Configuration, metadata
- `re` - Text processing
- `datetime` - Timestamps
- `hashlib` - ID generation
- `collections` - Data structures

**Optional (for advanced features):**
- `scikit-learn` - Full TF-IDF implementation
- `leidenalg` - Advanced clustering

**Fallback implementations provided** for systems without optional dependencies.

---

## Design Decisions

### Decision 1: SQLite Over NoSQL

**Reasoning:**
- Local-first: No server setup required
- ACID transactions: Data integrity guaranteed
- FTS5: Built-in full-text search
- Widely available: Pre-installed on most systems
- Zero configuration: Works out of the box

**Trade-offs:**
- Single-writer: Not suitable for high-concurrency scenarios
- Limited to local disk: No distributed access (feature, not bug)

---

### Decision 2: 4-Layer Additive Architecture

**Reasoning:**
- Modularity: Each layer can be disabled independently
- Progressive enhancement: System works even if upper layers fail
- Clear separation: Easy to understand and maintain
- Testability: Each layer can be tested in isolation

**Trade-offs:**
- Slight redundancy: Some data duplicated across layers
- Build time: Graph/pattern layers require periodic rebuilds

---

### Decision 3: Local-Only, No External APIs

**Reasoning:**
- Privacy: User data never leaves machine
- Reliability: No internet dependency
- Speed: No network latency
- Cost: No API bills

**Trade-offs:**
- No cloud sync: Multi-device requires manual export/import
- Limited ML: No access to large models (by design)

---

### Decision 4: TF-IDF + Leiden Clustering

**Reasoning:**
- TF-IDF: Fast, lightweight, no training required
- Leiden: Better than Louvain, finds quality communities
- Deterministic: Same input = same output
- Scalable: O(n log n) complexity

**Alternatives considered:**
- Vector embeddings: Too heavy, requires models
- LDA: Slower, less interpretable
- Simple keyword matching: Too simplistic

---

### Decision 5: Confidence Scoring Over Binary Classification

**Reasoning:**
- Nuance: Captures uncertainty in patterns
- User control: Filter by confidence threshold
- Adaptability: Patterns evolve as memories grow
- Transparency: Users see why patterns are suggested

**Example:**
```
React: 60% confidence → High priority suggestion
Vue: 10% confidence → Low priority, exploratory
```

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Typical Time |
|-----------|-----------|--------------|
| Add memory | O(1) | <10ms |
| Search (FTS5) | O(log n) | ~45ms |
| Graph build | O(n²) worst, O(n log n) avg | ~2s (100 memories) |
| Pattern update | O(n) | <2s (100 memories) |
| Find related | O(1) | <10ms |

### Space Complexity

| Component | Storage | Notes |
|-----------|---------|-------|
| Raw memories | ~1KB/memory | Typical text memory |
| FTS5 index | ~30% overhead | Full-text search index |
| Graph data | ~100 bytes/memory | Cluster memberships |
| Patterns | ~1KB total | Aggregate statistics |
| Compression (Tier 2) | 60% reduction | Summarized old memories |
| Compression (Tier 3) | 96% reduction | Archived to JSON |

**Example:** 500 memories ≈ 500KB raw + 150KB index + 50KB graph = ~700KB total

---

## Security & Privacy

### Threat Model

**Assumptions:**
- User has physical access to machine
- Local filesystem is trusted
- No network threats (local-only)

**Protections:**

1. **No External Data Leaks:**
   - Zero API calls
   - No telemetry
   - No auto-updates

2. **Data Integrity:**
   - SQLite ACID transactions
   - Automatic backups before resets

3. **Access Control:**
   - Relies on filesystem permissions
   - Standard Unix/macOS security model

**Not Protected Against:**
- Physical access to machine
- Root/admin access
- Filesystem malware

**Recommendation:** Use full-disk encryption for sensitive data.

---

## Scalability

### Current Limits (Tested)

| Memories | Build Time | Search Time | Database Size |
|----------|-----------|-------------|---------------|
| 20 | <0.03s | ~30ms | ~30KB |
| 100 | ~2s | ~45ms | ~150KB |
| 500 | ~15s | ~60ms | ~700KB |
| 1000 | ~45s | ~100ms | ~1.5MB |

### Scaling Strategies

**For 1000+ memories:**
1. **Profile Splitting:** Separate contexts (work, personal, learning)
2. **Compression:** Auto-archive old memories (Tier 3)
3. **Incremental Builds:** Graph updates instead of full rebuilds
4. **Selective Loading:** Load only active profile

**Future Optimizations:**
- Graph delta updates (vs. full rebuild)
- Lazy pattern loading
- Memory pagination for large searches

---

## Extension Points

### Adding New Layers

```python
# Layer 5 example: Predictive recommendations
class RecommendationEngine:
    def suggest_next_memory(self, context):
        # Use patterns + graph to predict what user might add next
        pass
```

### Adding New Pattern Categories

```python
# In pattern_learner.py
CATEGORIES["preferences"]["testing"] = [
    "pytest", "jest", "unittest", "TDD", "BDD"
]
```

### Custom Clustering Algorithms

```python
# In graph_engine.py
def custom_clustering(similarity_matrix):
    # Implement alternative clustering
    pass
```

---

## Conclusion

SuperLocalMemory V2's architecture provides:
- **Simplicity:** Standard tools (SQLite, Python stdlib)
- **Intelligence:** Auto-discovery of patterns and relationships
- **Privacy:** 100% local, zero external dependencies
- **Modularity:** Independent layers, clear interfaces
- **Performance:** Sub-second operations for typical workloads

**Design Philosophy:** Start simple (Layer 1), add intelligence progressively (Layers 2-4), maintain local-first principles throughout.

---

## Further Reading

- [Complete Feature List](docs/COMPLETE-FEATURE-LIST.md)
- [Graph Engine Implementation](docs/GRAPH_ENGINE_README.md)
- [Pattern Learning Details](docs/PATTERN_LEARNER_README.md)
- [Compression System](docs/COMPRESSION-README.md)

---

## Author

**Varun Pratap Bhardwaj**
*Solution Architect*

SuperLocalMemory V2 - Intelligent local memory system for AI coding assistants.

---

**Questions about architecture?**

See [CONTRIBUTING.md](CONTRIBUTING.md) for development discussions or open an issue on GitHub.
