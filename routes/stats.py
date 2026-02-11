"""
SuperLocalMemory V2 - Stats Routes
Copyright (c) 2026 Varun Pratap Bhardwaj — MIT License

Routes: /api/stats, /api/timeline, /api/patterns
"""

import json
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query

from .helpers import get_db_connection, dict_factory, get_active_profile, DB_PATH

router = APIRouter()


@router.get("/api/stats")
async def get_stats():
    """Get comprehensive system statistics."""
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        active_profile = get_active_profile()

        cursor.execute("SELECT COUNT(*) as total FROM memories WHERE profile = ?", (active_profile,))
        total_memories = cursor.fetchone()['total']

        # These tables may not exist on fresh DBs — graceful fallback to 0
        try:
            cursor.execute("SELECT COUNT(*) as total FROM sessions")
            total_sessions = cursor.fetchone()['total']
        except Exception:
            total_sessions = 0

        cursor.execute("SELECT COUNT(DISTINCT cluster_id) as total FROM memories WHERE cluster_id IS NOT NULL AND profile = ?", (active_profile,))
        total_clusters = cursor.fetchone()['total']

        try:
            cursor.execute("SELECT COUNT(*) as total FROM graph_nodes gn JOIN memories m ON gn.memory_id = m.id WHERE m.profile = ?", (active_profile,))
            total_graph_nodes = cursor.fetchone()['total']
        except Exception:
            total_graph_nodes = 0

        try:
            cursor.execute("SELECT COUNT(*) as total FROM graph_edges ge JOIN memories m ON ge.source_memory_id = m.id WHERE m.profile = ?", (active_profile,))
            total_graph_edges = cursor.fetchone()['total']
        except Exception:
            total_graph_edges = 0

        cursor.execute("SELECT category, COUNT(*) as count FROM memories WHERE category IS NOT NULL GROUP BY category ORDER BY count DESC LIMIT 10")
        categories = cursor.fetchall()

        cursor.execute("SELECT project_name, COUNT(*) as count FROM memories WHERE project_name IS NOT NULL GROUP BY project_name ORDER BY count DESC LIMIT 10")
        projects = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) as count FROM memories WHERE created_at >= datetime('now', '-7 days')")
        recent_memories = cursor.fetchone()['count']

        cursor.execute("SELECT importance, COUNT(*) as count FROM memories GROUP BY importance ORDER BY importance DESC")
        importance_dist = cursor.fetchall()

        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0

        if total_graph_nodes > 1:
            max_edges = (total_graph_nodes * (total_graph_nodes - 1)) / 2
            density = total_graph_edges / max_edges if max_edges > 0 else 0
        else:
            density = 0

        conn.close()

        return {
            "overview": {
                "total_memories": total_memories, "total_sessions": total_sessions,
                "total_clusters": total_clusters, "graph_nodes": total_graph_nodes,
                "graph_edges": total_graph_edges,
                "db_size_mb": round(db_size / (1024 * 1024), 2),
                "recent_memories_7d": recent_memories
            },
            "categories": categories, "projects": projects,
            "importance_distribution": importance_dist,
            "graph_stats": {
                "density": round(density, 4),
                "avg_degree": round(2 * total_graph_edges / total_graph_nodes, 2) if total_graph_nodes > 0 else 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")


@router.get("/api/timeline")
async def get_timeline(
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("day", pattern="^(day|week|month)$")
):
    """Get temporal view of memory creation with flexible grouping."""
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        active_profile = get_active_profile()

        if group_by == "day":
            date_group = "DATE(created_at)"
        elif group_by == "week":
            date_group = "strftime('%Y-W%W', created_at)"
        else:
            date_group = "strftime('%Y-%m', created_at)"

        cursor.execute(f"""
            SELECT {date_group} as period, COUNT(*) as count,
                   AVG(importance) as avg_importance,
                   MIN(importance) as min_importance, MAX(importance) as max_importance,
                   GROUP_CONCAT(DISTINCT category) as categories
            FROM memories
            WHERE created_at >= datetime('now', '-' || ? || ' days') AND profile = ?
            GROUP BY {date_group} ORDER BY period DESC
        """, (days, active_profile))
        timeline = cursor.fetchall()

        cursor.execute(f"""
            SELECT {date_group} as period, category, COUNT(*) as count
            FROM memories
            WHERE created_at >= datetime('now', '-' || ? || ' days')
              AND category IS NOT NULL AND profile = ?
            GROUP BY {date_group}, category ORDER BY period DESC, count DESC
        """, (days, active_profile))
        category_trend = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) as total_memories, COUNT(DISTINCT category) as categories_used,
                   COUNT(DISTINCT project_name) as projects_active, AVG(importance) as avg_importance
            FROM memories
            WHERE created_at >= datetime('now', '-' || ? || ' days') AND profile = ?
        """, (days, active_profile))
        period_stats = cursor.fetchone()

        conn.close()

        return {
            "timeline": timeline, "category_trend": category_trend,
            "period_stats": period_stats,
            "parameters": {"days": days, "group_by": group_by}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timeline error: {str(e)}")


@router.get("/api/patterns")
async def get_patterns():
    """Get learned patterns from Pattern Learner (Layer 4)."""
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='identity_patterns'")
        if not cursor.fetchone():
            return {"patterns": {}, "total_patterns": 0, "pattern_types": [],
                    "message": "Pattern learning not initialized. Run pattern learning first."}

        active_profile = get_active_profile()

        cursor.execute("""
            SELECT pattern_type, key, value, confidence, evidence_count, updated_at as last_updated
            FROM identity_patterns WHERE profile = ?
            ORDER BY confidence DESC, evidence_count DESC
        """, (active_profile,))
        patterns = cursor.fetchall()

        for pattern in patterns:
            if pattern['value']:
                try:
                    pattern['value'] = json.loads(pattern['value'])
                except Exception:
                    pass

        grouped = defaultdict(list)
        for pattern in patterns:
            grouped[pattern['pattern_type']].append(pattern)

        confidences = [p['confidence'] for p in patterns]
        confidence_stats = {
            "avg": sum(confidences) / len(confidences) if confidences else 0,
            "min": min(confidences) if confidences else 0,
            "max": max(confidences) if confidences else 0
        }

        conn.close()

        return {
            "patterns": dict(grouped), "total_patterns": len(patterns),
            "pattern_types": list(grouped.keys()), "confidence_stats": confidence_stats
        }

    except Exception as e:
        return {"patterns": {}, "total_patterns": 0, "error": str(e)}
