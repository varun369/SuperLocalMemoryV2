# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for v3.4.42 — `slm warmup` daemon-aware fast path (B2a).

The bug:
  When the unified daemon is running, it owns the embedding worker via the
  machine-wide singleton (PID file). A fresh EmbeddingService spawned by
  `slm warmup` sees the singleton, sets _available=False, embeds returns
  None, and warmup prints "embedding verification failed" with a misleading
  "Python path mismatch" diagnostic (no Python path is involved — the issue
  is the singleton).

The fix:
  cmd_warmup checks if the daemon is up and reports engine=initialized. If
  so, the model is already loaded inside the daemon's worker — no local
  warmup needed. Print PASS, return. Only fall through to the original
  local-spawn path when the daemon is genuinely unreachable.
"""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import patch

import pytest


class TestWarmupDaemonUpFastPath:
    """When daemon is up + engine=initialized, warmup is a no-op success."""

    def test_pass_when_daemon_up_and_engine_initialized(self, capsys) -> None:
        """B2a: daemon-up + engine=initialized → PASS, no local worker spawn."""
        from superlocalmemory.cli import commands

        with patch("superlocalmemory.cli.daemon.is_daemon_running", return_value=True), \
             patch(
                 "superlocalmemory.cli.daemon.daemon_request",
                 return_value={"status": "ok", "engine": "initialized"},
             ), \
             patch("superlocalmemory.core.embeddings.EmbeddingService") as svc_cls:
            commands.cmd_warmup(Namespace())

        out = capsys.readouterr().out
        assert "[PASS]" in out
        assert "Daemon is running" in out
        assert "Semantic search is fully operational" in out
        # Critical: never tried to spawn a local EmbeddingService
        svc_cls.assert_not_called()

    def test_info_when_daemon_up_but_engine_not_initialized(self, capsys) -> None:
        """B2a: daemon-up + engine=warming_up → INFO + return, no local spawn."""
        from superlocalmemory.cli import commands

        with patch("superlocalmemory.cli.daemon.is_daemon_running", return_value=True), \
             patch(
                 "superlocalmemory.cli.daemon.daemon_request",
                 return_value={"status": "ok", "engine": "warming_up"},
             ), \
             patch("superlocalmemory.core.embeddings.EmbeddingService") as svc_cls:
            commands.cmd_warmup(Namespace())

        out = capsys.readouterr().out
        assert "[INFO]" in out
        assert "warming_up" in out or "engine state" in out
        # Don't race the daemon for the singleton lock
        svc_cls.assert_not_called()

    def test_info_when_health_response_missing_engine_key(self, capsys) -> None:
        """B2a: defensive — daemon up but /health returns no 'engine' field."""
        from superlocalmemory.cli import commands

        with patch("superlocalmemory.cli.daemon.is_daemon_running", return_value=True), \
             patch(
                 "superlocalmemory.cli.daemon.daemon_request",
                 return_value={"status": "ok"},  # no engine key
             ), \
             patch("superlocalmemory.core.embeddings.EmbeddingService") as svc_cls:
            commands.cmd_warmup(Namespace())

        out = capsys.readouterr().out
        assert "[INFO]" in out
        assert "unknown" in out
        svc_cls.assert_not_called()


class TestWarmupDaemonDownFallback:
    """When daemon is unreachable, fall through to the original local-warmup path."""

    def test_falls_through_when_daemon_not_running(self, capsys) -> None:
        """B2a: daemon down → run local EmbeddingService warmup."""
        from superlocalmemory.cli import commands

        # Stub a healthy local service so the local path completes successfully
        fake_svc = type("FakeSvc", (), {"is_available": True})()
        fake_svc.embed = lambda _t: [0.0] * 768

        with patch("superlocalmemory.cli.daemon.is_daemon_running", return_value=False), \
             patch(
                 "superlocalmemory.core.embeddings.EmbeddingService",
                 return_value=fake_svc,
             ) as svc_cls:
            commands.cmd_warmup(Namespace())

        # Local path was taken — Step 1 message printed AND service was instantiated
        out = capsys.readouterr().out
        assert "Step 1/3" in out
        svc_cls.assert_called_once()

    def test_falls_through_when_daemon_probe_raises(self, capsys) -> None:
        """B2a: any exception during daemon probe is non-fatal — local warmup runs."""
        from superlocalmemory.cli import commands

        fake_svc = type("FakeSvc", (), {"is_available": True})()
        fake_svc.embed = lambda _t: [0.0] * 768

        with patch(
            "superlocalmemory.cli.daemon.is_daemon_running",
            side_effect=RuntimeError("daemon module borked"),
        ), patch(
            "superlocalmemory.core.embeddings.EmbeddingService",
            return_value=fake_svc,
        ) as svc_cls:
            commands.cmd_warmup(Namespace())

        out = capsys.readouterr().out
        assert "Step 1/3" in out
        svc_cls.assert_called_once()

    def test_local_path_failure_still_calls_diagnose(self, capsys) -> None:
        """Backwards-compat: when local warmup fails, _warmup_diagnose still fires."""
        from superlocalmemory.cli import commands

        fake_svc = type("FakeSvc", (), {"is_available": True})()
        fake_svc.embed = lambda _t: None  # simulate subprocess returning nothing

        with patch("superlocalmemory.cli.daemon.is_daemon_running", return_value=False), \
             patch(
                 "superlocalmemory.core.embeddings.EmbeddingService",
                 return_value=fake_svc,
             ), \
             patch.object(commands, "_warmup_diagnose") as diag:
            commands.cmd_warmup(Namespace())

        out = capsys.readouterr().out
        assert "[FAIL]" in out
        diag.assert_called_once()
