#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Rate Limiter
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
"""

"""
Lightweight rate limiter using sliding window algorithm.
Pure stdlib — no external dependencies.

Defaults:
    Write endpoints: 100 req/min per IP
    Read endpoints: 300 req/min per IP

Configurable via environment variables:
    SLM_RATE_LIMIT_WRITE=100
    SLM_RATE_LIMIT_READ=300
    SLM_RATE_LIMIT_WINDOW=60
"""

import os
import time
import threading
from collections import defaultdict
from typing import Tuple

import logging
logger = logging.getLogger("superlocalmemory.ratelimit")

# Configurable via env vars
WRITE_LIMIT = int(os.environ.get('SLM_RATE_LIMIT_WRITE', '100'))
READ_LIMIT = int(os.environ.get('SLM_RATE_LIMIT_READ', '300'))
WINDOW_SECONDS = int(os.environ.get('SLM_RATE_LIMIT_WINDOW', '60'))


class RateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """
        Check if request is allowed for this client.

        Returns:
            (allowed: bool, remaining: int) — whether request is allowed
            and how many requests remain in the window
        """
        now = time.time()
        cutoff = now - self.window

        with self._lock:
            # Remove expired entries
            self._requests[client_id] = [
                t for t in self._requests[client_id] if t > cutoff
            ]

            current = len(self._requests[client_id])

            if current >= self.max_requests:
                return False, 0

            self._requests[client_id].append(now)
            return True, self.max_requests - current - 1

    def cleanup(self):
        """Remove stale entries for clients that haven't made requests recently."""
        now = time.time()
        cutoff = now - self.window * 2  # Keep 2 windows of data

        with self._lock:
            stale_keys = [
                k for k, v in self._requests.items()
                if not v or max(v) < cutoff
            ]
            for k in stale_keys:
                del self._requests[k]


# Singleton instances for write and read endpoints
write_limiter = RateLimiter(max_requests=WRITE_LIMIT, window_seconds=WINDOW_SECONDS)
read_limiter = RateLimiter(max_requests=READ_LIMIT, window_seconds=WINDOW_SECONDS)
