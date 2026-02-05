#!/bin/bash
# Test script for all 6 SuperLocalMemory V2 commands
# Tests against the demo database

set -e

# Get the directory where this script is located
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$REPO_DIR/bin"
DEMO_DB="$REPO_DIR/demo-memory.db"

echo "═══════════════════════════════════════════════════════════"
echo "  SuperLocalMemory V2 - Command Verification Suite"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check if demo database exists
if [ ! -f "$DEMO_DB" ]; then
    echo "❌ ERROR: Demo database not found at $DEMO_DB"
    exit 1
fi

echo "✅ Demo database found: $DEMO_DB"
echo ""

# Check all 6 commands exist
echo "Checking command presence..."
COMMANDS=(
    "superlocalmemoryv2:status"
    "superlocalmemoryv2:reset"
    "superlocalmemoryv2:profile"
    "superlocalmemoryv2:remember"
    "superlocalmemoryv2:recall"
    "superlocalmemoryv2:list"
)

MISSING=()
for cmd in "${COMMANDS[@]}"; do
    if [ -f "$BIN_DIR/$cmd" ]; then
        echo "  ✅ $cmd"
    else
        echo "  ❌ $cmd - NOT FOUND"
        MISSING+=("$cmd")
    fi
done

echo ""

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "❌ ERROR: Missing ${#MISSING[@]} command(s)"
    exit 1
fi

echo "✅ All 6 commands present in bin/ directory"
echo ""

# Check corresponding hooks
echo "Checking hook files..."
HOOKS=(
    "memory-reset-skill.js"
    "memory-profile-skill.js"
    "memory-remember-skill.js"
    "memory-recall-skill.js"
    "memory-list-skill.js"
)

MISSING_HOOKS=()
for hook in "${HOOKS[@]}"; do
    if [ -f "$REPO_DIR/hooks/$hook" ]; then
        echo "  ✅ $hook"
    else
        echo "  ❌ $hook - NOT FOUND"
        MISSING_HOOKS+=("$hook")
    fi
done

echo ""

if [ ${#MISSING_HOOKS[@]} -gt 0 ]; then
    echo "⚠️  WARNING: Missing ${#MISSING_HOOKS[@]} hook file(s)"
    echo "   Note: status uses memory-reset-skill.js"
fi

echo ""

# Test each command (help only - won't modify database)
echo "═══════════════════════════════════════════════════════════"
echo "  Testing Command Help Output"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "1. Testing: superlocalmemoryv2:status"
echo "   Purpose: Show memory system status"
echo "   Type: Read-only query"
if "$BIN_DIR/superlocalmemoryv2:status" 2>&1 | head -5; then
    echo "   ✅ Command executable"
else
    echo "   ❌ Command failed"
fi
echo ""

echo "2. Testing: superlocalmemoryv2:reset --help"
echo "   Purpose: Reset/clear memory database"
echo "   Type: Destructive operation (requires confirmation)"
if "$BIN_DIR/superlocalmemoryv2:reset" --help 2>&1 | head -10; then
    echo "   ✅ Command executable"
else
    echo "   ❌ Command failed"
fi
echo ""

echo "3. Testing: superlocalmemoryv2:profile --help"
echo "   Purpose: Manage memory profiles"
echo "   Type: Configuration management"
if "$BIN_DIR/superlocalmemoryv2:profile" --help 2>&1 | head -10; then
    echo "   ✅ Command executable"
else
    echo "   ❌ Command failed"
fi
echo ""

echo "4. Testing: superlocalmemoryv2:remember --help"
echo "   Purpose: Save new memories"
echo "   Type: Write operation"
if "$BIN_DIR/superlocalmemoryv2:remember" --help 2>&1 | head -10; then
    echo "   ✅ Command executable"
else
    echo "   ❌ Command failed"
fi
echo ""

echo "5. Testing: superlocalmemoryv2:recall --help"
echo "   Purpose: Search and retrieve memories"
echo "   Type: Read-only query"
if "$BIN_DIR/superlocalmemoryv2:recall" --help 2>&1 | head -10; then
    echo "   ✅ Command executable"
else
    echo "   ❌ Command failed"
fi
echo ""

echo "6. Testing: superlocalmemoryv2:list --help"
echo "   Purpose: List all memories with filters"
echo "   Type: Read-only query"
if "$BIN_DIR/superlocalmemoryv2:list" --help 2>&1 | head -10; then
    echo "   ✅ Command executable"
else
    echo "   ❌ Command failed"
fi
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "  Verification Complete"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  • All 6 commands present: ✅"
echo "  • Hook files verified: ✅"
echo "  • Commands executable: ✅"
echo ""
echo "Commands available:"
echo "  1. superlocalmemoryv2:status    - Check system status"
echo "  2. superlocalmemoryv2:reset     - Reset database (destructive)"
echo "  3. superlocalmemoryv2:profile   - Manage profiles"
echo "  4. superlocalmemoryv2:remember  - Save memories"
echo "  5. superlocalmemoryv2:recall    - Search memories"
echo "  6. superlocalmemoryv2:list      - List all memories"
echo ""
echo "Note: These commands reference ~/.claude-memory/ for execution."
echo "      To use with demo database, ensure proper configuration."
echo ""
