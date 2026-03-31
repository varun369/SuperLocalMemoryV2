# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com
"""SuperLocalMemory V3 - Learning Routes
 - MIT License

Routes: /api/learning/status, /api/feedback, /api/feedback/dwell,
        /api/feedback/stats, /api/learning/backup, /api/learning/reset,
        /api/learning/retrain
Uses V3 learning modules: FeedbackCollector, EngagementTracker, AdaptiveLearner.
"""
import shutil
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter

from .helpers import get_active_profile, MEMORY_DIR

logger = logging.getLogger("superlocalmemory.routes.learning")
router = APIRouter()

LEARNING_DB = MEMORY_DIR / "learning.db"

# Feature detection
LEARNING_AVAILABLE = False
try:
    from superlocalmemory.learning.feedback import FeedbackCollector
    from superlocalmemory.learning.engagement import EngagementTracker
    from superlocalmemory.learning.ranker import AdaptiveRanker
    LEARNING_AVAILABLE = True
except ImportError:
    try:
        from superlocalmemory.learning.adaptive import AdaptiveLearner
        LEARNING_AVAILABLE = True
    except ImportError:
        logger.info("V3 learning system not available")

# Lazy singletons
_feedback: FeedbackCollector | None = None
_engagement: EngagementTracker | None = None


def _get_feedback() -> "FeedbackCollector | None":
    global _feedback
    if _feedback is None and LEARNING_AVAILABLE:
        try:
            _feedback = FeedbackCollector(str(LEARNING_DB))
        except Exception:
            pass
    return _feedback


def _get_engagement() -> "EngagementTracker | None":
    global _engagement
    if _engagement is None and LEARNING_AVAILABLE:
        try:
            _engagement = EngagementTracker(str(LEARNING_DB))
        except Exception:
            pass
    return _engagement


@router.get("/api/learning/status")
async def learning_status():
    """Get comprehensive learning system status for dashboard."""
    if not LEARNING_AVAILABLE:
        return {
            "available": False, "ranking_phase": None,
            "stats": None, "tech_preferences": [], "workflow_patterns": [],
            "source_scores": {}, "engagement": None,
            "message": "Learning features not installed.",
        }

    result = {"available": True}

    try:
        active_profile = get_active_profile()
        result["active_profile"] = active_profile

        # Real signal count from V3.1 learning_feedback table
        signal_count = 0
        unique_queries = 0
        try:
            from superlocalmemory.learning.feedback import FeedbackCollector
            from pathlib import Path
            import sqlite3 as _sqlite3
            learning_db = Path.home() / ".superlocalmemory" / "learning.db"
            if learning_db.exists():
                collector = FeedbackCollector(learning_db)
                signal_count = collector.get_feedback_count(active_profile)
                # Count unique queries for the dashboard
                _conn = _sqlite3.connect(str(learning_db))
                _conn.row_factory = _sqlite3.Row
                try:
                    _row = _conn.execute(
                        "SELECT COUNT(DISTINCT query_hash) AS cnt "
                        "FROM learning_feedback WHERE profile_id = ?",
                        (active_profile,),
                    ).fetchone()
                    unique_queries = _row["cnt"] if _row else 0
                except Exception:
                    pass
                finally:
                    _conn.close()
        except Exception:
            pass

        # Ranking phase based on real signal count
        if signal_count >= 200:
            result["ranking_phase"] = "ml_model"
        elif signal_count >= 20:
            result["ranking_phase"] = "rule_based"
        else:
            result["ranking_phase"] = "baseline"

        # Feedback stats — merge old system + new V3.1 signals
        stats_dict = {"feedback_count": signal_count, "unique_queries": unique_queries, "active_profile": active_profile}
        feedback = _get_feedback()
        if feedback:
            try:
                old_stats = feedback.get_feedback_summary(active_profile)
                if isinstance(old_stats, dict):
                    old_stats["feedback_count"] = signal_count
                    old_stats["unique_queries"] = unique_queries
                    old_stats["active_profile"] = active_profile
                    stats_dict = old_stats
            except Exception as exc:
                logger.debug("feedback summary: %s", exc)

        result["stats"] = stats_dict
        result["profile_feedback"] = {
            "profile": active_profile,
            "signals": signal_count,
        }

        # Engagement
        engagement = _get_engagement()
        if engagement:
            try:
                result["engagement"] = engagement.get_engagement_stats()
            except Exception:
                result["engagement"] = None
        else:
            result["engagement"] = None

        # Tech preferences + workflow patterns from V3.1 behavioral store
        try:
            from superlocalmemory.learning.behavioral import BehavioralPatternStore
            from pathlib import Path
            learning_db = Path.home() / ".superlocalmemory" / "learning.db"
            if learning_db.exists():
                store = BehavioralPatternStore(str(learning_db))
                all_patterns = store.get_patterns(profile_id=active_profile)
                tech = [
                    {"key": "tech", "value": p.get("metadata", {}).get("value", p.get("pattern_key", "")),
                     "confidence": p.get("confidence", 0), "evidence": p.get("evidence_count", 0)}
                    for p in all_patterns if p.get("pattern_type") == "tech_preference"
                ]
                workflows = [
                    {"type": p.get("pattern_type"), "key": p.get("pattern_key", ""),
                     "value": p.get("metadata", {}).get("value", ""),
                     "confidence": p.get("confidence", 0)}
                    for p in all_patterns if p.get("pattern_type") in ("temporal", "interest")
                ]
                result["tech_preferences"] = tech
                result["workflow_patterns"] = workflows

                # Privacy stats
                import os
                db_size = os.path.getsize(str(learning_db)) // 1024 if learning_db.exists() else 0
                stats_dict["db_size_kb"] = db_size
                stats_dict["transferable_patterns"] = len(all_patterns)
                stats_dict["models_trained"] = 1 if signal_count >= 200 else 0
                stats_dict["tracked_sources"] = len(set(
                    p.get("pattern_type") for p in all_patterns
                ))
            else:
                result["tech_preferences"] = []
                result["workflow_patterns"] = []
        except Exception:
            result["tech_preferences"] = []
            result["workflow_patterns"] = []
        result["source_scores"] = {}

    except Exception as e:
        logger.error("Error getting learning status: %s", e)
        result["error"] = str(e)

    return result


# ============================================================================
# FEEDBACK ENDPOINTS
# ============================================================================

@router.post("/api/feedback")
async def record_feedback(data: dict):
    """Record explicit feedback from dashboard (thumbs up/down, pin)."""
    if not LEARNING_AVAILABLE:
        return {"success": False, "error": "Learning system not available"}

    memory_id = data.get("memory_id")
    query = data.get("query", "")
    feedback_type = data.get("feedback_type")

    if not memory_id or not feedback_type:
        return {"success": False, "error": "memory_id and feedback_type required"}

    valid_types = {"thumbs_up", "thumbs_down", "pin"}
    if feedback_type not in valid_types:
        return {"success": False, "error": f"Invalid feedback_type. Must be one of: {valid_types}"}

    try:
        feedback = _get_feedback()
        if not feedback:
            return {"success": False, "error": "Feedback collector not initialized"}

        row_id = feedback.record_dashboard_feedback(
            memory_id=str(memory_id), query=query, feedback_type=feedback_type,
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

    if dwell_seconds >= 10.0:
        feedback_type = "dwell_positive"
    elif dwell_seconds < 2.0:
        feedback_type = "dwell_negative"
    else:
        return {"success": True, "message": "Dwell time in neutral range, no signal recorded"}

    try:
        feedback = _get_feedback()
        if not feedback:
            return {"success": False, "error": "Feedback collector not initialized"}

        row_id = feedback.record_dashboard_feedback(
            memory_id=str(memory_id), query=query, feedback_type=feedback_type,
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
            "total_signals": 0, "ranking_phase": "baseline",
            "progress": 0, "target": 200, "available": False,
        }

    try:
        feedback = _get_feedback()
        total = 0
        by_channel = {}
        by_type = {}

        if feedback:
            profile = get_active_profile()
            summary = feedback.get_feedback_summary(profile)
            total = summary.get("total", summary.get("total_signals", 0))
            by_channel = summary.get("by_channel", {})
            by_type = summary.get("by_type", {})

        target = 200
        progress = min(total / target * 100, 100)

        return {
            "total_signals": total, "ranking_phase": "baseline",
            "progress": round(progress, 1), "target": target,
            "by_channel": by_channel, "by_type": by_type, "available": True,
        }
    except Exception as e:
        logger.error("Error getting feedback stats: %s", e)
        return {"total_signals": 0, "ranking_phase": "baseline", "progress": 0, "error": str(e)}


@router.post("/api/learning/backup")
async def learning_backup():
    """Backup learning.db to a timestamped file."""
    try:
        if not LEARNING_DB.exists():
            return {"success": False, "error": "No learning.db found"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"learning.db.backup_{timestamp}"
        backup_path = MEMORY_DIR / backup_name
        shutil.copy2(str(LEARNING_DB), str(backup_path))

        return {
            "success": True, "filename": backup_name,
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
    return {"status": "not_implemented", "message": "Coming soon"}


@router.post("/api/learning/retrain")
async def learning_retrain():
    """Force retrain the ranking model."""
    if not LEARNING_AVAILABLE:
        return {"success": False, "error": "Learning system not available"}
    return {"status": "not_implemented", "message": "Coming soon"}
