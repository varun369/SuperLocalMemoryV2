# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""BlastRadius — bidirectional BFS impact analysis.

Given changed files or node IDs, computes the transitive impact
radius on the rustworkx graph with configurable depth and node caps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from superlocalmemory.code_graph.graph_engine import GraphEngine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BlastRadiusResult:
    """Impact analysis result."""

    changed_nodes: frozenset[str] = field(default_factory=frozenset)
    impacted_nodes: frozenset[str] = field(default_factory=frozenset)
    impacted_files: frozenset[str] = field(default_factory=frozenset)
    edges: tuple[tuple[str, str, dict[str, Any]], ...] = ()
    depth_reached: int = 0
    truncated: bool = False


# ---------------------------------------------------------------------------
# BlastRadius computer
# ---------------------------------------------------------------------------

class BlastRadius:
    """Computes blast radius via bidirectional BFS on the in-memory graph.

    Usage::

        br = BlastRadius(engine)
        result = br.compute(changed_files=["src/foo.py"], max_depth=2)
    """

    def __init__(self, engine: GraphEngine) -> None:
        self._engine = engine

    def compute(
        self,
        changed_files: list[str] | None = None,
        seed_node_ids: list[str] | None = None,
        max_depth: int = 2,
        max_nodes: int = 500,
        edge_kinds: set[str] | None = None,
        direction: str = "both",
    ) -> BlastRadiusResult:
        """Compute the blast radius from changed files or explicit seed nodes.

        Parameters
        ----------
        changed_files : list of relative file paths whose nodes are seeds
        seed_node_ids : explicit node IDs to use as seeds (additive)
        max_depth : maximum BFS hops
        max_nodes : cap on total visited nodes (seeds + impacted)
        edge_kinds : restrict traversal to these edge kinds (None = all)
        direction : "forward" (out-edges), "reverse" (in-edges), "both"

        Returns
        -------
        BlastRadiusResult with changed_nodes, impacted_nodes, etc.
        """
        graph = self._engine.graph
        index = self._engine.index

        # Collect seed rx indices
        seed_rx: set[int] = set()

        if changed_files:
            for fp in changed_files:
                for nid, rx_idx in index.id_to_rx.items():
                    node_data = graph[rx_idx]
                    if node_data["file_path"] == fp:
                        seed_rx.add(rx_idx)

        if seed_node_ids:
            for nid in seed_node_ids:
                rx_idx = index.id_to_rx.get(nid)
                if rx_idx is not None:
                    seed_rx.add(rx_idx)

        if not seed_rx:
            return BlastRadiusResult()

        # BFS
        visited: set[int] = set(seed_rx)
        frontier: set[int] = set(seed_rx)
        impacted_rx: set[int] = set()
        collected_edges: list[tuple[str, str, dict[str, Any]]] = []
        depth = 0
        truncated = False

        while frontier and depth < max_depth:
            next_frontier: set[int] = set()
            should_break = False

            for rx_idx in frontier:
                if should_break:
                    break

                # Forward (outgoing)
                if direction in ("forward", "both"):
                    for src, tgt, edge_data in graph.out_edges(rx_idx):
                        if edge_kinds and edge_data["kind"] not in edge_kinds:
                            continue
                        if tgt not in visited:
                            if len(visited) + len(next_frontier) >= max_nodes:
                                truncated = True
                                should_break = True
                                break
                            next_frontier.add(tgt)
                            collected_edges.append((
                                index.rx_to_id[src],
                                index.rx_to_id[tgt],
                                dict(edge_data),
                            ))

                if should_break:
                    break

                # Reverse (incoming)
                if direction in ("reverse", "both"):
                    for src, tgt, edge_data in graph.in_edges(rx_idx):
                        if edge_kinds and edge_data["kind"] not in edge_kinds:
                            continue
                        if src not in visited:
                            if len(visited) + len(next_frontier) >= max_nodes:
                                truncated = True
                                should_break = True
                                break
                            next_frontier.add(src)
                            collected_edges.append((
                                index.rx_to_id[src],
                                index.rx_to_id[tgt],
                                dict(edge_data),
                            ))

            impacted_rx.update(next_frontier)
            visited.update(next_frontier)
            frontier = next_frontier
            depth += 1

            if truncated:
                break

        # Convert to node IDs
        changed_ids = frozenset(index.rx_to_id[rx] for rx in seed_rx)
        impacted_ids = frozenset(index.rx_to_id[rx] for rx in impacted_rx)

        # Compute impacted file paths
        impacted_files = frozenset(
            graph[rx]["file_path"] for rx in impacted_rx
        )

        return BlastRadiusResult(
            changed_nodes=changed_ids,
            impacted_nodes=impacted_ids,
            impacted_files=impacted_files,
            edges=tuple(collected_edges),
            depth_reached=depth,
            truncated=truncated,
        )
