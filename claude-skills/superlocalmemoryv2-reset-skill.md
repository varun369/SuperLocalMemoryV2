---
name: superlocalmemoryv2:reset
description: Reset or clear SuperLocalMemory V2 database (destructive)
arguments: command (status/soft/hard/layer), options
---

# SuperLocalMemory V2: Reset

Reset or clear SuperLocalMemory V2 database with multiple safety levels.

**⚠️ WARNING: Destructive operations create automatic backups but should be used carefully.**

## Usage

```bash
/superlocalmemoryv2:reset status
/superlocalmemoryv2:reset soft
/superlocalmemoryv2:reset hard --confirm
/superlocalmemoryv2:reset layer --layers graph patterns
```

## Commands

### `status` (Safe)
Shows current state before reset operations.

**Usage:**
```bash
/superlocalmemoryv2:reset status
```

**Output:**
- Current memory count
- Database size
- Last backup info
- Available reset options

---

### `soft` (⚠️ Destructive)
Clears all memories but preserves database schema, indexes, and configuration.

**Usage:**
```bash
/superlocalmemoryv2:reset soft
```

**What gets cleared:**
- All memory entries
- Knowledge graph nodes and edges
- Pattern learning data

**What's preserved:**
- Database schema
- Indexes and triggers
- Configuration settings
- Profile information

**Automatic actions:**
- Creates timestamped backup before clearing
- Rebuilds empty indexes
- Resets statistics counters

---

### `hard --confirm` (🔴 Nuclear Option)
Deletes entire database and recreates from scratch.

**Usage:**
```bash
/superlocalmemoryv2:reset hard --confirm
```

**Requires:** `--confirm` flag (safety measure)

**What happens:**
- Deletes entire database file
- Removes all indexes
- Clears all profiles
- Recreates fresh database with default schema
- Initializes empty knowledge graph

**Use cases:**
- Corrupted database recovery
- Complete fresh start
- Schema migration issues

---

### `layer --layers <names>` (Selective)
Clears specific subsystems while preserving others.

**Usage:**
```bash
/superlocalmemoryv2:reset layer --layers graph
/superlocalmemoryv2:reset layer --layers patterns
/superlocalmemoryv2:reset layer --layers graph patterns
```

**Available layers:**
- `graph`: Knowledge graph (nodes, edges, clusters)
- `patterns`: Pattern learning models and data
- `indexes`: Semantic search indexes (rebuilds automatically)
- `metadata`: Tags, projects, importance scores

**Use cases:**
- Rebuild corrupted knowledge graph
- Reset pattern learning after configuration changes
- Refresh semantic indexes

## Implementation

This skill executes: `~/.claude-memory/bin/superlocalmemoryv2:reset`

The command:
1. Validates reset command and arguments
2. Creates automatic backup (except status)
3. Executes requested reset operation
4. Rebuilds indexes/schema as needed
5. Reports completion status

## Safety Features

**Automatic Backups:**
All destructive operations create timestamped backups in:
`~/.claude-memory/backups/YYYY-MM-DD_HH-MM-SS/`

**Confirmation Required:**
Hard reset requires explicit `--confirm` flag

**Rollback Support:**
Backups can be restored using:
```bash
/superlocalmemoryv2:restore <backup-timestamp>
```

## Examples

**Check before resetting:**
```bash
/superlocalmemoryv2:reset status
```

**Clear all memories (keep schema):**
```bash
/superlocalmemoryv2:reset soft
```

**Complete nuclear reset:**
```bash
/superlocalmemoryv2:reset hard --confirm
```

**Rebuild knowledge graph only:**
```bash
/superlocalmemoryv2:reset layer --layers graph
```

**Clear patterns and indexes:**
```bash
/superlocalmemoryv2:reset layer --layers patterns indexes
```

## Notes

- All destructive operations create automatic backups
- Backups retained for 30 days (configurable)
- Soft reset is reversible via backup restoration
- Hard reset cannot restore profile-specific settings
- Layer reset useful for targeted troubleshooting
