# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for core.db_pool."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

import pytest


def _imports():
    from superlocalmemory.core import db_pool
    return db_pool


def _make_pool(tmp_path: Path, size: int = 4):
    from superlocalmemory.core.safe_fs import _safe_open_db
    pool_cls = _imports().ConnectionPool
    return pool_cls(
        opener=lambda: _safe_open_db(tmp_path / "t.db"),
        size=size,
    )


def test_pool_acquires_and_releases(tmp_path: Path) -> None:
    pool = _make_pool(tmp_path, size=2)
    with pool.acquire() as conn:
        assert isinstance(conn, sqlite3.Connection)
        conn.execute("CREATE TABLE IF NOT EXISTS t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
    with pool.acquire() as conn2:
        assert conn2.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    pool.close()


def test_pool_reuses_connections(tmp_path: Path) -> None:
    pool = _make_pool(tmp_path, size=1)
    with pool.acquire() as c1:
        id1 = id(c1)
    with pool.acquire() as c2:
        id2 = id(c2)
    assert id1 == id2, "Single-slot pool must reuse the same connection"
    pool.close()


def test_pool_size_gate_blocks_when_saturated(tmp_path: Path) -> None:
    pool = _make_pool(tmp_path, size=1)
    released = threading.Event()
    acquired_second = threading.Event()

    def holder() -> None:
        with pool.acquire():
            released.wait(timeout=2.0)

    def latecomer() -> None:
        with pool.acquire():
            acquired_second.set()

    t1 = threading.Thread(target=holder); t1.start()
    time.sleep(0.05)
    t2 = threading.Thread(target=latecomer); t2.start()
    assert not acquired_second.wait(timeout=0.2), "Second acquire should block"
    released.set()
    assert acquired_second.wait(timeout=1.0), "Second never acquired after release"
    t1.join(timeout=1.0); t2.join(timeout=1.0)
    pool.close()


def test_pool_exception_returns_connection(tmp_path: Path) -> None:
    pool = _make_pool(tmp_path, size=1)
    with pytest.raises(RuntimeError, match="boom"):
        with pool.acquire():
            raise RuntimeError("boom")
    acquired = threading.Event()

    def other() -> None:
        with pool.acquire():
            acquired.set()

    t = threading.Thread(target=other); t.start()
    assert acquired.wait(timeout=1.0), "Connection leaked after exception"
    t.join(timeout=1.0)
    pool.close()


def test_pool_close_closes_all_connections(tmp_path: Path) -> None:
    pool = _make_pool(tmp_path, size=2)
    conns = []
    with pool.acquire() as c:
        conns.append(c)
    with pool.acquire() as c:
        conns.append(c)
    pool.close()
    # After close, using a checked-out connection raises ProgrammingError
    for c in conns:
        with pytest.raises(sqlite3.ProgrammingError):
            c.execute("SELECT 1")
