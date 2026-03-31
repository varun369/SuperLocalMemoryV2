# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3

"""Tests for forgetting filter — Phase A.

TDD: 3 tests covering archive removal, cold score reduction,
and active passthrough.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from superlocalmemory.core.config import ForgettingConfig
from superlocalmemory.retrieval.forgetting_filter import (
    ForgettingFilter,
    register_forgetting_filter,
)


@pytest.fixture
def config() -> ForgettingConfig:
    return ForgettingConfig()


@pytest.fixture
def disabled_config() -> ForgettingConfig:
    return ForgettingConfig(enabled=False)


def _make_mock_db(retention_data: dict[str, dict]) -> MagicMock:
    """Create a mock DB that returns retention data for batch_get_retention."""
    db = MagicMock()

    def batch_get_retention(fact_ids: list[str], profile_id: str) -> list[dict]:
        results = []
        for fid in fact_ids:
            if fid in retention_data:
                results.append(retention_data[fid])
        return results

    db.batch_get_retention = MagicMock(side_effect=batch_get_retention)
    return db


# ---- Test 13: Filter removes archived and forgotten facts ----

def test_filter_removes_archived(config: ForgettingConfig) -> None:
    """Archive-zone and forgotten-zone facts should be excluded from results."""
    retention_data = {
        "fact_active": {"fact_id": "fact_active", "retention_score": 0.9, "lifecycle_zone": "active"},
        "fact_archive": {"fact_id": "fact_archive", "retention_score": 0.1, "lifecycle_zone": "archive"},
        "fact_forgotten": {"fact_id": "fact_forgotten", "retention_score": 0.01, "lifecycle_zone": "forgotten"},
    }
    db = _make_mock_db(retention_data)
    filt = ForgettingFilter(db, config)

    all_results = {
        "semantic": [("fact_active", 0.8), ("fact_archive", 0.7), ("fact_forgotten", 0.6)],
    }

    filtered = filt.filter(all_results, "default", None)

    fact_ids_in_result = [fid for fid, _ in filtered["semantic"]]
    assert "fact_active" in fact_ids_in_result
    assert "fact_archive" not in fact_ids_in_result
    assert "fact_forgotten" not in fact_ids_in_result


# ---- Test 14: Filter reduces cold scores ----

def test_filter_reduces_cold_scores(config: ForgettingConfig) -> None:
    """Cold-zone facts should have score * 0.3."""
    retention_data = {
        "fact_cold": {"fact_id": "fact_cold", "retention_score": 0.4, "lifecycle_zone": "cold"},
    }
    db = _make_mock_db(retention_data)
    filt = ForgettingFilter(db, config)

    all_results = {
        "semantic": [("fact_cold", 1.0)],
    }

    filtered = filt.filter(all_results, "default", None)

    # Cold zone weight = 0.3, so score should be 1.0 * 0.3 = 0.3
    assert len(filtered["semantic"]) == 1
    fid, score = filtered["semantic"][0]
    assert fid == "fact_cold"
    assert score == pytest.approx(0.3, abs=0.01)


# ---- Test 15: Filter passes active unchanged ----

def test_filter_passes_active_unchanged(config: ForgettingConfig) -> None:
    """Active-zone facts should keep their original score (weight=1.0)."""
    retention_data = {
        "fact_active": {"fact_id": "fact_active", "retention_score": 0.9, "lifecycle_zone": "active"},
    }
    db = _make_mock_db(retention_data)
    filt = ForgettingFilter(db, config)

    all_results = {
        "semantic": [("fact_active", 0.85)],
    }

    filtered = filt.filter(all_results, "default", None)

    assert len(filtered["semantic"]) == 1
    fid, score = filtered["semantic"][0]
    assert fid == "fact_active"
    assert score == pytest.approx(0.85, abs=0.01)


# ---- HR-06: Filter returns unchanged when disabled ----

def test_filter_disabled_returns_unchanged(disabled_config: ForgettingConfig) -> None:
    """When config.enabled=False, filter returns results unchanged."""
    db = MagicMock()
    filt = ForgettingFilter(db, disabled_config)

    all_results = {
        "semantic": [("fact1", 0.9), ("fact2", 0.7)],
        "bm25": [("fact3", 0.6)],
    }

    filtered = filt.filter(all_results, "default", None)

    assert filtered == all_results
    # DB should NOT be called when disabled
    db.batch_get_retention.assert_not_called()


# ---- Coverage: Filter with empty results ----

def test_filter_empty_results(config: ForgettingConfig) -> None:
    """Empty results should be returned unchanged."""
    db = MagicMock()
    filt = ForgettingFilter(db, config)

    empty_results: dict[str, list[tuple[str, float]]] = {}
    filtered = filt.filter(empty_results, "default", None)
    assert filtered == {}


# ---- Coverage: Filter with no retention data (new memories) ----

def test_filter_no_retention_data_keeps_facts(config: ForgettingConfig) -> None:
    """Facts without retention data should be kept as-is (new memories)."""
    db = _make_mock_db({})  # No retention data at all
    filt = ForgettingFilter(db, config)

    all_results = {
        "semantic": [("new_fact", 0.9)],
    }
    filtered = filt.filter(all_results, "default", None)
    assert filtered["semantic"] == [("new_fact", 0.9)]


# ---- Coverage: register_forgetting_filter ----

def test_register_forgetting_filter(config: ForgettingConfig) -> None:
    """register_forgetting_filter should register with the registry."""
    from unittest.mock import MagicMock
    registry = MagicMock()
    db = MagicMock()

    register_forgetting_filter(registry, db, config)
    registry.register_filter.assert_called_once()


def test_register_forgetting_filter_disabled(disabled_config: ForgettingConfig) -> None:
    """register_forgetting_filter with disabled config should not register."""
    registry = MagicMock()
    db = MagicMock()

    register_forgetting_filter(registry, db, disabled_config)
    registry.register_filter.assert_not_called()
