# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Bridge Module

"""Temporal Checker — invalidate memories about deleted/renamed code.

For MVP: operates entirely on code_graph.db (code_memory_links table).
Does NOT write to memory.db fact_temporal_validity — that's Phase 4b.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from superlocalmemory.code_graph.database import CodeGraphDatabase

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StaleLink:
    """A code_memory_link that has been marked stale."""
    link_id: str
    code_node_id: str
    slm_fact_id: str
    qualified_name: str


@dataclass(frozen=True)
class DeletedCodeMemory:
    """A fact linked to a code node that no longer exists in the graph."""
    fact_id: str
    node_id: str
    node_qualified_name: str
    link_id: str


class TemporalChecker:
    """Checks and invalidates memories about deleted/renamed code.

    Operates on code_graph.db only (MVP constraint).
    """

    def __init__(self, code_graph_db: CodeGraphDatabase) -> None:
        self._db = code_graph_db

    def mark_links_stale(self, node_id: str) -> int:
        """Mark all non-stale links for a node as stale.

        Returns the count of links marked stale.
        """
        count = self._db.execute_write(
            "UPDATE code_memory_links SET is_stale = 1, "
            "last_verified = datetime('now') "
            "WHERE code_node_id = ? AND is_stale = 0",
            (node_id,),
        )
        if count > 0:
            logger.info(
                "Marked %d links stale for node %s", count, node_id,
            )
        return count

    def check_stale_links(self) -> list[StaleLink]:
        """Get all stale code_memory_links.

        Returns list of StaleLink with node metadata.
        """
        rows = self._db.execute(
            "SELECT cml.link_id, cml.code_node_id, cml.slm_fact_id, "
            "COALESCE(gn.qualified_name, 'deleted') as qualified_name "
            "FROM code_memory_links cml "
            "LEFT JOIN graph_nodes gn ON cml.code_node_id = gn.node_id "
            "WHERE cml.is_stale = 1",
            (),
        )
        return [
            StaleLink(
                link_id=row["link_id"],
                code_node_id=row["code_node_id"],
                slm_fact_id=row["slm_fact_id"],
                qualified_name=row["qualified_name"],
            )
            for row in rows
        ]

    def get_memories_for_deleted_code(self) -> list[DeletedCodeMemory]:
        """Find facts linked to code nodes that no longer exist in the graph.

        These are code_memory_links whose code_node_id has no matching
        graph_nodes row — the code was deleted.
        """
        rows = self._db.execute(
            "SELECT cml.slm_fact_id, cml.code_node_id, cml.link_id "
            "FROM code_memory_links cml "
            "LEFT JOIN graph_nodes gn ON cml.code_node_id = gn.node_id "
            "WHERE gn.node_id IS NULL",
            (),
        )
        return [
            DeletedCodeMemory(
                fact_id=row["slm_fact_id"],
                node_id=row["code_node_id"],
                node_qualified_name="deleted",
                link_id=row["link_id"],
            )
            for row in rows
        ]

    def bulk_verify(self) -> dict[str, int]:
        """Re-verify ALL code_memory_links against current graph state.

        - Links whose code_node_id still exists: mark verified
        - Links whose code_node_id is gone: mark stale

        Returns {"verified": int, "marked_stale": int, "already_stale": int}
        """
        # Count already stale
        already_rows = self._db.execute(
            "SELECT COUNT(*) as cnt FROM code_memory_links WHERE is_stale = 1",
            (),
        )
        already_stale = already_rows[0]["cnt"] if already_rows else 0

        # Mark stale: links to deleted nodes
        marked_stale = self._db.execute_write(
            "UPDATE code_memory_links SET is_stale = 1, "
            "last_verified = datetime('now') "
            "WHERE is_stale = 0 AND code_node_id NOT IN "
            "(SELECT node_id FROM graph_nodes)",
            (),
        )

        # Verify: links to existing nodes
        verified = self._db.execute_write(
            "UPDATE code_memory_links SET "
            "last_verified = datetime('now') "
            "WHERE is_stale = 0 AND code_node_id IN "
            "(SELECT node_id FROM graph_nodes)",
            (),
        )

        result = {
            "verified": verified,
            "marked_stale": marked_stale,
            "already_stale": already_stale,
        }
        logger.info("Bulk verify complete: %s", result)
        return result
