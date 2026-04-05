# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file

"""Tests for TemporalChecker — stale marking, deletion detection, bulk verify."""

from __future__ import annotations

import pytest

from superlocalmemory.code_graph.bridge.temporal_checker import (
    DeletedCodeMemory,
    StaleLink,
    TemporalChecker,
)
from superlocalmemory.code_graph.database import CodeGraphDatabase
from superlocalmemory.code_graph.models import (
    CodeMemoryLink,
    GraphNode,
    LinkType,
    NodeKind,
)


@pytest.fixture
def checker(db: CodeGraphDatabase) -> TemporalChecker:
    return TemporalChecker(db)


def _insert_node(db: CodeGraphDatabase, node_id: str, name: str) -> None:
    db.upsert_node(GraphNode(
        node_id=node_id,
        kind=NodeKind.FUNCTION,
        name=name,
        qualified_name=f"mod.py::{name}",
        file_path="mod.py",
        language="python",
    ))


def _insert_link(
    db: CodeGraphDatabase,
    *,
    link_id: str,
    code_node_id: str,
    slm_fact_id: str,
    is_stale: bool = False,
) -> None:
    db.upsert_link(CodeMemoryLink(
        link_id=link_id,
        code_node_id=code_node_id,
        slm_fact_id=slm_fact_id,
        link_type=LinkType.MENTIONS,
        confidence=0.9,
        created_at="2026-01-01",
        last_verified="2026-01-01",
        is_stale=is_stale,
    ))


class TestMarkLinksStale:
    """Test mark_links_stale."""

    def test_marks_single_link(
        self, db: CodeGraphDatabase, checker: TemporalChecker,
    ) -> None:
        _insert_node(db, "n1", "func_a")
        _insert_link(db, link_id="L1", code_node_id="n1", slm_fact_id="f1")

        count = checker.mark_links_stale("n1")
        assert count == 1

        links = db.get_links_for_node("n1")
        assert len(links) == 1
        assert links[0].is_stale is True

    def test_marks_multiple_links(
        self, db: CodeGraphDatabase, checker: TemporalChecker,
    ) -> None:
        _insert_node(db, "n1", "func_a")
        _insert_link(db, link_id="L1", code_node_id="n1", slm_fact_id="f1")
        _insert_link(db, link_id="L2", code_node_id="n1", slm_fact_id="f2")
        _insert_link(db, link_id="L3", code_node_id="n1", slm_fact_id="f3")

        count = checker.mark_links_stale("n1")
        assert count == 3

    def test_skips_already_stale(
        self, db: CodeGraphDatabase, checker: TemporalChecker,
    ) -> None:
        _insert_node(db, "n1", "func_a")
        _insert_link(db, link_id="L1", code_node_id="n1",
                     slm_fact_id="f1", is_stale=True)
        _insert_link(db, link_id="L2", code_node_id="n1", slm_fact_id="f2")

        count = checker.mark_links_stale("n1")
        assert count == 1  # Only the non-stale one

    def test_no_links_returns_zero(self, checker: TemporalChecker) -> None:
        count = checker.mark_links_stale("nonexistent")
        assert count == 0


class TestCheckStaleLinks:
    """Test check_stale_links."""

    def test_returns_stale_links(
        self, db: CodeGraphDatabase, checker: TemporalChecker,
    ) -> None:
        _insert_node(db, "n1", "func_a")
        _insert_link(db, link_id="L1", code_node_id="n1",
                     slm_fact_id="f1", is_stale=True)
        _insert_link(db, link_id="L2", code_node_id="n1", slm_fact_id="f2")

        stale = checker.check_stale_links()
        assert len(stale) == 1
        assert stale[0].link_id == "L1"
        assert stale[0].qualified_name == "mod.py::func_a"

    def test_no_stale_returns_empty(
        self, db: CodeGraphDatabase, checker: TemporalChecker,
    ) -> None:
        _insert_node(db, "n1", "func_a")
        _insert_link(db, link_id="L1", code_node_id="n1", slm_fact_id="f1")

        stale = checker.check_stale_links()
        assert stale == []

    def test_deleted_node_shows_deleted(
        self, db: CodeGraphDatabase, checker: TemporalChecker,
    ) -> None:
        """Link to a deleted node should show 'deleted' as qualified_name."""
        # Use raw connection with FK off to simulate orphaned link
        import sqlite3
        conn = sqlite3.connect(str(db.db_path))
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute(
            "INSERT INTO code_memory_links "
            "(link_id, code_node_id, slm_fact_id, link_type, confidence, "
            "created_at, is_stale) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("L1", "ghost", "f1", "mentions", 0.9, "2026-01-01", 1),
        )
        conn.commit()
        conn.close()

        stale = checker.check_stale_links()
        assert len(stale) == 1
        assert stale[0].qualified_name == "deleted"


class TestGetMemoriesForDeletedCode:
    """Test get_memories_for_deleted_code."""

    def test_finds_orphaned_links(
        self, db: CodeGraphDatabase, checker: TemporalChecker,
    ) -> None:
        """Links whose code_node_id has no matching graph_nodes row."""
        import sqlite3
        conn = sqlite3.connect(str(db.db_path))
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute(
            "INSERT INTO code_memory_links "
            "(link_id, code_node_id, slm_fact_id, link_type, confidence, "
            "created_at, is_stale) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("L1", "deleted_node", "f1", "mentions", 0.9, "2026-01-01", 0),
        )
        conn.commit()
        conn.close()

        deleted = checker.get_memories_for_deleted_code()
        assert len(deleted) == 1
        assert deleted[0].fact_id == "f1"
        assert deleted[0].node_id == "deleted_node"

    def test_existing_nodes_excluded(
        self, db: CodeGraphDatabase, checker: TemporalChecker,
    ) -> None:
        _insert_node(db, "n1", "func_a")
        _insert_link(db, link_id="L1", code_node_id="n1", slm_fact_id="f1")

        deleted = checker.get_memories_for_deleted_code()
        assert deleted == []


class TestBulkVerify:
    """Test bulk_verify."""

    def test_marks_deleted_stale(
        self, db: CodeGraphDatabase, checker: TemporalChecker,
    ) -> None:
        _insert_node(db, "n1", "func_a")
        _insert_link(db, link_id="L1", code_node_id="n1", slm_fact_id="f1")

        # Insert orphaned link (FK off via raw connection)
        import sqlite3
        conn = sqlite3.connect(str(db.db_path))
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute(
            "INSERT INTO code_memory_links "
            "(link_id, code_node_id, slm_fact_id, link_type, confidence, "
            "created_at, is_stale) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("L2", "deleted_node", "f2", "mentions", 0.9, "2026-01-01", 0),
        )
        conn.commit()
        conn.close()

        result = checker.bulk_verify()
        assert result["verified"] == 1
        assert result["marked_stale"] == 1
        assert result["already_stale"] == 0

    def test_already_stale_counted(
        self, db: CodeGraphDatabase, checker: TemporalChecker,
    ) -> None:
        _insert_node(db, "n1", "func_a")
        _insert_link(db, link_id="L1", code_node_id="n1",
                     slm_fact_id="f1", is_stale=True)

        result = checker.bulk_verify()
        assert result["already_stale"] == 1

    def test_empty_db(self, checker: TemporalChecker) -> None:
        result = checker.bulk_verify()
        assert result == {"verified": 0, "marked_stale": 0, "already_stale": 0}
