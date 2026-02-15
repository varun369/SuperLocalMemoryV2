#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Tests for SourceQualityScorer (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
"""

import sqlite3
from pathlib import Path

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
def memory_db(tmp_path):
    """Create a minimal memory.db with created_by column."""
    db_path = tmp_path / "memory.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            summary TEXT,
            project_path TEXT,
            project_name TEXT,
            tags TEXT DEFAULT '[]',
            category TEXT,
            parent_id INTEGER,
            tree_path TEXT DEFAULT '/',
            depth INTEGER DEFAULT 0,
            memory_type TEXT DEFAULT 'session',
            importance INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            content_hash TEXT,
            cluster_id INTEGER,
            profile TEXT DEFAULT 'default',
            created_by TEXT,
            source_protocol TEXT,
            trust_score REAL DEFAULT 1.0
        )
    ''')
    conn.commit()
    conn.close()
    return db_path


def _insert_memories(db_path, memories):
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    for m in memories:
        cursor.execute('''
            INSERT INTO memories (content, created_by, source_protocol)
            VALUES (?, ?, ?)
        ''', (
            m.get('content', 'test'),
            m.get('created_by'),
            m.get('source_protocol'),
        ))
    conn.commit()
    conn.close()


@pytest.fixture
def scorer(memory_db, learning_db):
    from src.learning.source_quality_scorer import SourceQualityScorer
    return SourceQualityScorer(
        memory_db_path=memory_db,
        learning_db=learning_db,
    )


# ---------------------------------------------------------------------------
# Beta-Binomial Calculation
# ---------------------------------------------------------------------------

class TestBetaBinomialScore:
    def test_zero_data(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        # (1 + 0) / (2 + 0) = 0.5
        assert abs(SourceQualityScorer._beta_binomial_score(0, 0) - 0.5) < 0.001

    def test_perfect_score(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        # (1 + 10) / (2 + 10) = 11/12 ~ 0.917
        score = SourceQualityScorer._beta_binomial_score(10, 10)
        assert abs(score - 11.0 / 12.0) < 0.001

    def test_poor_score(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        # (1 + 1) / (2 + 10) = 2/12 ~ 0.167
        score = SourceQualityScorer._beta_binomial_score(1, 10)
        assert abs(score - 2.0 / 12.0) < 0.001

    def test_even_split(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        # (1 + 5) / (2 + 10) = 6/12 = 0.5
        score = SourceQualityScorer._beta_binomial_score(5, 10)
        assert abs(score - 0.5) < 0.001

    def test_large_numbers_convergence(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        # (1 + 80) / (2 + 100) = 81/102 ~ 0.794
        score = SourceQualityScorer._beta_binomial_score(80, 100)
        assert abs(score - 81.0 / 102.0) < 0.001

    def test_score_bounded(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        # Should always be in [0.0, 1.0]
        for pos, total in [(0, 0), (100, 100), (0, 100), (100, 0)]:
            score = SourceQualityScorer._beta_binomial_score(pos, total)
            assert 0.0 <= score <= 1.0, f"pos={pos}, total={total}, score={score}"


# ---------------------------------------------------------------------------
# compute_source_scores
# ---------------------------------------------------------------------------

class TestComputeSourceScores:
    def test_empty_db(self, scorer):
        scores = scorer.compute_source_scores()
        assert scores == {}

    def test_with_memories(self, scorer, memory_db, learning_db):
        """Sources with memories should get computed scores."""
        _insert_memories(memory_db, [
            {"content": "test 1", "created_by": "mcp:claude"},
            {"content": "test 2", "created_by": "mcp:claude"},
            {"content": "test 3", "created_by": "mcp:cursor"},
            {"content": "test 4", "created_by": "cli:terminal"},
        ])
        scores = scorer.compute_source_scores()
        assert len(scores) >= 3
        assert "mcp:claude" in scores
        assert "mcp:cursor" in scores
        assert "cli:terminal" in scores

    def test_with_positive_feedback(self, scorer, memory_db, learning_db):
        """Sources with positive feedback should get higher scores."""
        _insert_memories(memory_db, [
            {"content": "test 1", "created_by": "good_source"},
            {"content": "test 2", "created_by": "good_source"},
            {"content": "test 3", "created_by": "bad_source"},
            {"content": "test 4", "created_by": "bad_source"},
        ])

        # Add positive feedback for good_source memories (id 1, 2)
        learning_db.store_feedback(
            query_hash="q1", memory_id=1,
            signal_type="mcp_used", signal_value=1.0, channel="mcp",
        )
        learning_db.store_feedback(
            query_hash="q2", memory_id=2,
            signal_type="mcp_used", signal_value=1.0, channel="mcp",
        )

        scores = scorer.compute_source_scores()
        assert scores["good_source"] > scores["bad_source"]

    def test_stores_in_learning_db(self, scorer, memory_db, learning_db):
        """Computed scores should be persisted in learning.db."""
        _insert_memories(memory_db, [
            {"content": "test", "created_by": "mcp:test"},
        ])
        scorer.compute_source_scores()

        db_scores = learning_db.get_source_scores()
        assert "mcp:test" in db_scores

    def test_no_created_by_column(self, tmp_path, learning_db):
        """Memory DB without created_by should group all as 'unknown'."""
        db_path = tmp_path / "old_memory.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY, content TEXT
            )
        ''')
        cursor.execute("INSERT INTO memories (content) VALUES ('test')")
        conn.commit()
        conn.close()

        from src.learning.source_quality_scorer import SourceQualityScorer
        s = SourceQualityScorer(memory_db_path=db_path, learning_db=learning_db)
        scores = s.compute_source_scores()
        assert "unknown" in scores


# ---------------------------------------------------------------------------
# get_source_boost
# ---------------------------------------------------------------------------

class TestGetSourceBoost:
    def test_known_source(self, scorer):
        """Known source from cache should return its score."""
        scorer._cached_scores = {"mcp:claude": 0.8, "cli:terminal": 0.4}

        memory = {"created_by": "mcp:claude"}
        assert scorer.get_source_boost(memory) == 0.8

    def test_unknown_source_returns_default(self, scorer):
        """Unknown source should return DEFAULT_QUALITY_SCORE (0.5)."""
        from src.learning.source_quality_scorer import DEFAULT_QUALITY_SCORE
        scorer._cached_scores = {"mcp:claude": 0.8}

        memory = {"created_by": "unknown_tool"}
        assert scorer.get_source_boost(memory) == DEFAULT_QUALITY_SCORE

    def test_no_source_info(self, scorer):
        """Memory with no created_by should return default."""
        from src.learning.source_quality_scorer import DEFAULT_QUALITY_SCORE
        memory = {"content": "no source info"}
        assert scorer.get_source_boost(memory) == DEFAULT_QUALITY_SCORE

    def test_explicit_scores_override_cache(self, scorer):
        """Passing source_scores directly should override cache."""
        scorer._cached_scores = {"mcp:claude": 0.8}
        override = {"mcp:claude": 0.3}

        memory = {"created_by": "mcp:claude"}
        assert scorer.get_source_boost(memory, source_scores=override) == 0.3

    def test_source_protocol_fallback(self, scorer):
        """If created_by is None, fall back to source_protocol."""
        scorer._cached_scores = {"mcp": 0.7}
        memory = {"created_by": None, "source_protocol": "mcp"}
        assert scorer.get_source_boost(memory) == 0.7

    def test_user_source(self, scorer):
        """created_by='user' is the default from provenance_tracker."""
        scorer._cached_scores = {"user": 0.6}
        memory = {"created_by": "user"}
        assert scorer.get_source_boost(memory) == 0.6


# ---------------------------------------------------------------------------
# extract_source_id
# ---------------------------------------------------------------------------

class TestExtractSourceId:
    def test_created_by_primary(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        memory = {"created_by": "mcp:claude-desktop", "source_protocol": "mcp"}
        assert SourceQualityScorer._extract_source_id(memory) == "mcp:claude-desktop"

    def test_source_protocol_fallback(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        memory = {"created_by": None, "source_protocol": "cli"}
        assert SourceQualityScorer._extract_source_id(memory) == "cli"

    def test_user_default(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        memory = {"created_by": "user"}
        assert SourceQualityScorer._extract_source_id(memory) == "user"

    def test_no_source_returns_none(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        memory = {"content": "no source info"}
        assert SourceQualityScorer._extract_source_id(memory) is None

    def test_empty_created_by(self):
        from src.learning.source_quality_scorer import SourceQualityScorer
        memory = {"created_by": ""}
        # Empty string should fall through to source_protocol
        result = SourceQualityScorer._extract_source_id(memory)
        assert result is None


# ---------------------------------------------------------------------------
# Refresh & Summary
# ---------------------------------------------------------------------------

class TestRefreshAndSummary:
    def test_refresh(self, scorer, memory_db):
        _insert_memories(memory_db, [
            {"content": "test", "created_by": "mcp:test"},
        ])
        scores = scorer.refresh()
        assert isinstance(scores, dict)

    def test_get_source_summary_empty(self, scorer):
        summary = scorer.get_source_summary()
        assert "No source quality data" in summary

    def test_get_source_summary_with_data(self, scorer, memory_db, learning_db):
        _insert_memories(memory_db, [
            {"content": "test", "created_by": "mcp:claude"},
        ])
        scorer.compute_source_scores()
        summary = scorer.get_source_summary()
        assert "mcp:claude" in summary

    def test_get_all_scores_empty(self, scorer):
        all_scores = scorer.get_all_scores()
        assert all_scores == {}

    def test_get_all_scores_with_data(self, scorer, memory_db, learning_db):
        _insert_memories(memory_db, [
            {"content": "test", "created_by": "mcp:test"},
        ])
        scorer.compute_source_scores()
        all_scores = scorer.get_all_scores()
        assert "mcp:test" in all_scores
        assert "quality_score" in all_scores["mcp:test"]
        assert "positive_signals" in all_scores["mcp:test"]
        assert "total_memories" in all_scores["mcp:test"]


# ---------------------------------------------------------------------------
# No Learning DB
# ---------------------------------------------------------------------------

class TestNoLearningDb:
    def test_scorer_without_learning_db(self, memory_db):
        from src.learning.source_quality_scorer import SourceQualityScorer
        scorer = SourceQualityScorer(
            memory_db_path=memory_db,
            learning_db=None,
        )
        # Should not crash
        scores = scorer.compute_source_scores()
        assert isinstance(scores, dict)

    def test_boost_without_cache(self, memory_db):
        from src.learning.source_quality_scorer import (
            SourceQualityScorer, DEFAULT_QUALITY_SCORE,
        )
        scorer = SourceQualityScorer(
            memory_db_path=memory_db,
            learning_db=None,
        )
        memory = {"created_by": "mcp:anything"}
        assert scorer.get_source_boost(memory) == DEFAULT_QUALITY_SCORE
