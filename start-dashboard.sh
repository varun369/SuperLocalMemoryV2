#!/bin/bash
# ============================================================================
# SuperLocalMemory V2.2.0 - Dashboard Startup Script
# Starts the web dashboard on http://localhost:8765
# Copyright (c) 2026 Varun Pratap Bhardwaj
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  SuperLocalMemory V2.2.0 - Dashboard                         ║"
echo "║  by Varun Pratap Bhardwaj                                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if FastAPI is installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  FastAPI not installed (optional dependency)"
    echo ""
    echo "To use the dashboard, install web dependencies:"
    echo "  pip3 install -r requirements-ui.txt"
    echo ""
    echo "Or install all features:"
    echo "  pip3 install -r requirements-full.txt"
    echo ""
    exit 1
fi

echo "🚀 Starting dashboard server..."
echo ""
echo "   Dashboard: http://localhost:8765"
echo "   API Docs:  http://localhost:8765/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start server
python3 ui_server.py
