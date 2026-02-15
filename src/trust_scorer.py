#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Trust Scorer
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Repository: https://github.com/varun369/SuperLocalMemoryV2
Author: Varun Pratap Bhardwaj (Solution Architect)

NOTICE: This software is protected by MIT License.
Attribution must be preserved in all copies or derivatives.
"""

"""
TrustScorer — Silent trust signal collection for AI agents.

v2.5 BEHAVIOR (this version):
    - All agents start at trust 1.0
    - Signals are collected silently (no enforcement, no ranking, no blocking)
    - Trust scores are updated in agent_registry.trust_score
    - Dashboard shows scores but they don't affect recall ordering yet

v2.6 BEHAVIOR (this version):
    - Trust scores visible in dashboard
    - Active enforcement: agents with trust < 0.3 blocked from write/delete operations
    - Quarantine and admin approval deferred to v3.0

v3.0 BEHAVIOR (future):
    - Quarantine low-trust memories for manual review
    - Admin approval workflow for untrusted agents

Trust Signals (all silently collected):
    POSITIVE (increase trust):
        - Memory recalled by other agents (cross-agent validation)
        - Memory updated (shows ongoing relevance)
        - High importance memories (agent writes valuable content)
        - Consistent write patterns (not spam-like)

    NEGATIVE (decrease trust):
        - Memory deleted shortly after creation (low quality)
        - Very high write volume in short time (potential spam/poisoning)
        - Content flagged or overwritten by user

    NEUTRAL:
        - Normal read/write patterns
        - Agent disconnects/reconnects

Scoring Algorithm:
    Bayesian-inspired moving average. Each signal adjusts the score
    by a small delta. Score is clamped to [0.0, 1.0].

    new_score = old_score + (delta * decay_factor)
    decay_factor = 1 / (1 + signal_count * 0.01)  # Stabilizes over time

    This means early signals have more impact, and the score converges
    as more data is collected. Similar to MACLA Beta-Binomial approach
    (arXiv:2512.18950) but simplified for local computation.

Security (OWASP for Agentic AI):
    - Memory poisoning (#1 threat): Trust scoring is the first defense layer
    - Over-permissioning: Trust scores inform future access control (v3.0)
    - Agent impersonation: Agent ID + protocol tracking detects anomalies
"""

import json
import logging
import math
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger("superlocalmemory.trust")

# Signal deltas (how much each signal moves the trust score)
SIGNAL_DELTAS = {
    # Positive signals
    "memory_recalled_by_others": +0.02,
    "memory_updated": +0.01,
    "high_importance_write": +0.015,   # importance >= 7
    "consistent_pattern": +0.01,

    # Negative signals
    "quick_delete": -0.03,             # deleted within 1 hour of creation
    "high_volume_burst": -0.02,        # >20 writes in 5 minutes
    "content_overwritten_by_user": -0.01,

    # Neutral (logged but no score change)
    "normal_write": 0.0,
    "normal_recall": 0.0,
}

# Thresholds
QUICK_DELETE_HOURS = 1       # Delete within 1 hour = negative signal
BURST_THRESHOLD = 20         # >20 writes in burst window = negative
BURST_WINDOW_MINUTES = 5     # Burst detection window


class TrustScorer:
    """
    Silent trust signal collector for AI agents.

    v2.5: Collection only, no enforcement. All agents start at 1.0.
    Thread-safe singleton per database path.
    """

    _instances: Dict[str, "TrustScorer"] = {}
    _instances_lock = threading.Lock()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> "TrustScorer":
        """Get or create the singleton TrustScorer."""
        if db_path is None:
            db_path = Path.home() / ".claude-memory" / "memory.db"
        key = str(db_path)
        with cls._instances_lock:
            if key not in cls._instances:
                cls._instances[key] = cls(db_path)
            return cls._instances[key]

    @classmethod
    def reset_instance(cls, db_path: Optional[Path] = None):
        """Remove singleton. Used for testing."""
        with cls._instances_lock:
            if db_path is None:
                cls._instances.clear()
            else:
                key = str(db_path)
                if key in cls._instances:
                    del cls._instances[key]

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

        # In-memory signal log for burst detection (agent_id -> list of timestamps)
        self._write_timestamps: Dict[str, list] = {}
        self._timestamps_lock = threading.Lock()

        # Signal count per agent (for decay factor calculation)
        self._signal_counts: Dict[str, int] = {}

        self._init_schema()
        logger.info("TrustScorer initialized (v2.5 — silent collection, no enforcement)")

    def _init_schema(self):
        """Create trust_signals table for audit trail."""
        try:
            from db_connection_manager import DbConnectionManager
            mgr = DbConnectionManager.get_instance(self.db_path)

            def _create(conn):
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS trust_signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent_id TEXT NOT NULL,
                        signal_type TEXT NOT NULL,
                        delta REAL NOT NULL,
                        old_score REAL,
                        new_score REAL,
                        context TEXT DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_trust_agent
                    ON trust_signals(agent_id)
                ''')
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_trust_created
                    ON trust_signals(created_at)
                ''')
                conn.commit()

            mgr.execute_write(_create)
        except ImportError:
            import sqlite3
            conn = sqlite3.connect(str(self.db_path))
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trust_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    delta REAL NOT NULL,
                    old_score REAL,
                    new_score REAL,
                    context TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_trust_agent ON trust_signals(agent_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_trust_created ON trust_signals(created_at)')
            conn.commit()
            conn.close()

    # =========================================================================
    # Signal Recording
    # =========================================================================

    def record_signal(
        self,
        agent_id: str,
        signal_type: str,
        context: Optional[dict] = None,
    ) -> bool:
        """
        Record a trust signal for an agent.

        Silently adjusts the agent's trust score based on the signal type.
        The signal and score change are logged to trust_signals table.

        Args:
            agent_id: Agent that generated the signal
            signal_type: One of SIGNAL_DELTAS keys
            context: Additional context (memory_id, etc.)
        """
        if signal_type not in SIGNAL_DELTAS:
            logger.warning("Unknown trust signal: %s", signal_type)
            return

        delta = SIGNAL_DELTAS[signal_type]

        # Get current trust score from agent registry
        old_score = self._get_agent_trust(agent_id)
        if old_score is None:
            old_score = 1.0  # Default for unknown agents

        # Apply decay factor (score stabilizes over time)
        count = self._signal_counts.get(agent_id, 0)
        decay = 1.0 / (1.0 + count * 0.01)
        adjusted_delta = delta * decay

        # Calculate new score (clamped to [0.0, 1.0])
        new_score = max(0.0, min(1.0, old_score + adjusted_delta))

        # Update signal count
        self._signal_counts[agent_id] = count + 1

        # Persist signal to audit trail
        self._persist_signal(agent_id, signal_type, adjusted_delta, old_score, new_score, context)

        # Update agent trust score (if score actually changed)
        if abs(new_score - old_score) > 0.0001:
            self._update_agent_trust(agent_id, new_score)

        logger.debug(
            "Trust signal: agent=%s, type=%s, delta=%.4f, score=%.4f→%.4f",
            agent_id, signal_type, adjusted_delta, old_score, new_score
        )

    def _persist_signal(self, agent_id, signal_type, delta, old_score, new_score, context):
        """Save signal to trust_signals table."""
        try:
            from db_connection_manager import DbConnectionManager
            mgr = DbConnectionManager.get_instance(self.db_path)

            def _insert(conn):
                conn.execute('''
                    INSERT INTO trust_signals (agent_id, signal_type, delta, old_score, new_score, context)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (agent_id, signal_type, delta, old_score, new_score, json.dumps(context or {})))
                conn.commit()

            mgr.execute_write(_insert)
        except Exception as e:
            logger.error("Failed to persist trust signal: %s", e)

    def _get_agent_trust(self, agent_id: str) -> Optional[float]:
        """Get current trust score from agent_registry."""
        try:
            from db_connection_manager import DbConnectionManager
            mgr = DbConnectionManager.get_instance(self.db_path)

            with mgr.read_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT trust_score FROM agent_registry WHERE agent_id = ?",
                    (agent_id,)
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def _update_agent_trust(self, agent_id: str, new_score: float):
        """Update trust score in agent_registry."""
        try:
            from db_connection_manager import DbConnectionManager
            mgr = DbConnectionManager.get_instance(self.db_path)

            def _update(conn):
                conn.execute(
                    "UPDATE agent_registry SET trust_score = ? WHERE agent_id = ?",
                    (round(new_score, 4), agent_id)
                )
                conn.commit()

            mgr.execute_write(_update)
        except Exception as e:
            logger.error("Failed to update agent trust: %s", e)

    # =========================================================================
    # High-Level Signal Helpers (called from memory_store_v2 / mcp_server)
    # =========================================================================

    def on_memory_created(self, agent_id: str, memory_id: int, importance: int = 5):
        """Record signals when a memory is created."""
        # Track write timestamp for burst detection
        self._track_write(agent_id)

        if importance >= 7:
            self.record_signal(agent_id, "high_importance_write",
                             context={"memory_id": memory_id, "importance": importance})
        else:
            self.record_signal(agent_id, "normal_write",
                             context={"memory_id": memory_id})

        # Check for burst pattern
        if self._is_burst(agent_id):
            self.record_signal(agent_id, "high_volume_burst",
                             context={"memory_id": memory_id})

    def on_memory_deleted(self, agent_id: str, memory_id: int, created_at: Optional[str] = None):
        """Record signals when a memory is deleted."""
        if created_at:
            try:
                created = datetime.fromisoformat(created_at)
                age_hours = (datetime.now() - created).total_seconds() / 3600
                if age_hours < QUICK_DELETE_HOURS:
                    self.record_signal(agent_id, "quick_delete",
                                     context={"memory_id": memory_id, "age_hours": round(age_hours, 2)})
                    return
            except (ValueError, TypeError):
                pass

        # Normal delete (no negative signal)
        self.record_signal(agent_id, "normal_write",
                         context={"memory_id": memory_id, "action": "delete"})

    def on_memory_recalled(self, agent_id: str, memory_id: int, created_by: Optional[str] = None):
        """Record signals when a memory is recalled."""
        if created_by and created_by != agent_id:
            # Cross-agent validation: another agent found this memory useful
            self.record_signal(created_by, "memory_recalled_by_others",
                             context={"memory_id": memory_id, "recalled_by": agent_id})

        self.record_signal(agent_id, "normal_recall",
                         context={"memory_id": memory_id})

    # =========================================================================
    # Burst Detection
    # =========================================================================

    def _track_write(self, agent_id: str):
        """Track a write timestamp for burst detection."""
        now = datetime.now()
        with self._timestamps_lock:
            if agent_id not in self._write_timestamps:
                self._write_timestamps[agent_id] = []
            timestamps = self._write_timestamps[agent_id]
            timestamps.append(now)
            # Keep only recent timestamps (within burst window)
            cutoff = now - timedelta(minutes=BURST_WINDOW_MINUTES)
            self._write_timestamps[agent_id] = [t for t in timestamps if t > cutoff]

    def _is_burst(self, agent_id: str) -> bool:
        """Check if agent is in a burst write pattern."""
        with self._timestamps_lock:
            timestamps = self._write_timestamps.get(agent_id, [])
            return len(timestamps) > BURST_THRESHOLD

    # =========================================================================
    # Query Trust Data
    # =========================================================================

    def get_trust_score(self, agent_id: str) -> float:
        """Get current trust score for an agent. Returns 1.0 if unknown."""
        score = self._get_agent_trust(agent_id)
        return score if score is not None else 1.0

    def check_trust(self, agent_id: str, operation: str = "write") -> bool:
        """
        Check if agent is trusted enough for the given operation.

        v2.6 enforcement: blocks write/delete for agents with trust < 0.3.
        New agents start at 1.0 — only repeated bad behavior triggers blocking.

        Args:
            agent_id: The agent identifier
            operation: One of "read", "write", "delete"

        Returns:
            True if operation is allowed, False if blocked
        """
        if operation == "read":
            return True  # Reads are always allowed

        score = self._get_agent_trust(agent_id)
        if score is None:
            return True  # Unknown agent = first-time = allowed (starts at 1.0)

        threshold = 0.3  # Block write/delete below this
        if score < threshold:
            logger.warning(
                "Trust enforcement: agent '%s' blocked from '%s' (trust=%.2f < %.2f)",
                agent_id, operation, score, threshold
            )
            return False

        return True

    def get_signals(self, agent_id: str, limit: int = 50) -> List[dict]:
        """Get recent trust signals for an agent."""
        try:
            from db_connection_manager import DbConnectionManager
            mgr = DbConnectionManager.get_instance(self.db_path)

            with mgr.read_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT signal_type, delta, old_score, new_score, context, created_at
                    FROM trust_signals
                    WHERE agent_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (agent_id, limit))

                signals = []
                for row in cursor.fetchall():
                    ctx = {}
                    try:
                        ctx = json.loads(row[4]) if row[4] else {}
                    except (json.JSONDecodeError, TypeError):
                        pass
                    signals.append({
                        "signal_type": row[0],
                        "delta": row[1],
                        "old_score": row[2],
                        "new_score": row[3],
                        "context": ctx,
                        "created_at": row[5],
                    })
                return signals

        except Exception as e:
            logger.error("Failed to get trust signals: %s", e)
            return []

    def get_trust_stats(self) -> dict:
        """Get trust system statistics."""
        try:
            from db_connection_manager import DbConnectionManager
            mgr = DbConnectionManager.get_instance(self.db_path)

            with mgr.read_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM trust_signals")
                total_signals = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT signal_type, COUNT(*) FROM trust_signals
                    GROUP BY signal_type ORDER BY COUNT(*) DESC
                """)
                by_type = dict(cursor.fetchall())

                cursor.execute("""
                    SELECT agent_id, COUNT(*) FROM trust_signals
                    GROUP BY agent_id ORDER BY COUNT(*) DESC LIMIT 10
                """)
                by_agent = dict(cursor.fetchall())

                cursor.execute("""
                    SELECT AVG(trust_score) FROM agent_registry
                    WHERE trust_score IS NOT NULL
                """)
                avg = cursor.fetchone()[0]

            return {
                "total_signals": total_signals,
                "by_signal_type": by_type,
                "by_agent": by_agent,
                "avg_trust_score": round(avg, 4) if avg else 1.0,
                "enforcement": "enabled (v2.6 — write/delete blocked below 0.3 trust)",
            }

        except Exception as e:
            logger.error("Failed to get trust stats: %s", e)
            return {"total_signals": 0, "error": str(e)}
