# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory v3.4.21 — Track A.2 (LLD-09 / LLD-00)

"""PostToolUse hook — detect fact usage + write engagement signal.

Flow (hot path, <10 ms typical, <20 ms hard):
  1. Read Claude Code JSON from stdin.
  2. Resolve session_id via ``safe_resolve_identifier`` (LLD-00 §4).
  3. Cap tool_response to 100 KB (bounded scan, LLD-09 §7 failure-mode #4).
  4. Extract HMAC markers (``slm:fact:<id>:<hmac8>``) — validate each
     (LLD-00 §3). Bare substring scans are **banned** by the Stage-5b
     CI gate.
  5. For each validated fact_id, find a pending_outcomes row where
     ``session_id`` matches AND ``fact_ids_json`` includes the fact_id
     AND ``status='pending'`` — call ``register_signal(outcome_id,
     signal_name, True)``. ``signal_name`` is ``'edit'`` for
     mutating tools (Edit/Write/NotebookEdit), else ``'dwell_ms'`` with
     a nominal 3000 ms value.
  6. Always emit ``{}`` on stdout and return 0. NEVER raise.

Crash-safety (LLD-09 §6):
  - Outer try/except around every code path. stderr breadcrumb (no
    stack trace, no payload echo). Always exit 0.
  - SQLite ``busy_timeout=50`` → fast-fail on DB contention.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from superlocalmemory.hooks._outcome_common import (
    emit_empty_json,
    log_perf,
    memory_db_path as _memory_db_path_fn,
    now_ms,
    open_memory_db,
    read_stdin_json,
    session_state_file,
    summarize_response,
)


_HOOK_NAME = "post_tool_outcome"

# Monkey-patchable indirection for tests.
def _memory_db_path() -> Path:
    return _memory_db_path_fn()


# Tools that imply an "edit" signal (the agent acted on the fact).
_EDIT_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

# Nominal dwell value for non-edit tool uses that hit a marker.
# The label formula clamps 2s..10s → 0.05..0.15 reward bonus.
_DEFAULT_DWELL_MS = 3000

# Marker regex — mirrors recall_pipeline._emit_marker but scoped locally
# so this module has no hot-path import of the full recall pipeline.
# ``fact_id`` allows anything that is not ':' or whitespace so the
# validator ultimately runs via recall_pipeline._validate_marker.
_MARKER_RE = re.compile(r"slm:fact:([^:\s]+):([0-9a-f]{8})")


def _validate(marker: str) -> str | None:
    """Delegate to the canonical validator (LLD-00 §3)."""
    try:
        from superlocalmemory.core.recall_pipeline import _validate_marker
    except Exception:
        return None
    try:
        return _validate_marker(marker)
    except Exception:
        return None


def _inner_main() -> str:
    """Return an ``outcome`` string (for perf log); never raises."""
    payload = read_stdin_json()
    if payload is None:
        return "invalid_payload"

    session_id = payload.get("session_id")
    tool_name = payload.get("tool_name") or ""
    if not isinstance(session_id, str) or not session_id:
        return "no_session"

    # Path-escape defence (SEC-C-02) — any unsafe session_id means we
    # must not touch the filesystem for this invocation. We still want
    # to safely query the DB (it uses parameterised SQL), so we only
    # gate the filesystem branch.
    _ = session_state_file(session_id)  # None → caller skips FS writes
    # Note: for post_tool_outcome we do NOT need to write session state.
    # Rehash / stop hooks are the writers/readers.

    # Response scan — capped BEFORE regex (bound O(cap)).
    response_text = summarize_response(payload.get("tool_response"))
    if not response_text:
        return "no_response"

    # Fast pre-check: if the HMAC prefix is absent, no marker can exist.
    if "slm:fact:" not in response_text:
        return "no_marker"

    hits: list[str] = []
    for m in _MARKER_RE.finditer(response_text):
        marker = m.group(0)
        fact_id = _validate(marker)
        if fact_id:
            hits.append(fact_id)
    if not hits:
        return "no_validated_marker"

    # Persist signals via the canonical reward model — the DB write is
    # behind ``register_signal`` which enforces the schema contract and
    # the pending→settled state machine.
    try:
        from superlocalmemory.learning.reward import EngagementRewardModel
    except Exception:
        return "import_fail"

    signal_name = "edit" if tool_name in _EDIT_TOOLS else "dwell_ms"
    signal_value: object = True if signal_name == "edit" else _DEFAULT_DWELL_MS

    # Locate pending outcome(s) for this session whose fact_ids_json
    # contains ANY of the validated fact_ids. We scan pending rows for
    # the session (typically very few) and JSON-decode in Python — small,
    # bounded, avoids SQL JSON1 feature dependence.
    try:
        with open_memory_db() as conn:
            rows = conn.execute(
                "SELECT outcome_id, fact_ids_json FROM pending_outcomes "
                "WHERE session_id = ? AND status = 'pending' "
                "ORDER BY created_at_ms DESC LIMIT 20",
                (session_id,),
            ).fetchall()
    except Exception:
        return "db_locked"

    if not rows:
        return "no_pending"

    import json as _json
    target_outcome_ids: list[str] = []
    hit_set = set(hits)
    for r in rows:
        try:
            facts = _json.loads(r["fact_ids_json"])
        except Exception:
            continue
        if not isinstance(facts, list):
            continue
        if hit_set.intersection(facts):
            target_outcome_ids.append(r["outcome_id"])

    if not target_outcome_ids:
        return "no_match"

    try:
        model = EngagementRewardModel(_memory_db_path())
    except Exception:
        return "model_init_fail"

    try:
        wrote = 0
        for oid in target_outcome_ids:
            ok = model.register_signal(
                outcome_id=oid,
                signal_name=signal_name,
                signal_value=signal_value,
            )
            if ok:
                wrote += 1
        return f"signal_{signal_name}_x{wrote}"
    finally:
        try:
            model.close()
        except Exception:
            pass


def main() -> int:
    """Hook entry point — stdin JSON → signals_json update. Always exits 0."""
    t0 = time.perf_counter()
    outcome = "exception"
    try:
        outcome = _inner_main()
    except Exception as exc:  # pragma: no cover — defensive
        try:
            sys.stderr.write(
                f"slm-hook {_HOOK_NAME}: {type(exc).__name__}\n"
            )
        except Exception:
            pass
    finally:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        emit_empty_json()
        try:
            log_perf(_HOOK_NAME, duration_ms, outcome)
        except Exception:
            pass
    return 0


if __name__ == "__main__":  # pragma: no cover — CLI entry only
    sys.exit(main())
