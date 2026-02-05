---
name: superlocalmemoryv2:list
description: List recent memories with optional filtering
arguments: --limit (optional), --sort (optional)
---

# SuperLocalMemory V2: List

Lists memories from SuperLocalMemory V2 with flexible filtering and sorting options.

## Usage

```bash
/superlocalmemoryv2:list
/superlocalmemoryv2:list --limit 10
/superlocalmemoryv2:list --sort importance
/superlocalmemoryv2:list --limit 5 --sort accessed
```

## Features

**Configurable Limit**: Default 20, adjustable via --limit
**Multiple Sort Options**:
  - `recent`: Sort by creation date (newest first) - default
  - `accessed`: Sort by last access time
  - `importance`: Sort by importance score (AI-computed)
  - `frequency`: Sort by access frequency

**Formatted Output**: Clean table with metadata

## Implementation

This skill executes: `~/.claude-memory/bin/superlocalmemoryv2:list`

The command:
1. Queries active profile's memory database
2. Applies sort and limit parameters
3. Formats results as readable table
4. Includes metadata: tags, dates, scores

## Output Format

```
Total Memories: 247

ID    Content Preview                           Tags              Created     Accessed    Score
--------------------------------------------------------------------------------------------
1234  React hooks pattern for state...          react,frontend    2026-02-01  2026-02-05  0.95
1235  API rate limiting best practices...       api,backend       2026-01-28  2026-02-04  0.87
1236  Database indexing strategies...           database,perf     2026-01-25  2026-02-03  0.82
```

## Examples

**Default listing (20 recent):**
```bash
/superlocalmemoryv2:list
```

**Top 5 most important:**
```bash
/superlocalmemoryv2:list --limit 5 --sort importance
```

**Recently accessed:**
```bash
/superlocalmemoryv2:list --sort accessed
```

**Frequently used:**
```bash
/superlocalmemoryv2:list --limit 10 --sort frequency
```

## Notes

- Default limit: 20 memories
- Default sort: recent (creation date)
- Importance scores computed by AI based on content and usage patterns
- Access frequency updated on each recall operation
