# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Emotional Tagging (VADER).

Extracts emotional valence and arousal from text.
Emotionally charged memories are stored more strongly and retrieved more easily
(amygdala tagging principle from neuroscience).

Ported from V1 — VADER-based, zero-LLM, works in all modes.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_vader_analyzer = None


def _get_vader():
    """Lazy-load VADER to avoid import cost on startup."""
    global _vader_analyzer
    if _vader_analyzer is not None:
        return _vader_analyzer
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning, module="vaderSentiment")
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            _vader_analyzer = SentimentIntensityAnalyzer()
    except ImportError:
        logger.warning("vaderSentiment not installed — emotional tagging disabled")
        _vader_analyzer = None
    return _vader_analyzer


@dataclass(frozen=True)
class EmotionalTag:
    """Emotional metadata for a memory or fact."""

    valence: float   # -1.0 (negative) to +1.0 (positive)
    arousal: float   # 0.0 (calm) to 1.0 (intense)


def tag_emotion(text: str) -> EmotionalTag:
    """Extract emotional valence and arousal from text.

    Valence: VADER compound score [-1, +1].
    Arousal: absolute compound + max(pos, neg) — higher = more emotional intensity.
    Falls back to keyword heuristic when VADER is unavailable.
    """
    analyzer = _get_vader()
    if analyzer is None:
        return _keyword_fallback(text)

    scores = analyzer.polarity_scores(text)
    compound = scores["compound"]     # -1 to +1
    pos = scores["pos"]               # 0 to 1
    neg = scores["neg"]               # 0 to 1

    valence = compound
    # Arousal = emotional intensity regardless of direction
    arousal = min(1.0, abs(compound) * 0.6 + max(pos, neg) * 0.4)

    return EmotionalTag(valence=round(valence, 4), arousal=round(arousal, 4))


_POSITIVE_WORDS: frozenset[str] = frozenset({
    "love", "amazing", "wonderful", "great", "happy", "fantastic",
    "excellent", "beautiful", "awesome", "brilliant", "incredible",
    "joy", "thrilled", "grateful", "delighted", "superb",
})

_NEGATIVE_WORDS: frozenset[str] = frozenset({
    "hate", "terrible", "horrible", "awful", "bad", "worst",
    "angry", "frustrated", "disappointed", "sad", "miserable",
    "disgusting", "dreadful", "pathetic", "furious", "outraged",
})


def _keyword_fallback(text: str) -> EmotionalTag:
    """Lightweight sentiment heuristic when VADER is unavailable.

    Counts positive/negative keywords and derives approximate valence/arousal.
    """
    if not text.strip():
        return EmotionalTag(valence=0.0, arousal=0.0)

    words = set(text.lower().split())
    pos_count = len(words & _POSITIVE_WORDS)
    neg_count = len(words & _NEGATIVE_WORDS)
    total = pos_count + neg_count

    if total == 0:
        return EmotionalTag(valence=0.0, arousal=0.0)

    # Valence: positive - negative, normalised to [-1, 1]
    raw_valence = (pos_count - neg_count) / total
    valence = max(-1.0, min(1.0, raw_valence))

    # Arousal: how many emotional words relative to total word count
    word_count = max(len(words), 1)
    arousal = min(1.0, total / word_count * 2.0)

    return EmotionalTag(valence=round(valence, 4), arousal=round(arousal, 4))


def is_emotionally_significant(tag: EmotionalTag, threshold: float = 0.3) -> bool:
    """Check if the emotional signal is strong enough to boost importance."""
    return tag.arousal >= threshold


def emotional_importance_boost(tag: EmotionalTag) -> float:
    """Compute importance boost from emotional signal.

    Returns 0.0-0.3 boost. High arousal memories get stored more strongly
    (amygdala-inspired encoding enhancement).
    """
    if tag.arousal <= 0.2:
        return 0.0
    return min(0.3, tag.arousal * 0.3)
