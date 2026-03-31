# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for HeartbeatMonitor — daemon thread monitoring parent process liveness.

TDD order 2: HeartbeatMonitor has no dependencies.
Test: T8.
"""

from __future__ import annotations

import subprocess
import threading
import os

import pytest


class TestHeartbeatDetectsDeadParent:
    """T8: Heartbeat triggers shutdown callback when parent dies."""

    def test_heartbeat_detects_dead_parent(self) -> None:
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor

        proc = subprocess.Popen(["true"])  # exits immediately
        proc.wait()
        dead_pid = proc.pid

        callback_called = threading.Event()

        def on_parent_dead() -> None:
            callback_called.set()

        monitor = HeartbeatMonitor(
            dead_pid, interval_seconds=1, shutdown_callback=on_parent_dead
        )
        monitor.start()
        try:
            assert callback_called.wait(
                timeout=5.0
            ), "Callback was not called within 5 seconds"
        finally:
            monitor.stop()


class TestHeartbeatSkipsLiveParent:
    """Heartbeat does NOT trigger shutdown when parent is alive."""

    def test_heartbeat_skips_live_parent(self) -> None:
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor

        callback_called = threading.Event()

        def on_parent_dead() -> None:
            callback_called.set()

        # Use own PID as "parent" -- guaranteed alive
        monitor = HeartbeatMonitor(
            os.getpid(), interval_seconds=1, shutdown_callback=on_parent_dead
        )
        monitor.start()
        try:
            # Should NOT fire within 3 seconds
            assert not callback_called.wait(
                timeout=3.0
            ), "Callback should NOT have been called for a live parent"
        finally:
            monitor.stop()


class TestHeartbeatDaemonThread:
    """Heartbeat thread is a daemon and can be stopped cleanly."""

    def test_thread_is_daemon(self) -> None:
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor

        monitor = HeartbeatMonitor(
            os.getpid(), interval_seconds=60, shutdown_callback=lambda: None
        )
        monitor.start()
        try:
            assert monitor.is_running is True
        finally:
            monitor.stop()
        assert monitor.is_running is False

    def test_double_start_no_error(self) -> None:
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor

        monitor = HeartbeatMonitor(
            os.getpid(), interval_seconds=60, shutdown_callback=lambda: None
        )
        monitor.start()
        monitor.start()  # Should not raise
        monitor.stop()

    def test_refuse_monitor_pid_1(self) -> None:
        """Refuse to monitor PID <= 1."""
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor

        monitor = HeartbeatMonitor(
            1, interval_seconds=60, shutdown_callback=lambda: None
        )
        monitor.start()
        # Should not actually start monitoring
        assert monitor.is_running is False

    def test_callback_exception_handled(self) -> None:
        """Heartbeat handles callback exceptions gracefully."""
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor

        proc = subprocess.Popen(["true"])
        proc.wait()
        dead_pid = proc.pid

        callback_ran = threading.Event()

        def bad_callback() -> None:
            callback_ran.set()
            raise RuntimeError("Simulated callback failure")

        monitor = HeartbeatMonitor(
            dead_pid, interval_seconds=1, shutdown_callback=bad_callback
        )
        monitor.start()
        try:
            assert callback_ran.wait(timeout=5.0), "Callback should have run"
        finally:
            monitor.stop()


# ---------------------------------------------------------------------------
# Coverage gap tests: stop() when not running (line 76)
# ---------------------------------------------------------------------------
class TestHeartbeatStopWhenNotRunning:
    """Cover the early return in stop() when not running."""

    def test_stop_when_not_started(self) -> None:
        """Calling stop() before start() does not raise."""
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor

        monitor = HeartbeatMonitor(
            os.getpid(), interval_seconds=60, shutdown_callback=lambda: None
        )
        # Never started -- stop should just return
        monitor.stop()
        assert monitor.is_running is False

    def test_double_stop_no_error(self) -> None:
        """Calling stop() twice does not raise."""
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor

        monitor = HeartbeatMonitor(
            os.getpid(), interval_seconds=60, shutdown_callback=lambda: None
        )
        monitor.start()
        monitor.stop()
        monitor.stop()  # Second stop when not running
        assert monitor.is_running is False


# ---------------------------------------------------------------------------
# Coverage gap tests: _is_parent_alive PID <= 1 (line 130)
# ---------------------------------------------------------------------------
class TestIsParentAlivePidCheck:
    """Cover the _is_parent_alive pid <= 1 check and error paths."""

    def test_is_parent_alive_pid_0(self) -> None:
        """_is_parent_alive returns False for PID 0."""
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor

        monitor = HeartbeatMonitor(
            0, interval_seconds=60, shutdown_callback=lambda: None
        )
        # Access private method directly for coverage
        assert monitor._is_parent_alive() is False

    def test_is_parent_alive_pid_1(self) -> None:
        """_is_parent_alive returns False for PID 1."""
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor

        monitor = HeartbeatMonitor(
            1, interval_seconds=60, shutdown_callback=lambda: None
        )
        assert monitor._is_parent_alive() is False


# ---------------------------------------------------------------------------
# Coverage gap tests: _is_parent_alive PermissionError + OSError (lines 137-140)
# ---------------------------------------------------------------------------
class TestIsParentAliveErrors:
    """Cover PermissionError and OSError in _is_parent_alive."""

    def test_is_parent_alive_permission_error(self) -> None:
        """PermissionError means parent exists (conservative)."""
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor
        from unittest.mock import patch

        monitor = HeartbeatMonitor(
            99999, interval_seconds=60, shutdown_callback=lambda: None
        )

        with patch("os.kill", side_effect=PermissionError("Operation not permitted")):
            assert monitor._is_parent_alive() is True

    def test_is_parent_alive_os_error(self) -> None:
        """Generic OSError means parent is dead."""
        from superlocalmemory.infra.heartbeat_monitor import HeartbeatMonitor
        from unittest.mock import patch

        monitor = HeartbeatMonitor(
            99999, interval_seconds=60, shutdown_callback=lambda: None
        )

        with patch("os.kill", side_effect=OSError("EPERM")):
            assert monitor._is_parent_alive() is False
