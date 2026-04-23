# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Auto-capture — detect and store important information automatically."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Patterns that indicate capture-worthy content
_DECISION_PATTERNS = [
    r"(?i)\b(decided|chose|picked|selected|went with|using|switched to)\b",
    r"(?i)\b(because|reason|rationale|due to|since)\b.*\b(chose|use|prefer)\b",
]

_BUG_PATTERNS = [
    r"(?i)\b(fixed|resolved|solved|root cause|bug|issue|error)\b",
    r"(?i)\b(the (?:fix|solution|problem) (?:was|is))\b",
]

_PREFERENCE_PATTERNS = [
    r"(?i)\b(prefer|always use|never use|I like|I hate|don't like)\b",
    r"(?i)\b(convention|standard|style|pattern)\b.*\b(is|should be|must be)\b",
]


@dataclass(frozen=True)
class CaptureDecision:
    """Result of evaluating content for auto-capture."""

    capture: bool
    confidence: float
    category: str  # "decision", "bug", "preference", "session_summary", "none"
    reason: str


class AutoCapture:
    """Detect and classify content for automatic storage.

    Two ways to wire the store side:

    - Pass ``engine=<MemoryEngine>`` (CLI/daemon path — historical shape).
    - Pass ``store_fn=<callable>`` (MCP/LIGHT path — the callable should
      match ``MemoryEngine.store(content, metadata=...)`` and return a
      list of fact ids). When both are supplied, ``store_fn`` wins.
    """

    def __init__(
        self,
        engine=None,
        config: dict | None = None,
        *,
        store_fn: Callable[..., Any] | None = None,
    ):
        self._engine = engine
        self._store_fn = store_fn
        self._config = config or {}
        self._enabled = self._config.get("enabled", True)
        self._min_confidence = self._config.get("min_confidence", 0.5)
        self._capture_decisions = self._config.get("capture_decisions", True)
        self._capture_bugs = self._config.get("capture_bugs", True)
        self._capture_preferences = self._config.get("capture_preferences", True)

    def evaluate(self, content: str) -> CaptureDecision:
        """Evaluate whether content should be auto-captured.

        Returns a CaptureDecision with capture=True/False,
        confidence score, and category.
        """
        if not self._enabled:
            return CaptureDecision(False, 0.0, "none", "auto-capture disabled")

        if len(content.strip()) < 20:
            return CaptureDecision(False, 0.0, "none", "content too short")

        # Check for decisions
        if self._capture_decisions:
            score = self._match_patterns(content, _DECISION_PATTERNS)
            if score >= self._min_confidence:
                return CaptureDecision(True, score, "decision", "decision pattern detected")

        # Check for bug fixes
        if self._capture_bugs:
            score = self._match_patterns(content, _BUG_PATTERNS)
            if score >= self._min_confidence:
                return CaptureDecision(True, score, "bug", "bug fix pattern detected")

        # Check for preferences
        if self._capture_preferences:
            score = self._match_patterns(content, _PREFERENCE_PATTERNS)
            if score >= self._min_confidence:
                return CaptureDecision(True, score, "preference", "preference pattern detected")

        return CaptureDecision(False, 0.0, "none", "no patterns matched")

    def capture(self, content: str, category: str = "", metadata: dict | None = None) -> bool:
        """Store content via engine or store_fn if auto-capture decides to.

        Never mutates the caller's metadata dict — we copy before adding
        our auto-capture bookkeeping keys. This matters because
        ``pool_store`` ships the dict cross-process and callers often
        reuse the same dict across captures.
        """
        if self._store_fn is None and self._engine is None:
            return False

        try:
            meta = {**(metadata or {}), "source": "auto-capture", "category": category}
            if self._store_fn is not None:
                fact_ids = self._store_fn(content, metadata=meta)
            else:
                fact_ids = self._engine.store(content, metadata=meta)
            return bool(fact_ids) and len(fact_ids) > 0
        except Exception as exc:
            logger.warning("Auto-capture store failed: %s", exc)
            return False

    def _match_patterns(self, content: str, patterns: list[str]) -> float:
        """Match content against regex patterns. Returns confidence 0.0-1.0."""
        matches = sum(1 for p in patterns if re.search(p, content))
        if matches == 0:
            return 0.0
        return min(1.0, 0.5 + (matches * 0.25))

    @property
    def enabled(self) -> bool:
        return self._enabled
