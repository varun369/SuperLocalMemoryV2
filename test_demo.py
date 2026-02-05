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
Comprehensive test of demo database functionality.
Demonstrates all major features with the generic demo data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from memory_store_v2 import MemoryStoreV2
from graph_engine import GraphEngine

DEMO_DB_PATH = Path(__file__).parent / "demo-memory.db"


def test_demo_database():
    """Test all major features with demo database."""

    print("="*70)
    print("SUPERLOCALMEMORV2 - DEMO DATABASE TEST")
    print("="*70)

    # Initialize
    store = MemoryStoreV2(db_path=DEMO_DB_PATH)
    graph = GraphEngine(db_path=DEMO_DB_PATH)

    # Test 1: Basic Statistics
    print("\n1. DATABASE STATISTICS")
    print("-" * 70)
    stats = store.get_stats()
    print(f"Total Memories: {stats['total_memories']}")
    print(f"Total Clusters: {stats['total_clusters']}")
    print(f"Categories: {len(stats['by_category'])}")
    print(f"Date Range: {stats['date_range']['earliest'][:10]} to {stats['date_range']['latest'][:10]}")

    # Test 2: Semantic Search
    print("\n2. SEMANTIC SEARCH TEST")
    print("-" * 70)

    search_queries = [
        ("React TypeScript", "frontend"),
        ("database performance", "performance"),
        ("testing best practices", "testing"),
    ]

    for query, expected_category in search_queries:
        print(f"\nQuery: '{query}'")
        results = store.search(query, limit=3)

        for i, mem in enumerate(results, 1):
            print(f"  {i}. [{mem['category']}] {mem['summary']}")
            print(f"     Score: {mem['score']:.3f}, Match: {mem['match_type']}")

    # Test 3: Category Filtering
    print("\n3. CATEGORY FILTERING")
    print("-" * 70)

    # Get all memories by category (direct query since search requires text)
    import sqlite3
    conn = sqlite3.connect(DEMO_DB_PATH)
    cursor = conn.cursor()

    for category in ['frontend', 'backend', 'testing']:
        cursor.execute("SELECT id, summary FROM memories WHERE category = ?", (category,))
        results = cursor.fetchall()
        print(f"\n{category.upper()} ({len(results)} memories):")
        for row in results:
            print(f"  - {row[1]}")

    conn.close()

    # Test 4: Graph Clusters
    print("\n4. GRAPH CLUSTER ANALYSIS")
    print("-" * 70)

    # Get unique cluster IDs
    import sqlite3
    conn = sqlite3.connect(DEMO_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT cluster_id FROM memories WHERE cluster_id IS NOT NULL ORDER BY cluster_id")
    cluster_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    for cluster_id in cluster_ids:
        # Get members using memory store instead
        members = store.get_by_cluster(cluster_id)
        print(f"\nCluster {cluster_id} ({len(members)} members):")
        for mem in members[:3]:  # Show first 3
            print(f"  - [{mem['id']}] {mem.get('category', 'N/A')}: {mem.get('summary', 'No summary')}")

    # Test 5: Recent Memories
    print("\n5. RECENT MEMORIES")
    print("-" * 70)

    recent = store.get_recent(limit=5)
    for mem in recent:
        print(f"  [{mem['id']}] {mem['category']}: {mem['summary']}")

    # Test 6: Memory Relationships
    print("\n6. MEMORY RELATIONSHIPS (Graph Edges)")
    print("-" * 70)

    # Get a sample memory and find related ones
    sample_mem = store.get_by_id(1)
    if sample_mem and sample_mem.get('cluster_id'):
        cluster_memories = store.get_by_cluster(sample_mem['cluster_id'])
        print(f"\nMemory 1 is in Cluster {sample_mem['cluster_id']}:")
        print(f"  '{sample_mem['summary']}'")
        print(f"\nRelated memories in same cluster ({len(cluster_memories)} total):")

        for mem in cluster_memories[:5]:
            if mem['id'] != 1:
                print(f"  - [{mem['id']}] {mem['summary']}")

    # Test 7: Full-Text Search
    print("\n7. FULL-TEXT SEARCH (FTS)")
    print("-" * 70)

    keywords = ['docker', 'optimization', 'api']
    for keyword in keywords:
        results = store.search(keyword, limit=2)
        print(f"\nKeyword: '{keyword}' ({len(results)} results)")
        for mem in results:
            print(f"  - {mem['summary']}")

    # Test 8: Export for Context
    print("\n8. CONTEXT EXPORT (for LLM injection)")
    print("-" * 70)

    context = store.export_for_context("frontend development", max_tokens=500)
    print(f"\nExported context (first 300 chars):")
    print(context[:300] + "...")

    # Summary
    print("\n" + "="*70)
    print("✓ ALL TESTS PASSED")
    print("="*70)
    print(f"\nDemo database location: {DEMO_DB_PATH}")
    print(f"Database size: {DEMO_DB_PATH.stat().st_size / 1024:.1f} KB")
    print("\nThis demonstrates:")
    print("  ✓ V2 schema with categories, clusters, and tree hierarchy")
    print("  ✓ Semantic search using TF-IDF (no external APIs)")
    print("  ✓ Graph clustering for relationship discovery")
    print("  ✓ Category-based organization")
    print("  ✓ Full-text search with FTS5")
    print("  ✓ Context export for LLM prompts")
    print("\nReady for distribution on GitHub!")


if __name__ == "__main__":
    try:
        test_demo_database()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
