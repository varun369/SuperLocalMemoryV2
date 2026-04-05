# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for OllamaEmbedder — production Ollama embedding provider.

Covers: initialization, availability check, single/batch embed, Fisher
params, normalization, error handling, timeout behavior, and graceful
fallback when Ollama is unreachable.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from superlocalmemory.core.ollama_embedder import OllamaEmbedder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_tags_response(models: list[str]) -> MagicMock:
    """Build a mock httpx response for /api/tags."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "models": [{"name": f"{m}:latest"} for m in models],
    }
    return resp


def _fake_embed_response(vectors: list[list[float]]) -> MagicMock:
    """Build a mock httpx response for /api/embed."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"embeddings": vectors}
    return resp


def _random_vec(dim: int = 768) -> list[float]:
    rng = np.random.default_rng(42)
    return rng.standard_normal(dim).tolist()


# ---------------------------------------------------------------------------
# Initialization & availability
# ---------------------------------------------------------------------------

class TestOllamaEmbedderAvailability:
    """Test Ollama availability detection."""

    def test_available_when_model_present(self) -> None:
        emb = OllamaEmbedder(model="nomic-embed-text")
        with patch("httpx.get", return_value=_fake_tags_response(["nomic-embed-text"])):
            assert emb.is_available is True

    def test_unavailable_when_model_missing(self) -> None:
        emb = OllamaEmbedder(model="nomic-embed-text")
        with patch("httpx.get", return_value=_fake_tags_response(["llama3.2"])):
            assert emb.is_available is False

    def test_unavailable_when_connection_refused(self) -> None:
        emb = OllamaEmbedder(model="nomic-embed-text")
        with patch("httpx.get", side_effect=ConnectionError("refused")):
            assert emb.is_available is False

    def test_unavailable_when_timeout(self) -> None:
        import httpx as _httpx
        emb = OllamaEmbedder(model="nomic-embed-text")
        with patch("httpx.get", side_effect=_httpx.TimeoutException("timeout")):
            assert emb.is_available is False

    def test_availability_cached_after_first_check(self) -> None:
        emb = OllamaEmbedder(model="nomic-embed-text")
        with patch("httpx.get", return_value=_fake_tags_response(["nomic-embed-text"])):
            assert emb.is_available is True
        # Second call should NOT hit httpx again (cached)
        with patch("httpx.get", side_effect=AssertionError("should not be called")):
            assert emb.is_available is True

    def test_dimension_property(self) -> None:
        emb = OllamaEmbedder(dimension=384)
        assert emb.dimension == 384

    def test_model_name_with_tag(self) -> None:
        """Model comparison strips tags: 'nomic-embed-text:latest' matches 'nomic-embed-text'."""
        emb = OllamaEmbedder(model="nomic-embed-text:latest")
        with patch("httpx.get", return_value=_fake_tags_response(["nomic-embed-text"])):
            assert emb.is_available is True


# ---------------------------------------------------------------------------
# Single embed
# ---------------------------------------------------------------------------

class TestOllamaEmbedSingle:
    """Test single text embedding."""

    def test_embed_returns_normalized_vector(self) -> None:
        raw_vec = _random_vec(768)
        emb = OllamaEmbedder(dimension=768)
        with patch("httpx.post", return_value=_fake_embed_response([raw_vec])):
            result = emb.embed("hello world")
        assert result is not None
        assert len(result) == 768
        # Check L2-normalized
        norm = float(np.linalg.norm(result))
        assert abs(norm - 1.0) < 1e-5

    def test_embed_empty_text_raises(self) -> None:
        emb = OllamaEmbedder()
        with pytest.raises(ValueError, match="empty"):
            emb.embed("")

    def test_embed_whitespace_only_raises(self) -> None:
        emb = OllamaEmbedder()
        with pytest.raises(ValueError, match="empty"):
            emb.embed("   ")

    def test_embed_returns_none_on_failure(self) -> None:
        emb = OllamaEmbedder()
        with patch("httpx.post", side_effect=ConnectionError("down")):
            result = emb.embed("test")
        assert result is None

    def test_embed_returns_none_on_http_error(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("500")
        emb = OllamaEmbedder()
        with patch("httpx.post", return_value=mock_resp):
            result = emb.embed("test")
        assert result is None


# ---------------------------------------------------------------------------
# Batch embed
# ---------------------------------------------------------------------------

class TestOllamaEmbedBatch:
    """Test batch embedding."""

    def test_batch_embed_two_texts(self) -> None:
        vecs = [_random_vec(768), _random_vec(768)]
        emb = OllamaEmbedder(dimension=768)
        with patch("httpx.post", return_value=_fake_embed_response(vecs)):
            results = emb.embed_batch(["hello", "world"])
        assert len(results) == 2
        for r in results:
            assert r is not None
            assert len(r) == 768

    def test_batch_embed_empty_raises(self) -> None:
        emb = OllamaEmbedder()
        with pytest.raises(ValueError, match="empty"):
            emb.embed_batch([])

    def test_batch_returns_nones_on_failure(self) -> None:
        emb = OllamaEmbedder()
        with patch("httpx.post", side_effect=ConnectionError("down")):
            results = emb.embed_batch(["a", "b", "c"])
        assert results == [None, None, None]


# ---------------------------------------------------------------------------
# Fisher-Rao parameters
# ---------------------------------------------------------------------------

class TestOllamaFisherParams:
    """Test Fisher-Rao parameter computation."""

    def test_fisher_params_shape(self) -> None:
        emb = OllamaEmbedder(dimension=768)
        vec = _random_vec(768)
        # Normalize first (as would come from embed())
        arr = np.asarray(vec, dtype=np.float32)
        arr = arr / np.linalg.norm(arr)
        mean, var = emb.compute_fisher_params(arr.tolist())
        assert len(mean) == 768
        assert len(var) == 768

    def test_fisher_variance_bounds(self) -> None:
        emb = OllamaEmbedder(dimension=768)
        vec = _random_vec(768)
        arr = np.asarray(vec, dtype=np.float32)
        arr = arr / np.linalg.norm(arr)
        _, var = emb.compute_fisher_params(arr.tolist())
        var_arr = np.asarray(var)
        assert float(np.min(var_arr)) >= 0.05 - 1e-7
        assert float(np.max(var_arr)) <= 2.0 + 1e-7

    def test_fisher_zero_vector(self) -> None:
        emb = OllamaEmbedder(dimension=4)
        mean, var = emb.compute_fisher_params([0.0, 0.0, 0.0, 0.0])
        assert all(m == 0.0 for m in mean)
        assert all(abs(v - 2.0) < 1e-7 for v in var)


# ---------------------------------------------------------------------------
# Unload (no-op)
# ---------------------------------------------------------------------------

class TestOllamaUnload:
    """Unload should be a no-op (Ollama manages its own lifecycle)."""

    def test_unload_does_not_raise(self) -> None:
        emb = OllamaEmbedder()
        emb.unload()  # Should not raise


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

class TestOllamaNormalization:
    """Test L2 normalization correctness."""

    def test_normalize_unit_vector(self) -> None:
        vec = [1.0, 0.0, 0.0]
        result = OllamaEmbedder._normalize(vec)
        assert abs(result[0] - 1.0) < 1e-7
        assert abs(result[1]) < 1e-7

    def test_normalize_zero_vector(self) -> None:
        vec = [0.0, 0.0, 0.0]
        result = OllamaEmbedder._normalize(vec)
        assert all(abs(v) < 1e-7 for v in result)

    def test_normalize_preserves_direction(self) -> None:
        vec = [3.0, 4.0]
        result = OllamaEmbedder._normalize(vec)
        assert abs(result[0] - 0.6) < 1e-5
        assert abs(result[1] - 0.8) < 1e-5
