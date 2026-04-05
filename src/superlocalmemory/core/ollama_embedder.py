# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Ollama Embedding Provider — lightweight HTTP-based embeddings.

Uses Ollama's /api/embed endpoint for fast local embeddings without
loading PyTorch or sentence-transformers into the process.

Typical latency: <1 second (vs 30s cold start for sentence-transformers).
Memory: ~0 MB in the SLM process (Ollama manages its own memory).

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Fisher variance constants (must match EmbeddingService)
_FISHER_VAR_MIN = 0.05
_FISHER_VAR_MAX = 2.0
_FISHER_VAR_RANGE = _FISHER_VAR_MAX - _FISHER_VAR_MIN

# Ollama connect/response timeouts
_CONNECT_TIMEOUT = 5.0
_RESPONSE_TIMEOUT = 30.0


class OllamaEmbedder:
    """Embedding service backed by a local Ollama instance.

    Drop-in replacement for EmbeddingService. Implements the same
    public interface (embed, embed_batch, compute_fisher_params,
    is_available, dimension) so the engine can swap transparently.
    """

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        dimension: int = 768,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._dimension = dimension
        self._available: bool | None = None  # lazy-checked

    # ------------------------------------------------------------------
    # Public interface (matches EmbeddingService)
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Check if Ollama is reachable and the model is pulled."""
        if self._available is not None:
            return self._available
        self._available = self._check_availability()
        return self._available

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, text: str) -> list[float] | None:
        """Embed a single text. Returns normalized vector or None on failure."""
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        try:
            return self._call_ollama_embed(text)
        except Exception as exc:
            logger.warning("Ollama embed failed: %s", exc)
            return None

    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        """Embed a batch of texts. Uses the batch API when available."""
        if not texts:
            raise ValueError("Cannot embed empty batch")
        try:
            return self._call_ollama_embed_batch(texts)
        except Exception as exc:
            logger.warning("Ollama batch embed failed: %s", exc)
            return [None] * len(texts)

    def compute_fisher_params(
        self, embedding: list[float],
    ) -> tuple[list[float], list[float]]:
        """Compute Fisher-Rao parameters from a raw embedding."""
        arr = np.asarray(embedding, dtype=np.float64)
        norm = float(np.linalg.norm(arr))
        if norm < 1e-10:
            mean = np.zeros(len(arr), dtype=np.float64)
            variance = np.full(len(arr), _FISHER_VAR_MAX, dtype=np.float64)
            return mean.tolist(), variance.tolist()
        mean = arr / norm
        abs_mean = np.abs(mean)
        max_val = float(np.max(abs_mean)) + 1e-10
        signal_strength = abs_mean / max_val
        variance = _FISHER_VAR_MAX - _FISHER_VAR_RANGE * signal_strength
        variance = np.clip(variance, _FISHER_VAR_MIN, _FISHER_VAR_MAX)
        return mean.tolist(), variance.tolist()

    def unload(self) -> None:
        """No-op for Ollama (Ollama manages its own model lifecycle)."""

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_availability(self) -> bool:
        """Verify Ollama is running and has the embedding model."""
        import httpx

        try:
            resp = httpx.get(
                f"{self._base_url}/api/tags",
                timeout=_CONNECT_TIMEOUT,
            )
            if resp.status_code != 200:
                return False
            models = resp.json().get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]
            model_base = self._model.split(":")[0]
            if model_base not in model_names:
                logger.info(
                    "Ollama running but model '%s' not found (have: %s)",
                    self._model, ", ".join(model_names),
                )
                return False
            return True
        except Exception as exc:
            logger.debug("Ollama not reachable: %s", exc)
            return False

    def _call_ollama_embed(self, text: str) -> list[float]:
        """Call Ollama embed endpoint for a single text."""
        import httpx

        resp = httpx.post(
            f"{self._base_url}/api/embed",
            json={"model": self._model, "input": [text]},
            timeout=httpx.Timeout(_RESPONSE_TIMEOUT, connect=_CONNECT_TIMEOUT),
        )
        resp.raise_for_status()
        data = resp.json()
        # Ollama /api/embed returns {"embeddings": [[...]]}
        vec = data["embeddings"][0]
        return self._normalize(vec)

    def _call_ollama_embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        """Call Ollama embed endpoint with batch input."""
        import httpx

        resp = httpx.post(
            f"{self._base_url}/api/embed",
            json={"model": self._model, "input": texts},
            timeout=httpx.Timeout(_RESPONSE_TIMEOUT, connect=_CONNECT_TIMEOUT),
        )
        resp.raise_for_status()
        data = resp.json()
        vectors = data.get("embeddings", [])
        return [self._normalize(v) for v in vectors]

    @staticmethod
    def _normalize(vec: list[float]) -> list[float]:
        """L2-normalize embedding vector."""
        arr = np.asarray(vec, dtype=np.float32)
        norm = float(np.linalg.norm(arr))
        if norm > 1e-10:
            arr = arr / norm
        return arr.tolist()
