# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 -- Parent Heartbeat Monitor.

Daemon thread that checks if the parent process (IDE/Claude session) is
still alive. If the parent dies, initiates graceful shutdown to prevent
zombie SLM processes consuming 1.5-2 GB each.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class HeartbeatMonitor:
    """Monitor parent process liveness via a daemon thread.

    When the parent PID is detected as dead, calls the provided
    shutdown_callback. The monitoring thread is a daemon thread
    (auto-dies with the main process per HR-06).
    """

    def __init__(
        self,
        parent_pid: int,
        interval_seconds: int,
        shutdown_callback: Callable[[], None],
    ) -> None:
        self._parent_pid = parent_pid
        self._interval = interval_seconds
        self._shutdown_callback = shutdown_callback
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    # -- Lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Start the heartbeat monitoring daemon thread."""
        if self._running:
            logger.warning("Heartbeat monitor already running")
            return

        # HR-02 equivalent: refuse to monitor PID 0 or 1
        if self._parent_pid <= 1:
            logger.warning(
                "Refusing to monitor PID %d (<= 1), heartbeat not started",
                self._parent_pid,
            )
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="slm-heartbeat",
            daemon=True,
        )
        self._thread.start()
        self._running = True
        logger.info(
            "Heartbeat monitor started: watching parent PID %d every %ds",
            self._parent_pid,
            self._interval,
        )

    def stop(self) -> None:
        """Stop the heartbeat monitor gracefully."""
        if not self._running:
            return

        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=self._interval + 2)

        self._running = False
        logger.info("Heartbeat monitor stopped")

    # -- Properties ---------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Whether the monitor thread is active."""
        return self._running

    # -- Internal -----------------------------------------------------------

    def _monitor_loop(self) -> None:
        """Heartbeat loop running in daemon thread.

        Uses threading.Event.wait(timeout) instead of time.sleep()
        because Event.wait() is immediately interruptible by stop(),
        while sleep() blocks for the full duration.
        """
        logger.debug(
            "Heartbeat loop started for parent PID %d", self._parent_pid
        )

        while not self._stop_event.is_set():
            stopped = self._stop_event.wait(timeout=self._interval)
            if stopped:
                break

            if not self._is_parent_alive():
                logger.warning(
                    "Parent PID %d died, initiating graceful shutdown",
                    self._parent_pid,
                )
                try:
                    self._shutdown_callback()
                except Exception:
                    logger.exception("Shutdown callback failed")
                break

        logger.debug("Heartbeat loop exited")

    def _is_parent_alive(self) -> bool:
        """Check if parent PID is still a running process.

        Conservative: returns True on PermissionError (parent exists
        but is owned by another user).
        """
        if self._parent_pid <= 1:
            return False

        try:
            os.kill(self._parent_pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # Alive, different user -- conservative
        except OSError:
            return False
