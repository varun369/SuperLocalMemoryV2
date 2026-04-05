#!/usr/bin/env python3
# SPDX-License-Identifier: Elastic-2.0
# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Part of Qualixar | Author: Varun Pratap Bhardwaj (qualixar.com | varunpratap.com)
"""
EngagementTracker -- Local-only engagement metrics for V3 learning.

Tracks user engagement events per profile:
    - recall_count, store_count, delete_count
    - session_count, active_days
    - composite engagement_score
    - health classification: active / warm / cold / inactive

All data stays local.  Uses direct sqlite3 with a self-contained
``engagement_events`` table.  NOT coupled to V3 DatabaseManager.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("superlocalmemory.learning.engagement")

# Valid event types
VALID_EVENT_TYPES = frozenset({"recall", "store", "delete", "session_start"})

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS engagement_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id   TEXT    NOT NULL,
    event_type   TEXT    NOT NULL,
    created_at   TEXT    NOT NULL
)
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_engagement_profile
    ON engagement_events (profile_id, event_type)
"""

# Health thresholds (events in last 7 days)
_ACTIVE_THRESHOLD = 10
_WARM_THRESHOLD = 3


def _utcnow_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _today_iso() -> str:
    """Return today's date as ISO-8601 string."""
    return date.today().isoformat()


class EngagementTracker:
    """
    Tracks per-profile engagement events for the V3 learning system.

    Each instance owns a sqlite3 database at *db_path*.
    Thread-safe: all writes serialised through a lock.

    Args:
        db_path: Path to the sqlite3 database file.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._lock = threading.Lock()
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute(_CREATE_TABLE)
            conn.execute(_CREATE_INDEX)
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Public API: record events
    # ------------------------------------------------------------------

    def record_event(self, profile_id: str, event_type: str) -> Optional[int]:
        """
        Record an engagement event.

        Args:
            profile_id: Profile that generated the event.
            event_type: One of ``recall``, ``store``, ``delete``,
                        ``session_start``.

        Returns:
            Row ID of the inserted record, or None on invalid input.
        """
        if not profile_id:
            return None
        if event_type not in VALID_EVENT_TYPES:
            logger.warning("Invalid event type: %r", event_type)
            return None

        now = _utcnow_iso()
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    "INSERT INTO engagement_events "
                    "(profile_id, event_type, created_at) VALUES (?, ?, ?)",
                    (profile_id, event_type, now),
                )
                conn.commit()
                return cursor.lastrowid
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Public API: stats
    # ------------------------------------------------------------------

    def get_stats(self, profile_id: str) -> Dict[str, Any]:
        """
        Return engagement statistics for a profile.

        Returns:
            Dict with keys: recall_count, store_count, delete_count,
            session_count, active_days, total_events, engagement_score.
        """
        conn = self._connect()
        try:
            # Count by event type
            rows = conn.execute(
                "SELECT event_type, COUNT(*) AS cnt "
                "FROM engagement_events WHERE profile_id = ? "
                "GROUP BY event_type",
                (profile_id,),
            ).fetchall()
            counts: Dict[str, int] = {r["event_type"]: r["cnt"] for r in rows}

            recall_count = counts.get("recall", 0)
            store_count = counts.get("store", 0)
            delete_count = counts.get("delete", 0)
            session_count = counts.get("session_start", 0)
            total_events = sum(counts.values())

            # Active days: count distinct dates
            active_days = self._count_active_days(conn, profile_id)

            # Composite engagement score
            score = self._compute_engagement_score(
                recall_count=recall_count,
                store_count=store_count,
                session_count=session_count,
                active_days=active_days,
            )

            return {
                "recall_count": recall_count,
                "store_count": store_count,
                "delete_count": delete_count,
                "session_count": session_count,
                "active_days": active_days,
                "total_events": total_events,
                "engagement_score": round(score, 4),
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Public API: health
    # ------------------------------------------------------------------

    def get_health(self, profile_id: str) -> str:
        """
        Classify engagement health for a profile.

        Uses events in the last 7 days:
            - **active**: >= 10 events
            - **warm**: >= 3 events
            - **cold**: >= 1 event
            - **inactive**: 0 events

        Args:
            profile_id: Profile to check.

        Returns:
            One of ``"active"``, ``"warm"``, ``"cold"``, ``"inactive"``.
        """
        recent = self._count_recent_events(profile_id, days=7)

        if recent >= _ACTIVE_THRESHOLD:
            return "active"
        if recent >= _WARM_THRESHOLD:
            return "warm"
        if recent >= 1:
            return "cold"
        return "inactive"

    # ------------------------------------------------------------------
    # Public API: weekly summary
    # ------------------------------------------------------------------

    def get_weekly_summary(self, profile_id: str) -> Dict[str, Any]:
        """
        Summarise the last 7 days of engagement.

        Returns:
            Dict with period_start, period_end, total_events,
            by_type, active_days.
        """
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=7)
        ).isoformat()

        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT event_type, COUNT(*) AS cnt "
                "FROM engagement_events "
                "WHERE profile_id = ? AND created_at >= ? "
                "GROUP BY event_type",
                (profile_id, cutoff),
            ).fetchall()
            by_type = {r["event_type"]: r["cnt"] for r in rows}
            total = sum(by_type.values())

            # Active days in the window
            day_rows = conn.execute(
                "SELECT COUNT(DISTINCT SUBSTR(created_at, 1, 10)) "
                "FROM engagement_events "
                "WHERE profile_id = ? AND created_at >= ?",
                (profile_id, cutoff),
            ).fetchone()
            active_days = day_rows[0] if day_rows else 0

            return {
                "period_start": (date.today() - timedelta(days=6)).isoformat(),
                "period_end": _today_iso(),
                "total_events": total,
                "by_type": by_type,
                "active_days": active_days,
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _count_active_days(
        self,
        conn: sqlite3.Connection,
        profile_id: str,
    ) -> int:
        """Count distinct dates with at least one event."""
        row = conn.execute(
            "SELECT COUNT(DISTINCT SUBSTR(created_at, 1, 10)) "
            "FROM engagement_events WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        return row[0] if row else 0

    def _count_recent_events(self, profile_id: str, days: int = 7) -> int:
        """Count events in the last *days* days."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).isoformat()

        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM engagement_events "
                "WHERE profile_id = ? AND created_at >= ?",
                (profile_id, cutoff),
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    @staticmethod
    def _compute_engagement_score(
        recall_count: int,
        store_count: int,
        session_count: int,
        active_days: int,
    ) -> float:
        """
        Compute a composite engagement score in [0.0, 1.0].

        Weighted sum normalised by a soft ceiling:
            raw = 0.4 * recall + 0.3 * store + 0.2 * session + 0.1 * days
            score = raw / (raw + 20)   (sigmoid-like saturation at ~20)

        This gives:
            - 0 activity  -> 0.0
            - 20 events   -> ~0.5
            - 100 events  -> ~0.83
        """
        raw = (
            0.4 * recall_count
            + 0.3 * store_count
            + 0.2 * session_count
            + 0.1 * active_days
        )
        if raw <= 0:
            return 0.0
        return raw / (raw + 20.0)
