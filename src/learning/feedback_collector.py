#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Feedback Collector (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Repository: https://github.com/varun369/SuperLocalMemoryV2
Author: Varun Pratap Bhardwaj (Solution Architect)

NOTICE: This software is protected by MIT License.
Attribution must be preserved in all copies or derivatives.
"""

"""
FeedbackCollector -- Multi-channel feedback collection for the LightGBM re-ranker.

Collects implicit and explicit relevance signals from three channels:

    1. MCP  -- ``memory_used`` tool with usefulness level (high/medium/low).
    2. CLI  -- ``slm useful <id> [<id>...]`` marks memories as helpful.
    3. Dashboard -- click events with optional dwell-time tracking.

Additionally tracks *passive decay*: memories that are repeatedly returned
by recall but never receive a positive signal are assigned a 0.0 (negative)
feedback entry, teaching the re-ranker to demote them.

Privacy:
    - Full query text is NEVER stored.
    - Queries are hashed to SHA-256[:16] for grouping.
    - Top 3 keywords are extracted for loose thematic grouping only.

All data is written to the ``ranking_feedback`` table in learning.db via
the shared LearningDB instance.

Research backing:
    - ADPMF (IPM 2024): privacy-preserving feedback for recommendation.
    - FCS LREC 2024: cold-start feedback bootstrapping.
"""

import hashlib
import logging
import re
import threading
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger("superlocalmemory.learning.feedback")

# ---------------------------------------------------------------------------
# Stopwords for keyword extraction (small, curated list -- no NLTK needed)
# ---------------------------------------------------------------------------
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "their", "its", "this", "that", "these", "those",
    "what", "which", "who", "whom", "how", "when", "where", "why",
    "not", "no", "nor", "but", "or", "and", "if", "then", "so",
    "of", "in", "on", "at", "to", "for", "with", "from", "by",
    "about", "into", "through", "during", "before", "after",
    "above", "below", "between", "out", "off", "up", "down",
    "all", "each", "every", "both", "few", "more", "most", "some", "any",
    "such", "only", "same", "than", "too", "very",
    "just", "also", "now", "here", "there",
})

# Regex to split on non-alphanumeric (keeps words and numbers)
_WORD_SPLIT = re.compile(r"[^a-zA-Z0-9]+")


class FeedbackCollector:
    """
    Collects multi-channel relevance feedback for the adaptive re-ranker.

    Each signal maps to a numeric value used as a training label:

        mcp_used_high   = 1.0  (strong positive)
        mcp_used_medium = 0.7
        mcp_used_low    = 0.4
        cli_useful      = 0.9
        dashboard_click = 0.8
        passive_decay   = 0.0  (negative signal)

    Usage:
        from learning.learning_db import LearningDB
        collector = FeedbackCollector(learning_db=LearningDB())

        # MCP channel
        collector.record_memory_used(42, "how to deploy FastAPI", usefulness="high")

        # CLI channel
        collector.record_cli_useful([42, 87], "deploy fastapi")

        # Dashboard channel
        collector.record_dashboard_click(42, "deploy fastapi", dwell_time=12.5)

        # Passive decay (call periodically)
        collector.record_recall_results("deploy fastapi", [42, 87, 91])
        collector.compute_passive_decay()
    """

    # Signal type -> numeric label for re-ranker training
    SIGNAL_VALUES: Dict[str, float] = {
        "mcp_used_high": 1.0,
        "mcp_used_medium": 0.7,
        "mcp_used_low": 0.4,
        "cli_useful": 0.9,
        "dashboard_click": 0.8,
        "dashboard_thumbs_up": 1.0,
        "dashboard_thumbs_down": 0.0,
        "dashboard_pin": 1.0,
        "dashboard_dwell_positive": 0.7,
        "dashboard_dwell_negative": 0.1,
        "implicit_positive_timegap": 0.6,
        "implicit_negative_requick": 0.1,
        "implicit_positive_reaccess": 0.7,
        "implicit_positive_post_update": 0.8,
        "implicit_negative_post_delete": 0.0,
        "implicit_positive_cross_tool": 0.8,
        "passive_decay": 0.0,
    }

    # Usefulness string -> signal type mapping
    _USEFULNESS_MAP: Dict[str, str] = {
        "high": "mcp_used_high",
        "medium": "mcp_used_medium",
        "low": "mcp_used_low",
    }

    def __init__(self, learning_db: Optional[Any] = None):
        """
        Args:
            learning_db: LearningDB instance for persisting feedback.
                         If None, auto-creates a LearningDB instance.
        """
        if learning_db is None:
            try:
                from .learning_db import LearningDB
                self.learning_db = LearningDB()
            except Exception:
                self.learning_db = None
        else:
            self.learning_db = learning_db

        # In-memory buffer for passive decay tracking.
        # Structure: {query_hash: {memory_id: times_returned_count}}
        # Protected by a lock since MCP/CLI/API may call concurrently.
        self._recall_buffer: Dict[str, Dict[int, int]] = {}
        self._recall_buffer_lock = threading.Lock()

        # Counter: total recall operations tracked (for decay threshold)
        self._recall_count: int = 0

    # ======================================================================
    # Channel 1: MCP -- memory_used tool
    # ======================================================================

    def record_memory_used(
        self,
        memory_id: int,
        query: str,
        usefulness: str = "high",
        source_tool: Optional[str] = None,
        rank_position: Optional[int] = None,
    ) -> Optional[int]:
        """
        Record that a memory was explicitly used after an MCP recall.

        Called by the ``memory_used`` MCP tool.  This is the highest-quality
        feedback signal because the AI agent explicitly indicates it found
        the memory useful.

        Args:
            memory_id:     ID of the used memory in memory.db.
            query:         The original recall query (hashed, not stored raw).
            usefulness:    "high", "medium", or "low".
            source_tool:   Which tool originated the query (e.g. 'claude-desktop').
            rank_position: Position of the memory in the recall results (1-based).

        Returns:
            Row ID of the feedback record, or None on error.
        """
        if not query:
            logger.warning("record_memory_used called with empty query")
            return None

        # Validate usefulness level
        usefulness = usefulness.lower().strip()
        if usefulness not in self._USEFULNESS_MAP:
            logger.warning(
                "Invalid usefulness level '%s', defaulting to 'high'",
                usefulness,
            )
            usefulness = "high"

        signal_type = self._USEFULNESS_MAP[usefulness]
        signal_value = self.SIGNAL_VALUES[signal_type]
        query_hash = self._hash_query(query)
        keywords = self._extract_keywords(query)

        return self._store_feedback(
            query_hash=query_hash,
            query_keywords=keywords,
            memory_id=memory_id,
            signal_type=signal_type,
            signal_value=signal_value,
            channel="mcp",
            source_tool=source_tool,
            rank_position=rank_position,
        )

    # ======================================================================
    # Channel 2: CLI -- slm useful <id> [<id>...]
    # ======================================================================

    def record_cli_useful(
        self,
        memory_ids: List[int],
        query: str,
    ) -> List[Optional[int]]:
        """
        Record positive feedback from the CLI ``slm useful`` command.

        Stores a positive signal for each memory_id.  The CLI typically
        captures the most recent recall query, so all IDs share the same
        query hash.

        Args:
            memory_ids: List of memory IDs the user marked as useful.
            query:      The recall query that surfaced these memories.

        Returns:
            List of row IDs (one per memory_id), or None entries on error.
        """
        if not query:
            logger.warning("record_cli_useful called with empty query")
            return [None] * len(memory_ids)

        query_hash = self._hash_query(query)
        keywords = self._extract_keywords(query)
        signal_value = self.SIGNAL_VALUES["cli_useful"]
        row_ids: List[Optional[int]] = []

        for mid in memory_ids:
            row_id = self._store_feedback(
                query_hash=query_hash,
                query_keywords=keywords,
                memory_id=mid,
                signal_type="cli_useful",
                signal_value=signal_value,
                channel="cli",
            )
            row_ids.append(row_id)

        logger.info(
            "CLI useful: %d memories marked for query_hash=%s",
            len(memory_ids),
            query_hash,
        )
        return row_ids

    # ======================================================================
    # Channel 3: Dashboard -- click events
    # ======================================================================

    def record_dashboard_click(
        self,
        memory_id: int,
        query: str,
        dwell_time: Optional[float] = None,
    ) -> Optional[int]:
        """
        Record a dashboard click on a memory card in search results.

        Optionally includes dwell time (seconds the user spent viewing
        the expanded memory).  Longer dwell times indicate higher relevance
        but this is captured as metadata, not reflected in signal_value
        (the re-ranker can learn from dwell_time as a feature).

        Args:
            memory_id:  ID of the clicked memory.
            query:      The search query active when the click happened.
            dwell_time: Seconds spent viewing the memory (optional).

        Returns:
            Row ID of the feedback record, or None on error.
        """
        if not query:
            logger.warning("record_dashboard_click called with empty query")
            return None

        query_hash = self._hash_query(query)
        keywords = self._extract_keywords(query)
        signal_value = self.SIGNAL_VALUES["dashboard_click"]

        return self._store_feedback(
            query_hash=query_hash,
            query_keywords=keywords,
            memory_id=memory_id,
            signal_type="dashboard_click",
            signal_value=signal_value,
            channel="dashboard",
            dwell_time=dwell_time,
        )

    # ======================================================================
    # Channel 4: Implicit Signals (v2.7.4 — auto-collected, zero user effort)
    # ======================================================================

    def record_implicit_signal(
        self,
        memory_id: int,
        query: str,
        signal_type: str,
        source_tool: Optional[str] = None,
        rank_position: Optional[int] = None,
    ) -> Optional[int]:
        """
        Record an implicit feedback signal inferred from user behavior.

        Called by the signal inference engine in mcp_server.py when it
        detects behavioral patterns (time gaps, re-queries, re-access, etc.).

        Args:
            memory_id:     ID of the memory.
            query:         The recall query (hashed, not stored raw).
            signal_type:   One of the implicit_* signal types.
            source_tool:   Which tool originated the query.
            rank_position: Where the memory appeared in results.

        Returns:
            Row ID of the feedback record, or None on error.
        """
        if not query or signal_type not in self.SIGNAL_VALUES:
            logger.warning(
                "record_implicit_signal: invalid query or signal_type=%s",
                signal_type,
            )
            return None

        signal_value = self.SIGNAL_VALUES[signal_type]
        query_hash = self._hash_query(query)
        keywords = self._extract_keywords(query)

        return self._store_feedback(
            query_hash=query_hash,
            query_keywords=keywords,
            memory_id=memory_id,
            signal_type=signal_type,
            signal_value=signal_value,
            channel="implicit",
            source_tool=source_tool,
            rank_position=rank_position,
        )

    def record_dashboard_feedback(
        self,
        memory_id: int,
        query: str,
        feedback_type: str,
        dwell_time: Optional[float] = None,
    ) -> Optional[int]:
        """
        Record explicit dashboard feedback (thumbs up/down, pin, dwell).

        Args:
            memory_id:     ID of the memory.
            query:         The search query active when feedback given.
            feedback_type: One of 'thumbs_up', 'thumbs_down', 'pin',
                           'dwell_positive', 'dwell_negative'.
            dwell_time:    Seconds spent viewing (for dwell signals).

        Returns:
            Row ID of the feedback record, or None on error.
        """
        type_map = {
            "thumbs_up": "dashboard_thumbs_up",
            "thumbs_down": "dashboard_thumbs_down",
            "pin": "dashboard_pin",
            "dwell_positive": "dashboard_dwell_positive",
            "dwell_negative": "dashboard_dwell_negative",
        }

        signal_type = type_map.get(feedback_type)
        if not signal_type or signal_type not in self.SIGNAL_VALUES:
            logger.warning(
                "record_dashboard_feedback: invalid feedback_type=%s",
                feedback_type,
            )
            return None

        if not query:
            query = f"__dashboard__:{memory_id}"

        signal_value = self.SIGNAL_VALUES[signal_type]
        query_hash = self._hash_query(query)
        keywords = self._extract_keywords(query)

        return self._store_feedback(
            query_hash=query_hash,
            query_keywords=keywords,
            memory_id=memory_id,
            signal_type=signal_type,
            signal_value=signal_value,
            channel="dashboard",
            dwell_time=dwell_time,
        )

    # ======================================================================
    # Passive Decay Tracking
    # ======================================================================

    def record_recall_results(
        self,
        query: str,
        returned_ids: List[int],
    ) -> None:
        """
        Track which memories were returned in a recall operation.

        This does NOT create feedback records immediately.  Instead, it
        populates an in-memory buffer.  When ``compute_passive_decay()``
        is called (periodically), memories that were returned in 5+
        distinct queries but never received a positive signal get a
        passive_decay (0.0) feedback entry.

        Args:
            query:        The recall query (hashed for grouping).
            returned_ids: Memory IDs returned by the recall.
        """
        if not query or not returned_ids:
            return

        query_hash = self._hash_query(query)

        with self._recall_buffer_lock:
            if query_hash not in self._recall_buffer:
                self._recall_buffer[query_hash] = {}

            for mid in returned_ids:
                self._recall_buffer[query_hash][mid] = (
                    self._recall_buffer[query_hash].get(mid, 0) + 1
                )

            self._recall_count += 1

    def compute_passive_decay(self, threshold: int = 10) -> int:
        """
        Emit passive decay signals for memories that appear in results
        but are never explicitly marked as useful.

        Algorithm:
            1. Only runs after *threshold* recall operations are tracked.
            2. For each memory that appeared in 5+ distinct query hashes:
               a. Check if it has ANY positive feedback in ranking_feedback.
               b. If not, insert a passive_decay signal (value=0.0).
            3. Clear the recall buffer after processing.

        This teaches the re-ranker: "this memory keeps showing up but
        nobody ever finds it useful -- demote it."

        Args:
            threshold: Minimum number of tracked recalls before running.

        Returns:
            Number of passive decay signals emitted.
        """
        with self._recall_buffer_lock:
            if self._recall_count < threshold:
                logger.debug(
                    "Passive decay skipped: %d/%d recalls tracked",
                    self._recall_count,
                    threshold,
                )
                return 0

            # Build a map: memory_id -> set of distinct query_hashes it appeared in
            memory_query_counts: Dict[int, int] = {}
            for query_hash, mem_counts in self._recall_buffer.items():
                for mid in mem_counts:
                    memory_query_counts[mid] = memory_query_counts.get(mid, 0) + 1

            # Find candidates: appeared in 5+ distinct queries
            candidates = [
                mid for mid, qcount in memory_query_counts.items()
                if qcount >= 5
            ]

            # Snapshot and clear buffer
            buffer_snapshot = dict(self._recall_buffer)
            self._recall_buffer.clear()
            self._recall_count = 0

        if not candidates:
            logger.debug("No passive decay candidates found")
            return 0

        # Check which candidates have positive feedback already
        decay_count = 0
        for mid in candidates:
            if self._has_positive_feedback(mid):
                continue

            # Emit passive decay signal.  Use a synthetic query hash
            # derived from the memory_id to group decay signals.
            decay_hash = self._hash_query(f"__passive_decay__:{mid}")
            self._store_feedback(
                query_hash=decay_hash,
                query_keywords=None,
                memory_id=mid,
                signal_type="passive_decay",
                signal_value=self.SIGNAL_VALUES["passive_decay"],
                channel="system",
            )
            decay_count += 1

        if decay_count > 0:
            logger.info(
                "Passive decay: emitted %d signals for %d candidates",
                decay_count,
                len(candidates),
            )

        return decay_count

    # ======================================================================
    # Summary & Diagnostics
    # ======================================================================

    def get_feedback_summary(self) -> dict:
        """
        Return summary statistics for display in CLI or dashboard.

        Returns:
            {
                'total_signals': 142,
                'unique_queries': 38,
                'by_channel': {'mcp': 80, 'cli': 35, 'dashboard': 20, 'system': 7},
                'by_type': {'mcp_used_high': 50, 'cli_useful': 35, ...},
                'passive_decay_pending': 12,
                'recall_buffer_size': 45,
            }
        """
        summary: Dict[str, Any] = {
            "total_signals": 0,
            "unique_queries": 0,
            "by_channel": {},
            "by_type": {},
            "passive_decay_pending": 0,
            "recall_buffer_size": 0,
        }

        # Buffer stats (always available, even without DB)
        with self._recall_buffer_lock:
            summary["recall_buffer_size"] = self._recall_count
            # Count memories that would be decay candidates
            memory_query_counts: Dict[int, int] = {}
            for _qh, mem_counts in self._recall_buffer.items():
                for mid in mem_counts:
                    memory_query_counts[mid] = memory_query_counts.get(mid, 0) + 1
            summary["passive_decay_pending"] = sum(
                1 for qcount in memory_query_counts.values() if qcount >= 5
            )

        if self.learning_db is None:
            summary["error"] = "No learning database connected"
            return summary

        try:
            conn = self.learning_db._get_connection()
            try:
                cursor = conn.cursor()

                # Total signals
                cursor.execute("SELECT COUNT(*) FROM ranking_feedback")
                summary["total_signals"] = cursor.fetchone()[0]

                # Unique queries
                cursor.execute(
                    "SELECT COUNT(DISTINCT query_hash) FROM ranking_feedback"
                )
                summary["unique_queries"] = cursor.fetchone()[0]

                # By channel
                cursor.execute(
                    "SELECT channel, COUNT(*) as cnt "
                    "FROM ranking_feedback GROUP BY channel"
                )
                summary["by_channel"] = {
                    row["channel"]: row["cnt"] for row in cursor.fetchall()
                }

                # By signal type
                cursor.execute(
                    "SELECT signal_type, COUNT(*) as cnt "
                    "FROM ranking_feedback GROUP BY signal_type"
                )
                summary["by_type"] = {
                    row["signal_type"]: row["cnt"] for row in cursor.fetchall()
                }

            finally:
                conn.close()

        except Exception as e:
            logger.error("Failed to get feedback summary: %s", e)
            summary["error"] = str(e)

        return summary

    # ======================================================================
    # Internal helpers
    # ======================================================================

    def _hash_query(self, query: str) -> str:
        """
        Privacy-preserving query hash.

        Returns the first 16 hex characters of the SHA-256 digest.
        This is sufficient for grouping without being reversible.
        """
        return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]

    def _extract_keywords(self, query: str, top_n: int = 3) -> str:
        """
        Extract the top N meaningful words from a query string.

        Removes stopwords and short tokens (< 2 chars), then returns
        the most frequent remaining words as a comma-separated string.

        Args:
            query:  Raw query text.
            top_n:  Number of keywords to extract.

        Returns:
            Comma-separated keyword string (e.g. "deploy,fastapi,docker").
            Empty string if no keywords extracted.
        """
        if not query:
            return ""

        words = _WORD_SPLIT.split(query.lower())
        # Filter stopwords and short tokens
        meaningful = [w for w in words if w and len(w) >= 2 and w not in _STOPWORDS]

        if not meaningful:
            return ""

        # Most common N words (preserves order of first occurrence for ties)
        counts = Counter(meaningful)
        top_words = [word for word, _count in counts.most_common(top_n)]
        return ",".join(top_words)

    def _store_feedback(
        self,
        query_hash: str,
        query_keywords: Optional[str],
        memory_id: int,
        signal_type: str,
        signal_value: float,
        channel: str,
        source_tool: Optional[str] = None,
        rank_position: Optional[int] = None,
        dwell_time: Optional[float] = None,
    ) -> Optional[int]:
        """
        Persist a single feedback record via LearningDB.

        Also updates the daily engagement metric counter.

        Returns:
            Row ID on success, None on failure or if no DB is available.
        """
        if self.learning_db is None:
            logger.debug(
                "Feedback not stored (no DB): memory=%d, type=%s",
                memory_id,
                signal_type,
            )
            return None

        try:
            row_id = self.learning_db.store_feedback(
                query_hash=query_hash,
                memory_id=memory_id,
                signal_type=signal_type,
                signal_value=signal_value,
                channel=channel,
                query_keywords=query_keywords,
                rank_position=rank_position,
                source_tool=source_tool,
                dwell_time=dwell_time,
            )

            # Update daily engagement counter (best-effort)
            try:
                self.learning_db.increment_engagement(
                    "feedback_signals",
                    count=1,
                    source=source_tool,
                )
            except Exception:
                pass

            return row_id

        except Exception as e:
            logger.error(
                "Failed to store feedback for memory %d: %s",
                memory_id,
                e,
            )
            return None

    def _has_positive_feedback(self, memory_id: int) -> bool:
        """
        Check if a memory has ANY positive feedback in learning.db.

        Positive = signal_value > 0.0 (anything above passive_decay).
        Used by passive decay to avoid penalising memories that were
        actually found useful at some point.

        Args:
            memory_id: Memory ID to check.

        Returns:
            True if at least one positive feedback record exists.
        """
        if self.learning_db is None:
            return False

        try:
            conn = self.learning_db._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM ranking_feedback
                    WHERE memory_id = ? AND signal_value > 0.0
                    """,
                    (memory_id,),
                )
                count = cursor.fetchone()[0]
                return count > 0
            finally:
                conn.close()
        except Exception as e:
            logger.error(
                "Failed to check positive feedback for memory %d: %s",
                memory_id,
                e,
            )
            # If we can't check, assume positive to avoid false penalisation
            return True


# ======================================================================
# Standalone execution (for diagnostics: python3 feedback_collector.py)
# ======================================================================

def main():
    """Print feedback summary from CLI."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Try to get LearningDB
    learning_db = None
    try:
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
        from learning_db import LearningDB
        learning_db = LearningDB()
    except ImportError:
        logger.warning("LearningDB not available")

    collector = FeedbackCollector(learning_db=learning_db)
    summary = collector.get_feedback_summary()

    print(f"\n{'='*60}")
    print(f"  Feedback Summary")
    print(f"{'='*60}")
    print(f"  Total signals:       {summary.get('total_signals', 0)}")
    print(f"  Unique queries:      {summary.get('unique_queries', 0)}")
    print(f"  Recall buffer size:  {summary.get('recall_buffer_size', 0)}")
    print(f"  Decay pending:       {summary.get('passive_decay_pending', 0)}")

    by_channel = summary.get("by_channel", {})
    if by_channel:
        print(f"\n  By Channel:")
        for ch, cnt in sorted(by_channel.items()):
            print(f"    {ch:>12s}: {cnt}")

    by_type = summary.get("by_type", {})
    if by_type:
        print(f"\n  By Signal Type:")
        for st, cnt in sorted(by_type.items()):
            print(f"    {st:>18s}: {cnt}")

    if "error" in summary:
        print(f"\n  Error: {summary['error']}")

    print()


if __name__ == "__main__":
    main()
