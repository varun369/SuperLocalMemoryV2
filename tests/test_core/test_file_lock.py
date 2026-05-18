# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for core.file_lock — cross-platform single-holder file lock."""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

import pytest


def _imports():
    from superlocalmemory.core import file_lock as fl
    return fl


def test_lock_acquire_release(tmp_path: Path) -> None:
    fl = _imports()
    lock_file = tmp_path / "d.lock"
    with fl.exclusive_lock(lock_file) as h:
        assert h is not None
    # After release, file exists and another lock can be taken
    with fl.exclusive_lock(lock_file):
        pass


def test_double_acquire_in_same_process_rejected(tmp_path: Path) -> None:
    fl = _imports()
    lock_file = tmp_path / "d.lock"
    with fl.exclusive_lock(lock_file):
        with pytest.raises(fl.LockHeldError):
            with fl.exclusive_lock(lock_file):
                pass


def _child_tries_lock(lock_path: str, result_queue: multiprocessing.Queue) -> None:
    from superlocalmemory.core import file_lock as fl
    try:
        with fl.exclusive_lock(Path(lock_path), timeout_s=0.1):
            result_queue.put("acquired")
    except fl.LockHeldError:
        result_queue.put("held")
    except Exception as exc:
        result_queue.put(f"error:{exc}")


def test_second_process_cannot_acquire(tmp_path: Path) -> None:
    fl = _imports()
    lock_file = tmp_path / "d.lock"
    ctx = multiprocessing.get_context("spawn")
    # 30s timeout: CI runners cold-import the full dep tree (torch, onnxruntime)
    # which takes ~5-15s before the child logic even starts.
    _JOIN_TIMEOUT = 30.0
    with fl.exclusive_lock(lock_file):
        q: multiprocessing.Queue = ctx.Queue()
        p = ctx.Process(target=_child_tries_lock, args=(str(lock_file), q))
        p.start()
        p.join(timeout=_JOIN_TIMEOUT)
        assert p.exitcode == 0, (
            f"Child process did not finish within {_JOIN_TIMEOUT}s "
            f"(exitcode={p.exitcode}). CI cold-start too slow?"
        )
        result = q.get(timeout=2.0)
    assert result == "held", f"Expected 'held', got {result}"


def test_released_lock_allows_second_process(tmp_path: Path) -> None:
    fl = _imports()
    lock_file = tmp_path / "d.lock"
    with fl.exclusive_lock(lock_file):
        pass  # release
    ctx = multiprocessing.get_context("spawn")
    _JOIN_TIMEOUT = 30.0
    q: multiprocessing.Queue = ctx.Queue()
    p = ctx.Process(target=_child_tries_lock, args=(str(lock_file), q))
    p.start()
    p.join(timeout=_JOIN_TIMEOUT)
    assert p.exitcode == 0, (
        f"Child process did not finish within {_JOIN_TIMEOUT}s "
        f"(exitcode={p.exitcode}). CI cold-start too slow?"
    )
    assert q.get(timeout=2.0) == "acquired"
