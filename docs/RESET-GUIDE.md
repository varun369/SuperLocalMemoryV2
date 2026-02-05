# SuperLocalMemory V2 - Reset & Reinitialize Guide

## Overview

The reset utility provides safe ways to clear and restart your memory system.

**Always creates automatic backups before any reset operation.**

---

## Reset Options

### 1. **Soft Reset** (Clear Memories, Keep Schema)
- Deletes all memories, patterns, graph data
- **Keeps** V2 schema structure intact
- **Keeps** virtual environment
- Fast reinitialize - just add new memories

**Use when:** You want to start fresh but keep the system installed

```bash
python ~/.claude-memory/memory-reset.py soft
```

---

### 2. **Hard Reset** (Nuclear Option)
- Deletes entire database file
- Reinitializes fresh V2 schema
- **Keeps** Python code and virtual environment
- **Keeps** all backups
- Clean slate installation

**Use when:** You want completely fresh V2 database

```bash
python ~/.claude-memory/memory-reset.py hard --confirm
```

**⚠️ Requires `--confirm` flag for safety**

---

### 3. **Layer Reset** (Selective Cleanup)
- Clear specific layers only
- Keeps other layers intact
- Useful for rebuilding graph or patterns without losing memories

**Available layers:**
- `graph` - Clear graph_nodes, graph_edges, graph_clusters
- `patterns` - Clear identity_patterns, pattern_examples
- `tree` - Clear memory_tree structure
- `archive` - Clear memory_archive (compressed memories)

```bash
# Clear only graph and patterns
python ~/.claude-memory/memory-reset.py layer --layers graph patterns

# Clear only graph
python ~/.claude-memory/memory-reset.py layer --layers graph
```

---

### 4. **Status Check** (Non-Destructive)
- Shows current database statistics
- No changes made
- View row counts and database size

```bash
python ~/.claude-memory/memory-reset.py status
```

---

## Safety Features

### Automatic Backups
Every reset operation creates a timestamped backup:
```
~/.claude-memory/backups/pre-reset-YYYYMMDD-HHMMSS.db
```

**Skip backup** (not recommended):
```bash
python ~/.claude-memory/memory-reset.py soft --no-backup
```

### Confirmation Prompts
- **Soft reset:** Asks "yes/no" confirmation
- **Hard reset:** Requires typing "DELETE EVERYTHING"
- **Layer reset:** Asks "yes/no" confirmation

### Rollback
If you reset by mistake:
```bash
# Find latest backup
ls -lt ~/.claude-memory/backups/

# Restore backup
cp ~/.claude-memory/backups/pre-reset-20260205-143000.db \
   ~/.claude-memory/memory.db
```

---

## Common Scenarios

### Scenario 1: "I want to start completely fresh"
```bash
# Check current state
python ~/.claude-memory/memory-reset.py status

# Hard reset (creates backup automatically)
python ~/.claude-memory/memory-reset.py hard --confirm

# Type: DELETE EVERYTHING

# Verify clean state
python ~/.claude-memory/memory-reset.py status
```

**Result:** Fresh V2 database, ready for new memories

---

### Scenario 2: "I want to clear memories but keep structure"
```bash
# Soft reset
python ~/.claude-memory/memory-reset.py soft

# Type: yes

# Add new memories
python ~/.claude-memory/memory_store.py add "First new memory"
```

**Result:** Empty database with V2 schema intact

---

### Scenario 3: "My graph is corrupted, rebuild it"
```bash
# Clear only graph layer
python ~/.claude-memory/memory-reset.py layer --layers graph

# Rebuild graph from existing memories
~/.claude-memory/venv/bin/python ~/.claude-memory/graph_engine.py build
```

**Result:** Graph rebuilt, memories and patterns untouched

---

### Scenario 4: "Patterns learned wrong, reset them"
```bash
# Clear only patterns layer
python ~/.claude-memory/memory-reset.py layer --layers patterns

# Re-learn patterns
~/.claude-memory/venv/bin/python ~/.claude-memory/pattern_learner.py update
```

**Result:** Patterns re-learned, memories and graph untouched

---

## What Gets Deleted vs Kept

### Soft Reset Deletes:
- ✅ All memories (memories table cleared)
- ✅ All graph data (nodes, edges, clusters)
- ✅ All patterns (identity_patterns cleared)
- ✅ All tree structure
- ✅ All archives

### Soft Reset Keeps:
- ✅ V2 schema (all tables and indexes)
- ✅ Python code (memory_store_v2.py, etc.)
- ✅ Virtual environment
- ✅ Documentation
- ✅ All backups

### Hard Reset Deletes:
- ✅ Entire database file (memory.db)

### Hard Reset Keeps:
- ✅ Python code
- ✅ Virtual environment
- ✅ Documentation
- ✅ All backups

### Layer Reset Deletes:
- ✅ Only specified layers

### Layer Reset Keeps:
- ✅ Everything else

---

## Complete Uninstall (Not Included)

To completely remove SuperLocalMemory V2:
```bash
# Manual uninstall (use with caution)
rm -rf ~/.claude-memory/
```

**⚠️ This deletes everything including backups!**

Better approach - keep documentation:
```bash
# Keep docs, delete data
rm ~/.claude-memory/memory.db
rm -rf ~/.claude-memory/venv/
```

---

## Verification After Reset

### After Soft Reset:
```bash
# Check tables exist but are empty
python ~/.claude-memory/memory-reset.py status

# Should show:
# Memories: 0 rows
# Tree Nodes: 0 rows (or 1 root)
# Graph Nodes: 0 rows
# etc.
```

### After Hard Reset:
```bash
# Check fresh V2 schema
python ~/.claude-memory/memory-reset.py status

# Should show:
# All tables present
# All tables empty (0 rows)
# Database size: ~50KB (empty schema)
```

### After Layer Reset:
```bash
# Check specific layer cleared
python ~/.claude-memory/memory-reset.py status

# Example after clearing graph:
# Graph Nodes: 0 rows
# Graph Edges: 0 rows
# Graph Clusters: 0 rows
# Memories: 20 rows (kept)
```

---

## Best Practices

1. **Always check status first:**
   ```bash
   python ~/.claude-memory/memory-reset.py status
   ```

2. **Use layer reset when possible:**
   - More surgical than soft/hard reset
   - Preserves unaffected data

3. **Test with soft reset first:**
   - Less destructive than hard reset
   - Faster recovery if needed

4. **Keep backups:**
   - Don't use `--no-backup` unless testing
   - Check backup directory regularly

5. **Document why you reset:**
   - Keep notes on what prompted reset
   - Helps avoid repeating issues

---

## Troubleshooting

### "No database found"
**After soft/hard reset:**
- Expected after hard reset
- Run hard reset again to reinitialize

**Before any reset:**
- Check: `ls -la ~/.claude-memory/memory.db`
- Database may have been moved/deleted

### "Permission denied"
```bash
# Make script executable
chmod +x ~/.claude-memory/memory-reset.py

# Or run with python
python ~/.claude-memory/memory-reset.py status
```

### "Backup failed"
- Check disk space: `df -h`
- Check permissions: `ls -la ~/.claude-memory/`
- Manually create backup:
  ```bash
  cp ~/.claude-memory/memory.db ~/.claude-memory/backups/manual-backup.db
  ```

### "Hard reset didn't reinitialize"
- Run again (idempotent)
- Check for errors in output
- Manually verify schema:
  ```bash
  sqlite3 ~/.claude-memory/memory.db ".tables"
  ```

---

## Emergency Recovery

### If reset went wrong:
1. **Stop immediately** - Don't run more commands
2. **Check backups:**
   ```bash
   ls -lt ~/.claude-memory/backups/
   ```
3. **Restore latest backup:**
   ```bash
   cp ~/.claude-memory/backups/pre-reset-<timestamp>.db \
      ~/.claude-memory/memory.db
   ```
4. **Verify restoration:**
   ```bash
   python ~/.claude-memory/memory-reset.py status
   ```

---

## Quick Reference

| Command | What It Does | Safety Level |
|---------|-------------|--------------|
| `status` | Show statistics | 🟢 Safe (read-only) |
| `soft` | Clear memories, keep schema | 🟡 Destructive (backed up) |
| `hard --confirm` | Delete everything, reinit | 🔴 Nuclear (backed up) |
| `layer --layers X` | Clear specific layers | 🟡 Selective (backed up) |

---

**Remember:** All reset operations create automatic backups. You can always recover.
