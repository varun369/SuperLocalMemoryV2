#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Tests for AdaptiveRanker (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
"""

import pytest


# Detect optional dependencies at import time
try:
    import lightgbm
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


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
def ranker(learning_db):
    from src.learning.adaptive_ranker import AdaptiveRanker
    return AdaptiveRanker(learning_db=learning_db)


def _make_result(memory_id, score=0.5, content="test memory", importance=5,
                 project_name=None, created_at="2026-02-16 10:00:00",
                 access_count=0, match_type="keyword"):
    """Helper to build a search result dict."""
    return {
        "id": memory_id,
        "content": content,
        "score": score,
        "match_type": match_type,
        "importance": importance,
        "created_at": created_at,
        "access_count": access_count,
        "project_name": project_name,
        "tags": [],
        "created_by": None,
    }


# ---------------------------------------------------------------------------
# Phase Detection
# ---------------------------------------------------------------------------

class TestGetPhase:
    def test_baseline_with_zero_signals(self, ranker):
        assert ranker.get_phase() == "baseline"

    def test_baseline_with_few_signals(self, ranker, learning_db):
        """Less than 20 signals should stay in baseline."""
        for i in range(10):
            learning_db.store_feedback(
                query_hash=f"q{i}",
                memory_id=i,
                signal_type="mcp_used",
            )
        assert ranker.get_phase() == "baseline"

    def test_rule_based_at_20_signals(self, ranker, learning_db):
        """20+ signals should enter rule_based phase."""
        for i in range(25):
            learning_db.store_feedback(
                query_hash=f"q{i}",
                memory_id=i,
                signal_type="mcp_used",
            )
        assert ranker.get_phase() == "rule_based"

    @pytest.mark.skipif(not HAS_LIGHTGBM or not HAS_NUMPY,
                        reason="LightGBM/NumPy required for ML phase")
    def test_ml_model_at_200_signals(self, ranker, learning_db):
        """200+ signals across 50+ queries should trigger ml_model."""
        for i in range(250):
            learning_db.store_feedback(
                query_hash=f"q{i % 60}",  # 60 unique queries
                memory_id=i,
                signal_type="mcp_used",
            )
        assert ranker.get_phase() == "ml_model"

    def test_ml_model_requires_enough_unique_queries(self, ranker, learning_db):
        """200+ signals but only 10 unique queries should stay rule_based."""
        for i in range(250):
            learning_db.store_feedback(
                query_hash=f"q{i % 10}",  # Only 10 unique queries
                memory_id=i,
                signal_type="mcp_used",
            )
        # Even with LightGBM available, not enough unique queries
        phase = ranker.get_phase()
        assert phase in ("rule_based", "ml_model")
        if HAS_LIGHTGBM and HAS_NUMPY:
            assert phase == "rule_based"  # 10 < 50 unique queries

    def test_no_learning_db_returns_baseline(self):
        from src.learning.adaptive_ranker import AdaptiveRanker
        ranker = AdaptiveRanker(learning_db=None)
        # Force no lazy init
        ranker._learning_db = None
        assert ranker.get_phase() == "baseline"


# ---------------------------------------------------------------------------
# Phase Info
# ---------------------------------------------------------------------------

class TestGetPhaseInfo:
    def test_phase_info_structure(self, ranker):
        info = ranker.get_phase_info()
        assert "phase" in info
        assert "feedback_count" in info
        assert "unique_queries" in info
        assert "thresholds" in info
        assert "model_loaded" in info
        assert "lightgbm_available" in info
        assert "numpy_available" in info

    def test_phase_info_values(self, ranker):
        info = ranker.get_phase_info()
        assert info["phase"] == "baseline"
        assert info["feedback_count"] == 0
        assert info["unique_queries"] == 0
        assert info["model_loaded"] is False


# ---------------------------------------------------------------------------
# Rerank Routing
# ---------------------------------------------------------------------------

class TestRerank:
    def test_empty_results(self, ranker):
        result = ranker.rerank([], "query")
        assert result == []

    def test_single_result_baseline(self, ranker):
        """Single result should get baseline phase annotation."""
        results = [_make_result(1, score=0.8)]
        reranked = ranker.rerank(results, "test query")
        assert len(reranked) == 1
        assert reranked[0]["ranking_phase"] == "baseline"
        assert reranked[0]["base_score"] == 0.8

    def test_baseline_preserves_order(self, ranker):
        """In baseline phase, original order should be preserved."""
        results = [
            _make_result(1, score=0.9),
            _make_result(2, score=0.5),
            _make_result(3, score=0.3),
        ]
        reranked = ranker.rerank(results, "test query")
        # All should be baseline
        for r in reranked:
            assert r["ranking_phase"] == "baseline"
        # Order preserved (no re-sorting in baseline)
        assert reranked[0]["id"] == 1
        assert reranked[1]["id"] == 2
        assert reranked[2]["id"] == 3

    def test_base_score_preserved(self, ranker, learning_db):
        """base_score should always contain the original score."""
        # Add enough feedback for rule_based
        for i in range(25):
            learning_db.store_feedback(
                query_hash=f"q{i}", memory_id=i, signal_type="mcp_used",
            )

        results = [
            _make_result(1, score=0.8),
            _make_result(2, score=0.5),
        ]
        reranked = ranker.rerank(results, "test query")
        for r in reranked:
            assert "base_score" in r


# ---------------------------------------------------------------------------
# Rule-Based Re-ranking
# ---------------------------------------------------------------------------

class TestRuleBasedReranking:
    def test_boost_applied(self, ranker, learning_db):
        """Rule-based should modify scores based on features."""
        for i in range(25):
            learning_db.store_feedback(
                query_hash=f"q{i}", memory_id=i, signal_type="mcp_used",
            )

        results = [
            _make_result(1, score=0.5, importance=9, access_count=8),
            _make_result(2, score=0.5, importance=2, access_count=0),
        ]
        reranked = ranker.rerank(results, "test query")

        # Both should be rule_based
        assert all(r["ranking_phase"] == "rule_based" for r in reranked)

        # High importance + access should get higher score
        high_imp = next(r for r in reranked if r["id"] == 1)
        low_imp = next(r for r in reranked if r["id"] == 2)
        assert high_imp["score"] > low_imp["score"]

    def test_project_match_boost(self, ranker, learning_db):
        """Memory matching current project should be boosted."""
        for i in range(25):
            learning_db.store_feedback(
                query_hash=f"q{i}", memory_id=i, signal_type="mcp_used",
            )

        results = [
            _make_result(1, score=0.5, project_name="SLM"),
            _make_result(2, score=0.5, project_name="OTHER"),
        ]
        context = {"current_project": "SLM"}
        reranked = ranker.rerank(results, "test query", context=context)

        slm_result = next(r for r in reranked if r["id"] == 1)
        other_result = next(r for r in reranked if r["id"] == 2)
        assert slm_result["score"] > other_result["score"]

    def test_results_resorted(self, ranker, learning_db):
        """Results should be re-sorted by boosted score."""
        for i in range(25):
            learning_db.store_feedback(
                query_hash=f"q{i}", memory_id=i, signal_type="mcp_used",
            )

        # Second result has much higher importance
        results = [
            _make_result(1, score=0.5, importance=2),
            _make_result(2, score=0.5, importance=10, access_count=10),
        ]
        reranked = ranker.rerank(results, "test query")
        # Higher importance should float to top
        assert reranked[0]["id"] == 2


# ---------------------------------------------------------------------------
# ML Training (skipped if LightGBM not available)
# ---------------------------------------------------------------------------

class TestTraining:
    @pytest.mark.skipif(not HAS_LIGHTGBM or not HAS_NUMPY,
                        reason="LightGBM/NumPy required")
    def test_train_insufficient_data(self, ranker, learning_db):
        """Training should return None with insufficient data."""
        result = ranker.train()
        assert result is None

    def test_train_without_lightgbm(self, ranker):
        """Should gracefully handle missing LightGBM."""
        from src.learning import adaptive_ranker as ar_module
        original = ar_module.HAS_LIGHTGBM
        ar_module.HAS_LIGHTGBM = False
        try:
            result = ranker.train()
            assert result is None
        finally:
            ar_module.HAS_LIGHTGBM = original


# ---------------------------------------------------------------------------
# Model Loading Fallback
# ---------------------------------------------------------------------------

class TestModelLoading:
    def test_load_nonexistent_model(self, ranker):
        """Loading a model that doesn't exist should return None."""
        model = ranker._load_model()
        assert model is None

    def test_load_attempt_cached(self, ranker):
        """After first failed load, _model_load_attempted should be True."""
        ranker._load_model()
        assert ranker._model_load_attempted is True

    def test_second_load_returns_cached_none(self, ranker):
        """Second load attempt should return None immediately (cached failure)."""
        ranker._load_model()
        result = ranker._load_model()
        assert result is None

    def test_reload_model_resets_flag(self, ranker):
        """reload_model should reset the _model_load_attempted flag."""
        ranker._load_model()
        assert ranker._model_load_attempted is True
        ranker.reload_model()
        # After reload, the flag should have been reset and tried again
        # (and failed again since no model file exists)
        assert ranker._model is None


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

class TestModuleLevel:
    def test_get_phase_function(self):
        from src.learning.adaptive_ranker import get_phase
        phase = get_phase()
        assert phase in ("baseline", "rule_based", "ml_model")
