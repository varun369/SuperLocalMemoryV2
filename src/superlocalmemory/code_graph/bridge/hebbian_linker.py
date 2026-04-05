# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Bridge Module

"""Hebbian Linker — code-aware association edge creation.

When two SLM facts mention functions in the same call subgraph,
creates code_memory_links entries to record the relationship.

For MVP: creates code_memory_links entries ONLY.  Does NOT write
to memory.db association_edges — that's Phase 4b (future).
This keeps the bridge completely isolated from memory.db writes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from superlocalmemory.code_graph.models import EdgeKind

if TYPE_CHECKING:
    from superlocalmemory.code_graph.database import CodeGraphDatabase
    from superlocalmemory.code_graph.graph_engine import GraphEngine

logger = logging.getLogger(__name__)

WEIGHT_BASE = 0.3
WEIGHT_PER_SHARED = 0.1
WEIGHT_CAP = 0.8


@dataclass(frozen=True)
class HebbianEdge:
    """A code-aware Hebbian association found between two facts."""
    source_fact_id: str
    target_fact_id: str
    weight: float
    shared_node_count: int


class HebbianLinker:
    """Finds facts sharing code subgraphs via code_memory_links in code_graph.db.

    For MVP: read-only analysis + returns results.  Does NOT write
    association_edges to memory.db.
    """

    def __init__(
        self,
        code_graph_db: CodeGraphDatabase,
        graph_engine: GraphEngine,
    ) -> None:
        self._db = code_graph_db
        self._engine = graph_engine

    def link(
        self,
        fact_id: str,
        linked_node_ids: list[str],
    ) -> list[HebbianEdge]:
        """Find facts sharing code subgraph and return Hebbian edges.

        Args:
            fact_id: The SLM fact that was just linked to code.
            linked_node_ids: Code node IDs the fact was linked to.

        Returns:
            List of HebbianEdge objects describing discovered associations.
        """
        if not linked_node_ids:
            return []

        # Step 1: Compute 1-hop call neighborhood for all linked nodes
        neighborhood_ids: set[str] = set(linked_node_ids)
        for node_id in linked_node_ids:
            neighbors = self._get_call_neighborhood(node_id)
            neighborhood_ids.update(neighbors)

        # Step 2: Find other facts linked to the same neighborhood
        other_facts = self._find_facts_in_neighborhood(
            neighborhood_ids, exclude_fact_id=fact_id,
        )

        if not other_facts:
            return []

        # Step 3: For each other fact, count shared nodes and compute weight
        edges: list[HebbianEdge] = []
        for other_fact_id, other_node_ids in other_facts.items():
            shared_count = len(neighborhood_ids & other_node_ids)
            if shared_count == 0:
                continue

            weight = min(
                WEIGHT_BASE + (shared_count * WEIGHT_PER_SHARED),
                WEIGHT_CAP,
            )
            edges.append(HebbianEdge(
                source_fact_id=fact_id,
                target_fact_id=other_fact_id,
                weight=weight,
                shared_node_count=shared_count,
            ))

        logger.debug(
            "Found %d Hebbian associations for fact %s",
            len(edges), fact_id,
        )
        return edges

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_call_neighborhood(self, node_id: str) -> set[str]:
        """Get 1-hop CALLS neighbors (both directions) for a node."""
        neighbors: set[str] = set()
        try:
            # Outgoing CALLS
            callees = self._engine.get_callees(
                node_id, edge_kinds={EdgeKind.CALLS.value},
            )
            for item in callees:
                nid = item["node"]["node_id"]
                neighbors.add(nid)

            # Incoming CALLS
            callers = self._engine.get_callers(
                node_id, edge_kinds={EdgeKind.CALLS.value},
            )
            for item in callers:
                nid = item["node"]["node_id"]
                neighbors.add(nid)
        except KeyError:
            # Node not in graph — skip
            logger.debug("Node %s not in graph, skipping neighborhood", node_id)

        return neighbors

    def _find_facts_in_neighborhood(
        self,
        neighborhood_ids: set[str],
        exclude_fact_id: str,
    ) -> dict[str, set[str]]:
        """Find other facts linked to nodes in the neighborhood.

        Returns dict of fact_id -> set of linked node_ids.
        """
        if not neighborhood_ids:
            return {}

        placeholders = ",".join("?" for _ in neighborhood_ids)
        rows = self._db.execute(
            f"SELECT DISTINCT slm_fact_id, code_node_id "
            f"FROM code_memory_links "
            f"WHERE code_node_id IN ({placeholders}) "
            f"AND slm_fact_id != ? "
            f"AND is_stale = 0",
            tuple(neighborhood_ids) + (exclude_fact_id,),
        )

        result: dict[str, set[str]] = {}
        for row in rows:
            fid = row["slm_fact_id"]
            nid = row["code_node_id"]
            result.setdefault(fid, set()).add(nid)

        return result
