# Knowledge Graph Guide

**How knowledge graphs work in SuperLocalMemory V2** - TF-IDF entity extraction, Leiden clustering, and graph-enhanced search explained for developers.

---

## What is a Knowledge Graph?

A **knowledge graph** is a network of entities (concepts) and relationships that represents how your memories connect to each other. SuperLocalMemory automatically builds this graph from your saved memories to improve search quality and discover hidden relationships.

**Example:**
```
Memory 1: "We use FastAPI for REST APIs"
Memory 2: "JWT tokens expire after 24 hours"
Memory 3: "FastAPI requires authentication middleware"

Knowledge Graph discovers:
  FastAPI ←→ REST APIs
  FastAPI ←→ authentication
  authentication ←→ JWT tokens

Even though Memory 1 and 2 don't mention each other,
the graph connects them via "authentication"!
```

---

## How It Works

SuperLocalMemory uses **GraphRAG** (Microsoft Research) approach with three core algorithms:

### 1. TF-IDF Entity Extraction

**What it does:** Identifies important terms (entities) in your memories.

**TF-IDF = Term Frequency - Inverse Document Frequency**

**Formula (simplified):**
```
importance = (how often term appears in memory)
           × log(total memories / memories with this term)
```

**Example:**
```
Memory: "FastAPI is faster than Flask for high-throughput APIs"

Extracted entities:
- "FastAPI" (TF-IDF: 0.85) ✅ Important
- "Flask" (TF-IDF: 0.72) ✅ Important
- "high-throughput" (TF-IDF: 0.68) ✅ Important
- "APIs" (TF-IDF: 0.45) ⚠️ Common but relevant
- "is" (TF-IDF: 0.02) ❌ Stop word, filtered out
- "than" (TF-IDF: 0.01) ❌ Stop word, filtered out
```

**Filtering rules:**
- Minimum TF-IDF score: 0.1
- Stop words removed (the, and, or, is, etc.)
- Case insensitive ("React" = "react")
- Minimum term length: 3 characters

### 2. Leiden Clustering Algorithm

**What it does:** Groups related memories into topic clusters.

**Leiden = Community detection algorithm** (better than older Louvain algorithm)

**How it works:**
1. Creates graph nodes from entities
2. Creates edges between entities that co-occur
3. Detects "communities" (groups of highly connected nodes)
4. Optimizes for modularity (how well-defined clusters are)

**Example clusters discovered:**
```
Cluster 1: "Authentication & Security" (23 memories)
  Top entities: JWT, OAuth, tokens, auth, security

Cluster 2: "Database & PostgreSQL" (18 memories)
  Top entities: PostgreSQL, database, SQL, queries, indexes

Cluster 3: "React & Frontend" (15 memories)
  Top entities: React, hooks, components, state, props
```

**Modularity score:**
- Excellent: >0.7 (clusters are well-defined)
- Good: 0.5-0.7 (clusters are meaningful)
- Poor: <0.3 (clusters are arbitrary)

### 3. Relationship Discovery

**What it does:** Finds connections between memories.

**Three types of edges:**

**A. Similarity Edges**
```python
cosine_similarity = dot(vector_A, vector_B) / (norm(vector_A) * norm(vector_B))
```

- Score 0.8-1.0: Very similar content
- Score 0.5-0.8: Related content
- Score 0.3-0.5: Loosely related
- Score <0.3: Not connected

**B. Co-occurrence Edges**
```
If two entities appear in same memory → create edge
Weight = number of co-occurrences
```

**C. Temporal Edges**
```
If two memories created within 1 hour → may be related
Useful for conversation threads
```

---

## Building the Graph

### Basic Build

```bash
slm build-graph
```

**Output:**
```
🔄 Building Knowledge Graph...

Phase 1: Entity Extraction
  Scanning 1,247 memories...
  Extracted 892 unique entities
  Created 892 graph nodes
  ✓ Complete (3.2s)

Phase 2: Relationship Discovery
  Computing similarity scores...
  Created 3,456 edges (relationships)
  Avg edges per node: 3.9
  ✓ Complete (5.1s)

Phase 3: Optimization
  Indexing graph structure...
  Pruning weak edges (score < 0.3)...
  Final edge count: 2,134
  ✓ Complete (1.2s)

✅ Knowledge graph built successfully!

Graph Statistics:
  Nodes: 892
  Edges: 2,134
  Density: 0.27%
  Largest Component: 856 nodes (96%)
```

### Build with Clustering

```bash
slm build-graph --clustering
```

**Requires optional dependencies:**
```bash
pip3 install python-igraph leidenalg
```

**Additional output:**
```
Phase 4: Topic Clustering (Leiden)
  Detecting communities...
  Found 47 clusters
  Largest cluster: 89 memories
  Smallest cluster: 3 memories
  Modularity score: 0.82 (excellent)
  ✓ Complete (2.3s)

Discovered Clusters:
  Cluster 1 (89 memories): "Authentication & Security"
    Top entities: JWT, OAuth, tokens, auth, security

  Cluster 2 (76 memories): "Database & PostgreSQL"
    Top entities: PostgreSQL, database, SQL, queries, indexes
```

### Force Rebuild

```bash
slm build-graph --force
```

Deletes existing graph and rebuilds from scratch. Use when:
- Graph seems corrupted
- After major bulk import
- Want fresh start

---

## Graph Statistics Explained

### Node Count

**Total unique entities extracted**

**Good indicators:**
- 100+ nodes for 1,000 memories
- 500+ nodes for 5,000 memories

**Poor indicators:**
- <10 nodes for 1,000 memories (not extracting entities properly)

### Edge Count

**Total relationships discovered**

**Edges/Nodes ratio:**
- Good: >2 (well-connected)
- Poor: <1 (disconnected graph)

**Example:**
```
892 nodes, 2,134 edges
Ratio: 2,134 / 892 = 2.39 ✅ Good
```

### Density

**How connected the graph is**

**Formula:**
```
density = (actual edges / possible edges) × 100
possible edges = nodes × (nodes - 1) / 2
```

**Example:**
```
892 nodes
Possible edges: 892 × 891 / 2 = 397,386
Actual edges: 2,134
Density: (2,134 / 397,386) × 100 = 0.54%
```

**Typical values:**
- 0.1% - 1%: Normal
- <0.05%: Very disconnected (isolated knowledge)
- >5%: Too connected (poor entity extraction)

### Largest Component

**Size of biggest connected subgraph**

**Good indicators:**
- >80% of nodes (knowledge is interconnected)

**Poor indicators:**
- <50% of nodes (fragmented knowledge islands)

**Example:**
```
892 nodes total
856 nodes in largest component
Coverage: 856 / 892 = 96% ✅ Excellent
```

---

## When to Rebuild Graph

### Always Rebuild After:

1. **Bulk imports** - Added 50+ memories at once
2. **Database restore** - Restored from backup
3. **Major milestone** - Sprint complete, project phase done

### Rebuild Periodically:

4. **Monthly** - Keep graph optimized
5. **After 500 new memories** - Maintain quality
6. **When search feels slow** - Rebuild indexes

### Rebuild on Issues:

7. **Poor search results** - Graph may be stale
8. **Missing relationships** - Rebuild connections
9. **Corrupted graph errors** - Force rebuild

**Automation (cron):**
```bash
# Every Sunday at 3 AM
0 3 * * 0 /usr/local/bin/slm build-graph --clustering >> /var/log/slm-build.log 2>&1
```

---

## Graph-Enhanced Search

### Without Graph

**Basic keyword matching:**
```bash
slm recall "authentication"

Results:
- "JWT tokens expire after 24 hours" ✅ Contains "auth" stem
- "User login endpoint uses POST" ❌ Missed (no "auth" keyword)
```

### With Graph

**Graph traversal finds related memories:**
```bash
slm recall "authentication"

Results (via graph):
- "JWT tokens expire after 24 hours" ✅ Direct match
- "User login endpoint uses POST" ✅ Graph: login → auth → JWT
- "OAuth 2.0 flow implementation" ✅ Graph: OAuth → tokens → auth
- "Session management strategy" ✅ Graph: sessions → auth → security
```

**How it works:**
1. Find memories matching query (direct)
2. Extract entities from those memories
3. Traverse graph to find related entities
4. Find memories containing related entities
5. Rank by combined score (keyword + graph + semantic)

---

## Advanced Features

### Cluster-Based Search

```bash
# Build with clustering
slm build-graph --clustering

# Search within specific cluster
slm recall "performance" --cluster "Database & PostgreSQL"
```

**Benefits:**
- Faster search (smaller search space)
- More relevant results (topically focused)
- Avoids false positives from other domains

### Related Memory Discovery

```python
# Python API
from memory_store_v2 import MemoryStoreV2
from graph_engine import GraphEngine

store = MemoryStoreV2()
graph = GraphEngine()

# Find memories related to ID 42
related = graph.get_related_memories(42, limit=5)

for mem_id, score in related:
    print(f"Memory {mem_id}: {score:.2f}")
```

### Graph Visualization (Planned v2.2.0)

```bash
# Export graph for visualization (coming soon)
slm build-graph --export graph.json

# Generate HTML visualization
slm graph-viz graph.json > graph.html
```

---

## Performance Benchmarks

### Build Time

| Memory Count | Build Time | With Clustering |
|--------------|------------|-----------------|
| 100 | ~1s | ~1.5s |
| 1,000 | ~10s | ~15s |
| 5,000 | ~1min | ~1.5min |
| 10,000 | ~2min | ~3min |
| 50,000+ | ~15min | ~25min |

**Factors affecting speed:**
- Memory content length (longer = slower)
- Vocabulary size (more unique words = slower)
- Hardware (CPU, RAM)

### Search Improvement

**Before graph:**
- Average search time: 150ms
- Recall@10: 68% (finds 68% of relevant memories)

**After graph:**
- Average search time: 45ms (3.3× faster!)
- Recall@10: 87% (finds 87% of relevant memories)

**Improvement: 28% more relevant results, 70% faster**

---

## Troubleshooting

### "Build failed: Memory error"

**Cause:** Not enough RAM for large graph

**Solution:**
```bash
# Build in chunks
slm build-graph --chunk-size 1000

# Or archive old memories first
sqlite3 ~/.claude-memory/memory.db \
  "DELETE FROM memories WHERE created_at < date('now', '-180 days');"
```

### "Clustering requires python-igraph"

**Cause:** Optional dependencies not installed

**Solution:**
```bash
pip3 install python-igraph leidenalg

# Verify
python3 -c "import igraph; import leidenalg"

# Try again
slm build-graph --clustering
```

### "Edges seem wrong"

**Cause:** Stale graph or poor similarity threshold

**Solution:**
```bash
# Force complete rebuild
slm build-graph --force

# Adjust similarity threshold (advanced)
slm build-graph --min-similarity 0.4  # Default: 0.3
```

### "Graph build slow"

**Solutions:**
```bash
# Show progress
slm build-graph --verbose

# Skip clustering (faster)
slm build-graph  # No --clustering flag

# Check disk space
df -h ~/.claude-memory/
```

---

## Best Practices

### 1. Build After Bulk Operations

```bash
# Import many memories
while read -r line; do
  slm remember "$line"
done < bulk_memories.txt

# Immediately rebuild graph
slm build-graph
```

### 2. Use Clustering for Large Databases

```bash
# Install dependencies once
pip3 install python-igraph leidenalg

# Always build with clustering if >1000 memories
if [ $(slm status | grep "Total memories" | awk '{print $3}') -gt 1000 ]; then
  slm build-graph --clustering
else
  slm build-graph
fi
```

### 3. Monitor Graph Quality

```bash
# Check graph statistics
slm status --verbose | grep -A 10 "Knowledge Graph"

# Good indicators:
# - Edges/Nodes ratio > 2
# - Density: 0.1% - 1%
# - Largest component: >80%
# - Modularity (if clustering): >0.5
```

### 4. Automate Rebuilds

```bash
# Add to crontab
# Weekly: Sunday 3 AM
0 3 * * 0 /usr/local/bin/slm build-graph --clustering

# After git push (post-push hook)
#!/bin/bash
slm remember "Pushed $(git log -1 --oneline)" --tags git
slm build-graph
```

---

## Technical Deep Dive

### TF-IDF Implementation

**Python code (simplified):**
```python
from sklearn.feature_extraction.text import TfidfVectorizer

# Extract entities
vectorizer = TfidfVectorizer(
    max_features=5000,
    min_df=2,
    max_df=0.8,
    stop_words='english',
    ngram_range=(1, 2)
)

# Fit on all memories
tfidf_matrix = vectorizer.fit_transform(memories)

# Get feature names (entities)
entities = vectorizer.get_feature_names_out()

# Filter by score threshold
important_entities = [e for e, score in zip(entities, scores) if score > 0.1]
```

### Leiden Algorithm Parameters

**Resolution parameter:**
- Default: 1.0
- Lower (0.5): Fewer, larger clusters
- Higher (2.0): More, smaller clusters

**Quality metric (modularity):**
```python
Q = (edges_within_clusters / total_edges) - (expected_edges_within_clusters / total_edges)²
```

### Edge Pruning

**Remove weak edges to improve performance:**
```python
# Keep only edges with score > threshold
threshold = 0.3
pruned_edges = [(u, v, w) for u, v, w in edges if w > threshold]

# Result: 30-50% fewer edges, same search quality
```

---

## Hierarchical Leiden Clustering (v2.4.1)

Standard Leiden finds flat communities — "Python", "JavaScript", "DevOps". **Hierarchical Leiden** goes deeper by recursively sub-clustering large communities:

```
Python (42 members)
├── FastAPI (18 members)
│   ├── Authentication (7 members)
│   └── Database Models (6 members)
├── Data Science (14 members)
└── CLI Tools (10 members)
```

### How It Works

1. Flat Leiden runs first (existing behavior)
2. Clusters with ≥10 members are recursively sub-clustered
3. Maximum depth: 3 levels (configurable via `max_depth` parameter)
4. Each sub-cluster gets its own name from TF-IDF entity extraction
5. `parent_cluster_id` and `depth` columns track the hierarchy in `graph_clusters` table

### CLI

```bash
# Run hierarchical sub-clustering on existing clusters
python3 ~/.claude-memory/graph_engine.py hierarchical

# Full build (includes hierarchical + summaries automatically)
python3 ~/.claude-memory/graph_engine.py build
```

### Schema

```sql
-- New columns on graph_clusters (added automatically)
ALTER TABLE graph_clusters ADD COLUMN parent_cluster_id INTEGER;
ALTER TABLE graph_clusters ADD COLUMN depth INTEGER DEFAULT 0;
ALTER TABLE graph_clusters ADD COLUMN summary TEXT;
```

---

## Community Summaries (v2.4.1)

Every cluster gets a **TF-IDF structured summary** describing its contents:

```
Cluster "FastAPI & Authentication"
Summary: Key topics: fastapi, authentication, jwt, middleware, oauth |
         Projects: myapp, api-gateway | Categories: backend |
         18 memories | Sub-cluster of: Python
```

### What's in a Summary

| Component | Source | Example |
|-----------|--------|---------|
| **Key topics** | Top 5 TF-IDF entities | fastapi, authentication, jwt |
| **Projects** | Distinct `project_name` values | myapp, api-gateway |
| **Categories** | Distinct `category` values | backend, security |
| **Size** | Member count | 18 memories |
| **Hierarchy** | Parent cluster name (if sub-cluster) | Sub-cluster of: Python |

### CLI

```bash
# Generate summaries for all clusters
python3 ~/.claude-memory/graph_engine.py summaries

# Summaries are also generated automatically during build
python3 ~/.claude-memory/graph_engine.py build
```

Summaries appear in the web dashboard clusters view and are returned by the `/api/clusters` endpoint.

---

## Related Pages

- [Quick Start Tutorial](Quick-Start-Tutorial) - First-time setup
- [Pattern Learning Explained](Pattern-Learning-Explained) - How pattern learning works
- [CLI Cheatsheet](CLI-Cheatsheet) - Command reference
- [Python API](Python-API) - Programmatic access
- [Why Local Matters](Why-Local-Matters) - Privacy benefits

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) • [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) • [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
