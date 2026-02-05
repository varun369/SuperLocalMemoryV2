# ============================================================================
# SuperLocalMemory V2 Installation Script (Windows PowerShell)
# Copyright (c) 2026 Varun Pratap Bhardwaj
# Licensed under MIT License
# Repository: https://github.com/varun369/SuperLocalMemoryV2
# ============================================================================

$ErrorActionPreference = "Stop"

$INSTALL_DIR = "$env:USERPROFILE\.claude-memory"
$REPO_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# Print banner
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  SuperLocalMemory V2 - Installation (Windows)                ║" -ForegroundColor Cyan
Write-Host "║  by Varun Pratap Bhardwaj                                    ║" -ForegroundColor Cyan
Write-Host "║  https://github.com/varun369/SuperLocalMemoryV2              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..."
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
            Write-Host "✗ Error: Python 3.8+ required (found $pythonVersion)" -ForegroundColor Red
            exit 1
        }
        Write-Host "✓ $pythonVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Error: Python not found. Install from https://python.org" -ForegroundColor Red
    exit 1
}

# Create installation directory
Write-Host ""
Write-Host "Creating installation directory..."
if (!(Test-Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
}
Write-Host "✓ Directory: $INSTALL_DIR" -ForegroundColor Green

# Copy source files
Write-Host ""
Write-Host "Copying source files..."
Copy-Item -Path "$REPO_DIR\src\*" -Destination $INSTALL_DIR -Recurse -Force
Write-Host "✓ Source files copied" -ForegroundColor Green

# Copy hooks
Write-Host "Copying hooks..."
$hooksDir = "$INSTALL_DIR\hooks"
if (!(Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
}
if (Test-Path "$REPO_DIR\hooks") {
    $hookFiles = Get-ChildItem "$REPO_DIR\hooks" -ErrorAction SilentlyContinue
    if ($hookFiles) {
        Copy-Item -Path "$REPO_DIR\hooks\*" -Destination $hooksDir -Recurse -Force
        Write-Host "✓ Hooks copied" -ForegroundColor Green
    } else {
        Write-Host "○ No hooks to copy" -ForegroundColor Yellow
    }
} else {
    Write-Host "○ No hooks directory" -ForegroundColor Yellow
}

# Copy CLI wrappers
Write-Host "Copying CLI wrappers..."
$binDir = "$INSTALL_DIR\bin"
if (!(Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}
Copy-Item -Path "$REPO_DIR\bin\*" -Destination $binDir -Recurse -Force
Write-Host "✓ CLI wrappers installed" -ForegroundColor Green

# Copy API server
if (Test-Path "$REPO_DIR\api_server.py") {
    Copy-Item -Path "$REPO_DIR\api_server.py" -Destination $INSTALL_DIR -Force
    Write-Host "✓ API server copied" -ForegroundColor Green
}

# Copy config if not exists
if (!(Test-Path "$INSTALL_DIR\config.json")) {
    Write-Host "Creating default config..."
    Copy-Item -Path "$REPO_DIR\config.json" -Destination "$INSTALL_DIR\config.json" -Force
    Write-Host "✓ Config created" -ForegroundColor Green
} else {
    Write-Host "○ Config exists (keeping existing)" -ForegroundColor Yellow
}

# Create necessary directories
Write-Host ""
Write-Host "Creating directories..."
$dirs = @("backups", "profiles", "vectors", "cold-storage", "jobs")
foreach ($dir in $dirs) {
    $path = "$INSTALL_DIR\$dir"
    if (!(Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}
Write-Host "✓ Directories created" -ForegroundColor Green

# Initialize database
Write-Host ""
Write-Host "Initializing database..."
try {
    python "$INSTALL_DIR\setup_validator.py" --init 2>&1 | Out-Null
    Write-Host "✓ Database initialized" -ForegroundColor Green
} catch {
    # Fallback: create basic tables
    $initScript = @"
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
cursor.execute('CREATE TABLE IF NOT EXISTS graph_nodes (id INTEGER PRIMARY KEY, memory_id INTEGER UNIQUE, entities TEXT DEFAULT "[]", embedding_vector BLOB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS graph_edges (id INTEGER PRIMARY KEY, source_memory_id INTEGER, target_memory_id INTEGER, similarity REAL, relationship_type TEXT, shared_entities TEXT DEFAULT "[]", created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS graph_clusters (id INTEGER PRIMARY KEY, cluster_name TEXT, description TEXT, memory_count INTEGER DEFAULT 0, avg_importance REAL DEFAULT 5.0, top_entities TEXT DEFAULT "[]", created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS identity_patterns (id INTEGER PRIMARY KEY, pattern_type TEXT, pattern_key TEXT, pattern_value TEXT, confidence REAL DEFAULT 0.0, frequency INTEGER DEFAULT 1, last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS pattern_examples (id INTEGER PRIMARY KEY, pattern_id INTEGER, memory_id INTEGER, context TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS memory_tree (id INTEGER PRIMARY KEY, node_type TEXT, name TEXT, parent_id INTEGER, tree_path TEXT DEFAULT "/", depth INTEGER DEFAULT 0, memory_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS memory_archive (id INTEGER PRIMARY KEY, original_memory_id INTEGER, compressed_content TEXT, compression_type TEXT DEFAULT "tier2", original_size INTEGER, compressed_size INTEGER, archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
cursor.execute('CREATE TABLE IF NOT EXISTS system_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
cursor.execute("INSERT OR REPLACE INTO system_metadata (key, value) VALUES ('product', 'SuperLocalMemory V2'), ('author', 'Varun Pratap Bhardwaj'), ('repository', 'https://github.com/varun369/SuperLocalMemoryV2'), ('license', 'MIT'), ('schema_version', '2.0.0')")
conn.commit()
conn.close()
print('Database ready')
"@
    python -c $initScript
    Write-Host "✓ Database initialized (fallback)" -ForegroundColor Green
}

# Check optional dependencies
Write-Host ""
Write-Host "Checking optional dependencies..."
$deps = @(
    @{Name="scikit-learn"; Feature="Knowledge Graph"; Import="sklearn"},
    @{Name="numpy"; Feature="Vector Operations"; Import="numpy"},
    @{Name="python-igraph"; Feature="Clustering"; Import="igraph"},
    @{Name="fastapi"; Feature="UI Server"; Import="fastapi"}
)
foreach ($dep in $deps) {
    try {
        python -c "import $($dep.Import)" 2>&1 | Out-Null
        Write-Host "✓ $($dep.Name) ($($dep.Feature))" -ForegroundColor Green
    } catch {
        Write-Host "○ $($dep.Name) not installed (optional)" -ForegroundColor Yellow
    }
}

# Summary
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Installation Complete!                                       ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "To use CLI commands, add this to your PowerShell profile:"
Write-Host ""
Write-Host '  $env:PATH += ";$env:USERPROFILE\.claude-memory\bin"' -ForegroundColor Yellow
Write-Host ""
Write-Host "Or run: notepad `$PROFILE"
Write-Host ""
Write-Host "Available commands:"
Write-Host "  superlocalmemoryv2:remember  - Save a new memory"
Write-Host "  superlocalmemoryv2:recall    - Search memories"
Write-Host "  superlocalmemoryv2:list      - List recent memories"
Write-Host "  superlocalmemoryv2:status    - Check system status"
Write-Host "  superlocalmemoryv2:profile   - Manage memory profiles"
Write-Host "  superlocalmemoryv2:reset     - Reset memory database"
Write-Host ""
Write-Host "Quick start:"
Write-Host "  1. superlocalmemoryv2:remember 'My first memory'"
Write-Host "  2. superlocalmemoryv2:recall 'first'"
Write-Host ""
Write-Host "For optional features (Knowledge Graph, Pattern Learning):"
Write-Host "  pip install scikit-learn numpy python-igraph leidenalg"
Write-Host ""
Write-Host "For UI Server:"
Write-Host "  pip install fastapi uvicorn"
Write-Host "  python $INSTALL_DIR\api_server.py"
Write-Host ""
Write-Host "Documentation: https://github.com/varun369/SuperLocalMemoryV2" -ForegroundColor Cyan
Write-Host "Author: Varun Pratap Bhardwaj" -ForegroundColor Cyan
Write-Host ""
