# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3

"""Root conftest — shared fixtures for Phase 0 Safety Net.

Provides in-memory DB, mock embedder, Mode A config, and
engine-with-mock-deps fixtures used across all test modules.

V3.3.7: Added session-scoped worker cleanup to prevent orphaned
subprocess workers (reranker_worker, embedding_worker) from leaking
memory across parallel test runs. Each worker consumes 0.5-1.5 GB.
"""

from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Session-scoped worker cleanup (prevents orphaned subprocess leak)
# ---------------------------------------------------------------------------

def _kill_orphaned_slm_workers() -> None:
    """Kill any orphaned SLM subprocess workers.

    Targets: reranker_worker, embedding_worker, recall_worker.
    These subprocesses each consume 0.5-1.5 GB and can orphan when
    tests crash, get interrupted, or when parallel agents run tests.
    """
    worker_patterns = [
        "superlocalmemory.core.reranker_worker",
        "superlocalmemory.core.embedding_worker",
        "superlocalmemory.core.recall_worker",
    ]
    for pattern in worker_patterns:
        try:
            subprocess.run(
                ["pkill", "-f", pattern],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass


@pytest.fixture(autouse=True, scope="session")
def cleanup_slm_workers_at_end():
    """Kill all SLM subprocess workers when the test session ends.

    Session-scoped + autouse = runs once at session start (yields),
    then cleans up after ALL tests complete or crash.
    """
    yield
    _kill_orphaned_slm_workers()


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database with full SLM schema.

    Returns a real sqlite3 Connection backed by :memory:.
    Gives real SQL execution without touching disk.
    """
    from superlocalmemory.storage import schema

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    schema.create_all_tables(conn)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_embedder():
    """Mock embedder that returns deterministic 768-dim vectors.

    Uses seeded RNG keyed on input string for reproducibility.
    Implements: embed(), is_available, compute_fisher_params().
    """
    emb = MagicMock()

    def _embed(text: str) -> list[float]:
        rng = np.random.RandomState(hash(text) % 2**31)
        vec = rng.randn(768).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()

    emb.embed.side_effect = _embed
    emb.is_available = True
    emb.compute_fisher_params.return_value = ([0.0] * 768, [1.0] * 768)
    return emb


@pytest.fixture
def mode_a_config(tmp_path):
    """SLMConfig for Mode A using tmp_path as base_dir."""
    from superlocalmemory.core.config import SLMConfig
    from superlocalmemory.storage.models import Mode

    config = SLMConfig.for_mode(Mode.A, base_dir=tmp_path)
    return config


@pytest.fixture
def engine_with_mock_deps(mode_a_config, mock_embedder, tmp_path):
    """A MemoryEngine with mocked LLM and embedder for fast unit tests.

    Initializes with real DB (on disk in tmp_path) and real schema,
    but mocked embeddings and no LLM. Suitable for testing store/recall
    flow without heavy ML dependencies.
    """
    from superlocalmemory.core.engine import MemoryEngine

    engine = MemoryEngine(mode_a_config)

    # Patch embedder initialization to use our mock
    with patch('superlocalmemory.core.engine_wiring.init_embedder', return_value=mock_embedder):
        engine.initialize()
        engine._embedder = mock_embedder

    yield engine
    engine.close()
