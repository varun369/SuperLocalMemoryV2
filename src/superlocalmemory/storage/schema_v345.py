# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory v3.4.5 "Scale-Ready" — Schema Extensions.

Adds:
  - atomic_facts.access_count_30d: rolling 30-day access window (F-14)
  - Graph edge indexes for bulk import performance (F-20)

Existing columns NOT touched: lifecycle, access_count, pinned_facts,
backend_status, fact_consolidations — already present from v3.4.11 pre-work.

Design rules:
  - ALTER TABLE ADD COLUMN with DEFAULT — idempotent, non-destructive
  - CREATE INDEX IF NOT EXISTS — safe on re-run

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL — access_count_30d (rolling 30-day window)
# ---------------------------------------------------------------------------

_ACCESS_30D_DDL = """
ALTER TABLE atomic_facts ADD COLUMN access_count_30d INTEGER DEFAULT 0;
"""

_ACCESS_30D_CHECK = (
    "SELECT COUNT(*) FROM pragma_table_info('atomic_facts') "
    "WHERE name = 'access_count_30d'"
)

# ---------------------------------------------------------------------------
# DDL — Graph edge indexes (F-20: audit fix)
# ---------------------------------------------------------------------------

_GRAPH_EDGE_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_graph_edges_source_id
    ON graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target_id
    ON graph_edges(target_id);
"""

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

_SCHEMA_VERSION_INSERT = (
    "INSERT OR IGNORE INTO schema_version (version, description) "
    "VALUES (5, 'v3.4.5: access_count_30d + graph edge indexes')"
)


def apply_migration(conn: sqlite3.Connection) -> dict:
    """Apply v3.4.5 schema migration. Idempotent.

    Returns dict with migration status.
    """
    result: dict[str, list[str]] = {"applied": [], "skipped": [], "errors": []}

    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")

        # access_count_30d column (skip if already exists)
        if conn.execute(_ACCESS_30D_CHECK).fetchone()[0] == 0:
            conn.executescript(_ACCESS_30D_DDL)
            result["applied"].append("access_count_30d")
        else:
            result["skipped"].append("access_count_30d (already present)")

        # Graph edge indexes
        conn.executescript(_GRAPH_EDGE_INDEX_DDL)
        result["applied"].append("graph_edge_indexes")

        # Schema version marker
        conn.execute(_SCHEMA_VERSION_INSERT)

        conn.commit()
        logger.info("Schema v3.4.5 applied: %s", result["applied"])

    except Exception as exc:
        logger.error("Schema v3.4.5 migration failed: %s", exc)
        result["errors"].append(str(exc))
        try:
            conn.rollback()
        except Exception:
            pass

    return result


def schema_version_applied(conn: sqlite3.Connection) -> bool:
    """Check if v3.4.5 schema has already been applied."""
    try:
        row = conn.execute(
            "SELECT 1 FROM schema_version WHERE version = 5"
        ).fetchone()
        return row is not None
    except sqlite3.OperationalError:
        return False
