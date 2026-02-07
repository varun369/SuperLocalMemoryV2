#!/usr/bin/env python3
"""
SuperLocalMemory V2 - example_graph_usage.py

Copyright (c) 2026 Varun Pratap Bhardwaj
Solution Architect & Original Creator

Licensed under MIT License (see LICENSE file)
Repository: https://github.com/varun369/SuperLocalMemoryV2

ATTRIBUTION REQUIRED: This notice must be preserved in all copies.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from graph_engine import GraphEngine


def example_build_graph():
    """Example: Build complete knowledge graph."""
    print("=" * 60)
    print("Example 1: Build Knowledge Graph")
    print("=" * 60)

    engine = GraphEngine()

    # Build graph with default similarity threshold (0.3)
    stats = engine.build_graph(min_similarity=0.3)

    print(f"Graph built successfully!")
    print(f"  - Nodes: {stats['nodes']}")
    print(f"  - Edges: {stats['edges']}")
    print(f"  - Clusters: {stats['clusters']}")
    print(f"  - Time: {stats['time_seconds']}s")
    print()


def example_find_related():
    """Example: Find related memories."""
    print("=" * 60)
    print("Example 2: Find Related Memories")
    print("=" * 60)

    engine = GraphEngine()

    # Find memories related to memory #1
    memory_id = 1
    related = engine.get_related(memory_id, max_hops=2)

    print(f"Memories related to #{memory_id}:")
    for idx, mem in enumerate(related[:5], 1):  # Top 5
        print(f"\n{idx}. Memory #{mem['id']} ({mem['hops']}-hop)")
        print(f"   Relationship: {mem['relationship']}")
        print(f"   Weight: {mem['weight']:.3f}")
        print(f"   Importance: {mem['importance']}")
        if mem['shared_entities']:
            print(f"   Shared entities: {', '.join(mem['shared_entities'][:3])}")
    print()


def example_query_clusters():
    """Example: Query memory clusters."""
    print("=" * 60)
    print("Example 3: Query Clusters")
    print("=" * 60)

    engine = GraphEngine()

    # Get statistics
    stats = engine.get_stats()

    print(f"Total clusters: {stats['clusters']}")
    print("\nTop clusters:")

    for cluster in stats['top_clusters'][:5]:
        print(f"\n  - {cluster['name']}")
        print(f"    Members: {cluster['members']}")
        print(f"    Avg Importance: {cluster['avg_importance']}")

        # Get cluster members
        cluster_id = stats['top_clusters'].index(cluster) + 1
        members = engine.get_cluster_members(cluster_id)

        print(f"    Sample memories: {[m['id'] for m in members[:3]]}")
    print()


def example_incremental_add():
    """Example: Add memory to existing graph."""
    print("=" * 60)
    print("Example 4: Incremental Add")
    print("=" * 60)

    engine = GraphEngine()

    # Simulate adding a new memory (would normally be created first)
    memory_id = 5  # Existing memory

    print(f"Adding memory #{memory_id} to graph...")
    success = engine.add_memory_incremental(memory_id)

    if success:
        print(f"Memory #{memory_id} added successfully!")

        # Find what it connected to
        related = engine.get_related(memory_id, max_hops=1)
        print(f"Connected to {len(related)} existing memories")
    else:
        print("Failed to add memory")
    print()


def example_extract_entities():
    """Example: Extract entities from a memory."""
    print("=" * 60)
    print("Example 5: Entity Extraction")
    print("=" * 60)

    engine = GraphEngine()

    memory_id = 1
    entities = engine.extract_entities(memory_id)

    print(f"Entities extracted from memory #{memory_id}:")
    for idx, entity in enumerate(entities[:10], 1):
        print(f"  {idx}. {entity}")
    print()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("GraphEngine Usage Examples")
    print("=" * 60 + "\n")

    # Run all examples
    example_build_graph()
    example_find_related()
    example_query_clusters()
    example_extract_entities()
    example_incremental_add()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
