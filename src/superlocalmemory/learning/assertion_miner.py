# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Behavioral Assertion Miner — extracts learned patterns from tool events and facts.

Zero-LLM approach: uses frequency analysis, co-occurrence detection, and
temporal clustering to discover behavioral patterns. No external model calls.

Runs as Step 8 in the consolidation pipeline.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_EVIDENCE = 3  # Minimum events to create an assertion
MAX_ASSERTIONS_PER_RUN = 20  # Cap assertions per mining cycle
REINFORCEMENT_NUDGE = 0.15  # Bayesian confidence increase
PROMOTION_MIN_PROJECTS = 2  # Minimum projects for cross-project promotion
PROMOTION_MIN_CONFIDENCE = 0.8  # Minimum avg confidence for promotion


class AssertionMiner:
    """Mine tool_events + atomic_facts for behavioral assertions.

    Discovers patterns like:
    - "User always reads a file before editing it" (tool sequence)
    - "User corrects verbose output frequently" (correction pattern)
    - "User prefers morning for debugging tasks" (temporal clustering)
    - "User pairs tool X with tool Y 90% of the time" (co-occurrence)
    """

    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)

    def mine(self, profile_id: str = "default") -> dict:
        """Run all mining strategies. Returns summary of assertions created/reinforced."""
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        results = {"created": 0, "reinforced": 0, "strategies": {}}

        try:
            # Strategy 1: Tool sequence patterns
            s1 = self._mine_tool_sequences(conn, profile_id)
            results["strategies"]["tool_sequences"] = s1
            results["created"] += s1.get("created", 0)
            results["reinforced"] += s1.get("reinforced", 0)

            # Strategy 2: Correction patterns
            s2 = self._mine_correction_patterns(conn, profile_id)
            results["strategies"]["corrections"] = s2
            results["created"] += s2.get("created", 0)
            results["reinforced"] += s2.get("reinforced", 0)

            # Strategy 3: Tool preference patterns
            s3 = self._mine_tool_preferences(conn, profile_id)
            results["strategies"]["tool_preferences"] = s3
            results["created"] += s3.get("created", 0)
            results["reinforced"] += s3.get("reinforced", 0)

            # Strategy 4: Temporal patterns
            s4 = self._mine_temporal_patterns(conn, profile_id)
            results["strategies"]["temporal"] = s4
            results["created"] += s4.get("created", 0)
            results["reinforced"] += s4.get("reinforced", 0)

            # Strategy 5: Cross-project assertion promotion
            s5 = self._promote_cross_project(conn, profile_id)
            results["strategies"]["cross_project"] = s5
            results["created"] += s5.get("promoted", 0)

            conn.commit()
        except Exception as exc:
            logger.warning("Assertion mining failed: %s", exc)
            results["error"] = str(exc)
        finally:
            conn.close()

        logger.info(
            "Assertion mining: %d created, %d reinforced",
            results["created"], results["reinforced"],
        )
        return results

    # ------------------------------------------------------------------
    # Strategy 1: Tool sequence patterns
    # ------------------------------------------------------------------

    def _mine_tool_sequences(self, conn: sqlite3.Connection, profile_id: str) -> dict:
        """Detect repeated tool sequences (A→B patterns)."""
        result = {"created": 0, "reinforced": 0}

        rows = conn.execute(
            "SELECT tool_name, created_at FROM tool_events "
            "WHERE profile_id = ? ORDER BY created_at ASC LIMIT 5000",
            (profile_id,),
        ).fetchall()

        if len(rows) < MIN_EVIDENCE * 2:
            return result

        # Count bigram sequences
        bigrams: Counter = Counter()
        for i in range(len(rows) - 1):
            a = rows[i]["tool_name"]
            b = rows[i + 1]["tool_name"]
            if a != b:  # Skip self-loops
                bigrams[(a, b)] += 1

        total_transitions = sum(bigrams.values())
        for (tool_a, tool_b), count in bigrams.most_common(10):
            if count < MIN_EVIDENCE:
                break
            pct = count / total_transitions
            if pct < 0.05:  # Skip rare sequences
                continue

            trigger = f"when using {tool_a}"
            action = f"typically follow with {tool_b} ({count} times, {pct:.0%} of transitions)"
            r = self._upsert_assertion(
                conn, profile_id,
                trigger=trigger, action=action,
                category="tool_preference",
                evidence_count=count,
                confidence=min(0.9, pct * 2),
            )
            result[r] = result.get(r, 0) + 1

        return result

    # ------------------------------------------------------------------
    # Strategy 2: Correction patterns
    # ------------------------------------------------------------------

    def _mine_correction_patterns(self, conn: sqlite3.Connection, profile_id: str) -> dict:
        """Detect tools with high correction rates."""
        result = {"created": 0, "reinforced": 0}

        rows = conn.execute(
            "SELECT tool_name, event_type, COUNT(*) as cnt "
            "FROM tool_events WHERE profile_id = ? "
            "GROUP BY tool_name, event_type",
            (profile_id,),
        ).fetchall()

        tool_stats: dict = {}
        for row in rows:
            tool = row["tool_name"]
            if tool not in tool_stats:
                tool_stats[tool] = {"total": 0, "corrections": 0, "errors": 0}
            tool_stats[tool]["total"] += row["cnt"]
            if row["event_type"] == "correction":
                tool_stats[tool]["corrections"] = row["cnt"]
            elif row["event_type"] == "error":
                tool_stats[tool]["errors"] = row["cnt"]

        for tool, stats in tool_stats.items():
            if stats["total"] < MIN_EVIDENCE:
                continue
            correction_rate = stats["corrections"] / stats["total"]
            if correction_rate > 0.15:  # 15%+ correction rate
                trigger = f"when using {tool}"
                action = (
                    f"high correction rate ({stats['corrections']}/{stats['total']} = "
                    f"{correction_rate:.0%}) — review output before accepting"
                )
                r = self._upsert_assertion(
                    conn, profile_id,
                    trigger=trigger, action=action,
                    category="workflow",
                    evidence_count=stats["corrections"],
                    confidence=min(0.85, correction_rate),
                )
                result[r] = result.get(r, 0) + 1

        return result

    # ------------------------------------------------------------------
    # Strategy 3: Tool preference patterns
    # ------------------------------------------------------------------

    def _mine_tool_preferences(self, conn: sqlite3.Connection, profile_id: str) -> dict:
        """Detect dominant tool usage patterns."""
        result = {"created": 0, "reinforced": 0}

        rows = conn.execute(
            "SELECT tool_name, COUNT(*) as cnt "
            "FROM tool_events WHERE profile_id = ? "
            "GROUP BY tool_name ORDER BY cnt DESC LIMIT 10",
            (profile_id,),
        ).fetchall()

        if not rows:
            return result

        total = sum(r["cnt"] for r in rows)
        for row in rows[:5]:
            tool = row["tool_name"]
            count = row["cnt"]
            pct = count / total
            if count >= MIN_EVIDENCE and pct > 0.1:
                trigger = "general workflow"
                action = f"frequently uses {tool} ({count} times, {pct:.0%} of all tool usage)"
                r = self._upsert_assertion(
                    conn, profile_id,
                    trigger=trigger, action=action,
                    category="tool_preference",
                    evidence_count=count,
                    confidence=min(0.8, pct),
                )
                result[r] = result.get(r, 0) + 1

        return result

    # ------------------------------------------------------------------
    # Strategy 4: Temporal patterns
    # ------------------------------------------------------------------

    def _mine_temporal_patterns(self, conn: sqlite3.Connection, profile_id: str) -> dict:
        """Detect time-of-day usage patterns."""
        result = {"created": 0, "reinforced": 0}

        rows = conn.execute(
            "SELECT created_at FROM tool_events "
            "WHERE profile_id = ? AND created_at IS NOT NULL LIMIT 5000",
            (profile_id,),
        ).fetchall()

        if len(rows) < MIN_EVIDENCE:
            return result

        hour_counts: Counter = Counter()
        for row in rows:
            try:
                dt = datetime.fromisoformat(row["created_at"])
                hour_counts[dt.hour] += 1
            except (ValueError, TypeError):
                continue

        if not hour_counts:
            return result

        total = sum(hour_counts.values())
        # Find peak hours (>15% of activity)
        peak_hours = [h for h, c in hour_counts.most_common() if c / total > 0.15]
        if peak_hours:
            hour_labels = ", ".join(f"{h}:00" for h in sorted(peak_hours))
            trigger = "session scheduling"
            action = f"peak activity hours: {hour_labels} (based on {total} events)"
            r = self._upsert_assertion(
                conn, profile_id,
                trigger=trigger, action=action,
                category="workflow",
                evidence_count=total,
                confidence=0.6,
            )
            result[r] = result.get(r, 0) + 1

        return result

    # ------------------------------------------------------------------
    # Strategy 5: Cross-project assertion promotion
    # ------------------------------------------------------------------

    def _promote_cross_project(
        self, conn: sqlite3.Connection, profile_id: str,
    ) -> dict:
        """Promote assertions that appear in 2+ projects to global scope.

        When the same trigger+action pattern is observed across multiple
        project_paths with avg confidence >= 0.8, create a global assertion
        (project_path='') so it applies everywhere.
        """
        result = {"promoted": 0, "candidates": 0}

        # Find assertions grouped by trigger+action across projects
        rows = conn.execute(
            "SELECT trigger_condition, action, category, "
            "COUNT(DISTINCT project_path) AS project_count, "
            "AVG(confidence) AS avg_confidence, "
            "SUM(evidence_count) AS total_evidence "
            "FROM behavioral_assertions "
            "WHERE profile_id = ? AND project_path != '' "
            "GROUP BY trigger_condition, action "
            "HAVING COUNT(DISTINCT project_path) >= ?",
            (profile_id, PROMOTION_MIN_PROJECTS),
        ).fetchall()

        result["candidates"] = len(rows)

        for row in rows:
            avg_conf = row["avg_confidence"]
            if avg_conf < PROMOTION_MIN_CONFIDENCE:
                continue

            trigger = row["trigger_condition"]
            action = row["action"]
            category = row["category"]
            total_ev = row["total_evidence"]
            project_count = row["project_count"]

            # Check if global assertion already exists
            global_id = hashlib.sha256(
                f"{profile_id}:{trigger}:{action}".encode()
            ).hexdigest()[:16]

            existing = conn.execute(
                "SELECT id FROM behavioral_assertions "
                "WHERE id = ? AND project_path = ''",
                (global_id,),
            ).fetchone()

            if existing:
                # Reinforce existing global assertion
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "UPDATE behavioral_assertions SET "
                    "confidence = MIN(0.95, confidence + ?), "
                    "evidence_count = ?, "
                    "reinforcement_count = reinforcement_count + 1, "
                    "last_reinforced_at = ?, updated_at = ? "
                    "WHERE id = ?",
                    (REINFORCEMENT_NUDGE, total_ev, now, now, global_id),
                )
            else:
                # Create new global assertion from cross-project evidence
                now = datetime.now(timezone.utc).isoformat()
                promoted_conf = min(0.9, avg_conf)
                conn.execute(
                    "INSERT INTO behavioral_assertions "
                    "(id, profile_id, project_path, trigger_condition, action, "
                    " category, confidence, evidence_count, source, "
                    " created_at, updated_at) "
                    "VALUES (?, ?, '', ?, ?, ?, ?, ?, 'cross_project', ?, ?)",
                    (global_id, profile_id, trigger, action,
                     category, round(promoted_conf, 4), total_ev, now, now),
                )
                result["promoted"] += 1
                logger.info(
                    "Promoted assertion to global: '%s' → '%s' "
                    "(from %d projects, avg_conf=%.2f)",
                    trigger, action, project_count, avg_conf,
                )

        return result

    # ------------------------------------------------------------------
    # Upsert logic
    # ------------------------------------------------------------------

    def _upsert_assertion(
        self, conn: sqlite3.Connection, profile_id: str, *,
        trigger: str, action: str, category: str,
        evidence_count: int, confidence: float,
        project_path: str = "",
    ) -> str:
        """Create or reinforce a behavioral assertion. Returns 'created' or 'reinforced'."""
        now = datetime.now(timezone.utc).isoformat()

        # Deterministic ID from trigger+action for idempotent upsert
        assertion_id = hashlib.sha256(
            f"{profile_id}:{trigger}:{action}".encode()
        ).hexdigest()[:16]

        existing = conn.execute(
            "SELECT id, confidence, reinforcement_count FROM behavioral_assertions WHERE id = ?",
            (assertion_id,),
        ).fetchone()

        if existing:
            # Reinforce: Bayesian nudge toward 1.0
            old_conf = existing["confidence"]
            new_conf = old_conf + (1.0 - old_conf) * REINFORCEMENT_NUDGE
            conn.execute(
                "UPDATE behavioral_assertions SET confidence = ?, "
                "evidence_count = ?, reinforcement_count = reinforcement_count + 1, "
                "last_reinforced_at = ?, updated_at = ? WHERE id = ?",
                (round(new_conf, 4), evidence_count, now, now, assertion_id),
            )
            return "reinforced"
        else:
            # Create new assertion at initial confidence
            conn.execute(
                "INSERT INTO behavioral_assertions "
                "(id, profile_id, project_path, trigger_condition, action, "
                " category, confidence, evidence_count, source, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'auto', ?, ?)",
                (assertion_id, profile_id, project_path, trigger, action,
                 category, round(min(confidence, 0.7), 4), evidence_count, now, now),
            )
            return "created"
