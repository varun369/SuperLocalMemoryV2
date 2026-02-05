#!/bin/bash
# SuperLocalMemory V2 - UI Server Startup Script

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$REPO_DIR"

echo "=================================================="
echo "SuperLocalMemory V2 - UI Server"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment not found."
    echo "Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements-ui.txt"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if database exists
if [ -f "demo-memory.db" ]; then
    echo "✓ Using demo database: demo-memory.db"
elif [ -f "$HOME/.claude-memory/memory.db" ]; then
    echo "✓ Using production database: ~/.claude-memory/memory.db"
else
    echo "⚠ WARNING: No memory database found!"
    echo ""
    echo "To create a demo database, run:"
    echo "  python create_demo_db.py"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check dependencies
echo ""
echo "Checking dependencies..."
python -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠ Installing missing dependencies..."
    pip install -q -r requirements-ui.txt
fi

echo "✓ Dependencies OK"
echo ""
echo "=================================================="
echo "Starting UI server on http://localhost:8000"
echo "=================================================="
echo ""
echo "Available endpoints:"
echo "  • Main UI:        http://localhost:8000"
echo "  • API Docs:       http://localhost:8000/docs"
echo "  • Stats:          http://localhost:8000/api/stats"
echo "  • Knowledge Graph: http://localhost:8000/api/graph"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start server
python api_server.py
