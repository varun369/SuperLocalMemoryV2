# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Simple bounded SQLite connection pool.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from queue import Empty, Queue
from typing import Callable, Iterator


class ConnectionPool:
    """Bounded pool of SQLite connections created on-demand."""

    def __init__(
        self,
        opener: Callable[[], sqlite3.Connection],
        size: int = 8,
    ) -> None:
        if size < 1:
            raise ValueError("size must be >= 1")
        self._opener = opener
        self._size = size
        self._available: Queue[sqlite3.Connection] = Queue(maxsize=size)
        self._created = 0
        self._lock = threading.Lock()
        self._closed = False
        self._all: list[sqlite3.Connection] = []

    def _get_or_create(self, timeout: float | None) -> sqlite3.Connection:
        try:
            return self._available.get_nowait()
        except Empty:
            pass
        with self._lock:
            if self._closed:
                raise RuntimeError("pool is closed")
            if self._created < self._size:
                conn = self._opener()
                self._all.append(conn)
                self._created += 1
                return conn
        # Pool saturated — block for a returned connection
        try:
            return self._available.get(timeout=timeout)
        except Empty as exc:
            raise TimeoutError("timed out acquiring DB connection") from exc

    @contextmanager
    def acquire(self, timeout: float | None = 30.0) -> Iterator[sqlite3.Connection]:
        if self._closed:
            raise RuntimeError("pool is closed")
        conn = self._get_or_create(timeout)
        try:
            yield conn
        finally:
            if not self._closed:
                self._available.put(conn)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        for conn in self._all:
            try:
                conn.close()
            except Exception:
                pass
        self._all.clear()

    def size(self) -> int:
        return self._size
