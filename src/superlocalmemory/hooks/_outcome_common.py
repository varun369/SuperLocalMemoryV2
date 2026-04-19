# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory v3.4.21 — Track A.2 (LLD-09)

"""Shared helpers for the three outcome-population hooks (LLD-09).

All helpers are stdlib-only, never raise, and bound their work by budget.
Used by:
  - ``post_tool_outcome_hook`` (hot path, <10 ms typical, <20 ms hard)
  - ``user_prompt_rehash_hook`` (hot path, <10 ms typical, <20 ms hard)
  - ``stop_outcome_hook``       (session-end, <500 ms typical, <1 s hard)

Contract refs:
  - LLD-00 §1.2 — pending_outcomes lives in memory.db, NOT cache.db.
  - LLD-00 §3   — HMAC marker validator for fact_id matching.
  - LLD-00 §4   — safe_resolve_identifier for any path built from session_id.
  - MASTER-PLAN §2 I1 — hot-path p95 budget.

This module is the single source of truth for:
  1. Locating memory.db (respecting SLM_HOME override used in tests).
  2. Opening a short-lived sqlite3 connection with busy_timeout=50.
  3. Reading/writing session_state/<session_id>.json with path-escape
     defence.
  4. Appending one NDJSON line to logs/hook-perf.log.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Budget constants
# ---------------------------------------------------------------------------

#: Hot-path SQLite busy timeout (ms). Fail fast rather than block a host tool.
BUSY_TIMEOUT_MS: int = 50

#: Cap on tool_response bytes scanned — bounds substring work to O(100 KB).
SCAN_BYTES_CAP: int = 100_000

#: Re-query detection window (ms). Outside → no signal.
REQUERY_WINDOW_MS: int = 60_000


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def slm_home() -> Path:
    """Return ``~/.superlocalmemory`` honouring ``SLM_HOME`` override.

    ``SLM_HOME`` exists solely so unit tests can isolate filesystem state.
    Production code sets nothing and falls back to the home-directory path.
    """
    override = os.environ.get("SLM_HOME", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".superlocalmemory"


def memory_db_path() -> Path:
    """Canonical memory.db path (hosts pending_outcomes + action_outcomes)."""
    return slm_home() / "memory.db"


def session_state_dir() -> Path:
    """Per-session JSON state directory (created on demand)."""
    d = slm_home() / "session_state"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:  # pragma: no cover — disk full / ro fs
        pass
    return d


def perf_log_path() -> Path:
    d = slm_home() / "logs"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:  # pragma: no cover
        pass
    return d / "hook-perf.log"


# ---------------------------------------------------------------------------
# SQLite — short-lived connection with busy_timeout
# ---------------------------------------------------------------------------


def open_memory_db() -> sqlite3.Connection:
    """Open memory.db with the hot-path busy timeout + autocommit.

    Caller is responsible for ``close()``. We intentionally do NOT enable
    WAL here — the daemon already set it on first boot; hooks are writers
    to a WAL DB and must not flip the journal mode under a live daemon.
    """
    conn = sqlite3.connect(
        str(memory_db_path()),
        timeout=2.0,
        isolation_level=None,  # autocommit — each statement is its own txn
    )
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Session state — path-escape-hardened read/write
# ---------------------------------------------------------------------------


def session_state_file(session_id: str) -> Path | None:
    """Resolve ``<session_state_dir>/<session_id>.json`` via the LLD-00
    §4 identifier validator. Returns ``None`` if ``session_id`` is unsafe.
    """
    try:
        from superlocalmemory.core.security_primitives import (
            safe_resolve_identifier,
        )
    except Exception:  # pragma: no cover — SLM import broken
        return None
    base = session_state_dir()
    try:
        path = safe_resolve_identifier(base, session_id)
    except ValueError:
        return None
    return path.with_suffix(".json") if path.suffix != ".json" else path


def load_session_state(session_id: str) -> dict:
    """Read session state JSON; ``{}`` on any failure."""
    p = session_state_file(session_id)
    if p is None or not p.exists():
        return {}
    try:
        raw = p.read_text()
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return {}
    return {}


def save_session_state(session_id: str, state: dict) -> None:
    """Persist session state JSON (best-effort; never raises)."""
    p = session_state_file(session_id)
    if p is None:
        return
    try:
        p.write_text(json.dumps(state))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tool-response size guard
# ---------------------------------------------------------------------------


def summarize_response(raw: object, cap: int = SCAN_BYTES_CAP) -> str:
    """Coerce ``raw`` to a string capped at ``cap`` bytes (UTF-8 safe).

    Claude Code passes tool_response as a string OR a structured blob; we
    str()-ify as a defensive fallback. The cap is applied before any
    regex / substring scan so the hot-path cost is O(cap) regardless of
    input size (failure mode #4 in LLD-09 §7).
    """
    if raw is None:
        return ""
    if not isinstance(raw, str):
        try:
            raw = json.dumps(raw, default=str)
        except Exception:
            try:
                raw = str(raw)
            except Exception:
                return ""
    if len(raw) <= cap:
        return raw
    return raw[:cap]


# ---------------------------------------------------------------------------
# Perf log (NDJSON append, best-effort)
# ---------------------------------------------------------------------------


def log_perf(hook_name: str, duration_ms: float, outcome: str) -> None:
    """Append one NDJSON line to ``logs/hook-perf.log``.

    Best-effort: disk full / unwritable dir → silently skip. One short
    ``open(..., 'a')`` per invocation. On POSIX, a single ``write()`` of
    ≤ PIPE_BUF (4 KB) is atomic — our lines are ≪100 bytes so no lock
    is required.
    """
    try:
        rec = {
            "ts": int(time.time() * 1000),
            "hook": hook_name,
            "duration_ms": round(duration_ms, 3),
            "outcome": outcome,
        }
        line = json.dumps(rec, separators=(",", ":")) + "\n"
        with open(perf_log_path(), "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:  # pragma: no cover — disk full / perms
        pass


# ---------------------------------------------------------------------------
# Entry-point helpers — shared exit-0 crash guard
# ---------------------------------------------------------------------------


def emit_empty_json() -> None:
    """Write ``{}`` to stdout. Hooks are passive observers (LLD-09 §3.4)."""
    try:
        sys.stdout.write("{}")
    except Exception:  # pragma: no cover — stdout closed
        pass


def read_stdin_json() -> dict | None:
    """Read a JSON dict from stdin. Returns None on any failure."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def now_ms() -> int:
    return int(time.time() * 1000)
