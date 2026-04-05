# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file

"""Tests for ImportResolver."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from superlocalmemory.code_graph.config import CodeGraphConfig
from superlocalmemory.code_graph.models import EdgeKind, GraphEdge, GraphNode, NodeKind
from superlocalmemory.code_graph.resolver import ImportResolver, UnsupportedLanguageError


@pytest.fixture
def config() -> CodeGraphConfig:
    return CodeGraphConfig(enabled=True)


# ---------------------------------------------------------------------------
# Python import resolution
# ---------------------------------------------------------------------------

def test_resolve_python_relative_import(tmp_path: Path, config: CodeGraphConfig):
    """Resolve dotted path to .py file."""
    (tmp_path / "src" / "utils").mkdir(parents=True)
    (tmp_path / "src" / "utils" / "helpers.py").write_text("# helpers")
    resolver = ImportResolver(tmp_path, config)
    result = resolver.resolve("src.utils.helpers", "main.py", "python")
    assert result is not None
    assert result == "src/utils/helpers.py"


def test_resolve_python_package_init(tmp_path: Path, config: CodeGraphConfig):
    """Resolve package import to __init__.py."""
    (tmp_path / "src" / "utils").mkdir(parents=True)
    (tmp_path / "src" / "utils" / "__init__.py").write_text("# pkg")
    resolver = ImportResolver(tmp_path, config)
    result = resolver.resolve("src.utils", "main.py", "python")
    assert result is not None
    assert "__init__.py" in result


def test_resolve_python_external_package(tmp_path: Path, config: CodeGraphConfig):
    """External packages should return None."""
    resolver = ImportResolver(tmp_path, config)
    result = resolver.resolve("requests", "src/main.py", "python")
    assert result is None


# ---------------------------------------------------------------------------
# TypeScript import resolution
# ---------------------------------------------------------------------------

def test_resolve_ts_relative_import(tmp_path: Path, config: CodeGraphConfig):
    """Resolve relative TS import."""
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "src" / "auth" / "validator.ts").write_text("// validator")
    resolver = ImportResolver(tmp_path, config)
    result = resolver.resolve("./auth/validator", "src/main.ts", "typescript")
    assert result is not None
    assert "validator.ts" in result


def test_resolve_ts_index_file(tmp_path: Path, config: CodeGraphConfig):
    """Resolve directory import to index.ts."""
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "src" / "auth" / "index.ts").write_text("// index")
    resolver = ImportResolver(tmp_path, config)
    result = resolver.resolve("./auth", "src/main.ts", "typescript")
    assert result is not None
    assert "index.ts" in result


def test_resolve_ts_extension_priority(tmp_path: Path, config: CodeGraphConfig):
    """TS extension should be preferred over JS."""
    (tmp_path / "src").mkdir(parents=True)
    (tmp_path / "src" / "utils.ts").write_text("// ts")
    (tmp_path / "src" / "utils.js").write_text("// js")
    resolver = ImportResolver(tmp_path, config)
    result = resolver.resolve("./utils", "src/main.ts", "typescript")
    assert result is not None
    assert result.endswith(".ts")


def test_resolve_ts_external_package(tmp_path: Path, config: CodeGraphConfig):
    """Bare package names should return None."""
    resolver = ImportResolver(tmp_path, config)
    result = resolver.resolve("express", "src/main.ts", "typescript")
    assert result is None


def test_resolve_ts_alias(tmp_path: Path, config: CodeGraphConfig):
    """Resolve @/ alias via tsconfig.json paths."""
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "src" / "auth" / "validator.ts").write_text("// val")
    tsconfig = {
        "compilerOptions": {
            "paths": {
                "@/*": ["src/*"]
            }
        }
    }
    (tmp_path / "tsconfig.json").write_text(json.dumps(tsconfig))
    resolver = ImportResolver(tmp_path, config)
    result = resolver.resolve("@/auth/validator", "src/main.ts", "typescript")
    assert result is not None
    assert "validator.ts" in result


# ---------------------------------------------------------------------------
# Symbol table
# ---------------------------------------------------------------------------

def test_build_symbol_table(config: CodeGraphConfig, tmp_path: Path):
    resolver = ImportResolver(tmp_path, config)
    nodes = [
        GraphNode(node_id="n1", name="authenticate", kind=NodeKind.METHOD,
                  qualified_name="a.py::Auth.authenticate", file_path="a.py"),
        GraphNode(node_id="n2", name="authenticate", kind=NodeKind.METHOD,
                  qualified_name="b.py::Other.authenticate", file_path="b.py"),
        GraphNode(node_id="n3", name="create_user", kind=NodeKind.FUNCTION,
                  qualified_name="c.py::create_user", file_path="c.py"),
    ]
    table = resolver.build_symbol_table(nodes)
    assert len(table["authenticate"]) == 2
    assert len(table["create_user"]) == 1


# ---------------------------------------------------------------------------
# Call target resolution
# ---------------------------------------------------------------------------

def test_resolve_call_targets_import_resolved(tmp_path: Path, config: CodeGraphConfig):
    """Import-resolved call should have confidence=1.0."""
    (tmp_path / "b.py").write_text("# b")
    resolver = ImportResolver(tmp_path, config)

    nodes = [
        GraphNode(node_id="caller", name="foo", kind=NodeKind.FUNCTION,
                  qualified_name="a.py::foo", file_path="a.py"),
        GraphNode(node_id="target", name="bar", kind=NodeKind.FUNCTION,
                  qualified_name="b.py::bar", file_path="b.py"),
    ]
    edges = [
        GraphEdge(edge_id="e1", kind=EdgeKind.CALLS,
                  source_node_id="caller", target_node_id="__call__bar",
                  file_path="a.py", line=5),
    ]
    import_maps = {
        "a.py": {"bar": ("b", "bar")},
    }
    resolved = resolver.resolve_call_targets(nodes, edges, import_maps)
    assert len(resolved) == 1
    assert resolved[0].target_node_id == "target"
    assert resolved[0].confidence == 1.0


def test_resolve_call_targets_heuristic(tmp_path: Path, config: CodeGraphConfig):
    """Single global match should use heuristic confidence."""
    resolver = ImportResolver(tmp_path, config)

    nodes = [
        GraphNode(node_id="caller", name="foo", kind=NodeKind.FUNCTION,
                  qualified_name="a.py::foo", file_path="a.py"),
        GraphNode(node_id="target", name="bar", kind=NodeKind.FUNCTION,
                  qualified_name="c.py::bar", file_path="c.py"),
    ]
    edges = [
        GraphEdge(edge_id="e1", kind=EdgeKind.CALLS,
                  source_node_id="caller", target_node_id="__call__bar",
                  file_path="a.py", line=5),
    ]
    resolved = resolver.resolve_call_targets(nodes, edges, {})
    assert len(resolved) == 1
    assert resolved[0].confidence == config.heuristic_confidence


def test_resolve_call_targets_ambiguous(tmp_path: Path, config: CodeGraphConfig):
    """Multiple matches should pick closest with reduced confidence."""
    resolver = ImportResolver(tmp_path, config)

    nodes = [
        GraphNode(node_id="caller", name="foo", kind=NodeKind.FUNCTION,
                  qualified_name="src/a.py::foo", file_path="src/a.py"),
        GraphNode(node_id="t1", name="bar", kind=NodeKind.FUNCTION,
                  qualified_name="src/b.py::bar", file_path="src/b.py"),
        GraphNode(node_id="t2", name="bar", kind=NodeKind.FUNCTION,
                  qualified_name="lib/c.py::bar", file_path="lib/c.py"),
        GraphNode(node_id="t3", name="bar", kind=NodeKind.FUNCTION,
                  qualified_name="vendor/d.py::bar", file_path="vendor/d.py"),
    ]
    edges = [
        GraphEdge(edge_id="e1", kind=EdgeKind.CALLS,
                  source_node_id="caller", target_node_id="__call__bar",
                  file_path="src/a.py", line=5),
    ]
    resolved = resolver.resolve_call_targets(nodes, edges, {})
    assert len(resolved) == 1
    # Should pick src/b.py (closest to src/a.py)
    assert resolved[0].target_node_id == "t1"
    assert resolved[0].confidence == pytest.approx(config.heuristic_confidence * 0.8)


def test_resolve_call_targets_external_dropped(tmp_path: Path, config: CodeGraphConfig):
    """Calls with no matching symbol should be dropped."""
    resolver = ImportResolver(tmp_path, config)

    nodes = [
        GraphNode(node_id="caller", name="foo", kind=NodeKind.FUNCTION,
                  qualified_name="a.py::foo", file_path="a.py"),
    ]
    edges = [
        GraphEdge(edge_id="e1", kind=EdgeKind.CALLS,
                  source_node_id="caller", target_node_id="__call__external_func",
                  file_path="a.py", line=5),
    ]
    resolved = resolver.resolve_call_targets(nodes, edges, {})
    assert len(resolved) == 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_unsupported_language_raises(tmp_path: Path, config: CodeGraphConfig):
    resolver = ImportResolver(tmp_path, config)
    with pytest.raises(UnsupportedLanguageError):
        resolver.resolve("foo", "file.rs", "rust")
