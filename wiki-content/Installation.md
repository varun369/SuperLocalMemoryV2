# Installation Guide

Complete installation instructions for SuperLocalMemory V2 on all platforms.

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

## 🚀 Quick Install

### Mac/Linux (Recommended)

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

### Windows (PowerShell)

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

---

## ✅ Verify Installation

```bash
# Check system status
superlocalmemoryv2:status

# Expected output:
# ╔══════════════════════════════════════════════════════════════╗
# ║  SuperLocalMemory V2 - System Status                         ║
# ╚══════════════════════════════════════════════════════════════╝
# ✓ Database: OK (0 memories)
# ✓ Graph: Ready
# ✓ Patterns: Ready
```

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

```bash
# Pull latest changes
cd SuperLocalMemoryV2
git pull origin main

# Re-run installer
./install.sh  # or .\install.ps1 on Windows
```

Your memories are preserved during updates.

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

## ⏭️ Next Steps

1. [[Quick-Start-Tutorial]] — Create your first memory
2. [[CLI-Cheatsheet]] — Essential commands
3. [[4-Layer-Architecture]] — Understand how it works

---

[[← Back to Home|Home]]
