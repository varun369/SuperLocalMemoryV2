# MCP Integration

SuperLocalMemory V2.1.0 includes a universal **mcp-server** that provides native integration with 16+ IDEs including Claude Desktop, Cursor IDE, Windsurf, and more. This local-first, mcp-protocol based integration enables AI assistants to naturally access your memory system without manual commands.

**Keywords:** mcp-server, claude-desktop, cursor-ide, windsurf, universal-integration, model-context-protocol

---

## 🌐 What is MCP?

**MCP (Model Context Protocol)** is Anthropic's open protocol that allows AI assistants to connect to external tools and data sources. SuperLocalMemory's MCP server provides:

- **6 Tools** - AI-accessible functions (remember, recall, status, etc.)
- **4 Resources** - Data feeds (graph, patterns, recent memories)
- **2 Prompts** - Context injection templates
- **100% Local** - No cloud dependencies, runs entirely on your machine

### Why MCP Matters

With MCP, you can say:
```
You: "Remember that we use FastAPI for all REST APIs"
Claude: [Automatically uses the remember tool] ✓ Saved to memory
```

No slash commands needed. The AI assistant naturally uses your memory system.

### How MCP Works in Practice

SuperLocalMemory runs an MCP server locally on your machine. When you open Claude Desktop, Cursor, or any supported IDE, it automatically connects to this server. Every time you ask your AI assistant to remember something or search your memory, it's making a direct local call — no cloud, no delays, complete privacy.

![MCP Protocol Diagram](../assets/screenshots/v25/v25-agents-tab.png)
*Figure: MCP client connected to SuperLocalMemory, showing protocol and trust score*

---

## 🚀 Supported IDEs

### Auto-Configured During Installation

These IDEs are **automatically detected and configured** when you run `./install.sh`:

| IDE | Config File | Status |
|-----|-------------|--------|
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` | ✅ Auto |
| **Cursor** | `~/.cursor/mcp_settings.json` | ✅ Auto |
| **Windsurf** | `~/.windsurf/mcp_settings.json` | ✅ Auto |
| **Continue.dev** | `.continue/config.yaml` | ✅ Auto |

### Manual Setup Required

These IDEs require manual configuration (see detailed steps below):

| IDE | Manual Setup | Documentation |
|-----|--------------|---------------|
| **ChatGPT Desktop** | Settings → MCP | [Setup Guide](#chatgpt-desktop) |
| **Perplexity AI** | App Settings | [Setup Guide](#perplexity-ai) |
| **Zed Editor** | JSON config | [Setup Guide](#zed-editor) |
| **OpenCode** | MCP config | [Setup Guide](#opencode) |
| **Antigravity IDE** | Settings | [Setup Guide](#antigravity-ide) |
| **Cody** | Custom commands | [Setup Guide](#cody) |
| **Aider** | Smart wrapper | [Setup Guide](#aider) |

**Total: 16+ supported tools**

---

## ⚡ Quick Start (Auto-Installation)

### Step 1: Install SuperLocalMemory

```bash
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2
./install.sh
```

The installer will:
1. Detect installed IDEs (Cursor, Windsurf, Claude Desktop, Continue)
2. Install MCP Python package if not present
3. Create MCP configuration files automatically
4. Configure each detected IDE

### Step 2: Verify Installation

**Claude Desktop:**
1. Restart Claude Desktop completely
2. Look for "superlocalmemory-v2" in available tools
3. Test: "Save this to memory: Test memory"

**Cursor:**
1. Restart Cursor IDE
2. Open AI assistant panel
3. Test: "Remember that we prefer TypeScript"

**Windsurf:**
1. Restart Windsurf
2. Check MCP tools list
3. Test: "What's in my recent memories?"

**Continue.dev:**
1. Reload VS Code window (Cmd+Shift+P → "Reload Window")
2. Open Continue panel
3. Test: Type `/slm-remember` to see the skill

---

## 🛠️ Manual Setup Guides

### ChatGPT Desktop

**Platform:** macOS, Windows

**Steps:**

1. Open ChatGPT Desktop App
2. Go to **Settings** → **MCP Servers**
3. Click **Add Server**
4. Enter configuration:

```json
{
  "name": "superlocalmemory-v2",
  "command": "python3",
  "args": [
    "/Users/yourusername/.claude-memory/mcp_server.py"
  ],
  "cwd": "/Users/yourusername/.claude-memory",
  "env": {
    "PYTHONPATH": "/Users/yourusername/.claude-memory"
  }
}
```

5. Replace `/Users/yourusername` with your actual home directory
6. Click **Save** and restart ChatGPT

**Verify:** Ask ChatGPT "What tools do you have access to?" - should see SuperLocalMemory tools.

---

### Perplexity AI

**Platform:** macOS, Web

**Steps:**

1. Open Perplexity App
2. Navigate to **Settings** → **Integrations** → **MCP**
3. Click **Add MCP Server**
4. Paste configuration:

```json
{
  "superlocalmemory-v2": {
    "command": "python3",
    "args": [
      "/Users/yourusername/.claude-memory/mcp_server.py"
    ],
    "cwd": "/Users/yourusername/.claude-memory"
  }
}
```

5. Save and restart Perplexity

**Verify:** Ask "Do you have memory tools?" - should list SuperLocalMemory.

---

### Zed Editor

**Platform:** macOS, Linux

**Config File:** `~/.config/zed/settings.json`

**Steps:**

1. Open `~/.config/zed/settings.json` in a text editor
2. Add MCP configuration:

```json
{
  "mcp": {
    "servers": {
      "superlocalmemory-v2": {
        "command": "python3",
        "args": [
          "/Users/yourusername/.claude-memory/mcp_server.py"
        ],
        "cwd": "/Users/yourusername/.claude-memory",
        "env": {
          "PYTHONPATH": "/Users/yourusername/.claude-memory"
        }
      }
    }
  }
}
```

3. Save and restart Zed
4. Open AI assistant panel

**Verify:** Check available tools in Zed's AI panel.

---

### OpenCode

**Platform:** Cross-platform

**Config File:** `~/.opencode/mcp.json`

**Steps:**

1. Create or edit `~/.opencode/mcp.json`:

```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": [
        "/Users/yourusername/.claude-memory/mcp_server.py"
      ],
      "cwd": "/Users/yourusername/.claude-memory"
    }
  }
}
```

2. Restart OpenCode
3. Check MCP tools list

---

### Antigravity IDE

**Platform:** Cross-platform

**Steps:**

1. Open Antigravity settings
2. Navigate to **Extensions** → **MCP**
3. Add server with Python command:
   - Command: `python3`
   - Script: `/Users/yourusername/.claude-memory/mcp_server.py`
   - Working Dir: `/Users/yourusername/.claude-memory`

4. Apply and restart

---

### Cody

**Note:** Cody uses **custom commands** instead of MCP. These are auto-configured by `install-skills.sh`.

**Manual Setup:**

1. Edit `.vscode/settings.json` (VS Code) or Cody settings (JetBrains):

```json
{
  "cody.customCommands": {
    "slm-remember": {
      "description": "Save to SuperLocalMemory",
      "prompt": "Execute: python3 ~/.claude-memory/skills/slm-remember/main.py \"${input}\""
    },
    "slm-recall": {
      "description": "Search SuperLocalMemory",
      "prompt": "Execute: python3 ~/.claude-memory/skills/slm-recall/main.py \"${input}\""
    }
  }
}
```

2. Reload VS Code or JetBrains IDE

**Usage:** Type `/slm-remember` in Cody panel.

---

### Aider

**Note:** Aider uses the **smart wrapper** instead of MCP.

**Setup:**

1. Run the install script (already done if you installed SuperLocalMemory)
2. Use `aider-smart` instead of `aider`:

```bash
# Instead of: aider myfile.py
# Use:
aider-smart myfile.py
```

**What it does:**
- Automatically injects recent memories as context
- Uses standard `slm` CLI commands
- No configuration needed

---

## 🔧 MCP Server Tools

### 6 Available Tools

| Tool | Purpose | Example AI Request |
|------|---------|-------------------|
| `remember()` | Save memory | "Remember that we use FastAPI" |
| `recall()` | Search memories | "What do we use for REST APIs?" |
| `list_recent()` | Show recent memories | "Show my recent memories" |
| `get_status()` | System statistics | "What's my memory system status?" |
| `build_graph()` | Rebuild knowledge graph | "Rebuild my knowledge graph" |
| `switch_profile()` | Change profile | "Switch to work profile" |

### 4 Resources

| Resource | Content | Access |
|----------|---------|--------|
| `memory://graph/clusters` | Knowledge graph clusters | Read-only |
| `memory://patterns/identity` | Learned patterns | Read-only |
| `memory://recent/10` | Recent memories feed | Read-only |
| `memory://identity/context` | Identity profile | Read-only |

### 2 Prompts

1. **Context Injection** - Automatically provides recent memories to AI
2. **Identity Profile** - Injects coding preferences from pattern learning

---

## ✅ Verify MCP Connection

Once you've configured MCP in your IDE, check the dashboard to confirm the connection is active:

```bash
# Start the web dashboard
python3 ~/.claude-memory/ui_server.py

# Dashboard opens at http://localhost:8765
# Navigate to the "Agents" tab
```

You should see your IDE listed as a connected MCP client:

![MCP Agents Connected](../assets/screenshots/v25/v25-agents-tab.png)
*Figure: Dashboard showing MCP client connected with trust score 1.00*

**Key indicators:**
- **Protocol:** Shows `MCP` (agent-to-tool) or `A2A` (agent-to-agent)
- **Trust Score:** Starts at 1.00 (full trust)
- **Last Seen:** Recent timestamp means active connection
- **Memory Operations:** Count of remember/recall calls this session

> **Note:** The Agents tab (v2.5 feature) tracks all MCP connections in real-time. This view helps you verify that your IDE is successfully connected and communicating with SuperLocalMemory.

---

## 🐛 Troubleshooting

### MCP Server Not Showing Up

**Problem:** IDE doesn't list SuperLocalMemory tools

**Solutions:**

1. **Check Python path:**
   ```bash
   which python3
   # Output: /usr/bin/python3 or /opt/homebrew/bin/python3
   ```
   Update config file with correct path.

2. **Verify MCP package:**
   ```bash
   pip3 install mcp
   ```

3. **Check install path:**
   ```bash
   ls ~/.claude-memory/mcp_server.py
   # Should exist
   ```

4. **Restart IDE completely** - Quit and reopen, don't just reload.

5. **Check logs:**
   - Claude Desktop: `~/Library/Logs/Claude/mcp.log`
   - Cursor: `~/.cursor/logs/mcp.log`

### "Permission Denied" Error

**Solution:** Make script executable:
```bash
chmod +x ~/.claude-memory/mcp_server.py
```

### "Module not found" Error

**Solution:** Install required packages:
```bash
cd ~/.claude-memory
pip3 install -r requirements.txt
```

### MCP Server Crashes

**Solution:** Check Python version:
```bash
python3 --version
# Must be 3.8+
```

### Configuration File Not Found

**Solution:** Create directory:
```bash
# Claude Desktop (macOS)
mkdir -p ~/Library/Application\ Support/Claude

# Cursor (macOS)
mkdir -p ~/.cursor

# Windsurf (macOS)
mkdir -p ~/.windsurf
```

[[More troubleshooting: MCP-TROUBLESHOOTING.md →]](https://github.com/varun369/SuperLocalMemoryV2/blob/main/docs/MCP-TROUBLESHOOTING.md)

---

## 📖 Complete Manual Setup Guide

For detailed manual setup instructions for all IDEs, see:

**[docs/MCP-MANUAL-SETUP.md](https://github.com/varun369/SuperLocalMemoryV2/blob/main/docs/MCP-MANUAL-SETUP.md)**

Includes:
- Step-by-step configuration for each IDE
- Platform-specific paths (macOS/Windows/Linux)
- Troubleshooting for each tool
- Custom MCP client examples

---

## 🔗 Related Pages

- [[Universal-Architecture]] - Understand the universal architecture
- [[Universal-Skills]] - Learn about slash-command based access
- [[Installation]] - Initial setup guide
- [[Home]] - Back to wiki home

---

**Created by Varun Pratap Bhardwaj**
