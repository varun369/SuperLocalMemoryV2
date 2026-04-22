# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Weighted fair scheduler for high/low job lanes.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import threading
from typing import Literal

Lane = Literal["high", "low"]


class WFQScheduler:
    """Deficit-round-robin-ish scheduler over two lanes.

    Tracks served counts and picks the lane whose ratio is furthest
    below its target share. Approximates the target ratio over any
    rolling window without requiring a time source.
    """

    def __init__(self, high_weight: int = 70, low_weight: int = 30) -> None:
        if high_weight <= 0 or low_weight <= 0:
            raise ValueError("weights must be positive")
        self.high_weight = high_weight
        self.low_weight = low_weight
        self._served = {"high": 0, "low": 0}
        self._lock = threading.Lock()

    def pick_lane(self, *, has_high: bool, has_low: bool) -> Lane | None:
        if not has_high and not has_low:
            return None
        if has_high and not has_low:
            return "high"
        if has_low and not has_high:
            return "low"
        with self._lock:
            total = self._served["high"] + self._served["low"]
            if total == 0:
                return "high"
            total_weight = self.high_weight + self.low_weight
            high_target = self.high_weight / total_weight
            low_target = self.low_weight / total_weight
            high_ratio = self._served["high"] / total
            low_ratio = self._served["low"] / total
            # Pick whichever lane is further below its target
            high_deficit = high_target - high_ratio
            low_deficit = low_target - low_ratio
            return "high" if high_deficit >= low_deficit else "low"

    def record_served(self, lane: Lane) -> None:
        with self._lock:
            self._served[lane] += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._served)
