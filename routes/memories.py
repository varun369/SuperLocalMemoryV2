"""
SuperLocalMemory V2 - Memory Routes
Copyright (c) 2026 Varun Pratap Bhardwaj — MIT License

Routes: /api/memories, /api/graph, /api/search, /api/clusters, /api/clusters/{id}
"""

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .helpers import (
    get_db_connection, dict_factory, get_active_profile,
    SearchRequest, DB_PATH, MEMORY_DIR
)

import sys
sys.path.insert(0, str(MEMORY_DIR))

from memory_store_v2 import MemoryStoreV2

router = APIRouter()


@router.get("/api/memories")
async def get_memories(
    category: Optional[str] = None,
    project_name: Optional[str] = None,
    cluster_id: Optional[int] = None,
    min_importance: Optional[int] = None,
    tags: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List memories with optional filtering and pagination."""
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        active_profile = get_active_profile()

        query = """
            SELECT id, content, summary, category, project_name, project_path,
                   importance, cluster_id, depth, access_count, parent_id,
                   created_at, updated_at, last_accessed, tags, memory_type
            FROM memories WHERE profile = ?
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
            "memories": memories, "total": total,
            "limit": limit, "offset": offset,
            "has_more": (offset + limit) < total
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/api/graph")
async def get_graph(
    max_nodes: int = Query(100, ge=10, le=500),
    min_importance: int = Query(1, ge=1, le=10)
):
    """Get knowledge graph data for D3.js force-directed visualization."""
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        active_profile = get_active_profile()

        # graph_nodes table may not exist on fresh DBs — graceful fallback
        try:
            cursor.execute("""
                SELECT m.id, m.content, m.summary, m.category,
                       m.cluster_id, m.importance, m.project_name,
                       m.created_at, m.tags, gn.entities
                FROM memories m
                LEFT JOIN graph_nodes gn ON m.id = gn.memory_id
                WHERE m.importance >= ? AND m.profile = ?
                ORDER BY m.importance DESC, m.updated_at DESC
                LIMIT ?
            """, (min_importance, active_profile, max_nodes))
        except Exception:
            # Fallback: no graph_nodes table yet
            cursor.execute("""
                SELECT id, content, summary, category,
                       cluster_id, importance, project_name,
                       created_at, tags, NULL as entities
                FROM memories
                WHERE importance >= ? AND profile = ?
                ORDER BY importance DESC, updated_at DESC
                LIMIT ?
            """, (min_importance, active_profile, max_nodes))
        nodes = cursor.fetchall()

        for node in nodes:
            if node['entities']:
                try:
                    node['entities'] = json.loads(node['entities'])
                except Exception:
                    node['entities'] = []
            else:
                node['entities'] = []
            if node['content']:
                node['content_preview'] = (
                    node['content'][:100] + "..."
                    if len(node['content']) > 100 else node['content']
                )

        memory_ids = [n['id'] for n in nodes]
        links = []
        if memory_ids:
            try:
                placeholders = ','.join('?' * len(memory_ids))
                cursor.execute(f"""
                    SELECT source_memory_id as source, target_memory_id as target,
                           weight, relationship_type, shared_entities
                    FROM graph_edges
                    WHERE source_memory_id IN ({placeholders})
                      AND target_memory_id IN ({placeholders})
                    ORDER BY weight DESC
                """, memory_ids + memory_ids)
                links = cursor.fetchall()
                for link in links:
                    if link['shared_entities']:
                        try:
                            link['shared_entities'] = json.loads(link['shared_entities'])
                        except Exception:
                            link['shared_entities'] = []
            except Exception:
                links = []  # graph_edges table may not exist

        cursor.execute("""
            SELECT cluster_id, COUNT(*) as size, AVG(importance) as avg_importance
            FROM memories
            WHERE cluster_id IS NOT NULL AND profile = ?
            GROUP BY cluster_id
        """, (active_profile,))
        clusters = cursor.fetchall()

        conn.close()

        return {
            "nodes": nodes, "links": links, "clusters": clusters,
            "metadata": {
                "node_count": len(nodes), "edge_count": len(links),
                "cluster_count": len(clusters),
                "filters_applied": {"max_nodes": max_nodes, "min_importance": min_importance}
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph error: {str(e)}")


@router.post("/api/search")
async def search_memories(request: SearchRequest):
    """Advanced semantic search with filters."""
    try:
        store = MemoryStoreV2(DB_PATH)
        results = store.search(query=request.query, limit=request.limit * 2)

        filtered = []
        for result in results:
            if result.get('score', 0) < request.min_score:
                continue
            if request.category and result.get('category') != request.category:
                continue
            if request.project_name and result.get('project_name') != request.project_name:
                continue
            if request.cluster_id is not None and result.get('cluster_id') != request.cluster_id:
                continue
            if request.date_from and (result.get('created_at', '') < request.date_from):
                continue
            if request.date_to and (result.get('created_at', '') > request.date_to):
                continue
            filtered.append(result)
            if len(filtered) >= request.limit:
                break

        return {
            "query": request.query, "results": filtered, "total": len(filtered),
            "filters_applied": {
                "category": request.category, "project_name": request.project_name,
                "cluster_id": request.cluster_id, "date_from": request.date_from,
                "date_to": request.date_to, "min_score": request.min_score
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/api/clusters")
async def get_clusters():
    """Get cluster information with member counts, themes, and statistics."""
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        active_profile = get_active_profile()

        # graph_clusters / graph_nodes may not exist on fresh DBs
        try:
            cursor.execute("""
                SELECT m.cluster_id, COUNT(*) as member_count,
                       AVG(m.importance) as avg_importance,
                       MIN(m.importance) as min_importance,
                       MAX(m.importance) as max_importance,
                       GROUP_CONCAT(DISTINCT m.category) as categories,
                       GROUP_CONCAT(DISTINCT m.project_name) as projects,
                       MIN(m.created_at) as first_memory,
                       MAX(m.created_at) as latest_memory,
                       gc.summary, gc.parent_cluster_id, gc.depth
                FROM memories m
                LEFT JOIN graph_clusters gc ON m.cluster_id = gc.id
                WHERE m.cluster_id IS NOT NULL AND m.profile = ?
                GROUP BY m.cluster_id
                ORDER BY COALESCE(gc.depth, 0) ASC, member_count DESC
            """, (active_profile,))
            clusters = cursor.fetchall()

            from collections import Counter
            for cluster in clusters:
                cluster_id = cluster['cluster_id']
                try:
                    cursor.execute("""
                        SELECT gn.entities FROM graph_nodes gn
                        JOIN memories m ON gn.memory_id = m.id
                        WHERE m.cluster_id = ?
                    """, (cluster_id,))
                    all_entities = []
                    for row in cursor.fetchall():
                        if row['entities']:
                            try:
                                all_entities.extend(json.loads(row['entities']))
                            except Exception:
                                pass
                    entity_counts = Counter(all_entities)
                    cluster['top_entities'] = [
                        {"entity": e, "count": c} for e, c in entity_counts.most_common(10)
                    ]
                except Exception:
                    cluster['top_entities'] = []
        except Exception:
            clusters = []

        cursor.execute("""
            SELECT COUNT(*) as count FROM memories
            WHERE cluster_id IS NULL AND profile = ?
        """, (active_profile,))
        unclustered = cursor.fetchone()['count']

        conn.close()

        return {"clusters": clusters, "total_clusters": len(clusters), "unclustered_count": unclustered}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cluster error: {str(e)}")


@router.get("/api/clusters/{cluster_id}")
async def get_cluster_detail(cluster_id: int, limit: int = Query(50, ge=1, le=200)):
    """Get detailed view of a specific cluster."""
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        cursor.execute("""
            SELECT m.id, m.content, m.summary, m.category,
                   m.project_name, m.importance, m.created_at,
                   m.tags, gn.entities
            FROM memories m
            LEFT JOIN graph_nodes gn ON m.id = gn.memory_id
            WHERE m.cluster_id = ?
            ORDER BY m.importance DESC, m.created_at DESC LIMIT ?
        """, (cluster_id, limit))
        members = cursor.fetchall()

        if not members:
            raise HTTPException(status_code=404, detail="Cluster not found")

        for member in members:
            if member['entities']:
                try:
                    member['entities'] = json.loads(member['entities'])
                except Exception:
                    member['entities'] = []

        cursor.execute("""
            SELECT COUNT(*) as total_members, AVG(importance) as avg_importance,
                   COUNT(DISTINCT category) as category_count,
                   COUNT(DISTINCT project_name) as project_count
            FROM memories WHERE cluster_id = ?
        """, (cluster_id,))
        stats = cursor.fetchone()

        member_ids = [m['id'] for m in members]
        connections = []
        if member_ids:
            placeholders = ','.join('?' * len(member_ids))
            cursor.execute(f"""
                SELECT source_memory_id as source, target_memory_id as target,
                       weight, shared_entities
                FROM graph_edges
                WHERE source_memory_id IN ({placeholders})
                  AND target_memory_id IN ({placeholders})
            """, member_ids + member_ids)
            connections = cursor.fetchall()

        conn.close()

        return {"cluster_info": {"cluster_id": cluster_id, **stats}, "members": members, "connections": connections}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cluster detail error: {str(e)}")
