# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com
"""SuperLocalMemory V3 - Behavioral Routes
 - Elastic License 2.0

Routes: /api/behavioral/status, /api/behavioral/report-outcome
Uses V3 learning.behavioral.BehavioralPatternStore and learning.outcomes.OutcomeTracker.
"""
import json
import logging

from fastapi import APIRouter

from .helpers import get_active_profile, MEMORY_DIR

logger = logging.getLogger("superlocalmemory.routes.behavioral")
router = APIRouter()

LEARNING_DB = MEMORY_DIR / "learning.db"

# Feature detection
BEHAVIORAL_AVAILABLE = False
try:
    from superlocalmemory.learning.behavioral import BehavioralPatternStore
    from superlocalmemory.learning.outcomes import OutcomeTracker
    BEHAVIORAL_AVAILABLE = True
except ImportError:
    logger.info("V3 behavioral engine not available")


@router.get("/api/behavioral/status")
async def behavioral_status():
    """Get behavioral learning status for active profile."""
    if not BEHAVIORAL_AVAILABLE:
        return {"available": False, "message": "Behavioral engine not available"}

    try:
        profile = get_active_profile()
        db_path = str(LEARNING_DB)

        # Outcomes
        total_outcomes = 0
        outcome_breakdown = {"success": 0, "failure": 0, "partial": 0}
        recent_outcomes = []
        try:
            tracker = OutcomeTracker(db_path)
            all_outcomes = tracker.get_outcomes(profile_id=profile, limit=50)
            total_outcomes = len(all_outcomes)
            for o in all_outcomes:
                key = o.outcome if hasattr(o, 'outcome') else str(o)
                if key in outcome_breakdown:
                    outcome_breakdown[key] += 1
            recent_outcomes = [
                {"outcome": o.outcome, "action_type": o.action_type,
                 "timestamp": o.timestamp}
                for o in all_outcomes[:20]
                if hasattr(o, 'outcome')
            ]
        except Exception as exc:
            logger.debug("outcome tracker: %s", exc)

        # Patterns
        patterns = []
        cross_project_transfers = 0
        try:
            store = BehavioralPatternStore(db_path)
            patterns = store.get_patterns(profile_id=profile)
            cross_project_transfers = 0
        except Exception as exc:
            logger.debug("pattern store: %s", exc)

        return {
            "available": True,
            "active_profile": profile,
            "total_outcomes": total_outcomes,
            "outcome_breakdown": outcome_breakdown,
            "patterns": patterns,
            "cross_project_transfers": cross_project_transfers,
            "recent_outcomes": recent_outcomes,
            "stats": {
                "success_count": outcome_breakdown.get("success", 0),
                "failure_count": outcome_breakdown.get("failure", 0),
                "partial_count": outcome_breakdown.get("partial", 0),
                "patterns_count": len(patterns),
            },
        }
    except Exception as e:
        logger.error("behavioral_status error: %s", e)
        return {"available": False, "error": str(e)}


@router.post("/api/behavioral/report-outcome")
async def report_outcome(data: dict):
    """Record an action outcome for behavioral learning.

    Body: {
        memory_ids: [str, ...],
        outcome: "success" | "failure" | "partial",
        action_type: str (optional),
        context: str (optional)
    }
    """
    if not BEHAVIORAL_AVAILABLE:
        return {"success": False, "error": "Behavioral engine not available"}

    memory_ids = data.get('memory_ids')
    outcome = data.get('outcome')
    action_type = data.get('action_type', 'other')
    context_note = data.get('context', '')

    if not memory_ids or not isinstance(memory_ids, list):
        return {"success": False, "error": "memory_ids must be a non-empty list"}

    valid_outcomes = ("success", "failure", "partial")
    if outcome not in valid_outcomes:
        return {"success": False, "error": f"outcome must be one of: {valid_outcomes}"}

    try:
        profile = get_active_profile()
        tracker = OutcomeTracker(str(LEARNING_DB))

        context_dict = {"note": context_note} if context_note else {}
        row_id = tracker.record_outcome(
            memory_ids=memory_ids,
            outcome=outcome,
            action_type=action_type,
            context=context_dict,
            project=profile,
        )

        if row_id is None:
            return {"success": False, "error": "Failed to record outcome"}

        return {
            "success": True, "outcome_id": row_id,
            "active_profile": profile,
            "message": f"Recorded {outcome} outcome for {len(memory_ids)} memories",
        }
    except Exception as e:
        logger.error("report_outcome error: %s", e)
        return {"success": False, "error": str(e)}
