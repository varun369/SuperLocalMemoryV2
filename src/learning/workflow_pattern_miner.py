#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Workflow Pattern Miner (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Repository: https://github.com/varun369/SuperLocalMemoryV2
Author: Varun Pratap Bhardwaj (Solution Architect)

NOTICE: This software is protected by MIT License.
Attribution must be preserved in all copies or derivatives.
"""

"""
WorkflowPatternMiner -- Layer 3: Sliding-window sequence and temporal pattern mining.

Detects repeating workflow sequences and time-of-day activity preferences
from memory creation timestamps and content.  Uses a custom sliding-window
n-gram approach inspired by TSW-PrefixSpan (IEEE 2020) -- NO external
dependencies beyond stdlib.

How it works:
    1. Fetches recent memories from memory.db (read-only).
    2. Classifies each memory into one of 7 activity types via keyword scoring.
    3. Extracts n-gram sequences (length 2-5) from the ordered activity stream.
    4. Calculates support (frequency / total windows) for each n-gram.
    5. Mines temporal patterns (dominant activity per time-of-day bucket).
    6. Stores discovered patterns in learning.db via LearningDB.

Design decisions:
    - Word-boundary matching prevents false positives (e.g. "document" != "docs").
    - Consecutive identical activities in an n-gram are skipped as noise.
    - Minimum evidence threshold (5 memories) prevents weak temporal claims.
    - Patterns are cleared and re-mined each run (idempotent operation).
"""

import json
import logging
import re
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("superlocalmemory.learning.workflow")

MEMORY_DIR = Path.home() / ".claude-memory"
MEMORY_DB_PATH = MEMORY_DIR / "memory.db"

# ---------------------------------------------------------------------------
# Activity type taxonomy (7 categories)
# ---------------------------------------------------------------------------
# Each key maps to a list of keyword phrases.  Scoring is word-boundary aware
# to avoid partial matches (e.g. "test" won't match inside "latest").

ACTIVITY_TYPES: Dict[str, List[str]] = {
    "docs": [
        "documentation", "readme", "wiki", "spec", "prd",
        "design doc", "changelog", "api doc",
    ],
    "architecture": [
        "architecture", "diagram", "system design", "schema",
        "api design", "data model", "erd",
    ],
    "code": [
        "implement", "function", "class", "module", "refactor",
        "code", "feature", "component",
    ],
    "test": [
        "test", "pytest", "jest", "coverage", "assertion",
        "mock", "spec", "unit test",
    ],
    "debug": [
        "bug", "fix", "error", "stack trace", "debug",
        "issue", "exception", "traceback",
    ],
    "deploy": [
        "deploy", "docker", "ci/cd", "pipeline", "release",
        "production", "staging", "build",
    ],
    "config": [
        "config", "env", "settings", "setup", "install",
        "dependency", "package", "requirements",
    ],
}

# Pre-compile word-boundary regexes per keyword for performance.
# Each entry: (activity_type, compiled_regex)
_KEYWORD_PATTERNS: List[tuple] = []
for _act_type, _keywords in ACTIVITY_TYPES.items():
    for _kw in _keywords:
        # Use re.escape for phrases that may contain special chars (e.g. "ci/cd")
        _KEYWORD_PATTERNS.append(
            (_act_type, re.compile(r"\b" + re.escape(_kw) + r"\b", re.IGNORECASE))
        )


class WorkflowPatternMiner:
    """
    Mines workflow sequences and temporal patterns from memory history.

    Reads from memory.db (never writes to it) and stores discovered
    patterns in learning.db via the shared LearningDB instance.

    Usage:
        from learning.learning_db import LearningDB
        miner = WorkflowPatternMiner(learning_db=LearningDB())
        results = miner.mine_all()
        print(results['sequences'])   # Top workflow sequences
        print(results['temporal'])    # Time-of-day preferences
    """

    def __init__(
        self,
        memory_db_path: Optional[Path] = None,
        learning_db: Optional[Any] = None,
    ):
        """
        Args:
            memory_db_path: Path to memory.db for reading memories.
                            Defaults to ~/.claude-memory/memory.db.
            learning_db:    LearningDB instance for storing patterns.
                            If None, patterns are returned but not persisted.
        """
        self.memory_db_path = Path(memory_db_path) if memory_db_path else MEMORY_DB_PATH
        self.learning_db = learning_db

    # ======================================================================
    # Public API
    # ======================================================================

    def mine_sequences(
        self,
        memories: Optional[List[dict]] = None,
        min_support: float = 0.3,
    ) -> List[dict]:
        """
        Mine repeating workflow sequences from memory content.

        Algorithm:
            1. Classify each memory into an activity type.
            2. Build an ordered activity stream (chronological).
            3. Extract n-grams of length 2-5 via sliding window.
            4. Filter out n-grams with consecutive identical activities.
            5. Compute support = count / total_windows_for_that_length.
            6. Return top 20 patterns above *min_support*.

        Args:
            memories:    List of memory dicts with 'content' and 'created_at'.
                         If None, fetches the last 500 from memory.db.
            min_support: Minimum support threshold (0.0 - 1.0).  Default 0.3.

        Returns:
            Sorted list of dicts:
                [{'sequence': ['docs', 'code', 'test'],
                  'support': 0.45, 'count': 12, 'length': 3}, ...]
        """
        if memories is None:
            memories = self._fetch_memories(limit=500)

        if not memories:
            logger.info("No memories to mine sequences from")
            return []

        # Step 1 + 2: classify and build activity stream
        activity_stream: List[str] = []
        for mem in memories:
            activity = self._classify_activity(mem.get("content", ""))
            if activity != "unknown":
                activity_stream.append(activity)

        if len(activity_stream) < 2:
            logger.info(
                "Activity stream too short (%d) for sequence mining",
                len(activity_stream),
            )
            return []

        # Step 3-5: extract n-grams and compute support
        all_patterns: List[dict] = []

        for n in range(2, 6):  # lengths 2, 3, 4, 5
            if len(activity_stream) < n:
                continue

            ngram_counts: Counter = Counter()
            total_windows = len(activity_stream) - n + 1

            for i in range(total_windows):
                ngram = tuple(activity_stream[i : i + n])

                # Skip n-grams where any consecutive pair repeats (noise)
                has_repeat = any(
                    ngram[j] == ngram[j + 1] for j in range(len(ngram) - 1)
                )
                if has_repeat:
                    continue

                ngram_counts[ngram] += 1

            # Convert to pattern dicts with support
            for ngram, count in ngram_counts.items():
                support = count / total_windows if total_windows > 0 else 0.0
                if support >= min_support:
                    all_patterns.append({
                        "sequence": list(ngram),
                        "support": round(support, 4),
                        "count": count,
                        "length": n,
                    })

        # Step 6: sort by support descending, limit to top 20
        all_patterns.sort(key=lambda p: (-p["support"], -p["length"]))
        top_patterns = all_patterns[:20]

        logger.info(
            "Mined %d sequence patterns from %d activities (top %d returned)",
            len(all_patterns),
            len(activity_stream),
            len(top_patterns),
        )
        return top_patterns

    def mine_temporal_patterns(
        self,
        memories: Optional[List[dict]] = None,
    ) -> Dict[str, dict]:
        """
        Detect time-of-day activity preferences.

        Buckets each memory by hour into morning/afternoon/evening/night,
        counts activity types per bucket, and identifies the dominant
        activity type for each time period.

        Args:
            memories: List of memory dicts with 'content' and 'created_at'.
                      If None, fetches from memory.db.

        Returns:
            Dict keyed by bucket name:
                {'morning': {
                    'dominant_activity': 'code',
                    'confidence': 0.65,
                    'evidence_count': 23,
                    'distribution': {'code': 15, 'test': 5, 'debug': 3}
                }, ...}

            Buckets with fewer than 5 evidence memories are omitted.
        """
        if memories is None:
            memories = self._fetch_memories(limit=500)

        if not memories:
            logger.info("No memories to mine temporal patterns from")
            return {}

        # bucket_name -> Counter of activity types
        bucket_activities: Dict[str, Counter] = {
            "morning": Counter(),
            "afternoon": Counter(),
            "evening": Counter(),
            "night": Counter(),
        }

        for mem in memories:
            activity = self._classify_activity(mem.get("content", ""))
            if activity == "unknown":
                continue

            hour = self._parse_hour(mem.get("created_at"))
            if hour is None:
                continue

            bucket = self._hour_to_bucket(hour)
            bucket_activities[bucket][activity] += 1

        # Build result: only include buckets with minimum evidence
        min_evidence = 5
        result: Dict[str, dict] = {}

        for bucket, counter in bucket_activities.items():
            total = sum(counter.values())
            if total < min_evidence:
                continue

            dominant_activity, dominant_count = counter.most_common(1)[0]
            confidence = round(dominant_count / total, 4) if total > 0 else 0.0

            result[bucket] = {
                "dominant_activity": dominant_activity,
                "confidence": confidence,
                "evidence_count": total,
                "distribution": dict(counter),
            }

        logger.info(
            "Mined temporal patterns for %d/%d buckets",
            len(result),
            len(bucket_activities),
        )
        return result

    def mine_all(
        self,
        memories: Optional[List[dict]] = None,
    ) -> dict:
        """
        Run all mining methods and optionally persist results to learning.db.

        Fetches memories once and passes to both miners.  If a LearningDB
        instance was provided at init, clears old patterns and stores new ones.

        Args:
            memories: Pre-fetched memories, or None to auto-fetch.

        Returns:
            {'sequences': [...], 'temporal': {...}}
        """
        if memories is None:
            memories = self._fetch_memories(limit=500)

        sequences = self.mine_sequences(memories=memories)
        temporal = self.mine_temporal_patterns(memories=memories)

        # Persist to learning.db if available
        if self.learning_db is not None:
            self._persist_patterns(sequences, temporal)

        return {
            "sequences": sequences,
            "temporal": temporal,
        }

    def get_workflow_insights(self) -> dict:
        """
        Read stored patterns from learning.db and format for display.

        Returns a user-friendly summary suitable for CLI output or
        dashboard rendering.  If no learning_db, returns empty structure.
        """
        if self.learning_db is None:
            return {
                "sequences": [],
                "temporal": {},
                "summary": "No learning database connected",
            }

        try:
            seq_patterns = self.learning_db.get_workflow_patterns(
                pattern_type="sequence",
            )
            temp_patterns = self.learning_db.get_workflow_patterns(
                pattern_type="temporal",
            )
        except Exception as e:
            logger.error("Failed to read workflow patterns: %s", e)
            return {
                "sequences": [],
                "temporal": {},
                "summary": "Error reading patterns",
            }

        # Parse stored JSON values back into structured data
        sequences = []
        for p in seq_patterns:
            try:
                value = json.loads(p.get("pattern_value", "{}"))
                sequences.append({
                    "sequence": value.get("sequence", []),
                    "support": p.get("confidence", 0.0),
                    "count": p.get("evidence_count", 0),
                    "length": len(value.get("sequence", [])),
                })
            except (json.JSONDecodeError, TypeError):
                continue

        temporal = {}
        for p in temp_patterns:
            try:
                value = json.loads(p.get("pattern_value", "{}"))
                bucket_name = p.get("pattern_key", "unknown")
                temporal[bucket_name] = value
            except (json.JSONDecodeError, TypeError):
                continue

        # Build a natural language summary
        summary_parts = []
        if sequences:
            top = sequences[0]
            seq_str = " -> ".join(top["sequence"])
            summary_parts.append(
                f"Most common workflow: {seq_str} "
                f"(support={top['support']:.0%}, seen {top['count']}x)"
            )
        if temporal:
            for bucket, info in sorted(temporal.items()):
                dominant = info.get("dominant_activity", "?")
                conf = info.get("confidence", 0)
                summary_parts.append(
                    f"  {bucket}: mostly {dominant} ({conf:.0%} confidence)"
                )

        return {
            "sequences": sequences,
            "temporal": temporal,
            "summary": "\n".join(summary_parts) if summary_parts else "No patterns discovered yet",
        }

    # ======================================================================
    # Internal helpers
    # ======================================================================

    def _classify_activity(self, content: str) -> str:
        """
        Classify a memory's content into one of the 7 activity types.

        Scores each type by counting word-boundary keyword matches in the
        content.  Returns the highest-scoring type, or 'unknown' if no
        keywords matched.

        Args:
            content: Raw memory content string.

        Returns:
            Activity type string (e.g. 'code', 'test') or 'unknown'.
        """
        if not content:
            return "unknown"

        scores: Counter = Counter()

        for act_type, pattern in _KEYWORD_PATTERNS:
            if pattern.search(content):
                scores[act_type] += 1

        if not scores:
            return "unknown"

        # Return the type with the highest score
        best_type, _best_count = scores.most_common(1)[0]
        return best_type

    def _hour_to_bucket(self, hour: int) -> str:
        """
        Map an hour (0-23) to a time-of-day bucket.

        Buckets:
            morning   = 6-11
            afternoon = 12-17
            evening   = 18-23
            night     = 0-5
        """
        if 6 <= hour <= 11:
            return "morning"
        elif 12 <= hour <= 17:
            return "afternoon"
        elif 18 <= hour <= 23:
            return "evening"
        else:  # 0-5
            return "night"

    def _parse_hour(self, timestamp: Optional[str]) -> Optional[int]:
        """
        Extract the hour from a timestamp string.

        Handles multiple formats gracefully:
            - ISO 8601:  '2026-02-14T09:30:00'
            - SQLite:    '2026-02-14 09:30:00'
            - Date only: '2026-02-14' (returns None -- no time info)

        Returns:
            Hour as int (0-23), or None if parsing fails.
        """
        if not timestamp:
            return None

        # Try ISO format first (handles both 'T' and space separator)
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                dt = datetime.strptime(timestamp, fmt)
                return dt.hour
            except (ValueError, TypeError):
                continue

        # Last resort: fromisoformat (Python 3.7+), handles wider range
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.hour
        except (ValueError, TypeError):
            pass

        logger.debug("Could not parse timestamp: %s", timestamp)
        return None

    def _fetch_memories(self, limit: int = 500) -> List[dict]:
        """
        Read recent memories from memory.db (read-only).

        Fetches id, content, created_at, and project_name ordered
        chronologically (ASC) so the activity stream preserves the
        user's actual workflow order.

        Args:
            limit: Maximum number of memories to fetch.

        Returns:
            List of dicts with keys: id, content, created_at, project_name.
            Returns empty list on any error.
        """
        if not self.memory_db_path.exists():
            logger.warning("memory.db not found at %s", self.memory_db_path)
            return []

        try:
            conn = sqlite3.connect(str(self.memory_db_path), timeout=5)
            conn.row_factory = sqlite3.Row
            # Read-only pragmas
            conn.execute("PRAGMA query_only=ON")
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, content, created_at, project_name
                FROM memories
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error("Failed to fetch memories: %s", e)
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _persist_patterns(
        self,
        sequences: List[dict],
        temporal: Dict[str, dict],
    ) -> None:
        """
        Clear old patterns and store newly mined ones in learning.db.

        Uses LearningDB.clear_workflow_patterns() then store_workflow_pattern()
        for each discovered pattern.  This is idempotent -- safe to call
        repeatedly.
        """
        if self.learning_db is None:
            return

        try:
            # Clear previous patterns (idempotent re-mine)
            self.learning_db.clear_workflow_patterns(pattern_type="sequence")
            self.learning_db.clear_workflow_patterns(pattern_type="temporal")

            # Store sequence patterns
            for pat in sequences:
                pattern_key = " -> ".join(pat["sequence"])
                pattern_value = json.dumps({
                    "sequence": pat["sequence"],
                    "count": pat["count"],
                })
                self.learning_db.store_workflow_pattern(
                    pattern_type="sequence",
                    pattern_key=pattern_key,
                    pattern_value=pattern_value,
                    confidence=pat["support"],
                    evidence_count=pat["count"],
                    metadata={"length": pat["length"]},
                )

            # Store temporal patterns
            for bucket_name, info in temporal.items():
                pattern_value = json.dumps(info)
                self.learning_db.store_workflow_pattern(
                    pattern_type="temporal",
                    pattern_key=bucket_name,
                    pattern_value=pattern_value,
                    confidence=info.get("confidence", 0.0),
                    evidence_count=info.get("evidence_count", 0),
                    metadata={"dominant_activity": info.get("dominant_activity")},
                )

            total_stored = len(sequences) + len(temporal)
            logger.info("Persisted %d workflow patterns to learning.db", total_stored)

            # Update engagement metric
            try:
                self.learning_db.increment_engagement(
                    "patterns_updated",
                    count=total_stored,
                )
            except Exception:
                pass  # Engagement tracking is best-effort

        except Exception as e:
            logger.error("Failed to persist workflow patterns: %s", e)


# ======================================================================
# Standalone execution (for CLI: python3 workflow_pattern_miner.py)
# ======================================================================

def main():
    """Run workflow mining from CLI and print results."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Try to get LearningDB
    learning_db = None
    try:
        # When run from src/learning/ directory or installed path
        sys.path.insert(0, str(Path(__file__).parent))
        from learning_db import LearningDB
        learning_db = LearningDB()
    except ImportError:
        logger.warning("LearningDB not available -- patterns will not be persisted")

    miner = WorkflowPatternMiner(learning_db=learning_db)
    results = miner.mine_all()

    # Pretty-print sequences
    sequences = results.get("sequences", [])
    if sequences:
        print(f"\n{'='*60}")
        print(f"  Workflow Sequences ({len(sequences)} patterns)")
        print(f"{'='*60}")
        for i, pat in enumerate(sequences, 1):
            seq_str = " -> ".join(pat["sequence"])
            print(f"  {i:2d}. {seq_str}")
            print(f"      support={pat['support']:.1%}  count={pat['count']}  length={pat['length']}")
    else:
        print("\n  No workflow sequences found.")

    # Pretty-print temporal patterns
    temporal = results.get("temporal", {})
    if temporal:
        print(f"\n{'='*60}")
        print(f"  Temporal Patterns")
        print(f"{'='*60}")
        for bucket in ("morning", "afternoon", "evening", "night"):
            if bucket in temporal:
                info = temporal[bucket]
                print(f"  {bucket:>10s}: {info['dominant_activity']:<14s} "
                      f"confidence={info['confidence']:.0%}  "
                      f"evidence={info['evidence_count']}")
    else:
        print("\n  No temporal patterns found (need >= 5 memories per time bucket).")

    print()


if __name__ == "__main__":
    main()
