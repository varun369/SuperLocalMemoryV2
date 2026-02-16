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
from mcp.types import ToolAnnotations
import sys
import os
import json
import re
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

# Agent Registry + Provenance (v2.5+)
try:
    from agent_registry import AgentRegistry
    from provenance_tracker import ProvenanceTracker
    PROVENANCE_AVAILABLE = True
except ImportError:
    PROVENANCE_AVAILABLE = False

# Trust Scorer (v2.6 — enforcement)
try:
    from trust_scorer import TrustScorer
    TRUST_AVAILABLE = True
except ImportError:
    TRUST_AVAILABLE = False

# Learning System (v2.7+)
try:
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from learning import get_learning_db, get_adaptive_ranker, get_feedback_collector, get_engagement_tracker, get_status as get_learning_status
    from learning import FULL_LEARNING_AVAILABLE, ML_RANKING_AVAILABLE
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False

# ============================================================================
# Synthetic Bootstrap Auto-Trigger (v2.7 — P1-12)
# Runs ONCE on first recall if: memory count > 50, no model, LightGBM available.
# Spawns in background thread — never blocks recall. All errors swallowed.
# ============================================================================

_bootstrap_checked = False


def _maybe_bootstrap():
    """Check if synthetic bootstrap is needed and run it in a background thread.

    Called once from the first recall invocation. Sets _bootstrap_checked = True
    immediately to prevent re-entry. The actual bootstrap runs in a daemon thread
    so it never blocks the recall response.

    Conditions for bootstrap:
        1. LEARNING_AVAILABLE and ML_RANKING_AVAILABLE flags are True
        2. SyntheticBootstrapper.should_bootstrap() returns True (checks:
           - LightGBM + NumPy installed
           - No existing model file at ~/.claude-memory/models/ranker.txt
           - Memory count > 50)

    CRITICAL: This function wraps everything in try/except. Bootstrap failure
    must NEVER break recall. It is purely an optimization — first-time ML
    model creation so users don't have to wait 200+ recalls for personalization.
    """
    global _bootstrap_checked
    _bootstrap_checked = True  # Set immediately to prevent re-entry

    try:
        if not LEARNING_AVAILABLE:
            return
        if not ML_RANKING_AVAILABLE:
            return

        from learning.synthetic_bootstrap import SyntheticBootstrapper
        bootstrapper = SyntheticBootstrapper(memory_db_path=DB_PATH)

        if not bootstrapper.should_bootstrap():
            return

        # Run bootstrap in background thread — never block recall
        import threading

        def _run_bootstrap():
            try:
                result = bootstrapper.bootstrap_model()
                if result:
                    import logging
                    logging.getLogger("superlocalmemory.mcp").info(
                        "Synthetic bootstrap complete: %d samples",
                        result.get('training_samples', 0)
                    )
            except Exception:
                pass  # Bootstrap failure is never critical

        thread = threading.Thread(target=_run_bootstrap, daemon=True)
        thread.start()

    except Exception:
        pass  # Any failure in bootstrap setup is swallowed silently


def _sanitize_error(error: Exception) -> str:
    """Strip internal paths and structure from error messages."""
    msg = str(error)
    # Strip file paths containing claude-memory
    msg = re.sub(r'/[\w./-]*claude-memory[\w./-]*', '[internal-path]', msg)
    # Strip file paths containing SuperLocalMemory
    msg = re.sub(r'/[\w./-]*SuperLocalMemory[\w./-]*', '[internal-path]', msg)
    # Strip SQLite table names from error messages
    msg = re.sub(r'table\s+\w+', 'table [redacted]', msg)
    return msg


# Parse command line arguments early (needed for port in constructor)
import argparse as _argparse
_parser = _argparse.ArgumentParser(add_help=False)
_parser.add_argument("--transport", default="stdio")
_parser.add_argument("--port", type=int, default=8417)
_pre_args, _ = _parser.parse_known_args()

# Initialize MCP server
mcp = FastMCP(
    name="SuperLocalMemory V2",
    host="127.0.0.1",
    port=_pre_args.port,
)

# Database path
DB_PATH = MEMORY_DIR / "memory.db"

# ============================================================================
# Shared singleton instances (v2.5 — fixes per-call instantiation overhead)
# All MCP tool handlers share one MemoryStoreV2 instance instead of creating
# a new one per call. This means one ConnectionManager, one TF-IDF vectorizer,
# one write queue — shared across all concurrent MCP requests.
# ============================================================================

_store = None
_graph_engine = None
_pattern_learner = None


def get_store() -> MemoryStoreV2:
    """Get or create the shared MemoryStoreV2 singleton."""
    global _store
    if _store is None:
        _store = MemoryStoreV2(DB_PATH)
    return _store


def get_graph_engine() -> GraphEngine:
    """Get or create the shared GraphEngine singleton."""
    global _graph_engine
    if _graph_engine is None:
        _graph_engine = GraphEngine(DB_PATH)
    return _graph_engine


def get_pattern_learner() -> PatternLearner:
    """Get or create the shared PatternLearner singleton."""
    global _pattern_learner
    if _pattern_learner is None:
        _pattern_learner = PatternLearner(DB_PATH)
    return _pattern_learner


_agent_registry = None
_provenance_tracker = None


def get_agent_registry():
    """Get shared AgentRegistry singleton (v2.5+). Returns None if unavailable."""
    global _agent_registry
    if not PROVENANCE_AVAILABLE:
        return None
    if _agent_registry is None:
        _agent_registry = AgentRegistry.get_instance(DB_PATH)
    return _agent_registry


def get_provenance_tracker():
    """Get shared ProvenanceTracker singleton (v2.5+). Returns None if unavailable."""
    global _provenance_tracker
    if not PROVENANCE_AVAILABLE:
        return None
    if _provenance_tracker is None:
        _provenance_tracker = ProvenanceTracker.get_instance(DB_PATH)
    return _provenance_tracker


_trust_scorer = None


def get_trust_scorer():
    """Get shared TrustScorer singleton (v2.6+). Returns None if unavailable."""
    global _trust_scorer
    if not TRUST_AVAILABLE:
        return None
    if _trust_scorer is None:
        _trust_scorer = TrustScorer.get_instance(DB_PATH)
    return _trust_scorer


def get_learning_components():
    """Get learning system components. Returns None if unavailable."""
    if not LEARNING_AVAILABLE:
        return None
    return {
        'db': get_learning_db(),
        'ranker': get_adaptive_ranker(),
        'feedback': get_feedback_collector(),
        'engagement': get_engagement_tracker(),
    }


def _register_mcp_agent(agent_name: str = "mcp-client"):
    """Register the calling MCP agent and record activity. Non-blocking."""
    registry = get_agent_registry()
    if registry:
        try:
            registry.register_agent(
                agent_id=f"mcp:{agent_name}",
                agent_name=agent_name,
                protocol="mcp",
            )
        except Exception:
            pass


# ============================================================================
# MCP TOOLS (Functions callable by AI)
# ============================================================================

@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    openWorldHint=False,
))
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
        # Register MCP agent (v2.5 — agent tracking)
        _register_mcp_agent()

        # Trust enforcement (v2.6) — block untrusted agents from writing
        try:
            trust = get_trust_scorer()
            if trust and not trust.check_trust("mcp:mcp-client", "write"):
                return {
                    "success": False,
                    "error": "Agent trust score too low for write operations",
                    "message": "Trust enforcement blocked this operation"
                }
        except Exception:
            pass  # Trust check failure should not block operations

        # Use existing MemoryStoreV2 class (no duplicate logic)
        store = get_store()

        # Call existing add_memory method
        memory_id = store.add_memory(
            content=content,
            tags=tags.split(",") if tags else None,
            project_name=project or None,
            importance=importance
        )

        # Record provenance (v2.5 — who created this memory)
        prov = get_provenance_tracker()
        if prov:
            try:
                prov.record_provenance(memory_id, created_by="mcp:client", source_protocol="mcp")
            except Exception:
                pass

        # Track write in agent registry
        registry = get_agent_registry()
        if registry:
            try:
                registry.record_write("mcp:mcp-client")
            except Exception:
                pass

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
            "error": _sanitize_error(e),
            "message": "Failed to save memory"
        }


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
))
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
        store = get_store()

        # Hybrid search (opt-in via env var, v2.6)
        _use_hybrid = os.environ.get('SLM_HYBRID_SEARCH', 'false').lower() == 'true'
        if _use_hybrid:
            try:
                from hybrid_search import HybridSearchEngine
                engine = HybridSearchEngine(store=store)
                results = engine.search(query, limit=limit)
            except (ImportError, Exception):
                results = store.search(query, limit=limit)
        else:
            results = store.search(query, limit=limit)

        # v2.7: Auto-trigger synthetic bootstrap on first recall (P1-12)
        if not _bootstrap_checked:
            _maybe_bootstrap()

        # v2.7: Learning-based re-ranking (optional, graceful fallback)
        if LEARNING_AVAILABLE:
            try:
                ranker = get_adaptive_ranker()
                if ranker:
                    results = ranker.rerank(results, query)
            except Exception:
                pass  # Re-ranking failure must never break recall

        # Track recall for passive feedback decay
        if LEARNING_AVAILABLE:
            try:
                feedback = get_feedback_collector()
                if feedback:
                    feedback.record_recall_results(query, [r.get('id') for r in results if r.get('id')])
                tracker = get_engagement_tracker()
                if tracker:
                    tracker.record_activity('recall_performed', source='mcp')
            except Exception:
                pass  # Tracking failure must never break recall

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
            "error": _sanitize_error(e),
            "message": "Failed to search memories",
            "results": [],
            "count": 0
        }


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
))
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
        store = get_store()

        # Call existing list_all method
        memories = store.list_all(limit=limit)

        return {
            "success": True,
            "memories": memories,
            "count": len(memories)
        }

    except Exception as e:
        return {
            "success": False,
            "error": _sanitize_error(e),
            "message": "Failed to list memories",
            "memories": [],
            "count": 0
        }


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
))
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
        store = get_store()

        # Call existing get_stats method
        stats = store.get_stats()

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        return {
            "success": False,
            "error": _sanitize_error(e),
            "message": "Failed to get status"
        }


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    openWorldHint=False,
))
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
        engine = get_graph_engine()

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
            "error": _sanitize_error(e),
            "message": "Failed to build graph"
        }


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    openWorldHint=False,
))
async def switch_profile(name: str) -> dict:
    """
    Switch to a different memory profile.

    Profiles allow you to maintain separate memory contexts
    (e.g., work, personal, client projects). All profiles share
    one database — switching is instant and safe (no data copying).

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
        # Import profile manager (uses column-based profiles)
        sys.path.insert(0, str(MEMORY_DIR))
        from importlib import import_module
        # Use direct JSON config update for speed
        import json
        config_file = MEMORY_DIR / "profiles.json"

        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {'profiles': {'default': {'name': 'default', 'description': 'Default memory profile'}}, 'active_profile': 'default'}

        if name not in config.get('profiles', {}):
            available = ', '.join(config.get('profiles', {}).keys())
            return {
                "success": False,
                "message": f"Profile '{name}' not found. Available: {available}"
            }

        old_profile = config.get('active_profile', 'default')
        config['active_profile'] = name

        from datetime import datetime
        config['profiles'][name]['last_used'] = datetime.now().isoformat()

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        return {
            "success": True,
            "profile": name,
            "previous_profile": old_profile,
            "message": f"Switched to profile '{name}'. Memory operations now use this profile."
        }

    except Exception as e:
        return {
            "success": False,
            "error": _sanitize_error(e),
            "message": "Failed to switch profile"
        }


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
))
async def backup_status() -> dict:
    """
    Get auto-backup system status for SuperLocalMemory.

    Returns backup configuration, last backup time, next scheduled backup,
    total backup count, and storage used. Useful for monitoring data safety.

    Returns:
        {
            "enabled": bool,
            "interval_display": str,
            "last_backup": str or null,
            "next_backup": str or null,
            "backup_count": int,
            "total_size_mb": float
        }
    """
    try:
        from auto_backup import AutoBackup
        backup = AutoBackup()
        status = backup.get_status()
        return {
            "success": True,
            **status
        }
    except ImportError:
        return {
            "success": False,
            "message": "Auto-backup module not installed. Update SuperLocalMemory to v2.4.0+.",
            "enabled": False,
            "backup_count": 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": _sanitize_error(e),
            "message": "Failed to get backup status"
        }


# ============================================================================
# LEARNING TOOLS (v2.7 — feedback, transparency, user control)
# ============================================================================

@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    openWorldHint=False,
))
async def memory_used(
    memory_id: int,
    query: str = "",
    usefulness: str = "high"
) -> dict:
    """
    Signal that a recalled memory was useful. Call this when you reference
    or apply a memory from recall results in your response.

    This helps SuperLocalMemory learn which memories are most relevant
    and improves future recall results.

    Args:
        memory_id: ID of the useful memory
        query: The recall query that found it (optional)
        usefulness: How useful - "high", "medium", or "low" (default "high")

    Returns:
        {"success": bool, "message": str}
    """
    try:
        if not LEARNING_AVAILABLE:
            return {"success": False, "message": "Learning features not available. Install: pip3 install lightgbm scipy"}

        feedback = get_feedback_collector()
        if feedback is None:
            return {"success": False, "message": "Feedback collector not initialized"}

        feedback.record_memory_used(
            memory_id=memory_id,
            query=query,
            usefulness=usefulness,
            source_tool="mcp-client",
        )

        return {
            "success": True,
            "message": f"Feedback recorded for memory #{memory_id} (usefulness: {usefulness})"
        }
    except Exception as e:
        return {"success": False, "error": _sanitize_error(e)}


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
))
async def get_learned_patterns(
    min_confidence: float = 0.6,
    category: str = "all"
) -> dict:
    """
    See what SuperLocalMemory has learned about your preferences,
    projects, and workflow patterns.

    Args:
        min_confidence: Minimum confidence threshold 0.0-1.0 (default 0.6)
        category: Filter by "tech", "workflow", "project", or "all" (default "all")

    Returns:
        {
            "success": bool,
            "patterns": {
                "tech_preferences": [...],
                "workflow_patterns": [...],
            },
            "ranking_phase": str,
            "feedback_count": int
        }
    """
    try:
        if not LEARNING_AVAILABLE:
            return {"success": False, "message": "Learning features not available. Install: pip3 install lightgbm scipy", "patterns": {}}

        ldb = get_learning_db()
        if ldb is None:
            return {"success": False, "message": "Learning database not initialized", "patterns": {}}

        result = {"success": True, "patterns": {}}

        # Tech preferences (Layer 1)
        if category in ("all", "tech"):
            patterns = ldb.get_transferable_patterns(min_confidence=min_confidence)
            result["patterns"]["tech_preferences"] = [
                {
                    "id": p["id"],
                    "type": p["pattern_type"],
                    "key": p["key"],
                    "value": p["value"],
                    "confidence": round(p["confidence"], 2),
                    "evidence": p["evidence_count"],
                    "profiles_seen": p["profiles_seen"],
                }
                for p in patterns
            ]

        # Workflow patterns (Layer 3)
        if category in ("all", "workflow"):
            workflows = ldb.get_workflow_patterns(min_confidence=min_confidence)
            result["patterns"]["workflow_patterns"] = [
                {
                    "id": p["id"],
                    "type": p["pattern_type"],
                    "key": p["pattern_key"],
                    "value": p["pattern_value"],
                    "confidence": round(p["confidence"], 2),
                }
                for p in workflows
            ]

        # Ranking phase info
        ranker = get_adaptive_ranker()
        if ranker:
            result["ranking_phase"] = ranker.get_phase()
            result["feedback_count"] = ldb.get_feedback_count()

        # Learning stats
        result["stats"] = ldb.get_stats()

        return result
    except Exception as e:
        return {"success": False, "error": _sanitize_error(e), "patterns": {}}


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    openWorldHint=False,
))
async def correct_pattern(
    pattern_id: int,
    correct_value: str,
    reason: str = ""
) -> dict:
    """
    Correct a learned pattern that is wrong. Use get_learned_patterns first
    to see pattern IDs.

    Args:
        pattern_id: ID of the pattern to correct
        correct_value: The correct value (e.g., "Vue" instead of "React")
        reason: Why the correction (optional)

    Returns:
        {"success": bool, "message": str}
    """
    try:
        if not LEARNING_AVAILABLE:
            return {"success": False, "message": "Learning features not available"}

        ldb = get_learning_db()
        if ldb is None:
            return {"success": False, "message": "Learning database not initialized"}

        # Get existing pattern
        conn = ldb._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM transferable_patterns WHERE id = ?', (pattern_id,))
            pattern = cursor.fetchone()
            if not pattern:
                return {"success": False, "message": f"Pattern #{pattern_id} not found"}

            old_value = pattern['value']

            # Update the pattern with correction
            ldb.upsert_transferable_pattern(
                pattern_type=pattern['pattern_type'],
                key=pattern['key'],
                value=correct_value,
                confidence=1.0,  # User correction = maximum confidence
                evidence_count=pattern['evidence_count'] + 1,
                profiles_seen=pattern['profiles_seen'],
                contradictions=[f"Corrected from '{old_value}' to '{correct_value}': {reason}"],
            )

            # Record as negative feedback for the old value
            feedback = get_feedback_collector()
            if feedback:
                feedback.record_memory_used(
                    memory_id=0,  # No specific memory
                    query=f"correction:{pattern['key']}",
                    usefulness="low",
                    source_tool="mcp-correction",
                )

            return {
                "success": True,
                "message": f"Pattern '{pattern['key']}' corrected: '{old_value}' → '{correct_value}'"
            }
        finally:
            conn.close()
    except Exception as e:
        return {"success": False, "error": _sanitize_error(e)}


# ============================================================================
# CHATGPT CONNECTOR TOOLS (search + fetch — required by OpenAI MCP spec)
# These two tools are required for ChatGPT Connectors and Deep Research.
# They wrap existing SuperLocalMemory search/retrieval logic.
# Ref: https://platform.openai.com/docs/mcp
# ============================================================================

@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
))
async def search(query: str) -> dict:
    """
    Search for documents in SuperLocalMemory.

    Required by ChatGPT Connectors and Deep Research.
    Returns a list of search results with id, title, text snippet, and url.

    Args:
        query: Search query string. Natural language queries work best.

    Returns:
        {"results": [{"id": str, "title": str, "text": str, "url": str}]}
    """
    try:
        store = get_store()
        raw_results = store.search(query, limit=20)

        # v2.7: Learning-based re-ranking (optional, graceful fallback)
        if LEARNING_AVAILABLE:
            try:
                ranker = get_adaptive_ranker()
                if ranker:
                    raw_results = ranker.rerank(raw_results, query)
            except Exception:
                pass  # Re-ranking failure must never break search

        results = []
        for r in raw_results:
            if r.get('score', 0) < 0.2:
                continue
            content = r.get('content', '') or r.get('summary', '') or ''
            snippet = content[:200] + "..." if len(content) > 200 else content
            mem_id = str(r.get('id', ''))
            title = r.get('category', 'Memory') + ': ' + (content[:60].replace('\n', ' ') if content else 'Untitled')
            results.append({
                "id": mem_id,
                "title": title,
                "text": snippet,
                "url": f"memory://local/{mem_id}"
            })

        return {"results": results}

    except Exception as e:
        return {"results": [], "error": _sanitize_error(e)}


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
))
async def fetch(id: str) -> dict:
    """
    Retrieve full content of a memory by ID.

    Required by ChatGPT Connectors and Deep Research.
    Use after search() to get complete document content for analysis and citation.

    Args:
        id: Memory ID from search results.

    Returns:
        {"id": str, "title": str, "text": str, "url": str, "metadata": dict|null}
    """
    try:
        store = get_store()
        mem = store.get_by_id(int(id))

        if not mem:
            raise ValueError(f"Memory with ID {id} not found")

        content = mem.get('content', '') or mem.get('summary', '') or ''
        title = (mem.get('category', 'Memory') or 'Memory') + ': ' + (content[:60].replace('\n', ' ') if content else 'Untitled')

        metadata = {}
        if mem.get('tags'):
            metadata['tags'] = mem['tags']
        if mem.get('project_name'):
            metadata['project'] = mem['project_name']
        if mem.get('importance'):
            metadata['importance'] = mem['importance']
        if mem.get('cluster_id'):
            metadata['cluster_id'] = mem['cluster_id']
        if mem.get('created_at'):
            metadata['created_at'] = mem['created_at']

        return {
            "id": str(id),
            "title": title,
            "text": content,
            "url": f"memory://local/{id}",
            "metadata": metadata if metadata else None
        }

    except Exception as e:
        raise ValueError(f"Failed to fetch memory {id}: {_sanitize_error(e)}")


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
        store = get_store()
        memories = store.list_all(limit=int(limit))
        return json.dumps(memories, indent=2)
    except Exception as e:
        return json.dumps({"error": _sanitize_error(e)}, indent=2)


@mcp.resource("memory://stats")
async def get_stats_resource() -> str:
    """
    Resource: Get system statistics.

    Usage: memory://stats
    """
    try:
        store = get_store()
        stats = store.get_stats()
        return json.dumps(stats, indent=2)
    except Exception as e:
        return json.dumps({"error": _sanitize_error(e)}, indent=2)


@mcp.resource("memory://graph/clusters")
async def get_clusters_resource() -> str:
    """
    Resource: Get knowledge graph clusters.

    Usage: memory://graph/clusters
    """
    try:
        engine = get_graph_engine()
        stats = engine.get_stats()
        clusters = stats.get('clusters', [])
        return json.dumps(clusters, indent=2)
    except Exception as e:
        return json.dumps({"error": _sanitize_error(e)}, indent=2)


@mcp.resource("memory://patterns/identity")
async def get_coding_identity_resource() -> str:
    """
    Resource: Get learned coding identity and patterns.

    Usage: memory://patterns/identity
    """
    try:
        learner = get_pattern_learner()
        patterns = learner.get_identity_context(min_confidence=0.5)
        return json.dumps(patterns, indent=2)
    except Exception as e:
        return json.dumps({"error": _sanitize_error(e)}, indent=2)


@mcp.resource("memory://learning/status")
async def get_learning_status_resource() -> str:
    """
    Resource: Get learning system status.

    Usage: memory://learning/status
    """
    try:
        if not LEARNING_AVAILABLE:
            return json.dumps({"available": False, "message": "Learning deps not installed"}, indent=2)
        status = get_learning_status()
        return json.dumps(status, indent=2)
    except Exception as e:
        return json.dumps({"error": _sanitize_error(e)}, indent=2)


@mcp.resource("memory://engagement")
async def get_engagement_resource() -> str:
    """
    Resource: Get engagement metrics.

    Usage: memory://engagement
    """
    try:
        if not LEARNING_AVAILABLE:
            return json.dumps({"available": False}, indent=2)
        tracker = get_engagement_tracker()
        if tracker:
            stats = tracker.get_engagement_stats()
            return json.dumps(stats, indent=2)
        return json.dumps({"available": False}, indent=2)
    except Exception as e:
        return json.dumps({"error": _sanitize_error(e)}, indent=2)


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
        learner = get_pattern_learner()
        patterns = learner.get_identity_context(min_confidence=0.6)

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
        return f"# Coding Identity\n\nError loading patterns: {_sanitize_error(e)}"


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
        store = get_store()

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
        return f"# Project Context: {project_name}\n\nError loading context: {_sanitize_error(e)}"


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
        choices=["stdio", "http", "sse", "streamable-http"],
        default="stdio",
        help="Transport method: stdio for local IDEs (default), sse/streamable-http for ChatGPT and remote access"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8417,
        help="Port for HTTP transport (default 8417)"
    )

    args = parser.parse_args()

    # Print startup message to stderr (stdout is used for MCP protocol)
    print("=" * 60, file=sys.stderr)
    print("SuperLocalMemory V2 - MCP Server", file=sys.stderr)
    print("Version: 2.7.0", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("Created by: Varun Pratap Bhardwaj (Solution Architect)", file=sys.stderr)
    print("Repository: https://github.com/varun369/SuperLocalMemoryV2", file=sys.stderr)
    print("License: MIT (attribution required - see ATTRIBUTION.md)", file=sys.stderr)
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
    print("  - search(query)          [ChatGPT Connector]", file=sys.stderr)
    print("  - fetch(id)              [ChatGPT Connector]", file=sys.stderr)
    print("  - list_recent(limit)", file=sys.stderr)
    print("  - get_status()", file=sys.stderr)
    print("  - build_graph()", file=sys.stderr)
    print("  - switch_profile(name)", file=sys.stderr)
    print("  - backup_status()        [Auto-Backup]", file=sys.stderr)
    if LEARNING_AVAILABLE:
        print("  - memory_used(memory_id, query, usefulness)  [v2.7 Learning]", file=sys.stderr)
        print("  - get_learned_patterns(min_confidence, category) [v2.7 Learning]", file=sys.stderr)
        print("  - correct_pattern(pattern_id, correct_value) [v2.7 Learning]", file=sys.stderr)
    print("", file=sys.stderr)
    print("MCP Resources Available:", file=sys.stderr)
    print("  - memory://recent/{limit}", file=sys.stderr)
    print("  - memory://stats", file=sys.stderr)
    print("  - memory://graph/clusters", file=sys.stderr)
    print("  - memory://patterns/identity", file=sys.stderr)
    if LEARNING_AVAILABLE:
        print("  - memory://learning/status", file=sys.stderr)
        print("  - memory://engagement", file=sys.stderr)
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
    elif args.transport == "streamable-http":
        # Streamable HTTP transport (recommended for ChatGPT 2026+)
        print(f"Streamable HTTP server at http://localhost:{args.port}", file=sys.stderr)
        print("ChatGPT setup: expose via ngrok, paste URL in Settings > Connectors", file=sys.stderr)
        mcp.run(transport="streamable-http")
    else:
        # SSE transport for remote access (ChatGPT, web clients)
        # "http" is accepted as alias for "sse"
        print(f"HTTP/SSE server will be available at http://localhost:{args.port}", file=sys.stderr)
        print("ChatGPT setup: expose via ngrok, paste URL in Settings > Connectors", file=sys.stderr)
        mcp.run(transport="sse")
