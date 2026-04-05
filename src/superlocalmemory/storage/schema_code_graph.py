# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""DDL for the code_graph.db database.

Single source of truth for all CodeGraph tables.
No other module should contain CREATE TABLE statements.

Tables:
  1. graph_nodes       — Code entities (functions, classes, files, modules)
  2. graph_edges       — Relationships (calls, imports, inherits, contains, tested_by)
  3. graph_files       — File tracking for incremental updates
  4. graph_metadata    — Key-value store for graph-level config
  5. code_memory_links — Bridge table linking code nodes to SLM memory facts
  6. code_node_embeddings — vec0 virtual table for semantic search (optional)
  7. graph_nodes_fts   — FTS5 virtual table for text search
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DDL Statements (executed in order)
# ---------------------------------------------------------------------------

_DDL_STATEMENTS: tuple[str, ...] = (
    # ── Table 1: graph_nodes ──────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS graph_nodes (
        node_id         TEXT PRIMARY KEY,
        kind            TEXT NOT NULL CHECK (kind IN ('file', 'class', 'function', 'method', 'module')),
        name            TEXT NOT NULL,
        qualified_name  TEXT NOT NULL UNIQUE,
        file_path       TEXT NOT NULL,
        line_start      INTEGER NOT NULL DEFAULT 0,
        line_end        INTEGER NOT NULL DEFAULT 0,
        language        TEXT NOT NULL DEFAULT '',
        parent_name     TEXT,
        signature       TEXT,
        docstring       TEXT,
        is_test         INTEGER NOT NULL DEFAULT 0,
        content_hash    TEXT,
        community_id    INTEGER,
        extra_json      TEXT NOT NULL DEFAULT '{}',
        created_at      REAL NOT NULL,
        updated_at      REAL NOT NULL
    )
    """,

    # ── Table 2: graph_edges ──────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS graph_edges (
        edge_id         TEXT PRIMARY KEY,
        kind            TEXT NOT NULL CHECK (kind IN ('calls', 'imports', 'inherits', 'contains', 'tested_by', 'depends_on')),
        source_node_id  TEXT NOT NULL REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
        target_node_id  TEXT NOT NULL REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
        file_path       TEXT NOT NULL,
        line            INTEGER NOT NULL DEFAULT 0,
        confidence      REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
        extra_json      TEXT NOT NULL DEFAULT '{}',
        created_at      REAL NOT NULL,
        updated_at      REAL NOT NULL
    )
    """,

    # ── Table 3: graph_files ──────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS graph_files (
        file_path       TEXT PRIMARY KEY,
        content_hash    TEXT NOT NULL,
        mtime           REAL NOT NULL,
        language        TEXT NOT NULL,
        node_count      INTEGER NOT NULL DEFAULT 0,
        edge_count      INTEGER NOT NULL DEFAULT 0,
        last_indexed    REAL NOT NULL
    )
    """,

    # ── Table 4: graph_metadata ───────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS graph_metadata (
        key             TEXT PRIMARY KEY,
        value           TEXT NOT NULL,
        updated_at      REAL NOT NULL
    )
    """,

    # ── Table 5: code_memory_links ────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS code_memory_links (
        link_id         TEXT PRIMARY KEY,
        code_node_id    TEXT NOT NULL REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
        slm_fact_id     TEXT NOT NULL,
        slm_entity_id   TEXT,
        link_type       TEXT NOT NULL CHECK (link_type IN (
            'mentions', 'decision_about', 'bug_fix', 'refactor', 'design_rationale'
        )),
        confidence      REAL NOT NULL DEFAULT 0.8 CHECK (confidence >= 0.0 AND confidence <= 1.0),
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        last_verified   TEXT,
        is_stale        INTEGER NOT NULL DEFAULT 0
    )
    """,
)

# Indexes (separate from tables for clarity)
_INDEX_STATEMENTS: tuple[str, ...] = (
    # graph_nodes indexes
    "CREATE INDEX IF NOT EXISTS idx_gn_file_path ON graph_nodes(file_path)",
    "CREATE INDEX IF NOT EXISTS idx_gn_kind ON graph_nodes(kind)",
    "CREATE INDEX IF NOT EXISTS idx_gn_name ON graph_nodes(name)",
    "CREATE INDEX IF NOT EXISTS idx_gn_qualified ON graph_nodes(qualified_name)",
    "CREATE INDEX IF NOT EXISTS idx_gn_parent ON graph_nodes(parent_name)",
    "CREATE INDEX IF NOT EXISTS idx_gn_language ON graph_nodes(language)",
    "CREATE INDEX IF NOT EXISTS idx_gn_community ON graph_nodes(community_id)",
    # graph_edges indexes
    "CREATE INDEX IF NOT EXISTS idx_ge_source ON graph_edges(source_node_id)",
    "CREATE INDEX IF NOT EXISTS idx_ge_target ON graph_edges(target_node_id)",
    "CREATE INDEX IF NOT EXISTS idx_ge_kind ON graph_edges(kind)",
    "CREATE INDEX IF NOT EXISTS idx_ge_file ON graph_edges(file_path)",
    "CREATE INDEX IF NOT EXISTS idx_ge_source_kind ON graph_edges(source_node_id, kind)",
    "CREATE INDEX IF NOT EXISTS idx_ge_target_kind ON graph_edges(target_node_id, kind)",
    # code_memory_links indexes
    "CREATE INDEX IF NOT EXISTS idx_cml_node ON code_memory_links(code_node_id)",
    "CREATE INDEX IF NOT EXISTS idx_cml_fact ON code_memory_links(slm_fact_id)",
    "CREATE INDEX IF NOT EXISTS idx_cml_entity ON code_memory_links(slm_entity_id)",
    "CREATE INDEX IF NOT EXISTS idx_cml_type ON code_memory_links(link_type)",
    "CREATE INDEX IF NOT EXISTS idx_cml_stale ON code_memory_links(is_stale)",
)

# FTS5 virtual table + sync triggers
_FTS5_STATEMENTS: tuple[str, ...] = (
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS graph_nodes_fts USING fts5(
        name,
        qualified_name,
        file_path,
        signature,
        content='graph_nodes',
        content_rowid='rowid',
        tokenize='porter unicode61'
    )
    """,
    # Auto-sync trigger: INSERT
    """
    CREATE TRIGGER IF NOT EXISTS trg_gn_fts_insert AFTER INSERT ON graph_nodes
    BEGIN
        INSERT INTO graph_nodes_fts(rowid, name, qualified_name, file_path, signature)
        VALUES (NEW.rowid, NEW.name, NEW.qualified_name, NEW.file_path, NEW.signature);
    END
    """,
    # Auto-sync trigger: DELETE
    """
    CREATE TRIGGER IF NOT EXISTS trg_gn_fts_delete AFTER DELETE ON graph_nodes
    BEGIN
        INSERT INTO graph_nodes_fts(graph_nodes_fts, rowid, name, qualified_name, file_path, signature)
        VALUES ('delete', OLD.rowid, OLD.name, OLD.qualified_name, OLD.file_path, OLD.signature);
    END
    """,
    # Auto-sync trigger: UPDATE
    """
    CREATE TRIGGER IF NOT EXISTS trg_gn_fts_update AFTER UPDATE ON graph_nodes
    BEGIN
        INSERT INTO graph_nodes_fts(graph_nodes_fts, rowid, name, qualified_name, file_path, signature)
        VALUES ('delete', OLD.rowid, OLD.name, OLD.qualified_name, OLD.file_path, OLD.signature);
        INSERT INTO graph_nodes_fts(rowid, name, qualified_name, file_path, signature)
        VALUES (NEW.rowid, NEW.name, NEW.qualified_name, NEW.file_path, NEW.signature);
    END
    """,
)


# ---------------------------------------------------------------------------
# Public API (matches SLM's schema.py pattern)
# ---------------------------------------------------------------------------

def create_all_tables(conn: sqlite3.Connection) -> None:
    """Create all CodeGraph tables, indexes, and triggers.

    Idempotent — safe to call multiple times (all DDL uses IF NOT EXISTS).
    """
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Core tables
    for ddl in _DDL_STATEMENTS:
        cursor.execute(ddl)

    # Indexes
    for idx in _INDEX_STATEMENTS:
        cursor.execute(idx)

    # FTS5 + triggers (may fail if SQLite lacks FTS5 — non-fatal)
    for stmt in _FTS5_STATEMENTS:
        try:
            cursor.execute(stmt)
        except sqlite3.OperationalError as exc:
            logger.warning("FTS5 setup failed (non-fatal): %s", exc)

    # vec0 virtual table for embeddings (may fail if sqlite-vec not loaded)
    try:
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS code_node_embeddings USING vec0(
                node_id TEXT PRIMARY KEY,
                embedding float[768] distance_metric=cosine
            )
        """)
    except sqlite3.OperationalError as exc:
        logger.warning("vec0 setup failed (non-fatal, embeddings disabled): %s", exc)

    conn.commit()
    logger.info("CodeGraph schema initialized (%d tables, %d indexes)",
                len(_DDL_STATEMENTS), len(_INDEX_STATEMENTS))


def drop_all_tables(conn: sqlite3.Connection) -> None:
    """Drop all CodeGraph tables. Used in tests only."""
    cursor = conn.cursor()
    for table in (
        "graph_nodes_fts", "code_node_embeddings",
        "code_memory_links", "graph_metadata",
        "graph_files", "graph_edges", "graph_nodes",
    ):
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        except sqlite3.OperationalError:
            pass
    # Drop triggers
    for trigger in ("trg_gn_fts_insert", "trg_gn_fts_delete", "trg_gn_fts_update"):
        cursor.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    conn.commit()
