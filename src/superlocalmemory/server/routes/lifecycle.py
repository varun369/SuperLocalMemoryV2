# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com
"""SuperLocalMemory V3 - Lifecycle Routes
 - MIT License

Routes: /api/lifecycle/status, /api/lifecycle/compact
Uses V3 compliance.lifecycle.LifecycleManager.
"""
import json
import logging
import sqlite3

from fastapi import APIRouter

from .helpers import get_active_profile, MEMORY_DIR, DB_PATH

logger = logging.getLogger("superlocalmemory.routes.lifecycle")
router = APIRouter()

# Feature detection
LIFECYCLE_AVAILABLE = False
try:
    from superlocalmemory.compliance.lifecycle import LifecycleManager
    LIFECYCLE_AVAILABLE = True
except ImportError:
    logger.info("V3 lifecycle engine not available")


@router.get("/api/lifecycle/status")
async def lifecycle_status():
    """Get lifecycle state distribution for active profile."""
    if not LIFECYCLE_AVAILABLE:
        return {"available": False, "message": "Lifecycle engine not available"}

    try:
        profile = get_active_profile()
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row

        # V3.3: Use fact_retention.lifecycle_zone (Ebbinghaus-driven, authoritative)
        # Falls back to atomic_facts.lifecycle for pre-3.3 databases
        states = {}
        try:
            rows = conn.execute(
                "SELECT lifecycle_zone, COUNT(*) as cnt "
                "FROM fact_retention WHERE profile_id = ? GROUP BY lifecycle_zone",
                (profile,),
            ).fetchall()
            if rows:
                states = {
                    row['lifecycle_zone']: row['cnt']
                    for row in rows
                }
        except sqlite3.OperationalError:
            pass

        if not states:
            # Fallback: V3.0-3.2 schema (atomic_facts.lifecycle column)
            try:
                rows = conn.execute(
                    "SELECT lifecycle, COUNT(*) as cnt "
                    "FROM atomic_facts WHERE profile_id = ? GROUP BY lifecycle",
                    (profile,),
                ).fetchall()
                states = {
                    (row['lifecycle'] or 'active'): row['cnt']
                    for row in rows
                }
            except sqlite3.OperationalError:
                # V2 fallback: memories table
                try:
                    rows = conn.execute(
                        "SELECT lifecycle, COUNT(*) as cnt "
                        "FROM memories WHERE profile = ? GROUP BY lifecycle",
                        (profile,),
                    ).fetchall()
                    states = {
                        (row['lifecycle'] or 'active'): row['cnt']
                        for row in rows
                    }
                except sqlite3.OperationalError:
                    # No lifecycle column at all — count everything as active
                    total = conn.execute(
                    "SELECT COUNT(*) FROM atomic_facts WHERE profile_id = ?",
                    (profile,),
                ).fetchone()[0]
                states = {'active': total}

        total = sum(states.values())

        # Age distribution per state (V3.3: join fact_retention with atomic_facts)
        age_stats = {}
        for state in ('active', 'warm', 'cold', 'archive', 'forgotten'):
            try:
                row = conn.execute(
                    "SELECT AVG(julianday('now') - julianday(af.created_at)) as avg_age, "
                    "MIN(julianday('now') - julianday(af.created_at)) as min_age, "
                    "MAX(julianday('now') - julianday(af.created_at)) as max_age "
                    "FROM fact_retention fr "
                    "JOIN atomic_facts af ON fr.fact_id = af.fact_id "
                    "WHERE fr.profile_id = ? AND fr.lifecycle_zone = ?",
                    (profile, state),
                ).fetchone()
                if row and row['avg_age'] is not None:
                    age_stats[state] = {
                        'avg_days': round(row['avg_age'], 1),
                        'min_days': round(row['min_age'], 1),
                        'max_days': round(row['max_age'], 1),
                    }
            except sqlite3.OperationalError:
                pass

        conn.close()

        return {
            "available": True,
            "active_profile": profile,
            "total_memories": total,
            "states": states,
            "recent_transitions": [],
            "age_stats": age_stats,
        }
    except Exception as e:
        logger.error("lifecycle_status error: %s", e)
        return {"available": False, "error": str(e)}


@router.post("/api/lifecycle/compact")
async def trigger_compaction(data: dict = {}):
    """Trigger lifecycle compaction. Body: {dry_run: true/false}."""
    if not LIFECYCLE_AVAILABLE:
        return {"success": False, "error": "Lifecycle engine not available"}

    return {"status": "not_implemented", "message": "Coming soon"}
