#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Engagement Tracker (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Repository: https://github.com/varun369/SuperLocalMemoryV2
Author: Varun Pratap Bhardwaj (Solution Architect)

NOTICE: This software is protected by MIT License.
Attribution must be preserved in all copies or derivatives.
"""

"""
EngagementTracker — Local-only engagement metrics.

Measures how actively the user interacts with the memory system.
All data stays local — NEVER transmitted anywhere.

Capabilities:
    - Comprehensive engagement stats (days active, staleness, per-day rates)
    - Health status classification (HEALTHY / DECLINING / AT_RISK / INACTIVE)
    - Activity recording (delegates to LearningDB.increment_engagement)
    - Weekly summary aggregation
    - CLI-friendly formatted output for `slm engagement`
    - MCP resource exposure (read-only stats)

Data sources:
    - memory.db  (read-only) — creation dates, total count, source agents
    - learning.db (read/write via LearningDB) — feedback counts, patterns,
      engagement_metrics daily rows

Design:
    - Thread-safe: each method opens/closes its own connection
    - Division-by-zero safe: all ratios default to 0.0 for empty databases
    - Graceful degradation: works even if learning.db does not exist yet
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger("superlocalmemory.learning.engagement")

MEMORY_DIR = Path.home() / ".claude-memory"
MEMORY_DB_PATH = MEMORY_DIR / "memory.db"


class EngagementTracker:
    """
    Local-only engagement metrics for the SuperLocalMemory system.

    Usage:
        tracker = EngagementTracker()
        stats = tracker.get_engagement_stats()
        print(tracker.format_for_cli())

    Thread-safe: all methods use per-call connections.
    """

    def __init__(
        self,
        memory_db_path: Optional[Path] = None,
        learning_db: Optional[Any] = None,
    ):
        """
        Initialize EngagementTracker.

        Args:
            memory_db_path: Path to memory.db. Defaults to
                ~/.claude-memory/memory.db. Opened read-only.
            learning_db: A LearningDB instance for reading/writing
                engagement metrics. If None, lazily created on first use.
        """
        self._memory_db_path = (
            Path(memory_db_path) if memory_db_path else MEMORY_DB_PATH
        )
        self._learning_db = learning_db
        self._lock = threading.Lock()
        logger.info(
            "EngagementTracker initialized: memory_db=%s",
            self._memory_db_path,
        )

    # ------------------------------------------------------------------
    # LearningDB access (lazy)
    # ------------------------------------------------------------------

    def _get_learning_db(self):
        """
        Get or lazily create the LearningDB instance.

        Returns None if LearningDB cannot be imported or initialized.
        """
        if self._learning_db is not None:
            return self._learning_db

        try:
            from .learning_db import LearningDB
            self._learning_db = LearningDB()
            return self._learning_db
        except Exception as e:
            logger.warning("Failed to initialize LearningDB: %s", e)
            return None

    # ------------------------------------------------------------------
    # Memory.db read-only access
    # ------------------------------------------------------------------

    def _open_memory_db(self) -> sqlite3.Connection:
        """
        Open a read-only connection to memory.db.

        Uses URI mode=ro when supported; falls back to regular connection.
        """
        db_str = str(self._memory_db_path)
        try:
            uri = f"file:{db_str}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=5)
        except (sqlite3.OperationalError, sqlite3.NotSupportedError):
            conn = sqlite3.connect(db_str, timeout=5)
        conn.execute("PRAGMA busy_timeout=3000")
        return conn

    def _get_memory_db_columns(self) -> set:
        """Get available columns in the memories table."""
        if not self._memory_db_path.exists():
            return set()
        try:
            conn = self._open_memory_db()
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(memories)")
                return {row[1] for row in cursor.fetchall()}
            finally:
                conn.close()
        except sqlite3.Error:
            return set()

    # ------------------------------------------------------------------
    # Core stats
    # ------------------------------------------------------------------

    def get_engagement_stats(self) -> Dict[str, Any]:
        """
        Return a comprehensive engagement report.

        Returns:
            Dict with keys:
                days_active      — Days since first memory was created
                days_since_last  — Days since most recent activity
                staleness_ratio  — days_since_last / days_active (0=active, 1=abandoned)
                total_memories   — Total memory count
                memories_per_day — Average memories created per active day
                recalls_per_day  — Average recalls per active day (from feedback)
                patterns_learned — Transferable patterns with confidence > 0.6
                feedback_signals — Total feedback count
                health_status    — 'HEALTHY', 'DECLINING', 'AT_RISK', 'INACTIVE'
                active_sources   — List of tool sources used recently
        """
        # --- Memory.db stats ---
        mem_stats = self._get_memory_stats()

        # --- Learning.db stats ---
        learn_stats = self._get_learning_stats()

        # --- Derived metrics ---
        days_active = mem_stats['days_active']
        days_since_last = mem_stats['days_since_last']
        total_memories = mem_stats['total_memories']

        # Staleness: 0.0 = used today, 1.0 = abandoned
        if days_active > 0:
            staleness_ratio = round(days_since_last / days_active, 4)
        else:
            staleness_ratio = 0.0  # Brand-new user — not stale

        # Cap staleness at 1.0 (can exceed if days_since_last > days_active
        # due to timezone edge cases)
        staleness_ratio = min(staleness_ratio, 1.0)

        # Per-day rates
        if days_active > 0:
            memories_per_day = round(total_memories / days_active, 2)
            recalls_per_day = round(
                learn_stats['feedback_signals'] / days_active, 2
            )
        else:
            memories_per_day = float(total_memories)  # Day 0 — show raw count
            recalls_per_day = 0.0

        health_status = self._compute_health_status(
            staleness_ratio, recalls_per_day
        )

        return {
            'days_active': days_active,
            'days_since_last': days_since_last,
            'staleness_ratio': staleness_ratio,
            'total_memories': total_memories,
            'memories_per_day': memories_per_day,
            'recalls_per_day': recalls_per_day,
            'patterns_learned': learn_stats['patterns_learned'],
            'feedback_signals': learn_stats['feedback_signals'],
            'health_status': health_status,
            'active_sources': mem_stats['active_sources'],
        }

    def _get_memory_stats(self) -> Dict[str, Any]:
        """
        Gather stats from memory.db (read-only).

        Returns dict with: days_active, days_since_last, total_memories,
        active_sources.
        """
        default = {
            'days_active': 0,
            'days_since_last': 0,
            'total_memories': 0,
            'active_sources': [],
        }

        if not self._memory_db_path.exists():
            return default

        available = self._get_memory_db_columns()

        try:
            conn = self._open_memory_db()
            try:
                cursor = conn.cursor()

                # Total memories
                cursor.execute("SELECT COUNT(*) FROM memories")
                total = cursor.fetchone()[0]
                if total == 0:
                    return default

                # Date range
                if 'created_at' in available:
                    cursor.execute(
                        "SELECT MIN(created_at), MAX(created_at) "
                        "FROM memories"
                    )
                    row = cursor.fetchone()
                    first_ts, last_ts = row[0], row[1]

                    first_date = self._parse_date(first_ts)
                    last_date = self._parse_date(last_ts)
                    today = date.today()

                    if first_date and last_date:
                        days_active = max((today - first_date).days, 1)
                        days_since_last = max((today - last_date).days, 0)
                    else:
                        days_active = 1
                        days_since_last = 0
                else:
                    days_active = 1
                    days_since_last = 0

                # Active sources (created_by field, v2.5+)
                active_sources = []
                if 'created_by' in available:
                    try:
                        cursor.execute(
                            "SELECT DISTINCT created_by FROM memories "
                            "WHERE created_by IS NOT NULL "
                            "AND created_by != '' "
                            "ORDER BY created_by"
                        )
                        active_sources = [
                            row[0] for row in cursor.fetchall()
                        ]
                    except sqlite3.OperationalError:
                        pass  # Column might not be queryable

                return {
                    'days_active': days_active,
                    'days_since_last': days_since_last,
                    'total_memories': total,
                    'active_sources': active_sources,
                }
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.warning("Failed to read memory stats: %s", e)
            return default

    def _get_learning_stats(self) -> Dict[str, Any]:
        """
        Gather stats from learning.db via LearningDB.

        Returns dict with: patterns_learned, feedback_signals.
        """
        default = {
            'patterns_learned': 0,
            'feedback_signals': 0,
        }

        ldb = self._get_learning_db()
        if ldb is None:
            return default

        try:
            # Feedback signals
            feedback_count = ldb.get_feedback_count()

            # High-confidence patterns
            patterns = ldb.get_transferable_patterns(min_confidence=0.6)
            patterns_count = len(patterns)

            return {
                'patterns_learned': patterns_count,
                'feedback_signals': feedback_count,
            }
        except Exception as e:
            logger.warning("Failed to read learning stats: %s", e)
            return default

    # ------------------------------------------------------------------
    # Health classification
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_health_status(
        staleness_ratio: float,
        recalls_per_day: float,
    ) -> str:
        """
        Classify engagement health.

        Tiers:
            HEALTHY   — staleness < 0.1 AND recalls > 0.5/day
            DECLINING — staleness < 0.3 OR  recalls > 0.2/day
            AT_RISK   — staleness < 0.5
            INACTIVE  — staleness >= 0.5

        Args:
            staleness_ratio: 0.0 (active) to 1.0 (abandoned).
            recalls_per_day: Average recall operations per day.

        Returns:
            One of 'HEALTHY', 'DECLINING', 'AT_RISK', 'INACTIVE'.
        """
        if staleness_ratio < 0.1 and recalls_per_day > 0.5:
            return 'HEALTHY'
        if staleness_ratio < 0.3 or recalls_per_day > 0.2:
            return 'DECLINING'
        if staleness_ratio < 0.5:
            return 'AT_RISK'
        return 'INACTIVE'

    # ------------------------------------------------------------------
    # Activity recording
    # ------------------------------------------------------------------

    def record_activity(
        self,
        activity_type: str,
        source: Optional[str] = None,
    ):
        """
        Record an engagement activity event.

        Delegates to LearningDB.increment_engagement() which maintains
        daily engagement_metrics rows.

        Args:
            activity_type: One of 'memory_created', 'recall_performed',
                'feedback_given', 'pattern_updated'.
            source: Source tool identifier (e.g., "claude-desktop",
                "cursor", "cli").
        """
        # Map activity_type to LearningDB metric column names
        metric_map = {
            'memory_created': 'memories_created',
            'recall_performed': 'recalls_performed',
            'feedback_given': 'feedback_signals',
            'pattern_updated': 'patterns_updated',
        }

        metric_type = metric_map.get(activity_type)
        if metric_type is None:
            logger.warning(
                "Unknown activity type: %r (expected one of %s)",
                activity_type,
                list(metric_map.keys()),
            )
            return

        ldb = self._get_learning_db()
        if ldb is None:
            logger.debug(
                "LearningDB unavailable — cannot record activity '%s'",
                activity_type,
            )
            return

        try:
            ldb.increment_engagement(
                metric_type=metric_type,
                count=1,
                source=source,
            )
            logger.debug(
                "Recorded activity: type=%s, source=%s",
                activity_type, source,
            )
        except Exception as e:
            logger.warning("Failed to record activity: %s", e)

    # ------------------------------------------------------------------
    # Weekly summary
    # ------------------------------------------------------------------

    def get_weekly_summary(self) -> Dict[str, Any]:
        """
        Aggregate the last 7 days of engagement_metrics.

        Returns:
            Dict with:
                period_start     — ISO date string
                period_end       — ISO date string
                days_with_data   — Number of days that had engagement rows
                total_memories_created
                total_recalls
                total_feedback
                total_patterns_updated
                avg_memories_per_day
                avg_recalls_per_day
                all_sources      — Unique tools used across the week
        """
        ldb = self._get_learning_db()
        default = {
            'period_start': (date.today() - timedelta(days=6)).isoformat(),
            'period_end': date.today().isoformat(),
            'days_with_data': 0,
            'total_memories_created': 0,
            'total_recalls': 0,
            'total_feedback': 0,
            'total_patterns_updated': 0,
            'avg_memories_per_day': 0.0,
            'avg_recalls_per_day': 0.0,
            'all_sources': [],
        }

        if ldb is None:
            return default

        try:
            history = ldb.get_engagement_history(days=7)
        except Exception as e:
            logger.warning("Failed to get engagement history: %s", e)
            return default

        if not history:
            return default

        total_mem = 0
        total_rec = 0
        total_fb = 0
        total_pat = 0
        all_sources: set = set()

        for row in history:
            total_mem += row.get('memories_created', 0) or 0
            total_rec += row.get('recalls_performed', 0) or 0
            total_fb += row.get('feedback_signals', 0) or 0
            total_pat += row.get('patterns_updated', 0) or 0

            sources_raw = row.get('active_sources', '[]')
            if isinstance(sources_raw, str):
                try:
                    sources = json.loads(sources_raw)
                    all_sources.update(sources)
                except (json.JSONDecodeError, TypeError):
                    pass

        days_with_data = len(history)

        return {
            'period_start': (date.today() - timedelta(days=6)).isoformat(),
            'period_end': date.today().isoformat(),
            'days_with_data': days_with_data,
            'total_memories_created': total_mem,
            'total_recalls': total_rec,
            'total_feedback': total_fb,
            'total_patterns_updated': total_pat,
            'avg_memories_per_day': (
                round(total_mem / days_with_data, 1)
                if days_with_data > 0 else 0.0
            ),
            'avg_recalls_per_day': (
                round(total_rec / days_with_data, 1)
                if days_with_data > 0 else 0.0
            ),
            'all_sources': sorted(all_sources),
        }

    # ------------------------------------------------------------------
    # CLI formatting
    # ------------------------------------------------------------------

    def format_for_cli(self) -> str:
        """
        Format engagement stats as human-readable CLI output.

        Example:
            Active for: 94 days
            Last activity: 2 days ago
            Memories per day: 3.2
            Recalls per day: 1.8
            Patterns learned: 23
            Engagement: HEALTHY (staleness: 0.02)
        """
        try:
            stats = self.get_engagement_stats()
        except Exception as e:
            return f"Error computing engagement stats: {e}"

        # Format "last activity" human-friendly
        days_since = stats['days_since_last']
        if days_since == 0:
            last_activity = "today"
        elif days_since == 1:
            last_activity = "yesterday"
        else:
            last_activity = f"{days_since} days ago"

        # Health status with optional color hint for terminals
        health = stats['health_status']
        staleness = stats['staleness_ratio']

        lines = [
            f"Active for: {stats['days_active']} days",
            f"Last activity: {last_activity}",
            f"Total memories: {stats['total_memories']}",
            f"Memories per day: {stats['memories_per_day']}",
            f"Recalls per day: {stats['recalls_per_day']}",
            f"Patterns learned: {stats['patterns_learned']}",
            f"Feedback signals: {stats['feedback_signals']}",
            f"Engagement: {health} (staleness: {staleness:.2f})",
        ]

        if stats['active_sources']:
            lines.append(f"Active sources: {', '.join(stats['active_sources'])}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(timestamp: Any) -> Optional[date]:
        """
        Parse a timestamp string into a date object.

        Handles multiple formats from SQLite:
            - '2026-02-16 14:30:00'
            - '2026-02-16T14:30:00'
            - '2026-02-16'
        """
        if timestamp is None:
            return None

        ts = str(timestamp).strip()
        if not ts:
            return None

        # Try ISO formats
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(ts, fmt).date()
            except ValueError:
                continue

        # Last resort: try to parse just the date portion
        try:
            return datetime.strptime(ts[:10], "%Y-%m-%d").date()
        except (ValueError, IndexError):
            logger.debug("Unparseable timestamp: %r", timestamp)
            return None


# ======================================================================
# Standalone testing
# ======================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    tracker = EngagementTracker()

    print("=== Engagement Stats ===")
    stats = tracker.get_engagement_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n=== CLI Output ===")
    print(tracker.format_for_cli())

    print("\n=== Weekly Summary ===")
    weekly = tracker.get_weekly_summary()
    for k, v in weekly.items():
        print(f"  {k}: {v}")

    print("\n=== Health Classification Tests ===")
    test_cases = [
        (0.02, 1.5, "HEALTHY"),
        (0.05, 0.3, "DECLINING"),
        (0.25, 0.3, "DECLINING"),
        (0.35, 0.1, "AT_RISK"),
        (0.60, 0.0, "INACTIVE"),
        (0.0, 0.0, "DECLINING"),       # Active but no recalls
        (0.99, 5.0, "DECLINING"),       # High staleness but high recall
    ]
    for staleness, recalls, expected in test_cases:
        actual = EngagementTracker._compute_health_status(staleness, recalls)
        status = "PASS" if actual == expected else "FAIL"
        print(
            f"  [{status}] staleness={staleness:.2f}, recalls={recalls:.1f}"
            f" -> {actual} (expected {expected})"
        )
