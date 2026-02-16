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
TrustScorer — Bayesian Beta-Binomial trust scoring for AI agents.

Scoring Model:
    Each agent's trust is modeled as a Beta(alpha, beta) distribution.
    - alpha accumulates evidence of trustworthy behavior
    - beta accumulates evidence of untrustworthy behavior
    - Trust score = alpha / (alpha + beta)  (posterior mean)

    Prior: Beta(2.0, 1.0) → initial trust = 0.667
    This gives new agents a positive-but-not-maximal starting trust,
    well above the 0.3 enforcement threshold but with room to grow.

    This follows the MACLA Beta-Binomial approach (arXiv:2512.18950)
    already used in pattern_learner.py for confidence scoring.

v2.5 BEHAVIOR (this version):
    - All agents start at Beta(2.0, 1.0) → trust 0.667
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
    POSITIVE (increase alpha — build trust):
        - Memory recalled by other agents (cross-agent validation)
        - Memory updated (shows ongoing relevance)
        - High importance memories (agent writes valuable content)
        - Consistent write patterns (not spam-like)

    NEGATIVE (increase beta — erode trust):
        - Memory deleted shortly after creation (low quality)
        - Very high write volume in short time (potential spam/poisoning)
        - Content flagged or overwritten by user

    NEUTRAL:
        - Normal read/write patterns (tiny alpha nudge to reward activity)
        - Agent disconnects/reconnects

Decay:
    Every DECAY_INTERVAL signals per agent, both alpha and beta are
    multiplied by DECAY_FACTOR (0.995). This slowly forgets very old
    signals so recent behavior matters more. Floors prevent total
    information loss: alpha >= 1.0, beta >= 0.5.

Security (OWASP for Agentic AI):
    - Memory poisoning (#1 threat): Trust scoring is the first defense layer
    - Over-permissioning: Trust scores inform future access control (v3.0)
    - Agent impersonation: Agent ID + protocol tracking detects anomalies
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger("superlocalmemory.trust")

# ---------------------------------------------------------------------------
# Beta-Binomial signal weights
# ---------------------------------------------------------------------------
# Positive signals increment alpha (building trust).
# Negative signals increment beta (eroding trust).
# Neutral signals give a tiny alpha nudge to reward normal activity.
#
# Asymmetry: negative weights are larger than positive weights.
# This means it's harder to build trust than to lose it — the system
# is intentionally skeptical. One poisoning event takes many good
# actions to recover from.
# ---------------------------------------------------------------------------

SIGNAL_WEIGHTS = {
    # Positive signals → alpha += weight
    "memory_recalled_by_others": ("positive", 0.30),   # cross-agent validation
    "memory_updated":            ("positive", 0.15),   # ongoing relevance
    "high_importance_write":     ("positive", 0.20),   # valuable content (importance >= 7)
    "consistent_pattern":        ("positive", 0.15),   # stable write behavior

    # Negative signals → beta += weight
    "quick_delete":              ("negative", 0.50),   # deleted within 1 hour
    "high_volume_burst":         ("negative", 0.40),   # >20 writes in 5 minutes
    "content_overwritten_by_user": ("negative", 0.25), # user had to fix output

    # Neutral signals → tiny alpha nudge
    "normal_write":              ("neutral", 0.01),
    "normal_recall":             ("neutral", 0.01),
}

# Backward-compatible: expose SIGNAL_DELTAS as a derived dict so that
# bm6_trust.py (which imports SIGNAL_DELTAS) and any other consumer
# continues to work. The values represent the *direction* and *magnitude*
# of each signal: positive for alpha, negative for beta, zero for neutral.
SIGNAL_DELTAS = {}
for _sig, (_direction, _weight) in SIGNAL_WEIGHTS.items():
    if _direction == "positive":
        SIGNAL_DELTAS[_sig] = +_weight
    elif _direction == "negative":
        SIGNAL_DELTAS[_sig] = -_weight
    else:
        SIGNAL_DELTAS[_sig] = 0.0

# ---------------------------------------------------------------------------
# Beta prior and decay parameters
# ---------------------------------------------------------------------------
INITIAL_ALPHA = 2.0        # Slight positive prior
INITIAL_BETA = 1.0         # → initial trust = 2/(2+1) = 0.667
DECAY_FACTOR = 0.995       # Multiply alpha & beta every DECAY_INTERVAL signals
DECAY_INTERVAL = 50        # Apply decay every N signals per agent
ALPHA_FLOOR = 1.0          # Never decay alpha below this
BETA_FLOOR = 0.5           # Never decay beta below this

# Thresholds
QUICK_DELETE_HOURS = 1       # Delete within 1 hour = negative signal
BURST_THRESHOLD = 20         # >20 writes in burst window = negative
BURST_WINDOW_MINUTES = 5     # Burst detection window


class TrustScorer:
    """
    Bayesian Beta-Binomial trust scorer for AI agents.

    Each agent is modeled as Beta(alpha, beta). Positive signals
    increment alpha, negative signals increment beta. The trust
    score is the posterior mean: alpha / (alpha + beta).

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

        # Signal count per agent (for decay interval tracking)
        self._signal_counts: Dict[str, int] = {}

        # In-memory cache of Beta parameters per agent
        # Key: agent_id, Value: (alpha, beta)
        self._beta_params: Dict[str, tuple] = {}
        self._beta_lock = threading.Lock()

        self._init_schema()
        logger.info("TrustScorer initialized (Beta-Binomial — alpha=%.1f, beta=%.1f prior)",
                     INITIAL_ALPHA, INITIAL_BETA)

    def _init_schema(self):
        """Create trust_signals table and add alpha/beta columns to agent_registry."""
        try:
            from db_connection_manager import DbConnectionManager
            mgr = DbConnectionManager.get_instance(self.db_path)

            def _create(conn):
                # Trust signals audit trail
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

                # Add trust_alpha and trust_beta columns to agent_registry
                # (backward compatible — old databases get these columns added)
                for col_name, col_default in [("trust_alpha", INITIAL_ALPHA),
                                               ("trust_beta", INITIAL_BETA)]:
                    try:
                        conn.execute(
                            f'ALTER TABLE agent_registry ADD COLUMN {col_name} REAL DEFAULT {col_default}'
                        )
                    except Exception:
                        pass  # Column already exists

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

            # Add trust_alpha and trust_beta columns (backward compatible)
            for col_name, col_default in [("trust_alpha", INITIAL_ALPHA),
                                           ("trust_beta", INITIAL_BETA)]:
                try:
                    conn.execute(
                        f'ALTER TABLE agent_registry ADD COLUMN {col_name} REAL DEFAULT {col_default}'
                    )
                except sqlite3.OperationalError:
                    pass  # Column already exists

            conn.commit()
            conn.close()

    # =========================================================================
    # Beta Parameter Management
    # =========================================================================

    def _get_beta_params(self, agent_id: str) -> tuple:
        """
        Get (alpha, beta) for an agent. Checks in-memory cache first,
        then database, then falls back to prior defaults.

        Returns:
            (alpha, beta) tuple
        """
        with self._beta_lock:
            if agent_id in self._beta_params:
                return self._beta_params[agent_id]

        # Not in cache — read from database
        alpha, beta = None, None
        try:
            from db_connection_manager import DbConnectionManager
            mgr = DbConnectionManager.get_instance(self.db_path)

            with mgr.read_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT trust_alpha, trust_beta FROM agent_registry WHERE agent_id = ?",
                    (agent_id,)
                )
                row = cursor.fetchone()
                if row:
                    alpha = row[0]
                    beta = row[1]
        except Exception:
            pass

        # Fall back to defaults if NULL or missing
        if alpha is None or beta is None:
            alpha = INITIAL_ALPHA
            beta = INITIAL_BETA

        with self._beta_lock:
            self._beta_params[agent_id] = (alpha, beta)

        return (alpha, beta)

    def _set_beta_params(self, agent_id: str, alpha: float, beta: float):
        """
        Update (alpha, beta) in cache and persist to agent_registry.
        Also computes and stores the derived trust_score = alpha/(alpha+beta).
        """
        trust_score = alpha / (alpha + beta) if (alpha + beta) > 0 else 0.0

        with self._beta_lock:
            self._beta_params[agent_id] = (alpha, beta)

        try:
            from db_connection_manager import DbConnectionManager
            mgr = DbConnectionManager.get_instance(self.db_path)

            def _update(conn):
                conn.execute(
                    """UPDATE agent_registry
                       SET trust_score = ?, trust_alpha = ?, trust_beta = ?
                       WHERE agent_id = ?""",
                    (round(trust_score, 4), round(alpha, 4), round(beta, 4), agent_id)
                )
                conn.commit()

            mgr.execute_write(_update)
        except Exception as e:
            logger.error("Failed to persist Beta params for %s: %s", agent_id, e)

    def _apply_decay(self, agent_id: str, alpha: float, beta: float) -> tuple:
        """
        Apply periodic decay to alpha and beta to forget very old signals.

        Called every DECAY_INTERVAL signals per agent.
        Multiplies both by DECAY_FACTOR with floor constraints.

        Returns:
            (decayed_alpha, decayed_beta)
        """
        new_alpha = max(ALPHA_FLOOR, alpha * DECAY_FACTOR)
        new_beta = max(BETA_FLOOR, beta * DECAY_FACTOR)
        return (new_alpha, new_beta)

    # =========================================================================
    # Signal Recording (Beta-Binomial Update)
    # =========================================================================

    def record_signal(
        self,
        agent_id: str,
        signal_type: str,
        context: Optional[dict] = None,
    ) -> bool:
        """
        Record a trust signal for an agent using Beta-Binomial update.

        Positive signals increment alpha (trust evidence).
        Negative signals increment beta (distrust evidence).
        Neutral signals give a tiny alpha nudge.

        Trust score = alpha / (alpha + beta) — the posterior mean.

        Args:
            agent_id: Agent that generated the signal
            signal_type: One of SIGNAL_WEIGHTS keys
            context: Additional context (memory_id, etc.)

        Returns:
            True if signal was recorded successfully
        """
        if signal_type not in SIGNAL_WEIGHTS:
            logger.warning("Unknown trust signal: %s", signal_type)
            return False

        direction, weight = SIGNAL_WEIGHTS[signal_type]

        # Get current Beta parameters
        alpha, beta = self._get_beta_params(agent_id)
        old_score = alpha / (alpha + beta) if (alpha + beta) > 0 else 0.0

        # Apply Beta-Binomial update
        if direction == "positive":
            alpha += weight
        elif direction == "negative":
            beta += weight
        else:  # neutral — tiny alpha nudge
            alpha += weight

        # Apply periodic decay
        count = self._signal_counts.get(agent_id, 0) + 1
        self._signal_counts[agent_id] = count

        if count % DECAY_INTERVAL == 0:
            alpha, beta = self._apply_decay(agent_id, alpha, beta)

        # Compute new trust score (posterior mean)
        new_score = alpha / (alpha + beta) if (alpha + beta) > 0 else 0.0

        # Compute delta for audit trail (backward compatible with trust_signals table)
        delta = new_score - old_score

        # Persist signal to audit trail
        self._persist_signal(agent_id, signal_type, delta, old_score, new_score, context)

        # Persist updated Beta parameters and derived trust_score
        self._set_beta_params(agent_id, alpha, beta)

        logger.debug(
            "Trust signal: agent=%s, type=%s (%s, w=%.2f), "
            "alpha=%.2f, beta=%.2f, score=%.4f->%.4f",
            agent_id, signal_type, direction, weight,
            alpha, beta, old_score, new_score
        )

        return True

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
        """
        Get current trust score from agent_registry.

        This reads the derived trust_score column (which is always kept
        in sync with alpha/(alpha+beta) by _set_beta_params).
        """
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
        """
        Update trust score in agent_registry (legacy compatibility method).

        In Beta-Binomial mode, this is a no-op because _set_beta_params
        already updates trust_score alongside alpha and beta. Kept for
        backward compatibility if any external code calls it directly.
        """
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
        """
        Get current trust score for an agent.

        Computes alpha/(alpha+beta) from cached or stored Beta params.
        Returns INITIAL_ALPHA/(INITIAL_ALPHA+INITIAL_BETA) = 0.667 for
        unknown agents.
        """
        alpha, beta = self._get_beta_params(agent_id)
        if (alpha + beta) > 0:
            return alpha / (alpha + beta)
        return INITIAL_ALPHA / (INITIAL_ALPHA + INITIAL_BETA)

    def get_beta_params(self, agent_id: str) -> Dict[str, float]:
        """
        Get the Beta distribution parameters for an agent.

        Returns:
            {"alpha": float, "beta": float, "trust_score": float}
        """
        alpha, beta = self._get_beta_params(agent_id)
        score = alpha / (alpha + beta) if (alpha + beta) > 0 else 0.0
        return {
            "alpha": round(alpha, 4),
            "beta": round(beta, 4),
            "trust_score": round(score, 4),
        }

    def check_trust(self, agent_id: str, operation: str = "write") -> bool:
        """
        Check if agent is trusted enough for the given operation.

        v2.6 enforcement: blocks write/delete for agents with trust < 0.3.
        New agents start at Beta(2,1) → trust 0.667 — only repeated bad
        behavior triggers blocking.

        Args:
            agent_id: The agent identifier
            operation: One of "read", "write", "delete"

        Returns:
            True if operation is allowed, False if blocked
        """
        if operation == "read":
            return True  # Reads are always allowed

        score = self.get_trust_score(agent_id)

        threshold = 0.3  # Block write/delete below this
        if score < threshold:
            logger.warning(
                "Trust enforcement: agent '%s' blocked from '%s' (trust=%.4f < %.2f)",
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
                "avg_trust_score": round(avg, 4) if avg else INITIAL_ALPHA / (INITIAL_ALPHA + INITIAL_BETA),
                "scoring_model": "Beta-Binomial",
                "prior": f"Beta({INITIAL_ALPHA}, {INITIAL_BETA})",
                "enforcement": "enabled (v2.6 — write/delete blocked below 0.3 trust)",
            }

        except Exception as e:
            logger.error("Failed to get trust stats: %s", e)
            return {"total_signals": 0, "error": str(e)}
