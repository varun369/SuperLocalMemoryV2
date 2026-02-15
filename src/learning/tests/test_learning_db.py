#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Tests for LearningDB (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
"""

import json
import sqlite3
import threading
import time
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset LearningDB singleton between tests to avoid cross-test pollution."""
    from src.learning.learning_db import LearningDB
    LearningDB.reset_instance()
    yield
    LearningDB.reset_instance()


@pytest.fixture
def learning_db(tmp_path):
    """Create a fresh LearningDB backed by a temp directory."""
    from src.learning.learning_db import LearningDB
    db_path = tmp_path / "learning.db"
    db = LearningDB(db_path=db_path)
    return db


# ---------------------------------------------------------------------------
# Schema Initialisation
# ---------------------------------------------------------------------------

class TestSchema:
    """Verify all 6 tables and indexes are created correctly."""

    def test_all_tables_exist(self, learning_db):
        conn = learning_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "transferable_patterns",
            "workflow_patterns",
            "ranking_feedback",
            "ranking_models",
            "source_quality",
            "engagement_metrics",
        }
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"

    def test_indexes_exist(self, learning_db):
        conn = learning_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_indexes = {
            "idx_feedback_query",
            "idx_feedback_memory",
            "idx_feedback_channel",
            "idx_feedback_created",
            "idx_patterns_type",
            "idx_workflow_type",
            "idx_engagement_date",
        }
        assert expected_indexes.issubset(indexes), (
            f"Missing indexes: {expected_indexes - indexes}"
        )

    def test_wal_mode_enabled(self, learning_db):
        conn = learning_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        conn.close()
        assert mode.lower() == "wal"


# ---------------------------------------------------------------------------
# Feedback Operations
# ---------------------------------------------------------------------------

class TestFeedback:
    """Tests for store_feedback / get_feedback_count / get_unique_query_count."""

    def test_store_feedback_basic(self, learning_db):
        row_id = learning_db.store_feedback(
            query_hash="abc123",
            memory_id=42,
            signal_type="mcp_used",
            signal_value=1.0,
            channel="mcp",
        )
        assert row_id is not None
        assert row_id >= 1

    def test_store_feedback_with_all_fields(self, learning_db):
        row_id = learning_db.store_feedback(
            query_hash="def456",
            memory_id=99,
            signal_type="dashboard_click",
            signal_value=0.8,
            channel="dashboard",
            query_keywords="deploy,fastapi",
            rank_position=3,
            source_tool="cursor",
            dwell_time=12.5,
        )
        assert row_id is not None

        # Verify all fields were stored
        rows = learning_db.get_feedback_for_training()
        assert len(rows) == 1
        row = rows[0]
        assert row["query_hash"] == "def456"
        assert row["memory_id"] == 99
        assert row["signal_type"] == "dashboard_click"
        assert row["signal_value"] == 0.8
        assert row["channel"] == "dashboard"
        assert row["query_keywords"] == "deploy,fastapi"
        assert row["rank_position"] == 3
        assert row["source_tool"] == "cursor"

    def test_feedback_count(self, learning_db):
        assert learning_db.get_feedback_count() == 0

        for i in range(5):
            learning_db.store_feedback(
                query_hash=f"q{i}",
                memory_id=i,
                signal_type="mcp_used",
            )
        assert learning_db.get_feedback_count() == 5

    def test_unique_query_count(self, learning_db):
        # 3 feedback entries across 2 distinct queries
        learning_db.store_feedback(query_hash="q1", memory_id=1, signal_type="mcp_used")
        learning_db.store_feedback(query_hash="q1", memory_id=2, signal_type="mcp_used")
        learning_db.store_feedback(query_hash="q2", memory_id=3, signal_type="cli_useful")

        assert learning_db.get_unique_query_count() == 2

    def test_feedback_for_training_limit(self, learning_db):
        for i in range(15):
            learning_db.store_feedback(
                query_hash=f"q{i % 5}",
                memory_id=i,
                signal_type="mcp_used",
            )

        # Fetch with limit
        rows = learning_db.get_feedback_for_training(limit=5)
        assert len(rows) == 5

    def test_feedback_for_training_order(self, learning_db):
        """Newest first ordering."""
        learning_db.store_feedback(query_hash="old", memory_id=1, signal_type="mcp_used")
        time.sleep(0.05)
        learning_db.store_feedback(query_hash="new", memory_id=2, signal_type="cli_useful")

        rows = learning_db.get_feedback_for_training()
        assert len(rows) == 2
        assert rows[0]["query_hash"] == "new"

    def test_signal_value_variations(self, learning_db):
        """Various signal values: 0.0, 0.5, 1.0."""
        for sv in [0.0, 0.4, 0.7, 1.0]:
            learning_db.store_feedback(
                query_hash="q",
                memory_id=1,
                signal_type="mcp_used",
                signal_value=sv,
            )
        rows = learning_db.get_feedback_for_training()
        values = sorted(r["signal_value"] for r in rows)
        assert values == [0.0, 0.4, 0.7, 1.0]


# ---------------------------------------------------------------------------
# Transferable Patterns
# ---------------------------------------------------------------------------

class TestTransferablePatterns:
    def test_upsert_insert(self, learning_db):
        row_id = learning_db.upsert_transferable_pattern(
            pattern_type="preference",
            key="frontend_framework",
            value="react",
            confidence=0.85,
            evidence_count=12,
        )
        assert row_id >= 1

        patterns = learning_db.get_transferable_patterns()
        assert len(patterns) == 1
        assert patterns[0]["key"] == "frontend_framework"
        assert patterns[0]["value"] == "react"

    def test_upsert_update(self, learning_db):
        """Second upsert with same type+key should UPDATE, not insert."""
        learning_db.upsert_transferable_pattern(
            pattern_type="preference",
            key="lang",
            value="python",
            confidence=0.6,
            evidence_count=5,
        )
        learning_db.upsert_transferable_pattern(
            pattern_type="preference",
            key="lang",
            value="typescript",
            confidence=0.8,
            evidence_count=10,
        )

        patterns = learning_db.get_transferable_patterns()
        assert len(patterns) == 1
        assert patterns[0]["value"] == "typescript"
        assert patterns[0]["confidence"] == 0.8
        assert patterns[0]["evidence_count"] == 10

    def test_get_with_confidence_filter(self, learning_db):
        learning_db.upsert_transferable_pattern(
            pattern_type="preference", key="a", value="v1",
            confidence=0.3, evidence_count=1,
        )
        learning_db.upsert_transferable_pattern(
            pattern_type="preference", key="b", value="v2",
            confidence=0.9, evidence_count=10,
        )

        high = learning_db.get_transferable_patterns(min_confidence=0.6)
        assert len(high) == 1
        assert high[0]["key"] == "b"

    def test_get_with_type_filter(self, learning_db):
        learning_db.upsert_transferable_pattern(
            pattern_type="preference", key="k1", value="v1",
            confidence=0.7, evidence_count=5,
        )
        learning_db.upsert_transferable_pattern(
            pattern_type="style", key="k2", value="v2",
            confidence=0.8, evidence_count=8,
        )

        prefs = learning_db.get_transferable_patterns(pattern_type="preference")
        assert len(prefs) == 1
        assert prefs[0]["key"] == "k1"

    def test_contradictions_stored_as_json(self, learning_db):
        learning_db.upsert_transferable_pattern(
            pattern_type="preference",
            key="db",
            value="postgres",
            confidence=0.7,
            evidence_count=5,
            contradictions=["Profile 'work' prefers 'mysql'"],
        )
        patterns = learning_db.get_transferable_patterns()
        raw = patterns[0]["contradictions"]
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        assert parsed == ["Profile 'work' prefers 'mysql'"]


# ---------------------------------------------------------------------------
# Workflow Patterns
# ---------------------------------------------------------------------------

class TestWorkflowPatterns:
    def test_store_and_get(self, learning_db):
        learning_db.store_workflow_pattern(
            pattern_type="sequence",
            pattern_key="docs -> code -> test",
            pattern_value='{"sequence": ["docs", "code", "test"]}',
            confidence=0.45,
            evidence_count=12,
        )

        patterns = learning_db.get_workflow_patterns()
        assert len(patterns) == 1
        assert patterns[0]["pattern_key"] == "docs -> code -> test"

    def test_get_with_type_filter(self, learning_db):
        learning_db.store_workflow_pattern(
            pattern_type="sequence", pattern_key="a", pattern_value="v",
            confidence=0.5, evidence_count=5,
        )
        learning_db.store_workflow_pattern(
            pattern_type="temporal", pattern_key="morning", pattern_value="{}",
            confidence=0.6, evidence_count=8,
        )

        seq = learning_db.get_workflow_patterns(pattern_type="sequence")
        assert len(seq) == 1
        assert seq[0]["pattern_type"] == "sequence"

    def test_clear_all(self, learning_db):
        for i in range(3):
            learning_db.store_workflow_pattern(
                pattern_type="sequence",
                pattern_key=f"p{i}",
                pattern_value="{}",
            )
        learning_db.clear_workflow_patterns()
        assert learning_db.get_workflow_patterns() == []

    def test_clear_by_type(self, learning_db):
        learning_db.store_workflow_pattern(
            pattern_type="sequence", pattern_key="a", pattern_value="{}",
        )
        learning_db.store_workflow_pattern(
            pattern_type="temporal", pattern_key="b", pattern_value="{}",
        )
        learning_db.clear_workflow_patterns(pattern_type="sequence")

        remaining = learning_db.get_workflow_patterns()
        assert len(remaining) == 1
        assert remaining[0]["pattern_type"] == "temporal"

    def test_confidence_filter(self, learning_db):
        learning_db.store_workflow_pattern(
            pattern_type="sequence", pattern_key="low",
            pattern_value="{}", confidence=0.2,
        )
        learning_db.store_workflow_pattern(
            pattern_type="sequence", pattern_key="high",
            pattern_value="{}", confidence=0.8,
        )

        high = learning_db.get_workflow_patterns(min_confidence=0.5)
        assert len(high) == 1
        assert high[0]["pattern_key"] == "high"


# ---------------------------------------------------------------------------
# Source Quality
# ---------------------------------------------------------------------------

class TestSourceQuality:
    def test_update_and_get(self, learning_db):
        learning_db.update_source_quality("mcp:claude", 8, 10)

        scores = learning_db.get_source_scores()
        assert "mcp:claude" in scores
        # Beta-Binomial: (1 + 8) / (2 + 10) = 0.75
        assert abs(scores["mcp:claude"] - 0.75) < 0.001

    def test_beta_binomial_calculation(self, learning_db):
        """Verify the Beta-Binomial formula: (1+pos)/(2+total)."""
        cases = [
            (0, 0, 0.5),      # No data = neutral
            (5, 10, 0.5),     # 50% positive = 0.5
            (1, 10, 2.0 / 12.0),  # Low positive
            (9, 10, 10.0 / 12.0),  # High positive
        ]
        for pos, total, expected in cases:
            learning_db.update_source_quality(f"src_{pos}_{total}", pos, total)
            scores = learning_db.get_source_scores()
            actual = scores[f"src_{pos}_{total}"]
            assert abs(actual - expected) < 0.001, (
                f"pos={pos}, total={total}: expected {expected}, got {actual}"
            )

    def test_upsert_on_conflict(self, learning_db):
        """Updating same source_id should overwrite, not duplicate."""
        learning_db.update_source_quality("mcp:cursor", 2, 10)
        learning_db.update_source_quality("mcp:cursor", 8, 10)

        scores = learning_db.get_source_scores()
        assert abs(scores["mcp:cursor"] - 0.75) < 0.001

    def test_empty_scores(self, learning_db):
        scores = learning_db.get_source_scores()
        assert scores == {}


# ---------------------------------------------------------------------------
# Model Metadata
# ---------------------------------------------------------------------------

class TestModelMetadata:
    def test_record_and_get_latest(self, learning_db):
        learning_db.record_model_training(
            model_version="v1",
            training_samples=500,
            synthetic_samples=200,
            real_samples=300,
            ndcg_at_10=0.85,
            model_path="/tmp/model.txt",
        )
        latest = learning_db.get_latest_model()
        assert latest is not None
        assert latest["model_version"] == "v1"
        assert latest["training_samples"] == 500
        assert latest["ndcg_at_10"] == 0.85

    def test_latest_model_ordering(self, learning_db):
        """Latest model should be the one with the highest rowid."""
        learning_db.record_model_training("v1", 100)
        # SQLite CURRENT_TIMESTAMP has second precision, so sleep long enough
        time.sleep(1.1)
        learning_db.record_model_training("v2", 200)

        latest = learning_db.get_latest_model()
        assert latest["model_version"] == "v2"

    def test_no_models(self, learning_db):
        assert learning_db.get_latest_model() is None


# ---------------------------------------------------------------------------
# Engagement Metrics
# ---------------------------------------------------------------------------

class TestEngagement:
    def test_increment_memories_created(self, learning_db):
        learning_db.increment_engagement("memories_created", count=3)
        history = learning_db.get_engagement_history(days=1)
        assert len(history) >= 1
        assert history[0]["memories_created"] == 3

    def test_increment_multiple_types(self, learning_db):
        learning_db.increment_engagement("memories_created", count=2)
        learning_db.increment_engagement("recalls_performed", count=5)
        learning_db.increment_engagement("feedback_signals", count=1)

        history = learning_db.get_engagement_history(days=1)
        row = history[0]
        assert row["memories_created"] == 2
        assert row["recalls_performed"] == 5
        assert row["feedback_signals"] == 1

    def test_invalid_metric_type_ignored(self, learning_db):
        """Invalid metric types should be silently ignored."""
        learning_db.increment_engagement("invalid_metric", count=1)
        # No row created if no valid metric incremented
        history = learning_db.get_engagement_history(days=1)
        assert len(history) == 0

    def test_source_tracking(self, learning_db):
        learning_db.increment_engagement(
            "memories_created", count=1, source="claude-desktop"
        )
        learning_db.increment_engagement(
            "recalls_performed", count=1, source="cursor"
        )

        history = learning_db.get_engagement_history(days=1)
        sources = json.loads(history[0]["active_sources"])
        assert "claude-desktop" in sources
        assert "cursor" in sources

    def test_source_deduplication(self, learning_db):
        """Same source added twice should appear only once."""
        learning_db.increment_engagement("memories_created", count=1, source="cli")
        learning_db.increment_engagement("recalls_performed", count=1, source="cli")

        history = learning_db.get_engagement_history(days=1)
        sources = json.loads(history[0]["active_sources"])
        assert sources.count("cli") == 1


# ---------------------------------------------------------------------------
# Stats & Reset
# ---------------------------------------------------------------------------

class TestStatsAndReset:
    def test_get_stats_empty(self, learning_db):
        stats = learning_db.get_stats()
        assert stats["feedback_count"] == 0
        assert stats["unique_queries"] == 0
        assert stats["transferable_patterns"] == 0
        assert stats["high_confidence_patterns"] == 0
        assert stats["workflow_patterns"] == 0
        assert stats["tracked_sources"] == 0
        assert stats["models_trained"] == 0
        assert stats["latest_model_version"] is None
        assert stats["db_size_bytes"] > 0  # DB file exists

    def test_get_stats_populated(self, learning_db):
        learning_db.store_feedback(
            query_hash="q1", memory_id=1, signal_type="mcp_used",
        )
        learning_db.upsert_transferable_pattern(
            pattern_type="preference", key="lang", value="python",
            confidence=0.9, evidence_count=10,
        )
        learning_db.store_workflow_pattern(
            pattern_type="sequence", pattern_key="a -> b",
            pattern_value="{}", confidence=0.5, evidence_count=5,
        )
        learning_db.update_source_quality("cli", 3, 5)
        learning_db.record_model_training("v1", 100, ndcg_at_10=0.8)

        stats = learning_db.get_stats()
        assert stats["feedback_count"] == 1
        assert stats["transferable_patterns"] == 1
        assert stats["high_confidence_patterns"] == 1
        assert stats["workflow_patterns"] == 1
        assert stats["tracked_sources"] == 1
        assert stats["models_trained"] == 1
        assert stats["latest_model_version"] == "v1"
        assert stats["latest_model_ndcg"] == 0.8

    def test_reset_clears_all(self, learning_db):
        learning_db.store_feedback(query_hash="q", memory_id=1, signal_type="x")
        learning_db.upsert_transferable_pattern(
            pattern_type="p", key="k", value="v", confidence=0.5, evidence_count=1,
        )
        learning_db.store_workflow_pattern(
            pattern_type="s", pattern_key="k", pattern_value="v",
        )
        learning_db.update_source_quality("src", 1, 1)
        learning_db.record_model_training("v1", 10)
        learning_db.increment_engagement("memories_created", count=1)

        learning_db.reset()

        stats = learning_db.get_stats()
        assert stats["feedback_count"] == 0
        assert stats["transferable_patterns"] == 0
        assert stats["workflow_patterns"] == 0
        assert stats["tracked_sources"] == 0
        assert stats["models_trained"] == 0


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

class TestConcurrency:
    def test_concurrent_writes(self, learning_db):
        """10 threads writing simultaneously should produce zero errors."""
        errors = []

        def writer(thread_id):
            try:
                for i in range(10):
                    learning_db.store_feedback(
                        query_hash=f"q_t{thread_id}_{i}",
                        memory_id=thread_id * 100 + i,
                        signal_type="mcp_used",
                        signal_value=1.0,
                        channel="mcp",
                    )
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=writer, args=(tid,)) for tid in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert errors == [], f"Concurrent write errors: {errors}"
        assert learning_db.get_feedback_count() == 100


# ---------------------------------------------------------------------------
# Singleton Pattern
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_instance_returns_same_object(self, tmp_path):
        from src.learning.learning_db import LearningDB
        LearningDB.reset_instance()

        db_path = tmp_path / "singleton_test.db"
        a = LearningDB.get_instance(db_path)
        b = LearningDB.get_instance(db_path)
        assert a is b

    def test_different_paths_different_instances(self, tmp_path):
        from src.learning.learning_db import LearningDB
        LearningDB.reset_instance()

        a = LearningDB.get_instance(tmp_path / "a.db")
        b = LearningDB.get_instance(tmp_path / "b.db")
        assert a is not b

    def test_reset_instance_clears(self, tmp_path):
        from src.learning.learning_db import LearningDB
        LearningDB.reset_instance()

        db_path = tmp_path / "reset_test.db"
        a = LearningDB.get_instance(db_path)
        LearningDB.reset_instance(db_path)
        b = LearningDB.get_instance(db_path)
        assert a is not b
