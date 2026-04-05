# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Database Migrations.

Handles schema versioning and V1 (slm_alpha) → Innovation migration.
Preserves existing data while upgrading schema structure.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1  # Innovation v1


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Read current schema version. Returns 0 if no version table."""
    try:
        row = conn.execute(
            "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
        ).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        return 0


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    """Record a schema version upgrade."""
    conn.execute(
        "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
        (version, datetime.now(UTC).isoformat(), f"Migration to v{version}"),
    )


def needs_migration(db_path: Path) -> bool:
    """Check if database needs migration."""
    if not db_path.exists():
        return False
    conn = sqlite3.connect(str(db_path))
    try:
        version = get_schema_version(conn)
        return version < CURRENT_SCHEMA_VERSION
    finally:
        conn.close()


def is_v1_database(db_path: Path) -> bool:
    """Detect if this is a V1 (slm_alpha) database by checking for V1-specific tables."""
    if not db_path.exists():
        return False
    conn = sqlite3.connect(str(db_path))
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        # V1 markers: episodic_memory table + no schema_version
        return "episodic_memory" in tables and "schema_version" not in tables
    finally:
        conn.close()


def backup_database(db_path: Path) -> Path:
    """Create timestamped backup before migration."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_suffix(f".backup_{timestamp}.db")
    shutil.copy2(str(db_path), str(backup_path))
    logger.info("Database backed up to %s", backup_path)
    return backup_path


def migrate_v1_to_innovation(
    v1_db_path: Path,
    innovation_db_path: Path,
    profile_id: str = "default",
) -> dict[str, Any]:
    """Migrate V1 (slm_alpha) database to Innovation schema.

    Preserves all memories and facts. Creates proper typed stores.
    Returns migration statistics.
    """
    from superlocalmemory.storage import schema

    stats: dict[str, Any] = {
        "memories_migrated": 0,
        "facts_migrated": 0,
        "entities_migrated": 0,
        "edges_migrated": 0,
        "errors": [],
    }

    if not v1_db_path.exists():
        stats["errors"].append(f"V1 database not found: {v1_db_path}")
        return stats

    # Backup V1 database
    backup_database(v1_db_path)

    # Create Innovation database with clean schema
    new_conn = sqlite3.connect(str(innovation_db_path))
    new_conn.row_factory = sqlite3.Row
    try:
        new_conn.execute("PRAGMA foreign_keys=ON")
        schema.create_all_tables(new_conn)

        # Ensure default profile exists
        new_conn.execute(
            "INSERT OR IGNORE INTO profiles (profile_id, name, description, mode, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (profile_id, profile_id, "Migrated from V1", "a", datetime.now(UTC).isoformat()),
        )

        # Open V1 database
        v1_conn = sqlite3.connect(str(v1_db_path))
        v1_conn.row_factory = sqlite3.Row
        try:
            stats = _migrate_memories(v1_conn, new_conn, profile_id, stats)
            stats = _migrate_facts(v1_conn, new_conn, profile_id, stats)
            stats = _migrate_entities(v1_conn, new_conn, profile_id, stats)
            stats = _migrate_edges(v1_conn, new_conn, profile_id, stats)
            new_conn.commit()
        finally:
            v1_conn.close()

        set_schema_version(new_conn, CURRENT_SCHEMA_VERSION)
        new_conn.commit()
        logger.info("Migration complete: %s", stats)

    finally:
        new_conn.close()

    return stats


def _migrate_memories(
    v1: sqlite3.Connection,
    new: sqlite3.Connection,
    profile_id: str,
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Migrate episodic_memory → memories table."""
    try:
        rows = v1.execute("SELECT * FROM episodic_memory").fetchall()
    except sqlite3.OperationalError:
        stats["errors"].append("No episodic_memory table in V1")
        return stats

    for row in rows:
        d = dict(row)
        try:
            new.execute(
                "INSERT OR IGNORE INTO memories "
                "(memory_id, profile_id, content, session_id, speaker, role, "
                "session_date, created_at, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    d.get("memory_id", d.get("id", "")),
                    profile_id,
                    d.get("content", ""),
                    d.get("session_id", ""),
                    d.get("speaker", ""),
                    d.get("role", ""),
                    d.get("session_date"),
                    d.get("created_at", datetime.now(UTC).isoformat()),
                    json.dumps({"migrated_from": "v1"}),
                ),
            )
            stats["memories_migrated"] += 1
        except sqlite3.Error as exc:
            stats["errors"].append(f"Memory {d.get('id', '?')}: {exc}")

    return stats


def _migrate_facts(
    v1: sqlite3.Connection,
    new: sqlite3.Connection,
    profile_id: str,
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Migrate semantic_facts → facts table."""
    try:
        rows = v1.execute("SELECT * FROM semantic_facts").fetchall()
    except sqlite3.OperationalError:
        return stats

    for row in rows:
        d = dict(row)
        try:
            new.execute(
                "INSERT OR IGNORE INTO facts "
                "(fact_id, memory_id, profile_id, content, fact_type, "
                "entities, canonical_entities, confidence, importance, "
                "evidence_count, access_count, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    d.get("fact_id", d.get("id", "")),
                    d.get("memory_id", ""),
                    profile_id,
                    d.get("content", d.get("fact", "")),
                    d.get("fact_type", "semantic"),
                    d.get("entities_json", "[]"),
                    d.get("canonical_entities_json", "[]"),
                    d.get("confidence", 1.0),
                    d.get("importance", 0.5),
                    d.get("evidence_count", 1),
                    d.get("access_count", 0),
                    d.get("created_at", datetime.now(UTC).isoformat()),
                ),
            )
            stats["facts_migrated"] += 1
        except sqlite3.Error as exc:
            stats["errors"].append(f"Fact {d.get('id', '?')}: {exc}")

    return stats


def _migrate_entities(
    v1: sqlite3.Connection,
    new: sqlite3.Connection,
    profile_id: str,
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Migrate canonical_entities → entities table."""
    try:
        rows = v1.execute("SELECT * FROM canonical_entities").fetchall()
    except sqlite3.OperationalError:
        return stats

    for row in rows:
        d = dict(row)
        try:
            new.execute(
                "INSERT OR IGNORE INTO entities "
                "(entity_id, profile_id, canonical_name, entity_type, "
                "first_seen, last_seen, fact_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    d.get("entity_id", d.get("id", "")),
                    profile_id,
                    d.get("canonical_name", d.get("name", "")),
                    d.get("entity_type", "unknown"),
                    d.get("first_seen", datetime.now(UTC).isoformat()),
                    d.get("last_seen", datetime.now(UTC).isoformat()),
                    d.get("fact_count", 0),
                ),
            )
            stats["entities_migrated"] += 1
        except sqlite3.Error as exc:
            stats["errors"].append(f"Entity {d.get('id', '?')}: {exc}")

    return stats


def _migrate_edges(
    v1: sqlite3.Connection,
    new: sqlite3.Connection,
    profile_id: str,
    stats: dict[str, Any],
) -> dict[str, Any]:
    """Migrate memory_edges → graph_edges table."""
    try:
        rows = v1.execute("SELECT * FROM memory_edges").fetchall()
    except sqlite3.OperationalError:
        return stats

    for row in rows:
        d = dict(row)
        try:
            new.execute(
                "INSERT OR IGNORE INTO graph_edges "
                "(edge_id, profile_id, source_id, target_id, edge_type, "
                "weight, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    d.get("edge_id", d.get("id", "")),
                    profile_id,
                    d.get("source_id", d.get("source", "")),
                    d.get("target_id", d.get("target", "")),
                    d.get("edge_type", d.get("relation_type", "entity")),
                    d.get("weight", 1.0),
                    d.get("created_at", datetime.now(UTC).isoformat()),
                ),
            )
            stats["edges_migrated"] += 1
        except sqlite3.Error as exc:
            stats["errors"].append(f"Edge {d.get('id', '?')}: {exc}")

    return stats
