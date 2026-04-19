# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory v3.4.21 — Track A.3 (LLD-10 §5)

"""Post-promotion watch + auto-rollback (LLD-10 §5).

After promotion flips ``is_active`` to the new row, the next 200
recalls are measured against the pre-promotion baseline. If mean
NDCG@10 drops by ≥ REGRESSION_THRESHOLD (2%), auto-rollback fires:

* Current active → ``is_rollback=1``, ``is_active=0``,
  ``rollback_reason=<reason>``.
* Former ``is_previous`` → ``is_active=1``, ``is_previous=0``.
* ``metadata_json.retrain_disabled_until`` set to now+24h; counter
  reset to 0.

All three flag flips happen inside one ``BEGIN IMMEDIATE`` transaction.
The partial unique indexes ``idx_model_active_one`` and
``idx_model_candidate_one`` (M009) enforce single-active and
single-candidate per profile.

Failure-mode handling (LLD-10 §5.4 "missing is_previous"):
   If the is_previous row is absent, we do NOT demote the current
   active — that would leave the profile with no active model.
   Instead we log an error, set ``metadata_json.safe_mode=1`` on the
   active row, and let AdaptiveRanker fall back to Phase-2 heuristic.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Final

logger = logging.getLogger(__name__)


_WATCH_WINDOW: Final[int] = 200
_REGRESSION_THRESHOLD: Final[float] = 0.02
_RETRAIN_DISABLED_HOURS: Final[int] = 24

#: Baseline floor below which the ratio ``(baseline - current) / baseline``
#: is numerically meaningless (division explodes; a 1pp drop on a 0.5%
#: baseline looks like 200% regression). Below this floor we switch to
#: an ABSOLUTE-drop comparison against ``_REGRESSION_THRESHOLD``. Stage 8
#: F4.B H-04 fix — previously baseline ≤ 0 silently disarmed the
#: watchdog, which meant a freshly-promoted-but-broken model with a
#: sparse-data baseline of 0 would never auto-rollback.
_BASELINE_RATIO_FLOOR: Final[float] = 0.05


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_in_hours(hours: int) -> str:
    return (
        datetime.now(timezone.utc) + timedelta(hours=hours)
    ).isoformat()


class ModelRollback:
    """Watch post-promotion NDCG@10 and flip lineage on regression."""

    WATCH_WINDOW: Final[int] = _WATCH_WINDOW
    REGRESSION_THRESHOLD: Final[float] = _REGRESSION_THRESHOLD
    RETRAIN_DISABLED_HOURS: Final[int] = _RETRAIN_DISABLED_HOURS

    def __init__(
        self,
        *,
        learning_db_path: str,
        profile_id: str,
        baseline_ndcg: float,
    ) -> None:
        self._db = str(learning_db_path)
        self._profile_id = profile_id
        self._baseline = float(baseline_ndcg)
        self._observations: list[float] = []

    # ------------------------------------------------------------------
    # Observation ingestion
    # ------------------------------------------------------------------

    def record_post_promotion(
        self, *, query_id: str, ndcg_at_10: float,
    ) -> None:
        """Record one post-promotion NDCG@10 sample (at most WATCH_WINDOW)."""
        if len(self._observations) >= self.WATCH_WINDOW:
            return
        self._observations.append(float(ndcg_at_10))

    def should_rollback(self) -> bool:
        """Return True iff ≥ WATCH_WINDOW samples and regression detected.

        Regression is detected by whichever of these is true:
          * **Ratio path** (baseline ≥ ``_BASELINE_RATIO_FLOOR``, i.e. 0.05):
            ``(baseline - current) / baseline ≥ REGRESSION_THRESHOLD``.
            Existing v3.4.21 pre-fix semantics preserved at normal
            baselines.
          * **Absolute path** (baseline below the ratio floor — includes
            zero and negative baselines which can happen on sparse data):
            ``(baseline - current) ≥ REGRESSION_THRESHOLD`` in absolute
            units. Stage 8 F4.B H-04 fix — a zero baseline is a valid
            observation, not "no baseline".

        Invariants:
          * Watch window minimum is always enforced — we will NOT fire
            before ``WATCH_WINDOW`` samples land.
          * ``REGRESSION_THRESHOLD`` is the same 0.02 for both paths, so
            the fix is not stricter for typical baselines.
        """
        if len(self._observations) < self.WATCH_WINDOW:
            return False
        current = sum(self._observations) / len(self._observations)
        drop_abs = self._baseline - current
        if self._baseline >= _BASELINE_RATIO_FLOOR:
            # Ratio path — existing semantics.
            drop_ratio = drop_abs / self._baseline
            return drop_ratio >= self.REGRESSION_THRESHOLD
        # Absolute path — works for zero, negative, or tiny positive
        # baselines. Previously this branch returned False unconditionally
        # (silent disarm). Now we fall back to the absolute drop.
        return drop_abs >= self.REGRESSION_THRESHOLD

    # ------------------------------------------------------------------
    # Lineage flip
    # ------------------------------------------------------------------

    def execute_rollback(self, reason: str) -> bool:
        """Flip lineage atomically — return True on success.

        Transaction shape (all under one BEGIN IMMEDIATE):
          1. Confirm an ``is_previous=1`` row exists for profile.
             If missing → abort, set ``safe_mode`` on active, return False.
          2. Current active row: set ``is_active=0, is_rollback=1,
             rollback_reason=?``.
          3. Previous row: set ``is_active=1, is_previous=0``.
          4. Patch ``metadata_json`` on the new active with
             ``retrain_disabled_until`` (+24h) and
             ``last_rollback_at``, counter reset.
        """
        with sqlite3.connect(self._db, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("BEGIN IMMEDIATE")
                prev = conn.execute(
                    "SELECT id FROM learning_model_state "
                    "WHERE profile_id = ? AND is_previous = 1 LIMIT 1",
                    (self._profile_id,),
                ).fetchone()
                if prev is None:
                    conn.rollback()
                    self._set_safe_mode(conn)
                    logger.error(
                        "rollback: missing is_previous row for profile=%s "
                        "reason=%s — entering safe_mode",
                        self._profile_id, reason,
                    )
                    return False

                # Step 2 — demote current active (unset is_active FIRST so
                # the partial unique index on is_active=1 never has two rows).
                conn.execute(
                    "UPDATE learning_model_state "
                    "SET is_active = 0, is_rollback = 1, "
                    "    rollback_reason = ? "
                    "WHERE profile_id = ? AND is_active = 1",
                    (reason, self._profile_id),
                )

                # Step 3 — promote previous to active.
                conn.execute(
                    "UPDATE learning_model_state "
                    "SET is_active = 1, is_previous = 0 "
                    "WHERE id = ?",
                    (prev["id"],),
                )

                # Step 4 — patch metadata on the new active.
                new_meta_row = conn.execute(
                    "SELECT metadata_json FROM learning_model_state "
                    "WHERE id = ?",
                    (prev["id"],),
                ).fetchone()
                try:
                    meta = json.loads(new_meta_row["metadata_json"] or "{}")
                except (TypeError, ValueError):
                    meta = {}
                meta.update({
                    "retrain_disabled_until": _iso_in_hours(
                        self.RETRAIN_DISABLED_HOURS,
                    ),
                    "last_rollback_at": _iso_now(),
                    "new_outcomes_since_last_retrain": 0,
                })
                conn.execute(
                    "UPDATE learning_model_state "
                    "SET metadata_json = ? WHERE id = ?",
                    (json.dumps(meta), prev["id"]),
                )
                conn.commit()
            except sqlite3.Error as exc:
                conn.rollback()
                logger.error(
                    "rollback: sqlite error profile=%s reason=%s: %s",
                    self._profile_id, reason, exc,
                )
                return False

        logger.warning(
            "AUTO-ROLLBACK profile=%s reason=%s observations=%d "
            "baseline_ndcg=%.4f current_ndcg=%.4f",
            self._profile_id, reason, len(self._observations),
            self._baseline,
            (sum(self._observations) / len(self._observations))
            if self._observations else 0.0,
        )
        return True

    # ------------------------------------------------------------------
    # Safe-mode helper (is_previous missing)
    # ------------------------------------------------------------------

    def _set_safe_mode(self, conn: sqlite3.Connection) -> None:
        try:
            row = conn.execute(
                "SELECT metadata_json FROM learning_model_state "
                "WHERE profile_id = ? AND is_active = 1",
                (self._profile_id,),
            ).fetchone()
            meta: dict
            if row is None:
                meta = {"safe_mode": 1}
            else:
                try:
                    meta = json.loads(row["metadata_json"] or "{}")
                except (TypeError, ValueError):
                    meta = {}
                meta["safe_mode"] = 1
            conn.execute(
                "UPDATE learning_model_state SET metadata_json = ? "
                "WHERE profile_id = ? AND is_active = 1",
                (json.dumps(meta), self._profile_id),
            )
            conn.commit()
        except sqlite3.Error as exc:  # pragma: no cover — defensive
            logger.debug("safe_mode set failed: %s", exc)


__all__ = ("ModelRollback",)
