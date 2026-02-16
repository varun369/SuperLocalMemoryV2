#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Learning API Routes (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
"""

import sys
import logging
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger("superlocalmemory.routes.learning")

router = APIRouter()

# Import learning system (graceful fallback)
LEARNING_AVAILABLE = False
try:
    MEMORY_DIR = Path.home() / ".claude-memory"
    if str(MEMORY_DIR) not in sys.path:
        sys.path.insert(0, str(MEMORY_DIR))
    # Try installed location first
    from learning import (
        get_learning_db, get_adaptive_ranker, get_feedback_collector,
        get_engagement_tracker, get_status as get_learning_system_status,
    )
    LEARNING_AVAILABLE = True
except ImportError:
    # Try repo src/ location
    try:
        REPO_SRC = Path(__file__).parent.parent / "src"
        if str(REPO_SRC) not in sys.path:
            sys.path.insert(0, str(REPO_SRC))
        from learning import (
            get_learning_db, get_adaptive_ranker, get_feedback_collector,
            get_engagement_tracker, get_status as get_learning_system_status,
        )
        LEARNING_AVAILABLE = True
    except ImportError:
        logger.info("Learning system not available (missing dependencies)")


@router.get("/api/learning/status")
async def learning_status():
    """Get comprehensive learning system status for dashboard."""
    if not LEARNING_AVAILABLE:
        return {
            "available": False,
            "ranking_phase": None,
            "stats": None,
            "tech_preferences": [],
            "workflow_patterns": [],
            "source_scores": {},
            "engagement": None,
            "message": "Learning features not installed. Run: pip3 install lightgbm scipy"
        }

    result = {"available": True}

    try:
        # v2.7.4: Detect active profile
        active_profile = "default"
        try:
            import json as _json
            profiles_path = MEMORY_DIR / "profiles.json"
            if profiles_path.exists():
                with open(profiles_path, 'r') as f:
                    active_profile = _json.load(f).get('active_profile', 'default')
        except Exception:
            pass
        result["active_profile"] = active_profile

        # System status
        status = get_learning_system_status()
        result["stats"] = status.get("learning_db_stats")
        result["dependencies"] = status.get("dependencies")

        # Auto-mine: if learning.db has zero patterns but memories exist, mine now
        ldb = get_learning_db()
        if ldb:
            stats = result["stats"] or {}
            has_no_patterns = (stats.get("transferable_patterns", 0) == 0
                              and stats.get("workflow_patterns", 0) == 0)
            if has_no_patterns:
                try:
                    import sqlite3
                    mem_db = MEMORY_DIR / "memory.db"
                    if mem_db.exists():
                        conn = sqlite3.connect(str(mem_db))
                        mem_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                        conn.close()
                        if mem_count >= 10:
                            logger.info("Auto-mining patterns from %d memories (first run)", mem_count)
                            try:
                                from learning.cross_project_aggregator import CrossProjectAggregator
                                CrossProjectAggregator(learning_db=ldb).aggregate_all_profiles()
                            except Exception as e:
                                logger.warning("Auto-mine aggregator failed: %s", e)
                            try:
                                from learning.workflow_pattern_miner import WorkflowPatternMiner
                                WorkflowPatternMiner(learning_db=ldb).mine_all()
                            except Exception as e:
                                logger.warning("Auto-mine workflow failed: %s", e)
                            try:
                                from learning.source_quality_scorer import SourceQualityScorer
                                SourceQualityScorer(learning_db=ldb).compute_source_scores()
                            except Exception as e:
                                logger.warning("Auto-mine source quality failed: %s", e)
                            # Refresh stats after mining
                            result["stats"] = ldb.get_stats()
                except Exception as e:
                    logger.warning("Auto-mine check failed: %s", e)

        # Ranking phase
        ranker = get_adaptive_ranker()
        if ranker:
            result["ranking_phase"] = ranker.get_phase()
        else:
            result["ranking_phase"] = "baseline"

        # Tech preferences (Layer 1) — profile-scoped in v2.7.4
        if ldb:
            patterns = ldb.get_transferable_patterns(min_confidence=0.3, profile_scoped=True)
            result["tech_preferences"] = [
                {
                    "id": p["id"],
                    "key": p["key"],
                    "value": p["value"],
                    "confidence": round(p["confidence"], 3),
                    "evidence": p["evidence_count"],
                    "profiles_seen": p["profiles_seen"],
                }
                for p in patterns
            ]

            # Workflow patterns (Layer 3) — profile-scoped in v2.7.4
            workflows = ldb.get_workflow_patterns(min_confidence=0.2, profile_scoped=True)
            result["workflow_patterns"] = [
                {
                    "id": p["id"],
                    "type": p["pattern_type"],
                    "key": p["pattern_key"],
                    "value": p["pattern_value"],
                    "confidence": round(p["confidence"], 3),
                    "count": p["evidence_count"],
                }
                for p in workflows
            ]

            # Source quality scores — profile-scoped in v2.7.4
            result["source_scores"] = ldb.get_source_scores(profile_scoped=True)

        # v2.7.4: Profile-scoped feedback stats
        if ldb:
            try:
                profile_count = ldb.get_feedback_count(profile_scoped=True)
                profile_queries = ldb.get_unique_query_count(profile_scoped=True)
                total_count = ldb.get_feedback_count(profile_scoped=False)
                result["profile_feedback"] = {
                    "profile": active_profile,
                    "signals": profile_count,
                    "unique_queries": profile_queries,
                    "total_signals": total_count,
                }
                # Override stats feedback_count with profile-scoped version
                if result.get("stats"):
                    result["stats"]["feedback_count"] = profile_count
                    result["stats"]["active_profile"] = active_profile
            except Exception as e:
                logger.warning("Profile feedback stats failed: %s", e)

        # Engagement
        tracker = get_engagement_tracker()
        if tracker:
            result["engagement"] = tracker.get_engagement_stats()
        else:
            result["engagement"] = None

    except Exception as e:
        logger.error("Error getting learning status: %s", e)
        result["error"] = str(e)

    return result


# ============================================================================
# FEEDBACK ENDPOINTS (v2.7.4 — Silent Learning)
# ============================================================================

@router.post("/api/feedback")
async def record_feedback(data: dict):
    """Record explicit feedback from dashboard (thumbs up/down, pin)."""
    if not LEARNING_AVAILABLE:
        return {"success": False, "error": "Learning system not available"}

    memory_id = data.get("memory_id")
    query = data.get("query", "")
    feedback_type = data.get("feedback_type")  # thumbs_up, thumbs_down, pin

    if not memory_id or not feedback_type:
        return {"success": False, "error": "memory_id and feedback_type required"}

    # Validate feedback_type
    valid_types = {"thumbs_up", "thumbs_down", "pin"}
    if feedback_type not in valid_types:
        return {"success": False, "error": f"Invalid feedback_type. Must be one of: {valid_types}"}

    try:
        feedback = get_feedback_collector()
        if not feedback:
            return {"success": False, "error": "Feedback collector not initialized"}

        row_id = feedback.record_dashboard_feedback(
            memory_id=int(memory_id),
            query=query,
            feedback_type=feedback_type,
        )

        return {
            "success": True,
            "message": f"Feedback recorded: {feedback_type} for memory #{memory_id}",
            "feedback_id": row_id,
        }
    except Exception as e:
        logger.error("Error recording feedback: %s", e)
        return {"success": False, "error": str(e)}


@router.post("/api/feedback/dwell")
async def record_dwell(data: dict):
    """Record dwell time feedback from dashboard modal."""
    if not LEARNING_AVAILABLE:
        return {"success": False, "error": "Learning system not available"}

    memory_id = data.get("memory_id")
    query = data.get("query", "")
    dwell_time = data.get("dwell_time", 0)

    if not memory_id:
        return {"success": False, "error": "memory_id required"}

    try:
        dwell_seconds = float(dwell_time)
    except (ValueError, TypeError):
        return {"success": False, "error": "dwell_time must be a number"}

    # Infer signal type from dwell time
    if dwell_seconds >= 10.0:
        feedback_type = "dwell_positive"
    elif dwell_seconds < 2.0:
        feedback_type = "dwell_negative"
    else:
        # 2-10 seconds is ambiguous — don't record
        return {"success": True, "message": "Dwell time in neutral range, no signal recorded"}

    try:
        feedback = get_feedback_collector()
        if not feedback:
            return {"success": False, "error": "Feedback collector not initialized"}

        row_id = feedback.record_dashboard_feedback(
            memory_id=int(memory_id),
            query=query,
            feedback_type=feedback_type,
            dwell_time=dwell_seconds,
        )

        return {
            "success": True,
            "message": f"Dwell feedback recorded: {feedback_type} ({dwell_seconds:.1f}s)",
            "feedback_id": row_id,
        }
    except Exception as e:
        logger.error("Error recording dwell: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/api/feedback/stats")
async def feedback_stats():
    """Get feedback signal statistics for dashboard progress bar."""
    if not LEARNING_AVAILABLE:
        return {
            "total_signals": 0,
            "ranking_phase": "baseline",
            "progress": 0,
            "target": 200,
            "available": False,
        }

    try:
        feedback = get_feedback_collector()
        ldb = get_learning_db()
        ranker = get_adaptive_ranker()

        total = 0
        phase = "baseline"
        by_channel = {}
        by_type = {}

        if feedback:
            summary = feedback.get_feedback_summary()
            total = summary.get("total_signals", 0)
            by_channel = summary.get("by_channel", {})
            by_type = summary.get("by_type", {})

        if ranker:
            phase = ranker.get_phase()

        # Calculate progress toward ML phase
        target = 200
        progress = min(total / target * 100, 100)

        return {
            "total_signals": total,
            "ranking_phase": phase,
            "progress": round(progress, 1),
            "target": target,
            "by_channel": by_channel,
            "by_type": by_type,
            "available": True,
        }
    except Exception as e:
        logger.error("Error getting feedback stats: %s", e)
        return {"total_signals": 0, "ranking_phase": "baseline", "progress": 0, "error": str(e)}


@router.post("/api/learning/backup")
async def learning_backup():
    """Backup learning.db to a timestamped file."""
    import shutil
    from datetime import datetime

    try:
        learning_db_path = MEMORY_DIR / "learning.db"
        if not learning_db_path.exists():
            return {"success": False, "error": "No learning.db found"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"learning.db.backup_{timestamp}"
        backup_path = MEMORY_DIR / backup_name
        shutil.copy2(str(learning_db_path), str(backup_path))

        return {
            "success": True,
            "filename": backup_name,
            "path": str(backup_path),
            "message": f"Learning DB backed up to {backup_name}",
        }
    except Exception as e:
        logger.error("Error backing up learning DB: %s", e)
        return {"success": False, "error": str(e)}


@router.post("/api/learning/reset")
async def learning_reset():
    """Reset all learning data. Memories preserved."""
    if not LEARNING_AVAILABLE:
        return {"success": False, "error": "Learning system not available"}

    try:
        ldb = get_learning_db()
        if ldb:
            ldb.reset()
            return {"success": True, "message": "Learning data reset. Memories preserved."}
        return {"success": False, "error": "Learning database not initialized"}
    except Exception as e:
        logger.error("Error resetting learning: %s", e)
        return {"success": False, "error": str(e)}


@router.post("/api/learning/retrain")
async def learning_retrain():
    """Force retrain the ranking model."""
    if not LEARNING_AVAILABLE:
        return {"success": False, "error": "Learning system not available"}

    try:
        ranker = get_adaptive_ranker()
        if ranker:
            result = ranker.train(force=True)
            if result:
                return {"success": True, "message": "Model retrained", "metadata": result}
            return {"success": False, "message": "Insufficient data for training"}
        return {"success": False, "error": "Ranker not initialized"}
    except Exception as e:
        logger.error("Error retraining: %s", e)
        return {"success": False, "error": str(e)}
