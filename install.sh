#!/bin/bash
# ============================================================================
# SuperLocalMemory V2 Installation Script
# Copyright (c) 2026 Varun Pratap Bhardwaj
# Licensed under MIT License
# Repository: https://github.com/varun369/SuperLocalMemoryV2
# ============================================================================

set -e

INSTALL_DIR="${HOME}/.claude-memory"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Print banner
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  SuperLocalMemory V2 - Installation                          ║"
echo "║  by Varun Pratap Bhardwaj                                    ║"
echo "║  https://github.com/varun369/SuperLocalMemoryV2              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "✗ Error: Python 3.8+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION"

# Create installation directory
echo ""
echo "Creating installation directory..."
mkdir -p "${INSTALL_DIR}"
echo "✓ Directory: ${INSTALL_DIR}"

# Copy source files
echo ""
echo "Copying source files..."
cp -r "${REPO_DIR}/src/"* "${INSTALL_DIR}/"
echo "✓ Source files copied"

# Copy hooks
echo "Copying hooks..."
mkdir -p "${INSTALL_DIR}/hooks"
if [ -d "${REPO_DIR}/hooks" ] && [ "$(ls -A ${REPO_DIR}/hooks)" ]; then
    cp -r "${REPO_DIR}/hooks/"* "${INSTALL_DIR}/hooks/"
    echo "✓ Hooks copied"
else
    echo "○ No hooks to copy"
fi

# Copy CLI wrappers
echo "Copying CLI wrappers..."
mkdir -p "${INSTALL_DIR}/bin"
cp -r "${REPO_DIR}/bin/"* "${INSTALL_DIR}/bin/"
chmod +x "${INSTALL_DIR}/bin/"*
echo "✓ CLI wrappers installed"

# Copy API server
if [ -f "${REPO_DIR}/api_server.py" ]; then
    cp "${REPO_DIR}/api_server.py" "${INSTALL_DIR}/"
    echo "✓ API server copied"
fi

# Copy config if not exists
if [ ! -f "${INSTALL_DIR}/config.json" ]; then
    echo "Creating default config..."
    cp "${REPO_DIR}/config.json" "${INSTALL_DIR}/config.json"
    echo "✓ Config created"
else
    echo "○ Config exists (keeping existing)"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p "${INSTALL_DIR}/backups"
mkdir -p "${INSTALL_DIR}/profiles"
mkdir -p "${INSTALL_DIR}/vectors"
mkdir -p "${INSTALL_DIR}/cold-storage"
mkdir -p "${INSTALL_DIR}/jobs"
echo "✓ Directories created"

# Make Python scripts executable
chmod +x "${INSTALL_DIR}/"*.py 2>/dev/null || true

# Initialize database
echo ""
echo "Initializing database..."
if python3 "${INSTALL_DIR}/setup_validator.py" --init > /dev/null 2>&1; then
    echo "✓ Database initialized"
else
    # Fallback: create basic tables
    python3 -c "
import sqlite3
from pathlib import Path
db_path = Path.home() / '.claude-memory' / 'memory.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    summary TEXT,
    project_path TEXT,
    project_name TEXT,
    tags TEXT DEFAULT '[]',
    category TEXT,
    parent_id INTEGER,
    tree_path TEXT DEFAULT '/',
    depth INTEGER DEFAULT 0,
    memory_type TEXT DEFAULT 'session',
    importance INTEGER DEFAULT 5,
    content_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    compressed_at TIMESTAMP,
    tier INTEGER DEFAULT 1,
    cluster_id INTEGER
)''')
cursor.execute('CREATE TABLE IF NOT EXISTS graph_nodes (id INTEGER PRIMARY KEY, memory_id INTEGER UNIQUE, entities TEXT DEFAULT \"[]\", embedding_vector BLOB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS graph_edges (id INTEGER PRIMARY KEY, source_memory_id INTEGER, target_memory_id INTEGER, similarity REAL, relationship_type TEXT, shared_entities TEXT DEFAULT \"[]\", created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS graph_clusters (id INTEGER PRIMARY KEY, cluster_name TEXT, description TEXT, memory_count INTEGER DEFAULT 0, avg_importance REAL DEFAULT 5.0, top_entities TEXT DEFAULT \"[]\", created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS identity_patterns (id INTEGER PRIMARY KEY, pattern_type TEXT, pattern_key TEXT, pattern_value TEXT, confidence REAL DEFAULT 0.0, frequency INTEGER DEFAULT 1, last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS pattern_examples (id INTEGER PRIMARY KEY, pattern_id INTEGER, memory_id INTEGER, context TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS memory_tree (id INTEGER PRIMARY KEY, node_type TEXT, name TEXT, parent_id INTEGER, tree_path TEXT DEFAULT \"/\", depth INTEGER DEFAULT 0, memory_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS memory_archive (id INTEGER PRIMARY KEY, original_memory_id INTEGER, compressed_content TEXT, compression_type TEXT DEFAULT \"tier2\", original_size INTEGER, compressed_size INTEGER, archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS system_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
cursor.execute(\"INSERT OR REPLACE INTO system_metadata (key, value) VALUES ('product', 'SuperLocalMemory V2'), ('author', 'Varun Pratap Bhardwaj'), ('repository', 'https://github.com/varun369/SuperLocalMemoryV2'), ('license', 'MIT'), ('schema_version', '2.0.0')\")
conn.commit()
conn.close()
print('Database ready')
" && echo "✓ Database initialized (fallback)"
fi

# Check optional dependencies
echo ""
echo "Checking optional dependencies..."
python3 -c "import sklearn" 2>/dev/null && echo "✓ scikit-learn (Knowledge Graph)" || echo "○ scikit-learn not installed (optional)"
python3 -c "import numpy" 2>/dev/null && echo "✓ numpy (Vector Operations)" || echo "○ numpy not installed (optional)"
python3 -c "import igraph" 2>/dev/null && echo "✓ python-igraph (Clustering)" || echo "○ python-igraph not installed (optional)"
python3 -c "import fastapi" 2>/dev/null && echo "✓ fastapi (UI Server)" || echo "○ fastapi not installed (optional)"

# Auto-configure PATH
echo ""
echo "Configuring PATH..."

# Detect user's default shell (not installer script's shell)
USER_SHELL="${SHELL:-/bin/bash}"
SHELL_CONFIG=""

if [[ "$USER_SHELL" == *"zsh"* ]]; then
    SHELL_CONFIG="${HOME}/.zshrc"
    # Create .zshrc if it doesn't exist
    touch "${SHELL_CONFIG}" 2>/dev/null
elif [[ "$USER_SHELL" == *"bash"* ]]; then
    # For bash, prefer .bash_profile on macOS, .bashrc on Linux
    if [[ "$(uname)" == "Darwin" ]] && [ -f "${HOME}/.bash_profile" ]; then
        SHELL_CONFIG="${HOME}/.bash_profile"
    else
        SHELL_CONFIG="${HOME}/.bashrc"
        touch "${SHELL_CONFIG}" 2>/dev/null
    fi
else
    # Fallback: check which config exists
    if [ -f "${HOME}/.zshrc" ]; then
        SHELL_CONFIG="${HOME}/.zshrc"
    elif [ -f "${HOME}/.bash_profile" ]; then
        SHELL_CONFIG="${HOME}/.bash_profile"
    elif [ -f "${HOME}/.bashrc" ]; then
        SHELL_CONFIG="${HOME}/.bashrc"
    else
        # Default to zsh on modern macOS
        SHELL_CONFIG="${HOME}/.zshrc"
        touch "${SHELL_CONFIG}"
    fi
fi

# Check if PATH already configured
PATH_EXPORT="export PATH=\"\${HOME}/.claude-memory/bin:\${PATH}\""
if grep -q ".claude-memory/bin" "${SHELL_CONFIG}" 2>/dev/null; then
    echo "○ PATH already configured in ${SHELL_CONFIG}"
else
    # Add PATH export to shell config
    echo "" >> "${SHELL_CONFIG}"
    echo "# SuperLocalMemory V2 - Added by installer on $(date '+%Y-%m-%d')" >> "${SHELL_CONFIG}"
    echo "${PATH_EXPORT}" >> "${SHELL_CONFIG}"
    echo "✓ PATH configured in ${SHELL_CONFIG}"
fi

# Add to current session PATH
export PATH="${HOME}/.claude-memory/bin:${PATH}"
echo "✓ Commands available in current session"

# Summary
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Installation Complete!                                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "✓ Commands are now globally available!"
echo ""
echo "  You can use them immediately:"
echo ""
echo "Available commands:"
echo "  superlocalmemoryv2:remember  - Save a new memory"
echo "  superlocalmemoryv2:recall    - Search memories"
echo "  superlocalmemoryv2:list      - List recent memories"
echo "  superlocalmemoryv2:status    - Check system status"
echo "  superlocalmemoryv2:profile   - Manage memory profiles"
echo "  superlocalmemoryv2:reset     - Reset memory database"
echo ""
echo "Quick start (try now):"
echo "  superlocalmemoryv2:status"
echo "  superlocalmemoryv2:remember 'My first memory'"
echo "  superlocalmemoryv2:recall 'first'"
echo ""
# Optional: Offer to install UI dependencies
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Optional: Web UI & Advanced Features                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "SuperLocalMemory V2 includes optional advanced features:"
echo "  • Web UI with graph visualization (FastAPI + D3.js)"
echo "  • Knowledge Graph (GraphRAG)"
echo "  • Pattern Learning (xMemory-style)"
echo "  • Multi-tier compression"
echo ""
echo "Install optional dependencies now? (y/N)"
read -r INSTALL_OPTIONAL

if [[ "$INSTALL_OPTIONAL" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Installing optional dependencies..."

    # Detect pip installation method
    if pip3 install --help | grep -q "break-system-packages"; then
        PIP_FLAGS="--break-system-packages"
    else
        PIP_FLAGS=""
    fi

    echo "  Installing: scikit-learn, numpy, python-igraph, leidenalg, fastapi, uvicorn..."
    pip3 install $PIP_FLAGS scikit-learn numpy python-igraph leidenalg fastapi uvicorn

    if [ $? -eq 0 ]; then
        echo "✓ Optional dependencies installed successfully"
        echo ""
        echo "Start Web UI:"
        echo "  python3 ~/.claude-memory/api_server.py"
        echo "  Then open: http://127.0.0.1:8000"
    else
        echo "⚠️  Installation failed. You can install manually later:"
        echo "  pip3 install scikit-learn numpy python-igraph leidenalg fastapi uvicorn"
    fi
else
    echo ""
    echo "Skipping optional dependencies."
    echo ""
    echo "To install later:"
    echo "  For advanced features: pip3 install scikit-learn numpy python-igraph leidenalg"
    echo "  For Web UI: pip3 install fastapi uvicorn"
    echo "  Start UI: python3 ~/.claude-memory/api_server.py"
fi

echo ""
echo "Documentation: https://github.com/varun369/SuperLocalMemoryV2"
echo "Author: Varun Pratap Bhardwaj"
echo ""
