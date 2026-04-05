# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file

"""Tests for TypeScriptExtractor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from superlocalmemory.code_graph.config import CodeGraphConfig
from superlocalmemory.code_graph.models import EdgeKind, NodeKind

# Skip all tests if tree-sitter is not installed
try:
    import tree_sitter  # noqa: F401
    from tree_sitter_language_pack import get_parser  # noqa: F401
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False

pytestmark = pytest.mark.skipif(
    not HAS_TREE_SITTER,
    reason="tree-sitter-language-pack not installed",
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_TS = FIXTURES_DIR / "sample_typescript.ts"


@pytest.fixture
def config() -> CodeGraphConfig:
    return CodeGraphConfig(enabled=True)


@pytest.fixture
def ts_extractor(config: CodeGraphConfig):
    """Create a TypeScriptExtractor for sample_typescript.ts."""
    from superlocalmemory.code_graph.extractors.typescript import TypeScriptExtractor

    source_bytes = SAMPLE_TS.read_bytes()
    parser = get_parser("typescript")
    tree = parser.parse(source_bytes)
    return TypeScriptExtractor(tree.root_node, source_bytes, "sample_typescript.ts", config)


# --- Functions ---

def test_extract_functions_declaration(ts_extractor):
    funcs = ts_extractor.extract_functions()
    names = [n.name for n in funcs if n.kind == NodeKind.FUNCTION]
    assert "handleRequest" in names


def test_extract_functions_arrow(ts_extractor):
    funcs = ts_extractor.extract_functions()
    names = [n.name for n in funcs]
    assert "createController" in names


def test_extract_methods(ts_extractor):
    funcs = ts_extractor.extract_functions()
    methods = [n for n in funcs if n.kind == NodeKind.METHOD]
    method_names = [m.name for m in methods]
    assert "authenticate" in method_names
    assert "decodeToken" in method_names

    auth = [m for m in methods if m.name == "authenticate"][0]
    assert auth.parent_name == "AuthController"


# --- Classes ---

def test_extract_classes(ts_extractor):
    classes = ts_extractor.extract_classes()
    names = [c.name for c in classes]
    assert "AuthController" in names


def test_extract_interfaces_as_class(ts_extractor):
    classes = ts_extractor.extract_classes()
    names = [c.name for c in classes]
    assert "UserPayload" in names
    iface = [c for c in classes if c.name == "UserPayload"][0]
    assert iface.kind == NodeKind.CLASS


# --- Imports ---

def test_extract_imports(ts_extractor):
    edges, import_map = ts_extractor.extract_imports()
    assert len(edges) > 0
    assert all(e.kind == EdgeKind.IMPORTS for e in edges)
    assert "Request" in import_map
    assert import_map["Request"] == ("express", "Request")
    assert "validateToken" in import_map
    assert import_map["validateToken"] == ("./auth/validator", "validateToken")
    assert "crypto" in import_map
    assert import_map["crypto"] == ("crypto", "*")


# --- Exports ---

def test_extract_exports(ts_extractor):
    exports = ts_extractor.extract_exports()
    assert "AuthController" in exports
    assert "createController" in exports
    assert "handleRequest" in exports


# --- Calls ---

def test_extract_calls(ts_extractor):
    _, import_map = ts_extractor.extract_imports()
    edges = ts_extractor.extract_calls(import_map)
    call_names = []
    for e in edges:
        extra = json.loads(e.extra_json)
        call_names.append(extra.get("call_name", ""))

    assert "validateToken" in call_names
    assert "createController" in call_names
    # new AuthController(secret) should be detected
    assert "AuthController" in call_names


def test_async_method_signature(ts_extractor):
    funcs = ts_extractor.extract_functions()
    auth = [n for n in funcs if n.name == "authenticate"][0]
    assert auth.signature is not None
    assert "async" in auth.signature
    assert "Promise" in auth.signature or "req" in auth.signature


def test_constructor(ts_extractor):
    funcs = ts_extractor.extract_functions()
    names = [n.name for n in funcs]
    assert "constructor" in names
    ctor = [n for n in funcs if n.name == "constructor"][0]
    assert ctor.kind == NodeKind.METHOD
    assert ctor.parent_name == "AuthController"


# --- JSX ---

def test_tsx_jsx_component_call(config):
    """TSX file with JSX component usage."""
    from superlocalmemory.code_graph.extractors.typescript import TypeScriptExtractor

    source = b"""
import React from 'react';
import MyComponent from './MyComponent';

export function App() {
  return <MyComponent prop="x" />;
}
"""
    parser = get_parser("tsx")
    tree = parser.parse(source)
    ext = TypeScriptExtractor(tree.root_node, source, "App.tsx", config)
    _, import_map = ext.extract_imports()
    edges = ext.extract_calls(import_map)
    call_names = [json.loads(e.extra_json).get("call_name", "") for e in edges]
    assert "MyComponent" in call_names


# --- Edge cases ---

def test_empty_file(config):
    from superlocalmemory.code_graph.extractors.typescript import TypeScriptExtractor

    parser = get_parser("typescript")
    tree = parser.parse(b"")
    ext = TypeScriptExtractor(tree.root_node, b"", "empty.ts", config)
    nodes, edges = ext.extract()
    assert nodes == []
    assert edges == []
