# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""3-phase adaptive ranker — from heuristic to ML.

Phase 1: cross-encoder score only (cold start)
Phase 2: heuristic boosts (some data)
Phase 3: LightGBM model (enough training data)

Transitions are automatic based on accumulated training data.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from superlocalmemory.learning.features import FeatureExtractor, FeatureVector, FEATURE_DIM

logger = logging.getLogger(__name__)

# Phase thresholds
PHASE_2_THRESHOLD = 50   # signals needed to enter Phase 2
PHASE_3_THRESHOLD = 200  # signals needed to enter Phase 3


class AdaptiveRanker:
    """3-phase adaptive re-ranker for V3 retrieval results."""

    def __init__(self, signal_count: int = 0, model_state: bytes | None = None) -> None:
        self._signal_count = signal_count
        self._model = None
        if model_state:
            self._load_model(model_state)

    @property
    def phase(self) -> int:
        if self._signal_count >= PHASE_3_THRESHOLD and self._model is not None:
            return 3
        if self._signal_count >= PHASE_2_THRESHOLD:
            return 2
        return 1

    @property
    def signal_count(self) -> int:
        return self._signal_count

    @signal_count.setter
    def signal_count(self, value: int) -> None:
        self._signal_count = value

    def rerank(self, results: list[dict], query_context: dict) -> list[dict]:
        """Re-rank retrieval results based on current phase."""
        if not results:
            return results

        if self.phase == 3:
            return self._rerank_ml(results, query_context)
        elif self.phase == 2:
            return self._rerank_heuristic(results, query_context)
        else:
            return self._rerank_baseline(results)

    def train(self, training_data: list[dict]) -> bool:
        """Train LightGBM model on labeled data. Returns True if model was trained."""
        if len(training_data) < PHASE_3_THRESHOLD:
            return False

        try:
            import lightgbm as lgb
        except ImportError:
            logger.warning("LightGBM not installed. Phase 3 ranking unavailable.")
            return False

        features_list = []
        labels = []
        for item in training_data:
            fv = item.get("features", {})
            label = item.get("label", 0.0)
            # Convert feature dict to ordered list
            vec = [fv.get(name, 0.0) for name in FeatureExtractor.extract(
                {"channel_scores": {}, "fact": {}}, {"query_type": ""}
            ).features.keys()]
            # Simpler: just use the feature values in order
            from superlocalmemory.learning.features import FEATURE_NAMES
            vec = [float(fv.get(name, 0.0)) for name in FEATURE_NAMES]
            features_list.append(vec)
            labels.append(float(label))

        if not features_list:
            return False

        dataset = lgb.Dataset(features_list, label=labels)
        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "num_leaves": 15,
            "learning_rate": 0.1,
            "verbose": -1,
        }
        self._model = lgb.train(params, dataset, num_boost_round=50)
        logger.info("LightGBM model trained with %d examples", len(features_list))
        return True

    def get_model_state(self) -> bytes | None:
        """Serialize model for persistence."""
        if self._model is None:
            return None
        return self._model.model_to_string().encode("utf-8")

    # -- Phase implementations --

    def _rerank_baseline(self, results: list[dict]) -> list[dict]:
        """Phase 1: rank by cross-encoder score."""
        return sorted(results, key=lambda r: r.get("cross_encoder_score", r.get("score", 0)), reverse=True)

    def _rerank_heuristic(self, results: list[dict], query_context: dict) -> list[dict]:
        """Phase 2: heuristic boosts on top of cross-encoder."""
        scored = []
        for r in results:
            base = r.get("cross_encoder_score", r.get("score", 0))
            # Boosts
            recency_boost = 0.1 * math.exp(-r.get("fact", {}).get("age_days", 30) / 30)
            access_boost = 0.05 * min(r.get("fact", {}).get("access_count", 0) / 10, 1.0)
            trust_boost = 0.1 * (r.get("trust_score", 0.5) - 0.5)
            final = base + recency_boost + access_boost + trust_boost
            scored.append({**r, "_adaptive_score": final})
        return sorted(scored, key=lambda r: r["_adaptive_score"], reverse=True)

    def _rerank_ml(self, results: list[dict], query_context: dict) -> list[dict]:
        """Phase 3: LightGBM prediction."""
        if self._model is None:
            return self._rerank_heuristic(results, query_context)

        feature_vectors = FeatureExtractor.extract_batch(results, query_context)
        predictions = []
        for fv in feature_vectors:
            vec = [fv.to_list()]
            pred = self._model.predict(vec)[0]
            predictions.append(pred)

        paired = list(zip(results, predictions))
        paired.sort(key=lambda x: x[1], reverse=True)
        return [r for r, _ in paired]

    def _load_model(self, state: bytes) -> None:
        """Load model from serialized state."""
        try:
            import lightgbm as lgb
            self._model = lgb.Booster(model_str=state.decode("utf-8"))
        except (ImportError, Exception) as exc:
            logger.warning("Could not load LightGBM model: %s", exc)
            self._model = None
