# SuperLocalMemory V2 - Manual MCP Setup Guide

This guide shows how to manually add SuperLocalMemory V2 as an MCP server in various applications and tools.

**Auto-configured by install.sh / npm install:**
- ✅ Claude Desktop, Cursor, Windsurf, Continue.dev
- ✅ OpenAI Codex CLI, VS Code/Copilot, Zed, OpenCode
- ✅ Antigravity, Perplexity, Gemini CLI
- ⚠️ ChatGPT (HTTP transport — run `slm serve`, see below)
- ⚠️ JetBrains (manual GUI setup — see below)
- ⚠️ Cody (manual setup — see below)

For tools marked ⚠️, follow the manual setup instructions below.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Configuration Template](#configuration-template)
3. [IDE/App Specific Setup](#ideapp-specific-setup)
   - [Claude Desktop](#claude-desktop)
   - [Cursor](#cursor)
   - [Windsurf](#windsurf)
   - [Continue.dev (VS Code)](#continuedev-vs-code)
   - [OpenAI Codex CLI](#openai-codex-cli)
   - [VS Code / GitHub Copilot](#vs-code--github-copilot)
   - [Gemini CLI](#gemini-cli)
   - [JetBrains IDEs](#jetbrains-ides)
   - [Cody (VS Code/JetBrains)](#cody-vs-codejetbrains)
   - [ChatGPT Desktop App](#chatgpt-desktop-app)
   - [Perplexity](#perplexity)
   - [Zed Editor](#zed-editor)
   - [HTTP Transport (Remote Access)](#http-transport-remote-access)
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

### OpenAI Codex CLI

**Configuration File:** `~/.codex/config.toml`
**Format:** TOML (not JSON)

**Method 1 — CLI command (preferred):**

```bash
codex mcp add superlocalmemory-v2 \
  --env "PYTHONPATH=/Users/yourusername/.claude-memory" \
  -- python3 /Users/yourusername/.claude-memory/mcp_server.py
```

**Method 2 — Manual TOML config:**

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.superlocalmemory-v2]
command = "python3"
args = ["/Users/yourusername/.claude-memory/mcp_server.py"]

[mcp_servers.superlocalmemory-v2.env]
PYTHONPATH = "/Users/yourusername/.claude-memory"
```

**Verify:** `codex mcp list` should show `superlocalmemory-v2`

**Auto-configured by install.sh:** ✅ Yes

---

### VS Code / GitHub Copilot

**Configuration File:** `~/.vscode/mcp.json` (user-level) or `.vscode/mcp.json` (workspace-level)

**Important:** VS Code uses `"servers"` (not `"mcpServers"`) and requires `"type": "stdio"`.

**Steps:**

1. Create or edit `~/.vscode/mcp.json`:

```json
{
  "servers": {
    "superlocalmemory-v2": {
      "type": "stdio",
      "command": "python3",
      "args": ["/Users/yourusername/.claude-memory/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/yourusername/.claude-memory"
      }
    }
  }
}
```

2. Restart VS Code
3. Copilot Chat should now have access to SuperLocalMemory tools

**Auto-configured by install.sh:** ✅ Yes

---

### Gemini CLI

**Configuration File:** `~/.gemini/settings.json`

**Steps:**

1. Create or edit `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": ["/Users/yourusername/.claude-memory/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/yourusername/.claude-memory"
      }
    }
  }
}
```

2. Restart Gemini CLI
3. Memory tools will be available in conversations

**Auto-configured by install.sh:** ✅ Yes

---

### JetBrains IDEs

**Supported:** IntelliJ IDEA, PyCharm, WebStorm, GoLand, and all JetBrains IDEs with AI Assistant (2025.2+)

**Steps (GUI-based):**

1. Open your JetBrains IDE
2. Go to **Settings → AI Assistant → MCP Servers**
3. Click **"+"** to add a new server
4. Enter:
   - **Name:** `superlocalmemory-v2`
   - **Command:** `python3`
   - **Arguments:** `/Users/yourusername/.claude-memory/mcp_server.py`
   - **Working Directory:** `/Users/yourusername/.claude-memory`
   - **Environment Variables:** `PYTHONPATH=/Users/yourusername/.claude-memory`
5. Click **OK** and restart

**JSON template** (for reference): See `configs/jetbrains-mcp.json`

```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": ["/Users/yourusername/.claude-memory/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/yourusername/.claude-memory"
      }
    }
  }
}
```

**Auto-configured by install.sh:** ❌ No (manual GUI setup required)

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

### ChatGPT Desktop App / ChatGPT Connectors

**Important:** ChatGPT requires HTTP transport, not stdio. You need to run a local HTTP server and expose it via a tunnel. As of v2.3.5, SuperLocalMemory includes `search(query)` and `fetch(id)` MCP tools required by OpenAI's MCP spec for ChatGPT Connectors and Deep Research.

**Requirements:**
- ChatGPT Plus, Team, or Enterprise plan
- **Developer Mode** must be enabled in ChatGPT settings
- A tunnel tool: `cloudflared` (recommended, free) or `ngrok`
- Reference: https://platform.openai.com/docs/mcp

**Available Tools in ChatGPT:**

| Tool | Purpose |
|------|---------|
| `search(query)` | Search memories (required by OpenAI MCP spec) |
| `fetch(id)` | Fetch a specific memory by ID (required by OpenAI MCP spec) |
| `remember(content, tags, project)` | Save a new memory |
| `recall(query, limit)` | Search memories with full options |

**Step-by-Step Setup:**

1. **Start the MCP HTTP server:**
   ```bash
   slm serve --port 8417
   # or with streamable-http transport (ChatGPT 2026+):
   slm serve --port 8417 --transport streamable-http
   # or using Python directly:
   python3 ~/.claude-memory/mcp_server.py --transport http --port 8417
   ```

2. **Expose via cloudflared tunnel** (in another terminal):
   ```bash
   # Install cloudflared (if not installed)
   # macOS: brew install cloudflared
   # Linux: sudo apt install cloudflared

   cloudflared tunnel --url http://localhost:8417
   ```
   Cloudflared will output a URL like `https://random-name.trycloudflare.com`

   **Alternative — ngrok:**
   ```bash
   ngrok http 8417
   ```

3. **Copy the HTTPS URL** from cloudflared/ngrok output

4. **Add to ChatGPT as a Connector:**
   - Open ChatGPT (desktop or web)
   - Go to **Settings → Connectors** (or **Settings → Apps & Connectors → Developer Mode**)
   - Click **"Add Connector"**
   - Paste the HTTPS URL with the `/sse/` suffix:
     ```
     https://random-name.trycloudflare.com/sse/
     ```
   - Name it: `SuperLocalMemory`
   - Click **Save**

5. **Verify in a new chat:**
   - Start a new conversation in ChatGPT
   - Look for the SuperLocalMemory connector in the tool selector
   - Try: "Search my memories for authentication decisions"
   - ChatGPT will call `search()` and return your local memories

**Important Notes:**
- The `/sse/` suffix on the URL is **required** by ChatGPT's MCP implementation
- 100% local — your MCP server runs on YOUR machine. The tunnel just makes it reachable by ChatGPT. Your data is served on demand and never stored by OpenAI beyond the conversation.
- The tunnel URL changes each time you restart cloudflared (unless you set up a named tunnel)
- For persistent URLs, configure a cloudflared named tunnel: `cloudflared tunnel create slm`

**Auto-configured by install.sh:** ❌ No (requires HTTP transport + tunnel)

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

### HTTP Transport (Remote Access)

For any MCP client that requires HTTP transport (ChatGPT, remote access, web-based tools):

**Start the HTTP server:**

```bash
# Using CLI wrapper
slm serve --port 8001

# Using Python directly
python3 ~/.claude-memory/mcp_server.py --transport http --port 8001
```

**For local access:**
```
http://localhost:8001
```

**For remote access (ChatGPT, etc.):**

```bash
# Option 1: ngrok (free tier available)
ngrok http 8001

# Option 2: Cloudflare Tunnel (free)
cloudflared tunnel --url http://localhost:8001
```

Then use the HTTPS URL from the tunnel in your MCP client.

**Security note:** The server binds to localhost only. The tunnel is the only way external services can reach it. Your data never leaves your machine — it's served on demand.

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
Version: 2.3.0-universal
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

Once configured, these 8 tools are available:

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| `remember()` | Save memories | "Remember we use React hooks" |
| `recall()` | Search memories | "What did we decide about authentication?" |
| `list_recent()` | Recent memories | "Show me recent discussions" |
| `get_status()` | System health | "How many memories do I have?" |
| `build_graph()` | Build knowledge graph | "Build the knowledge graph" |
| `switch_profile()` | Change profile | "Switch to work profile" |
| `search()` | Search memories (OpenAI MCP spec) | Used by ChatGPT Connectors and Deep Research |
| `fetch()` | Fetch memory by ID (OpenAI MCP spec) | Used by ChatGPT Connectors and Deep Research |

**Note:** `search()` and `fetch()` are required by OpenAI's MCP specification for ChatGPT Connectors. They are available in all transports but primarily used by ChatGPT.

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
