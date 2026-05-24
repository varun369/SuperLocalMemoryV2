# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory v3.4.5 — Graph Pruning Engine.

Reduces graph edge count without losing meaningful connections.
Strategies:
  1. Chain collapse: A→B→C → remove B→C if A→B exists with higher weight
  2. Garbage entity removal: remove edges connected to garbage entities
  3. Low-activity edge decay: edges between entities not accessed in 90+ days

CRITICAL RULE: NEVER delete atomic_facts. Only prune graph_edges.
Edges are derivable from facts — they can be regenerated.
Facts are the permanent record.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from superlocalmemory.storage.database import DatabaseManager

logger = logging.getLogger(__name__)

# Thresholds
LOW_ACTIVITY_DAYS = 90
CHAIN_COLLAPSE_MIN_WEIGHT_RATIO = 0.8
BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def prune_graph(
    db: DatabaseManager,
    profile_id: str = "default",
    dry_run: bool = False,
) -> dict[str, int]:
    """Prune graph edges using all strategies.

    Returns counts of edges removed per strategy.
    Safe to run repeatedly — idempotent.
    """
    stats = {
        "chain_collapsed": 0,
        "garbage_removed": 0,
        "low_activity_decayed": 0,
        "total_removed": 0,
        "edges_before": 0,
        "edges_after": 0,
    }

    # Count before
    rows = db.execute(
        "SELECT COUNT(*) as c FROM graph_edges", ()
    )
    stats["edges_before"] = rows[0]["c"] if rows else 0

    # Strategy 1: Chain collapse
    collapsed = _collapse_chains(db, profile_id, dry_run)
    stats["chain_collapsed"] = collapsed

    # Strategy 2: Garbage entity edges
    garbage = _remove_garbage_edges(db, profile_id, dry_run)
    stats["garbage_removed"] = garbage

    # Strategy 3: Low-activity edge decay
    decayed = _decay_low_activity_edges(db, profile_id, dry_run)
    stats["low_activity_decayed"] = decayed

    stats["total_removed"] = collapsed + garbage + decayed

    # Count after
    rows = db.execute(
        "SELECT COUNT(*) as c FROM graph_edges", ()
    )
    stats["edges_after"] = rows[0]["c"] if rows else 0

    if stats["total_removed"] > 0:
        logger.info(
            "Graph pruning: %d edges removed (%d → %d)",
            stats["total_removed"], stats["edges_before"], stats["edges_after"],
        )

    return stats


# ---------------------------------------------------------------------------
# Strategy 1: Chain Collapse
# ---------------------------------------------------------------------------

def _collapse_chains(db: DatabaseManager, profile_id: str, dry_run: bool) -> int:
    """Collapse redundant chain edges.

    If A→B (weight=0.9) and B→C (weight=0.5), and A→C also exists,
    remove B→C if A→C weight >= B→C weight * threshold.

    This preserves the semantic connection (A→C is stronger) while
    removing intermediate edges.
    """
    try:
        rows = db.execute("""
            SELECT ge1.source_id as a, ge1.target_id as b, ge1.weight as w_ab,
                   ge2.source_id as b2, ge2.target_id as c, ge2.weight as w_bc,
                   ge3.weight as w_ac
            FROM graph_edges ge1
            JOIN graph_edges ge2 ON ge1.target_id = ge2.source_id
            LEFT JOIN graph_edges ge3 ON ge1.source_id = ge3.source_id
                                       AND ge2.target_id = ge3.target_id
            WHERE ge3.weight >= ge2.weight * ?
            LIMIT ?
        """, (CHAIN_COLLAPSE_MIN_WEIGHT_RATIO, BATCH_SIZE))
    except Exception as exc:
        logger.warning("Chain collapse query failed: %s", exc)
        return 0

    remove_ids = []
    for row in rows:
        b_id = row["b"]
        c_id = row["c"]
        # Remove B→C edge
        if not dry_run:
            db.execute(
                "DELETE FROM graph_edges WHERE source_id = ? AND target_id = ?",
                (b_id, c_id),
            )
        remove_ids.append((b_id, c_id))

    if remove_ids and not dry_run:
        logger.info("Chain collapse: removed %d edges", len(remove_ids))

    return len(remove_ids)


# ---------------------------------------------------------------------------
# Strategy 2: Garbage Entity Edges
# ---------------------------------------------------------------------------

def _remove_garbage_edges(db: DatabaseManager, profile_id: str, dry_run: bool) -> int:
    """Remove edges connected to garbage/blacklisted entities."""
    try:
        rows = db.execute("""
            SELECT ge.source_id, ge.target_id
            FROM graph_edges ge
            WHERE ge.source_id IN (SELECT term FROM entity_blacklist)
               OR ge.target_id IN (SELECT term FROM entity_blacklist)
            LIMIT ?
        """, (BATCH_SIZE,))
    except Exception:
        return 0

    count = 0
    for row in rows:
        if not dry_run:
            db.execute(
                "DELETE FROM graph_edges WHERE source_id = ? AND target_id = ?",
                (row["source_id"], row["target_id"]),
            )
        count += 1

    if count and not dry_run:
        logger.info("Garbage edges removed: %d", count)

    return count


# ---------------------------------------------------------------------------
# Strategy 3: Low-Activity Edge Decay
# ---------------------------------------------------------------------------

def _decay_low_activity_edges(
    db: DatabaseManager, profile_id: str, dry_run: bool,
) -> int:
    """Remove edges between entities not accessed in 90+ days.

    Only removes edges where BOTH connected entities have no recent access.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=LOW_ACTIVITY_DAYS)).isoformat()

    try:
        rows = db.execute("""
            SELECT ge.source_id, ge.target_id
            FROM graph_edges ge
            WHERE ge.source_id NOT IN (
                SELECT DISTINCT entity_id FROM fact_access_log
                WHERE accessed_at >= ?
            )
            AND ge.target_id NOT IN (
                SELECT DISTINCT entity_id FROM fact_access_log
                WHERE accessed_at >= ?
            )
            LIMIT ?
        """, (cutoff, cutoff, BATCH_SIZE))
    except Exception:
        return 0

    count = 0
    for row in rows:
        if not dry_run:
            db.execute(
                "DELETE FROM graph_edges WHERE source_id = ? AND target_id = ?",
                (row["source_id"], row["target_id"]),
            )
        count += 1

    if count and not dry_run:
        logger.info("Low-activity edges decayed: %d", count)

    return count
