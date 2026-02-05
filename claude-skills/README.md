# Claude CLI Skills for SuperLocalMemory V2

**Optional convenience wrappers for Claude CLI users**

This directory contains Claude CLI skill definitions that provide convenient slash commands for SuperLocalMemory V2 operations. These skills are **completely optional** - SuperLocalMemory V2 works perfectly as a standalone system via terminal commands.

## What Are These Skills?

Skills are shortcuts that let you use SuperLocalMemory V2 directly from Claude CLI conversations using simple slash commands like `/superlocalmemoryv2:remember` instead of typing full terminal commands.

## Available Skills

### Core Memory Operations

| Skill | Command | Description |
|-------|---------|-------------|
| **remember** | `/superlocalmemoryv2:remember <text> [--tags] [--project]` | Add memory with semantic indexing |
| **recall** | `/superlocalmemoryv2:recall <query> [--limit]` | Search using semantic similarity |
| **list** | `/superlocalmemoryv2:list [--limit] [--sort]` | List recent memories with sorting |

### System Management

| Skill | Command | Description |
|-------|---------|-------------|
| **status** | `/superlocalmemoryv2:status` | System status and statistics |
| **reset** | `/superlocalmemoryv2:reset <cmd> [options]` | Reset operations (with safety) |
| **profile** | `/superlocalmemoryv2:profile <cmd> [name]` | Multi-profile management |

### Advanced Features (Legacy)

| Skill | Command | Description |
|-------|---------|-------------|
| **search** | `/superlocalmemoryv2:search <query>` | Full-text search (legacy) |
| **graph-build** | `/superlocalmemoryv2:graph-build` | Build/rebuild knowledge graph |
| **graph-stats** | `/superlocalmemoryv2:graph-stats` | View graph statistics and clusters |
| **patterns** | `/superlocalmemoryv2:patterns [cmd] [threshold]` | Learn and view coding patterns |

## Installation

### Quick Install (Recommended)

```bash
cd /path/to/SuperLocalMemoryV2-repo
./install-skills.sh
```

Then restart Claude CLI to load the new skills.

### Manual Installation

#### Option 1: Symlink (Recommended for Development)

```bash
# Create symlinks (changes in repo reflect immediately)
mkdir -p ~/.claude/skills
ln -sf "$(pwd)/claude-skills/"*.md ~/.claude/skills/
```

#### Option 2: Copy Files

```bash
# Copy files (stable, but requires manual updates)
mkdir -p ~/.claude/skills
cp claude-skills/*.md ~/.claude/skills/
```

### Verify Installation

After restarting Claude CLI, type `/super` and press TAB. You should see autocomplete for:

**Core Skills:**
- `superlocalmemoryv2:remember` - Save memories
- `superlocalmemoryv2:recall` - Search memories
- `superlocalmemoryv2:list` - List memories
- `superlocalmemoryv2:status` - System status
- `superlocalmemoryv2:reset` - Reset operations
- `superlocalmemoryv2:profile` - Profile management

**Advanced Skills:**
- `superlocalmemoryv2:search` - Full-text search
- `superlocalmemoryv2:graph-build` - Build knowledge graph
- `superlocalmemoryv2:graph-stats` - Graph statistics
- `superlocalmemoryv2:patterns` - Pattern learning

## Prerequisites

These skills require:
1. **SuperLocalMemory V2 installed** at `~/.claude-memory/`
2. **Claude CLI** installed and running
3. **Python 3.8+** available in PATH

If you haven't installed SuperLocalMemory V2 yet, see [INSTALL.md](../INSTALL.md).

## Usage Examples

### Core Memory Operations

**Save a memory:**
```
/superlocalmemoryv2:remember "Implemented JWT authentication for API" --tags auth,security,api
```

**Search memories:**
```
/superlocalmemoryv2:recall "authentication patterns"
/superlocalmemoryv2:recall "API design" --limit 5
```

**List recent memories:**
```
/superlocalmemoryv2:list
/superlocalmemoryv2:list --limit 10 --sort importance
```

### System Management

**Check system status:**
```
/superlocalmemoryv2:status
```

**Reset operations:**
```
/superlocalmemoryv2:reset status           # Safe: check current state
/superlocalmemoryv2:reset soft             # Clear memories, keep schema
/superlocalmemoryv2:reset hard --confirm   # Nuclear option
```

**Profile management:**
```
/superlocalmemoryv2:profile list
/superlocalmemoryv2:profile create work
/superlocalmemoryv2:profile switch work
```

### Advanced Features

**Build knowledge graph:**
```
/superlocalmemoryv2:graph-build
```

**View graph statistics:**
```
/superlocalmemoryv2:graph-stats
```

**Pattern learning:**
```
/superlocalmemoryv2:patterns update
/superlocalmemoryv2:patterns list 0.1
```

## Standalone Alternative

**Don't use Claude CLI?** No problem! SuperLocalMemory V2 works perfectly as a standalone system:

```bash
# Add memory
cd ~/.claude-memory
python3 memory_store_v2.py add "Your memory text" --tags tag1,tag2

# Search
python3 memory_store_v2.py search "query"

# Build graph
python3 graph_engine.py build

# View stats
python3 graph_engine.py stats

# Pattern learning
python3 pattern_learner.py update
python3 pattern_learner.py list 0.1

# System status
memory-status
```

## Troubleshooting

### Skills Not Showing Up

```bash
# Verify skills directory
ls -la ~/.claude/skills/superlocalmemoryv2-*.md

# Restart Claude CLI
# Skills are loaded at startup
```

### Permission Denied

```bash
# Make sure files are readable
chmod 644 ~/.claude/skills/superlocalmemoryv2-*.md
```

### Command Not Found Errors

Skills run terminal commands. If you get "command not found":

1. **Verify SuperLocalMemory V2 installation:**
   ```bash
   ls -la ~/.claude-memory/memory_store_v2.py
   ```

2. **Check Python availability:**
   ```bash
   which python3
   python3 --version  # Should be 3.8+
   ```

3. **Verify PATH includes bin directory:**
   ```bash
   echo $PATH | grep ".claude-memory/bin"
   ```

## Uninstallation

### Remove Skills Only

```bash
# Remove symlinks or files
rm ~/.claude/skills/superlocalmemoryv2-*.md
```

Then restart Claude CLI.

**Note:** This only removes Claude CLI integration. SuperLocalMemory V2 itself remains installed and functional.

### Remove Everything

To remove both skills and SuperLocalMemory V2, see [INSTALL.md](../INSTALL.md) uninstallation section.

## Integration Philosophy

These skills are **thin wrappers** around SuperLocalMemory V2's terminal commands:
- No additional logic or complexity
- Direct pass-through to underlying system
- Works identically to terminal usage
- Maintained in sync with core system

**Principle:** Skills add convenience, not dependency. SuperLocalMemory V2 remains a standalone system.

## Contributing

When adding new skills:
1. Follow the naming convention: `superlocalmemoryv2-<skillname>.md`
2. Keep skills simple and focused
3. Document prerequisites clearly
4. Test both symlink and copy installation methods
5. Verify commands work in both skill and terminal modes

## Support

For issues with:
- **Skills installation/usage**: Check this README
- **SuperLocalMemory V2 functionality**: See main [README.md](../README.md) and [docs/](../docs/)
- **Claude CLI issues**: Refer to Claude CLI documentation

## License

Same as SuperLocalMemory V2: MIT License

---

**Remember:** Claude CLI integration is optional. SuperLocalMemory V2 is a fully standalone system that works with any AI assistant, terminal workflow, or automation script.
