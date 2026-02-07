# Configuration

**Configuration options, environment variables, and performance tuning** for SuperLocalMemory V2 - Customize behavior, optimize performance, and adjust settings for your workflow.

---

## Configuration Files

SuperLocalMemory V2 uses multiple configuration files:

### Global Configuration

**Location:** `~/.claude-memory/config.json`

**Purpose:** System-wide settings affecting all profiles

**Default:**
```json
{
  "version": "2.1.0",
  "default_profile": "default",
  "mcp_server_enabled": true,
  "shell_integration": true,
  "auto_build_graph": false,
  "pattern_learning_enabled": true,
  "telemetry": false
}
```

### Profile Configuration

**Location:** `~/.claude-memory/profiles/<profile>/config.json`

**Purpose:** Profile-specific settings

**Default:**
```json
{
  "profile_name": "default",
  "description": "Default profile",
  "created_at": "2026-02-07T14:23:00",
  "settings": {
    "default_importance": 5,
    "auto_build_graph": false,
    "pattern_learning_threshold": 0.5,
    "search_min_score": 0.3,
    "compression_enabled": false
  }
}
```

### MCP Server Configuration

**Location:** IDE-specific (see [Quick Start Tutorial](Quick-Start-Tutorial))
- Cursor: `~/.cursor/mcp_settings.json`
- Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windsurf: `~/.windsurf/mcp_settings.json`

**Format:**
```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": ["/Users/username/.claude-memory/mcp_server.py"],
      "cwd": "/Users/username/.claude-memory",
      "env": {
        "PYTHONPATH": "/Users/username/.claude-memory"
      },
      "description": "SuperLocalMemory V2"
    }
  }
}
```

---

## Environment Variables

### Core Variables

#### SLM_PROFILE

**Description:** Override default profile

**Usage:**
```bash
export SLM_PROFILE=work
slm status  # Uses work profile

# Temporary override
SLM_PROFILE=personal slm recall "query"
```

#### SLM_DB_PATH

**Description:** Custom database location

**Usage:**
```bash
export SLM_DB_PATH=/custom/path/memory.db
slm remember "test"  # Saves to custom location
```

#### SLM_CONFIG_PATH

**Description:** Custom config file location

**Usage:**
```bash
export SLM_CONFIG_PATH=/custom/config.json
```

#### PYTHONPATH

**Description:** Python module search path (required for MCP server)

**Usage:**
```bash
export PYTHONPATH=$HOME/.claude-memory:$PYTHONPATH
```

### Performance Variables

#### SLM_CACHE_SIZE

**Description:** In-memory cache size (MB)

**Default:** 50

**Usage:**
```bash
export SLM_CACHE_SIZE=100  # 100MB cache
```

#### SLM_MAX_WORKERS

**Description:** Parallel processing threads

**Default:** 4

**Usage:**
```bash
export SLM_MAX_WORKERS=8  # 8 threads for graph building
```

#### SLM_GRAPH_CHUNK_SIZE

**Description:** Memories per graph build chunk

**Default:** 1000

**Usage:**
```bash
export SLM_GRAPH_CHUNK_SIZE=500  # Smaller chunks = less memory usage
```

### Debug Variables

#### SLM_DEBUG

**Description:** Enable debug logging

**Usage:**
```bash
export SLM_DEBUG=1
slm recall "query"  # Shows debug output
```

#### SLM_LOG_LEVEL

**Description:** Logging level

**Values:** DEBUG, INFO, WARNING, ERROR

**Usage:**
```bash
export SLM_LOG_LEVEL=DEBUG
```

#### SLM_LOG_FILE

**Description:** Log file location

**Usage:**
```bash
export SLM_LOG_FILE=/tmp/slm-debug.log
```

---

## Configuration Options

### Memory Settings

#### default_importance

**Description:** Default importance for new memories

**Type:** Integer (1-10)

**Default:** 5

**Usage:**
```json
{
  "settings": {
    "default_importance": 7
  }
}
```

#### max_content_size

**Description:** Maximum memory content size (bytes)

**Type:** Integer

**Default:** 1048576 (1MB)

**Usage:**
```json
{
  "settings": {
    "max_content_size": 2097152
  }
}
```

#### max_tags

**Description:** Maximum tags per memory

**Type:** Integer

**Default:** 50

**Usage:**
```json
{
  "settings": {
    "max_tags": 20
  }
}
```

### Search Settings

#### search_min_score

**Description:** Minimum relevance score for search results

**Type:** Float (0.0-1.0)

**Default:** 0.3

**Usage:**
```json
{
  "settings": {
    "search_min_score": 0.5
  }
}
```

#### search_default_limit

**Description:** Default number of search results

**Type:** Integer

**Default:** 10

**Usage:**
```json
{
  "settings": {
    "search_default_limit": 20
  }
}
```

#### search_methods

**Description:** Enabled search methods

**Type:** List of strings

**Default:** ["semantic", "fts", "graph"]

**Usage:**
```json
{
  "settings": {
    "search_methods": ["semantic", "fts"]
  }
}
```

### Graph Settings

#### auto_build_graph

**Description:** Automatically rebuild graph after N new memories

**Type:** Integer (0 = disabled)

**Default:** 0

**Usage:**
```json
{
  "settings": {
    "auto_build_graph": 50
  }
}
```

#### graph_min_similarity

**Description:** Minimum similarity for graph edges

**Type:** Float (0.0-1.0)

**Default:** 0.3

**Usage:**
```json
{
  "settings": {
    "graph_min_similarity": 0.4
  }
}
```

#### graph_max_edges_per_node

**Description:** Maximum edges per graph node

**Type:** Integer

**Default:** 50

**Usage:**
```json
{
  "settings": {
    "graph_max_edges_per_node": 30
  }
}
```

#### clustering_enabled

**Description:** Enable Leiden clustering by default

**Type:** Boolean

**Default:** false

**Usage:**
```json
{
  "settings": {
    "clustering_enabled": true
  }
}
```

#### clustering_resolution

**Description:** Leiden algorithm resolution parameter

**Type:** Float

**Default:** 1.0

**Usage:**
```json
{
  "settings": {
    "clustering_resolution": 1.5
  }
}
```

### Pattern Learning Settings

#### pattern_learning_enabled

**Description:** Enable pattern learning

**Type:** Boolean

**Default:** true

**Usage:**
```json
{
  "settings": {
    "pattern_learning_enabled": true
  }
}
```

#### pattern_learning_threshold

**Description:** Minimum confidence threshold for patterns

**Type:** Float (0.0-1.0)

**Default:** 0.5

**Usage:**
```json
{
  "settings": {
    "pattern_learning_threshold": 0.6
  }
}
```

#### pattern_min_frequency

**Description:** Minimum frequency to consider a pattern

**Type:** Integer

**Default:** 3

**Usage:**
```json
{
  "settings": {
    "pattern_min_frequency": 5
  }
}
```

### Compression Settings

#### compression_enabled

**Description:** Enable progressive compression (planned v2.2.0)

**Type:** Boolean

**Default:** false

**Usage:**
```json
{
  "settings": {
    "compression_enabled": true
  }
}
```

#### compression_age_threshold_days

**Description:** Days before compression eligible

**Type:** Integer

**Default:** 90

**Usage:**
```json
{
  "settings": {
    "compression_age_threshold_days": 180
  }
}
```

---

## Performance Tuning

### Optimize for Speed

**For fast search (<100ms):**
```json
{
  "settings": {
    "search_min_score": 0.5,
    "search_methods": ["fts", "semantic"],
    "graph_max_edges_per_node": 20
  }
}
```

**Environment:**
```bash
export SLM_CACHE_SIZE=100
export SLM_MAX_WORKERS=8
```

### Optimize for Memory Usage

**For low memory systems (<4GB RAM):**
```json
{
  "settings": {
    "graph_max_edges_per_node": 10,
    "clustering_enabled": false
  }
}
```

**Environment:**
```bash
export SLM_CACHE_SIZE=10
export SLM_MAX_WORKERS=2
export SLM_GRAPH_CHUNK_SIZE=500
```

### Optimize for Quality

**For best search quality:**
```json
{
  "settings": {
    "search_min_score": 0.3,
    "search_methods": ["semantic", "fts", "graph"],
    "graph_min_similarity": 0.2,
    "clustering_enabled": true,
    "pattern_learning_threshold": 0.4
  }
}
```

**Build graph regularly:**
```bash
# Cron job: daily at 3 AM
0 3 * * * slm build-graph --clustering
```

### Optimize for Large Databases (10K+ memories)

```json
{
  "settings": {
    "auto_build_graph": 0,
    "graph_min_similarity": 0.4,
    "graph_max_edges_per_node": 30,
    "search_default_limit": 20
  }
}
```

**Environment:**
```bash
export SLM_CACHE_SIZE=200
export SLM_MAX_WORKERS=8
export SLM_GRAPH_CHUNK_SIZE=2000
```

---

## Database Tuning

### SQLite Optimization

**Pragmas (applied automatically):**
```sql
PRAGMA journal_mode = WAL;           -- Write-Ahead Logging
PRAGMA synchronous = NORMAL;         -- Balance safety/speed
PRAGMA cache_size = -64000;          -- 64MB cache
PRAGMA temp_store = MEMORY;          -- In-memory temp tables
PRAGMA mmap_size = 268435456;        -- 256MB memory-mapped I/O
```

### Vacuum Database

**Reclaim space after deletions:**
```bash
sqlite3 ~/.claude-memory/memory.db "VACUUM;"
```

**Analyze statistics:**
```bash
sqlite3 ~/.claude-memory/memory.db "ANALYZE;"
```

### Rebuild Indexes

```bash
sqlite3 ~/.claude-memory/memory.db "REINDEX;"
```

---

## IDE-Specific Settings

### Cursor

**Config:** `~/.cursor/mcp_settings.json`

**Recommendations:**
```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "/opt/homebrew/bin/python3",
      "args": ["/Users/username/.claude-memory/mcp_server.py"],
      "cwd": "/Users/username/.claude-memory",
      "env": {
        "PYTHONPATH": "/Users/username/.claude-memory",
        "SLM_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Claude Desktop

**Config:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Recommendations:**
```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": ["/Users/username/.claude-memory/mcp_server.py"],
      "cwd": "/Users/username/.claude-memory",
      "env": {
        "PYTHONPATH": "/Users/username/.claude-memory"
      }
    }
  }
}
```

### VS Code (Continue.dev)

**Config:** Command Palette → "MCP: Open User Configuration"

**Recommendations:**
```json
{
  "servers": {
    "superlocalmemory-v2": {
      "type": "stdio",
      "command": "python3",
      "args": ["/Users/username/.claude-memory/mcp_server.py"]
    }
  }
}
```

---

## Shell Integration

### Bash Configuration

**Add to `~/.bashrc`:**
```bash
# SuperLocalMemory V2
export PATH="$HOME/.claude-memory/bin:$PATH"
export PYTHONPATH="$HOME/.claude-memory:$PYTHONPATH"

# Default profile
export SLM_PROFILE=default

# Performance tuning
export SLM_CACHE_SIZE=100

# Auto-complete
source ~/.claude-memory/completions/slm.bash

# Profile prompt
slm_prompt() {
  echo "SLM: $(slm status | grep 'Current Profile' | cut -d: -f2)"
}
export PS1="\$(slm_prompt) $PS1"
```

### Zsh Configuration

**Add to `~/.zshrc`:**
```zsh
# SuperLocalMemory V2
export PATH="$HOME/.claude-memory/bin:$PATH"
export PYTHONPATH="$HOME/.claude-memory:$PYTHONPATH"

# Auto-complete
source ~/.claude-memory/completions/slm.zsh

# Profile switching by directory
autoload -Uz add-zsh-hook
profile_switch() {
  case $PWD in
    */work/*) export SLM_PROFILE=work ;;
    */personal/*) export SLM_PROFILE=personal ;;
    *) export SLM_PROFILE=default ;;
  esac
}
add-zsh-hook chpwd profile_switch
```

---

## Backup Configuration

### Automated Backups

**Daily backup script:**
```bash
#!/bin/bash
# Save as: ~/bin/slm-backup.sh

BACKUP_DIR=~/backups/slm-$(date +%Y%m%d)
mkdir -p "$BACKUP_DIR"

# Backup all profiles
cp -r ~/.claude-memory/profiles/ "$BACKUP_DIR/"

# Backup config
cp ~/.claude-memory/config.json "$BACKUP_DIR/"

# Compress
tar czf "$BACKUP_DIR.tar.gz" -C ~/backups "$(basename $BACKUP_DIR)"
rm -rf "$BACKUP_DIR"

# Keep last 7 days
find ~/backups/ -name "slm-*.tar.gz" -mtime +7 -delete
```

**Cron job:**
```bash
# Daily at 2 AM
0 2 * * * ~/bin/slm-backup.sh
```

### Restore from Backup

```bash
# Extract backup
tar xzf ~/backups/slm-20260207.tar.gz -C ~/backups/

# Restore profiles
cp -r ~/backups/slm-20260207/profiles/* ~/.claude-memory/profiles/

# Restore config
cp ~/backups/slm-20260207/config.json ~/.claude-memory/

# Rebuild graphs
slm build-graph --force
```

---

## Security Configuration

### File Permissions

**Recommended permissions:**
```bash
# Directory
chmod 700 ~/.claude-memory/

# Databases
chmod 600 ~/.claude-memory/profiles/*/memory.db

# Scripts
chmod 700 ~/.claude-memory/*.py

# Config
chmod 600 ~/.claude-memory/config.json
```

### Network Security

**MCP server binds to localhost only:**
```python
# In mcp_server.py
server = Server(host="127.0.0.1", port=0)  # Localhost only
```

**No external connections:**
- Zero API calls
- No telemetry
- No cloud sync

---

## Troubleshooting

### "Config file not found"

**Solution:**
```bash
# Recreate default config
cd ~/path/to/SuperLocalMemoryV2
./install.sh
```

### "Invalid JSON in config"

**Solution:**
```bash
# Validate JSON
python3 -m json.tool ~/.claude-memory/config.json

# Fix syntax errors or restore from backup
cp ~/.claude-memory/config.json.backup ~/.claude-memory/config.json
```

### "Environment variable not working"

**Solution:**
```bash
# Verify variable is set
echo $SLM_PROFILE

# Restart shell
exec $SHELL

# Or source config
source ~/.bashrc  # or ~/.zshrc
```

---

## Related Pages

- [Quick Start Tutorial](Quick-Start-Tutorial) - First-time setup
- [CLI Cheatsheet](CLI-Cheatsheet) - Command reference
- [Multi-Profile Workflows](Multi-Profile-Workflows) - Profile management
- [Python API](Python-API) - Programmatic access
- [Why Local Matters](Why-Local-Matters) - Privacy benefits

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) • [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) • [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
