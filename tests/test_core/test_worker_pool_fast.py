# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""WorkerPool recall request shaping."""

from __future__ import annotations


def test_worker_pool_recall_forwards_fast_flag(monkeypatch):
    from superlocalmemory.core.worker_pool import WorkerPool

    pool = WorkerPool()
    sent = {}

    def _fake_send(payload):
        sent.update(payload)
        return {"ok": True}

    monkeypatch.setattr(pool, "_send", _fake_send)

    assert pool.recall("q", limit=3, session_id="s-1", fast=True) == {"ok": True}
    assert sent == {
        "cmd": "recall",
        "query": "q",
        "limit": 3,
        "session_id": "s-1",
        "fast": True,
    }
