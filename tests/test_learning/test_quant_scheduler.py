# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3

"""Tests for Quantization Scheduler (SAGQ + EAP combined).

TDD sequence (Phase D LLD Section 6):
  9.  test_scheduler_batch_processing
  10. test_downgrade_triggers_compress
  11. test_upgrade_requires_backup
  12. test_skip_when_no_precision_change
  13. test_audit_trail_logged_for_every_change
  14. test_core_memory_immune_to_quantization
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from superlocalmemory.core.config import SAGQConfig
from superlocalmemory.dynamics.activation_guided_quantization import (
    ActivationGuidedQuantizer,
    SAGQPrecision,
)
from superlocalmemory.learning.quantization_scheduler import (
    PrecisionChange,
    QuantizationScheduler,
    SchedulerRunResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_scheduler_test_db(tmp_path: Path) -> MagicMock:
    """Create mock DatabaseManager backed by real SQLite for scheduler tests."""
    db = MagicMock()
    conn = sqlite3.connect(str(tmp_path / "scheduler_test.db"))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS fact_importance (
            fact_id            TEXT NOT NULL,
            profile_id         TEXT NOT NULL,
            pagerank_score     REAL NOT NULL DEFAULT 0.0,
            community_id       INTEGER,
            degree_centrality  REAL NOT NULL DEFAULT 0.0,
            computed_at        TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (fact_id, profile_id)
        );

        CREATE TABLE IF NOT EXISTS activation_cache (
            cache_id         TEXT PRIMARY KEY,
            profile_id       TEXT NOT NULL,
            query_hash       TEXT NOT NULL,
            node_id          TEXT NOT NULL,
            activation_value REAL NOT NULL,
            iteration        INTEGER NOT NULL DEFAULT 0,
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at       TEXT NOT NULL DEFAULT (datetime('now', '+1 hour'))
        );

        CREATE TABLE IF NOT EXISTS embedding_metadata (
            vec_rowid    INTEGER,
            fact_id      TEXT NOT NULL,
            profile_id   TEXT NOT NULL,
            model_name   TEXT,
            dimension    INTEGER,
            bit_width    INTEGER NOT NULL DEFAULT 32,
            quantization_level TEXT NOT NULL DEFAULT 'float32',
            compressed_size_bytes INTEGER,
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (fact_id, profile_id)
        );

        CREATE TABLE IF NOT EXISTS core_memory_blocks (
            block_id         TEXT PRIMARY KEY,
            profile_id       TEXT NOT NULL,
            category         TEXT NOT NULL,
            content          TEXT NOT NULL,
            source_fact_ids  TEXT NOT NULL DEFAULT '[]',
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS fact_access_log (
            log_id       TEXT PRIMARY KEY,
            fact_id      TEXT NOT NULL,
            profile_id   TEXT NOT NULL,
            accessed_at  TEXT NOT NULL DEFAULT (datetime('now')),
            access_type  TEXT NOT NULL DEFAULT 'read',
            session_id   TEXT
        );

        CREATE TABLE IF NOT EXISTS polar_embeddings (
            fact_id     TEXT PRIMARY KEY,
            profile_id  TEXT NOT NULL,
            radius      REAL NOT NULL,
            angle_indices BLOB NOT NULL,
            qjl_bits    BLOB,
            bit_width   INTEGER NOT NULL DEFAULT 4,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()

    def _execute(sql, params=()):
        rows = conn.execute(sql, params).fetchall()
        conn.commit()
        return rows

    db.execute.side_effect = _execute
    db._test_conn = conn
    return db


@pytest.fixture
def sagq_config() -> SAGQConfig:
    return SAGQConfig()


@pytest.fixture
def test_db(tmp_path: Path) -> MagicMock:
    db = _create_scheduler_test_db(tmp_path)
    yield db
    db._test_conn.close()


@pytest.fixture
def quantizer(test_db: MagicMock, sagq_config: SAGQConfig) -> ActivationGuidedQuantizer:
    return ActivationGuidedQuantizer(test_db, sagq_config)


@pytest.fixture
def mock_quantized_store() -> MagicMock:
    """Mock QuantizedEmbeddingStore."""
    store = MagicMock()
    store.compress_fact.return_value = True
    return store


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Mock vector store for embedding retrieval."""
    store = MagicMock()
    store.get_embedding.return_value = np.random.default_rng(42).standard_normal(768).astype(np.float32)
    return store


@pytest.fixture
def scheduler(
    test_db: MagicMock,
    quantizer: ActivationGuidedQuantizer,
    mock_quantized_store: MagicMock,
    mock_vector_store: MagicMock,
    sagq_config: SAGQConfig,
) -> QuantizationScheduler:
    return QuantizationScheduler(
        db=test_db,
        sagq=quantizer,
        eap_mapper=lambda fid: 4,  # Default: EAP says 4-bit for all
        quantized_store=mock_quantized_store,
        vector_store=mock_vector_store,
        config=sagq_config,
    )


# ---------------------------------------------------------------------------
# 9. Batch processing
# ---------------------------------------------------------------------------


def test_scheduler_batch_processing(
    scheduler: QuantizationScheduler,
    test_db: MagicMock,
) -> None:
    """Scheduler processes multiple facts and returns correct totals."""
    conn = test_db._test_conn

    # Insert 5 facts with varying centrality
    for i in range(5):
        pr = i * 0.25
        deg = i * 0.2
        conn.execute(
            "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
            "VALUES (?, 'p1', ?, ?)",
            (f"f{i}", pr, deg),
        )
        conn.execute(
            "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
            "VALUES (?, 'p1', 32)",
            (f"f{i}",),
        )
    conn.commit()

    result = scheduler.run("p1")

    assert isinstance(result, SchedulerRunResult)
    assert result.total_facts == 5
    assert result.upgrades + result.downgrades + result.skipped + result.errors == 5
    assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# 10. Downgrade triggers compress
# ---------------------------------------------------------------------------


def test_downgrade_triggers_compress(
    scheduler: QuantizationScheduler,
    test_db: MagicMock,
    mock_quantized_store: MagicMock,
    mock_vector_store: MagicMock,
) -> None:
    """Downgrade action calls quantized_store.compress_fact with correct args."""
    conn = test_db._test_conn

    # Low centrality fact -> SAGQ will recommend low bit-width
    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('low', 'p1', 0.0, 0.0)"
    )
    # Also insert a max-value fact so normalization still makes 'low' be 0.0
    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('high', 'p1', 1.0, 1.0)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('low', 'p1', 32)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('high', 'p1', 32)"
    )
    conn.commit()

    # EAP says 2-bit for low, 32 for high
    scheduler._eap_mapper = lambda fid: 2 if fid == "low" else 32

    result = scheduler.run("p1")

    # 'low' should be downgraded (centrality=0 -> sagq=2, eap=2, final=2, current=32)
    assert result.downgrades >= 1
    # Verify compress_fact was called
    mock_quantized_store.compress_fact.assert_called()

    # Find the call for 'low'
    calls = mock_quantized_store.compress_fact.call_args_list
    low_calls = [c for c in calls if c[0][0] == "low"]
    assert len(low_calls) >= 1
    # Verify args: (fact_id, profile_id, embedding, target_bit_width)
    assert low_calls[0][0][1] == "p1"


# ---------------------------------------------------------------------------
# 11. Upgrade requires float32 backup
# ---------------------------------------------------------------------------


def test_upgrade_requires_backup(
    scheduler: QuantizationScheduler,
    test_db: MagicMock,
    mock_vector_store: MagicMock,
) -> None:
    """Upgrade is skipped when no float32 backup exists (vector store returns None)."""
    conn = test_db._test_conn

    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('no_backup', 'p1', 1.0, 1.0)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('no_backup', 'p1', 4)"
    )
    conn.commit()

    # EAP says 32-bit, SAGQ also says 32 -> wants upgrade from 4 to 32
    scheduler._eap_mapper = lambda fid: 32

    # But no float32 backup available
    mock_vector_store.get_embedding.return_value = None

    result = scheduler.run("p1")

    # Should not crash, just skip or error
    assert result.errors >= 1 or result.skipped >= 1


def test_upgrade_with_backup_succeeds(
    scheduler: QuantizationScheduler,
    test_db: MagicMock,
    mock_quantized_store: MagicMock,
    mock_vector_store: MagicMock,
) -> None:
    """Upgrade works when float32 backup exists."""
    conn = test_db._test_conn

    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('has_backup', 'p1', 1.0, 1.0)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('has_backup', 'p1', 4)"
    )
    conn.commit()

    scheduler._eap_mapper = lambda fid: 32

    # Float32 backup available
    mock_vector_store.get_embedding.return_value = (
        np.random.default_rng(42).standard_normal(768).astype(np.float32)
    )

    result = scheduler.run("p1")
    assert result.upgrades >= 1


# ---------------------------------------------------------------------------
# 12. Skip when no precision change
# ---------------------------------------------------------------------------


def test_skip_when_no_precision_change(
    scheduler: QuantizationScheduler,
    test_db: MagicMock,
    mock_quantized_store: MagicMock,
) -> None:
    """Fact where final_bw == current_bw -> skip, no compress/restore calls."""
    conn = test_db._test_conn

    # High centrality + high EAP -> both say 32, current is 32
    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('steady', 'p1', 1.0, 1.0)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('steady', 'p1', 32)"
    )
    conn.commit()

    scheduler._eap_mapper = lambda fid: 32

    mock_quantized_store.reset_mock()
    result = scheduler.run("p1")

    assert result.skipped >= 1
    # compress_fact should NOT be called for skipped facts
    mock_quantized_store.compress_fact.assert_not_called()


# ---------------------------------------------------------------------------
# 13. Audit trail logged for every change
# ---------------------------------------------------------------------------


def test_audit_trail_logged_for_every_change(
    scheduler: QuantizationScheduler,
    test_db: MagicMock,
) -> None:
    """After run with changes, fact_access_log has entries with access_type='consolidation'."""
    conn = test_db._test_conn

    # 3 facts that will be downgraded
    for i in range(3):
        conn.execute(
            "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
            "VALUES (?, 'p1', 0.0, 0.0)",
            (f"audit{i}",),
        )
        conn.execute(
            "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
            "VALUES (?, 'p1', 32)",
            (f"audit{i}",),
        )
    # Need at least one reference fact for normalization
    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('ref', 'p1', 1.0, 1.0)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('ref', 'p1', 32)"
    )
    conn.commit()

    scheduler._eap_mapper = lambda fid: 2 if fid.startswith("audit") else 32

    result = scheduler.run("p1")

    # Check audit trail
    audit_rows = conn.execute(
        "SELECT * FROM fact_access_log WHERE access_type = 'consolidation'"
    ).fetchall()

    # At least one change should have an audit entry
    change_count = result.downgrades + result.upgrades
    assert len(audit_rows) == change_count
    assert change_count >= 1

    for row in audit_rows:
        d = dict(row)
        assert d["session_id"] == "sagq_scheduler"
        assert d["access_type"] == "consolidation"


# ---------------------------------------------------------------------------
# 14. Core memory immune to quantization
# ---------------------------------------------------------------------------


def test_core_memory_immune_to_quantization(
    scheduler: QuantizationScheduler,
    test_db: MagicMock,
    mock_quantized_store: MagicMock,
) -> None:
    """Fact referenced by core_memory_blocks is never downgraded (HR-01)."""
    conn = test_db._test_conn

    import json

    # Insert a core memory block that references 'protected-fact'
    conn.execute(
        "INSERT INTO core_memory_blocks "
        "(block_id, profile_id, category, content, source_fact_ids) "
        "VALUES ('blk1', 'p1', 'identity', 'I am Varun', ?)",
        (json.dumps(["protected-fact"]),),
    )

    # The protected fact has low centrality -- would normally be downgraded
    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('protected-fact', 'p1', 0.0, 0.0)"
    )
    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('ref', 'p1', 1.0, 1.0)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('protected-fact', 'p1', 32)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('ref', 'p1', 32)"
    )
    conn.commit()

    # EAP says 2-bit, SAGQ says 2-bit -> both want downgrade
    scheduler._eap_mapper = lambda fid: 2

    mock_quantized_store.reset_mock()
    result = scheduler.run("p1")

    # Protected fact should NOT be downgraded
    compress_calls = mock_quantized_store.compress_fact.call_args_list
    protected_calls = [c for c in compress_calls if c[0][0] == "protected-fact"]
    assert len(protected_calls) == 0


# ---------------------------------------------------------------------------
# HR-07: Disabled config returns immediately
# ---------------------------------------------------------------------------


def test_disabled_scheduler_returns_empty(
    test_db: MagicMock,
) -> None:
    """Scheduler with enabled=False returns zero-result immediately."""
    config = SAGQConfig(enabled=False)
    q = ActivationGuidedQuantizer(test_db, config)
    sched = QuantizationScheduler(
        db=test_db, sagq=q, eap_mapper=lambda _: 32,
        quantized_store=MagicMock(), vector_store=MagicMock(), config=config,
    )
    result = sched.run("p1")
    assert result.total_facts == 0
    assert result.upgrades == 0
    assert result.downgrades == 0


# ---------------------------------------------------------------------------
# should_run timing check
# ---------------------------------------------------------------------------


def test_should_run_never_run_before() -> None:
    """If last_run_at is None, should_run returns True."""
    config = SAGQConfig()
    sched = QuantizationScheduler(
        db=MagicMock(), sagq=MagicMock(), eap_mapper=lambda _: 32,
        quantized_store=MagicMock(), vector_store=MagicMock(), config=config,
    )
    assert sched.should_run(None) is True


def test_should_run_recently() -> None:
    """If last run was 1 minute ago, should_run returns False."""
    config = SAGQConfig(scheduler_interval_hours=6.0)
    sched = QuantizationScheduler(
        db=MagicMock(), sagq=MagicMock(), eap_mapper=lambda _: 32,
        quantized_store=MagicMock(), vector_store=MagicMock(), config=config,
    )
    now = datetime.now(UTC)
    one_min_ago = (now - timedelta(minutes=1)).isoformat()
    assert sched.should_run(one_min_ago) is False


def test_should_run_overdue() -> None:
    """If last run was 7 hours ago and interval is 6h, should_run returns True."""
    config = SAGQConfig(scheduler_interval_hours=6.0)
    sched = QuantizationScheduler(
        db=MagicMock(), sagq=MagicMock(), eap_mapper=lambda _: 32,
        quantized_store=MagicMock(), vector_store=MagicMock(), config=config,
    )
    now = datetime.now(UTC)
    seven_hours_ago = (now - timedelta(hours=7)).isoformat()
    assert sched.should_run(seven_hours_ago) is True


# ---------------------------------------------------------------------------
# bit_width_to_quantization_level
# ---------------------------------------------------------------------------


def test_bit_width_to_quantization_level() -> None:
    """Verify the mapping from bit-width to quantization level string."""
    config = SAGQConfig()
    sched = QuantizationScheduler(
        db=MagicMock(), sagq=MagicMock(), eap_mapper=lambda _: 32,
        quantized_store=MagicMock(), vector_store=MagicMock(), config=config,
    )
    assert sched._bit_width_to_quantization_level(32) == "float32"
    assert sched._bit_width_to_quantization_level(8) == "int8"
    assert sched._bit_width_to_quantization_level(4) == "polar4"
    assert sched._bit_width_to_quantization_level(2) == "polar2"
    assert sched._bit_width_to_quantization_level(0) == "deleted"
    assert sched._bit_width_to_quantization_level(16) == "float32"  # unknown -> default


# ---------------------------------------------------------------------------
# Error isolation (one failure does not block others)
# ---------------------------------------------------------------------------


def test_error_isolation_continues_batch(
    scheduler: QuantizationScheduler,
    test_db: MagicMock,
    mock_quantized_store: MagicMock,
) -> None:
    """compress_fact failure for one fact does not block others."""
    conn = test_db._test_conn

    for i in range(3):
        conn.execute(
            "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
            "VALUES (?, 'p1', 0.0, 0.0)",
            (f"err{i}",),
        )
        conn.execute(
            "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
            "VALUES (?, 'p1', 32)",
            (f"err{i}",),
        )
    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('ref', 'p1', 1.0, 1.0)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('ref', 'p1', 32)"
    )
    conn.commit()

    scheduler._eap_mapper = lambda fid: 2 if fid.startswith("err") else 32

    # First call fails, rest succeed
    mock_quantized_store.compress_fact.side_effect = [
        RuntimeError("disk full"), True, True,
    ]

    result = scheduler.run("p1")
    assert result.errors >= 1
    # At least some succeeded
    assert result.downgrades >= 1


# ---------------------------------------------------------------------------
# Frozen dataclass enforcement
# ---------------------------------------------------------------------------


def test_precision_change_frozen() -> None:
    """PrecisionChange is immutable."""
    pc = PrecisionChange(
        fact_id="f1", old_bit_width=32, new_bit_width=4,
        action="downgrade", centrality=0.1,
        sagq_signal=2, eap_signal=4, timestamp="2026-03-31T00:00:00",
    )
    with pytest.raises(AttributeError):
        pc.action = "upgrade"  # type: ignore[misc]


def test_scheduler_run_result_frozen() -> None:
    """SchedulerRunResult is immutable."""
    sr = SchedulerRunResult(
        total_facts=5, upgrades=1, downgrades=2,
        skipped=1, errors=1, changes=(), duration_ms=100.0,
    )
    with pytest.raises(AttributeError):
        sr.total_facts = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Core memory query error path
# ---------------------------------------------------------------------------


def test_core_memory_query_error(
    test_db: MagicMock,
    sagq_config: SAGQConfig,
) -> None:
    """If core_memory_blocks query fails, no facts are excluded."""
    conn = test_db._test_conn

    # Drop core_memory_blocks to cause query error
    conn.execute("DROP TABLE core_memory_blocks")
    conn.commit()

    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('f1', 'p1', 0.0, 0.0)"
    )
    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('ref', 'p1', 1.0, 1.0)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('f1', 'p1', 32)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('ref', 'p1', 32)"
    )
    conn.commit()

    quantizer = ActivationGuidedQuantizer(test_db, sagq_config)
    mock_qs = MagicMock()
    mock_qs.compress_fact.return_value = True
    mock_vs = MagicMock()
    mock_vs.get_embedding.return_value = np.random.default_rng(42).standard_normal(768).astype(np.float32)

    sched = QuantizationScheduler(
        db=test_db, sagq=quantizer, eap_mapper=lambda _: 2,
        quantized_store=mock_qs, vector_store=mock_vs, config=sagq_config,
    )
    result = sched.run("p1")
    # Should still process (no exclusions due to error)
    assert result.total_facts >= 1


# ---------------------------------------------------------------------------
# Empty recommendations path
# ---------------------------------------------------------------------------


def test_scheduler_empty_recommendations(
    test_db: MagicMock,
    sagq_config: SAGQConfig,
) -> None:
    """Scheduler with no fact_importance data returns empty result."""
    quantizer = ActivationGuidedQuantizer(test_db, sagq_config)
    sched = QuantizationScheduler(
        db=test_db, sagq=quantizer, eap_mapper=lambda _: 32,
        quantized_store=MagicMock(), vector_store=MagicMock(), config=sagq_config,
    )
    result = sched.run("empty-profile")
    assert result.total_facts == 0
    assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# should_run parse error
# ---------------------------------------------------------------------------


def test_should_run_invalid_date() -> None:
    """If last_run_at is unparseable, should_run returns True (safe default)."""
    config = SAGQConfig()
    sched = QuantizationScheduler(
        db=MagicMock(), sagq=MagicMock(), eap_mapper=lambda _: 32,
        quantized_store=MagicMock(), vector_store=MagicMock(), config=config,
    )
    assert sched.should_run("not-a-date") is True


# ---------------------------------------------------------------------------
# Downgrade with vector_store returning None
# ---------------------------------------------------------------------------


def test_downgrade_no_embedding_skips(
    scheduler: QuantizationScheduler,
    test_db: MagicMock,
    mock_vector_store: MagicMock,
) -> None:
    """Downgrade is skipped (error) when vector_store returns None."""
    conn = test_db._test_conn

    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('no_emb', 'p1', 0.0, 0.0)"
    )
    conn.execute(
        "INSERT INTO fact_importance (fact_id, profile_id, pagerank_score, degree_centrality) "
        "VALUES ('ref', 'p1', 1.0, 1.0)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('no_emb', 'p1', 32)"
    )
    conn.execute(
        "INSERT INTO embedding_metadata (fact_id, profile_id, bit_width) "
        "VALUES ('ref', 'p1', 32)"
    )
    conn.commit()

    scheduler._eap_mapper = lambda fid: 2 if fid == "no_emb" else 32
    mock_vector_store.get_embedding.return_value = None

    result = scheduler.run("p1")
    # no_emb: action=downgrade but no embedding -> error
    assert result.errors >= 1


# ---------------------------------------------------------------------------
# should_run with naive datetime string (no timezone info)
# ---------------------------------------------------------------------------


def test_should_run_naive_datetime_string() -> None:
    """Naive datetime string (no timezone) is handled correctly (line 315)."""
    config = SAGQConfig(scheduler_interval_hours=6.0)
    sched = QuantizationScheduler(
        db=MagicMock(), sagq=MagicMock(), eap_mapper=lambda _: 32,
        quantized_store=MagicMock(), vector_store=MagicMock(), config=config,
    )
    # Naive datetime string (no +00:00 suffix)
    assert sched.should_run("2020-01-01T00:00:00") is True


# ---------------------------------------------------------------------------
# _process_precision_change with unknown action (line 241)
# ---------------------------------------------------------------------------


def test_process_change_unknown_action() -> None:
    """_process_precision_change returns None for unknown action."""
    config = SAGQConfig()
    sched = QuantizationScheduler(
        db=MagicMock(), sagq=MagicMock(), eap_mapper=lambda _: 32,
        quantized_store=MagicMock(), vector_store=MagicMock(), config=config,
    )
    # Create a mock precision with unknown action
    mock_prec = MagicMock()
    mock_prec.action = "unknown_action"
    mock_prec.fact_id = "f1"
    result = sched._process_precision_change(mock_prec, "p1")
    assert result is None


def test_run_with_unknown_action_counts_as_skipped() -> None:
    """Defensive: if SAGQ returns unknown action, scheduler counts it as skipped (line 178)."""
    config = SAGQConfig()
    mock_sagq = MagicMock()

    # Return a recommendation with an unrecognized action
    mock_prec = MagicMock()
    mock_prec.fact_id = "f1"
    mock_prec.action = "rebalance"  # Not skip/upgrade/downgrade
    mock_sagq.compute_sagq_precision_batch.return_value = [mock_prec]

    mock_db = MagicMock()
    mock_db.execute.return_value = []  # No core memory blocks

    sched = QuantizationScheduler(
        db=mock_db, sagq=mock_sagq, eap_mapper=lambda _: 32,
        quantized_store=MagicMock(), vector_store=MagicMock(), config=config,
    )
    result = sched.run("p1")
    # Unknown action -> _process_precision_change returns None -> skipped++
    assert result.skipped == 1
    assert result.total_facts == 1
