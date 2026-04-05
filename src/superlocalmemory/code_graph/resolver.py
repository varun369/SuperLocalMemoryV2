# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""Cross-file import resolution with heuristic fallback.

Resolves Python dotted imports and TypeScript/JS relative imports to
actual file paths within the repo. Falls back to name-based heuristics
with lower confidence for unresolvable calls.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from superlocalmemory.code_graph.config import CodeGraphConfig
from superlocalmemory.code_graph.models import (
    EdgeKind,
    GraphEdge,
    GraphNode,
)
from superlocalmemory.storage.models import _new_id

logger = logging.getLogger(__name__)


class UnsupportedLanguageError(Exception):
    """Raised when a language is not supported for import resolution."""


class ImportResolver:
    """Cross-file import resolution with heuristic fallback."""

    def __init__(self, repo_root: Path, config: CodeGraphConfig) -> None:
        self._repo_root = repo_root
        self._config = config

    def resolve(
        self, import_path: str, importer_file: str, language: str
    ) -> str | None:
        """Resolve an import path to a relative file path.

        Returns None for external packages.
        Raises UnsupportedLanguageError for unknown languages.
        """
        if language == "python":
            return self._resolve_python(import_path, importer_file)
        if language in ("typescript", "tsx", "javascript", "jsx"):
            return self._resolve_typescript(import_path, importer_file)
        raise UnsupportedLanguageError(
            f"Import resolution not supported for language: {language}"
        )

    def build_symbol_table(
        self, all_nodes: list[GraphNode]
    ) -> dict[str, list[GraphNode]]:
        """Build global symbol table: {bare_name -> [matching_nodes]}.

        Used for heuristic cross-file resolution.
        """
        table: dict[str, list[GraphNode]] = {}
        for node in all_nodes:
            if node.name:
                table.setdefault(node.name, []).append(node)
        return table

    def resolve_call_targets(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        import_maps: dict[str, dict[str, tuple[str, str]]],
    ) -> list[GraphEdge]:
        """Resolve CALLS edges with placeholder targets.

        Returns new list of edges with resolved target_node_ids.
        Unresolvable edges (external calls) are dropped.
        """
        symbol_table = self.build_symbol_table(nodes)

        # Index: (file_path, name) -> node
        file_name_index: dict[tuple[str, str], GraphNode] = {}
        for node in nodes:
            file_name_index[(node.file_path, node.name)] = node

        resolved: list[GraphEdge] = []

        for edge in edges:
            if edge.kind != EdgeKind.CALLS:
                resolved.append(edge)
                continue

            if not edge.target_node_id.startswith("__call__"):
                resolved.append(edge)
                continue

            call_name = edge.target_node_id.replace("__call__", "")
            source_file = edge.file_path
            file_import_map = import_maps.get(source_file, {})

            # Strategy 1: Import-resolved
            if call_name in file_import_map:
                module_path, imported_name = file_import_map[call_name]
                resolved_file = self.resolve(
                    module_path, source_file,
                    self._guess_language(source_file)
                )
                if resolved_file:
                    target = file_name_index.get((resolved_file, imported_name))
                    if target is None:
                        target = file_name_index.get((resolved_file, call_name))
                    if target:
                        resolved.append(GraphEdge(
                            edge_id=edge.edge_id,
                            kind=edge.kind,
                            source_node_id=edge.source_node_id,
                            target_node_id=target.node_id,
                            file_path=edge.file_path,
                            line=edge.line,
                            confidence=1.0,
                            extra_json=edge.extra_json,
                        ))
                        continue

            # Strategy 2: Same-file match
            same_file_target = file_name_index.get((source_file, call_name))
            if same_file_target:
                resolved.append(GraphEdge(
                    edge_id=edge.edge_id,
                    kind=edge.kind,
                    source_node_id=edge.source_node_id,
                    target_node_id=same_file_target.node_id,
                    file_path=edge.file_path,
                    line=edge.line,
                    confidence=1.0,
                    extra_json=edge.extra_json,
                ))
                continue

            # Strategy 3: Global heuristic
            candidates = symbol_table.get(call_name, [])
            if len(candidates) == 1:
                resolved.append(GraphEdge(
                    edge_id=edge.edge_id,
                    kind=edge.kind,
                    source_node_id=edge.source_node_id,
                    target_node_id=candidates[0].node_id,
                    file_path=edge.file_path,
                    line=edge.line,
                    confidence=self._config.heuristic_confidence,
                    extra_json=edge.extra_json,
                ))
            elif len(candidates) > 1:
                # Pick closest by directory proximity
                best = self._pick_closest(source_file, candidates)
                resolved.append(GraphEdge(
                    edge_id=edge.edge_id,
                    kind=edge.kind,
                    source_node_id=edge.source_node_id,
                    target_node_id=best.node_id,
                    file_path=edge.file_path,
                    line=edge.line,
                    confidence=self._config.heuristic_confidence * 0.8,
                    extra_json=edge.extra_json,
                ))
            else:
                # External call — drop
                logger.debug(
                    "Dropping unresolvable call: %s in %s", call_name, source_file
                )

        return resolved

    # ------------------------------------------------------------------
    # Private: Python resolution
    # ------------------------------------------------------------------

    def _resolve_python(self, import_path: str, importer_file: str) -> str | None:
        """Resolve a Python dotted import to a file path."""
        # Convert dots to path separators
        parts = import_path.replace(".", "/")

        # Try direct file
        candidate = self._repo_root / f"{parts}.py"
        if candidate.exists():
            return str(candidate.relative_to(self._repo_root))

        # Try package __init__.py
        candidate = self._repo_root / parts / "__init__.py"
        if candidate.exists():
            return str(candidate.relative_to(self._repo_root))

        # Walk up from importer directory
        importer_dir = (self._repo_root / importer_file).parent
        current = importer_dir
        while current >= self._repo_root:
            candidate = current / f"{parts}.py"
            if candidate.exists():
                return str(candidate.relative_to(self._repo_root))
            candidate = current / parts / "__init__.py"
            if candidate.exists():
                return str(candidate.relative_to(self._repo_root))
            if current == self._repo_root:
                break
            current = current.parent

        return None  # External package

    # ------------------------------------------------------------------
    # Private: TypeScript resolution
    # ------------------------------------------------------------------

    def _resolve_typescript(self, import_path: str, importer_file: str) -> str | None:
        """Resolve a TypeScript/JS import to a file path."""
        # Bare imports (no ./ or ../) = external package
        if not import_path.startswith(".") and not import_path.startswith("@/"):
            if import_path.startswith("@") and "/" in import_path:
                # Scoped package like @foo/bar — still external
                return None
            return None

        # Handle @/ alias
        if import_path.startswith("@/"):
            return self._resolve_ts_alias(import_path, importer_file)

        # Relative import
        importer_dir = (self._repo_root / importer_file).parent
        base = (importer_dir / import_path).resolve()

        # Try extensions in order
        extensions = [".ts", ".tsx", ".js", ".jsx"]
        for ext in extensions:
            candidate = base.with_suffix(ext)
            if candidate.exists():
                try:
                    return str(candidate.relative_to(self._repo_root))
                except ValueError:
                    continue

        # Try index files
        if base.is_dir():
            for ext in extensions:
                candidate = base / f"index{ext}"
                if candidate.exists():
                    try:
                        return str(candidate.relative_to(self._repo_root))
                    except ValueError:
                        continue

        # Try as directory even if doesn't exist as dir
        for ext in extensions:
            candidate = Path(str(base)) / f"index{ext}"
            if candidate.exists():
                try:
                    return str(candidate.relative_to(self._repo_root))
                except ValueError:
                    continue

        return None

    def _resolve_ts_alias(self, import_path: str, importer_file: str) -> str | None:
        """Resolve @/ style path aliases from tsconfig.json."""
        tsconfig_path = self._repo_root / "tsconfig.json"
        if not tsconfig_path.exists():
            return None

        try:
            tsconfig = json.loads(tsconfig_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

        paths = tsconfig.get("compilerOptions", {}).get("paths", {})
        for alias_pattern, targets in paths.items():
            prefix = alias_pattern.rstrip("*")
            if import_path.startswith(prefix):
                remainder = import_path[len(prefix):]
                for target in targets:
                    target_prefix = target.rstrip("*")
                    resolved_path = target_prefix + remainder
                    # Try with extensions
                    extensions = [".ts", ".tsx", ".js", ".jsx"]
                    for ext in extensions:
                        candidate = self._repo_root / f"{resolved_path}{ext}"
                        if candidate.exists():
                            return str(candidate.relative_to(self._repo_root))
                    # Try as-is
                    candidate = self._repo_root / resolved_path
                    if candidate.exists():
                        return str(candidate.relative_to(self._repo_root))

        return None

    # ------------------------------------------------------------------
    # Private: helpers
    # ------------------------------------------------------------------

    def _guess_language(self, file_path: str) -> str:
        """Guess language from file extension."""
        ext_map = self._config.extension_map
        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang
        return "python"

    @staticmethod
    def _pick_closest(source_file: str, candidates: list[GraphNode]) -> GraphNode:
        """Pick the candidate closest to source_file by directory depth."""
        source_parts = Path(source_file).parts

        def _distance(node: GraphNode) -> int:
            target_parts = Path(node.file_path).parts
            common = 0
            for s, t in zip(source_parts, target_parts):
                if s == t:
                    common += 1
                else:
                    break
            return len(source_parts) + len(target_parts) - 2 * common

        return min(candidates, key=_distance)
