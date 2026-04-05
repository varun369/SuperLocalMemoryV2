# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3

"""Tests for QuantizationAwareSearch (three-tier mixed-precision).

TDD sequence (LLD Section 6):
  15. test_mixed_precision_merges
  16. test_deduplication
  17. test_polar_penalty_applied
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from superlocalmemory.core.config import QuantizationConfig
from superlocalmemory.retrieval.quantization_aware_search import (
    QuantizationAwareSearch,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _random_vec(d: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(d)
    return v / np.linalg.norm(v)


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Mock VectorStore with search() and search_int8()."""
    vs = MagicMock()
    vs.search.return_value = [("f1", 0.95), ("f2", 0.80)]
    vs.search_int8.return_value = [("f3", 0.85)]
    vs.available = True
    return vs


@pytest.fixture
def mock_quantized_store() -> MagicMock:
    """Mock QuantizedEmbeddingStore with search()."""
    qs = MagicMock()
    qs.search.return_value = [("f4", 0.70), ("f5", 0.60)]
    return qs


@pytest.fixture
def config() -> QuantizationConfig:
    return QuantizationConfig(polar_search_penalty=0.95)


@pytest.fixture
def searcher(
    mock_vector_store: MagicMock,
    mock_quantized_store: MagicMock,
    config: QuantizationConfig,
) -> QuantizationAwareSearch:
    return QuantizationAwareSearch(mock_vector_store, mock_quantized_store, config)


# ---------------------------------------------------------------------------
# 15. Mixed precision merges results from all three tiers
# ---------------------------------------------------------------------------


def test_mixed_precision_merges(
    searcher: QuantizationAwareSearch,
    mock_vector_store: MagicMock,
    mock_quantized_store: MagicMock,
) -> None:
    """Results from float32 + int8 + polar tiers are merged."""
    query = _random_vec(768, seed=1)
    results = searcher.search(query, "p1", top_k=50)

    # Should have results from all three tiers
    fact_ids = {r[0] for r in results}
    assert "f1" in fact_ids  # float32
    assert "f3" in fact_ids  # int8
    assert "f4" in fact_ids  # polar

    # Verify all tier methods were called
    mock_vector_store.search.assert_called_once()
    mock_vector_store.search_int8.assert_called_once()
    mock_quantized_store.search.assert_called_once()


# ---------------------------------------------------------------------------
# 16. Deduplication keeps highest score
# ---------------------------------------------------------------------------


def test_deduplication(
    mock_vector_store: MagicMock,
    mock_quantized_store: MagicMock,
    config: QuantizationConfig,
) -> None:
    """Duplicate fact_ids across tiers are deduped by max score."""
    # f1 appears in float32 (0.95) AND polar (0.90 * 0.95 penalty = 0.855)
    mock_vector_store.search.return_value = [("f1", 0.95)]
    mock_vector_store.search_int8.return_value = []
    mock_quantized_store.search.return_value = [("f1", 0.90)]

    searcher = QuantizationAwareSearch(mock_vector_store, mock_quantized_store, config)
    query = _random_vec(768, seed=2)
    results = searcher.search(query, "p1", top_k=50)

    # f1 should appear only once
    f1_results = [(fid, s) for fid, s in results if fid == "f1"]
    assert len(f1_results) == 1
    # Should keep the higher score (float32: 0.95)
    assert f1_results[0][1] == pytest.approx(0.95, abs=0.01)


# ---------------------------------------------------------------------------
# 17. Polar penalty applied
# ---------------------------------------------------------------------------


def test_polar_penalty_applied(
    mock_vector_store: MagicMock,
    mock_quantized_store: MagicMock,
) -> None:
    """Polar results are penalized by config.polar_search_penalty."""
    mock_vector_store.search.return_value = []
    mock_vector_store.search_int8.return_value = []
    mock_quantized_store.search.return_value = [("f-polar", 1.0)]

    config = QuantizationConfig(polar_search_penalty=0.95)
    searcher = QuantizationAwareSearch(mock_vector_store, mock_quantized_store, config)
    query = _random_vec(768, seed=3)
    results = searcher.search(query, "p1", top_k=50)

    # Polar score of 1.0 * 0.95 penalty = 0.95
    assert len(results) == 1
    assert results[0][0] == "f-polar"
    assert results[0][1] == pytest.approx(0.95, abs=0.001)


# ---------------------------------------------------------------------------
# Edge case: int8 penalty
# ---------------------------------------------------------------------------


def test_int8_penalty_applied(
    mock_vector_store: MagicMock,
    mock_quantized_store: MagicMock,
    config: QuantizationConfig,
) -> None:
    """Int8 results are penalized by 0.98 factor."""
    mock_vector_store.search.return_value = []
    mock_vector_store.search_int8.return_value = [("f-int8", 1.0)]
    mock_quantized_store.search.return_value = []

    searcher = QuantizationAwareSearch(mock_vector_store, mock_quantized_store, config)
    query = _random_vec(768, seed=4)
    results = searcher.search(query, "p1", top_k=50)

    assert len(results) == 1
    assert results[0][0] == "f-int8"
    assert results[0][1] == pytest.approx(0.98, abs=0.001)


# ---------------------------------------------------------------------------
# Error path coverage: each tier handles exceptions gracefully
# ---------------------------------------------------------------------------


def test_float32_search_error_handled(
    mock_quantized_store: MagicMock,
    config: QuantizationConfig,
) -> None:
    """Float32 tier exception returns empty, other tiers still work."""
    vs = MagicMock()
    vs.search.side_effect = RuntimeError("float32 exploded")
    vs.search_int8.return_value = [("f-ok", 0.7)]
    mock_quantized_store.search.return_value = []

    searcher = QuantizationAwareSearch(vs, mock_quantized_store, config)
    query = _random_vec(768, seed=5)
    results = searcher.search(query, "p1", top_k=50)

    assert len(results) == 1
    assert results[0][0] == "f-ok"


def test_int8_search_error_handled(
    mock_vector_store: MagicMock,
    mock_quantized_store: MagicMock,
    config: QuantizationConfig,
) -> None:
    """Int8 tier exception returns empty, other tiers still work."""
    mock_vector_store.search_int8.side_effect = RuntimeError("int8 broke")
    mock_quantized_store.search.return_value = []

    searcher = QuantizationAwareSearch(mock_vector_store, mock_quantized_store, config)
    query = _random_vec(768, seed=6)
    results = searcher.search(query, "p1", top_k=50)

    # Float32 results still present
    assert len(results) >= 1


def test_polar_search_error_handled(
    mock_vector_store: MagicMock,
    config: QuantizationConfig,
) -> None:
    """Polar tier exception returns empty, other tiers still work."""
    qs = MagicMock()
    qs.search.side_effect = RuntimeError("polar broke")

    searcher = QuantizationAwareSearch(mock_vector_store, qs, config)
    query = _random_vec(768, seed=7)
    results = searcher.search(query, "p1", top_k=50)

    # Float32 and int8 results still present
    assert len(results) >= 1
