# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""TypeScript/JavaScript AST extractor using tree-sitter.

Handles .ts, .tsx, .js, .jsx via appropriate grammar selection.
Extracts: function_declaration, arrow_function, class_declaration,
interface_declaration, import_statement, call_expression, JSX elements.

tree-sitter imports are lazy (HR-07).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from superlocalmemory.code_graph.config import CodeGraphConfig
from superlocalmemory.code_graph.extractors import BaseExtractor
from superlocalmemory.code_graph.models import (
    EdgeKind,
    GraphEdge,
    GraphNode,
    NodeKind,
)
from superlocalmemory.storage.models import _new_id

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# S-expression queries
# ---------------------------------------------------------------------------

FUNC_DECL_QUERY_SRC = (
    "(function_declaration"
    " name: (identifier) @func.name"
    ") @func.def"
)

METHOD_DEF_QUERY_SRC = (
    "(method_definition"
    " name: (property_identifier) @method.name"
    ") @method.def"
)

ARROW_QUERY_SRC = (
    "(lexical_declaration"
    " (variable_declarator"
    "  name: (identifier) @arrow.name"
    "  value: (arrow_function) @arrow.func"
    " )"
    ") @arrow.decl"
)

CLASS_QUERY_SRC = (
    "(class_declaration"
    " name: (type_identifier) @class.name"
    ") @class.def"
)

IFACE_QUERY_SRC = (
    "(interface_declaration"
    " name: (type_identifier) @iface.name"
    ") @iface.def"
)

IMPORT_QUERY_SRC = (
    "(import_statement"
    " source: (string) @import.source"
    ") @import.stmt"
)

CALL_QUERY_SRC = (
    "(call_expression"
    " function: (identifier) @call.name"
    ") @call.expr"
)

CALL_MEMBER_QUERY_SRC = (
    "(call_expression"
    " function: (member_expression"
    "  property: (property_identifier) @call.method)"
    ") @call.member_expr"
)

JSX_ELEMENT_QUERY_SRC = (
    "(jsx_opening_element"
    " name: (identifier) @jsx.name"
    ") @jsx.open"
)

JSX_SELF_CLOSING_QUERY_SRC = (
    "(jsx_self_closing_element"
    " name: (identifier) @jsx.name"
    ") @jsx.self_close"
)

NEW_EXPR_QUERY_SRC = (
    "(new_expression"
    " constructor: (identifier) @new.name"
    ") @new.expr"
)

EXPORT_QUERY_SRC = "(export_statement) @export.stmt"


def _get_ts_modules() -> tuple[Any, Any]:
    """Lazy import of tree-sitter modules."""
    try:
        import tree_sitter
        from tree_sitter_language_pack import get_language
    except ImportError as exc:
        raise ImportError(
            "tree-sitter and tree-sitter-language-pack required for parsing. "
            "Install: pip install 'superlocalmemory[code-graph]'"
        ) from exc
    return tree_sitter, get_language


def _node_text(node: Any, source: bytes) -> str:
    """Extract text from a tree-sitter node."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _find_parent_class(node: Any) -> str | None:
    """Walk up AST to find enclosing class_declaration name."""
    current = node.parent
    while current is not None:
        if current.type == "class_declaration":
            name_node = current.child_by_field_name("name")
            if name_node:
                return name_node.text.decode("utf-8", errors="replace")
        current = current.parent
    return None


def _make_qualified_name(
    file_path: str, name: str, parent_name: str | None
) -> str:
    if parent_name:
        return f"{file_path}::{parent_name}.{name}"
    return f"{file_path}::{name}"


def _run_query(
    query_src: str, root_node: Any, language_name: str
) -> list[tuple[int, dict[str, list[Any]]]]:
    """Run a tree-sitter query and return matches."""
    ts_mod, get_language = _get_ts_modules()
    lang = get_language(language_name)
    query = ts_mod.Query(lang, query_src)
    cursor = ts_mod.QueryCursor(query)
    return cursor.matches(root_node)


def _safe_query(
    query_src: str, root_node: Any, language_name: str
) -> list[tuple[int, dict[str, list[Any]]]]:
    """Run query, returning empty list on error (some queries may not apply to all grammars)."""
    try:
        return _run_query(query_src, root_node, language_name)
    except Exception:
        return []


def _detect_language(file_path: str) -> str:
    """Map file extension to tree-sitter grammar name."""
    if file_path.endswith(".tsx"):
        return "tsx"
    if file_path.endswith(".ts"):
        return "typescript"
    if file_path.endswith(".jsx"):
        return "javascript"
    return "javascript"


class TypeScriptExtractor(BaseExtractor):
    """TypeScript/JavaScript AST extractor."""

    def __init__(
        self,
        root_node: Any,
        source_bytes: bytes,
        file_path: str,
        config: CodeGraphConfig,
    ) -> None:
        super().__init__(root_node, source_bytes, file_path, config)
        self._lang_name = _detect_language(file_path)
        self._exports: list[str] = []

    def extract_functions(self) -> list[GraphNode]:
        """Extract function declarations, arrow functions, and methods."""
        nodes: list[GraphNode] = []

        # Function declarations
        for _pat, captures in _run_query(FUNC_DECL_QUERY_SRC, self._root, self._lang_name):
            func_defs = captures.get("func.def", [])
            func_names = captures.get("func.name", [])
            for i, func_def in enumerate(func_defs):
                name_node = func_names[i] if i < len(func_names) else None
                if not name_node:
                    continue
                name = _node_text(name_node, self._source)
                parent = _find_parent_class(func_def)
                sig = self._build_func_signature(func_def, name)
                nodes.append(GraphNode(
                    node_id=_new_id(),
                    kind=NodeKind.METHOD if parent else NodeKind.FUNCTION,
                    name=name,
                    qualified_name=_make_qualified_name(self._file_path, name, parent),
                    file_path=self._file_path,
                    line_start=func_def.start_point[0],
                    line_end=func_def.end_point[0],
                    language=self._lang_name,
                    parent_name=parent,
                    signature=sig,
                ))

        # Method definitions
        for _pat, captures in _run_query(METHOD_DEF_QUERY_SRC, self._root, self._lang_name):
            method_defs = captures.get("method.def", [])
            method_names = captures.get("method.name", [])
            for i, method_def in enumerate(method_defs):
                name_node = method_names[i] if i < len(method_names) else None
                if not name_node:
                    continue
                name = _node_text(name_node, self._source)
                parent = _find_parent_class(method_def)
                sig = self._build_method_signature(method_def, name)
                nodes.append(GraphNode(
                    node_id=_new_id(),
                    kind=NodeKind.METHOD,
                    name=name,
                    qualified_name=_make_qualified_name(self._file_path, name, parent),
                    file_path=self._file_path,
                    line_start=method_def.start_point[0],
                    line_end=method_def.end_point[0],
                    language=self._lang_name,
                    parent_name=parent,
                    signature=sig,
                ))

        # Arrow functions assigned to variables
        for _pat, captures in _run_query(ARROW_QUERY_SRC, self._root, self._lang_name):
            arrow_decls = captures.get("arrow.decl", [])
            arrow_names = captures.get("arrow.name", [])
            arrow_funcs = captures.get("arrow.func", [])
            for i, decl in enumerate(arrow_decls):
                name_node = arrow_names[i] if i < len(arrow_names) else None
                func_node = arrow_funcs[i] if i < len(arrow_funcs) else None
                if not name_node:
                    continue
                name = _node_text(name_node, self._source)
                parent = _find_parent_class(decl)
                sig = self._build_arrow_signature(func_node, name) if func_node else f"const {name} = (...) => ..."
                nodes.append(GraphNode(
                    node_id=_new_id(),
                    kind=NodeKind.METHOD if parent else NodeKind.FUNCTION,
                    name=name,
                    qualified_name=_make_qualified_name(self._file_path, name, parent),
                    file_path=self._file_path,
                    line_start=decl.start_point[0],
                    line_end=decl.end_point[0],
                    language=self._lang_name,
                    parent_name=parent,
                    signature=sig,
                ))

        return nodes

    def extract_classes(self) -> list[GraphNode]:
        """Extract class and interface declarations."""
        nodes: list[GraphNode] = []
        self._inherits_info: list[tuple[str, str, int]] = []

        # Classes
        for _pat, captures in _run_query(CLASS_QUERY_SRC, self._root, self._lang_name):
            class_defs = captures.get("class.def", [])
            class_names = captures.get("class.name", [])
            for i, class_def in enumerate(class_defs):
                name_node = class_names[i] if i < len(class_names) else None
                if not name_node:
                    continue
                name = _node_text(name_node, self._source)
                qname = _make_qualified_name(self._file_path, name, None)
                # Check for heritage clause (extends/implements)
                self._extract_heritage(class_def, qname)
                nodes.append(GraphNode(
                    node_id=_new_id(),
                    kind=NodeKind.CLASS,
                    name=name,
                    qualified_name=qname,
                    file_path=self._file_path,
                    line_start=class_def.start_point[0],
                    line_end=class_def.end_point[0],
                    language=self._lang_name,
                ))

        # Interfaces
        for _pat, captures in _safe_query(IFACE_QUERY_SRC, self._root, self._lang_name):
            iface_defs = captures.get("iface.def", [])
            iface_names = captures.get("iface.name", [])
            for i, iface_def in enumerate(iface_defs):
                name_node = iface_names[i] if i < len(iface_names) else None
                if not name_node:
                    continue
                name = _node_text(name_node, self._source)
                nodes.append(GraphNode(
                    node_id=_new_id(),
                    kind=NodeKind.CLASS,
                    name=name,
                    qualified_name=_make_qualified_name(self._file_path, name, None),
                    file_path=self._file_path,
                    line_start=iface_def.start_point[0],
                    line_end=iface_def.end_point[0],
                    language=self._lang_name,
                ))

        return nodes

    def extract_imports(
        self,
    ) -> tuple[list[GraphEdge], dict[str, tuple[str, str]]]:
        """Extract import statements and build import_map."""
        edges: list[GraphEdge] = []
        import_map: dict[str, tuple[str, str]] = {}

        for _pat, captures in _run_query(IMPORT_QUERY_SRC, self._root, self._lang_name):
            stmts = captures.get("import.stmt", [])
            sources = captures.get("import.source", [])
            for i, stmt in enumerate(stmts):
                source_node = sources[i] if i < len(sources) else None
                if not source_node:
                    continue
                module_path = _node_text(source_node, self._source).strip("'\"")

                # Parse import clause
                for child in stmt.children:
                    if child.type == "import_clause":
                        self._parse_import_clause(child, module_path, import_map)

                edges.append(GraphEdge(
                    edge_id=_new_id(),
                    kind=EdgeKind.IMPORTS,
                    source_node_id="__unresolved__",
                    target_node_id="__unresolved__",
                    file_path=self._file_path,
                    line=stmt.start_point[0],
                    extra_json=json.dumps({"module": module_path}),
                ))

        return edges, import_map

    def extract_calls(
        self, import_map: dict[str, tuple[str, str]]
    ) -> list[GraphEdge]:
        """Extract function/method calls and new expressions."""
        edges: list[GraphEdge] = []

        # Simple calls: foo()
        for _pat, captures in _run_query(CALL_QUERY_SRC, self._root, self._lang_name):
            call_names = captures.get("call.name", [])
            for name_node in call_names:
                call_name = _node_text(name_node, self._source)
                confidence = 1.0 if call_name in import_map else self._config.heuristic_confidence
                edges.append(GraphEdge(
                    edge_id=_new_id(),
                    kind=EdgeKind.CALLS,
                    source_node_id="__unresolved__",
                    target_node_id=f"__call__{call_name}",
                    file_path=self._file_path,
                    line=name_node.start_point[0],
                    confidence=confidence,
                    extra_json=json.dumps({"call_name": call_name}),
                ))

        # Member calls: obj.method()
        for _pat, captures in _run_query(CALL_MEMBER_QUERY_SRC, self._root, self._lang_name):
            method_names = captures.get("call.method", [])
            for name_node in method_names:
                method_name = _node_text(name_node, self._source)
                edges.append(GraphEdge(
                    edge_id=_new_id(),
                    kind=EdgeKind.CALLS,
                    source_node_id="__unresolved__",
                    target_node_id=f"__call__{method_name}",
                    file_path=self._file_path,
                    line=name_node.start_point[0],
                    confidence=self._config.heuristic_confidence,
                    extra_json=json.dumps({"call_name": method_name, "is_method": True}),
                ))

        # new Foo()
        for _pat, captures in _run_query(NEW_EXPR_QUERY_SRC, self._root, self._lang_name):
            new_names = captures.get("new.name", [])
            for name_node in new_names:
                call_name = _node_text(name_node, self._source)
                confidence = 1.0 if call_name in import_map else self._config.heuristic_confidence
                edges.append(GraphEdge(
                    edge_id=_new_id(),
                    kind=EdgeKind.CALLS,
                    source_node_id="__unresolved__",
                    target_node_id=f"__call__{call_name}",
                    file_path=self._file_path,
                    line=name_node.start_point[0],
                    confidence=confidence,
                    extra_json=json.dumps({"call_name": call_name, "is_constructor": True}),
                ))

        # JSX components (tsx/jsx only)
        if self._lang_name in ("tsx", "javascript"):
            self._extract_jsx_calls(edges, import_map)

        return edges

    def extract_exports(self) -> list[str]:
        """Extract exported names."""
        exports: list[str] = []
        for _pat, captures in _safe_query(EXPORT_QUERY_SRC, self._root, self._lang_name):
            for stmt in captures.get("export.stmt", []):
                # Look for named children that contain identifiers
                for child in stmt.named_children:
                    if child.type == "function_declaration":
                        name_n = child.child_by_field_name("name")
                        if name_n:
                            exports.append(_node_text(name_n, self._source))
                    elif child.type == "class_declaration":
                        name_n = child.child_by_field_name("name")
                        if name_n:
                            exports.append(_node_text(name_n, self._source))
                    elif child.type == "lexical_declaration":
                        for decl in child.named_children:
                            if decl.type == "variable_declarator":
                                name_n = decl.child_by_field_name("name")
                                if name_n:
                                    exports.append(_node_text(name_n, self._source))
        self._exports = exports
        return exports

    def extract(self) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Override to also extract exports."""
        self.extract_exports()
        return super().extract()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_import_clause(
        self, clause: Any, module_path: str, import_map: dict[str, tuple[str, str]]
    ) -> None:
        """Parse an import_clause node into import_map entries."""
        for child in clause.children:
            if child.type == "identifier":
                # Default import: import Foo from '...'
                name = _node_text(child, self._source)
                import_map[name] = (module_path, "default")
            elif child.type == "named_imports":
                for spec in child.named_children:
                    if spec.type == "import_specifier":
                        name_n = spec.child_by_field_name("name")
                        alias_n = spec.child_by_field_name("alias")
                        if name_n:
                            orig = _node_text(name_n, self._source)
                            alias = _node_text(alias_n, self._source) if alias_n else orig
                            import_map[alias] = (module_path, orig)
            elif child.type == "namespace_import":
                # import * as ns from '...'
                for sub in child.children:
                    if sub.type == "identifier":
                        ns_name = _node_text(sub, self._source)
                        import_map[ns_name] = (module_path, "*")
                        break

    def _extract_heritage(
        self, class_node: Any, class_qname: str
    ) -> None:
        """Extract extends/implements from class heritage clause."""
        for child in class_node.children:
            if child.type == "class_heritage":
                for heritage in child.named_children:
                    if heritage.type in ("extends_clause", "implements_clause"):
                        for type_node in heritage.named_children:
                            base_name = _node_text(type_node, self._source)
                            self._inherits_info.append(
                                (class_qname, base_name, class_node.start_point[0])
                            )

    def _extract_jsx_calls(
        self, edges: list[GraphEdge], import_map: dict[str, tuple[str, str]]
    ) -> None:
        """Extract JSX component usage as CALLS edges."""
        for query_src in (JSX_ELEMENT_QUERY_SRC, JSX_SELF_CLOSING_QUERY_SRC):
            for _pat, captures in _safe_query(query_src, self._root, self._lang_name):
                for name_node in captures.get("jsx.name", []):
                    comp_name = _node_text(name_node, self._source)
                    # Only uppercase = React component (lowercase = HTML tag)
                    if comp_name and comp_name[0].isupper():
                        confidence = 1.0 if comp_name in import_map else self._config.heuristic_confidence
                        edges.append(GraphEdge(
                            edge_id=_new_id(),
                            kind=EdgeKind.CALLS,
                            source_node_id="__unresolved__",
                            target_node_id=f"__call__{comp_name}",
                            file_path=self._file_path,
                            line=name_node.start_point[0],
                            confidence=confidence,
                            extra_json=json.dumps({"call_name": comp_name, "is_jsx": True}),
                        ))

    def _build_func_signature(self, func_def: Any, name: str) -> str:
        """Build signature for function_declaration."""
        params_node = func_def.child_by_field_name("parameters")
        params = _node_text(params_node, self._source) if params_node else "()"
        rt = func_def.child_by_field_name("return_type")
        rt_text = _node_text(rt, self._source) if rt else ""
        # Check for async keyword
        is_async = any(
            c.type == "async" for c in func_def.children
            if hasattr(c, "type")
        )
        prefix = "async function" if is_async else "function"
        sig = f"{prefix} {name}{params}"
        if rt_text:
            sig += rt_text
        return sig

    def _build_method_signature(self, method_def: Any, name: str) -> str:
        """Build signature for method_definition."""
        params_node = method_def.child_by_field_name("parameters")
        params = _node_text(params_node, self._source) if params_node else "()"
        rt = method_def.child_by_field_name("return_type")
        rt_text = _node_text(rt, self._source) if rt else ""
        is_async = any(
            c.type == "async" for c in method_def.children
            if hasattr(c, "type")
        )
        prefix = "async " if is_async else ""
        sig = f"{prefix}{name}{params}"
        if rt_text:
            sig += rt_text
        return sig

    def _build_arrow_signature(self, arrow_func: Any, name: str) -> str:
        """Build signature for arrow function."""
        params_node = arrow_func.child_by_field_name("parameters")
        params = _node_text(params_node, self._source) if params_node else "()"
        rt = arrow_func.child_by_field_name("return_type")
        rt_text = _node_text(rt, self._source) if rt else ""
        sig = f"const {name} = {params}"
        if rt_text:
            sig += rt_text
        sig += " => ..."
        return sig
