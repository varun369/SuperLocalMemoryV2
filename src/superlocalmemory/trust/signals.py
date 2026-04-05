# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Trust Signal Recorder with Burst Detection.

Records trust signals and detects anomalous write patterns.
Burst detection uses an in-memory sliding window (collections.deque)
per agent. Signals are published via the event bus rather than a
separate table, keeping the storage footprint minimal.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Any

logger = logging.getLogger(__name__)

# Valid signal types (must match scorer._SIGNAL_WEIGHTS keys)
VALID_SIGNAL_TYPES = frozenset({
    "store_success",
    "store_rejected",
    "recall_hit",
    "contradiction",
    "deletion",
})


class SignalRecorder:
    """Records trust signals and detects anomalous write patterns.

    Burst detection: tracks write timestamps in a per-agent deque.
    If > threshold writes occur within the window, burst is flagged.
    Burst-flagged signals are still recorded but logged as anomalous.
    """

    def __init__(
        self,
        db: Any,
        burst_window_seconds: int = 60,
        burst_threshold: int = 20,
    ) -> None:
        self._db = db
        self._burst_window = burst_window_seconds
        self._burst_threshold = burst_threshold

        # Per-agent sliding window: key = (agent_id, profile_id)
        # Value = deque of timestamps (float, time.monotonic)
        self._windows: dict[tuple[str, str], deque[float]] = defaultdict(
            lambda: deque(maxlen=max(1, burst_threshold * 2))
        )

        # In-memory signal log for get_recent_signals
        self._recent: dict[tuple[str, str], deque[dict]] = defaultdict(
            lambda: deque(maxlen=200)
        )

    def record(
        self,
        agent_id: str,
        profile_id: str,
        signal_type: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Record a trust signal.

        Args:
            agent_id: The agent generating the signal.
            profile_id: Active profile scope.
            signal_type: One of VALID_SIGNAL_TYPES.
            context: Optional metadata about the signal.

        Returns:
            True if signal was accepted (even during burst).
            False if signal_type is invalid.
        """
        if signal_type not in VALID_SIGNAL_TYPES:
            logger.warning("invalid signal type: %s", signal_type)
            return False

        now = time.monotonic()
        key = (agent_id, profile_id)

        # Update sliding window
        window = self._windows[key]
        window.append(now)
        self._prune_window(window, now)

        # Check burst before recording
        is_burst = len(window) >= self._burst_threshold
        if is_burst:
            logger.warning(
                "burst detected: agent=%s profile=%s count=%d in %ds",
                agent_id, profile_id, len(window), self._burst_window,
            )

        # Record signal in memory log
        entry = {
            "agent_id": agent_id,
            "profile_id": profile_id,
            "signal_type": signal_type,
            "timestamp": now,
            "burst_flagged": is_burst,
            "context": context or {},
        }
        self._recent[key].append(entry)

        return True

    def is_burst_detected(self, agent_id: str, profile_id: str) -> bool:
        """True if agent has exceeded burst_threshold writes in window."""
        key = (agent_id, profile_id)
        window = self._windows.get(key)
        if window is None:
            return False

        now = time.monotonic()
        self._prune_window(window, now)
        return len(window) >= self._burst_threshold

    def get_recent_signals(
        self, agent_id: str, profile_id: str, limit: int = 50
    ) -> list[dict]:
        """Get recent signals for an agent, most recent first."""
        key = (agent_id, profile_id)
        signals = list(self._recent.get(key, []))
        signals.reverse()
        return signals[:limit]

    def get_burst_status(self, profile_id: str) -> dict[str, bool]:
        """Get burst status for all agents in a profile.

        Returns dict mapping agent_id -> is_bursting.
        """
        result: dict[str, bool] = {}
        now = time.monotonic()
        for (aid, pid), window in self._windows.items():
            if pid != profile_id:
                continue
            self._prune_window(window, now)
            result[aid] = len(window) >= self._burst_threshold
        return result

    def _prune_window(self, window: deque[float], now: float) -> None:
        """Remove timestamps older than the burst window."""
        cutoff = now - self._burst_window
        while window and window[0] < cutoff:
            window.popleft()
