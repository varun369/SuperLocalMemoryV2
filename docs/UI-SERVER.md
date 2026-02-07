# SuperLocalMemory V2 - UI Server

Web-based visualization interface for exploring the SuperLocalMemory knowledge graph.

## Features

### 8 REST API Endpoints

1. **GET /api/memories** - List memories with filtering (category, project, cluster, importance)
2. **GET /api/graph** - Graph data for D3.js force-directed visualization
3. **GET /api/clusters** - Cluster information with themes and members
4. **GET /api/patterns** - Learned user preferences and coding patterns
5. **GET /api/stats** - System statistics overview
6. **POST /api/search** - Semantic search using TF-IDF similarity
7. **GET /api/timeline** - Temporal view of memory creation
8. **GET /api/tree** - Hierarchical tree structure

### UI Features

- **Knowledge Graph**: Interactive D3.js force-directed graph showing memory relationships
- **Memory Browser**: Searchable table with filtering by category/project
- **Cluster Analysis**: Visual breakdown of thematic clusters with top entities
- **Pattern Viewer**: Display learned preferences and coding styles
- **Timeline**: Chart showing memory creation over time
- **Statistics Dashboard**: Real-time system metrics

## Quick Start

### 1. Install Dependencies

```bash
cd ~/Documents/AGENTIC_Official/SuperLocalMemoryV2-repo
pip install -r requirements-ui.txt
```

### 2. Ensure Memory Database Exists

The UI server requires an existing memory database. If you haven't created one yet:

```bash
# Create demo database with sample data
python create_demo_db.py

# OR use your existing ~/.claude-memory/memory.db
```

### 3. Start the Server

```bash
python ui_server.py
```

The server will start on **http://localhost:8000**

### 4. Open UI

Navigate to: **http://localhost:8000**

Interactive API documentation: **http://localhost:8000/docs**

## Usage

### Exploring the Knowledge Graph

1. Click **Knowledge Graph** tab
2. Hover over nodes to see memory details
3. Drag nodes to rearrange the layout
4. Change max nodes using the dropdown (50/100/200)

Node colors represent different clusters. Node size represents importance.

### Searching Memories

1. Click **Memories** tab
2. Enter search query in the search box
3. Or use filters: category, project
4. View results in the table

### Analyzing Clusters

1. Click **Clusters** tab
2. View thematic groupings of related memories
3. Top entities show dominant concepts in each cluster

### Viewing Learned Patterns

1. Click **Patterns** tab
2. See extracted preferences (tech stack, coding style, etc.)
3. Confidence % shows pattern strength

### Timeline Analysis

1. Click **Timeline** tab
2. View memory creation over last 30 days
3. Identify activity patterns

## API Examples

### Get Memories (with filters)

```bash
curl "http://localhost:8000/api/memories?category=Frontend&limit=10"
```

### Search Memories

```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "react components", "limit": 10, "min_score": 0.3}'
```

### Get Graph Data

```bash
curl "http://localhost:8000/api/graph?max_nodes=100"
```

### Get Statistics

```bash
curl "http://localhost:8000/api/stats"
```

## Configuration

### Database Path

By default, the server uses:
- Demo mode: `demo-memory.db` in the repo
- Production: `~/.claude-memory/memory.db`

To change the database path, modify `DB_PATH` in `ui_server.py`.

### Server Port

To change the port from 8000:

```python
# In ui_server.py, line ~650
uvicorn.run(app, host="0.0.0.0", port=8080)  # Change 8000 to 8080
```

Or use command line:

```bash
uvicorn api_server:app --port 8080
```

### CORS (for external access)

If accessing from a different domain, add CORS middleware:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Architecture

```
ui_server.py           # FastAPI backend (8 endpoints)
ui/
  ├── index.html        # Single-page UI
  └── app.js            # Frontend JavaScript (D3.js + Bootstrap)
```

### Tech Stack

**Backend:**
- FastAPI - Modern Python web framework
- Uvicorn - ASGI server
- SQLite - Database queries

**Frontend:**
- Bootstrap 5 - UI framework
- D3.js v7 - Force-directed graph visualization
- Vanilla JavaScript - No build step required

## Troubleshooting

### Server won't start

**Error: `Memory database not found`**

Solution: Create database first:
```bash
python create_demo_db.py
```

**Error: `ModuleNotFoundError: No module named 'fastapi'`**

Solution: Install requirements:
```bash
pip install -r requirements-ui.txt
```

### Graph not displaying

Check browser console for errors. Common issues:
- Database has no graph data (run graph engine first)
- No memories with cluster_id set

To build graph:
```bash
python -c "from src.graph_engine import GraphEngine; GraphEngine().build_graph()"
```

### Search returns no results

TF-IDF search requires:
1. Multiple memories in database
2. Diverse vocabulary
3. Query matching content keywords

Try broader search terms or check if vectors are built.

## Performance Notes

- **Graph rendering**: Limited to 200 nodes max to ensure smooth interaction
- **Memory list**: Paginated (50 per page default)
- **Search**: O(n) vector similarity, fast for <10k memories
- **Timeline**: Cached for 5 minutes

## Security

This UI server is intended for **local development** only.

**Do NOT expose to public internet without:**
- Authentication (OAuth, API keys)
- Input validation and sanitization
- Rate limiting
- HTTPS/TLS

## Next Steps

- Add authentication for multi-user access
- Implement real-time updates via WebSockets
- Add export functionality (JSON, CSV)
- Create memory editing interface
- Build cluster visualization with hierarchical layout

## Support

For issues or questions:
1. Check the main README: `README.md`
2. Review architecture docs: `docs/architecture/`
3. Examine demo: `DEMO_QUICKSTART.md`
