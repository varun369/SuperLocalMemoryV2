# ============================================================================
# SuperLocalMemory V2.2.0 - Windows Installation Script (PowerShell)
# Copyright (c) 2026 Varun Pratap Bhardwaj
# Licensed under MIT License
# Repository: https://github.com/varun369/SuperLocalMemoryV2
# ============================================================================

$ErrorActionPreference = "Stop"

$INSTALL_DIR = Join-Path $env:USERPROFILE ".claude-memory"
$REPO_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# Auto-detect non-interactive environment
$NON_INTERACTIVE = $false
if (-not [Environment]::UserInteractive) {
    $NON_INTERACTIVE = $true
}

# Parse command line arguments
param(
    [switch]$NonInteractive,
    [switch]$Auto,
    [switch]$Yes,
    [switch]$y
)

if ($NonInteractive -or $Auto -or $Yes -or $y) {
    $NON_INTERACTIVE = $true
}

# Print banner
Write-Host ""
Write-Host "=================================================================="
Write-Host "  SuperLocalMemory V2.2.0 - Windows Installation                 "
Write-Host "  by Varun Pratap Bhardwaj                                       "
Write-Host "  https://github.com/varun369/SuperLocalMemoryV2                 "
Write-Host "=================================================================="
Write-Host ""

# Show mode if non-interactive
if ($NON_INTERACTIVE) {
    Write-Host "🤖 Running in non-interactive mode" -ForegroundColor Cyan
    Write-Host "   Skipping optional prompts, using defaults" -ForegroundColor Cyan
    Write-Host ""
}

# Check Python version
Write-Host "Checking Python version..."
try {
    $PYTHON_VERSION = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
    $PYTHON_MAJOR = & python -c "import sys; print(sys.version_info.major)" 2>&1
    $PYTHON_MINOR = & python -c "import sys; print(sys.version_info.minor)" 2>&1

    if ([int]$PYTHON_MAJOR -lt 3 -or ([int]$PYTHON_MAJOR -eq 3 -and [int]$PYTHON_MINOR -lt 8)) {
        Write-Host "ERROR: Python 3.8+ required (found $PYTHON_VERSION)" -ForegroundColor Red
        exit 1
    }
    Write-Host "OK Python $PYTHON_VERSION" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found in PATH" -ForegroundColor Red
    Write-Host "Install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    exit 1
}

# Create installation directory
Write-Host ""
Write-Host "Creating installation directory..."
if (-not (Test-Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
}
Write-Host "OK Directory: $INSTALL_DIR" -ForegroundColor Green

# Copy source files
Write-Host ""
Write-Host "Copying source files..."
$srcDir = Join-Path $REPO_DIR "src"
if (Test-Path $srcDir) {
    Copy-Item -Path (Join-Path $srcDir "*") -Destination $INSTALL_DIR -Recurse -Force
    Write-Host "OK Source files copied" -ForegroundColor Green
} else {
    Write-Host "WARNING: Source directory not found, skipping" -ForegroundColor Yellow
}

# Copy hooks
Write-Host "Copying hooks..."
$hooksDir = Join-Path $REPO_DIR "hooks"
$installHooksDir = Join-Path $INSTALL_DIR "hooks"
if (-not (Test-Path $installHooksDir)) {
    New-Item -ItemType Directory -Path $installHooksDir -Force | Out-Null
}
if (Test-Path $hooksDir) {
    Copy-Item -Path (Join-Path $hooksDir "*") -Destination $installHooksDir -Recurse -Force
    Write-Host "OK Hooks copied" -ForegroundColor Green
} else {
    Write-Host "INFO: No hooks to copy" -ForegroundColor Yellow
}

# Copy CLI wrappers
Write-Host "Copying CLI wrappers..."
$binDir = Join-Path $REPO_DIR "bin"
$installBinDir = Join-Path $INSTALL_DIR "bin"
if (-not (Test-Path $installBinDir)) {
    New-Item -ItemType Directory -Path $installBinDir -Force | Out-Null
}
if (Test-Path $binDir) {
    Copy-Item -Path (Join-Path $binDir "*") -Destination $installBinDir -Recurse -Force
    Write-Host "OK CLI wrappers installed" -ForegroundColor Green
}

# Copy API server
$apiServerPath = Join-Path $REPO_DIR "api_server.py"
if (Test-Path $apiServerPath) {
    Copy-Item -Path $apiServerPath -Destination $INSTALL_DIR -Force
    Write-Host "OK API server copied" -ForegroundColor Green
}

# Copy UI server
$uiServerPath = Join-Path $REPO_DIR "ui_server.py"
if (Test-Path $uiServerPath) {
    Copy-Item -Path $uiServerPath -Destination $INSTALL_DIR -Force
    Write-Host "OK UI server copied" -ForegroundColor Green
}

# Copy MCP server
$mcpServerPath = Join-Path $REPO_DIR "mcp_server.py"
if (Test-Path $mcpServerPath) {
    Copy-Item -Path $mcpServerPath -Destination $INSTALL_DIR -Force
    Write-Host "OK MCP Server installed" -ForegroundColor Green
}

# Copy config if not exists
$configPath = Join-Path $INSTALL_DIR "config.json"
if (-not (Test-Path $configPath)) {
    Write-Host "Creating default config..."
    $repoConfigPath = Join-Path $REPO_DIR "config.json"
    if (Test-Path $repoConfigPath) {
        Copy-Item -Path $repoConfigPath -Destination $configPath -Force
        Write-Host "OK Config created" -ForegroundColor Green
    } else {
        Write-Host "WARNING: config.json not found, using defaults" -ForegroundColor Yellow
    }
} else {
    Write-Host "INFO: Config exists (keeping existing)" -ForegroundColor Yellow
}

# Create necessary directories
Write-Host ""
Write-Host "Creating directories..."
$directories = @("backups", "profiles", "vectors", "cold-storage", "jobs")
foreach ($dir in $directories) {
    $dirPath = Join-Path $INSTALL_DIR $dir
    if (-not (Test-Path $dirPath)) {
        New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
    }
}
Write-Host "OK Directories created" -ForegroundColor Green

# Initialize database
Write-Host ""
Write-Host "Initializing database..."
$setupValidatorPath = Join-Path $INSTALL_DIR "setup_validator.py"
if (Test-Path $setupValidatorPath) {
    try {
        & python $setupValidatorPath --init 2>$null | Out-Null
        Write-Host "OK Database initialized" -ForegroundColor Green
    } catch {
        Write-Host "WARNING: Database init failed, creating basic schema..." -ForegroundColor Yellow
        # Fallback: create basic database
        & python -c @"
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
    cluster_id INTEGER
)''')
cursor.execute('CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT UNIQUE, project_path TEXT, started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, ended_at TIMESTAMP, summary TEXT)')
conn.commit()
conn.close()
print('Database ready')
"@
        Write-Host "OK Database initialized (fallback)" -ForegroundColor Green
    }
} else {
    Write-Host "WARNING: setup_validator.py not found, skipping database init" -ForegroundColor Yellow
}

# Install core dependencies (required for graph & dashboard)
Write-Host ""
Write-Host "Installing core dependencies..."
Write-Host "INFO: This ensures graph visualization and patterns work out-of-box" -ForegroundColor Yellow

$coreRequirements = Join-Path $REPO_DIR "requirements-core.txt"
if (Test-Path $coreRequirements) {
    try {
        & python -m pip install -q -r $coreRequirements 2>$null
        Write-Host "OK Core dependencies installed (graph, dashboard, patterns)" -ForegroundColor Green
    } catch {
        Write-Host "WARNING: Core dependency installation failed. Some features may not work." -ForegroundColor Yellow
        Write-Host "   Install manually: python -m pip install -r $coreRequirements" -ForegroundColor Yellow
    }
} else {
    Write-Host "WARNING: requirements-core.txt not found, skipping dependency installation" -ForegroundColor Yellow
}

# Initialize knowledge graph and pattern learning
Write-Host ""
Write-Host "Initializing advanced features..."

# Add sample memories if database is empty (for first-time users)
$memoryCount = & python -c @"
import sqlite3
from pathlib import Path
db_path = Path.home() / '.claude-memory' / 'memory.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM memories')
print(cursor.fetchone()[0])
conn.close()
"@ 2>$null

if (-not $memoryCount) { $memoryCount = 0 }

if ([int]$memoryCount -eq 0) {
    Write-Host "INFO: Adding sample memories for demonstration..." -ForegroundColor Yellow
    & python "$INSTALL_DIR\memory_store_v2.py" add "SuperLocalMemory V2 is a local-first, privacy-focused memory system for AI assistants. All data stays on your machine." --tags "supermemory,system,intro" --importance 8 2>$null | Out-Null
    & python "$INSTALL_DIR\memory_store_v2.py" add "Knowledge graph uses TF-IDF for entity extraction and Leiden clustering for community detection." --tags "architecture,graph" --importance 7 2>$null | Out-Null
    & python "$INSTALL_DIR\memory_store_v2.py" add "Pattern learning analyzes your coding preferences, style, and terminology to provide better context." --tags "architecture,patterns" --importance 7 2>$null | Out-Null
}

# Build knowledge graph (Layer 3)
Write-Host "INFO: Building knowledge graph..." -ForegroundColor Yellow
try {
    & python "$INSTALL_DIR\graph_engine.py" build 2>$null | Out-Null
    Write-Host "  OK Knowledge graph initialized" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Graph build skipped (dependencies not installed)" -ForegroundColor Yellow
}

# Run pattern learning (Layer 4)
Write-Host "INFO: Learning patterns..." -ForegroundColor Yellow
try {
    & python "$INSTALL_DIR\pattern_learner.py" update 2>$null | Out-Null
    $patternCount = & python -c @"
import sqlite3
from pathlib import Path
db_path = Path.home() / '.claude-memory' / 'memory.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM identity_patterns')
count = cursor.fetchone()[0]
conn.close()
print(count)
"@ 2>$null
    if (-not $patternCount) { $patternCount = 0 }
    Write-Host "  OK Pattern learning complete ($patternCount patterns found)" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Pattern learning skipped (dependencies not installed)" -ForegroundColor Yellow
}

# Check optional dependencies
Write-Host ""
Write-Host "Checking optional dependencies..."
$dependencies = @{
    "sklearn" = "scikit-learn (Knowledge Graph)"
    "numpy" = "numpy (Vector Operations)"
    "igraph" = "python-igraph (Clustering)"
    "fastapi" = "fastapi (UI Server)"
}

foreach ($module in $dependencies.Keys) {
    try {
        & python -c "import $module" 2>$null
        Write-Host "OK $($dependencies[$module])" -ForegroundColor Green
    } catch {
        Write-Host "INFO: $($dependencies[$module]) not installed (optional)" -ForegroundColor Yellow
    }
}

# Configure PATH
Write-Host ""
Write-Host "Configuring PATH..."
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$installBinDir*") {
    $newPath = "$installBinDir;$userPath"
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    Write-Host "OK PATH configured (restart terminal to use commands)" -ForegroundColor Green
    $env:PATH = "$installBinDir;$env:PATH"
} else {
    Write-Host "INFO: PATH already configured" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "=================================================================="
Write-Host "  Installation Complete!                                         "
Write-Host "=================================================================="
Write-Host ""
Write-Host "OK Commands available after terminal restart!" -ForegroundColor Green
Write-Host ""
Write-Host "Quick start (restart terminal first):"
Write-Host "  python $INSTALL_DIR\memory_store_v2.py"
Write-Host ""

# Optional: Offer to install optional features
Write-Host ""
Write-Host "=================================================================="
Write-Host "  Optional Features Available                                    "
Write-Host "=================================================================="
Write-Host ""
Write-Host "SuperLocalMemory V2.2.0 includes optional features:"
Write-Host ""
Write-Host "  1) Advanced Search (~1.5GB, 5-10 min)"
Write-Host "     - Semantic search with sentence transformers"
Write-Host "     - Vector similarity with HNSWLIB"
Write-Host ""
Write-Host "  2) Web Dashboard (~50MB, 1-2 min)"
Write-Host "     - Graph visualization"
Write-Host "     - API server (FastAPI)"
Write-Host ""
Write-Host "  3) Full Package (~1.5GB, 5-10 min)"
Write-Host "     - Everything: Search + Dashboard"
Write-Host ""
Write-Host "  N) Skip (install later)"
Write-Host ""

# Handle interactive vs non-interactive mode
if ($NON_INTERACTIVE) {
    $INSTALL_CHOICE = "N"
    Write-Host "Auto-selecting: N (Skip)" -ForegroundColor Cyan
} else {
    $INSTALL_CHOICE = Read-Host "Choose option [1/2/3/N]"
}

$requirementsDir = $REPO_DIR
switch ($INSTALL_CHOICE) {
    "1" {
        Write-Host ""
        Write-Host "Installing Advanced Search features..."
        Write-Host "Downloading ~1.5GB (ML models)..." -ForegroundColor Yellow
        $searchReqPath = Join-Path $requirementsDir "requirements-search.txt"
        if (Test-Path $searchReqPath) {
            & pip install -r $searchReqPath
            Write-Host "OK Advanced Search installed successfully" -ForegroundColor Green
        } else {
            Write-Host "ERROR: requirements-search.txt not found" -ForegroundColor Red
        }
    }
    "2" {
        Write-Host ""
        Write-Host "Installing Web Dashboard..."
        Write-Host "Downloading ~50MB..." -ForegroundColor Yellow
        $uiReqPath = Join-Path $requirementsDir "requirements-ui.txt"
        if (Test-Path $uiReqPath) {
            & pip install -r $uiReqPath
            Write-Host "OK Web Dashboard installed successfully" -ForegroundColor Green
            Write-Host ""
            Write-Host "Start Web UI:"
            Write-Host "  python $INSTALL_DIR\api_server.py"
            Write-Host "  Then open: http://127.0.0.1:8000"
        } else {
            Write-Host "ERROR: requirements-ui.txt not found" -ForegroundColor Red
        }
    }
    "3" {
        Write-Host ""
        Write-Host "Installing Full Package (Search + Dashboard)..."
        Write-Host "Downloading ~1.5GB..." -ForegroundColor Yellow
        $fullReqPath = Join-Path $requirementsDir "requirements-full.txt"
        if (Test-Path $fullReqPath) {
            & pip install -r $fullReqPath
            Write-Host "OK Full package installed successfully" -ForegroundColor Green
            Write-Host ""
            Write-Host "All features enabled!"
        } else {
            Write-Host "ERROR: requirements-full.txt not found" -ForegroundColor Red
        }
    }
    default {
        Write-Host ""
        Write-Host "Skipping optional features."
        Write-Host ""
        Write-Host "To install later:"
        Write-Host "  Advanced Search: pip install -r requirements-search.txt"
        Write-Host "  Web Dashboard:   pip install -r requirements-ui.txt"
        Write-Host "  Full Package:    pip install -r requirements-full.txt"
    }
}

Write-Host ""
Write-Host "=================================================================="
Write-Host "  ATTRIBUTION NOTICE (REQUIRED BY MIT LICENSE)                   "
Write-Host "=================================================================="
Write-Host "  Created by: Varun Pratap Bhardwaj                              "
Write-Host "  Role: Solution Architect & Original Creator                    "
Write-Host "  Repository: github.com/varun369/SuperLocalMemoryV2             "
Write-Host "  License: MIT (attribution must be preserved)                   "
Write-Host "=================================================================="
Write-Host ""
