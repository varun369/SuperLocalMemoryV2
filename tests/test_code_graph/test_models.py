# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file

"""Tests for CodeGraph data models."""

import pytest

from superlocalmemory.code_graph.models import (
    CodeMemoryLink,
    EdgeKind,
    FileRecord,
    GraphEdge,
    GraphNode,
    LinkType,
    NodeKind,
    ParseResult,
)


class TestEnums:
    def test_node_kinds(self):
        assert NodeKind.FILE == "file"
        assert NodeKind.CLASS == "class"
        assert NodeKind.FUNCTION == "function"
        assert NodeKind.METHOD == "method"
        assert NodeKind.MODULE == "module"

    def test_edge_kinds(self):
        assert EdgeKind.CALLS == "calls"
        assert EdgeKind.IMPORTS == "imports"
        assert EdgeKind.INHERITS == "inherits"
        assert EdgeKind.CONTAINS == "contains"
        assert EdgeKind.TESTED_BY == "tested_by"
        assert EdgeKind.DEPENDS_ON == "depends_on"

    def test_link_types(self):
        assert LinkType.MENTIONS == "mentions"
        assert LinkType.BUG_FIX == "bug_fix"
        assert LinkType.DESIGN_RATIONALE == "design_rationale"


class TestGraphNode:
    def test_defaults(self):
        node = GraphNode()
        assert node.node_id  # Auto-generated
        assert node.kind == NodeKind.FUNCTION
        assert node.name == ""
        assert node.is_test is False
        assert node.community_id is None

    def test_frozen(self):
        node = GraphNode(name="hello")
        with pytest.raises(AttributeError):
            node.name = "world"  # type: ignore

    def test_custom_values(self):
        node = GraphNode(
            kind=NodeKind.CLASS,
            name="UserService",
            qualified_name="src/auth/service.py::UserService",
            file_path="src/auth/service.py",
            line_start=10,
            line_end=50,
            language="python",
            is_test=False,
        )
        assert node.kind == NodeKind.CLASS
        assert node.name == "UserService"
        assert node.line_start == 10


class TestGraphEdge:
    def test_defaults(self):
        edge = GraphEdge()
        assert edge.edge_id
        assert edge.kind == EdgeKind.CALLS
        assert edge.confidence == 1.0

    def test_frozen(self):
        edge = GraphEdge()
        with pytest.raises(AttributeError):
            edge.confidence = 0.5  # type: ignore

    def test_confidence_stored(self):
        edge = GraphEdge(confidence=0.7)
        assert edge.confidence == 0.7


class TestFileRecord:
    def test_defaults(self):
        rec = FileRecord()
        assert rec.file_path == ""
        assert rec.node_count == 0

    def test_frozen(self):
        rec = FileRecord(file_path="test.py")
        with pytest.raises(AttributeError):
            rec.file_path = "other.py"  # type: ignore


class TestParseResult:
    def test_creation(self):
        result = ParseResult(
            file_path="test.py",
            nodes=(),
            edges=(),
            file_record=FileRecord(file_path="test.py"),
        )
        assert result.file_path == "test.py"
        assert result.errors == ()
