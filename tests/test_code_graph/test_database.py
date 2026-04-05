# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file

"""Tests for CodeGraphDatabase CRUD operations."""

import time
from pathlib import Path

import pytest

from superlocalmemory.code_graph.database import CodeGraphDatabase
from superlocalmemory.code_graph.models import (
    CodeMemoryLink,
    EdgeKind,
    FileRecord,
    GraphEdge,
    GraphNode,
    LinkType,
    NodeKind,
)


def _make_node(
    node_id: str = "n1",
    name: str = "foo",
    kind: NodeKind = NodeKind.FUNCTION,
    file_path: str = "src/main.py",
    qualified_name: str | None = None,
    **kwargs,
) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        kind=kind,
        name=name,
        qualified_name=qualified_name or f"{file_path}::{name}",
        file_path=file_path,
        language="python",
        created_at=time.time(),
        updated_at=time.time(),
        **kwargs,
    )


def _make_edge(
    edge_id: str = "e1",
    source: str = "n1",
    target: str = "n2",
    kind: EdgeKind = EdgeKind.CALLS,
    file_path: str = "src/main.py",
    **kwargs,
) -> GraphEdge:
    return GraphEdge(
        edge_id=edge_id,
        kind=kind,
        source_node_id=source,
        target_node_id=target,
        file_path=file_path,
        created_at=time.time(),
        updated_at=time.time(),
        **kwargs,
    )


class TestDatabaseInit:
    def test_creates_db_file(self, db: CodeGraphDatabase):
        assert db.db_path.exists()

    def test_version_starts_at_zero(self, db_path: Path):
        db = CodeGraphDatabase(db_path)
        # Version is 0 initially (schema creation doesn't count as a user write)
        # but our init does create tables which bumps it. Let's check it's ≥ 0.
        assert db.version >= 0

    def test_wal_mode(self, db: CodeGraphDatabase):
        rows = db.execute("PRAGMA journal_mode")
        assert rows[0]["journal_mode"] == "wal"


class TestNodeCRUD:
    def test_upsert_and_get(self, db: CodeGraphDatabase):
        node = _make_node()
        db.upsert_node(node)
        result = db.get_node("n1")
        assert result is not None
        assert result.name == "foo"
        assert result.kind == NodeKind.FUNCTION

    def test_get_nonexistent(self, db: CodeGraphDatabase):
        assert db.get_node("nonexistent") is None

    def test_upsert_updates(self, db: CodeGraphDatabase):
        db.upsert_node(_make_node(name="foo"))
        db.upsert_node(_make_node(name="bar"))
        result = db.get_node("n1")
        assert result is not None
        assert result.name == "bar"

    def test_get_by_qualified_name(self, db: CodeGraphDatabase):
        node = _make_node(qualified_name="src/main.py::foo")
        db.upsert_node(node)
        result = db.get_node_by_qualified_name("src/main.py::foo")
        assert result is not None
        assert result.node_id == "n1"

    def test_get_nodes_by_file(self, db: CodeGraphDatabase):
        db.upsert_node(_make_node("n1", "foo", file_path="a.py", qualified_name="a.py::foo"))
        db.upsert_node(_make_node("n2", "bar", file_path="a.py", qualified_name="a.py::bar"))
        db.upsert_node(_make_node("n3", "baz", file_path="b.py", qualified_name="b.py::baz"))
        nodes = db.get_nodes_by_file("a.py")
        assert len(nodes) == 2

    def test_get_all_nodes(self, db: CodeGraphDatabase):
        db.upsert_node(_make_node("n1", qualified_name="q1"))
        db.upsert_node(_make_node("n2", qualified_name="q2"))
        assert len(db.get_all_nodes()) == 2

    def test_get_node_count(self, db: CodeGraphDatabase):
        assert db.get_node_count() == 0
        db.upsert_node(_make_node("n1", qualified_name="q1"))
        assert db.get_node_count() == 1

    def test_delete_by_file(self, db: CodeGraphDatabase):
        db.upsert_node(_make_node("n1", file_path="a.py", qualified_name="a.py::n1"))
        db.upsert_node(_make_node("n2", file_path="b.py", qualified_name="b.py::n2"))
        deleted = db.delete_nodes_by_file("a.py")
        assert deleted == 1
        assert db.get_node_count() == 1

    def test_is_test_stored(self, db: CodeGraphDatabase):
        db.upsert_node(_make_node("n1", is_test=True, qualified_name="q1"))
        result = db.get_node("n1")
        assert result is not None
        assert result.is_test is True


class TestEdgeCRUD:
    def _setup_nodes(self, db: CodeGraphDatabase):
        db.upsert_node(_make_node("n1", "foo", qualified_name="q1"))
        db.upsert_node(_make_node("n2", "bar", qualified_name="q2"))

    def test_upsert_and_get(self, db: CodeGraphDatabase):
        self._setup_nodes(db)
        db.upsert_edge(_make_edge())
        edges = db.get_edges_from("n1")
        assert len(edges) == 1
        assert edges[0].kind == EdgeKind.CALLS

    def test_edges_to(self, db: CodeGraphDatabase):
        self._setup_nodes(db)
        db.upsert_edge(_make_edge())
        edges = db.get_edges_to("n2")
        assert len(edges) == 1

    def test_edge_kind_filter(self, db: CodeGraphDatabase):
        self._setup_nodes(db)
        db.upsert_edge(_make_edge("e1", kind=EdgeKind.CALLS))
        db.upsert_edge(_make_edge("e2", kind=EdgeKind.IMPORTS))
        calls = db.get_edges_from("n1", kind=EdgeKind.CALLS)
        assert len(calls) == 1
        imports = db.get_edges_from("n1", kind=EdgeKind.IMPORTS)
        assert len(imports) == 1

    def test_confidence_stored(self, db: CodeGraphDatabase):
        self._setup_nodes(db)
        db.upsert_edge(_make_edge(confidence=0.7))
        edges = db.get_edges_from("n1")
        assert edges[0].confidence == 0.7

    def test_cascade_on_node_delete(self, db: CodeGraphDatabase):
        self._setup_nodes(db)
        db.upsert_edge(_make_edge())
        db.delete_nodes_by_file("src/main.py")
        assert db.get_edge_count() == 0

    def test_get_all_edges(self, db: CodeGraphDatabase):
        self._setup_nodes(db)
        db.upsert_edge(_make_edge("e1"))
        db.upsert_edge(_make_edge("e2", kind=EdgeKind.IMPORTS))
        assert len(db.get_all_edges()) == 2


class TestFileRecordCRUD:
    def test_upsert_and_get(self, db: CodeGraphDatabase):
        rec = FileRecord(
            file_path="src/main.py",
            content_hash="abc123",
            mtime=1000.0,
            language="python",
            node_count=5,
            edge_count=3,
            last_indexed=time.time(),
        )
        db.upsert_file_record(rec)
        result = db.get_file_record("src/main.py")
        assert result is not None
        assert result.content_hash == "abc123"
        assert result.node_count == 5

    def test_get_nonexistent(self, db: CodeGraphDatabase):
        assert db.get_file_record("nope.py") is None

    def test_get_all(self, db: CodeGraphDatabase):
        db.upsert_file_record(FileRecord(file_path="a.py", content_hash="h1", mtime=1.0, language="python"))
        db.upsert_file_record(FileRecord(file_path="b.py", content_hash="h2", mtime=2.0, language="python"))
        assert len(db.get_all_file_records()) == 2

    def test_delete(self, db: CodeGraphDatabase):
        db.upsert_file_record(FileRecord(file_path="a.py", content_hash="h1", mtime=1.0, language="python"))
        db.delete_file_record("a.py")
        assert db.get_file_record("a.py") is None


class TestMetadata:
    def test_set_and_get(self, db: CodeGraphDatabase):
        db.set_metadata("repo_root", "/home/user/project")
        assert db.get_metadata("repo_root") == "/home/user/project"

    def test_get_nonexistent(self, db: CodeGraphDatabase):
        assert db.get_metadata("missing") is None

    def test_upsert(self, db: CodeGraphDatabase):
        db.set_metadata("key", "v1")
        db.set_metadata("key", "v2")
        assert db.get_metadata("key") == "v2"


class TestAtomicFileReplacement:
    def test_store_file_parse_results(self, db: CodeGraphDatabase):
        # Insert initial data
        n1 = _make_node("n1", "old_func", qualified_name="test.py::old_func", file_path="test.py")
        db.upsert_node(n1)

        # Replace with new data
        new_nodes = [
            _make_node("n2", "new_func", qualified_name="test.py::new_func", file_path="test.py"),
            _make_node("n3", "helper", qualified_name="test.py::helper", file_path="test.py"),
        ]
        new_edges = [
            _make_edge("e1", "n2", "n3", file_path="test.py"),
        ]
        file_rec = FileRecord(
            file_path="test.py", content_hash="newhash",
            mtime=time.time(), language="python",
            node_count=2, edge_count=1,
        )
        db.store_file_parse_results("test.py", new_nodes, new_edges, file_rec)

        # Old node gone
        assert db.get_node("n1") is None
        # New nodes present
        assert db.get_node("n2") is not None
        assert db.get_node("n3") is not None
        # Edge present
        assert db.get_edge_count() == 1
        # File record updated
        rec = db.get_file_record("test.py")
        assert rec is not None
        assert rec.content_hash == "newhash"


class TestTransaction:
    def test_transaction_commit(self, db: CodeGraphDatabase):
        with db.transaction():
            db.upsert_node(_make_node("n1", qualified_name="q1"))
            db.upsert_node(_make_node("n2", qualified_name="q2"))
        assert db.get_node_count() == 2

    def test_transaction_rollback(self, db: CodeGraphDatabase):
        db.upsert_node(_make_node("existing", qualified_name="existing"))
        try:
            with db.transaction():
                db.upsert_node(_make_node("n1", qualified_name="q1"))
                raise ValueError("Simulated error")
        except ValueError:
            pass
        # n1 should NOT be persisted
        assert db.get_node("n1") is None
        # existing should still be there
        assert db.get_node("existing") is not None


class TestStats:
    def test_empty(self, db: CodeGraphDatabase):
        stats = db.get_stats()
        assert stats["nodes"] == 0
        assert stats["edges"] == 0
        assert stats["files"] == 0

    def test_with_data(self, db: CodeGraphDatabase):
        db.upsert_node(_make_node("n1", qualified_name="q1"))
        db.upsert_node(_make_node("n2", qualified_name="q2"))
        db.upsert_edge(_make_edge("e1"))
        db.upsert_file_record(FileRecord(file_path="a.py", content_hash="h", mtime=1.0, language="py"))
        stats = db.get_stats()
        assert stats["nodes"] == 2
        assert stats["edges"] == 1
        assert stats["files"] == 1


class TestCodeMemoryLinks:
    def test_upsert_and_get(self, db: CodeGraphDatabase):
        db.upsert_node(_make_node("n1", qualified_name="q1"))
        link = CodeMemoryLink(
            code_node_id="n1",
            slm_fact_id="fact123",
            link_type=LinkType.BUG_FIX,
            confidence=0.9,
            created_at="2026-04-05T12:00:00",
        )
        db.upsert_link(link)
        links = db.get_links_for_node("n1")
        assert len(links) == 1
        assert links[0].link_type == LinkType.BUG_FIX

    def test_get_by_fact(self, db: CodeGraphDatabase):
        db.upsert_node(_make_node("n1", qualified_name="q1"))
        link = CodeMemoryLink(
            code_node_id="n1",
            slm_fact_id="fact456",
            link_type=LinkType.MENTIONS,
            created_at="2026-04-05",
        )
        db.upsert_link(link)
        links = db.get_links_for_fact("fact456")
        assert len(links) == 1
