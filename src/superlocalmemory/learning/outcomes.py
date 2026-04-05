# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Outcome Tracking & Inference.

Records what happens AFTER memories are recalled: success, failure,
or partial outcomes. Also provides signal-based outcome inference
for implicit feedback loops.

Uses the ``action_outcomes`` table from the V3 schema and returns
``ActionOutcome`` dataclass instances for type safety.

The feedback loop:
  recall() -> user action -> record_outcome() -> learning engine

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import json
import logging
from typing import Any

from superlocalmemory.storage.models import ActionOutcome

logger = logging.getLogger(__name__)

# Valid outcome labels
VALID_OUTCOMES = frozenset({"success", "failure", "partial"})

# Inference signal weights
_SIGNAL_WEIGHTS: dict[str, tuple[str, float]] = {
    "used_immediately": ("success", 0.9),
    "mcp_used_high": ("success", 0.8),
    "cross_tool_access": ("success", 0.7),
    "no_requery_10m": ("success", 0.6),
    "partial_use": ("partial", 0.5),
    "requery_different_terms": ("failure", 0.3),
    "rapid_fire_queries": ("failure", 0.2),
    "deleted_after_recall": ("failure", 0.1),
    "ignored": ("failure", 0.4),
}


class OutcomeTracker:
    """Track retrieval outcomes and feed into learning.

    Accepts a ``DatabaseManager`` and operates on the ``action_outcomes``
    table created by the V3 schema.  Returns ``ActionOutcome`` dataclasses.
    """

    def __init__(self, db) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public API — Recording
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        query: str,
        fact_ids: list[str],
        outcome: str,
        profile_id: str,
        context: dict[str, Any] | None = None,
    ) -> ActionOutcome:
        """Record an outcome against one or more facts.

        Args:
            query: The recall query that produced these facts.
            fact_ids: List of fact IDs involved in the outcome.
            outcome: One of "success", "failure", "partial".
            profile_id: Profile scope.
            context: Arbitrary metadata dict.

        Returns:
            The persisted ActionOutcome.
        """
        if outcome not in VALID_OUTCOMES:
            logger.warning(
                "Invalid outcome '%s'. Must be one of %s", outcome, VALID_OUTCOMES
            )
            outcome = "partial"

        ao = ActionOutcome(
            profile_id=profile_id,
            query=query,
            fact_ids=list(fact_ids),
            outcome=outcome,
            context=dict(context) if context else {},
        )

        self._db.execute(
            "INSERT OR REPLACE INTO action_outcomes "
            "(outcome_id, profile_id, query, fact_ids_json, outcome, "
            " context_json, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ao.outcome_id,
                ao.profile_id,
                ao.query,
                json.dumps(ao.fact_ids),
                ao.outcome,
                json.dumps(ao.context),
                ao.timestamp,
            ),
        )
        return ao

    # ------------------------------------------------------------------
    # Public API — Querying
    # ------------------------------------------------------------------

    def get_outcomes(
        self,
        profile_id: str,
        limit: int = 50,
        outcome_filter: str | None = None,
    ) -> list[ActionOutcome]:
        """Get recent outcomes for a profile.

        Returns:
            List of ``ActionOutcome`` objects, newest first.
        """
        sql = "SELECT * FROM action_outcomes WHERE profile_id = ?"
        params: list[Any] = [profile_id]

        if outcome_filter and outcome_filter in VALID_OUTCOMES:
            sql += " AND outcome = ?"
            params.append(outcome_filter)

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self._db.execute(sql, tuple(params))
        return [self._row_to_outcome(r) for r in rows]

    def get_success_rate(self, profile_id: str) -> float:
        """Overall success rate.  ``success`` = 1.0, ``partial`` = 0.5."""
        rows = self._db.execute(
            "SELECT outcome, COUNT(*) AS cnt FROM action_outcomes "
            "WHERE profile_id = ? GROUP BY outcome",
            (profile_id,),
        )
        if not rows:
            return 0.0

        counts = {dict(r)["outcome"]: dict(r)["cnt"] for r in rows}
        total = sum(counts.values())
        if total == 0:
            return 0.0

        success = counts.get("success", 0)
        partial = counts.get("partial", 0) * 0.5
        return round((success + partial) / total, 4)

    def get_fact_success_rate(self, fact_id: str, profile_id: str) -> float:
        """How often a specific fact led to successful outcomes.

        Returns 0.5 (neutral) if no relevant data exists.
        """
        outcomes = self.get_outcomes(profile_id, limit=500)
        relevant = [o for o in outcomes if fact_id in o.fact_ids]

        if not relevant:
            return 0.5

        successes = sum(1 for o in relevant if o.outcome == "success")
        return round(successes / len(relevant), 4)

    # ------------------------------------------------------------------
    # Public API — Inference
    # ------------------------------------------------------------------

    def infer_outcome(
        self,
        profile_id: str,
        fact_ids: list[str],
        signals: dict[str, Any],
    ) -> str:
        """Infer outcome from behavioral signals and auto-record it."""
        success_score = 0.0
        failure_score = 0.0
        matched_signals: list[str] = []

        for signal_name, value in signals.items():
            if not value:
                continue
            if signal_name in _SIGNAL_WEIGHTS:
                outcome_label, weight = _SIGNAL_WEIGHTS[signal_name]
                matched_signals.append(signal_name)
                if outcome_label == "success":
                    success_score += weight
                elif outcome_label == "failure":
                    failure_score += weight
                else:
                    success_score += weight * 0.5
                    failure_score += weight * 0.5

        if success_score > failure_score:
            inferred = "success"
        elif failure_score > success_score:
            inferred = "failure"
        else:
            inferred = "partial"

        self.record_outcome(
            query="[inferred]",
            fact_ids=fact_ids,
            outcome=inferred,
            profile_id=profile_id,
            context={
                "signals": matched_signals,
                "success_score": round(success_score, 3),
                "failure_score": round(failure_score, 3),
            },
        )
        return inferred

    # ------------------------------------------------------------------
    # Public API — Maintenance
    # ------------------------------------------------------------------

    def delete_outcomes(self, profile_id: str) -> int:
        """Delete all outcomes for a profile. Returns count deleted."""
        rows = self._db.execute(
            "SELECT COUNT(*) AS c FROM action_outcomes WHERE profile_id = ?",
            (profile_id,),
        )
        count = int(dict(rows[0])["c"]) if rows else 0
        self._db.execute(
            "DELETE FROM action_outcomes WHERE profile_id = ?",
            (profile_id,),
        )
        return count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_outcome(row) -> ActionOutcome:
        """Convert a DB row to ActionOutcome."""
        d = dict(row)
        return ActionOutcome(
            outcome_id=d["outcome_id"],
            profile_id=d["profile_id"],
            query=d.get("query", ""),
            fact_ids=json.loads(d.get("fact_ids_json", "[]")),
            outcome=d.get("outcome", ""),
            context=json.loads(d.get("context_json", "{}")),
            timestamp=d.get("timestamp", ""),
        )
