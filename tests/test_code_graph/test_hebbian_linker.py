# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file

"""Tests for HebbianLinker — subgraph detection, link creation, weight capping."""

from __future__ import annotations

from pathlib import Path

import pytest

from superlocalmemory.code_graph.bridge.hebbian_linker import (
    WEIGHT_BASE,
    WEIGHT_CAP,
    WEIGHT_PER_SHARED,
    HebbianLinker,
)
from superlocalmemory.code_graph.database import CodeGraphDatabase
from superlocalmemory.code_graph.graph_engine import GraphEngine
from superlocalmemory.code_graph.graph_store import GraphStore
from superlocalmemory.code_graph.models import (
    CodeMemoryLink,
    EdgeKind,
    GraphEdge,
    GraphNode,
    LinkType,
    NodeKind,
)


@pytest.fixture
def store(db: CodeGraphDatabase) -> GraphStore:
    return GraphStore(db)


@pytest.fixture
def engine(store: GraphStore) -> GraphEngine:
    return GraphEngine(store)


@pytest.fixture
def linker(db: CodeGraphDatabase, engine: GraphEngine) -> HebbianLinker:
    return HebbianLinker(db, engine)


def _setup_call_graph(db: CodeGraphDatabase) -> None:
    """Create a small call graph: A -> B -> C, D -> B."""
    for nid, name in [("A", "func_a"), ("B", "func_b"),
                       ("C", "func_c"), ("D", "func_d")]:
        db.upsert_node(GraphNode(
            node_id=nid,
            kind=NodeKind.FUNCTION,
            name=name,
            qualified_name=f"mod.py::{name}",
            file_path="mod.py",
            language="python",
        ))

    # A calls B
    db.upsert_edge(GraphEdge(
        edge_id="e_ab", kind=EdgeKind.CALLS,
        source_node_id="A", target_node_id="B", file_path="mod.py",
    ))
    # B calls C
    db.upsert_edge(GraphEdge(
        edge_id="e_bc", kind=EdgeKind.CALLS,
        source_node_id="B", target_node_id="C", file_path="mod.py",
    ))
    # D calls B
    db.upsert_edge(GraphEdge(
        edge_id="e_db", kind=EdgeKind.CALLS,
        source_node_id="D", target_node_id="B", file_path="mod.py",
    ))


def _insert_link(
    db: CodeGraphDatabase,
    *,
    link_id: str,
    code_node_id: str,
    slm_fact_id: str,
) -> None:
    db.upsert_link(CodeMemoryLink(
        link_id=link_id,
        code_node_id=code_node_id,
        slm_fact_id=slm_fact_id,
        link_type=LinkType.MENTIONS,
        confidence=0.9,
        created_at="2026-01-01",
        last_verified="2026-01-01",
        is_stale=False,
    ))


class TestHebbianLink:
    """Test Hebbian edge discovery."""

    def test_finds_shared_subgraph(
        self, db: CodeGraphDatabase, engine: GraphEngine, linker: HebbianLinker,
    ) -> None:
        """Two facts linked to nodes in same call neighborhood should associate."""
        _setup_call_graph(db)

        # fact-1 linked to A
        _insert_link(db, link_id="L1", code_node_id="A", slm_fact_id="fact-1")
        # fact-2 linked to B (A's callee, so in A's neighborhood)
        _insert_link(db, link_id="L2", code_node_id="B", slm_fact_id="fact-2")

        edges = linker.link("fact-1", ["A"])
        assert len(edges) == 1
        assert edges[0].source_fact_id == "fact-1"
        assert edges[0].target_fact_id == "fact-2"
        assert edges[0].shared_node_count >= 1

    def test_no_shared_subgraph(
        self, db: CodeGraphDatabase, engine: GraphEngine, linker: HebbianLinker,
    ) -> None:
        """Facts linked to disconnected nodes should not associate."""
        # Node X is isolated
        db.upsert_node(GraphNode(
            node_id="X", kind=NodeKind.FUNCTION, name="isolated",
            qualified_name="other.py::isolated", file_path="other.py",
            language="python",
        ))
        db.upsert_node(GraphNode(
            node_id="Y", kind=NodeKind.FUNCTION, name="lonely",
            qualified_name="lone.py::lonely", file_path="lone.py",
            language="python",
        ))

        _insert_link(db, link_id="L3", code_node_id="X", slm_fact_id="fact-3")
        _insert_link(db, link_id="L4", code_node_id="Y", slm_fact_id="fact-4")

        edges = linker.link("fact-3", ["X"])
        assert edges == []

    def test_weight_calculation(
        self, db: CodeGraphDatabase, engine: GraphEngine, linker: HebbianLinker,
    ) -> None:
        """Weight should be base + per_shared * count, capped."""
        _setup_call_graph(db)

        # fact-1 linked to A
        _insert_link(db, link_id="L5", code_node_id="A", slm_fact_id="fact-5")
        # fact-6 linked to B (in A's neighborhood)
        _insert_link(db, link_id="L6", code_node_id="B", slm_fact_id="fact-6")

        edges = linker.link("fact-5", ["A"])
        assert len(edges) == 1
        # Weight should be at least WEIGHT_BASE
        assert edges[0].weight >= WEIGHT_BASE
        assert edges[0].weight <= WEIGHT_CAP

    def test_weight_cap(
        self, db: CodeGraphDatabase, engine: GraphEngine, linker: HebbianLinker,
    ) -> None:
        """Weight should be capped at WEIGHT_CAP."""
        _setup_call_graph(db)

        # Create many links to the same neighborhood
        _insert_link(db, link_id="L7", code_node_id="A", slm_fact_id="fact-7")

        # fact-8 linked to A, B, C, D — all in neighborhood
        _insert_link(db, link_id="L8a", code_node_id="A", slm_fact_id="fact-8")
        _insert_link(db, link_id="L8b", code_node_id="B", slm_fact_id="fact-8")
        _insert_link(db, link_id="L8c", code_node_id="C", slm_fact_id="fact-8")
        _insert_link(db, link_id="L8d", code_node_id="D", slm_fact_id="fact-8")

        edges = linker.link("fact-7", ["A"])
        assert len(edges) >= 1
        for edge in edges:
            assert edge.weight <= WEIGHT_CAP

    def test_empty_node_ids(self, linker: HebbianLinker) -> None:
        assert linker.link("fact-x", []) == []

    def test_excludes_self(
        self, db: CodeGraphDatabase, engine: GraphEngine, linker: HebbianLinker,
    ) -> None:
        """Should not return self-associations."""
        _setup_call_graph(db)
        _insert_link(db, link_id="L9", code_node_id="A", slm_fact_id="fact-9")

        edges = linker.link("fact-9", ["A"])
        for edge in edges:
            assert edge.target_fact_id != "fact-9"

    def test_stale_links_excluded(
        self, db: CodeGraphDatabase, engine: GraphEngine, linker: HebbianLinker,
    ) -> None:
        """Stale links should not appear in neighborhood search."""
        _setup_call_graph(db)
        _insert_link(db, link_id="L10", code_node_id="A", slm_fact_id="fact-10")

        # fact-11 linked to B but stale
        db.upsert_link(CodeMemoryLink(
            link_id="L11", code_node_id="B", slm_fact_id="fact-11",
            link_type=LinkType.MENTIONS, confidence=0.9,
            created_at="2026-01-01", last_verified="2026-01-01",
            is_stale=True,
        ))

        edges = linker.link("fact-10", ["A"])
        # fact-11 should not appear because its link is stale
        target_facts = {e.target_fact_id for e in edges}
        assert "fact-11" not in target_facts
