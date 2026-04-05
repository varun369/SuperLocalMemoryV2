# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Signal Inference (6 Types).

Infers the signal type of a memory/fact from its content.
Ported from V2.8 — used to adjust retrieval channel weights.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import re

from superlocalmemory.storage.models import SignalType

# Compiled patterns for each signal type
_PATTERNS: dict[SignalType, re.Pattern] = {
    SignalType.EMOTIONAL: re.compile(
        r"\b(happy|sad|angry|frustrated|excited|worried|anxious|"
        r"love|hate|afraid|grateful|disappointed|thrilled|upset|"
        r"feeling|emotion|mood)\b",
        re.IGNORECASE,
    ),
    SignalType.TEMPORAL: re.compile(
        r"\b(when|date|time|schedule|deadline|tomorrow|yesterday|"
        r"last week|next month|ago|soon|later|earlier|"
        r"january|february|march|april|may|june|july|"
        r"august|september|october|november|december|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        re.IGNORECASE,
    ),
    SignalType.OPINION: re.compile(
        r"\b(think|believe|prefer|opinion|recommend|suggest|"
        r"should|better|worse|best|worst|favorite|"
        r"in my view|personally|i feel|i guess)\b",
        re.IGNORECASE,
    ),
    SignalType.REQUEST: re.compile(
        r"\b(please|could you|would you|can you|help|need|"
        r"want|looking for|searching|find|tell me|show me|"
        r"remind me|remember)\b",
        re.IGNORECASE,
    ),
    SignalType.SOCIAL: re.compile(
        r"\b(friend|family|colleague|partner|boss|team|"
        r"relationship|together|married|dating|met with|"
        r"call|message|email|chat)\b",
        re.IGNORECASE,
    ),
}

# Priority order: more specific types checked first.
# SOCIAL before TEMPORAL because social signals often co-occur with
# temporal markers ("met yesterday") and the social context is primary.
_PRIORITY = [
    SignalType.REQUEST,
    SignalType.SOCIAL,
    SignalType.TEMPORAL,
    SignalType.EMOTIONAL,
    SignalType.OPINION,
]


def infer_signal(text: str) -> SignalType:
    """Infer the signal type of a text.

    Returns the most specific matching type, or FACTUAL as default.
    """
    for stype in _PRIORITY:
        pattern = _PATTERNS.get(stype)
        if pattern and pattern.search(text):
            return stype
    return SignalType.FACTUAL


def infer_signal_scores(text: str) -> dict[SignalType, float]:
    """Compute a signal score for each type (0.0-1.0).

    Useful for multi-signal content that mixes types.
    Score = number of pattern matches / 5 (capped at 1.0).
    """
    scores: dict[SignalType, float] = {}
    for stype, pattern in _PATTERNS.items():
        matches = pattern.findall(text)
        scores[stype] = min(1.0, len(matches) / 5.0)
    scores[SignalType.FACTUAL] = 1.0 - max(scores.values()) if scores else 1.0
    return scores
