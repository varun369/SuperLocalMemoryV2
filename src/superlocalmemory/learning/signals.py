# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Zero-Cost Learning Signals — mathematical learning without LLM tokens.

Four signal types that improve retrieval quality over time:

1. Entropy Gap     — Surprising content gets deeper indexing.
2. Co-Retrieval    — Memories retrieved together strengthen graph edges.
3. Channel Credit  — Track which retrieval channel works for which query type.
4. Confidence Lifecycle — Boost on access, decay over time.

All signals are computed locally with zero LLM cost.
Inspired by: Nemori (entropy), A-Mem (link evolution), RMM (citation feedback).

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
import math
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class LearningSignals:
    """Compute and apply zero-cost learning signals.

    Uses the main memory.db via direct sqlite3 (no engine dependency).
    Thread-safe via lock.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        self._ensure_tables()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _ensure_tables(self) -> None:
        """Create learning signal tables if they don't exist."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS channel_credits ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "profile_id TEXT NOT NULL, "
                    "query_type TEXT NOT NULL, "
                    "channel TEXT NOT NULL, "
                    "hits INTEGER DEFAULT 0, "
                    "total INTEGER DEFAULT 0, "
                    "updated_at TEXT NOT NULL)"
                )
                conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_channel_credit_unique "
                    "ON channel_credits(profile_id, query_type, channel)"
                )
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS co_retrieval_edges ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "profile_id TEXT NOT NULL, "
                    "fact_id_a TEXT NOT NULL, "
                    "fact_id_b TEXT NOT NULL, "
                    "co_count INTEGER DEFAULT 1, "
                    "updated_at TEXT NOT NULL)"
                )
                conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_co_retrieval_unique "
                    "ON co_retrieval_edges(profile_id, fact_id_a, fact_id_b)"
                )
                conn.commit()
            finally:
                conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Signal 1: Entropy Gap (store-time)
    # ------------------------------------------------------------------

    @staticmethod
    def compute_entropy_gap(
        new_embedding: list[float],
        cluster_embeddings: list[list[float]],
    ) -> float:
        """Compute how surprising new content is relative to existing cluster.

        High gap = surprising content = should get deeper indexing.
        Low gap = redundant content = standard indexing.

        Returns a value in [0.0, 1.0]. >0.7 is 'surprising'.
        """
        if not cluster_embeddings or not new_embedding:
            return 0.5  # neutral when no comparison available

        similarities = []
        for existing in cluster_embeddings:
            sim = _cosine_sim(new_embedding, existing)
            similarities.append(sim)

        avg_sim = sum(similarities) / len(similarities)
        gap = max(0.0, min(1.0, 1.0 - avg_sim))
        return gap

    # ------------------------------------------------------------------
    # Signal 2: Co-Retrieval (recall-time)
    # ------------------------------------------------------------------

    def record_co_retrieval(
        self, profile_id: str, fact_ids: list[str],
    ) -> int:
        """Record that these facts were co-retrieved.

        All pairs of facts in the result set get their co-retrieval
        count incremented. This strengthens implicit graph edges.
        """
        if len(fact_ids) < 2:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        pairs = []
        for i in range(len(fact_ids)):
            for j in range(i + 1, min(len(fact_ids), i + 5)):
                a, b = sorted([fact_ids[i], fact_ids[j]])
                pairs.append((profile_id, a, b, now))

        if not pairs:
            return 0

        with self._lock:
            conn = self._connect()
            try:
                for pid, a, b, ts in pairs:
                    conn.execute(
                        "INSERT INTO co_retrieval_edges "
                        "(profile_id, fact_id_a, fact_id_b, co_count, updated_at) "
                        "VALUES (?, ?, ?, 1, ?) "
                        "ON CONFLICT(profile_id, fact_id_a, fact_id_b) "
                        "DO UPDATE SET co_count = co_count + 1, updated_at = ?",
                        (pid, a, b, ts, ts),
                    )
                conn.commit()
                return len(pairs)
            finally:
                conn.close()

    def get_co_retrieval_boost(
        self, profile_id: str, fact_id: str, top_k: int = 5,
    ) -> list[dict]:
        """Get top co-retrieved facts for boosting."""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT fact_id_a, fact_id_b, co_count FROM co_retrieval_edges "
                    "WHERE profile_id = ? AND (fact_id_a = ? OR fact_id_b = ?) "
                    "ORDER BY co_count DESC LIMIT ?",
                    (profile_id, fact_id, fact_id, top_k),
                ).fetchall()
                results = []
                for r in rows:
                    d = dict(r)
                    other = d["fact_id_b"] if d["fact_id_a"] == fact_id else d["fact_id_a"]
                    results.append({"fact_id": other, "co_count": d["co_count"]})
                return results
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Signal 3: Channel Credit (recall-time)
    # ------------------------------------------------------------------

    def credit_channel(
        self, profile_id: str, query_type: str, channel: str, hit: bool,
    ) -> None:
        """Credit a retrieval channel for a hit or miss."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                hit_val = 1 if hit else 0
                conn.execute(
                    "INSERT INTO channel_credits "
                    "(profile_id, query_type, channel, hits, total, updated_at) "
                    "VALUES (?, ?, ?, ?, 1, ?) "
                    "ON CONFLICT(profile_id, query_type, channel) "
                    "DO UPDATE SET hits = hits + ?, total = total + 1, updated_at = ?",
                    (profile_id, query_type, channel, hit_val, now, hit_val, now),
                )
                conn.commit()
            finally:
                conn.close()

    def get_channel_weights(
        self, profile_id: str, query_type: str,
    ) -> dict[str, float]:
        """Get learned channel weights for a query type.

        Returns weight multipliers based on historical hit rates.
        """
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT channel, hits, total FROM channel_credits "
                    "WHERE profile_id = ? AND query_type = ? AND total >= 5",
                    (profile_id, query_type),
                ).fetchall()
                if not rows:
                    return {}
                weights = {}
                for r in rows:
                    d = dict(r)
                    rate = d["hits"] / max(d["total"], 1)
                    weights[d["channel"]] = 0.7 + (rate * 0.8)
                return weights
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Signal 4: Confidence Lifecycle (store + recall time)
    # ------------------------------------------------------------------

    @staticmethod
    def boost_confidence(db_path: str, fact_id: str, amount: float = 0.02) -> None:
        """Boost a fact's confidence on access. Capped at 1.0."""
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute(
                "UPDATE atomic_facts SET confidence = MIN(1.0, confidence + ?) "
                "WHERE fact_id = ?",
                (amount, fact_id),
            )
            conn.execute(
                "UPDATE atomic_facts SET access_count = access_count + 1 "
                "WHERE fact_id = ?",
                (fact_id,),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    @staticmethod
    def decay_confidence(db_path: str, profile_id: str, rate: float = 0.001) -> int:
        """Decay confidence on unused facts. Floor: 0.1."""
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("PRAGMA busy_timeout=5000")
            cursor = conn.execute(
                "UPDATE atomic_facts SET confidence = MAX(0.1, confidence - ?) "
                "WHERE profile_id = ? AND access_count = 0 "
                "AND created_at < datetime('now', '-7 days')",
                (rate, profile_id),
            )
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_signal_stats(self, profile_id: str) -> dict:
        """Get learning signal statistics for dashboard."""
        with self._lock:
            conn = self._connect()
            try:
                co_rows = conn.execute(
                    "SELECT COUNT(*) AS c, COALESCE(SUM(co_count), 0) AS total "
                    "FROM co_retrieval_edges WHERE profile_id = ?",
                    (profile_id,),
                ).fetchone()
                co = dict(co_rows) if co_rows else {"c": 0, "total": 0}

                ch_rows = conn.execute(
                    "SELECT channel, hits, total FROM channel_credits "
                    "WHERE profile_id = ? ORDER BY total DESC",
                    (profile_id,),
                ).fetchall()
                channels = {
                    dict(r)["channel"]: {
                        "hits": dict(r)["hits"],
                        "total": dict(r)["total"],
                        "rate": round(dict(r)["hits"] / max(dict(r)["total"], 1), 3),
                    }
                    for r in ch_rows
                }

                return {
                    "co_retrieval_edges": co["c"],
                    "co_retrieval_events": co["total"],
                    "channel_performance": channels,
                }
            finally:
                conn.close()


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return dot / (norm_a * norm_b)
