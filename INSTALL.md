# Installation Guide

## SuperLocalMemory V2 - Complete Installation Instructions

This guide walks you through installing SuperLocalMemory V2 as a **standalone intelligent memory system**. Works independently or integrates with Claude CLI, other AI assistants, or terminal workflows.

SuperLocalMemory V2 is NOT a dependency of Claude CLI - it's an independent system that can optionally work WITH Claude CLI.

---

## Table of Contents

- [System Requirements](#system-requirements)
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Method 1: Quick Install (Recommended)](#method-1-quick-install-recommended)
  - [Method 2: Manual Installation](#method-2-manual-installation)
  - [Method 3: Development Installation](#method-3-development-installation)
- [Verification](#verification)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)
- [Next Steps](#next-steps)

---

## System Requirements

### Operating Systems
- macOS 10.14+ (Mojave or later)
- Linux (Ubuntu 18.04+, Debian 10+, Fedora 30+, or equivalent)
- Windows 10/11 with WSL2 (Windows Subsystem for Linux)

### Hardware Requirements
- **Minimum:**
  - 2 GB RAM
  - 100 MB disk space (for core system)
  - 1 GB disk space (recommended for memory storage)
- **Recommended:**
  - 4 GB+ RAM (for faster graph/pattern processing)
  - 2 GB+ disk space (for large memory databases)

---

## Prerequisites

### Required Software

**1. Python 3.8 or higher**

Check your Python version:
```bash
python3 --version
```

If Python is not installed or version is older than 3.8:
- **macOS:** `brew install python3`
- **Ubuntu/Debian:** `sudo apt update && sudo apt install python3 python3-pip`
- **Fedora:** `sudo dnf install python3 python3-pip`

**2. SQLite3**

SQLite is usually pre-installed on most systems. Verify:
```bash
sqlite3 --version
```

If not installed:
- **macOS:** `brew install sqlite3`
- **Ubuntu/Debian:** `sudo apt install sqlite3`
- **Fedora:** `sudo dnf install sqlite`

**3. Git (for cloning repository)**

```bash
git --version
```

If not installed:
- **macOS:** `brew install git` or install Xcode Command Line Tools
- **Ubuntu/Debian:** `sudo apt install git`
- **Fedora:** `sudo dnf install git`

### Optional Dependencies

- **Virtual Environment** (recommended for development):
  - Python venv module (usually included with Python 3.8+)

---

## Installation Methods

### Method 1: Quick Install (Recommended)

**Best for:** End users who want to get started quickly.

```bash
# 1. Clone the repository
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2-repo

# 2. Run the installation script
./install.sh

# 3. Add CLI commands to your PATH
echo 'export PATH="${HOME}/.claude-memory/bin:${PATH}"' >> ~/.zshrc
source ~/.zshrc

# For bash users, replace ~/.zshrc with ~/.bashrc
```

**What the installer does:**
- Creates `~/.claude-memory/` directory
- Copies all source files to installation directory
- Sets up directory structure (backups, profiles, vectors, cold-storage, jobs)
- Creates CLI wrapper commands
- Sets executable permissions
- Copies default configuration

**Installation location:** `~/.claude-memory/`

---

### Method 2: Manual Installation

**Best for:** Advanced users who want control over installation location.

```bash
# 1. Clone the repository
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2-repo

# 2. Choose installation directory
INSTALL_DIR="${HOME}/.claude-memory"  # Or your preferred location
mkdir -p "${INSTALL_DIR}"

# 3. Copy source files
cp -r src/* "${INSTALL_DIR}/"
cp -r hooks "${INSTALL_DIR}/"
cp -r bin "${INSTALL_DIR}/"
cp config.json "${INSTALL_DIR}/"

# 4. Create directory structure
mkdir -p "${INSTALL_DIR}/"{backups,profiles,vectors,cold-storage,jobs}

# 5. Set permissions
chmod +x "${INSTALL_DIR}/"*.py
chmod +x "${INSTALL_DIR}/bin/"*

# 6. Add to PATH
echo "export PATH=\"${INSTALL_DIR}/bin:\${PATH}\"" >> ~/.zshrc
source ~/.zshrc
```

---

### Method 3: Development Installation

**Best for:** Contributors and developers who want to modify code.

```bash
# 1. Clone the repository
git clone https://github.com/varun369/SuperLocalMemoryV2.git
cd SuperLocalMemoryV2-repo

# 2. Create virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# 3. Verify Python version
python --version  # Should be 3.8+

# 4. Run install script with development mode
./install.sh

# 5. Create symlinks to source directory (for live code changes)
# This allows editing in repo while using installed version
ln -sf "$(pwd)/src/"*.py "${HOME}/.claude-memory/"

# 6. Add to PATH
echo 'export PATH="${HOME}/.claude-memory/bin:${PATH}"' >> ~/.zshrc
source ~/.zshrc
```

---

## Verification

After installation, verify everything is working:

### Step 1: Check CLI Commands

```bash
# Should display help information
memory-status

# Expected output:
# SuperLocalMemory V2 Status
# Database: ~/.claude-memory/memory.db
# ...
```

### Step 2: Verify Database Creation

```bash
# Check if database file exists
ls -lh ~/.claude-memory/memory.db

# If it doesn't exist, it will be created on first use
```

### Step 3: Test Core Functionality

```bash
# Test memory storage (via Python API)
cd ~/.claude-memory
python3 memory_store_v2.py add "Installation test" --tags test

# Test search
python3 memory_store_v2.py search "installation"

# Expected output: Should show the test memory you just added
```

### Step 4: Test Knowledge Graph

```bash
# Build graph from existing memories
python3 ~/.claude-memory/graph_engine.py build

# View statistics
python3 ~/.claude-memory/graph_engine.py stats

# Expected: Should show cluster and entity counts
```

### Step 5: Test Pattern Learning

```bash
# Update patterns
python3 ~/.claude-memory/pattern_learner.py update

# View patterns
python3 ~/.claude-memory/pattern_learner.py stats

# Expected: Pattern statistics displayed
```

### Step 6: Install Claude CLI Skills (Optional)

**Want to use SuperLocalMemory V2 with Claude CLI?** Install optional skills for convenient slash commands.

**Important:** This step is **completely optional**. SuperLocalMemory V2 works as a standalone system without Claude CLI.

#### Prerequisites for Skills

- Claude CLI installed and running
- SuperLocalMemory V2 already installed (steps 1-5 above)

#### Quick Install

```bash
# Navigate to repository
cd SuperLocalMemoryV2-repo

# Run skills installer
./install-skills.sh

# Choose installation method:
# 1. Symlink (recommended) - Changes in repo reflect immediately
# 2. Copy - Stable, requires manual updates

# Restart Claude CLI to load skills
```

#### Manual Install (Symlink Method)

```bash
# Create skills directory
mkdir -p ~/.claude/skills

# Create symlinks
cd /path/to/SuperLocalMemoryV2-repo
ln -sf "$(pwd)/claude-skills/"*.md ~/.claude/skills/

# Restart Claude CLI
```

#### Manual Install (Copy Method)

```bash
# Create skills directory
mkdir -p ~/.claude/skills

# Copy skill files
cp /path/to/SuperLocalMemoryV2-repo/claude-skills/*.md ~/.claude/skills/

# Restart Claude CLI
```

#### Verify Skills Installation

After restarting Claude CLI:

```bash
# List all skills
/skills

# You should see:
# - superlocalmemoryv2:remember
# - superlocalmemoryv2:search
# - superlocalmemoryv2:graph-build
# - superlocalmemoryv2:graph-stats
# - superlocalmemoryv2:patterns
# - superlocalmemoryv2:status

# Test a skill
/superlocalmemoryv2:status
```

#### Available Skills

Once installed, you can use these commands in Claude CLI:

```bash
# Add memory
/superlocalmemoryv2:remember "Your memory text" --tags tag1,tag2

# Search memories
/superlocalmemoryv2:search "query"

# Build knowledge graph
/superlocalmemoryv2:graph-build

# View statistics
/superlocalmemoryv2:graph-stats

# Learn patterns
/superlocalmemoryv2:patterns update

# System status
/superlocalmemoryv2:status
```

#### Standalone Alternative

**Don't use Claude CLI?** No problem. Use terminal commands instead:

```bash
# Everything works the same via terminal
cd ~/.claude-memory
python3 memory_store_v2.py add "Your memory" --tags tag1
python3 memory_store_v2.py search "query"
python3 graph_engine.py build
memory-status
```

**For complete skills documentation:** See [claude-skills/CLAUDE_CLI_INSTALLATION.md](claude-skills/CLAUDE_CLI_INSTALLATION.md)

---

## Configuration

### Default Configuration

The system uses `~/.claude-memory/config.json` for configuration:

```json
{
  "database_path": "~/.claude-memory/memory.db",
  "backup_dir": "~/.claude-memory/backups",
  "profiles_dir": "~/.claude-memory/profiles",
  "vector_dir": "~/.claude-memory/vectors",
  "compression": {
    "enabled": true,
    "min_age_days": 30,
    "archive_tier_days": 90
  }
}
```

### Customizing Configuration

Edit `~/.claude-memory/config.json` to customize:

**Change database location:**
```json
{
  "database_path": "/custom/path/to/memory.db"
}
```

**Disable compression:**
```json
{
  "compression": {
    "enabled": false
  }
}
```

**Change backup directory:**
```json
{
  "backup_dir": "/custom/backup/location"
}
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Command Not Found

**Symptom:**
```bash
memory-status
# zsh: command not found: memory-status
```

**Solution:**
```bash
# Verify bin directory is in PATH
echo $PATH | grep ".claude-memory/bin"

# If not found, add to shell config
echo 'export PATH="${HOME}/.claude-memory/bin:${PATH}"' >> ~/.zshrc
source ~/.zshrc
```

#### Issue 2: Permission Denied

**Symptom:**
```bash
./install.sh
# Permission denied
```

**Solution:**
```bash
# Make install script executable
chmod +x install.sh
./install.sh
```

#### Issue 3: Python Version Too Old

**Symptom:**
```bash
python3 --version
# Python 3.7.x
```

**Solution:**
```bash
# Install Python 3.8+ using package manager
# macOS:
brew install python@3.11

# Ubuntu/Debian:
sudo apt update
sudo apt install python3.11

# Update symlink if needed
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

#### Issue 4: SQLite Not Found

**Symptom:**
```bash
python3 -c "import sqlite3"
# ModuleNotFoundError: No module named '_sqlite3'
```

**Solution:**
```bash
# Rebuild Python with SQLite support (if installed from source)
# Or install system SQLite and reinstall Python

# macOS:
brew install sqlite3
brew reinstall python@3.11

# Ubuntu/Debian:
sudo apt install libsqlite3-dev
# Reinstall Python from source or use apt version
```

#### Issue 5: Database Locked

**Symptom:**
```bash
python3 memory_store_v2.py search "test"
# sqlite3.OperationalError: database is locked
```

**Solution:**
```bash
# Check for other processes using the database
lsof ~/.claude-memory/memory.db

# Kill processes if safe
# Or wait for them to complete
```

#### Issue 6: Installation Directory Already Exists

**Symptom:**
```bash
./install.sh
# Directory ~/.claude-memory already exists
```

**Solution:**
```bash
# Option 1: Backup and remove existing installation
mv ~/.claude-memory ~/.claude-memory.backup
./install.sh

# Option 2: Force reinstall (overwrites files)
rm -rf ~/.claude-memory
./install.sh
```

---

## Uninstallation

To completely remove SuperLocalMemory V2:

### Step 1: Backup Data (Optional)

```bash
# Backup database
cp ~/.claude-memory/memory.db ~/memory.db.backup

# Backup configuration
cp ~/.claude-memory/config.json ~/config.json.backup
```

### Step 2: Remove Installation

```bash
# Remove installation directory
rm -rf ~/.claude-memory
```

### Step 3: Remove PATH Entry

Edit `~/.zshrc` or `~/.bashrc` and remove:
```bash
export PATH="${HOME}/.claude-memory/bin:${PATH}"
```

Then reload:
```bash
source ~/.zshrc  # or ~/.bashrc
```

### Step 4: Clean Repository (Optional)

```bash
# Remove cloned repository
rm -rf ~/path/to/SuperLocalMemoryV2-repo
```

---

## Next Steps

After successful installation:

1. **Read the Quick Start Guide:** [QUICKSTART.md](QUICKSTART.md)
2. **Explore Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
3. **Learn CLI Commands:** [docs/CLI-COMMANDS-REFERENCE.md](docs/CLI-COMMANDS-REFERENCE.md)
4. **Set Up Profiles:** [docs/PROFILES-GUIDE.md](docs/PROFILES-GUIDE.md)
5. **Contribute:** [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Support

If you encounter issues not covered in this guide:

1. **Check existing documentation:** [docs/](docs/)
2. **Search GitHub Issues:** [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues)
3. **Create a new issue:** Provide error messages, OS version, Python version

---

## Author

**Varun Pratap Bhardwaj**
*Solution Architect*

SuperLocalMemory V2 - Standalone intelligent memory system that works with any AI assistant or terminal workflow.

---

**Installation successful? Let's build intelligent memory!**

See [QUICKSTART.md](QUICKSTART.md) for your first 5 minutes with SuperLocalMemory V2.
