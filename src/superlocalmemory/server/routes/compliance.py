# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com
"""SuperLocalMemory V3 - Compliance Routes
 - Elastic License 2.0

Routes: /api/compliance/status, /api/compliance/audit,
        /api/compliance/retention-policy
Uses V3 compliance modules: ABACEngine, AuditChain, RetentionEngine.
"""
import json
import logging
import sqlite3
from typing import Optional

from fastapi import APIRouter, Query

from .helpers import get_active_profile, MEMORY_DIR, DB_PATH

logger = logging.getLogger("superlocalmemory.routes.compliance")
router = APIRouter()

AUDIT_DB = MEMORY_DIR / "audit.db"

# Feature detection
COMPLIANCE_AVAILABLE = False
try:
    from superlocalmemory.compliance.audit import AuditChain
    from superlocalmemory.compliance.retention import RetentionEngine
    from superlocalmemory.compliance.abac import ABACEngine
    COMPLIANCE_AVAILABLE = True
except ImportError:
    logger.info("V3 compliance engine not available")


@router.get("/api/compliance/status")
async def compliance_status():
    """Get compliance engine status for active profile."""
    if not COMPLIANCE_AVAILABLE:
        return {"available": False, "message": "Compliance engine not available"}

    try:
        profile = get_active_profile()

        # Audit events
        audit_events_count = 0
        recent_audit_events = []
        try:
            audit = AuditChain(str(AUDIT_DB))
            audit_events_count = audit.count_events()
            recent_audit_events = audit.get_recent_events(limit=30)
        except Exception as exc:
            logger.debug("audit chain: %s", exc)

        # Retention policies
        retention_policies = []
        try:
            conn = sqlite3.connect(str(DB_PATH))
            engine = RetentionEngine(conn)
            retention_policies = engine.list_rules()
            conn.close()
        except Exception as exc:
            logger.debug("retention engine: %s", exc)

        # ABAC policies
        abac_policies_count = 0
        try:
            abac = ABACEngine()
            abac_policies_count = len(abac._policies)
        except Exception:
            pass

        return {
            "available": True,
            "active_profile": profile,
            "audit_events_count": audit_events_count,
            "recent_audit_events": recent_audit_events,
            "retention_policies": retention_policies,
            "abac_policies_count": abac_policies_count,
        }
    except Exception as e:
        logger.error("compliance_status error: %s", e)
        return {"available": False, "error": str(e)}


@router.get("/api/compliance/audit")
async def query_audit_trail(
    limit: int = Query(default=50, ge=1, le=500),
    event_type: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
):
    """Query audit trail events with optional filters."""
    if not COMPLIANCE_AVAILABLE:
        return {"available": False, "error": "Compliance engine not available"}

    try:
        audit = AuditChain(str(AUDIT_DB))
        events = audit.get_recent_events(
            limit=limit, event_type=event_type, since=since,
        )

        return {
            "available": True, "events": events, "total": len(events),
            "filters": {"event_type": event_type, "since": since, "limit": limit},
        }
    except Exception as e:
        logger.error("query_audit_trail error: %s", e)
        return {"available": False, "error": str(e)}


@router.post("/api/compliance/retention-policy")
async def create_retention_policy(data: dict):
    """Create a compliance retention policy.

    Body: {
        name: str,
        retention_days: int,
        category: str (maps to framework),
        action: "archive" | "tombstone" | "notify",
        applies_to: dict (optional)
    }
    """
    if not COMPLIANCE_AVAILABLE:
        return {"success": False, "error": "Compliance engine not available"}

    name = data.get('name')
    retention_days = data.get('retention_days')
    framework = data.get('category', 'custom')
    action = data.get('action')
    applies_to = data.get('applies_to', {})

    if not name or not isinstance(name, str):
        return {"success": False, "error": "name is required (string)"}
    if not isinstance(retention_days, int) or retention_days < 1:
        return {"success": False, "error": "retention_days must be a positive integer"}

    valid_actions = ("archive", "tombstone", "notify")
    if action not in valid_actions:
        return {"success": False, "error": f"action must be one of: {valid_actions}"}

    try:
        profile = get_active_profile()
        conn = sqlite3.connect(str(DB_PATH))
        engine = RetentionEngine(conn)

        rule_id = engine.create_rule(
            name=name, framework=framework,
            retention_days=retention_days, action=action,
            applies_to=applies_to, profile_id=profile,
        )
        conn.close()

        return {
            "success": True, "rule_id": rule_id,
            "active_profile": profile,
            "message": f"Retention policy '{name}' created ({retention_days}d, {action})",
        }
    except Exception as e:
        logger.error("create_retention_policy error: %s", e)
        return {"success": False, "error": str(e)}
