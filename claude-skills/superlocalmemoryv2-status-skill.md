---
name: superlocalmemoryv2:status
description: Show SuperLocalMemory V2 system status and statistics
arguments: none
---

# SuperLocalMemory V2: Status

Displays comprehensive system status and statistics for SuperLocalMemory V2.

## Usage

```bash
/superlocalmemoryv2:status
```

## Features

**Memory Statistics**:
- Total memories count
- Memories by project
- Tag distribution
- Average importance scores

**Knowledge Graph Metrics**:
- Total nodes (entities/concepts)
- Total edges (relationships)
- Graph clusters count
- Average node degree

**Pattern Learning**:
- Active patterns count
- Pattern confidence scores
- Learning iteration count

**System Information**:
- Database size (MB)
- Active profile name
- Profile location
- Last backup timestamp
- Index health status

## Implementation

This skill executes: `~/.claude-memory/bin/superlocalmemoryv2:status`

The command:
1. Queries memory database for counts and statistics
2. Analyzes knowledge graph structure
3. Checks pattern learning model status
4. Computes database size and health metrics
5. Formats comprehensive status report

## Output Format

```
=== SuperLocalMemory V2 Status ===

Profile: default
Location: ~/.claude-memory/profiles/default/

MEMORY STATISTICS
-----------------
Total Memories:           247
By Project:
  - ecommerce:            45
  - ml-research:          32
  - general:              170

Top Tags:
  - react (67)
  - api (45)
  - database (38)

Average Importance:       0.73

KNOWLEDGE GRAPH
---------------
Nodes (Entities):         1,234
Edges (Relations):        3,567
Clusters:                 23
Avg Node Degree:          2.89
Graph Density:            0.0047

PATTERN LEARNING
----------------
Active Patterns:          89
Avg Confidence:           0.81
Learning Iterations:      12,456

SYSTEM
------
Database Size:            45.2 MB
Index Status:             Healthy
Last Backup:              2026-02-05 10:30:15
Last Optimization:        2026-02-04 03:00:00
```

## Examples

**Check system status:**
```bash
/superlocalmemoryv2:status
```

## Notes

- No arguments required
- Safe read-only operation
- Useful for monitoring memory system health
- Database optimization recommended if size > 100MB
- Automatic backups run daily at 3 AM
