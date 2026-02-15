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
        # System status
        status = get_learning_system_status()
        result["stats"] = status.get("learning_db_stats")
        result["dependencies"] = status.get("dependencies")

        # Ranking phase
        ranker = get_adaptive_ranker()
        if ranker:
            result["ranking_phase"] = ranker.get_phase()
        else:
            result["ranking_phase"] = "baseline"

        # Tech preferences (Layer 1)
        ldb = get_learning_db()
        if ldb:
            patterns = ldb.get_transferable_patterns(min_confidence=0.3)
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

            # Workflow patterns (Layer 3)
            workflows = ldb.get_workflow_patterns(min_confidence=0.2)
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

            # Source quality scores
            result["source_scores"] = ldb.get_source_scores()

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
