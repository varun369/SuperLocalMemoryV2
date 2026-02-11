#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Intelligent Local Memory System
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Repository: https://github.com/varun369/SuperLocalMemoryV2
Author: Varun Pratap Bhardwaj (Solution Architect)

NOTICE: This software is protected by MIT License.
Attribution must be preserved in all copies or derivatives.
"""

"""
SuperLocalMemory V2.2.0 - FastAPI UI Server with WebSocket Support
Comprehensive REST and WebSocket API for memory visualization and real-time updates.

Features:
- Full REST API for memory CRUD operations
- WebSocket support for real-time memory updates
- Profile management and switching
- Import/Export functionality
- Advanced search with filters
- Cluster detail views
- Timeline aggregation (day/week/month)
- CORS enabled for cross-origin requests
- Response compression
- Comprehensive error handling
"""

import sqlite3
import json
import asyncio
import gzip
import io
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict

try:
    from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, UploadFile, File
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.gzip import GZipMiddleware
    from pydantic import BaseModel, Field, validator
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    raise ImportError(
        "FastAPI dependencies not installed. "
        "Install with: pip install 'fastapi[all]' uvicorn websockets"
    )

# Import local modules
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from memory_store_v2 import MemoryStoreV2
from graph_engine import GraphEngine
from pattern_learner import PatternLearner

# Configuration
MEMORY_DIR = Path.home() / ".claude-memory"
DB_PATH = MEMORY_DIR / "memory.db"
UI_DIR = Path(__file__).parent / "ui"
PROFILES_DIR = MEMORY_DIR / "profiles"

# Initialize FastAPI application
app = FastAPI(
    title="SuperLocalMemory V2.2.0 UI Server",
    description="Knowledge Graph Visualization with Real-Time Updates",
    version="2.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware (for web UI development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected clients
        self.active_connections -= disconnected

manager = ConnectionManager()

# Mount static files (UI directory)
UI_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


# ============================================================================
# Profile Helper
# ============================================================================

def get_active_profile() -> str:
    """Read the active profile from profiles.json. Falls back to 'default'."""
    config_file = MEMORY_DIR / "profiles.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                pconfig = json.load(f)
            return pconfig.get('active_profile', 'default')
        except (json.JSONDecodeError, IOError):
            pass
    return 'default'


# ============================================================================
# Request/Response Models
# ============================================================================

class SearchRequest(BaseModel):
    """Advanced search request model."""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)
    category: Optional[str] = None
    project_name: Optional[str] = None
    cluster_id: Optional[int] = None
    date_from: Optional[str] = None  # ISO format: YYYY-MM-DD
    date_to: Optional[str] = None

class MemoryFilter(BaseModel):
    """Memory filtering options."""
    category: Optional[str] = None
    project_name: Optional[str] = None
    cluster_id: Optional[int] = None
    min_importance: Optional[int] = Field(None, ge=1, le=10)
    tags: Optional[List[str]] = None

class ProfileSwitch(BaseModel):
    """Profile switching request."""
    profile_name: str = Field(..., min_length=1, max_length=50)

class TimelineParams(BaseModel):
    """Timeline aggregation parameters."""
    days: int = Field(default=30, ge=1, le=365)
    group_by: str = Field(default="day", pattern="^(day|week|month)$")


# ============================================================================
# Database Helper Functions
# ============================================================================

def get_db_connection():
    """Get database connection with attribution header."""
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="Memory database not found. Run 'memory-init' to initialize."
        )
    return sqlite3.connect(DB_PATH)

def dict_factory(cursor, row):
    """Convert SQLite row to dictionary."""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

def validate_profile_name(name: str) -> bool:
    """Validate profile name (alphanumeric, underscore, hyphen only)."""
    import re
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))


# ============================================================================
# API Endpoints - Basic Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main UI page."""
    index_path = UI_DIR / "index.html"
    if not index_path.exists():
        return """
        <!DOCTYPE html>
        <html>
            <head>
                <title>SuperLocalMemory V2.2.0</title>
                <meta charset="utf-8">
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                        padding: 40px;
                        max-width: 1200px;
                        margin: 0 auto;
                        background: #f5f5f5;
                    }
                    .header {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 30px;
                        border-radius: 8px;
                        margin-bottom: 30px;
                    }
                    h1 { margin: 0; font-size: 2em; }
                    h2 { color: #333; margin-top: 30px; }
                    ul { line-height: 1.8; }
                    a { color: #667eea; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                    .endpoint {
                        background: white;
                        padding: 10px 15px;
                        margin: 5px 0;
                        border-radius: 4px;
                        border-left: 3px solid #667eea;
                    }
                    .badge {
                        display: inline-block;
                        padding: 3px 8px;
                        background: #667eea;
                        color: white;
                        border-radius: 3px;
                        font-size: 0.8em;
                        margin-left: 10px;
                    }
                    footer {
                        margin-top: 50px;
                        padding-top: 20px;
                        border-top: 2px solid #ddd;
                        color: #666;
                        text-align: center;
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>SuperLocalMemory V2.2.0 UI Server</h1>
                    <p>FastAPI Backend with WebSocket Support</p>
                </div>

                <h2>Available Endpoints</h2>

                <div class="endpoint">
                    <a href="/api/docs">/api/docs</a>
                    <span class="badge">Interactive</span>
                    <p>Swagger UI - Interactive API Documentation</p>
                </div>

                <div class="endpoint">
                    <a href="/api/stats">/api/stats</a>
                    <span class="badge">GET</span>
                    <p>System statistics and overview</p>
                </div>

                <div class="endpoint">
                    <a href="/api/memories">/api/memories</a>
                    <span class="badge">GET</span>
                    <p>List and filter memories</p>
                </div>

                <div class="endpoint">
                    <a href="/api/graph">/api/graph</a>
                    <span class="badge">GET</span>
                    <p>Knowledge graph data for visualization</p>
                </div>

                <div class="endpoint">
                    <a href="/api/timeline">/api/timeline</a>
                    <span class="badge">GET</span>
                    <p>Timeline view with day/week/month aggregation</p>
                </div>

                <div class="endpoint">
                    <a href="/api/patterns">/api/patterns</a>
                    <span class="badge">GET</span>
                    <p>Learned patterns and preferences</p>
                </div>

                <div class="endpoint">
                    <a href="/api/clusters">/api/clusters</a>
                    <span class="badge">GET</span>
                    <p>Cluster information and themes</p>
                </div>

                <div class="endpoint">
                    /api/clusters/{id} <span class="badge">GET</span>
                    <p>Detailed cluster view with members</p>
                </div>

                <div class="endpoint">
                    /api/search <span class="badge">POST</span>
                    <p>Advanced semantic search</p>
                </div>

                <div class="endpoint">
                    <a href="/api/profiles">/api/profiles</a>
                    <span class="badge">GET</span>
                    <p>List available memory profiles</p>
                </div>

                <div class="endpoint">
                    /api/profiles/{name}/switch <span class="badge">POST</span>
                    <p>Switch active memory profile</p>
                </div>

                <div class="endpoint">
                    <a href="/api/export">/api/export</a>
                    <span class="badge">GET</span>
                    <p>Export memories as JSON</p>
                </div>

                <div class="endpoint">
                    /api/import <span class="badge">POST</span>
                    <p>Import memories from JSON file</p>
                </div>

                <div class="endpoint">
                    /ws/updates <span class="badge">WebSocket</span>
                    <p>Real-time memory updates stream</p>
                </div>

                <footer>
                    <p><strong>SuperLocalMemory V2.2.0</strong></p>
                    <p>Copyright (c) 2026 Varun Pratap Bhardwaj</p>
                    <p>Licensed under MIT License</p>
                </footer>
            </body>
        </html>
        """
    return index_path.read_text()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.2.0",
        "database": "connected" if DB_PATH.exists() else "missing",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# API Endpoints - Memory Management
# ============================================================================

@app.get("/api/memories")
async def get_memories(
    category: Optional[str] = None,
    project_name: Optional[str] = None,
    cluster_id: Optional[int] = None,
    min_importance: Optional[int] = None,
    tags: Optional[str] = None,  # Comma-separated
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List memories with optional filtering and pagination.

    Query Parameters:
    - category: Filter by category
    - project_name: Filter by project
    - cluster_id: Filter by cluster
    - min_importance: Minimum importance score (1-10)
    - tags: Comma-separated tag list
    - limit: Maximum results (default 50, max 200)
    - offset: Pagination offset

    Returns:
    - memories: List of memory objects
    - total: Total count matching filters
    - limit: Applied limit
    - offset: Applied offset
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        active_profile = get_active_profile()

        # Build dynamic query
        query = """
            SELECT
                id, content, summary, category, project_name, project_path,
                importance, cluster_id, depth, access_count, parent_id,
                created_at, updated_at, last_accessed, tags, memory_type
            FROM memories
            WHERE profile = ?
        """
        params = [active_profile]

        if category:
            query += " AND category = ?"
            params.append(category)

        if project_name:
            query += " AND project_name = ?"
            params.append(project_name)

        if cluster_id is not None:
            query += " AND cluster_id = ?"
            params.append(cluster_id)

        if min_importance:
            query += " AND importance >= ?"
            params.append(min_importance)

        if tags:
            tag_list = [t.strip() for t in tags.split(',')]
            for tag in tag_list:
                query += " AND tags LIKE ?"
                params.append(f'%{tag}%')

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        memories = cursor.fetchall()

        # Get total count
        count_query = "SELECT COUNT(*) as total FROM memories WHERE profile = ?"
        count_params = [active_profile]

        if category:
            count_query += " AND category = ?"
            count_params.append(category)
        if project_name:
            count_query += " AND project_name = ?"
            count_params.append(project_name)
        if cluster_id is not None:
            count_query += " AND cluster_id = ?"
            count_params.append(cluster_id)
        if min_importance:
            count_query += " AND importance >= ?"
            count_params.append(min_importance)

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['total']

        conn.close()

        return {
            "memories": memories,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/graph")
async def get_graph(
    max_nodes: int = Query(100, ge=10, le=500),
    min_importance: int = Query(1, ge=1, le=10)
):
    """
    Get knowledge graph data for D3.js force-directed visualization.

    Parameters:
    - max_nodes: Maximum nodes to return (default 100, max 500)
    - min_importance: Minimum importance filter (default 1)

    Returns:
    - nodes: List of memory nodes with metadata
    - links: List of edges between memories
    - clusters: Cluster information
    - metadata: Graph statistics
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        active_profile = get_active_profile()

        # Get nodes (memories with graph data)
        cursor.execute("""
            SELECT
                m.id, m.content, m.summary, m.category,
                m.cluster_id, m.importance, m.project_name,
                m.created_at, m.tags,
                gn.entities
            FROM memories m
            LEFT JOIN graph_nodes gn ON m.id = gn.memory_id
            WHERE m.importance >= ? AND m.profile = ?
            ORDER BY m.importance DESC, m.updated_at DESC
            LIMIT ?
        """, (min_importance, active_profile, max_nodes))
        nodes = cursor.fetchall()

        # Parse entities JSON and create previews
        for node in nodes:
            if node['entities']:
                try:
                    node['entities'] = json.loads(node['entities'])
                except:
                    node['entities'] = []
            else:
                node['entities'] = []

            # Create content preview
            if node['content']:
                node['content_preview'] = (
                    node['content'][:100] + "..."
                    if len(node['content']) > 100
                    else node['content']
                )

        # Get edges
        memory_ids = [n['id'] for n in nodes]
        if memory_ids:
            placeholders = ','.join('?' * len(memory_ids))
            cursor.execute(f"""
                SELECT
                    source_memory_id as source,
                    target_memory_id as target,
                    weight,
                    relationship_type,
                    shared_entities
                FROM graph_edges
                WHERE source_memory_id IN ({placeholders})
                  AND target_memory_id IN ({placeholders})
                ORDER BY weight DESC
            """, memory_ids + memory_ids)
            links = cursor.fetchall()

            # Parse shared entities
            for link in links:
                if link['shared_entities']:
                    try:
                        link['shared_entities'] = json.loads(link['shared_entities'])
                    except:
                        link['shared_entities'] = []
        else:
            links = []

        # Get cluster information
        cursor.execute("""
            SELECT
                cluster_id,
                COUNT(*) as size,
                AVG(importance) as avg_importance
            FROM memories
            WHERE cluster_id IS NOT NULL AND profile = ?
            GROUP BY cluster_id
        """, (active_profile,))
        clusters = cursor.fetchall()

        conn.close()

        return {
            "nodes": nodes,
            "links": links,
            "clusters": clusters,
            "metadata": {
                "node_count": len(nodes),
                "edge_count": len(links),
                "cluster_count": len(clusters),
                "filters_applied": {
                    "max_nodes": max_nodes,
                    "min_importance": min_importance
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph error: {str(e)}")


@app.get("/api/timeline")
async def get_timeline(
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("day", pattern="^(day|week|month)$")
):
    """
    Get temporal view of memory creation with flexible grouping.

    Parameters:
    - days: Number of days to look back (default 30, max 365)
    - group_by: Aggregation period ('day', 'week', 'month')

    Returns:
    - timeline: Aggregated memory counts by period
    - category_trend: Category breakdown over time
    - period_stats: Statistics for the period
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Determine date grouping SQL
        if group_by == "day":
            date_group = "DATE(created_at)"
        elif group_by == "week":
            date_group = "strftime('%Y-W%W', created_at)"
        else:  # month
            date_group = "strftime('%Y-%m', created_at)"

        active_profile = get_active_profile()

        # Timeline aggregates
        cursor.execute(f"""
            SELECT
                {date_group} as period,
                COUNT(*) as count,
                AVG(importance) as avg_importance,
                MIN(importance) as min_importance,
                MAX(importance) as max_importance,
                GROUP_CONCAT(DISTINCT category) as categories
            FROM memories
            WHERE created_at >= datetime('now', '-' || ? || ' days')
              AND profile = ?
            GROUP BY {date_group}
            ORDER BY period DESC
        """, (days, active_profile))
        timeline = cursor.fetchall()

        # Category trend over time
        cursor.execute(f"""
            SELECT
                {date_group} as period,
                category,
                COUNT(*) as count
            FROM memories
            WHERE created_at >= datetime('now', '-' || ? || ' days')
              AND category IS NOT NULL AND profile = ?
            GROUP BY {date_group}, category
            ORDER BY period DESC, count DESC
        """, (days, active_profile))
        category_trend = cursor.fetchall()

        # Period statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_memories,
                COUNT(DISTINCT category) as categories_used,
                COUNT(DISTINCT project_name) as projects_active,
                AVG(importance) as avg_importance
            FROM memories
            WHERE created_at >= datetime('now', '-' || ? || ' days')
              AND profile = ?
        """, (days, active_profile))
        period_stats = cursor.fetchone()

        conn.close()

        return {
            "timeline": timeline,
            "category_trend": category_trend,
            "period_stats": period_stats,
            "parameters": {
                "days": days,
                "group_by": group_by
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timeline error: {str(e)}")


@app.get("/api/clusters")
async def get_clusters():
    """
    Get cluster information with member counts, themes, and statistics.

    Returns:
    - clusters: List of clusters with metadata
    - total_clusters: Total number of clusters
    - unclustered_count: Memories without cluster assignment
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        active_profile = get_active_profile()

        # Get cluster statistics with hierarchy and summaries
        cursor.execute("""
            SELECT
                m.cluster_id,
                COUNT(*) as member_count,
                AVG(m.importance) as avg_importance,
                MIN(m.importance) as min_importance,
                MAX(m.importance) as max_importance,
                GROUP_CONCAT(DISTINCT m.category) as categories,
                GROUP_CONCAT(DISTINCT m.project_name) as projects,
                MIN(m.created_at) as first_memory,
                MAX(m.created_at) as latest_memory,
                gc.summary,
                gc.parent_cluster_id,
                gc.depth
            FROM memories m
            LEFT JOIN graph_clusters gc ON m.cluster_id = gc.id
            WHERE m.cluster_id IS NOT NULL AND m.profile = ?
            GROUP BY m.cluster_id
            ORDER BY COALESCE(gc.depth, 0) ASC, member_count DESC
        """, (active_profile,))
        clusters = cursor.fetchall()

        # Get dominant entities per cluster
        for cluster in clusters:
            cluster_id = cluster['cluster_id']

            # Aggregate entities from all members
            cursor.execute("""
                SELECT gn.entities
                FROM graph_nodes gn
                JOIN memories m ON gn.memory_id = m.id
                WHERE m.cluster_id = ?
            """, (cluster_id,))

            all_entities = []
            for row in cursor.fetchall():
                if row['entities']:
                    try:
                        entities = json.loads(row['entities'])
                        all_entities.extend(entities)
                    except:
                        pass

            # Count and get top entities
            from collections import Counter
            entity_counts = Counter(all_entities)
            cluster['top_entities'] = [
                {"entity": e, "count": c}
                for e, c in entity_counts.most_common(10)
            ]

        # Get unclustered count
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM memories
            WHERE cluster_id IS NULL AND profile = ?
        """, (active_profile,))
        unclustered = cursor.fetchone()['count']

        conn.close()

        return {
            "clusters": clusters,
            "total_clusters": len(clusters),
            "unclustered_count": unclustered
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cluster error: {str(e)}")


@app.get("/api/clusters/{cluster_id}")
async def get_cluster_detail(
    cluster_id: int,
    limit: int = Query(50, ge=1, le=200)
):
    """
    Get detailed view of a specific cluster.

    Parameters:
    - cluster_id: Cluster ID to retrieve
    - limit: Maximum members to return

    Returns:
    - cluster_info: Cluster metadata and statistics
    - members: List of memories in the cluster
    - connections: Internal edges within cluster
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Get cluster members
        cursor.execute("""
            SELECT
                m.id, m.content, m.summary, m.category,
                m.project_name, m.importance, m.created_at,
                m.tags, gn.entities
            FROM memories m
            LEFT JOIN graph_nodes gn ON m.id = gn.memory_id
            WHERE m.cluster_id = ?
            ORDER BY m.importance DESC, m.created_at DESC
            LIMIT ?
        """, (cluster_id, limit))
        members = cursor.fetchall()

        if not members:
            raise HTTPException(status_code=404, detail="Cluster not found")

        # Parse entities
        for member in members:
            if member['entities']:
                try:
                    member['entities'] = json.loads(member['entities'])
                except:
                    member['entities'] = []

        # Get cluster statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_members,
                AVG(importance) as avg_importance,
                COUNT(DISTINCT category) as category_count,
                COUNT(DISTINCT project_name) as project_count
            FROM memories
            WHERE cluster_id = ?
        """, (cluster_id,))
        stats = cursor.fetchone()

        # Get internal connections
        member_ids = [m['id'] for m in members]
        if member_ids:
            placeholders = ','.join('?' * len(member_ids))
            cursor.execute(f"""
                SELECT
                    source_memory_id as source,
                    target_memory_id as target,
                    weight,
                    shared_entities
                FROM graph_edges
                WHERE source_memory_id IN ({placeholders})
                  AND target_memory_id IN ({placeholders})
            """, member_ids + member_ids)
            connections = cursor.fetchall()
        else:
            connections = []

        conn.close()

        return {
            "cluster_info": {
                "cluster_id": cluster_id,
                **stats
            },
            "members": members,
            "connections": connections
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cluster detail error: {str(e)}")


@app.get("/api/patterns")
async def get_patterns():
    """
    Get learned patterns from Pattern Learner (Layer 4).

    Returns:
    - patterns: Grouped patterns by type
    - total_patterns: Total pattern count
    - pattern_types: List of pattern types found
    - confidence_stats: Confidence distribution
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Check if identity_patterns table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='identity_patterns'
        """)

        if not cursor.fetchone():
            return {
                "patterns": {},
                "total_patterns": 0,
                "pattern_types": [],
                "message": "Pattern learning not initialized. Run pattern learning first."
            }

        active_profile = get_active_profile()

        cursor.execute("""
            SELECT
                pattern_type, key, value, confidence,
                evidence_count, updated_at as last_updated
            FROM identity_patterns
            WHERE profile = ?
            ORDER BY confidence DESC, evidence_count DESC
        """, (active_profile,))
        patterns = cursor.fetchall()

        # Parse value JSON
        for pattern in patterns:
            if pattern['value']:
                try:
                    pattern['value'] = json.loads(pattern['value'])
                except:
                    pass

        # Group by type
        grouped = defaultdict(list)
        for pattern in patterns:
            grouped[pattern['pattern_type']].append(pattern)

        # Confidence statistics
        confidences = [p['confidence'] for p in patterns]
        confidence_stats = {
            "avg": sum(confidences) / len(confidences) if confidences else 0,
            "min": min(confidences) if confidences else 0,
            "max": max(confidences) if confidences else 0
        }

        conn.close()

        return {
            "patterns": dict(grouped),
            "total_patterns": len(patterns),
            "pattern_types": list(grouped.keys()),
            "confidence_stats": confidence_stats
        }

    except Exception as e:
        return {
            "patterns": {},
            "total_patterns": 0,
            "error": str(e)
        }


@app.get("/api/stats")
async def get_stats():
    """
    Get comprehensive system statistics.

    Returns:
    - overview: Basic counts and metrics
    - categories: Category breakdown
    - projects: Project breakdown
    - importance_distribution: Importance score distribution
    - recent_activity: Recent memory statistics
    - graph_stats: Graph-specific metrics
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        active_profile = get_active_profile()

        # Basic counts (profile-filtered)
        cursor.execute("SELECT COUNT(*) as total FROM memories WHERE profile = ?", (active_profile,))
        total_memories = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM sessions")
        total_sessions = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(DISTINCT cluster_id) as total FROM memories WHERE cluster_id IS NOT NULL AND profile = ?", (active_profile,))
        total_clusters = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COUNT(*) as total FROM graph_nodes gn
            JOIN memories m ON gn.memory_id = m.id
            WHERE m.profile = ?
        """, (active_profile,))
        total_graph_nodes = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COUNT(*) as total FROM graph_edges ge
            JOIN memories m ON ge.source_memory_id = m.id
            WHERE m.profile = ?
        """, (active_profile,))
        total_graph_edges = cursor.fetchone()['total']

        # Category breakdown
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM memories
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
            LIMIT 10
        """)
        categories = cursor.fetchall()

        # Project breakdown
        cursor.execute("""
            SELECT project_name, COUNT(*) as count
            FROM memories
            WHERE project_name IS NOT NULL
            GROUP BY project_name
            ORDER BY count DESC
            LIMIT 10
        """)
        projects = cursor.fetchall()

        # Recent activity (last 7 days)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM memories
            WHERE created_at >= datetime('now', '-7 days')
        """)
        recent_memories = cursor.fetchone()['count']

        # Importance distribution
        cursor.execute("""
            SELECT importance, COUNT(*) as count
            FROM memories
            GROUP BY importance
            ORDER BY importance DESC
        """)
        importance_dist = cursor.fetchall()

        # Database size
        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0

        # Graph density (edges / potential edges)
        if total_graph_nodes > 1:
            max_edges = (total_graph_nodes * (total_graph_nodes - 1)) / 2
            density = total_graph_edges / max_edges if max_edges > 0 else 0
        else:
            density = 0

        conn.close()

        return {
            "overview": {
                "total_memories": total_memories,
                "total_sessions": total_sessions,
                "total_clusters": total_clusters,
                "graph_nodes": total_graph_nodes,
                "graph_edges": total_graph_edges,
                "db_size_mb": round(db_size / (1024 * 1024), 2),
                "recent_memories_7d": recent_memories
            },
            "categories": categories,
            "projects": projects,
            "importance_distribution": importance_dist,
            "graph_stats": {
                "density": round(density, 4),
                "avg_degree": round(2 * total_graph_edges / total_graph_nodes, 2) if total_graph_nodes > 0 else 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")


@app.post("/api/search")
async def search_memories(request: SearchRequest):
    """
    Advanced semantic search with filters.

    Request body:
    - query: Search query (required)
    - limit: Max results (default 10, max 100)
    - min_score: Minimum similarity score (default 0.3)
    - category: Optional category filter
    - project_name: Optional project filter
    - cluster_id: Optional cluster filter
    - date_from: Optional start date (YYYY-MM-DD)
    - date_to: Optional end date (YYYY-MM-DD)

    Returns:
    - results: Matching memories with scores
    - query: Original query
    - total: Result count
    - filters_applied: Applied filters
    """
    try:
        store = MemoryStoreV2(DB_PATH)
        results = store.search(
            query=request.query,
            limit=request.limit * 2  # Get more, then filter
        )

        # Apply additional filters
        filtered = []
        for result in results:
            # Score filter
            if result.get('score', 0) < request.min_score:
                continue

            # Category filter
            if request.category and result.get('category') != request.category:
                continue

            # Project filter
            if request.project_name and result.get('project_name') != request.project_name:
                continue

            # Cluster filter
            if request.cluster_id is not None and result.get('cluster_id') != request.cluster_id:
                continue

            # Date filters
            if request.date_from:
                created = result.get('created_at', '')
                if created < request.date_from:
                    continue

            if request.date_to:
                created = result.get('created_at', '')
                if created > request.date_to:
                    continue

            filtered.append(result)

            if len(filtered) >= request.limit:
                break

        return {
            "query": request.query,
            "results": filtered,
            "total": len(filtered),
            "filters_applied": {
                "category": request.category,
                "project_name": request.project_name,
                "cluster_id": request.cluster_id,
                "date_from": request.date_from,
                "date_to": request.date_to,
                "min_score": request.min_score
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


# ============================================================================
# API Endpoints - Profile Management
# ============================================================================

@app.get("/api/profiles")
async def list_profiles():
    """
    List available memory profiles (column-based).

    Returns:
    - profiles: List of profiles with memory counts
    - active_profile: Currently active profile
    - total_profiles: Profile count
    """
    try:
        config_file = MEMORY_DIR / "profiles.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {'profiles': {'default': {'name': 'default', 'description': 'Default memory profile'}}, 'active_profile': 'default'}

        active = config.get('active_profile', 'default')
        profiles = []

        conn = get_db_connection()
        cursor = conn.cursor()

        for name, info in config.get('profiles', {}).items():
            cursor.execute("SELECT COUNT(*) FROM memories WHERE profile = ?", (name,))
            count = cursor.fetchone()[0]
            profiles.append({
                "name": name,
                "description": info.get('description', ''),
                "memory_count": count,
                "created_at": info.get('created_at', ''),
                "last_used": info.get('last_used', ''),
                "is_active": name == active
            })

        conn.close()

        return {
            "profiles": profiles,
            "active_profile": active,
            "total_profiles": len(profiles)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile list error: {str(e)}")


@app.post("/api/profiles/{name}/switch")
async def switch_profile(name: str):
    """
    Switch active memory profile (column-based, instant).

    Parameters:
    - name: Profile name to switch to

    Returns:
    - success: Switch status
    - active_profile: New active profile
    - previous_profile: Previously active profile
    - memory_count: Memories in new profile
    """
    try:
        if not validate_profile_name(name):
            raise HTTPException(
                status_code=400,
                detail="Invalid profile name. Use alphanumeric, underscore, or hyphen only."
            )

        config_file = MEMORY_DIR / "profiles.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {'profiles': {'default': {'name': 'default', 'description': 'Default memory profile'}}, 'active_profile': 'default'}

        if name not in config.get('profiles', {}):
            raise HTTPException(
                status_code=404,
                detail=f"Profile '{name}' not found. Available: {', '.join(config.get('profiles', {}).keys())}"
            )

        previous = config.get('active_profile', 'default')
        config['active_profile'] = name
        config['profiles'][name]['last_used'] = datetime.now().isoformat()

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        # Get memory count for new profile
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories WHERE profile = ?", (name,))
        count = cursor.fetchone()[0]
        conn.close()

        # Broadcast profile switch to WebSocket clients
        await manager.broadcast({
            "type": "profile_switched",
            "profile": name,
            "previous": previous,
            "memory_count": count,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "success": True,
            "active_profile": name,
            "previous_profile": previous,
            "memory_count": count,
            "message": f"Switched to profile '{name}' ({count} memories). Changes take effect immediately."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile switch error: {str(e)}")


@app.post("/api/profiles/create")
async def create_profile(body: ProfileSwitch):
    """
    Create a new memory profile.

    Parameters:
    - profile_name: Name for the new profile

    Returns:
    - success: Creation status
    - profile: Created profile name
    """
    try:
        name = body.profile_name
        if not validate_profile_name(name):
            raise HTTPException(status_code=400, detail="Invalid profile name")

        config_file = MEMORY_DIR / "profiles.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {'profiles': {'default': {'name': 'default', 'description': 'Default memory profile'}}, 'active_profile': 'default'}

        if name in config.get('profiles', {}):
            raise HTTPException(status_code=409, detail=f"Profile '{name}' already exists")

        config['profiles'][name] = {
            'name': name,
            'description': f'Memory profile: {name}',
            'created_at': datetime.now().isoformat(),
            'last_used': None
        }

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        return {
            "success": True,
            "profile": name,
            "message": f"Profile '{name}' created"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile create error: {str(e)}")


@app.delete("/api/profiles/{name}")
async def delete_profile(name: str):
    """
    Delete a profile. Moves its memories to 'default'.
    """
    try:
        if name == 'default':
            raise HTTPException(status_code=400, detail="Cannot delete 'default' profile")

        config_file = MEMORY_DIR / "profiles.json"
        with open(config_file, 'r') as f:
            config = json.load(f)

        if name not in config.get('profiles', {}):
            raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")

        if config.get('active_profile') == name:
            raise HTTPException(status_code=400, detail="Cannot delete active profile. Switch first.")

        # Move memories to default
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE memories SET profile = 'default' WHERE profile = ?", (name,))
        moved = cursor.rowcount
        conn.commit()
        conn.close()

        del config['profiles'][name]
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        return {
            "success": True,
            "message": f"Profile '{name}' deleted. {moved} memories moved to 'default'."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile delete error: {str(e)}")


# ============================================================================
# API Endpoints - Import/Export
# ============================================================================

@app.get("/api/export")
async def export_memories(
    format: str = Query("json", pattern="^(json|jsonl)$"),
    category: Optional[str] = None,
    project_name: Optional[str] = None
):
    """
    Export memories as JSON or JSONL.

    Parameters:
    - format: Export format ('json' or 'jsonl')
    - category: Optional category filter
    - project_name: Optional project filter

    Returns:
    - Downloadable JSON file with memories
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Build query with filters
        query = "SELECT * FROM memories WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if project_name:
            query += " AND project_name = ?"
            params.append(project_name)

        query += " ORDER BY created_at"

        cursor.execute(query, params)
        memories = cursor.fetchall()
        conn.close()

        # Format export
        if format == "jsonl":
            # JSON Lines format
            content = "\n".join(json.dumps(m) for m in memories)
            media_type = "application/x-ndjson"
        else:
            # Standard JSON
            content = json.dumps({
                "version": "2.2.0",
                "exported_at": datetime.now().isoformat(),
                "total_memories": len(memories),
                "filters": {
                    "category": category,
                    "project_name": project_name
                },
                "memories": memories
            }, indent=2)
            media_type = "application/json"

        # Compress if large
        if len(content) > 10000:
            compressed = gzip.compress(content.encode())
            return StreamingResponse(
                io.BytesIO(compressed),
                media_type="application/gzip",
                headers={
                    "Content-Disposition": f"attachment; filename=memories_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}.gz"
                }
            )
        else:
            return StreamingResponse(
                io.BytesIO(content.encode()),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename=memories_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


@app.post("/api/import")
async def import_memories(file: UploadFile = File(...)):
    """
    Import memories from JSON file.

    Parameters:
    - file: JSON file containing memories

    Returns:
    - success: Import status
    - imported_count: Number of memories imported
    - skipped_count: Number of duplicates skipped
    - errors: List of import errors
    """
    try:
        # Read file content
        content = await file.read()

        # Handle gzip compressed files
        if file.filename.endswith('.gz'):
            content = gzip.decompress(content)

        # Parse JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        # Extract memories array
        if isinstance(data, dict) and 'memories' in data:
            memories = data['memories']
        elif isinstance(data, list):
            memories = data
        else:
            raise HTTPException(status_code=400, detail="Invalid format: expected 'memories' array")

        # Import memories
        store = MemoryStoreV2(DB_PATH)
        imported = 0
        skipped = 0
        errors = []

        for idx, memory in enumerate(memories):
            try:
                # Validate required fields
                if 'content' not in memory:
                    errors.append(f"Memory {idx}: missing 'content' field")
                    continue

                # Add memory
                store.add_memory(
                    content=memory.get('content'),
                    summary=memory.get('summary'),
                    project_path=memory.get('project_path'),
                    project_name=memory.get('project_name'),
                    tags=memory.get('tags', '').split(',') if memory.get('tags') else None,
                    category=memory.get('category'),
                    importance=memory.get('importance', 5)
                )
                imported += 1

                # Broadcast update to WebSocket clients
                await manager.broadcast({
                    "type": "memory_added",
                    "memory_id": imported,
                    "timestamp": datetime.now().isoformat()
                })

            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    skipped += 1
                else:
                    errors.append(f"Memory {idx}: {str(e)}")

        return {
            "success": True,
            "imported_count": imported,
            "skipped_count": skipped,
            "total_processed": len(memories),
            "errors": errors[:10]  # Limit error list
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")


# ============================================================================
# API Endpoints - Backup Management
# ============================================================================

class BackupConfigRequest(BaseModel):
    """Backup configuration update request."""
    interval_hours: Optional[int] = Field(None, ge=1, le=8760)
    max_backups: Optional[int] = Field(None, ge=1, le=100)
    enabled: Optional[bool] = None


@app.get("/api/backup/status")
async def backup_status():
    """
    Get auto-backup system status.

    Returns:
    - enabled: Whether auto-backup is active
    - interval_display: Human-readable interval
    - last_backup: Timestamp of last backup
    - next_backup: When next backup is due
    - backup_count: Number of existing backups
    - total_size_mb: Total backup storage used
    """
    try:
        from auto_backup import AutoBackup
        backup = AutoBackup()
        return backup.get_status()
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Auto-backup module not installed. Update SuperLocalMemory to v2.4.0+."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup status error: {str(e)}")


@app.post("/api/backup/create")
async def backup_create():
    """
    Create a manual backup of memory.db immediately.

    Returns:
    - success: Whether backup was created
    - filename: Name of the backup file
    - status: Updated backup system status
    """
    try:
        from auto_backup import AutoBackup
        backup = AutoBackup()
        filename = backup.create_backup(label='manual')

        if filename:
            return {
                "success": True,
                "filename": filename,
                "message": f"Backup created: {filename}",
                "status": backup.get_status()
            }
        else:
            return {
                "success": False,
                "message": "Backup failed — database may not exist",
                "status": backup.get_status()
            }
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Auto-backup module not installed. Update SuperLocalMemory to v2.4.0+."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup create error: {str(e)}")


@app.post("/api/backup/configure")
async def backup_configure(request: BackupConfigRequest):
    """
    Update auto-backup configuration.

    Request body (all optional):
    - interval_hours: Hours between backups (24=daily, 168=weekly)
    - max_backups: Maximum backup files to retain
    - enabled: Enable/disable auto-backup

    Returns:
    - Updated backup status
    """
    try:
        from auto_backup import AutoBackup
        backup = AutoBackup()
        result = backup.configure(
            interval_hours=request.interval_hours,
            max_backups=request.max_backups,
            enabled=request.enabled
        )
        return {
            "success": True,
            "message": "Backup configuration updated",
            "status": result
        }
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Auto-backup module not installed. Update SuperLocalMemory to v2.4.0+."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup configure error: {str(e)}")


@app.get("/api/backup/list")
async def backup_list():
    """
    List all available backups.

    Returns:
    - backups: List of backup files with metadata (filename, size, age, created)
    - count: Total number of backups
    """
    try:
        from auto_backup import AutoBackup
        backup = AutoBackup()
        backups = backup.list_backups()
        return {
            "backups": backups,
            "count": len(backups)
        }
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Auto-backup module not installed. Update SuperLocalMemory to v2.4.0+."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup list error: {str(e)}")


# ============================================================================
# WebSocket Endpoint - Real-Time Updates
# ============================================================================

@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """
    WebSocket endpoint for real-time memory updates.

    Broadcasts events:
    - memory_added: New memory created
    - memory_updated: Memory modified
    - cluster_updated: Cluster recalculated
    - system_stats: Periodic statistics update
    """
    await manager.connect(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": datetime.now().isoformat()
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message from client (ping/pong, commands, etc.)
                data = await websocket.receive_json()

                # Handle client requests
                if data.get('type') == 'ping':
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })

                elif data.get('type') == 'get_stats':
                    # Send current stats
                    stats = await get_stats()
                    await websocket.send_json({
                        "type": "stats_update",
                        "data": stats,
                        "timestamp": datetime.now().isoformat()
                    })

            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })

    finally:
        manager.disconnect(websocket)


# ============================================================================
# Server Startup
# ============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SuperLocalMemory V2 - Web Dashboard")
    parser.add_argument("--port", type=int, default=8765, help="Port to run on (default 8765)")
    parser.add_argument("--profile", type=str, default=None, help="Memory profile to use")
    args = parser.parse_args()

    import socket

    def find_available_port(preferred):
        """Try preferred port, then scan next 20 ports."""
        for port in [preferred] + list(range(preferred + 1, preferred + 20)):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                    return port
            except OSError:
                continue
        return preferred

    ui_port = find_available_port(args.port)
    if ui_port != args.port:
        print(f"\n  Port {args.port} in use — using {ui_port} instead\n")

    print("=" * 70)
    print("  SuperLocalMemory V2.4.1 - FastAPI UI Server")
    print("  Copyright (c) 2026 Varun Pratap Bhardwaj")
    print("=" * 70)
    print(f"  Database: {DB_PATH}")
    print(f"  UI Directory: {UI_DIR}")
    print(f"  Profiles: {PROFILES_DIR}")
    print("=" * 70)
    print(f"\n  Server URLs:")
    print(f"  - Main UI:       http://localhost:{ui_port}")
    print(f"  - API Docs:      http://localhost:{ui_port}/api/docs")
    print(f"  - Health Check:  http://localhost:{ui_port}/health")
    print(f"  - WebSocket:     ws://localhost:{ui_port}/ws/updates")
    print("\n  Press Ctrl+C to stop\n")

    # SECURITY: Bind to localhost only to prevent unauthorized network access
    # For remote access, use a reverse proxy (nginx/caddy) with authentication
    uvicorn.run(
        app,
        host="127.0.0.1",  # localhost only - NEVER use 0.0.0.0 without auth
        port=ui_port,
        log_level="info",
        access_log=True
    )
