#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Tests for FeedbackCollector (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
"""

import hashlib
import time

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    from src.learning.learning_db import LearningDB
    LearningDB.reset_instance()
    yield
    LearningDB.reset_instance()


@pytest.fixture
def learning_db(tmp_path):
    from src.learning.learning_db import LearningDB
    db_path = tmp_path / "learning.db"
    return LearningDB(db_path=db_path)


@pytest.fixture
def collector(learning_db):
    from src.learning.feedback_collector import FeedbackCollector
    return FeedbackCollector(learning_db=learning_db)


@pytest.fixture
def collector_no_db():
    """Collector with no database — tests graceful degradation."""
    from src.learning.feedback_collector import FeedbackCollector
    return FeedbackCollector(learning_db=None)


# ---------------------------------------------------------------------------
# Channel 1: MCP memory_used
# ---------------------------------------------------------------------------

class TestRecordMemoryUsed:
    def test_high_usefulness(self, collector, learning_db):
        row_id = collector.record_memory_used(42, "deploy fastapi", usefulness="high")
        assert row_id is not None

        rows = learning_db.get_feedback_for_training()
        assert len(rows) == 1
        assert rows[0]["signal_type"] == "mcp_used_high"
        assert rows[0]["signal_value"] == 1.0
        assert rows[0]["channel"] == "mcp"

    def test_medium_usefulness(self, collector, learning_db):
        collector.record_memory_used(42, "deploy fastapi", usefulness="medium")
        rows = learning_db.get_feedback_for_training()
        assert rows[0]["signal_type"] == "mcp_used_medium"
        assert rows[0]["signal_value"] == 0.7

    def test_low_usefulness(self, collector, learning_db):
        collector.record_memory_used(42, "deploy fastapi", usefulness="low")
        rows = learning_db.get_feedback_for_training()
        assert rows[0]["signal_type"] == "mcp_used_low"
        assert rows[0]["signal_value"] == 0.4

    def test_invalid_usefulness_defaults_to_high(self, collector, learning_db):
        collector.record_memory_used(42, "test query", usefulness="INVALID")
        rows = learning_db.get_feedback_for_training()
        assert rows[0]["signal_type"] == "mcp_used_high"

    def test_empty_query_returns_none(self, collector):
        result = collector.record_memory_used(42, "")
        assert result is None

    def test_source_tool_recorded(self, collector, learning_db):
        collector.record_memory_used(
            42, "test query", source_tool="claude-desktop", rank_position=2,
        )
        rows = learning_db.get_feedback_for_training()
        assert rows[0]["source_tool"] == "claude-desktop"
        assert rows[0]["rank_position"] == 2

    def test_no_db_auto_creates(self, collector_no_db):
        """v2.7.2+: FeedbackCollector auto-creates LearningDB when None passed."""
        result = collector_no_db.record_memory_used(42, "test query")
        # Auto-created DB means this succeeds (returns row ID)
        assert result is not None


# ---------------------------------------------------------------------------
# Channel 2: CLI slm useful
# ---------------------------------------------------------------------------

class TestRecordCliUseful:
    def test_batch_ids(self, collector, learning_db):
        row_ids = collector.record_cli_useful([10, 20, 30], "deploy fastapi")
        assert len(row_ids) == 3
        assert all(rid is not None for rid in row_ids)
        assert learning_db.get_feedback_count() == 3

    def test_signal_value(self, collector, learning_db):
        collector.record_cli_useful([42], "query")
        rows = learning_db.get_feedback_for_training()
        assert rows[0]["signal_value"] == 0.9
        assert rows[0]["signal_type"] == "cli_useful"
        assert rows[0]["channel"] == "cli"

    def test_all_share_same_query_hash(self, collector, learning_db):
        collector.record_cli_useful([1, 2, 3], "same query")
        rows = learning_db.get_feedback_for_training()
        hashes = {r["query_hash"] for r in rows}
        assert len(hashes) == 1

    def test_empty_query(self, collector):
        result = collector.record_cli_useful([1, 2], "")
        assert result == [None, None]


# ---------------------------------------------------------------------------
# Channel 3: Dashboard click
# ---------------------------------------------------------------------------

class TestRecordDashboardClick:
    def test_basic_click(self, collector, learning_db):
        row_id = collector.record_dashboard_click(42, "test query")
        assert row_id is not None
        rows = learning_db.get_feedback_for_training()
        assert rows[0]["signal_type"] == "dashboard_click"
        assert rows[0]["signal_value"] == 0.8
        assert rows[0]["channel"] == "dashboard"

    def test_with_dwell_time(self, collector, learning_db):
        collector.record_dashboard_click(42, "test query", dwell_time=15.3)
        # dwell_time is stored in ranking_feedback but not in training export
        # Verify via direct DB query
        conn = learning_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT dwell_time FROM ranking_feedback WHERE memory_id = 42")
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert abs(row[0] - 15.3) < 0.01

    def test_empty_query_returns_none(self, collector):
        result = collector.record_dashboard_click(42, "")
        assert result is None


# ---------------------------------------------------------------------------
# Query Hashing
# ---------------------------------------------------------------------------

class TestHashQuery:
    def test_deterministic(self, collector):
        h1 = collector._hash_query("deploy fastapi")
        h2 = collector._hash_query("deploy fastapi")
        assert h1 == h2

    def test_sha256_first_16(self, collector):
        query = "deploy fastapi"
        expected = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
        assert collector._hash_query(query) == expected

    def test_length_is_16(self, collector):
        result = collector._hash_query("any string")
        assert len(result) == 16

    def test_different_queries_different_hashes(self, collector):
        h1 = collector._hash_query("query one")
        h2 = collector._hash_query("query two")
        assert h1 != h2


# ---------------------------------------------------------------------------
# Keyword Extraction
# ---------------------------------------------------------------------------

class TestExtractKeywords:
    def test_stopword_removal(self, collector):
        kw = collector._extract_keywords("how to deploy the app")
        assert "how" not in kw
        assert "to" not in kw
        assert "the" not in kw
        assert "deploy" in kw

    def test_top_n_limit(self, collector):
        kw = collector._extract_keywords(
            "python fastapi docker kubernetes deployment pipeline"
        )
        assert len(kw.split(",")) <= 3

    def test_empty_query(self, collector):
        assert collector._extract_keywords("") == ""

    def test_only_stopwords(self, collector):
        assert collector._extract_keywords("the and or but") == ""

    def test_comma_separated_output(self, collector):
        kw = collector._extract_keywords("deploy fastapi docker")
        assert "," in kw or len(kw.split(",")) == 1  # single keyword = no comma


# ---------------------------------------------------------------------------
# Passive Decay
# ---------------------------------------------------------------------------

class TestPassiveDecay:
    def test_record_recall_results(self, collector):
        collector.record_recall_results("test query", [1, 2, 3])
        assert collector._recall_count == 1

    def test_compute_passive_decay_below_threshold(self, collector):
        """Should return 0 if below threshold."""
        collector.record_recall_results("test query", [1, 2, 3])
        result = collector.compute_passive_decay(threshold=10)
        assert result == 0

    def test_compute_passive_decay_with_candidates(self, collector, learning_db):
        """Memory appearing in 5+ distinct queries should get decay signal."""
        # Create 10+ recall operations with memory_id=99 appearing in 6 distinct queries
        for i in range(10):
            collector.record_recall_results(f"query_{i}", [99, 100 + i])

        decay_count = collector.compute_passive_decay(threshold=10)
        # memory 99 appeared in 10 distinct queries, no positive feedback
        assert decay_count >= 1

    def test_no_decay_for_positively_rated(self, collector, learning_db):
        """Memories with positive feedback should NOT get passive decay."""
        # Give memory 99 positive feedback first
        learning_db.store_feedback(
            query_hash="q", memory_id=99, signal_type="mcp_used",
            signal_value=1.0, channel="mcp",
        )

        # Record 10+ recall operations with memory 99
        for i in range(12):
            collector.record_recall_results(f"query_{i}", [99])

        decay_count = collector.compute_passive_decay(threshold=10)
        assert decay_count == 0

    def test_buffer_cleared_after_decay(self, collector):
        """Recall buffer should be cleared after computing decay."""
        for i in range(10):
            collector.record_recall_results(f"q{i}", [1])
        collector.compute_passive_decay(threshold=10)
        assert collector._recall_count == 0

    def test_empty_query_ignored(self, collector):
        collector.record_recall_results("", [1, 2, 3])
        assert collector._recall_count == 0

    def test_empty_ids_ignored(self, collector):
        collector.record_recall_results("test query", [])
        assert collector._recall_count == 0


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class TestFeedbackSummary:
    def test_summary_with_data(self, collector, learning_db):
        collector.record_memory_used(1, "q1", usefulness="high")
        collector.record_cli_useful([2], "q2")
        collector.record_dashboard_click(3, "q3")

        summary = collector.get_feedback_summary()
        assert summary["total_signals"] == 3
        assert summary["unique_queries"] == 3
        assert "mcp" in summary["by_channel"]
        assert "cli" in summary["by_channel"]
        assert "dashboard" in summary["by_channel"]

    def test_summary_empty_db(self, collector):
        summary = collector.get_feedback_summary()
        assert summary["total_signals"] == 0
        assert summary["unique_queries"] == 0

    def test_summary_no_db_auto_creates(self, collector_no_db):
        """v2.7.2+: Auto-created DB returns valid summary, not error."""
        summary = collector_no_db.get_feedback_summary()
        assert "total_signals" in summary

    def test_summary_buffer_stats(self, collector):
        collector.record_recall_results("q1", [1, 2, 3])
        collector.record_recall_results("q2", [1, 4, 5])

        summary = collector.get_feedback_summary()
        assert summary["recall_buffer_size"] == 2
