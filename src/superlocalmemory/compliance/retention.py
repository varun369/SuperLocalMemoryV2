# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Named retention rules engine for compliance (GDPR, HIPAA, custom).

Rules are bound to profiles. Each rule specifies a retention period
in days. The engine can identify expired facts and enforce deletion.

Retention rules are stored in a dedicated SQLite table and operate
independently of the main memory lifecycle system.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

_RETENTION_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS retention_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    days INTEGER NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_id, rule_name)
)
"""

_FACTS_TABLE_CHECK = """
SELECT name FROM sqlite_master
WHERE type='table' AND name='atomic_facts'
"""


class RetentionEngine:
    """Named retention rules for compliance (GDPR, HIPAA, custom).

    Rules are bound to profiles. Each rule specifies a retention period.
    The engine can identify expired facts and enforce deletion.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._ensure_table()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        """Create the retention_rules table if it does not exist."""
        self._db.execute(_RETENTION_RULES_TABLE)
        self._db.commit()

    def _has_facts_table(self) -> bool:
        """Check if atomic_facts table exists in the database."""
        row = self._db.execute(_FACTS_TABLE_CHECK).fetchone()
        return row is not None

    @staticmethod
    def _age_in_days(created_at_str: str) -> float:
        """Calculate age from an ISO timestamp string to now, in days."""
        try:
            created = datetime.fromisoformat(created_at_str)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return (now - created).total_seconds() / 86400.0
        except (ValueError, TypeError):
            return 0.0

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(
        self,
        profile_id: str,
        rule_name: str,
        days: int,
        description: str = "",
    ) -> None:
        """Add a retention rule to a profile.

        Args:
            profile_id: Profile this rule applies to.
            rule_name: Human-readable name (e.g. 'GDPR-30d').
            days: Retention period in days.
            description: Optional description of the rule.

        Raises:
            sqlite3.IntegrityError: If rule_name already exists for profile.
        """
        self._db.execute(
            "INSERT OR REPLACE INTO retention_rules "
            "(profile_id, rule_name, days, description) "
            "VALUES (?, ?, ?, ?)",
            (profile_id, rule_name, days, description),
        )
        self._db.commit()
        logger.info(
            "Added retention rule '%s' (%d days) to profile '%s'",
            rule_name, days, profile_id,
        )

    def remove_rule(self, profile_id: str, rule_name: str) -> None:
        """Remove a retention rule.

        Args:
            profile_id: Profile the rule belongs to.
            rule_name: Name of the rule to remove.
        """
        self._db.execute(
            "DELETE FROM retention_rules "
            "WHERE profile_id = ? AND rule_name = ?",
            (profile_id, rule_name),
        )
        self._db.commit()
        logger.info(
            "Removed retention rule '%s' from profile '%s'",
            rule_name, profile_id,
        )

    def get_rules(self, profile_id: str) -> list[dict[str, Any]]:
        """Get all retention rules for a profile.

        Args:
            profile_id: Profile to query rules for.

        Returns:
            List of rule dicts with keys: rule_name, days, description.
        """
        rows = self._db.execute(
            "SELECT rule_name, days, description, created_at "
            "FROM retention_rules WHERE profile_id = ? "
            "ORDER BY id",
            (profile_id,),
        ).fetchall()
        return [
            {
                "rule_name": r[0],
                "days": r[1],
                "description": r[2],
                "created_at": r[3],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Expiration detection
    # ------------------------------------------------------------------

    def get_expired_facts(self, profile_id: str) -> list[str]:
        """Get fact IDs that have exceeded their retention period.

        Checks each fact's created_at against the profile's shortest
        retention rule. A fact is expired if its age exceeds the
        minimum retention days across all rules for the profile.

        Args:
            profile_id: Profile to check facts for.

        Returns:
            List of expired fact IDs (as strings).
        """
        rules = self.get_rules(profile_id)
        if not rules:
            return []

        # Use the shortest retention period (most restrictive)
        min_days = min(r["days"] for r in rules)

        if not self._has_facts_table():
            return []

        rows = self._db.execute(
            "SELECT id, created_at FROM atomic_facts "
            "WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()

        expired: list[str] = []
        for row in rows:
            fact_id = str(row[0])
            created_at = row[1] if len(row) > 1 else None
            if created_at and self._age_in_days(created_at) > min_days:
                expired.append(fact_id)

        return expired

    # ------------------------------------------------------------------
    # Enforcement
    # ------------------------------------------------------------------

    def enforce(self, profile_id: str) -> dict[str, Any]:
        """Enforce retention rules — delete expired facts.

        Finds all expired facts for the profile and deletes them.

        Args:
            profile_id: Profile to enforce rules on.

        Returns:
            Dict with keys: deleted_count, expired_ids, profile_id.
        """
        expired_ids = self.get_expired_facts(profile_id)
        deleted_count = 0

        if expired_ids and self._has_facts_table():
            placeholders = ",".join("?" for _ in expired_ids)
            self._db.execute(
                f"DELETE FROM atomic_facts WHERE id IN ({placeholders})",
                [int(fid) for fid in expired_ids],
            )
            self._db.commit()
            deleted_count = len(expired_ids)
            logger.info(
                "Retention enforcement: deleted %d facts from profile '%s'",
                deleted_count, profile_id,
            )

        return {
            "profile_id": profile_id,
            "deleted_count": deleted_count,
            "expired_ids": expired_ids,
        }
