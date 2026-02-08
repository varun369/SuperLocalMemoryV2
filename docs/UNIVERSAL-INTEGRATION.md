# Universal Integration Guide

**Version:** 2.3.0-universal
**Status:** Production Ready
**Updated:** February 7, 2026

---

## Overview

SuperLocalMemory V2 now works across **16+ IDEs and CLI tools** with automatic detection and configuration. This guide shows you how to use it in every supported environment.

---

## Quick Start

### Step 1: Install
```bash
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2
./install.sh
```

The installer automatically:
- ✅ Detects your installed IDEs (Cursor, Windsurf, Claude Desktop, VS Code)
- ✅ Configures MCP servers where supported
- ✅ Sets up CLI tools and completions
- ✅ Configures skills for Continue.dev and Cody
- ✅ No manual configuration needed!

### Step 2: Restart Your Tools
After installation, restart any IDE you want to use SuperLocalMemory with.

### Step 3: Start Using It
- **In Cursor/Windsurf:** Just talk naturally - "Remember that we use FastAPI for APIs"
- **In Claude Code:** Use `/superlocalmemoryv2:remember` or the new `slm` commands
- **In Terminal:** Use `slm remember "content"`

---

## Integration by Tool

### Claude Code (Skills) ✅

**How It Works:** Native skills via `/` commands

**Setup:** Automatic during installation

**Usage:**
```
/superlocalmemoryv2:remember "Use FastAPI for REST APIs"
/superlocalmemoryv2:recall "FastAPI"
/superlocalmemoryv2:list
/superlocalmemoryv2:status
/superlocalmemoryv2:profile list
```

**OR use the simpler CLI:**
```bash
slm remember "Use FastAPI for REST APIs"
slm recall "FastAPI"
slm list
slm status
```

### Cursor IDE (MCP) ✅

**How It Works:** Native MCP integration - AI has direct tool access

**Setup:** Automatic detection and configuration

**Configuration File:** `~/.cursor/mcp_settings.json` (auto-created)

**Usage:**
```
User: "Remember that we prefer React hooks over class components"
AI: [calls remember() tool automatically]
✓ Memory saved

User: "What did we decide about React?"
AI: [calls recall() tool automatically]
✓ Returns: "We prefer React hooks over class components"
```

**Manual Configuration (if needed):**
```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": [
        "/Users/yourname/.claude-memory/mcp_server.py"
      ]
    }
  }
}
```

### Windsurf IDE (MCP) ✅

**How It Works:** Native MCP integration with stdio transport

**Setup:** Automatic detection and configuration

**Configuration File:** `~/.windsurf/mcp_settings.json` (auto-created)

**Usage:** Same as Cursor - AI automatically uses memory tools

**Manual Configuration (if needed):**
```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": ["/Users/yourname/.claude-memory/mcp_server.py"],
      "transport": "stdio"
    }
  }
}
```

### Claude Desktop (MCP) ✅

**How It Works:** Native MCP server support

**Setup:** Automatic configuration

**Configuration File:** `~/Library/Application Support/Claude/claude_desktop_config.json` (auto-created)

**Usage:** Natural conversation with AI having memory access

**Manual Configuration (if needed):**
```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": ["/Users/yourname/.claude-memory/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/yourname/.claude-memory"
      }
    }
  }
}
```

### VS Code + Continue.dev ✅

**How It Works:** Both MCP tools AND slash commands

**Setup:** Automatic configuration if Continue detected

**Configuration File:** `~/.continue/config.yaml`

**Usage (Slash Commands):**
```
/slm-remember Use pytest for all tests
/slm-recall pytest patterns
/slm-list
/slm-status
```

**Usage (MCP):**
Continue's AI can also call memory tools directly.

**Manual Configuration (if needed):**
```yaml
# For slash commands
slashCommands:
  - name: "slm-remember"
    description: "Save to SuperLocalMemory"
    run: "~/.claude-memory/bin/superlocalmemoryv2:remember \"{{input}}\""

# For MCP tools
contextProviders:
  - name: mcp
    params:
      serverName: "superlocalmemory-v2"
      command: "python3"
      args:
        - "/Users/yourname/.claude-memory/mcp_server.py"
```

### VS Code + Cody ✅

**How It Works:** Custom commands

**Setup:** Automatic configuration if Cody detected

**Configuration File:** `~/.vscode/settings.json`

**Usage:**
```
/slm-remember (with text selected)
/slm-recall search query
/slm-context (get project context)
```

**Manual Configuration (if needed):**
```json
{
  "cody.customCommands": {
    "slm-remember": {
      "description": "Save to SuperLocalMemory",
      "prompt": "Save this to SuperLocalMemory",
      "context": {
        "selection": true
      }
    }
  }
}
```

### Aider CLI ✅

**How It Works:** Smart wrapper with auto-context injection

**Setup:** `aider-smart` command installed automatically

**Usage:**
```bash
# Instead of: aider
# Use: aider-smart

aider-smart "Add authentication to the API"
```

**What It Does:**
1. Automatically gathers project context from SuperLocalMemory
2. Includes your coding patterns
3. Passes context to Aider
4. Aider gets relevant memories without you asking

### Any Terminal / Script ✅

**How It Works:** Universal CLI wrapper

**Commands Installed:**
- `slm` - Main command
- All original `superlocalmemoryv2:*` commands still work

**Usage:**
```bash
# Simple syntax
slm remember "Use PostgreSQL for this project"
slm recall "database decisions"
slm list
slm status
slm context  # Get context for current directory

# Profile management
slm profile list
slm profile create work
slm profile switch work

# Knowledge graph
slm graph build
slm graph stats

# Pattern learning
slm patterns update
slm patterns list 0.6
```

**Bash Completion:**
```bash
slm [TAB]  # Shows: remember, recall, list, status, context, profile, graph, patterns
slm profile [TAB]  # Shows: list, create, switch, delete, current
```

---

## Three-Tier Architecture

All access methods use the **SAME local SQLite database**:

```
┌─────────────────────────────────────────────┐
│            ACCESS METHODS                   │
├─────────────────────────────────────────────┤
│ TIER 1: Skills                              │
│  • Claude Code: /superlocalmemoryv2:*       │
│  • Continue: /slm-*                         │
│  • Cody: /slm-*                            │
├─────────────────────────────────────────────┤
│ TIER 2: MCP                                 │
│  • Cursor: AI tools                         │
│  • Windsurf: AI tools                       │
│  • Claude Desktop: AI tools                 │
│  • Continue: MCP providers                  │
├─────────────────────────────────────────────┤
│ TIER 3: CLI                                 │
│  • slm commands                             │
│  • aider-smart wrapper                      │
│  • Any script                              │
└────────────────┬────────────────────────────┘
                 │
                 ▼
         ┌───────────────────┐
         │ SuperLocalMemory   │
         │ Core (Unchanged)   │
         │ memory.db (SQLite) │
         └───────────────────┘
```

**Key Point:** No matter which method you use, all data goes to the same place. You can use `/superlocalmemoryv2:remember` in Claude Code, then `slm recall` in terminal, and see the same memories.

---

## Troubleshooting

### "MCP server won't start"

**Check MCP SDK:**
```bash
python3 -c "import mcp" && echo "OK" || echo "Not installed"
```

**Install if needed:**
```bash
pip3 install mcp
```

### "Skills not working in Claude Code"

**Run skills installer:**
```bash
./install-skills.sh
```

**Restart Claude Code after installation.**

### "Continue.dev doesn't have slash commands"

**Check config:**
```bash
cat ~/.continue/config.yaml
```

**Should contain `slm-remember`, `slm-recall`, etc.**

**Re-run installer if missing:**
```bash
./install-skills.sh
```

### "slm command not found"

**Check PATH:**
```bash
echo $PATH | grep claude-memory
```

**Add to PATH if missing:**
```bash
# Add to ~/.zshrc or ~/.bashrc
export PATH="${HOME}/.claude-memory/bin:${PATH}"

# Then reload
source ~/.zshrc  # or ~/.bashrc
```

### "Existing tools not detected during install"

**Install detects tools at installation time only.**

**If you install a new IDE after running install.sh:**
1. Run the installer again: `./install.sh`
2. It will detect and configure the new tool
3. Won't affect existing configurations

---

## Advanced: Manual MCP Server Testing

**Start MCP server manually:**
```bash
python3 ~/.claude-memory/mcp_server.py
```

**Start with HTTP transport:**
```bash
python3 ~/.claude-memory/mcp_server.py --transport http --port 8001
```

**Check MCP server tools:**
```bash
# Server outputs available tools on startup
# Look for: remember, recall, list_recent, get_status, build_graph, switch_profile
```

---

## Backward Compatibility

**100% backward compatible with v2.0.0:**

| Old Command | Still Works? | New Alternative |
|-------------|--------------|-----------------|
| `superlocalmemoryv2:remember` | ✅ Yes | `slm remember` |
| `superlocalmemoryv2:recall` | ✅ Yes | `slm recall` |
| `superlocalmemoryv2:list` | ✅ Yes | `slm list` |
| `superlocalmemoryv2:status` | ✅ Yes | `slm status` |
| `superlocalmemoryv2:profile` | ✅ Yes | `slm profile` |

**Nothing breaks. Everything gains new capabilities.**

---

## Supported Platforms

- ✅ macOS (tested on macOS 14+)
- ✅ Linux (tested on Ubuntu 22.04+)
- ✅ Windows via WSL2
- ✅ Windows PowerShell (use `install.ps1`)

---

## What's Next?

- **For most users:** Just use it! Works automatically after installation.
- **For advanced users:** See [MCP-INTEGRATION.md](./MCP-INTEGRATION.md) for deep dive
- **For CLI users:** See [CLI-UNIVERSAL.md](./CLI-UNIVERSAL.md) for all slm commands
- **For skill users:** See [SKILLS-EVERYWHERE.md](./SKILLS-EVERYWHERE.md) for multi-tool skills

---

**Questions?** Open an issue: https://github.com/varun369/SuperLocalMemoryV2/issues

**Version:** 2.3.0-universal
**Author:** Varun Pratap Bhardwaj
**License:** MIT
