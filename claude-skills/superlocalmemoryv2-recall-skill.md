---
name: superlocalmemoryv2:recall
description: Search and retrieve memories using semantic similarity
arguments: query (required), --limit (optional)
---

# SuperLocalMemory V2: Recall

Searches SuperLocalMemory V2 using advanced retrieval methods:
- TF-IDF semantic similarity scoring
- Knowledge graph relationship traversal
- Full-text search with ranking
- Hybrid retrieval combining multiple signals

## Usage

```bash
/superlocalmemoryv2:recall "React patterns"
/superlocalmemoryv2:recall "API design" --limit 5
/superlocalmemoryv2:recall "database optimization" --limit 10
```

## Features

**Semantic Search**: Uses TF-IDF vectors to find conceptually similar memories
**Graph Relationships**: Traverses knowledge graph for related concepts
**Full-Text Search**: SQLite FTS5 for exact phrase matching
**Ranked Results**: Combined scoring from multiple retrieval methods
**Relevance Scores**: Each result includes similarity score (0-1)

## Implementation

This skill executes: `~/.claude-memory/bin/superlocalmemoryv2:recall`

The command:
1. Parses query and generates TF-IDF vector
2. Searches semantic index (cosine similarity)
3. Queries knowledge graph for related nodes
4. Performs full-text search
5. Combines and ranks results
6. Returns top N with relevance scores

## Output Format

```
Results for "React patterns":

1. [Score: 0.95] React hooks pattern for state management
   Tags: react, frontend, hooks
   Created: 2026-02-01 | Accessed: 2026-02-05

2. [Score: 0.87] Custom hooks best practices
   Tags: react, patterns
   Created: 2026-01-28 | Accessed: 2026-02-05
```

## Examples

**Simple search:**
```bash
/superlocalmemoryv2:recall "authentication"
```

**Limited results:**
```bash
/superlocalmemoryv2:recall "machine learning algorithms" --limit 3
```

**Broad concept search:**
```bash
/superlocalmemoryv2:recall "performance optimization"
```

## Notes

- Default limit: 10 results
- Minimum relevance score: 0.3 (configurable)
- Results sorted by combined relevance score
- Updates access timestamps and frequency counters
