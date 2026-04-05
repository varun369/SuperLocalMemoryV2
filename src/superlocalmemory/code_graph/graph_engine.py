# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""GraphEngine — rustworkx in-memory directed graph.

Loads from SQLite via GraphStore, caches in a rustworkx PyDiGraph,
and provides O(1) node lookup + O(degree) traversals.

Cache invalidation: rebuild when store.version changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from superlocalmemory.code_graph.graph_store import GraphStore
from superlocalmemory.code_graph.models import EdgeKind, GraphNode

logger = logging.getLogger(__name__)

try:
    import rustworkx as rx  # type: ignore[import-untyped]
except ImportError as _rx_err:
    rx = None  # type: ignore[assignment]
    _RX_IMPORT_ERROR = _rx_err
else:
    _RX_IMPORT_ERROR = None


class RustworkxNotInstalledError(ImportError):
    """Raised when rustworkx is required but not installed."""


class NodeNotFoundError(KeyError):
    """Raised when a node_id is not present in the graph."""


def _require_rustworkx() -> None:
    """Guard: raise if rustworkx is not available."""
    if rx is None:
        raise RustworkxNotInstalledError(
            "rustworkx is required for GraphEngine. "
            "Install it with: pip install rustworkx"
        ) from _RX_IMPORT_ERROR


# ---------------------------------------------------------------------------
# GraphIndex — bidirectional ID mapping
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GraphIndex:
    """Bidirectional mapping between SQLite TEXT node_id and rustworkx int index."""

    id_to_rx: dict[str, int] = field(default_factory=dict)
    rx_to_id: dict[int, str] = field(default_factory=dict)
    qname_to_id: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# GraphEngine
# ---------------------------------------------------------------------------

class GraphEngine:
    """In-memory directed graph backed by rustworkx PyDiGraph.

    Lazily built from SQLite on first query. Automatically rebuilds
    when the underlying GraphStore version changes (writes detected).
    """

    def __init__(self, store: GraphStore) -> None:
        _require_rustworkx()
        self._store = store
        self._graph: rx.PyDiGraph | None = None  # type: ignore[name-defined]
        self._index: GraphIndex = GraphIndex()
        self._graph_version: int = -1

    # ------------------------------------------------------------------
    # Graph lifecycle
    # ------------------------------------------------------------------

    def build_graph(self) -> rx.PyDiGraph:  # type: ignore[name-defined]
        """Load all nodes and edges from SQLite into a rustworkx PyDiGraph.

        Returns the cached graph if the store version hasn't changed.
        """
        if (
            self._graph is not None
            and self._graph_version == self._store.version
        ):
            return self._graph

        nodes, edges = self._store.get_all_nodes_and_edges()

        graph = rx.PyDiGraph(multigraph=True)

        id_to_rx: dict[str, int] = {}
        rx_to_id: dict[int, str] = {}
        qname_to_id: dict[str, str] = {}

        # Add nodes
        for node in nodes:
            node_data: dict[str, Any] = {
                "node_id": node.node_id,
                "kind": node.kind.value,
                "name": node.name,
                "qualified_name": node.qualified_name,
                "file_path": node.file_path,
                "line_start": node.line_start,
                "line_end": node.line_end,
                "language": node.language,
                "parent_name": node.parent_name,
                "is_test": node.is_test,
                "community_id": node.community_id,
            }
            rx_idx = graph.add_node(node_data)
            id_to_rx[node.node_id] = rx_idx
            rx_to_id[rx_idx] = node.node_id
            qname_to_id[node.qualified_name] = node.node_id

        # Add edges
        for edge in edges:
            src_rx = id_to_rx.get(edge.source_node_id)
            tgt_rx = id_to_rx.get(edge.target_node_id)
            if src_rx is None or tgt_rx is None:
                logger.warning(
                    "Skipping dangling edge %s -> %s (kind=%s)",
                    edge.source_node_id, edge.target_node_id, edge.kind.value,
                )
                continue
            edge_data: dict[str, Any] = {
                "edge_id": edge.edge_id,
                "kind": edge.kind.value,
                "file_path": edge.file_path,
                "line": edge.line,
                "confidence": edge.confidence,
            }
            graph.add_edge(src_rx, tgt_rx, edge_data)

        # Cache
        self._graph = graph
        self._index = GraphIndex(
            id_to_rx=id_to_rx,
            rx_to_id=rx_to_id,
            qname_to_id=qname_to_id,
        )
        self._graph_version = self._store.version
        logger.debug(
            "Built graph: %d nodes, %d edges",
            graph.num_nodes(), graph.num_edges(),
        )
        return graph

    def invalidate(self) -> None:
        """Force a graph rebuild on next access."""
        self._graph = None
        self._graph_version = -1

    @property
    def index(self) -> GraphIndex:
        """Current graph index (builds graph if needed)."""
        self._ensure_graph()
        return self._index

    @property
    def graph(self) -> rx.PyDiGraph:  # type: ignore[name-defined]
        """Current rustworkx graph (builds if needed)."""
        return self._ensure_graph()

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    def get_callers(
        self,
        node_id: str,
        edge_kinds: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return all nodes that have edges pointing *to* node_id.

        Each result is ``{"node": <node_data>, "edge": <edge_data>}``.
        """
        graph = self._ensure_graph()
        rx_idx = self._resolve_rx(node_id)

        results: list[dict[str, Any]] = []
        for src_rx, _tgt_rx, edge_data in graph.in_edges(rx_idx):
            if edge_kinds is not None and edge_data["kind"] not in edge_kinds:
                continue
            results.append({
                "node": dict(graph[src_rx]),
                "edge": dict(edge_data),
            })
        return results

    def get_callees(
        self,
        node_id: str,
        edge_kinds: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return all nodes that node_id has edges pointing *to*.

        Each result is ``{"node": <node_data>, "edge": <edge_data>}``.
        """
        graph = self._ensure_graph()
        rx_idx = self._resolve_rx(node_id)

        results: list[dict[str, Any]] = []
        for _src_rx, tgt_rx, edge_data in graph.out_edges(rx_idx):
            if edge_kinds is not None and edge_data["kind"] not in edge_kinds:
                continue
            results.append({
                "node": dict(graph[tgt_rx]),
                "edge": dict(edge_data),
            })
        return results

    def get_tests_for(self, node_id: str) -> list[dict[str, Any]]:
        """Return test nodes associated with *node_id*.

        Checks:
        1. Outgoing TESTED_BY edges from node_id
        2. Incoming CALLS edges from nodes where is_test=True
        """
        graph = self._ensure_graph()
        rx_idx = self._resolve_rx(node_id)

        seen_ids: set[str] = set()
        results: list[dict[str, Any]] = []

        # Outgoing TESTED_BY
        for _src, tgt_rx, edge_data in graph.out_edges(rx_idx):
            if edge_data["kind"] == EdgeKind.TESTED_BY.value:
                tgt_data = dict(graph[tgt_rx])
                tid = tgt_data["node_id"]
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    results.append(tgt_data)

        # Incoming CALLS from test nodes
        for src_rx, _tgt, edge_data in graph.in_edges(rx_idx):
            if edge_data["kind"] == EdgeKind.CALLS.value:
                src_data = dict(graph[src_rx])
                if src_data.get("is_test") and src_data["node_id"] not in seen_ids:
                    seen_ids.add(src_data["node_id"])
                    results.append(src_data)

        return results

    def get_connected_component(self, node_id: str) -> list[str]:
        """Return all node_ids in the same weakly-connected component.

        Uses rustworkx.weakly_connected_components.
        """
        graph = self._ensure_graph()
        rx_idx = self._resolve_rx(node_id)

        components = rx.weakly_connected_components(graph)
        for component in components:
            if rx_idx in component:
                return [self._index.rx_to_id[i] for i in component]

        # Shouldn't reach here if node exists, but return just the node
        return [node_id]

    def get_node_data(self, node_id: str) -> dict[str, Any]:
        """Return the node data dict for a node_id."""
        graph = self._ensure_graph()
        rx_idx = self._resolve_rx(node_id)
        return dict(graph[rx_idx])

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_graph(self) -> rx.PyDiGraph:  # type: ignore[name-defined]
        """Build graph if needed and return it."""
        if (
            self._graph is None
            or self._graph_version != self._store.version
        ):
            return self.build_graph()
        return self._graph

    def _resolve_rx(self, node_id: str) -> int:
        """Resolve a TEXT node_id to a rustworkx index. Raises NodeNotFoundError."""
        rx_idx = self._index.id_to_rx.get(node_id)
        if rx_idx is None:
            raise NodeNotFoundError(
                f"Node '{node_id}' not found in graph"
            )
        return rx_idx
