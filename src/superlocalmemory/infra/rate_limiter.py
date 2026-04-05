# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com
"""Sliding-window rate limiter for per-agent request throttling.

Pure stdlib -- no external dependencies.  Thread-safe.

Defaults (configurable via env vars):
    SLM_RATE_LIMIT_WRITE  = 100 req / window
    SLM_RATE_LIMIT_READ   = 300 req / window
    SLM_RATE_LIMIT_WINDOW = 60  seconds
"""

import logging
import os
import threading
import time
from collections import defaultdict
from typing import Dict, List, Tuple

logger = logging.getLogger("superlocalmemory.ratelimit")

# ---------------------------------------------------------------------------
# Module-level defaults (overridable via environment)
# ---------------------------------------------------------------------------
WRITE_LIMIT = int(os.environ.get("SLM_RATE_LIMIT_WRITE", "100"))
READ_LIMIT = int(os.environ.get("SLM_RATE_LIMIT_READ", "300"))
WINDOW_SECONDS = int(os.environ.get("SLM_RATE_LIMIT_WINDOW", "60"))


class RateLimiter:
    """Thread-safe sliding-window rate limiter.

    Each *client_id* (agent name, IP, etc.) gets its own independent
    request window.  Expired timestamps are pruned lazily on every call
    to ``allow()`` or ``is_allowed()``.

    Args:
        max_requests: Maximum requests allowed per window.
        window_seconds: Length of the sliding window in seconds.
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    # ----- public API -----

    def allow(self, client_id: str) -> bool:
        """Check **and record** a request for *client_id*.

        Returns ``True`` when the request is allowed, ``False`` when the
        client has exceeded its limit for the current window.
        """
        allowed, _ = self.is_allowed(client_id)
        return allowed

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """Check and record a request.

        Returns:
            ``(allowed, remaining)`` -- whether the request is permitted
            and how many requests remain in the current window.
        """
        now = time.time()
        cutoff = now - self.window

        with self._lock:
            # Prune expired timestamps
            self._requests[client_id] = [
                t for t in self._requests[client_id] if t > cutoff
            ]

            current = len(self._requests[client_id])

            if current >= self.max_requests:
                return False, 0

            self._requests[client_id].append(now)
            return True, self.max_requests - current - 1

    def remaining(self, client_id: str) -> int:
        """Return how many requests *client_id* has left without recording one."""
        now = time.time()
        cutoff = now - self.window

        with self._lock:
            active = [t for t in self._requests.get(client_id, []) if t > cutoff]
            return max(0, self.max_requests - len(active))

    def reset(self, client_id: str) -> None:
        """Clear all recorded requests for *client_id*."""
        with self._lock:
            self._requests.pop(client_id, None)

    def cleanup(self) -> int:
        """Remove stale entries for clients with no recent requests.

        Returns:
            Number of client entries removed.
        """
        now = time.time()
        cutoff = now - self.window * 2  # keep 2 windows of data

        with self._lock:
            stale = [
                k
                for k, v in self._requests.items()
                if not v or max(v) < cutoff
            ]
            for k in stale:
                del self._requests[k]
            return len(stale)

    def get_stats(self) -> dict:
        """Return a snapshot of limiter state."""
        with self._lock:
            return {
                "max_requests": self.max_requests,
                "window_seconds": self.window,
                "tracked_clients": len(self._requests),
            }


# ---------------------------------------------------------------------------
# Module-level convenience singletons
# ---------------------------------------------------------------------------
write_limiter = RateLimiter(max_requests=WRITE_LIMIT, window_seconds=WINDOW_SECONDS)
read_limiter = RateLimiter(max_requests=READ_LIMIT, window_seconds=WINDOW_SECONDS)
