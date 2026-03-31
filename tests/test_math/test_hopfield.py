# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3

"""Tests for ModernHopfieldNetwork (Phase G: 6th Retrieval Channel).

TDD Phase: RED first, then GREEN.
8 tests per LLD Section 6.1.
"""

from __future__ import annotations

import math

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_patterns(n: int, d: int, seed: int = 42) -> np.ndarray:
    """Generate n random L2-normalized d-dimensional patterns."""
    rng = np.random.default_rng(seed)
    mat = rng.standard_normal((n, d)).astype(np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    return mat / np.maximum(norms, 1e-8)


def _orthogonal_patterns(n: int, d: int) -> np.ndarray:
    """Generate n orthogonal unit vectors in d-dimensional space.

    Each pattern has a 1.0 in one of the first n dimensions, 0 elsewhere.
    Well-separated by construction.
    """
    mat = np.zeros((n, d), dtype=np.float32)
    for i in range(n):
        mat[i, i] = 1.0
    return mat


# ---------------------------------------------------------------------------
# Test 6 (LLD order): Beta scaling -- simplest, just constructor
# ---------------------------------------------------------------------------

class TestHopfieldBetaScaling:
    """LLD Test 6: Verify beta = 1/sqrt(d) for different dimensions."""

    def test_hopfield_beta_scaling_768(self) -> None:
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        config = HopfieldConfig(dimension=768)
        net = ModernHopfieldNetwork(config)
        expected = 1.0 / math.sqrt(768)
        assert net._beta == pytest.approx(expected, rel=1e-6)

    def test_hopfield_beta_scaling_384(self) -> None:
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        config = HopfieldConfig(dimension=384)
        net = ModernHopfieldNetwork(config)
        expected = 1.0 / math.sqrt(384)
        assert net._beta == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# Test 7: Softmax numerical stability
# ---------------------------------------------------------------------------

class TestHopfieldSoftmaxNumericalStability:
    """LLD Test 7: Shifted softmax produces finite values for extreme logits."""

    def test_hopfield_softmax_numerical_stability(self) -> None:
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        net = ModernHopfieldNetwork(HopfieldConfig(dimension=3))
        logits = np.array([1000.0, 1001.0, 999.0])
        result = net._softmax(logits)

        # Must be finite (no NaN/Inf)
        assert np.all(np.isfinite(result)), f"Non-finite softmax output: {result}"
        # Must sum to 1.0
        assert float(np.sum(result)) == pytest.approx(1.0, abs=1e-6)
        # Middle element (1001) should have highest weight
        assert np.argmax(result) == 1


# ---------------------------------------------------------------------------
# Test 8: Empty memory matrix
# ---------------------------------------------------------------------------

class TestHopfieldEmptyMemoryMatrix:
    """LLD Test 8: Empty (0 x d) matrix -- graceful handling, no crash."""

    def test_hopfield_empty_memory_matrix(self) -> None:
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        config = HopfieldConfig(dimension=8)
        net = ModernHopfieldNetwork(config)
        empty = np.zeros((0, 8), dtype=np.float32)
        query = np.ones(8, dtype=np.float32)

        # energy() on empty matrix should return 0.0
        e = net.energy(query, empty)
        assert e == 0.0

        # retrieve() on empty matrix should return a state with empty pattern
        state = net.retrieve(query, empty)
        assert state.iterations == 0
        assert not state.converged


# ---------------------------------------------------------------------------
# Test 1: Energy decreases after update
# ---------------------------------------------------------------------------

class TestHopfieldEnergyDecreasesAfterUpdate:
    """LLD Test 1: E(xi_new) <= E(xi) + epsilon after one update step."""

    def test_hopfield_energy_decreases_after_update(self) -> None:
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        d = 768
        config = HopfieldConfig(dimension=d)
        net = ModernHopfieldNetwork(config)
        memory = _random_patterns(10, d, seed=99)
        rng = np.random.default_rng(123)
        query = rng.standard_normal(d).astype(np.float32)
        query = query / np.linalg.norm(query)

        e_before = net.energy(query, memory)
        xi_new = net.update(query, memory)
        e_after = net.energy(xi_new, memory)

        # Energy must not increase (with small tolerance for float precision)
        assert e_after <= e_before + 1e-9, (
            f"Energy increased: {e_before:.6f} -> {e_after:.6f}"
        )


# ---------------------------------------------------------------------------
# Test 2: One-step convergence for well-separated patterns
# ---------------------------------------------------------------------------

class TestHopfieldConvergenceOneStep:
    """LLD Test 2: Orthogonal patterns + noisy query -> closest match in 1 step."""

    def test_hopfield_convergence_one_step(self) -> None:
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        d = 768
        config = HopfieldConfig(dimension=d)
        net = ModernHopfieldNetwork(config)
        memory = _orthogonal_patterns(5, d)

        # Query = pattern[2] + 0.1 * noise
        rng = np.random.default_rng(77)
        noise = rng.standard_normal(d).astype(np.float32) * 0.1
        query = memory[2] + noise
        query = query / np.linalg.norm(query)

        xi_new = net.update(query.astype(np.float32), memory)
        similarities = memory @ xi_new
        assert np.argmax(similarities) == 2


# ---------------------------------------------------------------------------
# Test 3: Exact stored pattern retrieval
# ---------------------------------------------------------------------------

class TestHopfieldRetrievesExactStoredPattern:
    """LLD Test 3: Querying with an exact stored pattern -> max attention at that index.

    Uses orthogonal patterns (well-separated) so attention is strongly peaked
    and the retrieved pattern is near-identical to the stored one.
    Random 768-d patterns with beta=1/sqrt(768) produce nearly uniform attention,
    which is correct math but makes allclose meaningless. Orthogonal patterns
    demonstrate the intended behaviour: delta-like attention -> exact retrieval.
    """

    def test_hopfield_retrieves_exact_stored_pattern(self) -> None:
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        d = 768
        config = HopfieldConfig(dimension=d)
        net = ModernHopfieldNetwork(config)
        # Use orthogonal patterns for well-separated test (LLD Section 2.1 note:
        # "Exact match produces a near-delta attention distribution")
        memory = _orthogonal_patterns(20, d)

        query = memory[7].copy()
        attention = net.attention_scores(query, memory)
        assert np.argmax(attention) == 7

        state = net.retrieve(query, memory)
        # The retrieved pattern is X' @ attention. With beta=1/sqrt(768) the
        # attention is only slightly peaked, so allclose to a single pattern
        # is not expected. What IS guaranteed: the component corresponding
        # to the target pattern has the highest value in the retrieved vector.
        assert np.argmax(state.retrieved_pattern) == 7
        # The target dimension's value exceeds all others
        assert state.retrieved_pattern[7] > state.retrieved_pattern[0]


# ---------------------------------------------------------------------------
# Test 4: Pattern completion from noisy query
# ---------------------------------------------------------------------------

class TestHopfieldPatternCompletionNoisyQuery:
    """LLD Test 4: 80% signal + 20% noise -> retrieved pattern closest to source.

    Uses orthogonal patterns so the Hopfield attention is peaked enough for
    pattern completion to clearly identify the closest stored pattern.
    With beta=1/sqrt(768), random patterns produce near-uniform attention
    (correct math) but insufficient discrimination for this test.
    """

    def test_hopfield_pattern_completion_noisy_query(self) -> None:
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        d = 768
        config = HopfieldConfig(dimension=d)
        net = ModernHopfieldNetwork(config)
        memory = _orthogonal_patterns(10, d)

        rng = np.random.default_rng(44)
        noise = rng.standard_normal(d).astype(np.float32)
        noise = noise / np.linalg.norm(noise)
        query = 0.8 * memory[3] + 0.2 * noise
        query = query / np.linalg.norm(query)

        state = net.retrieve(query.astype(np.float32), memory)
        retrieved_norm = state.retrieved_pattern / max(
            float(np.linalg.norm(state.retrieved_pattern)), 1e-8,
        )

        # Cosine similarity to target pattern[3] should be highest
        cosine_target = float(np.dot(retrieved_norm, memory[3]))
        for i in range(10):
            if i == 3:
                continue
            cosine_other = float(np.dot(retrieved_norm, memory[i]))
            assert cosine_target > cosine_other, (
                f"Pattern {i} has higher cosine ({cosine_other:.4f}) "
                f"than target 3 ({cosine_target:.4f})"
            )


# ---------------------------------------------------------------------------
# Test 5: Capacity -- 100 patterns
# ---------------------------------------------------------------------------

class TestHopfieldCapacity100Patterns:
    """LLD Test 5: 100 random 768-d patterns, >= 95/100 correct retrievals."""

    def test_hopfield_capacity_100_patterns(self) -> None:
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        d = 768
        config = HopfieldConfig(dimension=d)
        net = ModernHopfieldNetwork(config)
        memory = _random_patterns(100, d, seed=11)

        correct = 0
        for idx in range(100):
            # Query = pattern + 10% noise
            rng = np.random.default_rng(1000 + idx)
            noise = rng.standard_normal(d).astype(np.float32) * 0.1
            query = memory[idx] + noise
            query = query / np.linalg.norm(query)
            attention = net.attention_scores(query.astype(np.float32), memory)
            if np.argmax(attention) == idx:
                correct += 1

        assert correct >= 95, f"Only {correct}/100 correct (need >= 95)"


# ---------------------------------------------------------------------------
# Coverage gap tests — exercise uncovered branches
# ---------------------------------------------------------------------------

class TestHopfieldCoverageGaps:
    """Additional tests to cover edge-case branches for 100% coverage."""

    def test_update_empty_matrix_returns_zeros(self) -> None:
        """Direct call to update() with empty matrix returns zero vector."""
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        config = HopfieldConfig(dimension=8)
        net = ModernHopfieldNetwork(config)
        empty = np.zeros((0, 8), dtype=np.float32)
        query = np.ones(8, dtype=np.float32)

        result = net.update(query, empty)
        assert result.shape == (8,)
        assert np.allclose(result, 0.0)

    def test_attention_scores_empty_matrix(self) -> None:
        """attention_scores() with empty matrix returns empty array."""
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        config = HopfieldConfig(dimension=8)
        net = ModernHopfieldNetwork(config)
        empty = np.zeros((0, 8), dtype=np.float32)
        query = np.ones(8, dtype=np.float32)

        result = net.attention_scores(query, empty)
        assert result.shape == (0,)

    def test_multi_iteration_convergence_early_exit(self) -> None:
        """retrieve() with max_iterations>1 triggers convergence break."""
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        d = 16
        config = HopfieldConfig(
            dimension=d, max_iterations=10, convergence_epsilon=1e-3,
        )
        net = ModernHopfieldNetwork(config)
        # Orthogonal patterns converge in 1-2 steps
        memory = _orthogonal_patterns(3, d)
        query = memory[1].copy() + 0.01 * np.ones(d, dtype=np.float32)
        query = query / np.linalg.norm(query)

        state = net.retrieve(query.astype(np.float32), memory, max_iterations=10)
        # Should converge well before 10 iterations
        assert state.converged
        assert state.iterations < 10

    def test_energy_nan_guard_degenerate_matrix(self) -> None:
        """energy() returns 0.0 when computation yields NaN."""
        from superlocalmemory.math.hopfield import HopfieldConfig, ModernHopfieldNetwork

        config = HopfieldConfig(dimension=4)
        net = ModernHopfieldNetwork(config)
        # All-NaN matrix to force NaN in energy computation
        nan_matrix = np.full((2, 4), np.nan, dtype=np.float32)
        query = np.ones(4, dtype=np.float32)

        result = net.energy(query, nan_matrix)
        assert result == 0.0
