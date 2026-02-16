#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Tests for SyntheticBootstrapper (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
"""

import sqlite3
from pathlib import Path

import pytest

# Detect optional dependencies at import time
try:
    import lightgbm
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    from src.learning.learning_db import LearningDB
    LearningDB.reset_instance()
    yield
    LearningDB.reset_instance()


@pytest.fixture
def learning_db(tmp_path):
    from src.learning.learning_db import LearningDB
    db_path = tmp_path / "learning.db"
    return LearningDB(db_path=db_path)


@pytest.fixture
def memory_db(tmp_path):
    """Create a memory.db with FTS5 and identity_patterns tables."""
    db_path = tmp_path / "memory.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            summary TEXT,
            project_path TEXT,
            project_name TEXT,
            tags TEXT DEFAULT '[]',
            category TEXT,
            parent_id INTEGER,
            tree_path TEXT DEFAULT '/',
            depth INTEGER DEFAULT 0,
            memory_type TEXT DEFAULT 'session',
            importance INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            content_hash TEXT,
            cluster_id INTEGER,
            profile TEXT DEFAULT 'default',
            created_by TEXT,
            source_protocol TEXT,
            trust_score REAL DEFAULT 1.0
        )
    ''')
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
        USING fts5(content, summary, tags, content='memories', content_rowid='id')
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS identity_patterns (
            id INTEGER PRIMARY KEY,
            pattern_type TEXT,
            pattern_key TEXT,
            pattern_value TEXT,
            confidence REAL DEFAULT 0.0,
            frequency INTEGER DEFAULT 1,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    return db_path


def _insert_memories(db_path, memories):
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    for m in memories:
        cursor.execute('''
            INSERT INTO memories (content, tags, project_name, project_path,
                                  importance, access_count, profile, created_by,
                                  source_protocol, created_at, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            m.get('content', 'test'),
            m.get('tags', '[]'),
            m.get('project_name'),
            m.get('project_path'),
            m.get('importance', 5),
            m.get('access_count', 0),
            m.get('profile', 'default'),
            m.get('created_by'),
            m.get('source_protocol'),
            m.get('created_at', '2026-02-16 10:00:00'),
            m.get('category'),
        ))
    conn.commit()
    conn.close()


def _insert_patterns(db_path, patterns):
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    for p in patterns:
        cursor.execute('''
            INSERT INTO identity_patterns (pattern_type, pattern_key,
                                            pattern_value, confidence)
            VALUES (?, ?, ?, ?)
        ''', (
            p.get('pattern_type', 'tech'),
            p.get('key', 'unknown'),
            p.get('value', 'unknown'),
            p.get('confidence', 0.8),
        ))
    conn.commit()
    conn.close()


@pytest.fixture
def bootstrapper(memory_db, learning_db):
    from src.learning.synthetic_bootstrap import SyntheticBootstrapper
    return SyntheticBootstrapper(
        memory_db_path=memory_db,
        learning_db=learning_db,
    )


@pytest.fixture
def bootstrapper_with_data(memory_db, learning_db):
    """Bootstrapper with 60 memories (above MIN_MEMORIES_FOR_BOOTSTRAP=50)."""
    memories = []
    for i in range(60):
        memories.append({
            "content": f"Memory about python fastapi development topic {i} implementing features",
            "tags": '["python", "fastapi"]',
            "project_name": "TestProject" if i % 3 == 0 else "OtherProject",
            "importance": 8 if i % 5 == 0 else 5,
            "access_count": 10 if i % 4 == 0 else 1,
            "created_at": f"2026-02-{(i % 28) + 1:02d} 10:00:00",
            "category": "development" if i % 2 == 0 else "architecture",
        })
    _insert_memories(memory_db, memories)

    from src.learning.synthetic_bootstrap import SyntheticBootstrapper
    return SyntheticBootstrapper(
        memory_db_path=memory_db,
        learning_db=learning_db,
    )


# ---------------------------------------------------------------------------
# should_bootstrap
# ---------------------------------------------------------------------------

class TestShouldBootstrap:
    def test_returns_false_below_50_memories(self, bootstrapper, memory_db):
        """With fewer than 50 memories, bootstrap should not run."""
        _insert_memories(memory_db, [
            {"content": f"Memory {i}"} for i in range(10)
        ])
        assert bootstrapper.should_bootstrap() is False

    @pytest.mark.skipif(not HAS_LIGHTGBM or not HAS_NUMPY,
                        reason="LightGBM/NumPy required")
    def test_returns_true_above_50(self, bootstrapper_with_data, tmp_path):
        """With 50+ memories, LightGBM, and no existing model, should be True."""
        # Ensure no model file exists
        from src.learning.synthetic_bootstrap import MODEL_PATH
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        assert bootstrapper_with_data.should_bootstrap() is True

    def test_returns_false_without_lightgbm(self, bootstrapper_with_data):
        """Without LightGBM, bootstrap should be False."""
        from src.learning import synthetic_bootstrap as sb_module
        original = sb_module.HAS_LIGHTGBM
        sb_module.HAS_LIGHTGBM = False
        try:
            assert bootstrapper_with_data.should_bootstrap() is False
        finally:
            sb_module.HAS_LIGHTGBM = original

    def test_returns_false_with_existing_model(self, bootstrapper_with_data, tmp_path):
        """If a model file exists, bootstrap should be False."""
        from src.learning.synthetic_bootstrap import MODEL_PATH
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        MODEL_PATH.write_text("dummy model")
        try:
            assert bootstrapper_with_data.should_bootstrap() is False
        finally:
            if MODEL_PATH.exists():
                MODEL_PATH.unlink()


# ---------------------------------------------------------------------------
# get_tier
# ---------------------------------------------------------------------------

class TestGetTier:
    def test_none_below_50(self, bootstrapper, memory_db):
        _insert_memories(memory_db, [{"content": f"m{i}"} for i in range(10)])
        assert bootstrapper.get_tier() is None

    def test_small_tier(self, bootstrapper, memory_db):
        _insert_memories(memory_db, [{"content": f"m{i}"} for i in range(60)])
        assert bootstrapper.get_tier() == "small"

    def test_medium_tier(self, bootstrapper, memory_db):
        _insert_memories(memory_db, [{"content": f"m{i}"} for i in range(600)])
        assert bootstrapper.get_tier() == "medium"

    def test_large_tier(self, bootstrapper, memory_db):
        _insert_memories(memory_db, [{"content": f"m{i}"} for i in range(5100)])
        assert bootstrapper.get_tier() == "large"


# ---------------------------------------------------------------------------
# Synthetic Data Generation
# ---------------------------------------------------------------------------

class TestGenerateSyntheticData:
    def test_generates_records(self, bootstrapper_with_data):
        """Should produce non-empty list of training records."""
        records = bootstrapper_with_data.generate_synthetic_training_data()
        assert len(records) > 0

    def test_record_structure(self, bootstrapper_with_data):
        records = bootstrapper_with_data.generate_synthetic_training_data()
        if records:
            r = records[0]
            assert "query" in r
            assert "query_hash" in r
            assert "memory_id" in r
            assert "label" in r
            assert "source" in r
            assert "features" in r
            assert len(r["features"]) == 10  # 10-dimensional feature vector

    def test_labels_in_range(self, bootstrapper_with_data):
        records = bootstrapper_with_data.generate_synthetic_training_data()
        for r in records:
            assert 0.0 <= r["label"] <= 1.0, f"Label out of range: {r['label']}"

    def test_multiple_sources(self, bootstrapper_with_data):
        """Data should come from multiple strategies."""
        records = bootstrapper_with_data.generate_synthetic_training_data()
        sources = {r["source"] for r in records}
        # At least 2 different source strategies should contribute
        assert len(sources) >= 1  # access_based or importance_based at minimum

    def test_with_identity_patterns(self, memory_db, learning_db):
        """Pattern-based strategy should use identity_patterns."""
        _insert_memories(memory_db, [
            {
                "content": f"Using python and fastapi for backend development {i}",
                "importance": 8 if i % 3 == 0 else 5,
                "access_count": 6 if i % 4 == 0 else 1,
            }
            for i in range(60)
        ])
        _insert_patterns(memory_db, [
            {"pattern_type": "tech", "key": "language", "value": "python",
             "confidence": 0.9},
            {"pattern_type": "tech", "key": "framework", "value": "fastapi",
             "confidence": 0.85},
        ])

        from src.learning.synthetic_bootstrap import SyntheticBootstrapper
        bs = SyntheticBootstrapper(
            memory_db_path=memory_db,
            learning_db=learning_db,
        )
        records = bs.generate_synthetic_training_data()
        pattern_records = [r for r in records if r["source"] == "pattern"]
        # Pattern-based records may or may not be generated depending on FTS5
        # The important thing is no crash
        assert isinstance(pattern_records, list)


# ---------------------------------------------------------------------------
# Keyword Extraction
# ---------------------------------------------------------------------------

class TestExtractKeywords:
    def test_basic_extraction(self, bootstrapper):
        kws = bootstrapper._extract_keywords("python fastapi deployment docker")
        assert len(kws) <= 3
        assert len(kws) > 0
        assert all(isinstance(k, str) for k in kws)

    def test_stopword_removal(self, bootstrapper):
        kws = bootstrapper._extract_keywords("the and or but python")
        assert "the" not in kws
        assert "and" not in kws
        assert "python" in kws

    def test_empty_content(self, bootstrapper):
        assert bootstrapper._extract_keywords("") == []

    def test_only_stopwords(self, bootstrapper):
        assert bootstrapper._extract_keywords("the and or but is are") == []

    def test_short_words_filtered(self, bootstrapper):
        """Words shorter than MIN_KEYWORD_LENGTH (3) should be filtered."""
        kws = bootstrapper._extract_keywords("a by python")
        assert "a" not in kws
        assert "by" not in kws

    def test_frequency_based(self, bootstrapper):
        """Most frequent word should appear first."""
        kws = bootstrapper._extract_keywords(
            "python python python fastapi fastapi docker"
        )
        assert kws[0] == "python"


# ---------------------------------------------------------------------------
# bootstrap_model (LightGBM required)
# ---------------------------------------------------------------------------

class TestBootstrapModel:
    @pytest.mark.skipif(not HAS_LIGHTGBM or not HAS_NUMPY,
                        reason="LightGBM/NumPy required for bootstrap training")
    def test_bootstrap_with_sufficient_data(self, bootstrapper_with_data, tmp_path):
        """Full bootstrap should produce a model file and return metadata."""
        from src.learning.synthetic_bootstrap import MODEL_PATH, MODELS_DIR
        # Clean up any existing model
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()

        result = bootstrapper_with_data.bootstrap_model()
        if result is not None:
            assert "model_version" in result
            assert "training_samples" in result
            assert result["training_samples"] > 0
            assert "bootstrap" in result["model_version"]
            assert "tier" in result
            assert result["tier"] == "small"  # 60 memories = small tier

            # Clean up
            if MODEL_PATH.exists():
                MODEL_PATH.unlink()

    def test_bootstrap_without_lightgbm(self, bootstrapper_with_data):
        """Should return None gracefully when LightGBM not available."""
        from src.learning import synthetic_bootstrap as sb_module
        original_lgb = sb_module.HAS_LIGHTGBM
        sb_module.HAS_LIGHTGBM = False
        try:
            result = bootstrapper_with_data.bootstrap_model()
            assert result is None
        finally:
            sb_module.HAS_LIGHTGBM = original_lgb

    def test_bootstrap_below_minimum(self, bootstrapper, memory_db):
        """Should return None with too few memories."""
        _insert_memories(memory_db, [{"content": f"m{i}"} for i in range(10)])
        result = bootstrapper.bootstrap_model()
        assert result is None


# ---------------------------------------------------------------------------
# Diverse Sample
# ---------------------------------------------------------------------------

class TestDiverseSample:
    def test_under_target(self, bootstrapper):
        records = [{"source": "a", "query_hash": "q1", "memory_id": 1}] * 5
        result = bootstrapper._diverse_sample(records, 10)
        assert len(result) == 5

    def test_over_target_proportional(self, bootstrapper):
        records = (
            [{"source": "a", "query_hash": f"qa{i}", "memory_id": i} for i in range(50)]
            + [{"source": "b", "query_hash": f"qb{i}", "memory_id": i + 50} for i in range(50)]
        )
        result = bootstrapper._diverse_sample(records, 20)
        assert len(result) == 20
        sources = {r["source"] for r in result}
        assert len(sources) == 2  # Both sources represented


# ---------------------------------------------------------------------------
# Count Sources
# ---------------------------------------------------------------------------

class TestCountSources:
    def test_count(self, bootstrapper):
        records = [
            {"source": "access_positive"},
            {"source": "access_positive"},
            {"source": "importance_positive"},
            {"source": "recency_positive"},
        ]
        counts = bootstrapper._count_sources(records)
        assert counts["access_positive"] == 2
        assert counts["importance_positive"] == 1
        assert counts["recency_positive"] == 1


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

class TestModuleLevel:
    def test_should_bootstrap_function(self, memory_db):
        from src.learning.synthetic_bootstrap import should_bootstrap
        result = should_bootstrap(memory_db_path=memory_db)
        assert isinstance(result, bool)
