#!/usr/bin/env python3
"""
SuperLocalMemory V2 - MCP Server
Universal memory access for all MCP-compatible tools (Cursor, Windsurf, Claude Desktop, Continue.dev)

Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
Repository: https://github.com/varun369/SuperLocalMemoryV2

IMPORTANT: This is an ADDITION to existing skills, not a replacement.
           Skills in Claude Code continue to work unchanged.

Architecture:
    MCP Server (this file)
         ↓
    Calls existing memory_store_v2.py
         ↓
    Same SQLite database as skills

Usage:
    # Run as stdio MCP server (for local IDEs)
    python3 mcp_server.py

    # Run as HTTP MCP server (for remote access)
    python3 mcp_server.py --transport http --port 8001
"""

from mcp.server.fastmcp import FastMCP
import sys
import json
from pathlib import Path
from typing import Optional

# Add src directory to path (use existing code!)
MEMORY_DIR = Path.home() / ".claude-memory"
sys.path.insert(0, str(MEMORY_DIR))

# Import existing core modules (zero duplicate logic)
try:
    from memory_store_v2 import MemoryStoreV2
    from graph_engine import GraphEngine
    from pattern_learner import PatternLearner
except ImportError as e:
    print(f"Error: Could not import SuperLocalMemory modules: {e}", file=sys.stderr)
    print(f"Ensure SuperLocalMemory V2 is installed at {MEMORY_DIR}", file=sys.stderr)
    sys.exit(1)

# Initialize MCP server
mcp = FastMCP(
    name="SuperLocalMemory V2",
    version="2.1.0-universal"
)

# Database path
DB_PATH = MEMORY_DIR / "memory.db"

# ============================================================================
# MCP TOOLS (Functions callable by AI)
# ============================================================================

@mcp.tool()
async def remember(
    content: str,
    tags: str = "",
    project: str = "",
    importance: int = 5
) -> dict:
    """
    Save content to SuperLocalMemory with intelligent indexing.

    This calls the SAME backend as /superlocalmemoryv2:remember skill.
    All memories are stored in the same local SQLite database.

    Args:
        content: The content to remember (required)
        tags: Comma-separated tags (optional, e.g. "python,api,backend")
        project: Project name (optional, groups related memories)
        importance: Importance score 1-10 (default 5)

    Returns:
        {
            "success": bool,
            "memory_id": int,
            "message": str,
            "content_preview": str
        }

    Examples:
        remember("Use FastAPI for REST APIs", tags="python,backend", project="myapp")
        remember("JWT auth with refresh tokens", tags="security,auth", importance=8)
    """
    try:
        # Use existing MemoryStoreV2 class (no duplicate logic)
        store = MemoryStoreV2(DB_PATH)

        # Call existing add_memory method
        memory_id = store.add_memory(
            content=content,
            tags=tags.split(",") if tags else None,
            project_name=project or None,
            importance=importance
        )

        # Format response
        preview = content[:100] + "..." if len(content) > 100 else content

        return {
            "success": True,
            "memory_id": memory_id,
            "message": f"Memory saved with ID {memory_id}",
            "content_preview": preview
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to save memory"
        }


@mcp.tool()
async def recall(
    query: str,
    limit: int = 10,
    min_score: float = 0.3
) -> dict:
    """
    Search memories using semantic similarity and knowledge graph.

    This calls the SAME backend as /superlocalmemoryv2:recall skill.

    Args:
        query: Search query (required)
        limit: Maximum results to return (default 10)
        min_score: Minimum relevance score 0.0-1.0 (default 0.3)

    Returns:
        {
            "query": str,
            "results": [
                {
                    "id": int,
                    "content": str,
                    "score": float,
                    "tags": list,
                    "project": str,
                    "created_at": str
                }
            ],
            "count": int
        }

    Examples:
        recall("authentication patterns")
        recall("FastAPI", limit=5, min_score=0.5)
    """
    try:
        # Use existing MemoryStoreV2 class
        store = MemoryStoreV2(DB_PATH)

        # Call existing search method
        results = store.search(query, limit=limit)

        # Filter by minimum score
        filtered_results = [
            r for r in results
            if r.get('score', 0) >= min_score
        ]

        return {
            "success": True,
            "query": query,
            "results": filtered_results,
            "count": len(filtered_results),
            "total_searched": len(results)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to search memories",
            "results": [],
            "count": 0
        }


@mcp.tool()
async def list_recent(limit: int = 10) -> dict:
    """
    List most recent memories.

    Args:
        limit: Number of memories to return (default 10)

    Returns:
        {
            "memories": list,
            "count": int
        }
    """
    try:
        # Use existing MemoryStoreV2 class
        store = MemoryStoreV2(DB_PATH)

        # Call existing list_memories method
        memories = store.list_memories(limit=limit)

        return {
            "success": True,
            "memories": memories,
            "count": len(memories)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to list memories",
            "memories": [],
            "count": 0
        }


@mcp.tool()
async def get_status() -> dict:
    """
    Get SuperLocalMemory system status and statistics.

    Returns:
        {
            "total_memories": int,
            "graph_clusters": int,
            "patterns_learned": int,
            "database_size_mb": float
        }
    """
    try:
        # Use existing MemoryStoreV2 class
        store = MemoryStoreV2(DB_PATH)

        # Call existing get_stats method
        stats = store.get_stats()

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get status"
        }


@mcp.tool()
async def build_graph() -> dict:
    """
    Build or rebuild the knowledge graph from existing memories.

    This runs TF-IDF entity extraction and Leiden clustering to
    automatically discover relationships between memories.

    Returns:
        {
            "success": bool,
            "clusters_created": int,
            "memories_processed": int,
            "message": str
        }
    """
    try:
        # Use existing GraphEngine class
        engine = GraphEngine(DB_PATH)

        # Call existing build_graph method
        stats = engine.build_graph()

        return {
            "success": True,
            "message": "Knowledge graph built successfully",
            **stats
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to build graph"
        }


@mcp.tool()
async def switch_profile(name: str) -> dict:
    """
    Switch to a different memory profile.

    Profiles allow you to maintain separate memory contexts
    (e.g., work, personal, client projects).

    Args:
        name: Profile name to switch to

    Returns:
        {
            "success": bool,
            "profile": str,
            "message": str
        }
    """
    try:
        # Profile switching logic (calls existing system)
        profile_path = MEMORY_DIR / "profiles" / name

        if not profile_path.exists():
            return {
                "success": False,
                "message": f"Profile '{name}' does not exist. Use list_profiles() to see available profiles."
            }

        # Update current profile symlink
        current_link = MEMORY_DIR / "current_profile"
        if current_link.exists() or current_link.is_symlink():
            current_link.unlink()
        current_link.symlink_to(profile_path)

        return {
            "success": True,
            "profile": name,
            "message": f"Switched to profile '{name}'. Restart IDE to use new profile."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to switch profile"
        }


# ============================================================================
# MCP RESOURCES (Data endpoints)
# ============================================================================

@mcp.resource("memory://recent/{limit}")
async def get_recent_memories_resource(limit: str) -> str:
    """
    Resource: Get N most recent memories.

    Usage: memory://recent/10
    """
    try:
        store = MemoryStoreV2(DB_PATH)
        memories = store.list_memories(limit=int(limit))
        return json.dumps(memories, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.resource("memory://stats")
async def get_stats_resource() -> str:
    """
    Resource: Get system statistics.

    Usage: memory://stats
    """
    try:
        store = MemoryStoreV2(DB_PATH)
        stats = store.get_stats()
        return json.dumps(stats, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.resource("memory://graph/clusters")
async def get_clusters_resource() -> str:
    """
    Resource: Get knowledge graph clusters.

    Usage: memory://graph/clusters
    """
    try:
        engine = GraphEngine(DB_PATH)
        clusters = engine.get_clusters()
        return json.dumps(clusters, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.resource("memory://patterns/identity")
async def get_coding_identity_resource() -> str:
    """
    Resource: Get learned coding identity and patterns.

    Usage: memory://patterns/identity
    """
    try:
        learner = PatternLearner(DB_PATH)
        patterns = learner.get_context(threshold=0.5)
        return json.dumps(patterns, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ============================================================================
# MCP PROMPTS (Template injection)
# ============================================================================

@mcp.prompt()
async def coding_identity_prompt() -> str:
    """
    Generate prompt with user's learned coding identity.

    Inject this at the start of conversations for personalized assistance
    based on learned preferences and patterns.
    """
    try:
        learner = PatternLearner(DB_PATH)
        patterns = learner.get_context(threshold=0.6)

        if not patterns:
            return "# Coding Identity\n\nNo patterns learned yet. Use remember() to save coding decisions and preferences."

        prompt = "# Your Coding Identity (Learned from History)\n\n"
        prompt += "SuperLocalMemory has learned these patterns from your past decisions:\n\n"

        if 'frameworks' in patterns:
            prompt += f"**Preferred Frameworks:** {', '.join(patterns['frameworks'])}\n"

        if 'style' in patterns:
            prompt += f"**Coding Style:** {', '.join(patterns['style'])}\n"

        if 'testing' in patterns:
            prompt += f"**Testing Approach:** {', '.join(patterns['testing'])}\n"

        if 'api_style' in patterns:
            prompt += f"**API Style:** {', '.join(patterns['api_style'])}\n"

        prompt += "\n*Use this context to provide personalized suggestions aligned with established preferences.*"

        return prompt

    except Exception as e:
        return f"# Coding Identity\n\nError loading patterns: {str(e)}"


@mcp.prompt()
async def project_context_prompt(project_name: str) -> str:
    """
    Generate prompt with project-specific context.

    Args:
        project_name: Name of the project to get context for

    Returns:
        Formatted prompt with relevant project memories
    """
    try:
        store = MemoryStoreV2(DB_PATH)

        # Search for project-related memories
        memories = store.search(f"project:{project_name}", limit=20)

        if not memories:
            return f"# Project Context: {project_name}\n\nNo memories found for this project. Use remember() with project='{project_name}' to save project-specific context."

        prompt = f"# Project Context: {project_name}\n\n"
        prompt += f"Found {len(memories)} relevant memories:\n\n"

        for i, mem in enumerate(memories[:10], 1):
            prompt += f"{i}. {mem['content'][:150]}\n"
            if mem.get('tags'):
                prompt += f"   Tags: {', '.join(mem['tags'])}\n"
            prompt += "\n"

        if len(memories) > 10:
            prompt += f"\n*Showing top 10 of {len(memories)} total memories.*"

        return prompt

    except Exception as e:
        return f"# Project Context: {project_name}\n\nError loading context: {str(e)}"


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="SuperLocalMemory V2 - MCP Server for Universal IDE Integration"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport method: stdio for local IDEs (default), http for remote access"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port for HTTP transport (default 8001)"
    )

    args = parser.parse_args()

    # Print startup message to stderr (stdout is used for MCP protocol)
    print("=" * 60, file=sys.stderr)
    print("SuperLocalMemory V2 - MCP Server", file=sys.stderr)
    print("Version: 2.1.0-universal", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("", file=sys.stderr)
    print(f"Transport: {args.transport}", file=sys.stderr)

    if args.transport == "http":
        print(f"Port: {args.port}", file=sys.stderr)

    print(f"Database: {DB_PATH}", file=sys.stderr)
    print("", file=sys.stderr)
    print("MCP Tools Available:", file=sys.stderr)
    print("  - remember(content, tags, project, importance)", file=sys.stderr)
    print("  - recall(query, limit, min_score)", file=sys.stderr)
    print("  - list_recent(limit)", file=sys.stderr)
    print("  - get_status()", file=sys.stderr)
    print("  - build_graph()", file=sys.stderr)
    print("  - switch_profile(name)", file=sys.stderr)
    print("", file=sys.stderr)
    print("MCP Resources Available:", file=sys.stderr)
    print("  - memory://recent/{limit}", file=sys.stderr)
    print("  - memory://stats", file=sys.stderr)
    print("  - memory://graph/clusters", file=sys.stderr)
    print("  - memory://patterns/identity", file=sys.stderr)
    print("", file=sys.stderr)
    print("MCP Prompts Available:", file=sys.stderr)
    print("  - coding_identity_prompt()", file=sys.stderr)
    print("  - project_context_prompt(project_name)", file=sys.stderr)
    print("", file=sys.stderr)
    print("Status: Starting server...", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("", file=sys.stderr)

    # Run MCP server
    if args.transport == "stdio":
        # stdio transport for local IDEs (default)
        mcp.run(transport="stdio")
    else:
        # HTTP transport for remote access
        print(f"HTTP server will be available at http://localhost:{args.port}", file=sys.stderr)
        mcp.run(transport="http", port=args.port)
