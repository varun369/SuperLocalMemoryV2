# SuperLocalMemory V2: Graph Build

Build or rebuild the knowledge graph to discover relationships between memories.

## Usage

```
/superlocalmemoryv2:graph-build
```

## What This Skill Does

Analyzes all memories and builds a knowledge graph:
- Extracts key entities using TF-IDF
- Discovers relationships between memories
- Creates thematic clusters using Leiden algorithm
- Auto-names clusters based on common themes

## Examples

```bash
# Build/rebuild entire knowledge graph
/superlocalmemoryv2:graph-build
```

## Implementation

This skill runs:
```bash
cd ~/.claude-memory && python3 graph_engine.py build
```

## What Gets Built

**Entities Extracted:**
- Technical terms (React, JWT, Docker, etc.)
- Concepts (authentication, performance, security)
- Technologies and frameworks

**Clusters Created:**
- Automatically groups related memories
- Names clusters based on common themes
- Examples: "Authentication & Security", "React & Frontend", "DevOps & Deployment"

**Relationships Discovered:**
- Shared entities between memories
- Thematic connections
- Temporal patterns

## Output

```
Building knowledge graph...
Extracted 45 entities from 20 memories
Created 6 clusters using Leiden algorithm

Cluster 1: "Authentication & Security" (5 memories)
Cluster 2: "React & Frontend" (4 memories)
Cluster 3: "Performance & Optimization" (3 memories)
...

Knowledge graph build complete!
```

## When to Rebuild

Rebuild the graph:
- After adding 10+ new memories
- Weekly maintenance routine
- Before important searches or presentations
- When you notice outdated relationships

## Performance

- 20 memories: < 0.1 seconds
- 100 memories: < 2 seconds
- 500 memories: ~15 seconds

## Prerequisites

- SuperLocalMemory V2 installed
- At least 2 memories in database
- Python 3.8+ with scikit-learn (auto-installed)

## Integration with Other Skills

After building graph:
- `/superlocalmemoryv2:graph-stats` - View cluster statistics
- `/superlocalmemoryv2:related --memory-id X` - Find related memories
- `/superlocalmemoryv2:cluster --cluster-id Y` - View cluster details

---

**Part of SuperLocalMemory V2 - Standalone intelligent memory system**
