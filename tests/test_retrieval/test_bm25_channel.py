# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for superlocalmemory.retrieval.bm25_channel — BM25Plus keyword search.

Covers:
  - tokenize() function (stopword removal, lowercasing, regex)
  - Cold-load from DB (ensure_loaded)
  - Fallback tokenization when no pre-stored tokens
  - Incremental add()
  - search() with matching and non-matching queries
  - search() auto-loads profile on first call
  - document_count property
  - clear() resets state
  - Empty corpus returns empty results
  - Stopword-only query returns empty
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from superlocalmemory.retrieval.bm25_channel import BM25Channel, tokenize
from superlocalmemory.storage import schema as real_schema
from superlocalmemory.storage.database import DatabaseManager
from superlocalmemory.storage.models import AtomicFact, MemoryRecord


# ---------------------------------------------------------------------------
# tokenize()
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_basic_tokenization(self) -> None:
        tokens = tokenize("Alice works at Acme Corp")
        assert "alice" in tokens
        assert "works" in tokens
        assert "acme" in tokens
        assert "corp" in tokens

    def test_stopwords_removed(self) -> None:
        tokens = tokenize("the cat is on the mat")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "on" not in tokens
        assert "cat" in tokens
        assert "mat" in tokens

    def test_lowercase(self) -> None:
        tokens = tokenize("Alice BOB Charlie")
        assert all(t == t.lower() for t in tokens)

    def test_empty_string(self) -> None:
        assert tokenize("") == []

    def test_only_stopwords(self) -> None:
        assert tokenize("the is are was") == []

    def test_hyphenated_words(self) -> None:
        tokens = tokenize("well-known fact")
        assert "well-known" in tokens

    def test_apostrophe_words(self) -> None:
        tokens = tokenize("Alice's friend")
        assert "alice's" in tokens

    def test_numbers_preserved(self) -> None:
        tokens = tokenize("born in 1990")
        assert "born" in tokens
        assert "1990" in tokens


# ---------------------------------------------------------------------------
# BM25Channel with mock DB
# ---------------------------------------------------------------------------

class TestBM25ChannelMocked:
    def _mock_db(
        self,
        tokens_map: dict[str, list[str]] | None = None,
        facts: list[AtomicFact] | None = None,
    ) -> MagicMock:
        db = MagicMock()
        db.get_all_bm25_tokens.return_value = tokens_map or {}
        db.get_all_facts.return_value = facts or []
        return db

    def test_ensure_loaded_from_tokens(self) -> None:
        db = self._mock_db(tokens_map={
            "f1": ["alice", "engineer"],
            "f2": ["bob", "doctor"],
        })
        ch = BM25Channel(db)
        ch.ensure_loaded("default")
        assert ch.document_count == 2

    def test_ensure_loaded_idempotent(self) -> None:
        db = self._mock_db(tokens_map={"f1": ["hello"]})
        ch = BM25Channel(db)
        ch.ensure_loaded("default")
        ch.ensure_loaded("default")
        # Should only call get_all_bm25_tokens once
        assert db.get_all_bm25_tokens.call_count == 1

    def test_ensure_loaded_fallback_to_facts(self) -> None:
        facts = [
            AtomicFact(fact_id="f1", memory_id="m0", content="Alice is an engineer"),
        ]
        db = self._mock_db(tokens_map={}, facts=facts)
        ch = BM25Channel(db)
        ch.ensure_loaded("default")
        assert ch.document_count == 1
        # Should persist tokens for next time
        db.store_bm25_tokens.assert_called_once()

    def test_add_increments_count(self) -> None:
        db = self._mock_db()
        ch = BM25Channel(db)
        ch.add("f1", "Alice works at Acme", "default")
        assert ch.document_count == 1
        db.store_bm25_tokens.assert_called_once()

    def test_add_empty_content_noop(self) -> None:
        db = self._mock_db()
        ch = BM25Channel(db)
        ch.add("f1", "the is are", "default")  # All stopwords
        assert ch.document_count == 0

    def test_search_returns_matching_docs(self) -> None:
        db = self._mock_db(tokens_map={
            "f1": ["alice", "engineer"],
            "f2": ["bob", "doctor"],
        })
        ch = BM25Channel(db)
        results = ch.search("alice engineer", "default")
        assert len(results) > 0
        fact_ids = [r[0] for r in results]
        assert "f1" in fact_ids

    def test_search_auto_loads(self) -> None:
        db = self._mock_db(tokens_map={"f1": ["hello", "world"]})
        ch = BM25Channel(db)
        # Don't call ensure_loaded — search should auto-load
        results = ch.search("hello", "default")
        assert len(results) > 0

    def test_search_empty_corpus(self) -> None:
        db = self._mock_db()
        ch = BM25Channel(db)
        results = ch.search("hello", "default")
        assert results == []

    def test_search_stopword_query(self) -> None:
        db = self._mock_db(tokens_map={"f1": ["hello"]})
        ch = BM25Channel(db)
        results = ch.search("the is are", "default")
        assert results == []

    def test_search_top_k(self) -> None:
        tokens_map = {f"f{i}": ["common", "word"] for i in range(20)}
        db = self._mock_db(tokens_map=tokens_map)
        ch = BM25Channel(db)
        results = ch.search("common word", "default", top_k=5)
        assert len(results) <= 5

    def test_search_scores_descending(self) -> None:
        db = self._mock_db(tokens_map={
            "f1": ["alice", "alice", "alice"],
            "f2": ["alice"],
        })
        ch = BM25Channel(db)
        results = ch.search("alice", "default")
        if len(results) >= 2:
            assert results[0][1] >= results[1][1]

    def test_clear_resets(self) -> None:
        db = self._mock_db(tokens_map={"f1": ["hello"]})
        ch = BM25Channel(db)
        ch.ensure_loaded("default")
        assert ch.document_count == 1
        ch.clear()
        assert ch.document_count == 0


# ---------------------------------------------------------------------------
# BM25Channel with real DB
# ---------------------------------------------------------------------------

class TestBM25ChannelRealDB:
    @pytest.fixture()
    def db(self, tmp_path: Path) -> DatabaseManager:
        db_path = tmp_path / "test.db"
        mgr = DatabaseManager(db_path)
        mgr.initialize(real_schema)
        return mgr

    def test_round_trip_with_real_db(self, db: DatabaseManager) -> None:
        db.store_memory(MemoryRecord(memory_id="m0", content="parent"))
        db.store_fact(AtomicFact(
            fact_id="f1", memory_id="m0", content="Alice is an engineer",
        ))

        ch = BM25Channel(db)
        ch.add("f1", "Alice is an engineer", "default")

        results = ch.search("engineer", "default")
        assert len(results) == 1
        assert results[0][0] == "f1"
        assert results[0][1] > 0.0
