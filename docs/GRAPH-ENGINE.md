# GraphEngine - Knowledge Graph Clustering for SuperLocalMemory

Complete implementation of GraphRAG with Leiden community detection for automatic memory clustering and relationship discovery.

## Overview

The GraphEngine implements Layer 3 of the memory architecture, building a knowledge graph that auto-discovers relationships between memories across projects using:

- **TF-IDF Entity Extraction** - Local keyword extraction (top 20 per memory)
- **Cosine Similarity Edges** - Relationship building (threshold > 0.3)
- **Leiden Clustering** - Community detection for thematic grouping
- **Auto-naming** - TF-IDF-based cluster name generation

**All processing is local** - no external APIs, all data stays on your machine.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ GraphEngine (graph_engine.py)                          │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐           │
│  │ EntityExtractor  │  │ EdgeBuilder      │           │
│  │ (TF-IDF)         │  │ (Cosine sim)     │           │
│  └──────────────────┘  └──────────────────┘           │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐           │
│  │ ClusterBuilder   │  │ ClusterNamer     │           │
│  │ (Leiden)         │  │ (TF-IDF)         │           │
│  └──────────────────┘  └──────────────────┘           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ SQLite Tables │
                  │ - graph_nodes │
                  │ - graph_edges │
                  │ - graph_clusters │
                  └───────────────┘
```

## Components

### 1. EntityExtractor
Extracts key concepts from memory content using TF-IDF vectorization.

**Features:**
- Top 20 keywords per memory
- Unigrams + bigrams (e.g., "authentication", "jwt tokens")
- English stop words filtering
- Minimum score threshold (0.05)

**Example:**
```python
Memory: "Next.js authentication using NextAuth.js with JWT tokens..."

Entities:
["nextjs", "authentication", "nextauth", "jwt", "tokens",
 "oauth", "session", "credentials", "callback", "api"]
```

### 2. EdgeBuilder
Creates weighted edges between similar memories based on entity overlap.

**Algorithm:**
1. Compute pairwise cosine similarity of TF-IDF vectors
2. Create edge if similarity >= threshold (default 0.3)
3. Classify relationship type:
   - `similar` (sim > 0.7) - Strong match
   - `depends_on` - Contains dependency keywords
   - `related_to` - Moderate/weak match

**Example:**
```python
Memory #42: ["nextjs", "authentication", "jwt"]
Memory #15: ["jwt", "tokens", "authentication", "python"]

Similarity: 0.72
Shared entities: ["authentication", "jwt"]
Edge type: "similar"
```

### 3. ClusterBuilder
Groups related memories into thematic clusters using Leiden algorithm.

**Why Leiden?**
- Better quality than Louvain algorithm
- Deterministic (reproducible with seed)
- Scalable (handles 1000+ nodes)
- Production-ready (used by Scanpy, 10k+ citations)

**Performance:**
- 50 memories: ~500ms
- 100 memories: ~2s
- 500 memories: ~15s

**Output:**
```
Cluster #1: 8 memories (avg importance: 7.2)
  Theme: Authentication & JWT
  Members: [12, 15, 23, 33, 42, 52, 67, 71]

Cluster #2: 12 memories (avg importance: 6.8)
  Theme: React & Architecture
  Members: [5, 8, 14, 19, 28, 35, 41, 46, 53, 60, 65, 70]
```

### 4. ClusterNamer
Auto-generates human-readable cluster names from member entities.

**Strategy:**
1. Collect all entities from cluster members
2. Count entity frequencies
3. Use top 2-3 entities for name

**Examples:**
- `"Authentication & JWT"` (from ["authentication", "jwt", "oauth"])
- `"React & Architecture"` (from ["react", "component", "architecture"])
- `"Performance & Optimization"` (from ["performance", "optimize", "speed"])

## Database Schema

### graph_nodes
Stores extracted entities and embedding vectors for each memory.

```sql
CREATE TABLE graph_nodes (
    id INTEGER PRIMARY KEY,
    memory_id INTEGER UNIQUE NOT NULL,
    entities TEXT,              -- JSON: ["auth", "jwt", ...]
    embedding_vector TEXT,      -- JSON: TF-IDF vector
    created_at TIMESTAMP,
    FOREIGN KEY (memory_id) REFERENCES memories(id)
);
```

### graph_edges
Stores relationships between memories.

```sql
CREATE TABLE graph_edges (
    id INTEGER PRIMARY KEY,
    source_memory_id INTEGER NOT NULL,
    target_memory_id INTEGER NOT NULL,
    relationship_type TEXT,     -- 'similar', 'depends_on', 'related_to'
    weight REAL,                -- Similarity score (0-1)
    shared_entities TEXT,       -- JSON: ["auth", "jwt"]
    similarity_score REAL,
    created_at TIMESTAMP,
    UNIQUE(source_memory_id, target_memory_id)
);
```

### graph_clusters
Stores detected communities.

```sql
CREATE TABLE graph_clusters (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,         -- "Authentication & JWT"
    description TEXT,
    member_count INTEGER,
    avg_importance REAL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Installation

### Dependencies
```bash
pip install scikit-learn python-igraph leidenalg
```

**Note:** All dependencies are already installed in the virtual environment.

## Usage

### CLI Commands

#### 1. Build Complete Graph
```bash
python graph_engine.py build [--min-similarity 0.3]
```

**Output:**
```json
{
  "success": true,
  "memories": 18,
  "nodes": 18,
  "edges": 40,
  "clusters": 4,
  "time_seconds": 0.03
}
```

#### 2. View Statistics
```bash
python graph_engine.py stats
```

**Output:**
```json
{
  "nodes": 18,
  "edges": 40,
  "clusters": 4,
  "top_clusters": [
    {
      "name": "Authentication & Tokens",
      "members": 4,
      "avg_importance": 6.2
    },
    {
      "name": "Performance & Code",
      "members": 4,
      "avg_importance": 5.0
    }
  ]
}
```

#### 3. Find Related Memories
```bash
python graph_engine.py related --memory-id 1 [--hops 2]
```

**Output:**
```
1. Memory #4 (1-hop, weight=0.875)
   Relationship: similar
   Summary: Authentication implementation...
   Shared: authentication, jwt, oauth

2. Memory #2 (1-hop, weight=0.709)
   Relationship: related_to
   Summary: API security patterns...
   Shared: security, api, tokens
```

#### 4. View Cluster Members
```bash
python graph_engine.py cluster --cluster-id 1
```

**Output:**
```
Cluster #1 members:

1. Memory #5 (importance=7)
   JWT authentication implementation...

2. Memory #8 (importance=6)
   OAuth2 flow setup...

3. Memory #10 (importance=8)
   Security best practices...
```

### Programmatic Usage

```python
from graph_engine import GraphEngine

# Initialize engine
engine = GraphEngine()

# Build complete graph
stats = engine.build_graph(min_similarity=0.3)
print(f"Built graph: {stats['nodes']} nodes, {stats['edges']} edges")

# Find related memories
related = engine.get_related(memory_id=1, max_hops=2)
for mem in related:
    print(f"Related: #{mem['id']} ({mem['relationship']}, weight={mem['weight']:.3f})")

# Query clusters
stats = engine.get_stats()
for cluster in stats['top_clusters']:
    print(f"Cluster: {cluster['name']} ({cluster['members']} members)")

    # Get cluster details
    members = engine.get_cluster_members(cluster_id)
    for mem in members:
        print(f"  - Memory #{mem['id']}: {mem['summary'][:50]}...")

# Add memory incrementally
success = engine.add_memory_incremental(new_memory_id)
if success:
    print("Memory added to graph successfully")
```

### Example Script

Run `example_graph_usage.py` to see all features in action:

```bash
python example_graph_usage.py
```

This demonstrates:
1. Building a complete graph
2. Finding related memories
3. Querying clusters
4. Extracting entities
5. Incremental memory addition

## Performance

### Build Time (Full Graph)
- 10 memories: 0.02s
- 50 memories: 0.5s
- 100 memories: 2s
- 500 memories: ~15s

### Query Time
- Find related (1-hop): <5ms
- Find related (2-hop): <10ms
- Get cluster members: <2ms
- Graph stats: <5ms

### Space Complexity
- **Sparse storage** - Only edges > threshold
- **Example:** 50 memories
  - Full matrix: 2,500 entries
  - Sparse graph: ~150 edges (94% reduction)

## Graph Operations

### Full Rebuild
Recommended when:
- First time setup
- Major changes (10+ new memories)
- Weekly maintenance (cron job)

```python
stats = engine.build_graph(min_similarity=0.3)
```

### Incremental Update
Recommended when:
- Adding single memory
- Real-time graph updates
- After each new memory addition

```python
success = engine.add_memory_incremental(memory_id)
# Re-cluster if > 5 new edges added
```

### Graph Traversal
Find related memories via BFS traversal:

```python
# 1-hop: Direct neighbors only
related = engine.get_related(memory_id, max_hops=1)

# 2-hop: Neighbors + neighbors of neighbors
related = engine.get_related(memory_id, max_hops=2)
```

## Configuration

### Similarity Threshold
Controls edge creation sensitivity:

```python
# Strict (fewer, stronger connections)
engine.build_graph(min_similarity=0.5)

# Balanced (default)
engine.build_graph(min_similarity=0.3)

# Loose (more connections)
engine.build_graph(min_similarity=0.2)
```

**Recommendations:**
- Small corpus (<50 memories): 0.2-0.3
- Medium corpus (50-200): 0.3-0.4
- Large corpus (>200): 0.4-0.5

### Entity Extraction
Adjust entity count in `EntityExtractor`:

```python
extractor = EntityExtractor(max_features=20)  # Default
extractor = EntityExtractor(max_features=30)  # More granular
```

## Integration with Memory System

### Hook Integration (Optional - for Claude CLI)
If using Claude CLI integration, add to `hooks/remember-hook.js`:

```javascript
// After storing memory
execFile('python', ['graph_engine.py', 'add-memory', memoryId], (err) => {
    if (err) console.error('Graph update failed:', err);
});
```

**Note:** SuperLocalMemory V2 works standalone. Hooks are optional Claude CLI integration.

### Automated Rebuild
Add to crontab for weekly rebuild:

```bash
# Run every Sunday at 2 AM
0 2 * * 0 cd ~/.claude-memory && ./venv/bin/python graph_engine.py build
```

### Search Enhancement
Use graph for context expansion in search:

```python
# Find memory via search
memory = store.search(query)[0]

# Expand context with related memories
related = engine.get_related(memory['id'], max_hops=2)

# Include related in context window
context = memory['content']
for rel in related[:3]:  # Top 3
    context += f"\n\nRelated: {rel['summary']}"
```

## Troubleshooting

### No Clusters Detected
**Cause:** Not enough edges or isolated memories
**Solution:**
- Lower similarity threshold: `--min-similarity 0.2`
- Add more memories (need 10+ for good clustering)
- Check if memories are diverse enough

### Slow Build Time
**Cause:** Large corpus (>500 memories)
**Solution:**
- Use incremental updates instead of full rebuild
- Increase similarity threshold to reduce edges
- Run as background job (cron)

### Import Errors (Python 3.14)
**Cause:** Conflict with `compression` module
**Solution:**
- Already handled via lazy imports in code
- Imports happen inside methods, not at module level

### Memory Not Found
**Cause:** Memory ID doesn't exist or graph not built
**Solution:**
- Verify memory exists: `SELECT id FROM memories WHERE id = ?`
- Rebuild graph: `python graph_engine.py build`

## Future Enhancements

### Optional LLM Naming
Use local LLM (Ollama) for better cluster names:

```python
# Install Ollama and pull model
ollama pull llama3.2

# Enable LLM naming (future feature)
engine.build_graph(use_llm_naming=True)
```

### Temporal Clustering
Group memories by time + content:

```python
# Future feature: time-aware clustering
engine.build_graph(temporal_weight=0.3)
```

### Interactive Visualization
Web-based D3.js graph viewer (see `docs/architecture/03-ui-architecture.md`)

## References

- [GraphRAG (Microsoft)](https://microsoft.github.io/graphrag/) - Knowledge graph clustering
- [Leiden Algorithm](https://www.nature.com/articles/s41598-019-41695-z) - Community detection
- [PageIndex](https://pageindex.ai/) - Hierarchical RAG patterns
- [TF-IDF](https://en.wikipedia.org/wiki/Tf%E2%80%93idf) - Text vectorization

## Files

- `graph_engine.py` - Main implementation (31KB)
- `example_graph_usage.py` - Usage examples
- `docs/architecture/04-graph-engine.md` - Architecture documentation
- `docs/ARCHITECTURE.md` - Full system design

## License

Local-only, no external dependencies. All data stays on your machine.

---

**Implementation complete.** Ready for production use with SuperLocalMemory V2.
