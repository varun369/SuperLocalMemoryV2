# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for superlocalmemory.storage.database — DatabaseManager CRUD.

Covers:
  - store_memory + retrieve via execute
  - store_fact + get_all_facts + get_facts_by_type + get_facts_by_entity
  - store_entity + get_entity_by_name (case-insensitive)
  - store_edge + get_edges_for_node
  - store_temporal_event + get_temporal_events
  - BM25 token persistence (store + retrieve)
  - FTS5 search (store facts, search by text)
  - Transaction commit + rollback
  - Profile isolation (two profiles, data separated)
  - update_fact + delete_fact
  - get_fact_count

Uses the real schema module (storage.schema) since database.py was aligned
to schema.py table names in S17.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from superlocalmemory.storage import schema as real_schema
from superlocalmemory.storage.database import DatabaseManager
from superlocalmemory.storage.models import (
    AtomicFact,
    CanonicalEntity,
    EdgeType,
    EntityAlias,
    FactType,
    GraphEdge,
    MemoryRecord,
    TemporalEvent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path: Path) -> DatabaseManager:
    """DatabaseManager wired to a temp directory with schema applied."""
    db_path = tmp_path / "test.db"
    mgr = DatabaseManager(db_path)
    mgr.initialize(real_schema)
    return mgr


@pytest.fixture()
def db_with_profile(db: DatabaseManager) -> DatabaseManager:
    """DB with an extra profile 'work' pre-created."""
    db.execute(
        "INSERT OR IGNORE INTO profiles (profile_id, name) VALUES ('work', 'Work')"
    )
    return db


# ---------------------------------------------------------------------------
# Memory CRUD
# ---------------------------------------------------------------------------

class TestStoreMemory:
    def test_store_and_retrieve(self, db: DatabaseManager) -> None:
        record = MemoryRecord(
            memory_id="m1",
            profile_id="default",
            content="Hello world",
            session_id="s1",
            speaker="user",
        )
        result_id = db.store_memory(record)
        assert result_id == "m1"

        rows = db.execute(
            "SELECT * FROM memories WHERE memory_id = ?", ("m1",)
        )
        assert len(rows) == 1
        assert dict(rows[0])["content"] == "Hello world"

    def test_store_memory_upsert(self, db: DatabaseManager) -> None:
        r1 = MemoryRecord(memory_id="m_dup", content="v1")
        r2 = MemoryRecord(memory_id="m_dup", content="v2")
        db.store_memory(r1)
        db.store_memory(r2)
        rows = db.execute(
            "SELECT content FROM memories WHERE memory_id = ?", ("m_dup",)
        )
        assert dict(rows[0])["content"] == "v2"


# ---------------------------------------------------------------------------
# Fact CRUD
# ---------------------------------------------------------------------------

class TestStoreFact:
    def _store_parent_memory(self, db: DatabaseManager, memory_id: str = "m0") -> None:
        db.store_memory(MemoryRecord(memory_id=memory_id, content="parent"))

    def test_store_and_get_all_facts(self, db: DatabaseManager) -> None:
        self._store_parent_memory(db)
        f = AtomicFact(
            fact_id="f1", memory_id="m0",
            content="Alice is an engineer",
            fact_type=FactType.SEMANTIC,
        )
        result_id = db.store_fact(f)
        assert result_id == "f1"

        facts = db.get_all_facts("default")
        assert len(facts) == 1
        assert facts[0].content == "Alice is an engineer"
        assert facts[0].fact_type == FactType.SEMANTIC

    def test_get_facts_by_type(self, db: DatabaseManager) -> None:
        self._store_parent_memory(db)
        db.store_fact(AtomicFact(
            fact_id="f_sem", memory_id="m0", content="cats are mammals",
            fact_type=FactType.SEMANTIC,
        ))
        db.store_fact(AtomicFact(
            fact_id="f_epi", memory_id="m0", content="Alice met Bob",
            fact_type=FactType.EPISODIC,
        ))

        semantic = db.get_facts_by_type(FactType.SEMANTIC, "default")
        assert len(semantic) == 1
        assert semantic[0].fact_id == "f_sem"

        episodic = db.get_facts_by_type(FactType.EPISODIC, "default")
        assert len(episodic) == 1
        assert episodic[0].fact_id == "f_epi"

    def test_get_facts_by_entity(self, db: DatabaseManager) -> None:
        self._store_parent_memory(db)
        db.store_fact(AtomicFact(
            fact_id="fe1", memory_id="m0",
            content="Alice works at Acme",
            canonical_entities=["ent_alice"],
        ))
        db.store_fact(AtomicFact(
            fact_id="fe2", memory_id="m0",
            content="Bob works at Beta",
            canonical_entities=["ent_bob"],
        ))

        alice_facts = db.get_facts_by_entity("ent_alice", "default")
        assert len(alice_facts) == 1
        assert alice_facts[0].fact_id == "fe1"

    def test_update_fact(self, db: DatabaseManager) -> None:
        self._store_parent_memory(db)
        db.store_fact(AtomicFact(
            fact_id="f_upd", memory_id="m0", content="old content",
        ))
        db.update_fact("f_upd", {"content": "new content", "confidence": 0.9})

        facts = db.get_all_facts("default")
        match = [f for f in facts if f.fact_id == "f_upd"]
        assert len(match) == 1
        assert match[0].content == "new content"
        assert match[0].confidence == 0.9

    def test_update_fact_empty_raises(self, db: DatabaseManager) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            db.update_fact("f_any", {})

    def test_delete_fact(self, db: DatabaseManager) -> None:
        self._store_parent_memory(db)
        db.store_fact(AtomicFact(
            fact_id="f_del", memory_id="m0", content="to delete",
        ))
        db.delete_fact("f_del")
        assert db.get_fact_count("default") == 0

    def test_get_fact_count(self, db: DatabaseManager) -> None:
        self._store_parent_memory(db)
        assert db.get_fact_count("default") == 0
        db.store_fact(AtomicFact(fact_id="fc1", memory_id="m0", content="a"))
        db.store_fact(AtomicFact(fact_id="fc2", memory_id="m0", content="b"))
        assert db.get_fact_count("default") == 2


# ---------------------------------------------------------------------------
# Entity CRUD
# ---------------------------------------------------------------------------

class TestStoreEntity:
    def test_store_and_get_by_name(self, db: DatabaseManager) -> None:
        entity = CanonicalEntity(
            entity_id="e1", canonical_name="Alice",
            entity_type="person",
        )
        db.store_entity(entity)
        found = db.get_entity_by_name("Alice", "default")
        assert found is not None
        assert found.entity_id == "e1"
        assert found.entity_type == "person"

    def test_get_entity_case_insensitive(self, db: DatabaseManager) -> None:
        db.store_entity(CanonicalEntity(
            entity_id="e2", canonical_name="Bob",
        ))
        assert db.get_entity_by_name("bob", "default") is not None
        assert db.get_entity_by_name("BOB", "default") is not None

    def test_get_entity_not_found(self, db: DatabaseManager) -> None:
        assert db.get_entity_by_name("nonexistent", "default") is None


# ---------------------------------------------------------------------------
# Alias CRUD
# ---------------------------------------------------------------------------

class TestStoreAlias:
    def test_store_and_get_aliases(self, db: DatabaseManager) -> None:
        db.store_entity(CanonicalEntity(entity_id="ea", canonical_name="Alice"))
        db.store_alias(EntityAlias(
            alias_id="a1", entity_id="ea", alias="Ali", source="test",
        ))
        db.store_alias(EntityAlias(
            alias_id="a2", entity_id="ea", alias="A", source="test",
        ))
        aliases = db.get_aliases_for_entity("ea")
        assert len(aliases) == 2
        alias_names = {a.alias for a in aliases}
        assert alias_names == {"Ali", "A"}


# ---------------------------------------------------------------------------
# Edge CRUD
# ---------------------------------------------------------------------------

class TestStoreEdge:
    def test_store_and_get_edges(self, db: DatabaseManager) -> None:
        edge = GraphEdge(
            edge_id="edge1", source_id="f1", target_id="f2",
            edge_type=EdgeType.SEMANTIC, weight=0.9,
        )
        db.store_edge(edge)
        edges = db.get_edges_for_node("f1", "default")
        assert len(edges) == 1
        assert edges[0].edge_type == EdgeType.SEMANTIC
        assert edges[0].weight == 0.9

    def test_get_edges_for_node_as_target(self, db: DatabaseManager) -> None:
        db.store_edge(GraphEdge(
            edge_id="e_t", source_id="x", target_id="y",
        ))
        edges = db.get_edges_for_node("y", "default")
        assert len(edges) == 1


# ---------------------------------------------------------------------------
# Temporal events
# ---------------------------------------------------------------------------

class TestTemporalEvents:
    def test_store_and_get(self, db: DatabaseManager) -> None:
        db.store_entity(CanonicalEntity(entity_id="te_e", canonical_name="Eve"))
        db.store_memory(MemoryRecord(memory_id="te_m", content="event"))
        db.store_fact(AtomicFact(fact_id="te_f", memory_id="te_m", content="event fact"))

        event = TemporalEvent(
            event_id="te1", entity_id="te_e", fact_id="te_f",
            observation_date="2026-03-11",
            referenced_date="2026-03-10",
            description="Eve started a new job",
        )
        db.store_temporal_event(event)

        events = db.get_temporal_events("te_e", "default")
        assert len(events) == 1
        assert events[0].description == "Eve started a new job"
        assert events[0].observation_date == "2026-03-11"


# ---------------------------------------------------------------------------
# BM25 token persistence
# ---------------------------------------------------------------------------

class TestBM25Tokens:
    def test_store_and_retrieve(self, db: DatabaseManager) -> None:
        db.store_bm25_tokens("f_bm", "default", ["alice", "works", "acme"])
        index = db.get_all_bm25_tokens("default")
        assert "f_bm" in index
        assert index["f_bm"] == ["alice", "works", "acme"]

    def test_upsert_replaces(self, db: DatabaseManager) -> None:
        db.store_bm25_tokens("f_bm2", "default", ["old"])
        db.store_bm25_tokens("f_bm2", "default", ["new", "tokens"])
        index = db.get_all_bm25_tokens("default")
        assert index["f_bm2"] == ["new", "tokens"]

    def test_empty_for_unknown_profile(self, db: DatabaseManager) -> None:
        index = db.get_all_bm25_tokens("nonexistent")
        assert index == {}


# ---------------------------------------------------------------------------
# FTS5 search
# ---------------------------------------------------------------------------

class TestFTS5Search:
    def test_search_by_text(self, db: DatabaseManager) -> None:
        db.store_memory(MemoryRecord(memory_id="m_fts", content="parent"))
        db.store_fact(AtomicFact(
            fact_id="fts_1", memory_id="m_fts",
            content="Alice loves hiking in the mountains",
        ))
        db.store_fact(AtomicFact(
            fact_id="fts_2", memory_id="m_fts",
            content="Bob enjoys swimming in the ocean",
        ))

        results = db.search_facts_fts("hiking", "default")
        assert len(results) == 1
        assert results[0].fact_id == "fts_1"

    def test_fts_no_results(self, db: DatabaseManager) -> None:
        results = db.search_facts_fts("xyzzyx_no_match", "default")
        assert results == []


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

class TestTransaction:
    def test_commit_on_success(self, db: DatabaseManager) -> None:
        with db.transaction():
            db.execute(
                "INSERT INTO memories (memory_id, profile_id, content) "
                "VALUES ('txn_ok', 'default', 'committed')"
            )
        rows = db.execute(
            "SELECT * FROM memories WHERE memory_id = 'txn_ok'"
        )
        assert len(rows) == 1

    def test_rollback_on_error(self, db: DatabaseManager) -> None:
        try:
            with db.transaction():
                db.execute(
                    "INSERT INTO memories (memory_id, profile_id, content) "
                    "VALUES ('txn_fail', 'default', 'should rollback')"
                )
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass

        rows = db.execute(
            "SELECT * FROM memories WHERE memory_id = 'txn_fail'"
        )
        assert len(rows) == 0, "Transaction should have rolled back"


# ---------------------------------------------------------------------------
# Profile isolation
# ---------------------------------------------------------------------------

class TestProfileIsolation:
    def test_two_profiles_data_separated(
        self, db_with_profile: DatabaseManager
    ) -> None:
        db = db_with_profile

        # Store memory + fact in default
        db.store_memory(MemoryRecord(
            memory_id="md", profile_id="default", content="default data",
        ))
        db.store_fact(AtomicFact(
            fact_id="fd", memory_id="md", profile_id="default",
            content="default fact",
        ))

        # Store memory + fact in work
        db.store_memory(MemoryRecord(
            memory_id="mw", profile_id="work", content="work data",
        ))
        db.store_fact(AtomicFact(
            fact_id="fw", memory_id="mw", profile_id="work",
            content="work fact",
        ))

        # Verify isolation
        default_facts = db.get_all_facts("default")
        work_facts = db.get_all_facts("work")

        assert len(default_facts) == 1
        assert default_facts[0].fact_id == "fd"

        assert len(work_facts) == 1
        assert work_facts[0].fact_id == "fw"

    def test_entity_isolated_by_profile(
        self, db_with_profile: DatabaseManager
    ) -> None:
        db = db_with_profile
        db.store_entity(CanonicalEntity(
            entity_id="e_def", profile_id="default", canonical_name="Alice",
        ))
        db.store_entity(CanonicalEntity(
            entity_id="e_wrk", profile_id="work", canonical_name="Alice",
        ))

        default_alice = db.get_entity_by_name("Alice", "default")
        work_alice = db.get_entity_by_name("Alice", "work")

        assert default_alice is not None
        assert work_alice is not None
        assert default_alice.entity_id != work_alice.entity_id


# ---------------------------------------------------------------------------
# Config store
# ---------------------------------------------------------------------------

class TestConfigStore:
    def test_set_and_get_config(self, db: DatabaseManager) -> None:
        db.set_config("mode", "a")
        assert db.get_config("mode") == "a"

    def test_get_config_returns_none_for_missing(self, db: DatabaseManager) -> None:
        assert db.get_config("nonexistent") is None

    def test_set_config_upsert(self, db: DatabaseManager) -> None:
        db.set_config("k", "v1")
        db.set_config("k", "v2")
        assert db.get_config("k") == "v2"


# ---------------------------------------------------------------------------
# Context manager protocol
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_works_as_context_manager(self, tmp_path: Path) -> None:
        db_path = tmp_path / "ctx.db"
        with DatabaseManager(db_path) as mgr:
            mgr.initialize(real_schema)
            mgr.store_memory(MemoryRecord(memory_id="ctx1", content="ctx test"))
            rows = mgr.execute("SELECT * FROM memories WHERE memory_id = 'ctx1'")
            assert len(rows) == 1

    def test_list_tables(self, db: DatabaseManager) -> None:
        tables = db.list_tables()
        assert "memories" in tables
        assert "atomic_facts" in tables
        assert "canonical_entities" in tables
