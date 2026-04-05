# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Background Maintenance Scheduler.

V3.3.13: Periodically triggers Langevin/Ebbinghaus/Sheaf maintenance
so users don't need to call run_maintenance manually.

Configurable interval via ForgettingConfig.scheduler_interval_minutes.
Defaults to 30 min. Disabled during benchmarks (no config.forgetting.enabled).

Part of Qualixar | Author: Varun Pratap Bhardwaj
License: Elastic-2.0
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from superlocalmemory.core.config import SLMConfig
    from superlocalmemory.storage.database import DatabaseManager

logger = logging.getLogger(__name__)


class MaintenanceScheduler:
    """Background scheduler for periodic math maintenance.

    Runs Langevin/Sheaf/Fisher maintenance at configurable intervals.
    Thread-safe. Auto-stops on garbage collection or explicit stop().
    """

    def __init__(
        self,
        db: DatabaseManager,
        config: SLMConfig,
        profile_id: str = "default",
    ) -> None:
        self._db = db
        self._config = config
        self._profile_id = profile_id
        self._timer: threading.Timer | None = None
        self._running = False
        self._interval = config.forgetting.scheduler_interval_minutes * 60.0

    def start(self) -> None:
        """Start the periodic scheduler. Idempotent."""
        if self._running:
            return
        self._running = True
        self._schedule_next()
        logger.info(
            "Maintenance scheduler started (interval=%dm)",
            self._config.forgetting.scheduler_interval_minutes,
        )

    def stop(self) -> None:
        """Stop the scheduler. Idempotent."""
        self._running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        logger.info("Maintenance scheduler stopped")

    def _schedule_next(self) -> None:
        """Schedule the next maintenance run."""
        if not self._running:
            return
        self._timer = threading.Timer(self._interval, self._run)
        self._timer.daemon = True
        self._timer.start()

    def _run(self) -> None:
        """Execute maintenance and schedule next run."""
        if not self._running:
            return
        try:
            from superlocalmemory.core.maintenance import run_maintenance
            counts = run_maintenance(self._db, self._config, self._profile_id)
            logger.info("Scheduled maintenance complete: %s", counts)
        except Exception as exc:
            logger.warning("Scheduled maintenance failed: %s", exc)
        finally:
            self._schedule_next()

    def __del__(self) -> None:
        try:
            self.stop()
        except Exception:
            pass
