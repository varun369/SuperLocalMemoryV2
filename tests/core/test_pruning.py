# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3

"""Tests for pruning_engine.py — Sprint 5."""

from __future__ import annotations

import pytest
import sqlite3

from superlocalmemory.core.pruning_engine import prune_graph


class MockDB:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=()):
        cur = self.conn.execute(sql, params or ())
        self.conn.commit()
        rows = cur.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in rows]


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE graph_edges (
            source_id TEXT, target_id TEXT,
            edge_type TEXT DEFAULT 'related',
            weight REAL DEFAULT 1.0
        )
    """)
    conn.execute("""
        CREATE TABLE entity_blacklist (term TEXT PRIMARY KEY)
    """)
    conn.execute("""
        CREATE TABLE fact_access_log (
            entity_id TEXT, accessed_at TEXT
        )
    """)
    yield MockDB(conn)
    conn.close()


class TestPruning:
    def test_prune_empty_graph(self, db):
        stats = prune_graph(db)
        assert stats["edges_before"] == 0
        assert stats["total_removed"] == 0

    def test_dry_run_removes_nothing(self, db):
        db.execute(
            "INSERT INTO graph_edges VALUES ('a', 'b', 'related', 1.0)"
        )
        stats = prune_graph(db, dry_run=True)
        assert stats["total_removed"] >= 0
        # Verify edge still exists
        rows = db.execute("SELECT COUNT(*) as c FROM graph_edges")
        assert rows[0]["c"] == 1

    def test_garbage_edges_removed(self, db):
        db.execute("INSERT INTO entity_blacklist VALUES ('garbage')")
        db.execute(
            "INSERT INTO graph_edges VALUES ('garbage', 'b', 'related', 1.0)"
        )
        db.execute(
            "INSERT INTO graph_edges VALUES ('c', 'garbage', 'related', 1.0)"
        )
        stats = prune_graph(db)
        assert stats["garbage_removed"] == 2

    def test_prune_is_idempotent(self, db):
        db.execute("INSERT INTO entity_blacklist VALUES ('trash')")
        db.execute(
            "INSERT INTO graph_edges VALUES ('trash', 'x', 'bad', 1.0)"
        )
        stats1 = prune_graph(db)
        stats2 = prune_graph(db)
        assert stats2["garbage_removed"] == 0  # Already removed

    def test_stats_structure(self, db):
        stats = prune_graph(db)
        for key in ["chain_collapsed", "garbage_removed",
                     "low_activity_decayed", "total_removed",
                     "edges_before", "edges_after"]:
            assert key in stats, f"Missing key: {key}"
