# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Entropy Gate (Deduplication).

Filters low-information and duplicate content before expensive encoding.
AriadneMem pattern: block near-duplicates within a time window.

Ported from V1 with fixed threshold (0.95 from S13 fix).

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from superlocalmemory.core.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

# Minimum content length to pass gate (very short = low information)
_MIN_CONTENT_LENGTH = 10

# Words that indicate low-information content
_LOW_INFO_PATTERNS = frozenset({
    "ok", "okay", "yes", "no", "yeah", "sure", "thanks",
    "thank you", "got it", "right", "hmm", "hm", "ah",
    "i see", "alright", "fine", "cool", "nice", "great",
})


class EntropyGate:
    """Filter low-information and duplicate content before encoding.

    Two-stage filter:
    1. Content-based: reject very short or formulaic responses
    2. Similarity-based: reject near-duplicates of recent memories
    """

    def __init__(
        self,
        embedder: EmbeddingService | None = None,
        similarity_threshold: float = 0.95,
        window_size: int = 50,
    ) -> None:
        self._embedder = embedder
        self._threshold = similarity_threshold
        self._window_size = window_size
        self._recent_embeddings: list[list[float]] = []

    def should_pass(self, content: str) -> bool:
        """Return True if content has enough information to store.

        Returns False for low-info or near-duplicate content.
        """
        # Stage 1: Content-based filtering
        stripped = content.strip()
        if len(stripped) < _MIN_CONTENT_LENGTH:
            logger.debug("Entropy gate: blocked (too short: %d chars)", len(stripped))
            return False

        normalized = stripped.lower().strip(".,!?;:")
        if normalized in _LOW_INFO_PATTERNS:
            logger.debug("Entropy gate: blocked (low-info pattern: '%s')", normalized)
            return False

        # Stage 2: Similarity-based deduplication (requires embeddings)
        if self._embedder is not None:
            emb = self._embedder.embed(content)
            if emb is not None:
                if self._recent_embeddings:
                    for recent in self._recent_embeddings:
                        sim = _cosine(emb, recent)
                        if sim > self._threshold:
                            logger.debug(
                                "Entropy gate: blocked (near-duplicate, sim=%.3f)", sim
                            )
                            return False
                self._recent_embeddings.append(emb)
                if len(self._recent_embeddings) > self._window_size:
                    self._recent_embeddings.pop(0)

        return True

    def reset(self) -> None:
        """Clear the recent embeddings window."""
        self._recent_embeddings.clear()


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
