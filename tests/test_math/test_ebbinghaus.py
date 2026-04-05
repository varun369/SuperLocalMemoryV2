# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3

"""Tests for Ebbinghaus forgetting curve — Phase A.

TDD: 9 tests covering retention, strength, spaced repetition,
lifecycle zones, and convergence proof.
"""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta

import pytest

from superlocalmemory.core.config import ForgettingConfig
from superlocalmemory.math.ebbinghaus import (
    EbbinghausCurve,
    FactRetentionInput,
    MemoryStrength,
)


@pytest.fixture
def config() -> ForgettingConfig:
    """Default forgetting config."""
    return ForgettingConfig()


@pytest.fixture
def curve(config: ForgettingConfig) -> EbbinghausCurve:
    """EbbinghausCurve with default config."""
    return EbbinghausCurve(config)


# ---- Test 1: Retention decays over time ----

def test_retention_decays_over_time(curve: EbbinghausCurve) -> None:
    """R(24h, S=1.0) < R(0h, S=1.0) — retention must decrease with time."""
    r_fresh = curve.retention(0.0, 1.0)
    r_24h = curve.retention(24.0, 1.0)

    assert r_fresh > r_24h, "Retention should decay over time"
    assert r_fresh == pytest.approx(1.0, abs=1e-9), "Fresh memory should have ~1.0 retention"
    assert r_24h > 0.0, "Retention should not be zero after 24h with S=1.0"


# ---- Test 2: Retention always in [0, 1] ----

def test_retention_in_unit_range(curve: EbbinghausCurve) -> None:
    """0 <= R(t, S) <= 1 for 100 random inputs."""
    rng = random.Random(42)
    for _ in range(100):
        hours = rng.uniform(0.0, 10000.0)
        strength = rng.uniform(0.001, 200.0)
        r = curve.retention(hours, strength)
        assert 0.0 <= r <= 1.0, f"Retention {r} out of [0,1] for t={hours}, S={strength}"


# ---- Test 3: Retention never negative ----

def test_retention_never_negative(curve: EbbinghausCurve) -> None:
    """Boundary test: extreme decay should still be >= 0."""
    r = curve.retention(1e6, 0.001)
    assert r >= 0.0, "Retention must never be negative"
    assert not math.isnan(r), "Retention must not be NaN"
    assert not math.isinf(r), "Retention must not be Inf"


# ---- Test 4: Strength from access count (logarithmic) ----

def test_strength_from_access_count(curve: EbbinghausCurve) -> None:
    """More accesses -> higher strength (logarithmic growth)."""
    s_few = curve.memory_strength(1, 0.0, 0, 0.0)
    s_many = curve.memory_strength(10, 0.0, 0, 0.0)

    assert s_many > s_few, "More accesses should produce higher strength"


# ---- Test 5: Strength from importance ----

def test_strength_from_importance(curve: EbbinghausCurve) -> None:
    """Higher importance -> higher strength."""
    s_low = curve.memory_strength(0, 0.1, 0, 0.0)
    s_high = curve.memory_strength(0, 0.9, 0, 0.0)

    assert s_high > s_low, "Higher importance should produce higher strength"


# ---- Test 6: Strength bounds ----

def test_strength_bounds(curve: EbbinghausCurve) -> None:
    """Strength must be in [min_strength, max_strength] for extreme inputs."""
    config = curve._config

    # Very low inputs -> floored at min_strength
    s_min = curve.memory_strength(0, 0.0, 0, 0.0)
    assert s_min >= config.min_strength, f"Strength {s_min} below min {config.min_strength}"

    # Very high inputs -> capped at max_strength
    s_max = curve.memory_strength(10000, 100.0, 10000, 100.0)
    assert s_max <= config.max_strength, f"Strength {s_max} above max {config.max_strength}"


# ---- Test 7: Spaced repetition — long gap strengthens more ----

def test_spaced_repetition_long_gap_stronger(curve: EbbinghausCurve) -> None:
    """update(S, 72h) > update(S, 1h) — longer gaps produce more strength boost."""
    base_strength = 5.0
    s_short = curve.spaced_repetition_update(base_strength, 1.0)
    s_long = curve.spaced_repetition_update(base_strength, 72.0)

    assert s_long > s_short, "Longer gap should produce more strength boost"
    # HR-07: Spaced repetition only INCREASES strength
    assert s_short >= base_strength, "Spaced repetition must not decrease strength"
    assert s_long >= base_strength, "Spaced repetition must not decrease strength"


# ---- Test 8: Lifecycle zones ----

def test_lifecycle_zones(curve: EbbinghausCurve) -> None:
    """Zone classification matches thresholds."""
    assert curve.lifecycle_zone(0.9) == "active"
    assert curve.lifecycle_zone(0.6) == "warm"
    assert curve.lifecycle_zone(0.3) == "cold"
    assert curve.lifecycle_zone(0.1) == "archive"
    assert curve.lifecycle_zone(0.01) == "forgotten"


# ---- Test 19 (A-HIGH-01): Convergence proof ----

def test_convergence_proof(curve: EbbinghausCurve) -> None:
    """Run 1000 decay+access cycles. Assert retention converges to stable equilibrium.

    Validates that the Ebbinghaus curve admits a numerical steady state
    when alternating between decay and spaced repetition updates.
    """
    strength = 5.0
    retentions: list[float] = []

    for i in range(1000):
        # Decay for 24 hours
        r = curve.retention(24.0, strength)
        retentions.append(r)

        # Access event (spaced repetition boost)
        strength = curve.spaced_repetition_update(strength, 24.0)

    # Last 100 values should be stable (std dev < 0.01)
    last_100 = retentions[-100:]
    import statistics
    std_dev = statistics.stdev(last_100)
    assert std_dev < 0.01, (
        f"Retention did not converge: std_dev of last 100 = {std_dev:.4f}"
    )


# ---- Coverage: Negative time returns 1.0 ----

def test_retention_negative_time_returns_one(curve: EbbinghausCurve) -> None:
    """Negative hours_since_access should return 1.0 (future access)."""
    r = curve.retention(-5.0, 1.0)
    assert r == 1.0


# ---- Coverage: compute_strength returns MemoryStrength ----

def test_compute_strength_returns_dataclass(curve: EbbinghausCurve) -> None:
    """compute_strength should return a MemoryStrength with all components."""
    ms = curve.compute_strength("fact_1", 5, 0.5, 3, 0.2)
    assert isinstance(ms, MemoryStrength)
    assert ms.fact_id == "fact_1"
    assert ms.strength > 0
    assert ms.access_component > 0
    assert ms.importance_component > 0
    assert ms.confirmation_component > 0
    assert ms.emotional_component > 0


# ---- Coverage: batch_compute_retention ----

def test_batch_compute_retention(curve: EbbinghausCurve) -> None:
    """batch_compute_retention should process a list of facts."""
    now = datetime.now(UTC).isoformat()
    facts: list[FactRetentionInput] = [
        {
            "fact_id": "f1",
            "access_count": 10,
            "importance": 0.8,
            "confirmation_count": 5,
            "emotional_salience": 0.3,
            "last_accessed_at": now,
        },
        {
            "fact_id": "f2",
            "access_count": 0,
            "importance": 0.0,
            "confirmation_count": 0,
            "emotional_salience": 0.0,
            "last_accessed_at": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
        },
    ]

    results = curve.batch_compute_retention(facts)

    assert len(results) == 2
    assert results[0]["fact_id"] == "f1"
    assert results[1]["fact_id"] == "f2"
    assert 0.0 <= results[0]["retention"] <= 1.0
    assert 0.0 <= results[1]["retention"] <= 1.0
    assert results[0]["zone"] in ("active", "warm", "cold", "archive", "forgotten")


# ---- Coverage: batch_compute_retention with invalid date ----

def test_batch_compute_retention_invalid_date(curve: EbbinghausCurve) -> None:
    """Invalid date string should be handled gracefully."""
    facts: list[FactRetentionInput] = [
        {
            "fact_id": "f_bad",
            "access_count": 0,
            "importance": 0.0,
            "confirmation_count": 0,
            "emotional_salience": 0.0,
            "last_accessed_at": "not-a-date",
        },
    ]
    results = curve.batch_compute_retention(facts)
    assert len(results) == 1
    assert 0.0 <= results[0]["retention"] <= 1.0


# ---- Coverage: lifecycle_weight ----

def test_lifecycle_weight_mapping(curve: EbbinghausCurve) -> None:
    """lifecycle_weight should return correct weight for each zone."""
    assert curve.lifecycle_weight("active") == 1.0
    assert curve.lifecycle_weight("warm") == 0.7
    assert curve.lifecycle_weight("cold") == 0.3
    assert curve.lifecycle_weight("archive") == 0.0
    assert curve.lifecycle_weight("forgotten") == 0.0
    assert curve.lifecycle_weight("unknown_zone") == 0.0


# ---- Coverage: NaN/Inf guard in retention (lines 136-140) ----

def test_retention_nan_inf_guard(curve: EbbinghausCurve) -> None:
    """retention() must return 0.0 when math.exp produces NaN or Inf."""
    from unittest.mock import patch

    with patch("superlocalmemory.math.ebbinghaus.math.exp", return_value=float("nan")):
        result = curve.retention(10.0, 1.0)
        assert result == 0.0

    with patch("superlocalmemory.math.ebbinghaus.math.exp", return_value=float("inf")):
        result = curve.retention(10.0, 1.0)
        assert result == 0.0


# ---- Coverage: batch_compute_retention with timezone-naive datetime (line 289) ----

def test_batch_compute_retention_timezone_naive(curve: EbbinghausCurve) -> None:
    """batch_compute_retention handles timezone-naive datetime strings."""
    facts = [
        {
            "fact_id": "f_naive",
            "access_count": 5,
            "importance": 0.5,
            "confirmation_count": 2,
            "emotional_salience": 0.3,
            "last_accessed_at": "2026-03-01 12:00:00",  # No timezone info
        },
    ]
    results = curve.batch_compute_retention(facts)
    assert len(results) == 1
    assert 0.0 <= results[0]["retention"] <= 1.0
    assert results[0]["fact_id"] == "f_naive"
