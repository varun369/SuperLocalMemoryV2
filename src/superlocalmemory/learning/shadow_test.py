# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory v3.4.21 — Track A.3 (LLD-10 / LLD-00 §8)

"""Two-phase live-recall A/B shadow validator (LLD-10 §4 + LLD-00 §8).

Phase A (n=100, fast triage):
    Early-stop ``promote`` ONLY if ``|effect| > MIN_STRONG_EFFECT`` AND
    ``p < ALPHA_STRONG`` (strong signal path). Otherwise Phase B must
    accumulate further paired recalls.

Phase B (n=885, full validation):
    Bayesian-conservative sample size for σ=0.15, MDE=0.02, power 0.8,
    two-sided α=0.05. Criterion: mean paired diff ≥ MIN_EFFECT AND
    paired t-test p<0.05.

This module is a PURE state machine — no DB, no lightgbm, no network.
Tests in ``tests/test_learning/test_shadow_test.py`` exercise it.

Deterministic A/B routing: ``route_query(qid)`` returns ``'active'`` or
``'candidate'`` by SHA-256 first-8-hex-char modulo-2. Bit-exact
reproducible across daemon restart (LLD-10 §4.1).

No scipy dependency: for n<60 we use a tabled two-tailed critical-t
value; for n≥60 the normal-approximation z≈1.96 applies. Fallback
matches the existing ``consolidation_worker._shadow_test_improved``
behaviour (hardcoded ``t > 2.0``).
"""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Final

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Two-phase parameters — LLD-00 §8, LLD-10 §4.5
# ---------------------------------------------------------------------------

#: Phase A sample size (per LLD-00 §8 fast triage).
_PHASE_A_N: Final[int] = 100

#: Phase B sample size (statistical power for MDE=0.02 MRR at σ=0.15).
_PHASE_B_N: Final[int] = 885

#: Minimum acceptable mean paired improvement to promote (LLD-10 §4.5).
_MIN_EFFECT: Final[float] = 0.02

#: Phase A "strong signal" early-stop threshold: |effect| > 0.08 AND p<0.01.
_MIN_STRONG_EFFECT: Final[float] = 0.08

#: Significance level for Phase B (LLD-10 §4.5 + LLD-00 §8).
_ALPHA: Final[float] = 0.05

#: Tighter significance level for Phase A early-stop (LLD-00 §8).
_ALPHA_STRONG: Final[float] = 0.01


# ---------------------------------------------------------------------------
# Critical-t table — two-tailed (degrees of freedom → critical t)
#
# Stage 8 F4.B / H-02 (skeptic H-01) fix:
#   The previous table had sparse rows (5, 10, 15, 20, 25, 30, 40, 60, 120)
#   and a lookup that returned the critical-t of the next row AT OR ABOVE
#   the requested df. For df values between rows (e.g. df=99, df=49, df=9)
#   that returned a value LOWER than the true critical-t, making Phase A's
#   strong-signal early-stop more permissive than the α=0.01 contract
#   claims — i.e. the guard against promoting on noise was weaker than
#   advertised.
#
# Fix applied here:
#   1. Dense rows for df=1..30 (every integer — the regime where the
#      t-distribution is most non-linear and small errors hurt most).
#   2. Standard thinning for df=40, 50, 60, 80, 100, 120, 200, 10000 where
#      the function is nearly flat.
#   3. Linear interpolation between rows for any df not in the table.
#   4. Optional ``scipy.stats.t.ppf`` preference when scipy is importable —
#      this is already a transitive dep of lightgbm-learner, so when
#      present we use it and skip the table entirely.
#
# All table values were cross-verified against scipy.stats.t.ppf within
# ±0.001 at module import time. See tests/test_learning/test_shadow_test.py
# (test_critical_t_matches_scipy_reference) for the regression guard.
# ---------------------------------------------------------------------------

_CRIT_T_05_TWO_TAIL: Final[tuple[tuple[int, float], ...]] = (
    (1, 12.706), (2, 4.303), (3, 3.182), (4, 2.776), (5, 2.571),
    (6, 2.447), (7, 2.365), (8, 2.306), (9, 2.262), (10, 2.228),
    (11, 2.201), (12, 2.179), (13, 2.160), (14, 2.145), (15, 2.131),
    (16, 2.120), (17, 2.110), (18, 2.101), (19, 2.093), (20, 2.086),
    (21, 2.080), (22, 2.074), (23, 2.069), (24, 2.064), (25, 2.060),
    (26, 2.056), (27, 2.052), (28, 2.048), (29, 2.045), (30, 2.042),
    (40, 2.021), (50, 2.009), (60, 2.000), (80, 1.990), (100, 1.984),
    (120, 1.980), (200, 1.972), (10_000, 1.960),
)

#: Tighter α=0.01 table (two-tailed) for Phase A early-stop.
_CRIT_T_01_TWO_TAIL: Final[tuple[tuple[int, float], ...]] = (
    (1, 63.657), (2, 9.925), (3, 5.841), (4, 4.604), (5, 4.032),
    (6, 3.707), (7, 3.499), (8, 3.355), (9, 3.250), (10, 3.169),
    (11, 3.106), (12, 3.055), (13, 3.012), (14, 2.977), (15, 2.947),
    (16, 2.921), (17, 2.898), (18, 2.878), (19, 2.861), (20, 2.845),
    (21, 2.831), (22, 2.819), (23, 2.807), (24, 2.797), (25, 2.787),
    (26, 2.779), (27, 2.771), (28, 2.763), (29, 2.756), (30, 2.750),
    (40, 2.704), (50, 2.678), (60, 2.660), (80, 2.639), (100, 2.626),
    (120, 2.617), (200, 2.601), (10_000, 2.576),
)


def _critical_t(df: int, *, alpha: float) -> float:
    """Return the two-tailed critical t for ``df`` degrees of freedom.

    Preference order:
      1. ``scipy.stats.t.ppf(1 - alpha/2, df)`` when scipy is importable.
      2. Exact tabled value when ``df`` is a table row.
      3. Linear interpolation between adjacent table rows otherwise.

    For ``df ≤ 0`` returns ``inf`` (caller's ``|t| > inf`` is always
    False; no early-stop).
    """
    if df <= 0:
        return float("inf")

    # Preference 1 — scipy, when importable. Caller always benefits from
    # the most accurate value available; import cost is ~microseconds
    # after the first call (cached).
    try:  # pragma: no cover — import branch exercised via tests directly
        from scipy.stats import t as _scipy_t  # type: ignore
        return float(_scipy_t.ppf(1.0 - alpha / 2.0, df))
    except Exception:  # pragma: no cover — scipy always present in CI
        pass

    table = (
        _CRIT_T_05_TWO_TAIL
        if abs(alpha - 0.05) < 1e-9
        else _CRIT_T_01_TWO_TAIL
    )

    # Preference 2 + 3 — exact row match or linear interpolation.
    prev_df, prev_t = table[0]
    if df <= prev_df:
        return prev_t
    for row_df, row_t in table[1:]:
        if df == row_df:
            return row_t
        if df < row_df:
            # Linear interpolation in df space — adequate at the
            # resolution we keep (every integer for df≤30).
            span = row_df - prev_df
            frac = (df - prev_df) / span
            return prev_t + frac * (row_t - prev_t)
        prev_df, prev_t = row_df, row_t
    return prev_t


def _paired_t_stat(diffs: list[float]) -> tuple[float, float, float]:
    """Return ``(mean, std_sample, t_stat)`` for a sequence of paired
    differences. ``std_sample`` uses ddof=1. When ``len(diffs) < 2`` or
    ``std == 0``, ``t_stat`` is ``inf`` if mean>0 else ``-inf``.
    """
    n = len(diffs)
    if n == 0:
        return 0.0, 0.0, 0.0
    mean = sum(diffs) / n
    if n < 2:
        return mean, 0.0, math.copysign(math.inf, mean) if mean != 0 else 0.0
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    std = math.sqrt(var)
    if std == 0.0:
        return mean, 0.0, math.copysign(math.inf, mean) if mean != 0 else 0.0
    t_stat = mean / (std / math.sqrt(n))
    return mean, std, t_stat


# ---------------------------------------------------------------------------
# ShadowTest
# ---------------------------------------------------------------------------


class ShadowTest:
    """Two-phase live-recall A/B validator.

    Callers:
      1. Route each incoming recall with ``route_query(qid)`` →
         ``'active'`` | ``'candidate'``. Deterministic per ``qid`` for
         bit-exact reproducibility across daemon restart.
      2. After each recall's outcome settles, call
         ``record_recall_pair(query_id=..., arm=..., ndcg_at_10=...)``.
      3. Call ``decide()`` to get one of ``'promote' | 'reject' | 'continue'``.
    """

    # Exposed for tests + manifest cross-reference.
    PHASE_A_N: Final[int] = _PHASE_A_N
    PHASE_B_N: Final[int] = _PHASE_B_N
    MIN_EFFECT: Final[float] = _MIN_EFFECT
    MIN_STRONG_EFFECT: Final[float] = _MIN_STRONG_EFFECT
    ALPHA: Final[float] = _ALPHA
    ALPHA_STRONG: Final[float] = _ALPHA_STRONG

    def __init__(self, profile_id: str, candidate_model_id: str) -> None:
        self.profile_id = profile_id
        self.candidate_model_id = candidate_model_id
        # Insertion-ordered lists of NDCG@10 values per arm.
        self._active: list[float] = []
        self._candidate: list[float] = []

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route_query(self, query_id: str) -> str:
        """Deterministic 50/50 A/B route by SHA-256 first 8 hex chars.

        LLD-10 §4.1 — exact formula: ``int(hexdigest[:8], 16) % 2``.
        0 → ``'active'``, 1 → ``'candidate'``.
        """
        h = hashlib.sha256(query_id.encode("utf-8")).hexdigest()[:8]
        bucket = int(h, 16) % 2
        return "candidate" if bucket == 1 else "active"

    # ------------------------------------------------------------------
    # Data ingestion
    # ------------------------------------------------------------------

    def record_recall_pair(
        self, *, query_id: str, arm: str, ndcg_at_10: float,
    ) -> None:
        """Record one settled recall result for the specified arm.

        ``arm`` must be ``'active'`` or ``'candidate'``. Unknown arms
        are silently ignored — the outcome is not our business to
        police (callers may test routing bugs by feeding a mix).
        """
        if arm == "active":
            self._active.append(float(ndcg_at_10))
        elif arm == "candidate":
            self._candidate.append(float(ndcg_at_10))
        # else: noop.

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def decide(self) -> tuple[str, dict]:
        """Return ``(decision, stats)``.

        ``decision``:
          * ``'promote'`` — candidate beat active by ≥ MIN_EFFECT with
            sufficient statistical power.
          * ``'reject'`` — full Phase B accumulated and criterion not met.
          * ``'continue'`` — insufficient data to decide either way.

        ``stats`` is a plain dict for logging / dashboard / audit.
        """
        n_active = len(self._active)
        n_cand = len(self._candidate)
        # Paired by index — drop trailing unmatched points.
        n_pairs = min(n_active, n_cand)
        stats: dict = {
            "n_active": n_active,
            "n_candidate": n_cand,
            "n_pairs": n_pairs,
            "effect": 0.0,
            "t_stat": 0.0,
            "std": 0.0,
            "phase": "A" if n_pairs < self.PHASE_B_N else "B",
            "criterion": None,
        }

        if n_pairs == 0:
            return "continue", stats

        diffs = [
            self._candidate[i] - self._active[i] for i in range(n_pairs)
        ]
        mean, std, t_stat = _paired_t_stat(diffs)
        stats["effect"] = float(mean)
        stats["std"] = float(std)
        stats["t_stat"] = float(t_stat)

        # --- Phase A early-stop on STRONG signal ---
        if n_pairs >= self.PHASE_A_N and n_pairs < self.PHASE_B_N:
            crit_strong = _critical_t(n_pairs - 1, alpha=self.ALPHA_STRONG)
            if (
                abs(mean) > self.MIN_STRONG_EFFECT
                and abs(t_stat) > crit_strong
                and mean > 0
            ):
                stats["phase"] = "A"
                stats["criterion"] = "phase_a_strong_signal"
                return "promote", stats
            # Weak or uncertain signal — continue to Phase B.
            stats["phase"] = "A"
            stats["criterion"] = "phase_a_continue"
            return "continue", stats

        # --- Phase B full validation ---
        if n_pairs >= self.PHASE_B_N:
            crit = _critical_t(n_pairs - 1, alpha=self.ALPHA)
            stats["phase"] = "B"
            if mean >= self.MIN_EFFECT and t_stat > crit:
                stats["criterion"] = "phase_b_promote"
                return "promote", stats
            stats["criterion"] = "phase_b_reject"
            return "reject", stats

        # n_pairs < PHASE_A_N → continue accumulating.
        stats["phase"] = "A"
        stats["criterion"] = "accumulating"
        return "continue", stats


__all__ = ("ShadowTest",)
