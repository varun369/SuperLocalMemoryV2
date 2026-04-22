# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for core.priority_queue — weighted fair scheduler."""

from __future__ import annotations


def _imports():
    from superlocalmemory.core import priority_queue as pq
    return pq


def test_default_weights_70_30():
    pq = _imports()
    sched = pq.WFQScheduler()
    assert sched.high_weight == 70
    assert sched.low_weight == 30


def test_pick_high_when_only_high_available():
    pq = _imports()
    sched = pq.WFQScheduler()
    assert sched.pick_lane(has_high=True, has_low=False) == "high"


def test_pick_low_when_only_low_available():
    pq = _imports()
    sched = pq.WFQScheduler()
    assert sched.pick_lane(has_high=False, has_low=True) == "low"


def test_pick_none_when_nothing_available():
    pq = _imports()
    sched = pq.WFQScheduler()
    assert sched.pick_lane(has_high=False, has_low=False) is None


def test_wfq_ratio_approximates_70_30_over_1000_rounds():
    pq = _imports()
    sched = pq.WFQScheduler()
    counts = {"high": 0, "low": 0}
    # Both lanes always have work → ratio should hit 70:30
    for _ in range(1000):
        lane = sched.pick_lane(has_high=True, has_low=True)
        sched.record_served(lane)
        counts[lane] += 1
    # Tolerance ±3 percentage points
    high_pct = counts["high"] / 1000 * 100
    assert 67 <= high_pct <= 73, f"high lane got {high_pct}% (expected ~70)"


def test_low_lane_never_fully_starved_under_sustained_high():
    pq = _imports()
    sched = pq.WFQScheduler()
    counts = {"high": 0, "low": 0}
    for _ in range(100):
        lane = sched.pick_lane(has_high=True, has_low=True)
        sched.record_served(lane)
        counts[lane] += 1
    assert counts["low"] > 20, (
        f"Low lane starved: {counts['low']} in 100 rounds (expected ~30)"
    )


def test_custom_weights():
    pq = _imports()
    sched = pq.WFQScheduler(high_weight=80, low_weight=20)
    counts = {"high": 0, "low": 0}
    for _ in range(1000):
        lane = sched.pick_lane(has_high=True, has_low=True)
        sched.record_served(lane)
        counts[lane] += 1
    high_pct = counts["high"] / 1000 * 100
    assert 77 <= high_pct <= 83
