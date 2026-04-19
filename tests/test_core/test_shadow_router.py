# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory v3.4.21 — Track A.3 / Stage 8 SB-1

"""Tests for ``core/shadow_router.py`` — daemon-resident A/B router.

The router is the single in-process seam that wires LLD-10 Track A.3
pieces together at recall time:

  - ``ShadowTest`` (pre-promotion A/B accumulator).
  - ``ModelRollback`` (post-promotion 200-observation watch window).

Contract references:
  - LLD-00 §8    — two-phase shadow + auto-rollback.
  - LLD-10 §4.1  — deterministic A/B routing, tamper-proof via install_token.
  - LLD-10 §5    — atomic BEGIN IMMEDIATE promotion + rollback.
  - Stage 8 SB-1 — ship-blocker: router wires previously-dead code.

Stdlib-only. Exercises the pure state-machine; DB interaction is
monkey-patched where promotion / rollback are triggered so tests run
in milliseconds without lightgbm.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Shared schema — minimal subset needed for shadow_router promotion path
# ---------------------------------------------------------------------------

_LEARNING_SCHEMA = """
CREATE TABLE learning_model_state (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id        TEXT NOT NULL,
    model_version     TEXT NOT NULL DEFAULT '3.4.21',
    state_bytes       BLOB NOT NULL,
    bytes_sha256      TEXT NOT NULL DEFAULT '',
    trained_on_count  INTEGER NOT NULL DEFAULT 0,
    feature_names     TEXT NOT NULL DEFAULT '[]',
    metrics_json      TEXT NOT NULL DEFAULT '{}',
    is_active         INTEGER NOT NULL DEFAULT 0,
    trained_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    is_previous       INTEGER DEFAULT 0,
    is_rollback       INTEGER DEFAULT 0,
    is_candidate      INTEGER DEFAULT 0,
    shadow_results_json TEXT,
    promoted_at       TEXT,
    rollback_reason   TEXT,
    metadata_json     TEXT
);
CREATE UNIQUE INDEX idx_model_active_one
    ON learning_model_state(profile_id) WHERE is_active = 1;
CREATE UNIQUE INDEX idx_model_candidate_one
    ON learning_model_state(profile_id) WHERE is_candidate = 1;
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture()
def learning_db(tmp_path: Path) -> Path:
    db = tmp_path / "learning.db"
    with sqlite3.connect(db) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_LEARNING_SCHEMA)
    return db


@pytest.fixture()
def memory_db(tmp_path: Path) -> Path:
    db = tmp_path / "memory.db"
    # shadow_router does not DDL memory.db — a bare file is enough.
    db.write_bytes(b"")
    return db


@pytest.fixture(autouse=True)
def _reset_router_singleton():
    """Ensure each test starts with a fresh router singleton."""
    from superlocalmemory.core import shadow_router
    shadow_router.reset_for_testing()
    yield
    shadow_router.reset_for_testing()


@pytest.fixture(autouse=True)
def _stable_install_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Force a deterministic install token so route_query is reproducible."""
    from superlocalmemory.core import security_primitives as sp
    fake_path = tmp_path / ".install_token"
    fake_path.write_text("deadbeef" * 8, encoding="utf-8")
    monkeypatch.setattr(sp, "_install_token_path", lambda: fake_path)


# ---------------------------------------------------------------------------
# Route-query determinism + tamper resistance
# ---------------------------------------------------------------------------


def test_shadow_router_route_query_uses_install_token(
    learning_db: Path, memory_db: Path, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """route_query MUST hash install_token + query_id, not query_id alone.

    Closes skeptic H-02 + H-03 — an attacker who controls query_id
    cannot bias the A/B split without also reading the install_token.
    """
    from superlocalmemory.core import shadow_router as sr_mod
    from superlocalmemory.core import security_primitives as sp

    router_a = sr_mod.ShadowRouter(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="p",
    )
    arm_a = router_a.route_query("query-abc")

    # Rotate install token → arm for same query_id may flip.
    new_token_file = tmp_path / ".install_token_rotated"
    new_token_file.write_text("c0ffee" * 16, encoding="utf-8")
    monkeypatch.setattr(sp, "_install_token_path", lambda: new_token_file)

    router_b = sr_mod.ShadowRouter(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="p",
    )
    # Deterministic verification: manual hash matches implementation.
    token_b = new_token_file.read_text().strip()
    expected_h = hashlib.sha256(
        (token_b + "query-abc").encode("utf-8"),
    ).hexdigest()[:8]
    expected_arm = "candidate" if int(expected_h, 16) % 2 == 1 else "baseline"
    assert router_b.route_query("query-abc") == expected_arm
    # And the route_query result uses the token — not query_id alone.
    query_only = hashlib.sha256("query-abc".encode("utf-8")).hexdigest()[:8]
    naive_arm = "candidate" if int(query_only, 16) % 2 == 1 else "baseline"
    # The two SHOULD often disagree; if they happen to agree for this
    # input, use another input to prove token-dependence.
    if router_b.route_query("query-abc") == naive_arm:
        # Find a query_id that distinguishes token vs naive — exists
        # in practice because SHA-256 distributes uniformly.
        for q in (f"q-{i}" for i in range(1000)):
            token_h = hashlib.sha256(
                (token_b + q).encode("utf-8"),
            ).hexdigest()[:8]
            naive_h = hashlib.sha256(q.encode("utf-8")).hexdigest()[:8]
            if (int(token_h, 16) % 2) != (int(naive_h, 16) % 2):
                assert router_b.route_query(q) != (
                    "candidate" if int(naive_h, 16) % 2 == 1 else "baseline"
                )
                return
        pytest.fail("route_query appears to ignore install_token")


def test_shadow_router_route_query_deterministic(
    learning_db: Path, memory_db: Path,
) -> None:
    """Same (install_token, query_id) → same arm, always.

    Deterministic re-routing survives daemon restart (LLD-10 §4.1).
    """
    from superlocalmemory.core.shadow_router import ShadowRouter

    r1 = ShadowRouter(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="p",
    )
    r2 = ShadowRouter(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="p",
    )
    qids = [f"q-{i:04d}" for i in range(32)]
    for qid in qids:
        assert r1.route_query(qid) == r2.route_query(qid)
    # And the returned value is strictly in the expected arm vocabulary.
    assert {r1.route_query(q) for q in qids} <= {"baseline", "candidate"}


# ---------------------------------------------------------------------------
# Promotion on ShadowTest.decide == 'promote'
# ---------------------------------------------------------------------------


def _seed_active_and_candidate(db_path: Path, profile_id: str) -> tuple[int, int]:
    now = _now_iso()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO learning_model_state "
            "(profile_id, state_bytes, bytes_sha256, is_active, "
            " trained_at, updated_at, metadata_json) "
            "VALUES (?, ?, ?, 1, ?, ?, ?)",
            (profile_id, b"active-bytes", "0" * 64, now, now, "{}"),
        )
        active_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO learning_model_state "
            "(profile_id, state_bytes, bytes_sha256, is_active, is_candidate,"
            " trained_at, updated_at, metadata_json) "
            "VALUES (?, ?, ?, 0, 1, ?, ?, ?)",
            (profile_id, b"cand-bytes", "0" * 64, now, now, "{}"),
        )
        cand_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
    return active_id, cand_id


def test_shadow_router_promote_on_decide_promote(
    learning_db: Path, memory_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ShadowTest.decide() == 'promote', router fires
    ``_promote_candidate`` atomically and clears its shadow state.
    """
    from superlocalmemory.core import shadow_router as sr_mod

    _, cand_id = _seed_active_and_candidate(learning_db, "p")

    router = sr_mod.ShadowRouter(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="p",
    )
    # Force the shadow test to return 'promote' after first settled pair.
    called = {"n": 0}

    class _FakeShadowTest:
        def __init__(self, *a, **kw):
            pass
        def record_recall_pair(self, **kw):
            called["n"] += 1
        def decide(self):
            return "promote", {"effect": 0.1}

    monkeypatch.setattr(sr_mod, "ShadowTest", _FakeShadowTest)
    # Re-attach a fresh shadow test that uses the fake class.
    router._shadow = _FakeShadowTest()
    router._candidate_id = cand_id

    router.on_recall_settled(
        query_id="q1", arm="candidate", ndcg_at_10=0.9,
    )

    # Promotion fired — candidate flag cleared on lineage_state row.
    with sqlite3.connect(learning_db) as conn:
        n_cand = conn.execute(
            "SELECT COUNT(*) FROM learning_model_state "
            "WHERE profile_id='p' AND is_candidate=1",
        ).fetchone()[0]
        assert n_cand == 0
        n_active = conn.execute(
            "SELECT COUNT(*) FROM learning_model_state "
            "WHERE profile_id='p' AND is_active=1",
        ).fetchone()[0]
        assert n_active == 1
        promoted = conn.execute(
            "SELECT id FROM learning_model_state "
            "WHERE profile_id='p' AND is_active=1",
        ).fetchone()[0]
        assert promoted == cand_id


def test_shadow_router_rollback_on_200_regression(
    learning_db: Path, memory_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After promotion, 200 post-observation regressions trigger rollback."""
    from superlocalmemory.core import shadow_router as sr_mod

    # Seed an active + a is_previous row so rollback has something to restore.
    now = _now_iso()
    with sqlite3.connect(learning_db) as conn:
        conn.execute(
            "INSERT INTO learning_model_state "
            "(profile_id, state_bytes, bytes_sha256, is_active, is_previous,"
            " trained_at, updated_at, metadata_json) "
            "VALUES (?, ?, ?, 0, 1, ?, ?, ?)",
            ("p", b"prev", "0" * 64, now, now, "{}"),
        )
        conn.execute(
            "INSERT INTO learning_model_state "
            "(profile_id, state_bytes, bytes_sha256, is_active, "
            " trained_at, updated_at, metadata_json) "
            "VALUES (?, ?, ?, 1, ?, ?, ?)",
            ("p", b"active", "0" * 64, now, now, "{}"),
        )
        conn.commit()

    router = sr_mod.ShadowRouter(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="p",
    )
    # Arm post-promotion watcher with high baseline, feed 200 low NDCG samples.
    router.arm_post_promotion_watch(baseline_ndcg=0.8)
    for i in range(200):
        router.on_recall_settled(
            query_id=f"q-{i}", arm="baseline", ndcg_at_10=0.1,
        )

    with sqlite3.connect(learning_db) as conn:
        row = conn.execute(
            "SELECT is_rollback FROM learning_model_state "
            "WHERE profile_id='p' AND state_bytes=?",
            (b"active",),
        ).fetchone()
        assert row is not None and row[0] == 1


# ---------------------------------------------------------------------------
# Singleton factory + reset
# ---------------------------------------------------------------------------


def test_shadow_router_singleton_factory_returns_same_instance(
    learning_db: Path, memory_db: Path,
) -> None:
    """``get_shadow_router`` returns the same instance for the same key."""
    from superlocalmemory.core.shadow_router import get_shadow_router

    r1 = get_shadow_router(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="p",
    )
    r2 = get_shadow_router(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="p",
    )
    assert r1 is r2

    # Different profile_id → different instance.
    r3 = get_shadow_router(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="q",
    )
    assert r3 is not r1


def test_shadow_router_reset_for_testing(
    learning_db: Path, memory_db: Path,
) -> None:
    """``reset_for_testing`` wipes the singleton cache."""
    from superlocalmemory.core import shadow_router as sr_mod

    r1 = sr_mod.get_shadow_router(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="p",
    )
    sr_mod.reset_for_testing()
    r2 = sr_mod.get_shadow_router(
        memory_db=str(memory_db),
        learning_db=str(learning_db),
        profile_id="p",
    )
    assert r1 is not r2
