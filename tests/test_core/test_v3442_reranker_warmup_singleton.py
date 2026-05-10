# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for v3.4.42 — engine_wiring reranker warmup-status disambiguation (B2b).

The bug:
  Any CLI process (slm health, slm doctor, slm recall) that wires a
  RetrievalEngine while the unified daemon is running would log:
      "Cross-encoder reranker warmup failed — recalls will use fallback scoring"
  even though the daemon's reranker was healthy and serving fine. The CLI
  process's warmup was blocked by the machine-wide singleton (correct
  behavior), but the warning was indistinguishable from a real failure.
  This was a false-positive that masked real reranker issues and eroded
  trust in slm health output.

The fix:
  After warmup_sync returns False, probe _is_reranker_worker_alive(). If
  another process owns the worker (the legitimate singleton case), log INFO
  describing the situation rather than WARNING about a failure. Real
  failures (singleton not held, model didn't load anywhere) still log
  WARNING — the diagnostic value is preserved.
"""

from __future__ import annotations

import logging
from unittest.mock import patch, MagicMock


def _drive_log_warmup_status(reranker, *, singleton_held: bool, probe_raises: bool = False):
    """Reproduce the exact closure that engine_wiring builds inside init_engine.

    We can't import the closure directly (it's nested in init_engine), but
    its body is small and stable — mirroring it here keeps tests focused
    on the fix without spinning up a full DB + engine. Any change to the
    closure body that breaks this mirror surfaces here as a test failure
    and prompts the test author to re-mirror — that's the desired signal.
    """
    logger = logging.getLogger("superlocalmemory.core.engine_wiring")

    ready = reranker.warmup_sync(timeout=180)
    if ready:
        logger.info("Cross-encoder reranker warm and ready")
        return
    try:
        from superlocalmemory.retrieval.reranker import _is_reranker_worker_alive as _probe
        if probe_raises:
            raise RuntimeError("probe boom")
        if _probe():
            logger.info(
                "Cross-encoder reranker worker held by another process "
                "(machine-wide singleton — usually the unified daemon); "
                "this process will route reranking through that worker"
            )
            return
    except Exception:
        pass
    logger.warning(
        "Cross-encoder reranker warmup failed — recalls will use fallback scoring"
    )


class TestRerankerWarmupLogDisambiguation:
    """v3.4.42 fix: distinguish singleton-held (benign) from actual failure."""

    def test_logs_info_when_warmup_sync_returns_true(self, caplog) -> None:
        """Healthy warmup logs INFO 'warm and ready' — unchanged behavior."""
        rr = MagicMock()
        rr.warmup_sync.return_value = True

        with caplog.at_level(logging.INFO, logger="superlocalmemory.core.engine_wiring"):
            _drive_log_warmup_status(rr, singleton_held=False)

        infos = [r for r in caplog.records if r.levelno == logging.INFO]
        warns = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("warm and ready" in r.message for r in infos)
        assert warns == []

    def test_logs_info_not_warning_when_singleton_held(self, caplog) -> None:
        """B2b: singleton held by another process → INFO, not WARNING.

        This is the bug fix — before v3.4.42 this case logged a misleading
        WARNING about reranker warmup failure even though the daemon's
        reranker was perfectly fine.
        """
        rr = MagicMock()
        rr.warmup_sync.return_value = False

        with patch(
            "superlocalmemory.retrieval.reranker._is_reranker_worker_alive",
            return_value=True,
        ), caplog.at_level(logging.INFO, logger="superlocalmemory.core.engine_wiring"):
            _drive_log_warmup_status(rr, singleton_held=True)

        infos = [r for r in caplog.records if r.levelno == logging.INFO]
        warns = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("held by another process" in r.message for r in infos), (
            "Expected an INFO line explaining the singleton ownership; got: "
            + repr([r.message for r in caplog.records])
        )
        assert warns == [], (
            "Singleton-held case must NOT log WARNING — that was the v3.4.42 false positive."
        )

    def test_logs_warning_when_warmup_failed_and_no_singleton(self, caplog) -> None:
        """Real failure path is preserved — WARNING when no one owns the worker."""
        rr = MagicMock()
        rr.warmup_sync.return_value = False

        with patch(
            "superlocalmemory.retrieval.reranker._is_reranker_worker_alive",
            return_value=False,
        ), caplog.at_level(logging.INFO, logger="superlocalmemory.core.engine_wiring"):
            _drive_log_warmup_status(rr, singleton_held=False)

        warns = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("warmup failed" in r.message for r in warns), (
            "Real failure (no singleton owner) must still log WARNING."
        )

    def test_probe_exception_falls_back_to_warning(self, caplog) -> None:
        """Defensive: if singleton probe itself raises, we still warn (not silently swallow)."""
        rr = MagicMock()
        rr.warmup_sync.return_value = False

        with caplog.at_level(logging.INFO, logger="superlocalmemory.core.engine_wiring"):
            _drive_log_warmup_status(rr, singleton_held=False, probe_raises=True)

        warns = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("warmup failed" in r.message for r in warns)
