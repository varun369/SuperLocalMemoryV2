# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file

"""Tests for PythonExtractor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from superlocalmemory.code_graph.config import CodeGraphConfig
from superlocalmemory.code_graph.extractors import BaseExtractor
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
SAMPLE_PYTHON = FIXTURES_DIR / "sample_python.py"


@pytest.fixture
def config() -> CodeGraphConfig:
    return CodeGraphConfig(enabled=True)


@pytest.fixture
def python_extractor(config: CodeGraphConfig):
    """Create a PythonExtractor for sample_python.py."""
    from superlocalmemory.code_graph.extractors.python import PythonExtractor

    source_bytes = SAMPLE_PYTHON.read_bytes()
    parser = get_parser("python")
    tree = parser.parse(source_bytes)
    return PythonExtractor(tree.root_node, source_bytes, "sample_python.py", config)


# --- BaseExtractor ---

def test_base_extractor_is_abstract():
    """BaseExtractor cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseExtractor(None, b"", "", CodeGraphConfig())  # type: ignore


# --- Functions ---

def test_extract_functions_finds_top_level(python_extractor):
    funcs = python_extractor.extract_functions()
    names = [n.name for n in funcs]
    assert "create_auth_service" in names
    top_level = [n for n in funcs if n.name == "create_auth_service"][0]
    assert top_level.kind == NodeKind.FUNCTION
    assert top_level.line_start > 0


def test_extract_functions_finds_methods(python_extractor):
    funcs = python_extractor.extract_functions()
    method_names = [n.name for n in funcs if n.kind == NodeKind.METHOD]
    assert "authenticate" in method_names
    assert "_lookup_user" in method_names
    assert "__init__" in method_names

    auth = [n for n in funcs if n.name == "authenticate"][0]
    assert auth.parent_name == "AuthService"


def test_extract_functions_signature(python_extractor):
    funcs = python_extractor.extract_functions()
    auth = [n for n in funcs if n.name == "authenticate"][0]
    assert auth.signature is not None
    assert "token: str" in auth.signature
    assert "Optional[dict]" in auth.signature


def test_extract_functions_docstring(python_extractor):
    funcs = python_extractor.extract_functions()
    auth = [n for n in funcs if n.name == "authenticate"][0]
    assert auth.docstring is not None
    assert "Authenticate a user by token." in auth.docstring


# --- Classes ---

def test_extract_classes(python_extractor):
    classes = python_extractor.extract_classes()
    names = [n.name for n in classes]
    assert "AuthService" in names
    assert "AdminService" in names
    auth = [n for n in classes if n.name == "AuthService"][0]
    admin = [n for n in classes if n.name == "AdminService"][0]
    assert auth.kind == NodeKind.CLASS
    assert auth.line_start < admin.line_start


def test_extract_inherits(python_extractor):
    """AdminService should have inherits info for AuthService."""
    python_extractor.extract_classes()
    inherits = python_extractor._inherits_info
    base_names = [base for _, base, _ in inherits]
    assert "AuthService" in base_names


# --- Imports ---

def test_extract_imports(python_extractor):
    edges, import_map = python_extractor.extract_imports()
    assert len(edges) > 0
    assert all(e.kind == EdgeKind.IMPORTS for e in edges)
    assert "Path" in import_map
    assert import_map["Path"] == ("pathlib", "Path")
    assert "validate_token" in import_map
    assert import_map["validate_token"][0] == "utils.helpers"
    assert "os" in import_map


# --- Calls ---

def test_extract_calls(python_extractor):
    _, import_map = python_extractor.extract_imports()
    edges = python_extractor.extract_calls(import_map)
    call_names = []
    for e in edges:
        extra = json.loads(e.extra_json)
        call_names.append(extra.get("call_name", ""))

    assert "validate_token" in call_names
    assert "_lookup_user" in call_names
    assert "AuthService" in call_names
    assert "authenticate" in call_names


# --- Full extraction ---

def test_extract_all_returns_both(python_extractor):
    nodes, edges = python_extractor.extract()
    assert len(nodes) >= 6  # 2 classes + 4+ functions/methods
    assert len(edges) > 0


# --- Edge cases ---

def test_empty_file(config):
    from superlocalmemory.code_graph.extractors.python import PythonExtractor

    parser = get_parser("python")
    tree = parser.parse(b"")
    ext = PythonExtractor(tree.root_node, b"", "empty.py", config)
    nodes, edges = ext.extract()
    assert nodes == []
    assert edges == []


def test_syntax_error_file(config):
    """tree-sitter is error-tolerant — should not crash."""
    from superlocalmemory.code_graph.extractors.python import PythonExtractor

    source = b"def foo(:\n  pass\n\ndef bar(): return 1"
    parser = get_parser("python")
    tree = parser.parse(source)
    ext = PythonExtractor(tree.root_node, source, "broken.py", config)
    nodes, edges = ext.extract()
    # Should get at least bar()
    names = [n.name for n in nodes]
    assert "bar" in names


def test_decorated_function(config):
    """Functions with decorators should be extracted."""
    from superlocalmemory.code_graph.extractors.python import PythonExtractor

    source = b"""
class Foo:
    @staticmethod
    def bar():
        pass
"""
    parser = get_parser("python")
    tree = parser.parse(source)
    ext = PythonExtractor(tree.root_node, source, "decorated.py", config)
    nodes, edges = ext.extract()
    names = [n.name for n in nodes]
    assert "bar" in names
