# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""Database manager for code_graph.db.

Mirrors SLM's DatabaseManager pattern: per-call connections, WAL mode,
retry with backoff, transaction support. Points at a separate SQLite file.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from superlocalmemory.code_graph.models import (
    CodeMemoryLink,
    EdgeKind,
    FileRecord,
    GraphEdge,
    GraphNode,
    LinkType,
    NodeKind,
)
from superlocalmemory.storage import schema_code_graph

logger = logging.getLogger(__name__)

_BUSY_TIMEOUT_MS = 10_000
_MAX_RETRIES = 5
_RETRY_BASE_SECONDS = 0.1


class CodeGraphDatabase:
    """SQLite database manager for code_graph.db.

    Each public method opens a fresh connection, executes, and closes.
    WAL mode enabled. Foreign keys enforced. Retry with backoff on SQLITE_BUSY.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._txn_conn: sqlite3.Connection | None = None
        self._version = 0  # Incremented on every write (cache invalidation)

        # Initialize: create file, enable WAL, create schema
        conn = self._connect()
        try:
            schema_code_graph.create_all_tables(conn)
        finally:
            conn.close()
        logger.info("CodeGraphDatabase initialized at %s", self.db_path)

    @property
    def version(self) -> int:
        """Monotonic version counter. Incremented on writes."""
        return self._version

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=_BUSY_TIMEOUT_MS / 1000)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def execute(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> list[sqlite3.Row]:
        """Execute SQL with retry. Returns list of rows."""
        # If inside a transaction, use the shared connection
        if self._txn_conn is not None:
            cursor = self._txn_conn.execute(sql, params)
            return cursor.fetchall()

        for attempt in range(_MAX_RETRIES):
            conn = self._connect()
            try:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                conn.commit()
                return rows
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc) and attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BASE_SECONDS * (2 ** attempt)
                    logger.debug("DB locked, retry %d in %.1fs", attempt + 1, wait)
                    time.sleep(wait)
                else:
                    raise
            finally:
                conn.close()
        return []  # Unreachable, but satisfies type checker

    def execute_write(
        self, sql: str, params: tuple[Any, ...] = ()
    ) -> int:
        """Execute a write statement. Returns rowcount. Bumps version."""
        if self._txn_conn is not None:
            cursor = self._txn_conn.execute(sql, params)
            self._version += 1
            return cursor.rowcount

        conn = self._connect()
        try:
            cursor = conn.execute(sql, params)
            conn.commit()
            self._version += 1
            return cursor.rowcount
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Context manager for multi-statement transactions."""
        with self._lock:
            conn = self._connect()
            conn.execute("BEGIN IMMEDIATE")
            self._txn_conn = conn
            try:
                yield
                conn.commit()
                self._version += 1
            except Exception:
                conn.rollback()
                raise
            finally:
                self._txn_conn = None
                conn.close()

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    def upsert_node(self, node: GraphNode) -> None:
        """Insert or replace a graph node."""
        self.execute_write(
            """INSERT OR REPLACE INTO graph_nodes
               (node_id, kind, name, qualified_name, file_path,
                line_start, line_end, language, parent_name, signature,
                docstring, is_test, content_hash, community_id,
                extra_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node.node_id, node.kind.value, node.name, node.qualified_name,
                node.file_path, node.line_start, node.line_end, node.language,
                node.parent_name, node.signature, node.docstring,
                int(node.is_test), node.content_hash, node.community_id,
                node.extra_json, node.created_at, node.updated_at,
            ),
        )

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve a single node by ID."""
        rows = self.execute(
            "SELECT * FROM graph_nodes WHERE node_id = ?", (node_id,)
        )
        return self._row_to_node(rows[0]) if rows else None

    def get_node_by_qualified_name(self, qualified_name: str) -> GraphNode | None:
        """Retrieve a node by its unique qualified name."""
        rows = self.execute(
            "SELECT * FROM graph_nodes WHERE qualified_name = ?",
            (qualified_name,),
        )
        return self._row_to_node(rows[0]) if rows else None

    def get_nodes_by_file(self, file_path: str) -> list[GraphNode]:
        """All nodes in a file, ordered by line_start."""
        rows = self.execute(
            "SELECT * FROM graph_nodes WHERE file_path = ? ORDER BY line_start",
            (file_path,),
        )
        return [self._row_to_node(r) for r in rows]

    def get_all_nodes(self) -> list[GraphNode]:
        """All nodes in the graph."""
        rows = self.execute("SELECT * FROM graph_nodes")
        return [self._row_to_node(r) for r in rows]

    def get_node_count(self) -> int:
        """Total node count."""
        rows = self.execute("SELECT COUNT(*) as cnt FROM graph_nodes")
        return rows[0]["cnt"] if rows else 0

    def delete_nodes_by_file(self, file_path: str) -> int:
        """Delete all nodes for a file. Cascades to edges via FK."""
        return self.execute_write(
            "DELETE FROM graph_nodes WHERE file_path = ?", (file_path,)
        )

    # ------------------------------------------------------------------
    # Edge CRUD
    # ------------------------------------------------------------------

    def upsert_edge(self, edge: GraphEdge) -> None:
        """Insert or replace a graph edge."""
        self.execute_write(
            """INSERT OR REPLACE INTO graph_edges
               (edge_id, kind, source_node_id, target_node_id, file_path,
                line, confidence, extra_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                edge.edge_id, edge.kind.value, edge.source_node_id,
                edge.target_node_id, edge.file_path, edge.line,
                edge.confidence, edge.extra_json,
                edge.created_at, edge.updated_at,
            ),
        )

    def get_edges_from(
        self, node_id: str, kind: EdgeKind | None = None
    ) -> list[GraphEdge]:
        """Outgoing edges from a node."""
        if kind is not None:
            rows = self.execute(
                "SELECT * FROM graph_edges WHERE source_node_id = ? AND kind = ?",
                (node_id, kind.value),
            )
        else:
            rows = self.execute(
                "SELECT * FROM graph_edges WHERE source_node_id = ?",
                (node_id,),
            )
        return [self._row_to_edge(r) for r in rows]

    def get_edges_to(
        self, node_id: str, kind: EdgeKind | None = None
    ) -> list[GraphEdge]:
        """Incoming edges to a node."""
        if kind is not None:
            rows = self.execute(
                "SELECT * FROM graph_edges WHERE target_node_id = ? AND kind = ?",
                (node_id, kind.value),
            )
        else:
            rows = self.execute(
                "SELECT * FROM graph_edges WHERE target_node_id = ?",
                (node_id,),
            )
        return [self._row_to_edge(r) for r in rows]

    def get_all_edges(self) -> list[GraphEdge]:
        """All edges in the graph."""
        rows = self.execute("SELECT * FROM graph_edges")
        return [self._row_to_edge(r) for r in rows]

    def get_edge_count(self) -> int:
        """Total edge count."""
        rows = self.execute("SELECT COUNT(*) as cnt FROM graph_edges")
        return rows[0]["cnt"] if rows else 0

    def delete_edges_by_file(self, file_path: str) -> int:
        """Delete all edges originating from a file."""
        return self.execute_write(
            "DELETE FROM graph_edges WHERE file_path = ?", (file_path,)
        )

    # ------------------------------------------------------------------
    # File record CRUD
    # ------------------------------------------------------------------

    def upsert_file_record(self, record: FileRecord) -> None:
        """Insert or replace a file tracking record."""
        self.execute_write(
            """INSERT OR REPLACE INTO graph_files
               (file_path, content_hash, mtime, language,
                node_count, edge_count, last_indexed)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                record.file_path, record.content_hash, record.mtime,
                record.language, record.node_count, record.edge_count,
                record.last_indexed,
            ),
        )

    def get_file_record(self, file_path: str) -> FileRecord | None:
        """Retrieve file record."""
        rows = self.execute(
            "SELECT * FROM graph_files WHERE file_path = ?", (file_path,)
        )
        if not rows:
            return None
        r = rows[0]
        return FileRecord(
            file_path=r["file_path"],
            content_hash=r["content_hash"],
            mtime=r["mtime"],
            language=r["language"],
            node_count=r["node_count"],
            edge_count=r["edge_count"],
            last_indexed=r["last_indexed"],
        )

    def get_all_file_records(self) -> list[FileRecord]:
        """All tracked files."""
        rows = self.execute("SELECT * FROM graph_files")
        return [
            FileRecord(
                file_path=r["file_path"],
                content_hash=r["content_hash"],
                mtime=r["mtime"],
                language=r["language"],
                node_count=r["node_count"],
                edge_count=r["edge_count"],
                last_indexed=r["last_indexed"],
            )
            for r in rows
        ]

    def delete_file_record(self, file_path: str) -> None:
        """Delete a file record."""
        self.execute_write(
            "DELETE FROM graph_files WHERE file_path = ?", (file_path,)
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_metadata(self, key: str) -> str | None:
        """Read a metadata value."""
        rows = self.execute(
            "SELECT value FROM graph_metadata WHERE key = ?", (key,)
        )
        return rows[0]["value"] if rows else None

    def set_metadata(self, key: str, value: str) -> None:
        """Write a metadata value (upsert)."""
        self.execute_write(
            """INSERT OR REPLACE INTO graph_metadata (key, value, updated_at)
               VALUES (?, ?, ?)""",
            (key, value, time.time()),
        )

    # ------------------------------------------------------------------
    # Atomic file replacement
    # ------------------------------------------------------------------

    def store_file_parse_results(
        self,
        file_path: str,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        file_record: FileRecord,
    ) -> None:
        """Atomically replace all data for a file.

        Within a single transaction:
        1. Delete old edges for this file
        2. Delete old nodes for this file (cascades code_memory_links)
        3. Insert new nodes
        4. Insert new edges
        5. Upsert file record
        """
        with self.transaction():
            # Delete old data (edges first due to FK)
            self.execute_write(
                "DELETE FROM graph_edges WHERE file_path = ?", (file_path,)
            )
            self.execute_write(
                "DELETE FROM graph_nodes WHERE file_path = ?", (file_path,)
            )
            # Insert new nodes
            for node in nodes:
                self.upsert_node(node)
            # Insert new edges
            for edge in edges:
                self.upsert_edge(edge)
            # Upsert file record
            self.upsert_file_record(file_record)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, int]:
        """Returns {"nodes": N, "edges": E, "files": F}."""
        return {
            "nodes": self.get_node_count(),
            "edges": self.get_edge_count(),
            "files": len(self.get_all_file_records()),
        }

    # ------------------------------------------------------------------
    # Code memory links (bridge)
    # ------------------------------------------------------------------

    def upsert_link(self, link: CodeMemoryLink) -> None:
        """Insert or replace a code-memory bridge link."""
        self.execute_write(
            """INSERT OR REPLACE INTO code_memory_links
               (link_id, code_node_id, slm_fact_id, slm_entity_id,
                link_type, confidence, created_at, last_verified, is_stale)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                link.link_id, link.code_node_id, link.slm_fact_id,
                link.slm_entity_id, link.link_type.value, link.confidence,
                link.created_at, link.last_verified, int(link.is_stale),
            ),
        )

    def get_links_for_node(self, code_node_id: str) -> list[CodeMemoryLink]:
        """All bridge links for a code node."""
        rows = self.execute(
            "SELECT * FROM code_memory_links WHERE code_node_id = ?",
            (code_node_id,),
        )
        return [self._row_to_link(r) for r in rows]

    def get_links_for_fact(self, slm_fact_id: str) -> list[CodeMemoryLink]:
        """All bridge links for an SLM fact."""
        rows = self.execute(
            "SELECT * FROM code_memory_links WHERE slm_fact_id = ?",
            (slm_fact_id,),
        )
        return [self._row_to_link(r) for r in rows]

    # ------------------------------------------------------------------
    # Row converters
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> GraphNode:
        d = dict(row)
        return GraphNode(
            node_id=d["node_id"],
            kind=NodeKind(d["kind"]),
            name=d["name"],
            qualified_name=d["qualified_name"],
            file_path=d["file_path"],
            line_start=d["line_start"],
            line_end=d["line_end"],
            language=d["language"],
            parent_name=d.get("parent_name"),
            signature=d.get("signature"),
            docstring=d.get("docstring"),
            is_test=bool(d.get("is_test", 0)),
            content_hash=d.get("content_hash"),
            community_id=d.get("community_id"),
            extra_json=d.get("extra_json", "{}"),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )

    @staticmethod
    def _row_to_edge(row: sqlite3.Row) -> GraphEdge:
        d = dict(row)
        return GraphEdge(
            edge_id=d["edge_id"],
            kind=EdgeKind(d["kind"]),
            source_node_id=d["source_node_id"],
            target_node_id=d["target_node_id"],
            file_path=d["file_path"],
            line=d["line"],
            confidence=d["confidence"],
            extra_json=d.get("extra_json", "{}"),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )

    @staticmethod
    def _row_to_link(row: sqlite3.Row) -> CodeMemoryLink:
        d = dict(row)
        return CodeMemoryLink(
            link_id=d["link_id"],
            code_node_id=d["code_node_id"],
            slm_fact_id=d["slm_fact_id"],
            slm_entity_id=d.get("slm_entity_id"),
            link_type=LinkType(d["link_type"]),
            confidence=d["confidence"],
            created_at=d["created_at"],
            last_verified=d.get("last_verified"),
            is_stale=bool(d.get("is_stale", 0)),
        )
