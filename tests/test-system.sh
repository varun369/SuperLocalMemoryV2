#!/bin/bash
# SuperLocalMemory V2 - Comprehensive System Test
# Tests all components for production readiness

set -e  # Exit on error

VENV_PYTHON="$HOME/.claude-memory/venv/bin/python"
MEMORY_DIR="$HOME/.claude-memory"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║   SuperLocalMemory V2 - Production Readiness Test       ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

test_passed() {
    echo -e "${GREEN}✓ PASSED${NC}: $1"
    ((TESTS_PASSED++))
}

test_failed() {
    echo -e "${RED}✗ FAILED${NC}: $1"
    echo -e "  Error: $2"
    ((TESTS_FAILED++))
}

test_warning() {
    echo -e "${YELLOW}⚠ WARNING${NC}: $1"
}

echo "════════════════════════════════════════════════════════════"
echo "TEST 1: Database Schema Verification"
echo "════════════════════════════════════════════════════════════"

# Check if database exists
if [ -f "$MEMORY_DIR/memory.db" ]; then
    test_passed "Database file exists"
else
    test_failed "Database file missing" "Expected: $MEMORY_DIR/memory.db"
    exit 1
fi

# Check V2 tables exist
TABLES=$(sqlite3 "$MEMORY_DIR/memory.db" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")

for table in "memories" "memory_tree" "graph_nodes" "graph_edges" "graph_clusters" "identity_patterns" "pattern_examples" "memory_archive"; do
    if echo "$TABLES" | grep -q "^$table$"; then
        test_passed "Table '$table' exists"
    else
        test_failed "Table '$table' missing" "V2 schema incomplete"
    fi
done

# Check V2 columns in memories table
COLUMNS=$(sqlite3 "$MEMORY_DIR/memory.db" "PRAGMA table_info(memories);" | cut -d'|' -f2)

for column in "tier" "cluster_id" "tree_path" "parent_id" "depth" "category" "last_accessed" "access_count"; do
    if echo "$COLUMNS" | grep -q "^$column$"; then
        test_passed "Column 'memories.$column' exists"
    else
        test_failed "Column 'memories.$column' missing" "V2 migration incomplete"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 2: Memory Store Operations"
echo "════════════════════════════════════════════════════════════"

# Test reading memories
MEMORY_COUNT=$(sqlite3 "$MEMORY_DIR/memory.db" "SELECT COUNT(*) FROM memories;")
if [ "$MEMORY_COUNT" -gt 0 ]; then
    test_passed "Can read memories (found $MEMORY_COUNT)"
else
    test_warning "No memories found (database empty)"
fi

# Test V1 compatibility
if [ -f "$MEMORY_DIR/memory_store.py" ]; then
    if python "$MEMORY_DIR/memory_store.py" stats > /dev/null 2>&1; then
        test_passed "V1 memory_store.py works"
    else
        test_failed "V1 memory_store.py broken" "Backward compatibility issue"
    fi
else
    test_warning "V1 memory_store.py not found"
fi

# Test V2 memory store
if [ -f "$MEMORY_DIR/memory_store_v2.py" ]; then
    if "$VENV_PYTHON" "$MEMORY_DIR/memory_store_v2.py" stats > /dev/null 2>&1; then
        test_passed "V2 memory_store_v2.py works"
    else
        test_failed "V2 memory_store_v2.py broken" "Check Python syntax"
    fi
else
    test_failed "V2 memory_store_v2.py missing" "Core component not found"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 3: Graph Engine"
echo "════════════════════════════════════════════════════════════"

# Check graph engine exists
if [ ! -f "$MEMORY_DIR/graph_engine.py" ]; then
    test_failed "graph_engine.py missing" "Core component not found"
else
    # Test graph stats
    if "$VENV_PYTHON" "$MEMORY_DIR/graph_engine.py" stats > /dev/null 2>&1; then
        test_passed "Graph engine runs"

        # Check if graph data exists
        NODE_COUNT=$(sqlite3 "$MEMORY_DIR/memory.db" "SELECT COUNT(*) FROM graph_nodes;")
        EDGE_COUNT=$(sqlite3 "$MEMORY_DIR/memory.db" "SELECT COUNT(*) FROM graph_edges;")
        CLUSTER_COUNT=$(sqlite3 "$MEMORY_DIR/memory.db" "SELECT COUNT(*) FROM graph_clusters;")

        if [ "$NODE_COUNT" -gt 0 ]; then
            test_passed "Graph has nodes ($NODE_COUNT)"
        else
            test_warning "No graph nodes (run: graph_engine.py build)"
        fi

        if [ "$EDGE_COUNT" -gt 0 ]; then
            test_passed "Graph has edges ($EDGE_COUNT)"
        else
            test_warning "No graph edges (run: graph_engine.py build)"
        fi

        if [ "$CLUSTER_COUNT" -gt 0 ]; then
            test_passed "Graph has clusters ($CLUSTER_COUNT)"
        else
            test_warning "No clusters detected (run: graph_engine.py build)"
        fi
    else
        test_failed "Graph engine broken" "Check dependencies (python-igraph, leidenalg)"
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 4: Pattern Learning"
echo "════════════════════════════════════════════════════════════"

if [ ! -f "$MEMORY_DIR/pattern_learner.py" ]; then
    test_failed "pattern_learner.py missing" "Core component not found"
else
    # Test pattern learner
    if "$VENV_PYTHON" "$MEMORY_DIR/pattern_learner.py" stats > /dev/null 2>&1; then
        test_passed "Pattern learner runs"

        # Check if patterns exist
        PATTERN_COUNT=$(sqlite3 "$MEMORY_DIR/memory.db" "SELECT COUNT(*) FROM identity_patterns;")

        if [ "$PATTERN_COUNT" -gt 0 ]; then
            test_passed "Patterns learned ($PATTERN_COUNT)"
        else
            test_warning "No patterns learned (run: pattern_learner.py update)"
        fi
    else
        test_failed "Pattern learner broken" "Check Python syntax"
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 5: Tree Manager"
echo "════════════════════════════════════════════════════════════"

if [ ! -f "$MEMORY_DIR/tree_manager.py" ]; then
    test_failed "tree_manager.py missing" "Core component not found"
else
    if "$VENV_PYTHON" "$MEMORY_DIR/tree_manager.py" stats > /dev/null 2>&1; then
        test_passed "Tree manager runs"

        TREE_NODE_COUNT=$(sqlite3 "$MEMORY_DIR/memory.db" "SELECT COUNT(*) FROM memory_tree;")
        if [ "$TREE_NODE_COUNT" -gt 0 ]; then
            test_passed "Tree structure exists ($TREE_NODE_COUNT nodes)"
        else
            test_warning "No tree nodes (run: tree_manager.py build_tree)"
        fi
    else
        test_failed "Tree manager broken" "Check Python syntax"
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 6: Reset System"
echo "════════════════════════════════════════════════════════════"

if [ ! -f "$MEMORY_DIR/memory-reset.py" ]; then
    test_failed "memory-reset.py missing" "Reset utility not found"
else
    if python "$MEMORY_DIR/memory-reset.py" status > /dev/null 2>&1; then
        test_passed "Reset utility runs"
    else
        test_failed "Reset utility broken" "Check Python syntax"
    fi
fi

# Check CLI wrapper
if [ -f "$MEMORY_DIR/bin/memory-reset" ]; then
    test_passed "CLI wrapper exists (bin/memory-reset)"
else
    test_warning "CLI wrapper missing (optional)"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 7: Profile System"
echo "════════════════════════════════════════════════════════════"

if [ ! -f "$MEMORY_DIR/memory-profiles.py" ]; then
    test_failed "memory-profiles.py missing" "Profile system not found"
else
    if python "$MEMORY_DIR/memory-profiles.py" list > /dev/null 2>&1; then
        test_passed "Profile manager runs"

        # Check if profiles directory exists
        if [ -d "$MEMORY_DIR/profiles" ]; then
            test_passed "Profiles directory exists"
        else
            test_warning "Profiles directory not created yet (will auto-create)"
        fi

        # Check if config exists
        if [ -f "$MEMORY_DIR/profiles.json" ]; then
            test_passed "Profile config exists"
        else
            test_warning "Profile config not created yet (will auto-create)"
        fi
    else
        test_failed "Profile manager broken" "Check Python syntax"
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 8: Compression System"
echo "════════════════════════════════════════════════════════════"

if [ ! -f "$MEMORY_DIR/memory_compression.py" ]; then
    test_warning "memory_compression.py not found (optional)"
else
    if "$VENV_PYTHON" "$MEMORY_DIR/memory_compression.py" --help > /dev/null 2>&1; then
        test_passed "Compression system exists"
    else
        test_warning "Compression system may need fixes"
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 9: Dependencies"
echo "════════════════════════════════════════════════════════════"

# Check Python version
PYTHON_VERSION=$("$VENV_PYTHON" --version 2>&1)
if [ $? -eq 0 ]; then
    test_passed "Python accessible ($PYTHON_VERSION)"
else
    test_failed "Python not found" "Check venv installation"
fi

# Check critical dependencies
for package in "sklearn" "numpy" "igraph" "leidenalg"; do
    if "$VENV_PYTHON" -c "import $package" 2>/dev/null; then
        test_passed "Package '$package' installed"
    else
        test_failed "Package '$package' missing" "Run: pip install $package"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 10: Documentation"
echo "════════════════════════════════════════════════════════════"

# Check key documentation files
for doc in "docs/README.md" "docs/COMPREHENSIVE-ARCHITECTURE.md" "RESET-GUIDE.md" "PROFILES-GUIDE.md" "CLI-COMMANDS-SETUP.md"; do
    if [ -f "$MEMORY_DIR/$doc" ]; then
        test_passed "Documentation: $doc"
    else
        test_warning "Documentation missing: $doc"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 11: Backup System"
echo "════════════════════════════════════════════════════════════"

if [ -d "$MEMORY_DIR/backups" ]; then
    test_passed "Backup directory exists"

    BACKUP_COUNT=$(ls -1 "$MEMORY_DIR/backups"/*.db 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        test_passed "Backups available ($BACKUP_COUNT)"
    else
        test_warning "No backups yet (will create on first reset)"
    fi
else
    test_warning "Backup directory not created yet (will auto-create)"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                    TEST SUMMARY                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CRITICAL TESTS PASSED${NC}"
    echo ""
    echo "SuperLocalMemory V2 is PRODUCTION READY!"
    echo ""
    echo "Next steps:"
    echo "  1. Start using /remember and /recall in Claude CLI"
    echo "  2. Build graph: $VENV_PYTHON $MEMORY_DIR/graph_engine.py build"
    echo "  3. Learn patterns: $VENV_PYTHON $MEMORY_DIR/pattern_learner.py update"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Please fix the failed tests before using in production."
    echo "Check errors above for details."
    echo ""
    exit 1
fi
