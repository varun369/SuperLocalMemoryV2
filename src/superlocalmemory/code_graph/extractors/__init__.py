# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""Base extractor ABC for language-specific AST extraction.

Each language implements extract_functions, extract_classes,
extract_imports, and extract_calls. The concrete extract() method
orchestrates them in order and returns (nodes, edges).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from superlocalmemory.code_graph.config import CodeGraphConfig
from superlocalmemory.code_graph.models import GraphEdge, GraphNode


class BaseExtractor(ABC):
    """Abstract base class for language-specific AST extractors.

    Each instance processes exactly one file. No mutable class-level state (HR-12).
    """

    def __init__(
        self,
        root_node: Any,          # tree_sitter.Node
        source_bytes: bytes,
        file_path: str,          # Relative path
        config: CodeGraphConfig,
    ) -> None:
        self._root = root_node
        self._source = source_bytes
        self._file_path = file_path
        self._config = config

    @abstractmethod
    def extract_functions(self) -> list[GraphNode]:
        """Extract all function/method definitions."""

    @abstractmethod
    def extract_classes(self) -> list[GraphNode]:
        """Extract all class/interface definitions."""

    @abstractmethod
    def extract_imports(self) -> tuple[list[GraphEdge], dict[str, tuple[str, str]]]:
        """Extract import statements.

        Returns:
            (edges, import_map) where import_map is
            {local_name: (module_path, imported_name)}.
        """

    @abstractmethod
    def extract_calls(
        self, import_map: dict[str, tuple[str, str]]
    ) -> list[GraphEdge]:
        """Extract function/method calls.

        Uses import_map for initial resolution.
        """

    def extract(self) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Run all extractors in order. Non-abstract.

        Step 1: classes = extract_classes()
        Step 2: functions = extract_functions()
        Step 3: import_edges, import_map = extract_imports()
        Step 4: call_edges = extract_calls(import_map)
        Step 5: Return (classes + functions, import_edges + call_edges)
        """
        classes = self.extract_classes()
        functions = self.extract_functions()
        import_edges, import_map = self.extract_imports()
        call_edges = self.extract_calls(import_map)
        return (classes + functions, import_edges + call_edges)
