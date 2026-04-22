# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Queue-backed dispatcher coordinator.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from superlocalmemory.core import rate_limit as rl
from superlocalmemory.core import recall_queue as rq
from superlocalmemory.core.engine_lock import EngineRWLock


class QueueDispatcher:
    """Coordinates rate-limit check, enqueue, and poll for callers."""

    def __init__(
        self,
        *,
        db_path: Path | str,
        global_rps: float = 100.0,
        per_pid_rps: float = 30.0,
        per_agent_rps: float = 10.0,
    ) -> None:
        self.queue = rq.RecallQueue(db_path=db_path)
        self.engine_lock = EngineRWLock()
        self._rate = rl.LayeredRateLimiter(
            global_rps=global_rps,
            per_pid_rps=per_pid_rps,
            per_agent_rps=per_agent_rps,
        )
        # Module handles kept for test introspection.
        self.rl = rl
        self.rq = rq

    def _check_rate(self, *, pid: int, agent_id: str | None) -> None:
        self._rate.check_and_consume(pid=pid, agent_id=agent_id)

    def dispatch(
        self,
        *,
        query: str,
        limit_n: int,
        mode: str,
        agent_id: str,
        session_id: str,
        tenant_id: str = "",
        namespace: str = "",
        priority: str = "high",
        stall_timeout_s: float = 25.0,
        timeout_s: float = 30.0,
    ) -> dict[str, Any]:
        self._check_rate(pid=os.getpid(), agent_id=agent_id)
        rid = self.queue.enqueue(
            query=query, limit_n=limit_n, mode=mode,
            agent_id=agent_id, session_id=session_id,
            tenant_id=tenant_id, namespace=namespace,
            priority=priority, stall_timeout_s=stall_timeout_s,
        )
        try:
            return self.queue.poll_result(rid, timeout_s=timeout_s)
        finally:
            self.queue.unsubscribe(rid)

    def close(self) -> None:
        self.queue.close()
