# CLI Cheatsheet

**Quick reference for all SuperLocalMemory V2 commands** - Copy-paste ready commands organized by task for fast lookup.

---

## Memory Operations

### Remember (Save)

```bash
# Basic memory
slm remember "content"

# With tags
slm remember "content" --tags tag1,tag2,tag3

# With project
slm remember "content" --project myapp

# With importance (1-10)
slm remember "content" --importance 8

# All options combined
slm remember "Critical: Production requires approval" \
  --tags deployment,production \
  --project myapp \
  --importance 10
```

**Parameters:**
- `content` - Text to remember (required)
- `--tags` - Comma-separated tags (optional)
- `--project` - Project name (optional, default: "default")
- `--importance` - Priority 1-10 (optional, default: 5)

### Recall (Search)

```bash
# Basic search
slm recall "query"

# Limit results
slm recall "query" --limit 5

# Minimum relevance score (0.0-1.0)
slm recall "query" --min-score 0.7

# Filter by tags
slm recall "query" --tags security,auth

# Filter by project
slm recall "query" --project myapp

# Combined filters
slm recall "authentication" \
  --limit 3 \
  --min-score 0.7 \
  --tags security \
  --project myapp
```

**Parameters:**
- `query` - Search query (required)
- `--limit` - Max results (optional, default: 10)
- `--min-score` - Minimum relevance 0.0-1.0 (optional, default: 0.3)
- `--tags` - Filter by tags (optional)
- `--project` - Filter by project (optional)

### List Recent

```bash
# List 10 most recent
slm list

# Custom limit
slm list --limit 20

# Filter by project
slm list --project myapp

# Filter by tags
slm list --tags important
```

**Parameters:**
- `--limit` - Number to show (optional, default: 10)
- `--project` - Filter by project (optional)
- `--tags` - Filter by tags (optional)

---

## Knowledge Graph

### Build Graph

```bash
# Build or update graph
slm build-graph

# Force complete rebuild
slm build-graph --force

# With topic clustering (requires python-igraph, leidenalg)
slm build-graph --clustering

# Verbose output
slm build-graph --verbose

# Dry run (preview without saving)
slm build-graph --dry-run
```

**When to run:**
- After bulk imports (50+ memories)
- Monthly maintenance
- When search quality degrades
- After database restore

See [Knowledge Graph Guide](Knowledge-Graph-Guide) for details.

### Graph Statistics

```bash
# View graph stats
slm status

# Detailed graph info
slm status --verbose
```

---

## Profile Management

### Switch Profiles

```bash
# List all profiles
slm switch-profile list

# Create new profile
slm switch-profile create work --description "Work projects"

# Switch to profile
slm switch-profile work

# Switch back to default
slm switch-profile default

# Delete profile (with confirmation)
slm switch-profile delete work --confirm
```

**Use cases:**
- Separate work/personal memories
- Client-specific knowledge bases
- Project-specific contexts
- Experimentation sandboxes

See [Multi-Profile Workflows](Multi-Profile-Workflows) for best practices.

---

## System Management

### Status Check

```bash
# Basic status
slm status

# Verbose with all details
slm status --verbose

# JSON output (for scripts)
slm status --format json
```

**Status includes:**
- Total memories count
- Database size
- Knowledge graph statistics
- Pattern learning stats
- Current active profile

### Pattern Learning

```bash
# Update learned patterns
python3 ~/.claude-memory/pattern_learner.py update

# Get identity context
python3 ~/.claude-memory/pattern_learner.py context 0.5

# View all patterns
python3 ~/.claude-memory/pattern_learner.py list

# Reset patterns
python3 ~/.claude-memory/pattern_learner.py reset
```

See [Pattern Learning Explained](Pattern-Learning-Explained) for details.

---

## Advanced Operations

### Database Management

```bash
# Check database integrity
sqlite3 ~/.claude-memory/memory.db "PRAGMA integrity_check;"

# Count total memories
sqlite3 ~/.claude-memory/memory.db "SELECT COUNT(*) FROM memories;"

# List all tags
sqlite3 ~/.claude-memory/memory.db "SELECT DISTINCT tag FROM memory_tags ORDER BY tag;"

# Vacuum database (optimize space)
sqlite3 ~/.claude-memory/memory.db "VACUUM;"

# Backup database
cp ~/.claude-memory/memory.db ~/.claude-memory/memory.db.backup
```

### Export/Import

```bash
# Export all memories to JSON
sqlite3 ~/.claude-memory/memory.db \
  "SELECT json_group_array(json_object(
    'id', id,
    'content', content,
    'tags', tags,
    'project_name', project_name,
    'created_at', created_at
  )) FROM memories;" > memories.json

# Import from JSON (Python script)
python3 << 'EOF'
import json, sqlite3
conn = sqlite3.connect("/Users/$(whoami)/.claude-memory/memory.db")
with open('memories.json') as f:
    data = json.load(f)
    for mem in data:
        conn.execute(
            "INSERT INTO memories (content, tags, project_name) VALUES (?, ?, ?)",
            (mem['content'], mem['tags'], mem['project_name'])
        )
conn.commit()
EOF
```

### Bulk Operations

```bash
# Bulk import from text file (one per line)
while IFS= read -r line; do
  slm remember "$line"
done < memories.txt

# Bulk import from CSV
while IFS=',' read -r content tags project importance; do
  slm remember "$content" \
    --tags "$tags" \
    --project "$project" \
    --importance "$importance"
done < memories.csv

# Bulk tag update (SQL)
sqlite3 ~/.claude-memory/memory.db \
  "UPDATE memories SET tags = tags || ',reviewed' WHERE created_at < date('now', '-30 days');"
```

---

## Scripting & Automation

### Daily Standup Helper

```bash
#!/bin/bash
# Save as: ~/bin/standup.sh

echo "Yesterday's Decisions:"
slm recall "decided" --limit 5

echo -e "\nCurrent Blockers:"
slm recall "blocked" --tags critical --limit 3

echo -e "\nRecent TODOs:"
slm recall "TODO" --limit 5
```

### Git Post-Commit Hook

```bash
#!/bin/bash
# Save as: .git/hooks/post-commit

commit_msg=$(git log -1 --pretty=%B)
commit_hash=$(git log -1 --pretty=%H)

slm remember "Commit: $commit_msg (${commit_hash:0:7})" \
  --tags git,commit \
  --project "$(basename $(git rev-parse --show-toplevel))"
```

### Weekly Graph Rebuild (Cron)

```bash
# Add to crontab (crontab -e)
# Every Sunday at 3 AM
0 3 * * 0 /usr/local/bin/slm build-graph --clustering >> /var/log/slm-build.log 2>&1
```

### Context Injection for Aider

```bash
# Use aider-smart wrapper (auto-context injection)
aider-smart

# Or manually inject context
context=$(slm recall "current project" --limit 3 --min-score 0.7)
aider --message "Context: $context. Now help me with..."
```

---

## Output Formatting

### JSON Output

```bash
# Status as JSON
slm status --format json

# Search results as JSON
slm recall "query" --format json

# Parse with jq
slm recall "FastAPI" --format json | jq '.results[0].content'
```

### CSV Output

```bash
# Export search results to CSV
slm recall "query" --format csv > results.csv

# Import into spreadsheet
# File → Import → CSV
```

---

## Common Tasks

### Setup New Project

```bash
# Create project profile
slm switch-profile create myproject

# Add initial context
slm remember "Tech stack: FastAPI, PostgreSQL, React" --project myproject
slm remember "Repository: github.com/me/myproject" --project myproject
slm remember "Team: @alice, @bob, @charlie" --project myproject

# Build initial graph
slm build-graph
```

### Search by Time Range

```bash
# Last 7 days (SQL)
sqlite3 ~/.claude-memory/memory.db \
  "SELECT id, content, created_at FROM memories WHERE created_at >= date('now', '-7 days') ORDER BY created_at DESC;"

# Specific date range
sqlite3 ~/.claude-memory/memory.db \
  "SELECT id, content FROM memories WHERE created_at BETWEEN '2026-02-01' AND '2026-02-07';"
```

### Find High-Importance Memories

```bash
# Importance >= 8
sqlite3 ~/.claude-memory/memory.db \
  "SELECT id, content, importance FROM memories WHERE importance >= 8 ORDER BY importance DESC;"
```

### Archive Old Memories

```bash
# Export old memories (90+ days)
sqlite3 ~/.claude-memory/memory.db \
  "SELECT * FROM memories WHERE created_at < date('now', '-90 days');" > old_memories.sql

# Delete old memories (with backup first!)
cp ~/.claude-memory/memory.db ~/.claude-memory/memory.db.backup
sqlite3 ~/.claude-memory/memory.db \
  "DELETE FROM memories WHERE created_at < date('now', '-90 days');"

# Rebuild graph
slm build-graph --force
```

---

## Troubleshooting Commands

### Check Installation

```bash
# Verify files exist
ls -la ~/.claude-memory/
ls -la ~/.claude-memory/memory.db

# Check slm command
which slm

# Test database
sqlite3 ~/.claude-memory/memory.db "SELECT COUNT(*) FROM memories;"
```

### Fix Permissions

```bash
# Fix directory permissions
chmod 755 ~/.claude-memory/

# Fix database permissions
chmod 644 ~/.claude-memory/memory.db

# Fix script permissions
chmod +x ~/.claude-memory/*.py
```

### Database Repair

```bash
# Check integrity
sqlite3 ~/.claude-memory/memory.db "PRAGMA integrity_check;"

# Rebuild indexes
sqlite3 ~/.claude-memory/memory.db "REINDEX;"

# Vacuum
sqlite3 ~/.claude-memory/memory.db "VACUUM;"
```

### Reset Everything

```bash
# Backup first!
cp -r ~/.claude-memory/ ~/.claude-memory.backup/

# Soft reset (clear memories, keep structure)
rm ~/.claude-memory/memory.db
cd ~/path/to/SuperLocalMemoryV2
./install.sh

# Hard reset (complete removal)
rm -rf ~/.claude-memory/
cd ~/path/to/SuperLocalMemoryV2
./install.sh
```

---

## Quick Reference Table

| Task | Command | Notes |
|------|---------|-------|
| Save memory | `slm remember "text"` | Basic save |
| Search | `slm recall "query"` | Multi-method search |
| List recent | `slm list` | Last 10 by default |
| System status | `slm status` | Health check |
| Build graph | `slm build-graph` | Improve search |
| Switch profile | `slm switch-profile <name>` | Change context |
| View patterns | `python3 ~/.claude-memory/pattern_learner.py list` | Learned preferences |
| Database backup | `cp ~/.claude-memory/memory.db backup.db` | Safety first |
| Check integrity | `sqlite3 ~/.claude-memory/memory.db "PRAGMA integrity_check;"` | Verify DB |
| Count memories | `sqlite3 ~/.claude-memory/memory.db "SELECT COUNT(*) FROM memories;"` | Total count |

---

## Related Pages

- [Quick Start Tutorial](Quick-Start-Tutorial) - First-time setup
- [Python API](Python-API) - Programmatic access
- [Configuration](Configuration) - Advanced settings
- [Knowledge Graph Guide](Knowledge-Graph-Guide) - Graph features
- [Multi-Profile Workflows](Multi-Profile-Workflows) - Profile management

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) • [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) • [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
