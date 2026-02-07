# MCP Troubleshooting Guide

**SuperLocalMemory V2** - Debugging MCP Integration Issues

---

## 🚀 Quick Diagnosis (Start Here)

### Step 1: Verify MCP Server Works Standalone
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
  ...

Status: Starting server...
```

**If this fails, see Issue 1 below.**

---

### Step 2: Check IDE Shows MCP Server

| IDE | How to Check |
|-----|--------------|
| **Cursor** | Settings → Tools & MCP → "superlocalmemory-v2" (green dot) |
| **Claude Desktop** | Settings → Developer → "Edit Config" |
| **Windsurf** | Settings → MCP Servers |
| **VS Code** | Command Palette → "MCP: Open User Configuration" |
| **Zed** | Agent Panel → Settings → Green indicator dot |
| **ChatGPT** | Settings → Developer Mode → Connectors → MCP |

**If server doesn't appear, see Issue 2 below.**

---

### Step 3: Verify Configuration File

```bash
# Cursor
cat ~/.cursor/mcp_settings.json | python3 -m json.tool

# Claude Desktop (macOS)
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python3 -m json.tool

# Windsurf
cat ~/.windsurf/mcp_settings.json | python3 -m json.tool

# Zed
cat ~/.config/zed/settings.json | python3 -m json.tool

# OpenCode
cat ~/.config/opencode/opencode.json | python3 -m json.tool

# Antigravity
cat ~/.gemini/antigravity/mcp_config.json | python3 -m json.tool
```

**Look for:**
- Valid JSON (no syntax errors)
- Correct paths (no `{{INSTALL_DIR}}` placeholders)
- `cwd` field present
- `env.PYTHONPATH` field present

**If JSON is invalid, see Issue 3 below.**

---

### Step 4: Check Python Environment

```bash
which python3
# Should show: /usr/bin/python3 or /opt/homebrew/bin/python3 or similar

python3 -c "import mcp"
# Should complete without error

python3 -c "import sys; print('\n'.join(sys.path))"
# Should show paths including ~/.claude-memory
```

**If Python issues, see Issue 2 or 4 below.**

---

## 🐛 Common Issues & Fixes

### Issue 1: "MCP server won't start manually"

**Symptoms:**
```bash
$ python3 ~/.claude-memory/mcp_server.py
Error: Could not import SuperLocalMemory modules
```

**Diagnosis:**
```bash
# Check if files exist
ls -la ~/.claude-memory/mcp_server.py
ls -la ~/.claude-memory/memory_store_v2.py
ls -la ~/.claude-memory/graph_engine.py
ls -la ~/.claude-memory/pattern_learner.py
```

**Fix:**
1. Verify installation:
   ```bash
   cd ~/path/to/SuperLocalMemoryV2
   ./install.sh
   ```

2. Check permissions:
   ```bash
   chmod +x ~/.claude-memory/mcp_server.py
   chmod +x ~/.claude-memory/*.py
   ```

3. Test imports:
   ```bash
   cd ~/.claude-memory
   python3 -c "from memory_store_v2 import MemoryStoreV2"
   ```

---

### Issue 2: "ModuleNotFoundError: No module named 'mcp'"

**Symptoms:**
- Server crashes on startup
- Import error in logs
- "mcp" module not found

**Diagnosis:**
```bash
python3 -c "import mcp"
# If this errors, mcp package not installed
```

**Fix:**
```bash
# Install MCP package
pip3 install mcp

# Or if using conda:
conda install -c conda-forge mcp

# Or if system Python (macOS):
python3 -m pip install --user mcp
```

**Verify:**
```bash
python3 -c "import mcp; print(mcp.__version__)"
# Should print version number (e.g., 1.26.0)
```

---

### Issue 3: "Python not found" or wrong Python

**Symptoms:**
- "command not found: python3"
- Server uses wrong Python version
- Import errors despite mcp being installed

**Diagnosis:**
```bash
# Find Python installations
which python3
which python
ls -la /usr/bin/python*
ls -la /opt/homebrew/bin/python*

# Check where mcp is installed
python3 -c "import mcp; print(mcp.__file__)"
```

**Fix:**

**Option A: Use full Python path in config**
```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "/opt/homebrew/bin/python3",  // Full path
      "args": ["/Users/username/.claude-memory/mcp_server.py"]
    }
  }
}
```

**Option B: Fix PATH (if using conda)**
1. Find conda Python:
   ```bash
   conda info --base
   # Example: /opt/homebrew/Caskroom/miniforge/base
   ```

2. Update config:
   ```json
   {
     "command": "/opt/homebrew/Caskroom/miniforge/base/bin/python3"
   }
   ```

**Option C: Install mcp in correct Python**
```bash
# Use the SAME Python your IDE will use
/path/to/your/python3 -m pip install mcp
```

---

### Issue 4: IDE doesn't show MCP tools after restart

**Symptoms:**
- Config looks correct
- Server starts manually
- But IDE shows no tools

**Fix:**

**1. Complete restart (not just reload):**
- **macOS:** Cmd+Q (quit completely), then reopen
- **Windows/Linux:** Close ALL windows, reopen from scratch

**2. Check missing fields:**

Most common mistake - missing `cwd` or `PYTHONPATH`:
```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "python3",
      "args": ["/Users/username/.claude-memory/mcp_server.py"],
      "cwd": "/Users/username/.claude-memory",  // REQUIRED
      "env": {
        "PYTHONPATH": "/Users/username/.claude-memory"  // REQUIRED
      }
    }
  }
}
```

**3. Check IDE logs:**

| IDE | Where to find logs |
|-----|-------------------|
| **Cursor** | Help → Show Logs → Search for "mcp" |
| **Claude Desktop** | View → Developer → Toggle Developer Tools → Console |
| **VS Code** | Output panel → Select "MCP" from dropdown |
| **Zed** | View logs in `~/.config/zed/logs/` |

**4. Verify file paths are absolute:**
```json
// ❌ WRONG (relative path)
"args": ["mcp_server.py"]

// ✅ CORRECT (absolute path)
"args": ["/Users/username/.claude-memory/mcp_server.py"]
```

---

### Issue 5: "Cannot import SuperLocalMemory modules"

**Symptoms:**
- MCP server starts
- Tools appear in IDE
- But crash on first tool call
- Error: "ModuleNotFoundError: No module named 'memory_store_v2'"

**Diagnosis:**
```bash
cd ~/.claude-memory
python3 -c "from memory_store_v2 import MemoryStoreV2"
# Should work without error

# Check if files exist
ls -la ~/.claude-memory/*.py
```

**Fix:**

**If files missing:**
```bash
cd ~/path/to/SuperLocalMemoryV2-repo
./install.sh
```

**If files exist but import fails:**

Add `PYTHONPATH` to config (if missing):
```json
{
  "env": {
    "PYTHONPATH": "/Users/username/.claude-memory"
  },
  "cwd": "/Users/username/.claude-memory"
}
```

**Verify with test:**
```bash
cd ~/.claude-memory
PYTHONPATH=~/.claude-memory python3 -c "from memory_store_v2 import MemoryStoreV2; print('OK')"
```

---

### Issue 6: Config file keeps getting overwritten

**Symptoms:**
- Manually edit config
- Run `./install.sh`
- Custom settings lost

**Solution:**

**1. Check for backups:**
```bash
ls -la ~/.cursor/*.backup.*
ls -la ~/Library/Application\ Support/Claude/*.backup.*
```

**2. Restore backup:**
```bash
# Cursor
cp ~/.cursor/mcp_settings.json.backup.20260207-143000 ~/.cursor/mcp_settings.json

# Claude Desktop
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json.backup.* \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**3. Merge manually before reinstalling:**
```bash
# Backup your custom config first
cp ~/.cursor/mcp_settings.json ~/.cursor/mcp_settings.json.custom

# Then merge after install.sh runs
```

---

### Issue 7: Tools work but data not persisting

**Symptoms:**
- Can save memories
- But disappear after restart
- Or across different tools

**Diagnosis:**
```bash
# Check database exists and is writable
ls -la ~/.claude-memory/memory.db

# Check it's not empty
sqlite3 ~/.claude-memory/memory.db "SELECT COUNT(*) FROM memories;"

# Check multiple tools use same database
# (They all should point to same file)
```

**Fix:**

**1. Verify database location:**
```bash
# All tools should use this path
~/.claude-memory/memory.db

# NOT multiple databases like:
# ~/.cursor/memory.db  ❌
# ~/.claude/memory.db  ❌
```

**2. Check write permissions:**
```bash
ls -ld ~/.claude-memory/
# Should NOT be read-only

chmod 755 ~/.claude-memory/
chmod 644 ~/.claude-memory/memory.db
```

**3. Check database not locked:**
```bash
# Kill any hanging MCP servers
ps aux | grep mcp_server
kill <PID>  # If any found

# Test database access
sqlite3 ~/.claude-memory/memory.db "PRAGMA integrity_check;"
# Should output: ok
```

---

### Issue 8: MCP server crashes on tool call

**Symptoms:**
- Tools appear in IDE
- But crash when invoked
- Error in logs

**Diagnosis:**
```bash
# Start server with debug output
python3 ~/.claude-memory/mcp_server.py 2>&1 | tee /tmp/mcp-debug.log

# In another terminal, try to trigger crash
# Then check log:
cat /tmp/mcp-debug.log
```

**Common causes:**

**1. Missing environment variable:**
```json
{
  "env": {
    "PYTHONPATH": "/Users/username/.claude-memory"  // Must be set
  }
}
```

**2. Wrong working directory:**
```json
{
  "cwd": "/Users/username/.claude-memory"  // Must match install location
}
```

**3. Database locked:**
```bash
# Check for other processes
lsof ~/.claude-memory/memory.db

# Kill if needed
kill <PID>
```

**4. Corrupted database:**
```bash
# Check integrity
sqlite3 ~/.claude-memory/memory.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
cp ~/.claude-memory/backups/memory.db.backup.* ~/.claude-memory/memory.db
```

---

## 🔧 IDE-Specific Troubleshooting

### Cursor

**Config Location:** `~/.cursor/mcp_settings.json` (NOT `mcp.json`)

**How to check:**
1. Settings → Tools & MCP
2. Look for "superlocalmemory-v2"
3. Green dot = working, gray = not connected

**Common issues:**
- Wrong filename (should be `mcp_settings.json`)
- Missing `cwd` field
- Missing `env.PYTHONPATH` field

**Full working config:**
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

**Test manually:**
```bash
cd ~/.cursor
cat mcp_settings.json | python3 -m json.tool
# Should be valid JSON
```

---

### Claude Desktop

**Config Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**How to check:**
1. Settings → Developer → "Edit Config"
2. Look for "superlocalmemory-v2" section

**Common issues:**
- Spaces in path not escaped
- JSON syntax errors (missing commas, quotes)

**Test:**
```bash
# macOS
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python3 -m json.tool
```

---

### VS Code

**Config Location:** Accessed via command, NOT a direct file path

**How to access:**
1. Cmd+Shift+P (macOS) or Ctrl+Shift+P (Windows/Linux)
2. Type: "MCP: Open User Configuration"
3. Edit JSON

**Important:** VS Code uses `servers` object, NOT `mcpServers`:
```json
{
  "servers": {  // NOT "mcpServers"
    "superlocalmemory-v2": {
      "type": "stdio",
      "command": "python3",
      "args": ["/Users/username/.claude-memory/mcp_server.py"]
    }
  }
}
```

**Logs:**
Output panel → Select "MCP" from dropdown

---

### Zed Editor

**Config Location:** `~/.config/zed/settings.json`

**Format:** Merged into existing settings under `context_servers`:
```json
{
  "context_servers": {
    "superlocalmemory-v2": {
      "source": "custom",  // Required
      "command": "python3",
      "args": ["/Users/username/.claude-memory/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/username/.claude-memory"
      }
    }
  },
  // ... other Zed settings
}
```

**How to check:**
1. Open Agent Panel
2. Click settings gear
3. Look for green indicator dot

**Common issues:**
- Missing `"source": "custom"` field (required for Zed)
- Config not merged properly into existing settings.json

---

### JetBrains IDEs (IntelliJ, PyCharm, WebStorm)

**Config Location:** Via IDE settings (not file)

**How to access:**
1. Settings → Tools → AI Assistant → Model Context Protocol (MCP)
2. Or: Settings → Tools → MCP Server

**Requirements:**
- IntelliJ IDEA 2025.1+ (as MCP client)
- JetBrains IDE 2025.2+ (as MCP server)
- AI Assistant plugin 251.26094.80.5+

**Common issues:**
- Old IDE version (update to 2025.1+)
- AI Assistant plugin not installed
- MCP feature not enabled in settings

---

### ChatGPT Desktop

**Config Location:** Via app settings (not file)

**How to access:**
1. Settings → Advanced → Developer Mode
2. Enable "Developer mode"
3. Settings → Connectors → MCP
4. Add server configuration

**Requirements:**
- ChatGPT Desktop latest version (January 2026+)
- ChatGPT Pro, Plus, Business, Enterprise, or Edu plan

**Common issues:**
- Old app version (update to latest)
- Developer mode not enabled
- Plan doesn't support MCP (need Pro/Plus minimum)

---

### OpenCode

**Config Location:** `~/.config/opencode/opencode.json`

**Format:**
```json
{
  "mcp": {  // Note: "mcp" not "mcpServers"
    "superlocalmemory-v2": {
      "command": "python3",
      "args": ["/Users/username/.claude-memory/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/username/.claude-memory"
      },
      "cwd": "/Users/username/.claude-memory"
    }
  }
}
```

**Common issues:**
- Using `mcpServers` instead of `mcp`
- Missing OAuth tokens (if using remote servers)

---

### Google Antigravity

**Config Location:** `~/.gemini/antigravity/mcp_config.json`

**How to access:**
1. Click Agent session
2. Select "..." dropdown in editor side panel
3. Select "MCP Servers" → "Manage MCP Servers"
4. Click "View raw config"

**Limitations:**
- Maximum ~50-80 tools across ALL servers
- May conflict with Gemini CLI (both use `~/.gemini/`)

**Common issues:**
- Too many servers (>50-80 tools total)
- Conflict with Gemini CLI configuration

---

## 🛠️ Manual Configuration (Last Resort)

If auto-configuration fails completely, manually add to your IDE's config:

```json
{
  "mcpServers": {
    "superlocalmemory-v2": {
      "command": "/full/path/to/python3",
      "args": ["/Users/yourusername/.claude-memory/mcp_server.py"],
      "cwd": "/Users/yourusername/.claude-memory",
      "env": {
        "PYTHONPATH": "/Users/yourusername/.claude-memory"
      },
      "description": "SuperLocalMemory V2"
    }
  }
}
```

**Steps:**
1. Find Python: `which python3`
2. Find install dir: `echo ~/.claude-memory`
3. Replace paths above with YOUR actual paths
4. Validate JSON: `cat config.json | python3 -m json.tool`
5. Restart IDE completely
6. Check logs for errors

---

## 📞 Getting Help

### Before Opening an Issue

1. ✅ **Check logs** (see IDE-specific sections)
2. ✅ **Test server manually:** `python3 ~/.claude-memory/mcp_server.py`
3. ✅ **Verify config is valid JSON**
4. ✅ **Try manual configuration** (see above)
5. ✅ **Search existing issues:** https://github.com/varun369/SuperLocalMemoryV2/issues

### Opening an Issue

**Include this information:**
- **IDE/Tool:** Name and version (e.g., "Cursor 0.42.3")
- **OS:** macOS 14.2, Windows 11, Ubuntu 22.04, etc.
- **Python:** Output of `python3 --version`
- **Config file:** Contents (redact sensitive paths if needed)
- **Error message:** Exact error from logs
- **Manual test:** Output of `python3 ~/.claude-memory/mcp_server.py`
- **What you tried:** List troubleshooting steps already attempted

**Template:**
```markdown
**IDE/Tool:** Cursor 0.42.3
**OS:** macOS 14.2
**Python:** 3.11.7

**Issue:** MCP server doesn't appear in Tools & MCP settings

**Config file:**
[paste config here]

**Manual test:**
$ python3 ~/.claude-memory/mcp_server.py
[paste output here]

**What I tried:**
- Complete restart of IDE
- Verified JSON is valid
- Checked cwd and PYTHONPATH fields
- Installed mcp package
```

---

## 🎯 Quick Reference

### Most Common Causes (Fix These First)

1. **Wrong Python path** → Use full path in config
2. **Missing `cwd` field** → Add to config
3. **Missing `PYTHONPATH`** → Add to env section
4. **Didn't completely restart IDE** → Cmd+Q and reopen
5. **MCP package not installed** → `pip3 install mcp`
6. **Wrong config file location** → Check IDE-specific section
7. **JSON syntax errors** → Validate with `python3 -m json.tool`
8. **Relative paths instead of absolute** → Use full paths

### Verification Checklist

- [ ] Server starts manually without errors
- [ ] Config file is valid JSON
- [ ] Config has `cwd` field
- [ ] Config has `env.PYTHONPATH` field
- [ ] All paths are absolute (not relative)
- [ ] Python path is correct for your system
- [ ] MCP package is installed
- [ ] IDE completely restarted (not just reloaded)
- [ ] Server appears in IDE's MCP settings
- [ ] Database file exists and is writable

---

**Most issues resolve by:**
1. Using full Python path
2. Adding `cwd` and `PYTHONPATH`
3. Completely restarting IDE

**Still stuck? Open an issue with full details above.** 🚀
