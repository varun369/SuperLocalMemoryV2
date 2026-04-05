# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""GraphStore — thin graph-specific layer over CodeGraphDatabase.

All graph writes go through this layer.  Provides:
- Atomic file replacement  (store_file_nodes_edges)
- Bulk read for in-memory graph building  (get_all_nodes_and_edges)
- File removal  (remove_file)
- Version tracking for cache invalidation
"""

from __future__ import annotations

import logging
from typing import Sequence

from superlocalmemory.code_graph.database import CodeGraphDatabase
from superlocalmemory.code_graph.models import (
    FileRecord,
    GraphEdge,
    GraphNode,
)

logger = logging.getLogger(__name__)


class GraphStore:
    """SQLite persistence layer for graph nodes, edges, and file records.

    Delegates to CodeGraphDatabase but adds higher-level operations
    that Phase 2+ modules depend on (bulk load, atomic replace, version).
    """

    def __init__(self, db: CodeGraphDatabase) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def db(self) -> CodeGraphDatabase:
        """Underlying database instance."""
        return self._db

    @property
    def version(self) -> int:
        """Monotonic write-version for cache invalidation."""
        return self._db.version

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def store_file_nodes_edges(
        self,
        file_path: str,
        nodes: Sequence[GraphNode],
        edges: Sequence[GraphEdge],
        file_record: FileRecord,
    ) -> None:
        """Atomically replace all data for *file_path*.

        Within a single transaction:
        1. Delete old edges for this file
        2. Delete old nodes for this file
        3. Insert new nodes
        4. Insert new edges
        5. Upsert file record

        The database's ``store_file_parse_results`` already does this.
        """
        self._db.store_file_parse_results(
            file_path,
            list(nodes),
            list(edges),
            file_record,
        )
        logger.debug(
            "Stored %d nodes, %d edges for %s",
            len(nodes), len(edges), file_path,
        )

    def remove_file(self, file_path: str) -> None:
        """Remove all graph data for *file_path*.

        Deletes nodes (cascade → edges via FK), edges sourced from this
        file, and the file record.  All within a transaction.
        """
        with self._db.transaction():
            self._db.delete_edges_by_file(file_path)
            self._db.delete_nodes_by_file(file_path)
            self._db.delete_file_record(file_path)
        logger.debug("Removed all data for %s", file_path)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_all_nodes_and_edges(
        self,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Load every node and edge — used by GraphEngine.build_graph().

        Returns (nodes, edges) as plain lists.
        """
        nodes = self._db.get_all_nodes()
        edges = self._db.get_all_edges()
        return nodes, edges

    def get_nodes_by_file(self, file_path: str) -> list[GraphNode]:
        """All nodes in *file_path*, ordered by line_start."""
        return self._db.get_nodes_by_file(file_path)

    def get_node(self, node_id: str) -> GraphNode | None:
        """Single node by ID."""
        return self._db.get_node(node_id)

    def get_file_record(self, file_path: str) -> FileRecord | None:
        """File record by path."""
        return self._db.get_file_record(file_path)

    def get_all_file_records(self) -> list[FileRecord]:
        """All tracked file records."""
        return self._db.get_all_file_records()

    # ------------------------------------------------------------------
    # Dependent tracing (used by IncrementalUpdater)
    # ------------------------------------------------------------------

    def find_dependents(self, file_path: str) -> set[str]:
        """Return file paths that have edges *targeting* nodes in *file_path*.

        Looks for IMPORTS, CALLS, INHERITS, DEPENDS_ON edges whose
        target lives in *file_path* but whose source is in a *different* file.
        """
        rows = self._db.execute(
            """
            SELECT DISTINCT ge.file_path
            FROM graph_edges ge
            JOIN graph_nodes gn_target
                ON ge.target_node_id = gn_target.node_id
            WHERE gn_target.file_path = ?
              AND ge.file_path != ?
            """,
            (file_path, file_path),
        )
        return {row["file_path"] for row in rows}

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, int]:
        """Delegate to DB stats."""
        return self._db.get_stats()
