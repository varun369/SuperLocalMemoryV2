# SuperLocalMemory V2: Graph Stats

View knowledge graph statistics including clusters, entities, and relationships.

## Usage

```
/superlocalmemoryv2:graph-stats
```

## What This Skill Does

Displays comprehensive statistics about your knowledge graph:
- Total number of clusters discovered
- Total entities extracted
- Cluster names and sizes
- Average cluster metrics
- Graph health indicators

## Examples

```bash
# View current graph statistics
/superlocalmemoryv2:graph-stats
```

## Implementation

This skill runs:
```bash
cd ~/.claude-memory && python3 graph_engine.py stats
```

## Output Format

```
Knowledge Graph Statistics:
==========================

Overview:
- Total Memories: 20
- Total Clusters: 6
- Total Entities: 45
- Average Cluster Size: 3.3 memories
- Last Built: 2026-02-05 14:30:00

Discovered Clusters:
--------------------
1. "Authentication & Security" (5 memories)
   Key entities: JWT, tokens, auth, security, refresh

2. "React & Frontend" (4 memories)
   Key entities: React, hooks, components, UI, state

3. "Performance & Optimization" (3 memories)
   Key entities: performance, optimization, queries, indexes

4. "DevOps & Deployment" (3 memories)
   Key entities: Docker, Kubernetes, deployment, CI/CD

5. "Database & Backend" (3 memories)
   Key entities: database, API, queries, endpoints

6. "Testing & Quality" (2 memories)
   Key entities: testing, tests, quality, coverage
```

## Use Cases

**Knowledge Discovery:**
- "What topics have I worked on?"
- "How are my memories organized?"
- "What are my main focus areas?"

**Health Monitoring:**
- Check graph freshness (last build time)
- Verify cluster coverage
- Identify isolated memories

**Planning:**
- Identify knowledge gaps
- Plan learning paths
- Organize documentation

## Prerequisites

- SuperLocalMemory V2 installed
- Knowledge graph built (use `/superlocalmemoryv2:graph-build`)
- At least 2 memories in database

## Integration with Other Skills

Use stats to guide next actions:
- View cluster details: `/superlocalmemoryv2:cluster --cluster-id X`
- Find related memories: `/superlocalmemoryv2:related --memory-id Y`
- Rebuild if outdated: `/superlocalmemoryv2:graph-build`

## Pro Tips

- Run after major graph rebuilds to verify results
- Use to identify dominant themes in your work
- Check cluster sizes to find underrepresented topics
- Monitor last build time for maintenance scheduling

---

**Part of SuperLocalMemory V2 - Standalone intelligent memory system**
