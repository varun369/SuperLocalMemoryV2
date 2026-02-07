# SuperLocalMemory V2 - Manual MCP Setup Guide

This guide shows how to manually add SuperLocalMemory V2 as an MCP server in various applications and tools.

**Auto-Configuration:** If you installed using `./install.sh`, the following IDEs are already configured:
- ✅ Claude Desktop
- ✅ Cursor
- ✅ Windsurf
- ✅ Continue.dev (VS Code)

For all other tools, follow the manual setup instructions below.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Configuration Template](#configuration-template)
3. [IDE/App Specific Setup](#ideapp-specific-setup)
   - [Claude Desktop](#claude-desktop)
   - [Cursor](#cursor)
   - [Windsurf](#windsurf)
   - [Continue.dev (VS Code)](#continuedev-vs-code)
   - [Cody (VS Code/JetBrains)](#cody-vs-codejetbrains)
   - [ChatGPT Desktop App](#chatgpt-desktop-app)
   - [Perplexity](#perplexity)
   - [Zed Editor](#zed-editor)
   - [Custom MCP Clients](#custom-mcp-clients)
4. [Troubleshooting](#troubleshooting)
5. [Verification](#verification)

---

## Prerequisites

1. **SuperLocalMemory V2 installed:**
   ```bash
   ./install.sh
   ```

2. **MCP Python package installed:**
   ```bash
   pip3 install mcp
   ```

3. **Know your Python path:**
   ```bash
   which python3
   # Output: /usr/bin/python3 or /opt/homebrew/bin/python3 or similar
   ```

4. **Know your install directory:**
   ```bash
   echo ~/.claude-memory
   # Default: /Users/yourusername/.claude-memory
   ```

---

## Configuration Template

This is the base MCP configuration that works across all tools:

```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": [
        "/Users/yourusername/.claude-memory/mcp_server.py"
      ],
      "cwd": "/Users/yourusername/.claude-memory",
      "env": {
        "PYTHONPATH": "/Users/yourusername/.claude-memory"
      },
      "description": "SuperLocalMemory V2 - 100% local memory system"
    }
  }
}
```

**Replace `/Users/yourusername/.claude-memory` with your actual install path.**

---

## IDE/App Specific Setup

### Claude Desktop

**Configuration File:** `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
**Configuration File:** `%APPDATA%\Claude\claude_desktop_config.json` (Windows)
**Configuration File:** `~/.config/Claude/claude_desktop_config.json` (Linux)

**Steps:**

1. Open Claude Desktop settings or directly edit the config file
2. Add the MCP server configuration:

```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": [
        "/Users/yourusername/.claude-memory/mcp_server.py"
      ],
      "cwd": "/Users/yourusername/.claude-memory",
      "env": {
        "PYTHONPATH": "/Users/yourusername/.claude-memory"
      },
      "description": "SuperLocalMemory V2 - Local memory system"
    }
  }
}
```

3. **Restart Claude Desktop completely**
4. Verify: Look for "superlocalmemory-v2" in available tools

**Auto-configured by install.sh:** ✅ Yes

---

### Cursor

**Configuration File:** `~/.cursor/mcp_settings.json` (macOS/Linux)
**Configuration File:** `%USERPROFILE%\.cursor\mcp_settings.json` (Windows)

**Steps:**

1. Create or edit `~/.cursor/mcp_settings.json`:

```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": [
        "/Users/yourusername/.claude-memory/mcp_server.py"
      ],
      "cwd": "/Users/yourusername/.claude-memory",
      "env": {
        "PYTHONPATH": "/Users/yourusername/.claude-memory"
      },
      "description": "SuperLocalMemory V2"
    }
  }
}
```

2. **Completely quit Cursor (Cmd+Q on macOS)** and reopen
3. Go to Settings → Tools & MCP
4. Verify "superlocalmemory-v2" shows with green indicator

**Auto-configured by install.sh:** ✅ Yes

---

### Windsurf

**Configuration File:** `~/.windsurf/mcp_settings.json` (macOS/Linux)
**Configuration File:** `%USERPROFILE%\.windsurf\mcp_settings.json` (Windows)

**Steps:**

1. Create or edit `~/.windsurf/mcp_settings.json`:

```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": [
        "/Users/yourusername/.claude-memory/mcp_server.py"
      ],
      "cwd": "/Users/yourusername/.claude-memory",
      "env": {
        "PYTHONPATH": "/Users/yourusername/.claude-memory"
      },
      "transport": "stdio",
      "description": "SuperLocalMemory V2"
    }
  }
}
```

2. Restart Windsurf
3. Check MCP servers in settings

**Auto-configured by install.sh:** ✅ Yes

---

### Continue.dev (VS Code)

**Configuration File:** `~/.continue/config.yaml` (macOS/Linux)
**Configuration File:** `%USERPROFILE%\.continue\config.yaml` (Windows)

**Steps:**

1. Open VS Code → Continue extension settings
2. Or edit `~/.continue/config.yaml` directly:

```yaml
mcpServers:
  - name: superlocalmemory-v2
    command: python3
    args:
      - /Users/yourusername/.claude-memory/mcp_server.py
    cwd: /Users/yourusername/.claude-memory
    env:
      PYTHONPATH: /Users/yourusername/.claude-memory
    description: SuperLocalMemory V2 - Local memory system
```

3. Reload VS Code window (Cmd+Shift+P → Reload Window)
4. Verify in Continue extension panel

**Auto-configured by install.sh:** ✅ Partial (manual merge if config exists)

---

### Cody (VS Code/JetBrains)

**Configuration:** Via VS Code settings or IDE settings

**Steps:**

1. Open VS Code → Settings → Extensions → Cody
2. Look for "MCP Servers" or "External Tools" section
3. Add server configuration:

```json
{
  "cody.mcpServers": [
    {
      "name": "superlocalmemory-v2",
      "command": "python3",
      "args": ["/Users/yourusername/.claude-memory/mcp_server.py"],
      "cwd": "/Users/yourusername/.claude-memory",
      "env": {
        "PYTHONPATH": "/Users/yourusername/.claude-memory"
      }
    }
  ]
}
```

4. Restart VS Code
5. Check Cody status bar for connected MCP servers

**Auto-configured by install.sh:** ❌ No (manual setup required)

---

### ChatGPT Desktop App

**Note:** As of February 2026, ChatGPT Desktop supports MCP in beta.

**Steps:**

1. Open ChatGPT Desktop app
2. Go to **Settings → Advanced → Model Context Protocol**
3. Click **"Add MCP Server"**
4. Enter details:
   - **Name:** `SuperLocalMemory V2`
   - **Command:** `python3`
   - **Arguments:** `/Users/yourusername/.claude-memory/mcp_server.py`
   - **Working Directory:** `/Users/yourusername/.claude-memory`
   - **Environment Variables:** `PYTHONPATH=/Users/yourusername/.claude-memory`

5. Click **Save**
6. Restart ChatGPT app
7. In a new chat, look for MCP tools in the tool selector

**Auto-configured by install.sh:** ❌ No (manual setup via GUI)

---

### Perplexity

**Note:** Perplexity AI may support MCP integration via their developer settings.

**Steps:**

1. Open Perplexity app
2. Go to **Settings → Integrations** or **Settings → Developer**
3. Look for **"Custom MCP Servers"** or **"External Tools"**
4. Add configuration:

```json
{
  "name": "SuperLocalMemory V2",
  "command": "python3",
  "args": ["/Users/yourusername/.claude-memory/mcp_server.py"],
  "cwd": "/Users/yourusername/.claude-memory",
  "env": {
    "PYTHONPATH": "/Users/yourusername/.claude-memory"
  }
}
```

5. Save and restart Perplexity
6. Check if MCP tools appear in conversation context

**Auto-configured by install.sh:** ❌ No (manual setup via app settings)

**Note:** MCP support in Perplexity may vary by version. Check their documentation.

---

### Zed Editor

**Configuration File:** `~/.config/zed/settings.json`

**Steps:**

1. Open Zed → Settings (Cmd+,)
2. Click "Open Settings File" (JSON editor)
3. Add MCP server configuration:

```json
{
  "assistant": {
    "mcpServers": {
      "superlocalmemory-v2": {
        "command": "python3",
        "args": ["/Users/yourusername/.claude-memory/mcp_server.py"],
        "cwd": "/Users/yourusername/.claude-memory",
        "env": {
          "PYTHONPATH": "/Users/yourusername/.claude-memory"
        }
      }
    }
  }
}
```

4. Save settings (Cmd+S)
5. Restart Zed
6. Check assistant panel for available MCP tools

**Auto-configured by install.sh:** ❌ No (manual setup required)

---

### Custom MCP Clients

If you're building your own MCP client or integrating with a custom tool:

**Python Example:**

```python
from mcp import Client

client = Client()
client.add_server(
    name="superlocalmemory-v2",
    command="python3",
    args=["/Users/yourusername/.claude-memory/mcp_server.py"],
    cwd="/Users/yourusername/.claude-memory",
    env={"PYTHONPATH": "/Users/yourusername/.claude-memory"}
)

# Use the MCP server
response = client.call_tool("remember", {"content": "Test memory"})
print(response)
```

**HTTP Transport (for remote access):**

Start MCP server in HTTP mode:
```bash
python3 ~/.claude-memory/mcp_server.py --transport http --port 8001
```

Then connect via HTTP:
```
http://localhost:8001
```

---

## Troubleshooting

### Issue 1: "MCP server not found"

**Solution:**
1. Verify file exists:
   ```bash
   ls -la ~/.claude-memory/mcp_server.py
   ```
2. Check permissions:
   ```bash
   chmod +x ~/.claude-memory/mcp_server.py
   ```

### Issue 2: "ModuleNotFoundError: No module named 'mcp'"

**Solution:**
```bash
pip3 install mcp
# Or if using conda:
conda install -c conda-forge mcp
```

### Issue 3: "Python not found"

**Solution:**
1. Check Python installation:
   ```bash
   which python3
   ```
2. Use full Python path in config:
   ```json
   "command": "/usr/bin/python3"
   ```

### Issue 4: "Cannot import SuperLocalMemory modules"

**Solution:**
1. Verify `cwd` and `PYTHONPATH` are set in config
2. Check modules exist:
   ```bash
   ls ~/.claude-memory/memory_store_v2.py
   ```

### Issue 5: IDE doesn't show MCP tools

**Solution:**
1. **Completely restart the IDE** (not just reload)
2. Check IDE's MCP settings/logs
3. Test MCP server manually:
   ```bash
   python3 ~/.claude-memory/mcp_server.py
   # Should start without errors
   ```

### Issue 6: "Config file is overwritten"

**Solution:**
- install.sh creates backups: `mcp_settings.json.backup.YYYYMMDD-HHMMSS`
- Restore if needed:
  ```bash
  cp ~/.cursor/mcp_settings.json.backup.* ~/.cursor/mcp_settings.json
  ```

---

## Verification

After setup, verify MCP integration works:

### 1. Check MCP Server Status

```bash
python3 ~/.claude-memory/mcp_server.py
```

**Expected output:**
```
============================================================
SuperLocalMemory V2 - MCP Server
Version: 2.1.0-universal
============================================================

Transport: stdio
Database: /Users/yourusername/.claude-memory/memory.db

MCP Tools Available:
  - remember(content, tags, project, importance)
  - recall(query, limit, min_score)
  - list_recent(limit)
  - get_status()
  - build_graph()
  - switch_profile(name)

...
```

### 2. Test in Your IDE/App

Try these natural language commands:

**Save a memory:**
```
Remember that SuperLocalMemory V2 MCP integration works perfectly
```

**Search memories:**
```
What do we know about MCP integration?
```

**Check status:**
```
What's the status of my memory system?
```

### 3. Verify Tools are Visible

In your IDE/app, check:
- **Cursor:** Settings → Tools & MCP → Should show "superlocalmemory-v2" (green)
- **Claude Desktop:** Tools menu → Should list SuperLocalMemory tools
- **Continue.dev:** Extension panel → MCP servers section
- **ChatGPT:** Tool selector in chat → Look for memory tools

---

## Available MCP Tools

Once configured, these 6 tools are available:

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `remember()` | Save memories | "Remember we use React hooks" |
| `recall()` | Search memories | "What did we decide about authentication?" |
| `list_recent()` | Recent memories | "Show me recent discussions" |
| `get_status()` | System health | "How many memories do I have?" |
| `build_graph()` | Build knowledge graph | "Build the knowledge graph" |
| `switch_profile()` | Change profile | "Switch to work profile" |

Plus **2 MCP prompts** and **4 MCP resources** for advanced use.

---

## Need Help?

1. **Check logs:** Most IDEs have MCP server logs in their developer tools
2. **Test manually:** Run `python3 ~/.claude-memory/mcp_server.py` to see errors
3. **GitHub Issues:** https://github.com/varun369/SuperLocalMemoryV2/issues
4. **Documentation:** https://github.com/varun369/SuperLocalMemoryV2

---

**100% local. 100% private. Works everywhere.**

SuperLocalMemory V2 - by Varun Pratap Bhardwaj
Licensed under MIT License
