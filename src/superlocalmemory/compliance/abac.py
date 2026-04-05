# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Attribute-Based Access Control for memory operations.

Evaluates policies: (agent_id, profile_id, action) -> allow/deny.
Default: allow all (open access). Policies restrict specific agents.

Actions: "read", "write", "delete", "admin".
Policies are stored in-memory (loaded from DB on init).
Simple deny-list approach: if a deny policy matches, access is blocked.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Valid ABAC actions
VALID_ACTIONS = frozenset({"read", "write", "delete", "admin"})

_POLICY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS abac_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    action TEXT NOT NULL,
    deny INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


class AccessDenied(PermissionError):
    """Raised when ABAC denies an operation."""


class ABACEngine:
    """Attribute-Based Access Control for memory operations.

    Evaluates policies: (agent_id, profile_id, action) -> allow/deny.
    Default: allow all (open access). Deny policies restrict specific
    agent+profile+action combinations.
    """

    def __init__(self, db: Optional[sqlite3.Connection] = None) -> None:
        self._policies: list[dict[str, Any]] = []
        self._db = db
        if db is not None:
            self._load_policies_from_db(db)

    # ------------------------------------------------------------------
    # Policy loading
    # ------------------------------------------------------------------

    def _load_policies_from_db(self, db: sqlite3.Connection) -> None:
        """Load policies from the abac_policies table."""
        try:
            db.execute(_POLICY_TABLE_SQL)
            db.commit()
            rows = db.execute(
                "SELECT profile_id, agent_id, action, deny "
                "FROM abac_policies"
            ).fetchall()
            for row in rows:
                self._policies.append({
                    "profile_id": row[0],
                    "agent_id": row[1],
                    "action": row[2],
                    "deny": bool(row[3]),
                })
            logger.info("Loaded %d ABAC policies from DB", len(self._policies))
        except sqlite3.OperationalError as exc:
            logger.warning("Failed to load ABAC policies: %s", exc)

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def add_policy(
        self,
        profile_id: str,
        agent_id: str,
        action: str,
        deny: bool = True,
    ) -> None:
        """Add an access control policy.

        Args:
            profile_id: Profile this policy applies to.
            agent_id: Agent this policy applies to.
            action: The action to control (read/write/delete/admin).
            deny: If True, this is a deny policy. Default True.
        """
        if action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action '{action}'. Must be one of {VALID_ACTIONS}")
        policy = {
            "profile_id": profile_id,
            "agent_id": agent_id,
            "action": action,
            "deny": deny,
        }
        self._policies.append(policy)
        self._persist_policy(policy)

    def remove_policy(
        self,
        profile_id: str,
        agent_id: str,
        action: str,
    ) -> None:
        """Remove a policy matching profile_id + agent_id + action."""
        self._policies = [
            p for p in self._policies
            if not (
                p["profile_id"] == profile_id
                and p["agent_id"] == agent_id
                and p["action"] == action
            )
        ]
        if self._db is not None:
            try:
                self._db.execute(
                    "DELETE FROM abac_policies WHERE profile_id = ? AND agent_id = ? AND action = ?",
                    (profile_id, agent_id, action),
                )
                self._db.commit()
            except sqlite3.OperationalError:
                pass

    def _persist_policy(self, policy: dict[str, Any]) -> None:
        """Write a policy to DB so it survives restart."""
        if self._db is None:
            return
        try:
            self._db.execute(
                "INSERT INTO abac_policies (profile_id, agent_id, action, deny) "
                "VALUES (?, ?, ?, ?)",
                (policy["profile_id"], policy["agent_id"], policy["action"], int(policy["deny"])),
            )
            self._db.commit()
        except sqlite3.OperationalError as exc:
            logger.warning("Failed to persist ABAC policy: %s", exc)

    # ------------------------------------------------------------------
    # Access evaluation
    # ------------------------------------------------------------------

    def check(self, agent_id: str, profile_id: str, action: str) -> bool:
        """Evaluate access. Returns True if allowed, False if denied.

        Default: allow if no deny policy matches the request.
        Deny-first semantics: any matching deny policy blocks access.
        """
        for policy in self._policies:
            if not policy.get("deny", True):
                continue
            if (
                policy["agent_id"] == agent_id
                and policy["profile_id"] == profile_id
                and policy["action"] == action
            ):
                return False
        return True

    def check_or_raise(
        self,
        agent_id: str,
        profile_id: str,
        action: str,
    ) -> None:
        """Like check() but raises AccessDenied if denied."""
        if not self.check(agent_id, profile_id, action):
            raise AccessDenied(
                f"Agent '{agent_id}' denied '{action}' "
                f"on profile '{profile_id}'"
            )

    # ------------------------------------------------------------------
    # Policy listing
    # ------------------------------------------------------------------

    def list_policies(
        self,
        profile_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List all policies, optionally filtered by profile.

        Args:
            profile_id: If provided, only return policies for this profile.

        Returns:
            List of policy dicts with keys: profile_id, agent_id, action, deny.
        """
        if profile_id is None:
            return [dict(p) for p in self._policies]
        return [
            dict(p) for p in self._policies
            if p["profile_id"] == profile_id
        ]
