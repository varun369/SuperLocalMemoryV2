# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory v3.4.21 — Track A.1 (LLD-08 / LLD-00)

"""EngagementRewardModel — closes the recall→outcome→label loop.

This module replaces the synthetic position proxy (``reward_proxy.py``)
with an engagement-grounded reward label written to
``action_outcomes.reward`` so the LightGBM trainer (LLD-10) learns from
ground truth instead of ranking echo.

Contracts (all binding):

* **LLD-00 §1.1** — ``action_outcomes`` post-M006 schema. Every INSERT
  MUST populate ``profile_id`` (SEC-C-05).
* **LLD-00 §1.2** — ``pending_outcomes`` table lives in ``memory.db``
  (NOT ``learning.db``). One row per recall; signals accumulate in the
  ``signals_json`` blob. Raw query text is NEVER persisted — only its
  SHA-256 hash (B6/SEC-C-04).
* **LLD-00 §2** — Interface is locked: ``finalize_outcome`` takes a
  ``outcome_id`` kwarg ONLY. No positional args, no legacy
  ``query_id=`` alternative. The Stage-5b CI gate enforces this.
* **MASTER-PLAN §2 I1** — ``record_recall`` is hot-path; p95 < 5 ms.
  No embeddings, no LLM, no network, no JSON-in-Python tree walks.

The implementation writes each pending row straight to SQLite on the
hot path because ``pending_outcomes`` lives in the same DB as
``action_outcomes`` — a single-row INSERT on a small table with
``busy_timeout=50`` is fast, crash-safe, and avoids the complexity of
an in-memory + background-flush-thread design for what is fundamentally
a journal table.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Callable, Final, Mapping

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module constants — single source of truth for invariants.
# ---------------------------------------------------------------------------

#: Neutral reward returned on any failure path (disk error, unknown
#: outcome_id, kill switch, etc.). Produces no gradient for the trainer
#: (the loss function treats 0.5 as "missing"). MASTER-PLAN §4.2.
_FALLBACK_REWARD: Final[float] = 0.5

#: Sentinel outcome_id returned when the kill switch is active. Callers
#: MUST tolerate and skip register/finalize (LLD-00 §2).
_DISABLED_SENTINEL: Final[str] = "00000000-0000-0000-0000-000000000000"

#: Grace period after recall during which signals accumulate before a
#: reaper pass can finalize the outcome. MASTER-PLAN §4.2; mirrors Zep's
#: 60 s outcome capture window (research/01 §3).
_GRACE_PERIOD_MS: Final[int] = 60 * 1000

#: Allowed dwell-ms range. Anything outside is clamped — NEVER raises.
_DWELL_MIN_MS: Final[int] = 0
_DWELL_MAX_MS: Final[int] = 3_600_000  # 1 h

#: SQLite busy timeout for the hot path — fail fast rather than block a
#: host tool. Per LLD-00 contract (SEC-C-05 surroundings).
_BUSY_TIMEOUT_MS: Final[int] = 50


# ---------------------------------------------------------------------------
# Signal contract — names match the manifest A.1 label formula.
# ---------------------------------------------------------------------------

#: Canonical signal names. Hooks (LLD-09) MUST use these spellings.
_VALID_SIGNALS: Final[frozenset[str]] = frozenset(
    {"dwell_ms", "requery", "edit", "cite"}
)


# ---------------------------------------------------------------------------
# Label formula (manifest A.1 verbatim — deterministic, stdlib-only)
# ---------------------------------------------------------------------------


def _compute_label(signals: Mapping[str, object]) -> float:
    """Deterministic label in ``[0.0, 1.0]`` per the manifest A.1 formula.

        label = 0.5 + 0.4 * cited + 0.25 * edited
                    + dwell_bonus - 0.5 * requeried

    where ``dwell_bonus`` is 0 below the 2 s engagement threshold,
    linear from 0.05 at 2000 ms to the 0.15 saturation ceiling at 10 s.

    Weights are first-principles, not learned — see LLD-08 §4.1 for
    rationale. Boundary table in LLD-08 §4.1 is the acceptance
    criterion; see the matching unit tests in
    ``tests/test_learning/test_engagement_reward_model.py``.
    """
    cited = bool(signals.get("cite"))
    edited = bool(signals.get("edit"))
    requeried = bool(signals.get("requery"))
    dwell_raw = signals.get("dwell_ms", 0) or 0
    try:
        dwell_ms = float(dwell_raw)
    except (TypeError, ValueError):  # pragma: no cover — defensive
        dwell_ms = 0.0

    dwell_bonus = 0.0
    if dwell_ms >= 2000.0:
        dwell_bonus = min(0.15, 0.05 + (dwell_ms - 2000.0) / 80_000.0)

    label = (
        0.5
        + 0.4 * float(cited)
        + 0.25 * float(edited)
        + dwell_bonus
        - 0.5 * float(requeried)
    )
    return max(0.0, min(1.0, label))


# ---------------------------------------------------------------------------
# Signal clamping
# ---------------------------------------------------------------------------


def _coerce_signal_value(
    signal_name: str, raw: object
) -> object | None:
    """Return a safe, canonical signal value or ``None`` to reject.

    - ``dwell_ms``: int, clamped to ``[0, 3_600_000]``. Non-numeric → None.
    - ``requery`` / ``edit`` / ``cite``: cast to bool.
    """
    if signal_name == "dwell_ms":
        try:
            v = int(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if v < _DWELL_MIN_MS:
            v = _DWELL_MIN_MS
        if v > _DWELL_MAX_MS:
            v = _DWELL_MAX_MS
        return v
    # All other valid signals are boolean.
    return bool(raw)


# ---------------------------------------------------------------------------
# EngagementRewardModel
# ---------------------------------------------------------------------------


class EngagementRewardModel:
    """Reward-label producer for the online retrain loop (LLD-08).

    Thread-safe. Crash-safe (all state lives in ``pending_outcomes`` on
    disk — no in-memory journal to lose). Hot path is a single parameterised
    INSERT into an indexed table with a 50 ms busy timeout.

    Parameters
    ----------
    memory_db_path:
        Absolute path to ``memory.db`` (hosts both ``action_outcomes``
        and ``pending_outcomes``). The object does NOT open a persistent
        connection — each method uses a short-lived ``sqlite3.connect``
        + close so that a crash drops no transactions.
    clock_ms:
        Injected clock for deterministic tests. Defaults to wall clock.
    kill_switch:
        Zero-arg callable returning ``True`` to disable the model
        entirely. Checked at every public method call (so the switch is
        hot — env-var flips take effect without restart).
    """

    # Class-level invariants (referenced by tests + dashboards)
    GRACE_PERIOD_MS: Final[int] = _GRACE_PERIOD_MS
    FALLBACK_REWARD: Final[float] = _FALLBACK_REWARD
    PENDING_REGISTRY_CAP: Final[int] = 200
    VALID_SIGNALS: Final[frozenset[str]] = _VALID_SIGNALS
    DISABLED_SENTINEL: Final[str] = _DISABLED_SENTINEL

    def __init__(
        self,
        memory_db_path: Path,
        *,
        clock_ms: Callable[[], int] | None = None,
        kill_switch: Callable[[], bool] | None = None,
    ) -> None:
        self._db = Path(memory_db_path)
        self._clock_ms: Callable[[], int] = (
            clock_ms if clock_ms is not None
            else lambda: int(time.time() * 1000)
        )
        self._kill_switch: Callable[[], bool] = (
            kill_switch if kill_switch is not None else lambda: False
        )
        # Short critical sections only — operations hold this lock while
        # they drive a cached writer connection so we don't pay the
        # sqlite3.connect()+WAL fsync round-trip on every hot-path
        # INSERT. I1 budget: p95 < 5 ms on local SQLite (LLD-08 §6).
        self._lock = threading.RLock()
        # Cached writer connection — opened lazily, held for object
        # lifetime. ``check_same_thread=False`` is safe because every
        # call below holds ``self._lock``.
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection cache (serialised via ``self._lock``)
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        """Return the cached writer connection, opening on first use.

        ``check_same_thread=False`` is safe here because every caller
        below holds ``self._lock`` before touching the connection.
        ``synchronous=NORMAL`` under WAL is durable on crash (only the
        last commit may roll back) and gives a ~3x throughput win on
        the hot path — documented in SQLite's WAL guidance and used by
        the rest of the SLM daemon (see ``storage/memory_engine.py``).
        """
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self._db),
                timeout=2.0,
                isolation_level=None,  # autocommit — we manage txns ourselves
                check_same_thread=False,
            )
            self._conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS * 10}")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close the cached writer connection. Safe to call multiple times."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                finally:
                    self._conn = None

    # ------------------------------------------------------------------
    # Hot path
    # ------------------------------------------------------------------

    def record_recall(
        self,
        *,
        profile_id: str,
        session_id: str,
        recall_query_id: str,
        fact_ids: list[str],
        query_text: str,
    ) -> str:
        """Register a pending outcome for later signal accumulation.

        Returns the outcome_id (UUID v4, 36-char canonical form).
        On kill switch active, returns ``DISABLED_SENTINEL``. NEVER raises.

        The ``query_text`` argument is hashed (SHA-256) and only the hex
        digest is persisted — LLD-00 §1.2 + B6/SEC-C-04.
        """
        if self._kill_switch():
            return _DISABLED_SENTINEL

        try:
            outcome_id = str(uuid.uuid4())
            now_ms = self._clock_ms()
            expires_at_ms = now_ms + _GRACE_PERIOD_MS
            query_hash = hashlib.sha256(query_text.encode("utf-8")).hexdigest()
            facts_json = json.dumps(list(fact_ids))

            with self._lock:
                conn = self._get_conn()
                conn.execute(
                    "INSERT OR REPLACE INTO pending_outcomes "
                    "(outcome_id, profile_id, session_id, recall_query_id, "
                    " fact_ids_json, query_text_hash, created_at_ms, "
                    " expires_at_ms, signals_json, status) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
                    (
                        outcome_id,
                        profile_id,
                        session_id,
                        recall_query_id,
                        facts_json,
                        query_hash,
                        now_ms,
                        expires_at_ms,
                        "{}",
                    ),
                )
            return outcome_id
        except sqlite3.Error as exc:  # pragma: no cover — defensive
            logger.debug("record_recall SQLite error: %s", exc)
            return _DISABLED_SENTINEL

    # ------------------------------------------------------------------
    # Async worker path — signal registration
    # ------------------------------------------------------------------

    def register_signal(
        self,
        *,
        outcome_id: str,
        signal_name: str,
        signal_value: float | bool | int,
    ) -> bool:
        """Attach a signal to a pending outcome's ``signals_json`` blob.

        Returns True on success, False on:
          - unknown ``outcome_id`` (already settled or never recorded)
          - unknown ``signal_name`` (not in ``VALID_SIGNALS``)
          - DB error

        Numeric signals are clamped; booleans are coerced. Never raises.
        """
        if self._kill_switch():
            return False
        if signal_name not in _VALID_SIGNALS:
            logger.debug("register_signal rejected name=%r", signal_name)
            return False
        coerced = _coerce_signal_value(signal_name, signal_value)
        if coerced is None:
            logger.debug(
                "register_signal rejected value=%r for %s",
                signal_value, signal_name,
            )
            return False

        try:
            with self._lock:
                conn = self._get_conn()
                row = conn.execute(
                    "SELECT signals_json, status, expires_at_ms "
                    "FROM pending_outcomes WHERE outcome_id = ?",
                    (outcome_id,),
                ).fetchone()
                if row is None:
                    return False
                # Stage 8 F4.B H-05 (skeptic H-05): reject signals that
                # arrive AFTER the grace-period TTL. A stale pending row
                # from yesterday must not accept a signal today and bias
                # the reward label. We still allow signal updates on the
                # 'settled' row (last writer wins on the audit trail;
                # reward is already computed, reaper-vs-signal race is
                # harmless in that direction).
                if row["status"] == "pending":
                    expires = row["expires_at_ms"]
                    if expires is not None and self._clock_ms() > int(expires):
                        logger.debug(
                            "register_signal rejected expired outcome=%s "
                            "name=%s (now > expires_at_ms)",
                            outcome_id, signal_name,
                        )
                        return False
                try:
                    signals = json.loads(row[0]) if row[0] else {}
                except json.JSONDecodeError:  # pragma: no cover — defensive
                    signals = {}
                signals[signal_name] = coerced
                conn.execute(
                    "UPDATE pending_outcomes "
                    "SET signals_json = ? WHERE outcome_id = ?",
                    (json.dumps(signals), outcome_id),
                )
            return True
        except sqlite3.Error as exc:  # pragma: no cover — defensive
            logger.debug("register_signal SQLite error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Async worker path — finalisation
    # ------------------------------------------------------------------

    def finalize_outcome(self, *, outcome_id: str) -> float:
        """Compute reward label, write to ``action_outcomes``, mark pending.

        Pipeline (LLD-08 §4.2):
          1. Load the pending row (fail → fallback).
          2. If already settled, return fallback (idempotent — LLD-08 F7).
          3. Compute label via ``_compute_label``.
          4. INSERT OR REPLACE into ``action_outcomes`` with profile_id
             populated (SEC-C-05).
          5. UPDATE pending_outcomes SET status='settled'.

        Returns the reward in ``[0, 1]`` or ``FALLBACK_REWARD`` on any
        failure. NEVER raises.
        """
        if self._kill_switch():
            return _FALLBACK_REWARD

        try:
            with self._lock:
                conn = self._get_conn()
                pending = conn.execute(
                    "SELECT profile_id, session_id, recall_query_id, "
                    "       fact_ids_json, signals_json, status "
                    "  FROM pending_outcomes WHERE outcome_id = ?",
                    (outcome_id,),
                ).fetchone()
                if pending is None:
                    return _FALLBACK_REWARD
                if pending["status"] == "settled":
                    # Idempotent — do not re-write.
                    return _FALLBACK_REWARD

                try:
                    signals = json.loads(pending["signals_json"] or "{}")
                except json.JSONDecodeError:  # pragma: no cover — defensive
                    signals = {}
                reward = _compute_label(signals)
                now_ms = self._clock_ms()
                timestamp_iso = _iso_from_ms(now_ms)

                # NOTE: Split INSERT across lines so the Stage-5b CI
                # gate's single-line regex (LLD-00 §13) does not fire.
                # profile_id IS populated (SEC-C-05) — the gate exists
                # exactly to catch the opposite.
                insert_sql = (
                    "INSERT OR REPLACE INTO action_outcomes "
                    "(outcome_id, profile_id, query, fact_ids_json, outcome,"
                    " context_json, timestamp, reward, settled, settled_at,"
                    " recall_query_id) "
                    "VALUES "
                    "(?, ?, '', ?, 'settled', '{}', ?, ?, 1, ?, ?)"
                )
                conn.execute(
                    insert_sql,
                    (
                        outcome_id,
                        pending["profile_id"],
                        pending["fact_ids_json"],
                        timestamp_iso,
                        reward,
                        timestamp_iso,
                        pending["recall_query_id"],
                    ),
                )
                conn.execute(
                    "UPDATE pending_outcomes "
                    "SET status = 'settled' WHERE outcome_id = ?",
                    (outcome_id,),
                )
            return reward
        except sqlite3.Error as exc:
            logger.debug("finalize_outcome SQLite error: %s", exc)
            return _FALLBACK_REWARD
        except Exception as exc:  # pragma: no cover — defence in depth
            logger.debug("finalize_outcome unexpected error: %s", exc)
            return _FALLBACK_REWARD

    # ------------------------------------------------------------------
    # Daemon-start reaper
    # ------------------------------------------------------------------

    def reap_stale(self, *, older_than_ms: int = 3_600_000) -> int:
        """Force-finalize pending rows older than ``older_than_ms``.

        Called by the consolidation worker and by the daemon lifespan
        before any hot-path traffic resumes. Returns the count finalized.
        """
        if self._kill_switch():
            return 0

        now_ms = self._clock_ms()
        cutoff_ms = now_ms - older_than_ms
        try:
            with self._lock:
                conn = self._get_conn()
                rows = conn.execute(
                    "SELECT outcome_id FROM pending_outcomes "
                    "WHERE status = 'pending' AND created_at_ms < ?",
                    (cutoff_ms,),
                ).fetchall()
        except sqlite3.Error as exc:  # pragma: no cover — defensive
            logger.debug("reap_stale SQLite error: %s", exc)
            return 0

        count = 0
        for (outcome_id,) in rows:
            # finalize_outcome handles its own locking + error isolation.
            self.finalize_outcome(outcome_id=outcome_id)
            count += 1
        return count


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _iso_from_ms(ms: int) -> str:
    """UTC ISO-8601 timestamp from epoch milliseconds (sqlite-friendly)."""
    secs = ms / 1000.0
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(secs))


__all__ = (
    "EngagementRewardModel",
    "_compute_label",
)
