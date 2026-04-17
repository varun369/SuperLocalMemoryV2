# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | Worker idle-timeout configuration tests

"""Regression tests for v3.4.19 — worker idle-timeout defaults + env overrides.

Guards two separate things:

1. **Defaults**: embedding worker and cross-encoder reranker now keep their
   models warm for 30 min (1800 s) by default. Prior to v3.4.19 this was
   120 s, which caused 30-60 s cold-starts on every recall after a short
   pause.

2. **Kill-switch**: ``SLM_EMBED_IDLE_TIMEOUT`` and
   ``SLM_RERANKER_IDLE_TIMEOUT`` must still override the default so users
   on low-RAM machines can flip back to the old aggressive policy without
   a code change or redeploy.

Both constants are read at import time (module-level ``os.environ.get``),
so these tests manipulate the environment and reload the module.
"""

from __future__ import annotations

import importlib
import os
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reload_with_env(module_name: str, env: dict) -> object:
    """Reimport ``module_name`` with ``env`` overlaid on ``os.environ``.

    Returns the freshly-loaded module. Caller is responsible for resetting
    ``os.environ`` if it cares about isolation (we save/restore here).
    """
    saved = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = str(v)

        if module_name in sys.modules:
            del sys.modules[module_name]
        module = importlib.import_module(module_name)
        return module
    finally:
        for k, old in saved.items():
            if old is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old
        if module_name in sys.modules:
            del sys.modules[module_name]


# ---------------------------------------------------------------------------
# Embedding worker idle timeout
# ---------------------------------------------------------------------------


class TestEmbeddingIdleTimeout:
    """Cover both the new 1800 s default and the env kill-switch."""

    def test_default_is_30_minutes(self):
        """With no override, idle timeout is 1800 s (not the pre-v3.4.19 120 s)."""
        mod = _reload_with_env(
            "superlocalmemory.core.embeddings",
            {"SLM_EMBED_IDLE_TIMEOUT": None},
        )
        assert mod._IDLE_TIMEOUT_SECONDS == 1800, (
            f"v3.4.19 ships a 30-minute default. Got {mod._IDLE_TIMEOUT_SECONDS}s."
        )

    def test_env_var_overrides_default(self):
        """``SLM_EMBED_IDLE_TIMEOUT=120`` must revert to the old aggressive policy."""
        mod = _reload_with_env(
            "superlocalmemory.core.embeddings",
            {"SLM_EMBED_IDLE_TIMEOUT": "120"},
        )
        assert mod._IDLE_TIMEOUT_SECONDS == 120, (
            "Kill-switch broken: SLM_EMBED_IDLE_TIMEOUT should restore 120 s."
        )

    def test_env_var_accepts_zero_for_immediate_kill(self):
        """Edge case: ``0`` means 'kill immediately' — useful for CI/stress tests."""
        mod = _reload_with_env(
            "superlocalmemory.core.embeddings",
            {"SLM_EMBED_IDLE_TIMEOUT": "0"},
        )
        assert mod._IDLE_TIMEOUT_SECONDS == 0


# ---------------------------------------------------------------------------
# Reranker idle timeout
# ---------------------------------------------------------------------------


class TestRerankerIdleTimeout:
    """Same contract for the cross-encoder reranker."""

    def test_default_is_30_minutes(self):
        mod = _reload_with_env(
            "superlocalmemory.retrieval.reranker",
            {"SLM_RERANKER_IDLE_TIMEOUT": None},
        )
        assert mod._IDLE_TIMEOUT_SECONDS == 1800

    def test_env_var_overrides_default(self):
        mod = _reload_with_env(
            "superlocalmemory.retrieval.reranker",
            {"SLM_RERANKER_IDLE_TIMEOUT": "120"},
        )
        assert mod._IDLE_TIMEOUT_SECONDS == 120


# ---------------------------------------------------------------------------
# Safety: we did NOT bump recall_worker's idle — it holds data caches, not
# model weights, and respawns cheaply. If a future edit accidentally bumps
# it too, flag it.
# ---------------------------------------------------------------------------


class TestRecallWorkerIdleUnchanged:
    """recall_worker should stay short-lived (data caches go stale)."""

    def test_recall_worker_idle_is_still_short(self):
        """Should be ≤ 300 s. Tests catch a well-meaning future bump."""
        mod = _reload_with_env(
            "superlocalmemory.core.worker_pool",
            {"SLM_RECALL_IDLE_TIMEOUT": None},
        )
        assert mod._IDLE_TIMEOUT <= 300, (
            f"recall_worker should stay short-lived; got {mod._IDLE_TIMEOUT}s. "
            "If this was intentional, update the test."
        )
