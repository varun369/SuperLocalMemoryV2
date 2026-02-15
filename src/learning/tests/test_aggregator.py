#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Tests for CrossProjectAggregator (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
"""

import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


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
    """Create a minimal memory.db with test data."""
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
                                  source_protocol, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Temporal Decay
# ---------------------------------------------------------------------------

class TestTemporalDecay:
    def test_days_since_recent(self):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        now = datetime(2026, 2, 16, 12, 0, 0)
        ts = "2026-02-16T10:00:00"
        days = CrossProjectAggregator._days_since(ts, now)
        assert 0.0 <= days < 1.0

    def test_days_since_365_days_ago(self):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        now = datetime(2026, 2, 16, 12, 0, 0)
        old = (now - timedelta(days=365)).isoformat()
        days = CrossProjectAggregator._days_since(old, now)
        assert abs(days - 365.0) < 1.0

    def test_days_since_empty_string(self):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        assert CrossProjectAggregator._days_since("") == 0.0

    def test_days_since_invalid_string(self):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        assert CrossProjectAggregator._days_since("not-a-date") == 0.0

    def test_days_since_space_separated(self):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        now = datetime(2026, 2, 16, 12, 0, 0)
        ts = "2026-02-15 12:00:00"
        days = CrossProjectAggregator._days_since(ts, now)
        assert abs(days - 1.0) < 0.01

    def test_decay_weight_recent(self):
        """Recent timestamp -> weight close to 1.0."""
        from src.learning.cross_project_aggregator import DECAY_HALF_LIFE_DAYS
        # 0 days -> exp(0) = 1.0
        weight = math.exp(-0.0 / DECAY_HALF_LIFE_DAYS)
        assert abs(weight - 1.0) < 0.001

    def test_decay_weight_365_days(self):
        """365-day-old pattern -> weight ~ 0.37."""
        from src.learning.cross_project_aggregator import DECAY_HALF_LIFE_DAYS
        weight = math.exp(-365.0 / DECAY_HALF_LIFE_DAYS)
        assert 0.30 < weight < 0.40


# ---------------------------------------------------------------------------
# Contradiction Detection
# ---------------------------------------------------------------------------

class TestContradictionDetection:
    def test_cross_profile_disagreement(self, learning_db, memory_db):
        """Two profiles with different values should trigger a contradiction."""
        from src.learning.cross_project_aggregator import CrossProjectAggregator

        aggregator = CrossProjectAggregator(
            memory_db_path=memory_db,
            learning_db=learning_db,
        )

        pattern_data = {
            "value": "react",
            "profile_history": [
                {"profile": "work", "value": "react", "confidence": 0.8,
                 "weight": 1.0, "timestamp": "2026-02-16"},
                {"profile": "personal", "value": "vue", "confidence": 0.7,
                 "weight": 0.9, "timestamp": "2026-02-15"},
            ],
        }

        contradictions = aggregator._detect_contradictions("frontend", pattern_data)
        assert len(contradictions) >= 1
        assert any("vue" in c and "react" in c for c in contradictions)

    def test_no_contradiction_when_unanimous(self, learning_db, memory_db):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        aggregator = CrossProjectAggregator(
            memory_db_path=memory_db,
            learning_db=learning_db,
        )
        pattern_data = {
            "value": "python",
            "profile_history": [
                {"profile": "work", "value": "python", "confidence": 0.9,
                 "weight": 1.0, "timestamp": "2026-02-16"},
                {"profile": "personal", "value": "python", "confidence": 0.8,
                 "weight": 0.9, "timestamp": "2026-02-15"},
            ],
        }
        contradictions = aggregator._detect_contradictions("lang", pattern_data)
        assert len(contradictions) == 0


# ---------------------------------------------------------------------------
# get_tech_preferences from learning.db
# ---------------------------------------------------------------------------

class TestGetTechPreferences:
    def test_empty_db_returns_empty(self, learning_db, memory_db):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        aggregator = CrossProjectAggregator(
            memory_db_path=memory_db,
            learning_db=learning_db,
        )
        prefs = aggregator.get_tech_preferences(min_confidence=0.0)
        assert prefs == {}

    def test_stored_patterns_returned(self, learning_db, memory_db):
        from src.learning.cross_project_aggregator import CrossProjectAggregator

        # Pre-populate learning.db with a preference pattern
        learning_db.upsert_transferable_pattern(
            pattern_type="preference",
            key="language",
            value="python",
            confidence=0.85,
            evidence_count=15,
            profiles_seen=2,
        )

        aggregator = CrossProjectAggregator(
            memory_db_path=memory_db,
            learning_db=learning_db,
        )
        prefs = aggregator.get_tech_preferences(min_confidence=0.5)
        assert "language" in prefs
        assert prefs["language"]["value"] == "python"
        assert prefs["language"]["confidence"] == 0.85

    def test_confidence_filter(self, learning_db, memory_db):
        from src.learning.cross_project_aggregator import CrossProjectAggregator

        learning_db.upsert_transferable_pattern(
            pattern_type="preference", key="low", value="x",
            confidence=0.3, evidence_count=2,
        )
        learning_db.upsert_transferable_pattern(
            pattern_type="preference", key="high", value="y",
            confidence=0.9, evidence_count=20,
        )

        aggregator = CrossProjectAggregator(
            memory_db_path=memory_db,
            learning_db=learning_db,
        )
        prefs = aggregator.get_tech_preferences(min_confidence=0.6)
        assert "high" in prefs
        assert "low" not in prefs

    def test_no_learning_db(self, memory_db):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        aggregator = CrossProjectAggregator(
            memory_db_path=memory_db,
            learning_db=None,
        )
        # Should not crash
        prefs = aggregator.get_tech_preferences()
        assert prefs == {}


# ---------------------------------------------------------------------------
# is_within_window
# ---------------------------------------------------------------------------

class TestIsWithinWindow:
    def test_recent_within_window(self):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        now_str = datetime.now().isoformat()
        assert CrossProjectAggregator._is_within_window(now_str, 90) is True

    def test_old_outside_window(self):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        old = (datetime.now() - timedelta(days=200)).isoformat()
        assert CrossProjectAggregator._is_within_window(old, 90) is False

    def test_empty_timestamp(self):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        assert CrossProjectAggregator._is_within_window("", 90) is False

    def test_invalid_timestamp(self):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        assert CrossProjectAggregator._is_within_window("not-a-date", 90) is False


# ---------------------------------------------------------------------------
# Preference Context Formatting
# ---------------------------------------------------------------------------

class TestPreferenceContext:
    def test_no_preferences(self, learning_db, memory_db):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        aggregator = CrossProjectAggregator(
            memory_db_path=memory_db,
            learning_db=learning_db,
        )
        ctx = aggregator.get_preference_context()
        assert "No transferable preferences learned yet" in ctx

    def test_with_preferences(self, learning_db, memory_db):
        from src.learning.cross_project_aggregator import CrossProjectAggregator
        learning_db.upsert_transferable_pattern(
            pattern_type="preference", key="framework", value="FastAPI",
            confidence=0.8, evidence_count=10, profiles_seen=2,
        )
        aggregator = CrossProjectAggregator(
            memory_db_path=memory_db,
            learning_db=learning_db,
        )
        ctx = aggregator.get_preference_context(min_confidence=0.5)
        assert "FastAPI" in ctx
        assert "Framework" in ctx  # Title-cased key
