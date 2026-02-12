# Installation Guide

Complete installation instructions for SuperLocalMemory V2.3.0 with universal MCP integration on all platforms. This guide covers setup for 16+ IDEs including Claude Desktop, Cursor IDE, Windsurf, VS Code, and more.

---

## 📋 Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| **Python** | 3.8+ | `python3 --version` |
| **Git** | Any | `git --version` |
| **SQLite** | 3.x (usually pre-installed) | `sqlite3 --version` |

### Platform-Specific Notes

| Platform | Notes |
|----------|-------|
| **macOS** | Python 3 may need: `brew install python3` |
| **Linux** | Usually ready. Ubuntu/Debian: `sudo apt install python3` |
| **Windows** | Download Python from [python.org](https://python.org). Check "Add to PATH" during install |

---

## 📹 Video Walkthrough (1 minute)

Watch the step-by-step installation process:

![Installation Walkthrough Video](https://varun369.github.io/SuperLocalMemoryV2/assets/videos/installation-walkthrough.mp4)

Or follow the detailed guide below.

---

## 🚀 Quick Install

### npm (Recommended — All Platforms)

**Easiest method. Works on Mac, Linux, and Windows:**

```bash
# Install globally
npm install -g superlocalmemory

# Verify installation
slm status

# Start using
slm remember "Your first memory"
```

**Auto-configures:** Claude Desktop, Cursor, Windsurf, VS Code, Continue.dev, and 11+ other IDEs.

**Path setup:** Automatic (npm handles it).

---

### Mac/Linux (Manual Install)

```bash
# 1. Clone the repository
git clone https://github.com/varun369/SuperLocalMemoryV2.git

# 2. Enter directory
cd SuperLocalMemoryV2

# 3. Run installer
./install.sh

# 4. Add to PATH (optional but recommended)
echo 'export PATH="${HOME}/.claude-memory/bin:${PATH}"' >> ~/.zshrc
source ~/.zshrc
```

**After installation, verify with:**
```bash
slm status
```

![CLI Status Output](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-status.png)
*Figure: Successful Mac/Linux installation showing 0 memories and all systems ready*

### Windows (PowerShell — Manual Install)

```powershell
# 1. Clone the repository
git clone https://github.com/varun369/SuperLocalMemoryV2.git

# 2. Enter directory
cd SuperLocalMemoryV2

# 3. Run installer (Run PowerShell as Administrator)
.\install.ps1

# 4. Add to PATH (add to your PowerShell profile)
$env:PATH += ";$env:USERPROFILE\.claude-memory\bin"
```

**Windows users:** See the [[Video Walkthrough|#-video-walkthrough-1-minute]] above for a visual step-by-step guide. If you encounter the "running scripts is disabled" error, refer to the troubleshooting section below.

---

## ✅ Verify Installation

Run the status command to confirm everything is working:

```bash
slm status
```

**Expected output:**

![Successful Installation](https://varun369.github.io/SuperLocalMemoryV2/assets/screenshots/cli/cli-status.png)

*Figure: Fresh installation showing 0 memories and all systems ready*

The output should show:
```
╔══════════════════════════════════════════════════════════════╗
║  SuperLocalMemory V2.5.0 - System Status                     ║
╚══════════════════════════════════════════════════════════════╝
✓ Database: OK (0 memories)
✓ Graph: Ready
✓ Patterns: Ready
✓ MCP: Configured for 4 IDEs
✓ Skills: Installed (6 skills)
```

### What Was Configured?

The installer automatically detects and configures:

**IDEs with MCP Support:**
- ✅ Claude Desktop - MCP server configured
- ✅ Cursor - MCP settings added
- ✅ Windsurf - MCP integration enabled
- ✅ Continue.dev - MCP + skills configured

**Skills Installed:**
- ✅ 6 universal skills (slm-remember, slm-recall, etc.)
- ✅ Compatible with Claude Code, Continue.dev, Cody

**CLI Access:**
- ✅ `slm` command available globally
- ✅ `aider-smart` wrapper for Aider integration
- ✅ Bash/Zsh completion installed

---

## 🎨 Start Visualization Dashboard (NEW v2.2.0)

### Quick Start

```bash
# Launch the interactive web dashboard
python ~/.claude-memory/ui_server.py

# Opens at http://localhost:8765
```

**Expected output:**
```
╔══════════════════════════════════════════════════════════════╗
║  SuperLocalMemory V2.2.0 - Visualization Dashboard           ║
╚══════════════════════════════════════════════════════════════╝

✓ Database loaded: 523 memories
✓ Knowledge graph loaded: 8 clusters, 312 entities
✓ Pattern data loaded: 24 learned patterns

🌐 Dashboard running at: http://localhost:8765
🔧 Press Ctrl+C to stop server
```

### Install Dashboard Dependencies

**If dashboard fails to start**, install visualization dependencies:

```bash
# Install required packages
pip install dash plotly pandas networkx

# Or install from requirements file
pip install -r ~/.claude-memory/requirements-dashboard.txt
```

### Dashboard Features

| Feature | Description |
|---------|-------------|
| **📈 Timeline View** | See all memories chronologically with importance color-coding |
| **🔍 Search Explorer** | Real-time semantic search with visual score bars |
| **🕸️ Graph Visualization** | Interactive knowledge graph with clusters |
| **📊 Statistics Dashboard** | Memory trends, tag clouds, pattern insights |
| **🎯 Advanced Filters** | Filter by tags, importance, date range, clusters |
| **🌓 Dark Mode** | Eye-friendly theme for extended use |

### Configuration

**Custom port:**
```bash
python ~/.claude-memory/ui_server.py --port 8080
```

**Specific profile:**
```bash
python ~/.claude-memory/ui_server.py --profile work
```

**Debug mode:**
```bash
python ~/.claude-memory/ui_server.py --debug
```

### Performance

| Dataset Size | Dashboard Load | Timeline Render | Graph Draw |
|--------------|----------------|-----------------|------------|
| 100 memories | < 100ms | < 100ms | < 200ms |
| 500 memories | < 300ms | < 200ms | < 500ms |
| 1,000 memories | < 500ms | < 300ms | < 1s |
| 5,000 memories | < 2s | < 1s | < 3s |

**[[Complete Dashboard Guide →|Visualization-Dashboard]]**

---

---

**🌐 Official Website:** [varun369.github.io/SuperLocalMemoryV2](https://varun369.github.io/SuperLocalMemoryV2/) | **📦 NPM:** [npmjs.com/package/superlocalmemory](https://www.npmjs.com/package/superlocalmemory)

---

## 📁 Installation Directory

Everything is installed to `~/.claude-memory/`:

```
~/.claude-memory/
├── memory.db           # SQLite database
├── config.json         # Configuration
├── bin/                # CLI commands
├── vectors/            # Embeddings (if using)
├── profiles/           # Multi-profile storage
├── backups/            # Automatic backups
└── *.py                # Core Python modules
```

---

## 🔧 Optional Dependencies

Core features work with **zero external dependencies**. For advanced features:

```bash
# Knowledge Graph (clustering, visualization)
pip install scikit-learn numpy

# Advanced Clustering (Leiden algorithm)
pip install python-igraph leidenalg

# Web UI Server
pip install fastapi uvicorn
```

### Feature Availability

| Feature | Required Packages | Status Without |
|---------|------------------|----------------|
| Memory storage | None | ✅ Full |
| Full-text search | None | ✅ Full |
| Multi-profile | None | ✅ Full |
| Knowledge Graph | scikit-learn | ⚠️ Basic clustering only |
| Pattern Learning | None | ✅ Full |
| Web UI | fastapi, uvicorn | ❌ CLI only |

---

## 🔄 Updating

### npm Users (Recommended)

```bash
# Update to latest version
npm update -g superlocalmemory

# Or force latest (if update doesn't work)
npm install -g superlocalmemory@latest

# Install specific version
npm install -g superlocalmemory@2.3.7
```

**What happens during update:**
- ✅ Downloads new version from npm
- ✅ Auto-runs postinstall script
- ✅ Copies updated files to `~/.claude-memory/`
- ✅ Preserves your database and memories
- ✅ No restart needed (works immediately)

**Verify update:**
```bash
slm status  # Should show new version number
slm recall "test"  # Test functionality
```

### Manual Install Users (Git)

```bash
# Pull latest changes
cd SuperLocalMemoryV2
git pull origin main

# Re-run installer
./install.sh  # Mac/Linux
# or
.\install.ps1  # Windows
```

**Your memories are preserved during updates.** The installer never touches `~/.claude-memory/memory.db`.

---

## 🗑️ Uninstalling

```bash
# Remove installation directory
rm -rf ~/.claude-memory

# Remove from PATH (edit ~/.zshrc or ~/.bashrc)
# Delete the line: export PATH="${HOME}/.claude-memory/bin:${PATH}"
```

**Warning:** This deletes all your memories. Back up `~/.claude-memory/memory.db` first if needed.

---

## 🐛 Troubleshooting

### "command not found: superlocalmemoryv2"

**Solution:** Add to PATH:
```bash
export PATH="${HOME}/.claude-memory/bin:${PATH}"
```

### "Permission denied" on install.sh

**Solution:** Make executable:
```bash
chmod +x install.sh
./install.sh
```

### Python version error

**Solution:** Ensure Python 3.8+:
```bash
python3 --version
# If too old, install newer Python
```

### Windows: "running scripts is disabled"

**Solution:** Enable script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

[[More troubleshooting →|Troubleshooting]]

---

## 🔧 IDE-Specific Setup

### Already Configured (Auto)

If you have these IDEs installed, they're **already configured**:
- Claude Desktop
- Cursor
- Windsurf
- Continue.dev (VS Code)

Just **restart the IDE** and the SuperLocalMemory tools will be available.

### Manual Setup Required

For these IDEs, see the [[MCP-Integration]] guide:
- **ChatGPT Desktop** - Settings → MCP
- **Perplexity AI** - App settings
- **Zed Editor** - JSON config
- **OpenCode** - MCP config
- **Antigravity IDE** - Settings
- **Cody** - Already has skills via install-skills.sh
- **Aider** - Use `aider-smart` wrapper

[[Complete IDE setup guide →|MCP-Integration]]

---

## 🎯 Testing Your Installation

### Test MCP Integration (Claude Desktop)

1. Open Claude Desktop
2. Start a new conversation
3. Say: "What tools do you have access to?"
4. You should see SuperLocalMemory tools listed
5. Test: "Remember that we use FastAPI for APIs"
6. Verify: "What do we use for APIs?"

### Test Skills (Claude Code)

1. Open Claude Code
2. Type `/` to see available skills
3. You should see `/slm-remember`, `/slm-recall`, etc.
4. Test: `/slm-remember "Test memory"`

### Test CLI

```bash
# Add a memory
slm remember "Testing SuperLocalMemory CLI"

# Search for it
slm recall "testing"

# Check status
slm status
```

---

## 🆕 What's New in v2.2.0?

**Visualization & Search Enhancements:**
- ✅ **Interactive Web Dashboard** - Timeline, search, graph visualization, statistics
- ✅ **Hybrid Search** - Combines semantic, FTS5, and graph for maximum accuracy
- ✅ **Advanced Filters** - Multi-dimensional filtering across all views
- ✅ **Dark Mode** - Eye-friendly theme for extended use
- ✅ **Real-time Analytics** - Memory trends, tag clouds, pattern insights

**v2.1.0 Features (Still Included):**
- ✅ MCP server for 16+ IDEs
- ✅ 6 universal skills
- ✅ Universal CLI (`slm` command)
- ✅ Auto-detection and configuration

**Backward Compatible:**
- ✅ All v2.1 and v2.0 commands still work
- ✅ Existing memories preserved
- ✅ No breaking changes

---

## ⏭️ Next Steps

1. [[Visualization-Dashboard]] — Explore the interactive web UI (NEW v2.2.0)
2. [[MCP-Integration]] — Learn about IDE integration
3. [[Universal-Skills]] — Master the 6 skills
4. [[Quick-Start-Tutorial]] — Create your first memory
5. [[Universal-Architecture]] — Understand the 9-layer system
6. [[CLI-Cheatsheet]] — Essential commands

---

## 📸 Screenshots

*Coming soon: Screenshots of SuperLocalMemory in Claude Desktop, Cursor, and Windsurf*

---

[[← Back to Home|Home]]

---

**Created by Varun Pratap Bhardwaj**
