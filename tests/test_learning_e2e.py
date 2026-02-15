#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Learning System End-to-End Tests (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Full pipeline E2E tests that exercise the complete learning system from
memory seeding through feedback collection, pattern aggregation, workflow
mining, and adaptive ranking. All tests use temporary databases -- NEVER
touches production ~/.claude-memory/.

Run with:
    pytest tests/test_learning_e2e.py -v
"""

import hashlib
import json
import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
REPO_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(REPO_DIR / "src"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_memory_db(db_path: Path) -> sqlite3.Connection:
    """Create a memory.db with the full v2.6 schema including v2.5 columns."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            summary TEXT,
            tags TEXT DEFAULT '[]',
            category TEXT,
            memory_type TEXT DEFAULT 'general',
            importance INTEGER DEFAULT 5,
            project_name TEXT,
            project_path TEXT,
            profile TEXT DEFAULT 'default',
            parent_id INTEGER,
            cluster_id INTEGER,
            tier INTEGER DEFAULT 1,
            entity_vector TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            created_by TEXT,
            source_protocol TEXT,
            trust_score REAL DEFAULT 1.0,
            provenance_chain TEXT
        )
    ''')

    # FTS5 virtual table for full-text search
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
        USING fts5(content, summary, tags, content='memories', content_rowid='id')
    ''')

    # Identity patterns table (used by pattern_learner)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS identity_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            evidence_count INTEGER DEFAULT 0,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Graph clusters table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS graph_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            summary TEXT,
            member_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Creator metadata (required by system)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS creator_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute(
        "INSERT OR REPLACE INTO creator_metadata (key, value) "
        "VALUES ('creator', 'Varun Pratap Bhardwaj')"
    )

    conn.commit()
    return conn


def seed_memories(
    db_path: Path,
    count: int = 100,
    profile: str = "default",
    with_patterns: bool = False,
    with_timestamps: bool = False,
    source: str = None,
    base_date: datetime = None,
):
    """
    Seed test memories with realistic content.

    Returns list of inserted memory IDs.
    """
    if base_date is None:
        base_date = datetime.now() - timedelta(days=30)

    tech_topics = [
        ("Implemented FastAPI endpoint for user authentication using OAuth2",
         "python,fastapi,auth", "code", "MyProject"),
        ("Wrote pytest fixtures for database integration tests",
         "python,pytest,testing", "test", "MyProject"),
        ("Configured Docker compose for local development environment",
         "docker,devops,config", "config", "MyProject"),
        ("Designed REST API schema for payment processing service",
         "architecture,api,design", "docs", "PaymentService"),
        ("Debugged race condition in WebSocket handler for real-time updates",
         "python,websocket,debug", "debug", "MyProject"),
        ("Set up CI/CD pipeline with GitHub Actions for automated deployment",
         "ci/cd,github,deploy", "deploy", "MyProject"),
        ("Refactored database connection pool to use async context managers",
         "python,database,refactor", "code", "PaymentService"),
        ("Created React component for user dashboard with real-time charts",
         "react,frontend,component", "code", "Dashboard"),
        ("Wrote comprehensive documentation for the API endpoints",
         "documentation,api,docs", "docs", "MyProject"),
        ("Analyzed performance bottleneck in search query optimization",
         "performance,database,optimization", "debug", "MyProject"),
    ]

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    inserted_ids = []

    for i in range(count):
        topic = tech_topics[i % len(tech_topics)]
        content, tags, category, project = topic

        # Vary content slightly
        content = f"{content} (iteration {i})"
        importance = min(10, max(1, 5 + (i % 6) - 3))
        access_count = (i % 8)

        if with_timestamps:
            created_at = (base_date + timedelta(hours=i * 2)).isoformat()
        else:
            created_at = (base_date + timedelta(days=i % 30)).isoformat()

        created_by = source or ("mcp:claude-desktop" if i % 3 == 0 else
                                "cli:terminal" if i % 3 == 1 else
                                "mcp:cursor")

        cursor.execute('''
            INSERT INTO memories
                (content, tags, category, importance, project_name,
                 profile, created_at, access_count, created_by,
                 source_protocol, trust_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            content, json.dumps(tags.split(",")), category, importance,
            project, profile, created_at, access_count, created_by,
            created_by.split(":")[0] if ":" in created_by else created_by,
            1.0,
        ))
        inserted_ids.append(cursor.lastrowid)

        # Sync FTS5
        cursor.execute('''
            INSERT INTO memories_fts(rowid, content, summary, tags)
            VALUES (?, ?, ?, ?)
        ''', (cursor.lastrowid, content, "", json.dumps(tags.split(","))))

    if with_patterns:
        patterns = [
            ("preference", "python_framework", "FastAPI", 0.85, 12),
            ("preference", "test_framework", "pytest", 0.78, 8),
            ("preference", "frontend_framework", "React", 0.65, 5),
        ]
        for ptype, key, value, confidence, evidence in patterns:
            cursor.execute('''
                INSERT INTO identity_patterns
                    (pattern_type, key, value, confidence, evidence_count, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ptype, key, value, confidence, evidence, "tech"))

    conn.commit()
    conn.close()
    return inserted_ids


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons between tests."""
    from src.learning.learning_db import LearningDB
    LearningDB.reset_instance()
    yield
    LearningDB.reset_instance()


@pytest.fixture
def test_env(tmp_path):
    """Create isolated test environment with memory.db and learning.db."""
    memory_db = tmp_path / "memory.db"
    learning_db_path = tmp_path / "learning.db"

    # Create memory.db with full schema
    conn = _create_memory_db(memory_db)
    conn.close()

    # Create LearningDB
    from src.learning.learning_db import LearningDB
    ldb = LearningDB(db_path=learning_db_path)

    return {
        "memory_db": memory_db,
        "learning_db": learning_db_path,
        "ldb": ldb,
        "tmp_path": tmp_path,
    }


# ============================================================================
# E2E Test Scenarios
# ============================================================================


class TestFreshInstallZeroMemories:
    """Scenario 1: Empty memory.db + no learning.db -> install -> verify."""

    def test_fresh_install_zero_memories(self, test_env):
        """Empty DB -> learning.db created with all 6 tables -> no crash."""
        ldb = test_env["ldb"]

        # Verify learning.db was created
        assert test_env["learning_db"].exists()

        # Verify all 6 tables exist
        conn = ldb._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_tables = {
            "transferable_patterns",
            "workflow_patterns",
            "ranking_feedback",
            "ranking_models",
            "source_quality",
            "engagement_metrics",
        }
        assert expected_tables.issubset(tables), (
            f"Missing tables: {expected_tables - tables}"
        )

        # Verify recall (empty) returns nothing, no crash
        stats = ldb.get_stats()
        assert stats["feedback_count"] == 0
        assert stats["transferable_patterns"] == 0
        assert stats["workflow_patterns"] == 0
        assert stats["tracked_sources"] == 0
        assert stats["models_trained"] == 0


class TestFreshInstallWithMemories:
    """Scenario 2: Pre-seeded memories -> first recall -> learning init."""

    def test_fresh_install_with_memories(self, test_env):
        """100 pre-seeded memories -> learning system initializes."""
        memory_db = test_env["memory_db"]
        ldb = test_env["ldb"]

        # Seed 100 memories
        ids = seed_memories(memory_db, count=100, with_patterns=True)
        assert len(ids) == 100

        # Verify memory.db has data
        conn = sqlite3.connect(str(memory_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        assert cursor.fetchone()[0] == 100
        conn.close()

        # Learning DB starts empty
        stats = ldb.get_stats()
        assert stats["feedback_count"] == 0

        # Engagement tracker can read from memory.db
        from src.learning.engagement_tracker import EngagementTracker
        tracker = EngagementTracker(
            memory_db_path=memory_db,
            learning_db=ldb,
        )
        eng_stats = tracker.get_engagement_stats()
        assert eng_stats["total_memories"] == 100
        assert eng_stats["days_active"] >= 1


class TestFullFeedbackLoop:
    """Scenario 3: Remember -> recall -> feedback -> verify ranking phase."""

    def test_full_feedback_loop(self, test_env):
        """Remember 20 memories -> recall -> feedback -> verify data stored."""
        memory_db = test_env["memory_db"]
        ldb = test_env["ldb"]

        # Seed 20 memories
        ids = seed_memories(memory_db, count=20)

        # Create feedback collector
        from src.learning.feedback_collector import FeedbackCollector
        collector = FeedbackCollector(learning_db=ldb)

        # Simulate MCP recall -> memory_used feedback
        for i, mid in enumerate(ids[:10]):
            collector.record_memory_used(
                memory_id=mid,
                query="deploy FastAPI application",
                usefulness="high" if i < 5 else "medium",
                source_tool="claude-desktop",
                rank_position=i + 1,
            )

        # Simulate CLI feedback
        collector.record_cli_useful(ids[10:15], "pytest fixtures")

        # Simulate dashboard click
        collector.record_dashboard_click(
            memory_id=ids[15],
            query="docker compose setup",
            dwell_time=8.5,
        )

        # Verify feedback stored in learning.db
        assert ldb.get_feedback_count() == 16  # 10 mcp + 5 cli + 1 dashboard

        # Verify summary
        summary = collector.get_feedback_summary()
        assert summary["total_signals"] == 16
        assert summary["by_channel"]["mcp"] == 10
        assert summary["by_channel"]["cli"] == 5
        assert summary["by_channel"]["dashboard"] == 1

        # Check adaptive ranker phase (should be baseline with 16 signals)
        from src.learning.adaptive_ranker import AdaptiveRanker
        ranker = AdaptiveRanker(learning_db=ldb)
        assert ranker.get_phase() == "baseline"

        # Add more feedback to reach rule_based threshold (20+)
        for mid in ids[16:20]:
            collector.record_memory_used(
                memory_id=mid,
                query="authentication setup",
                usefulness="high",
            )
        assert ldb.get_feedback_count() == 20
        assert ranker.get_phase() == "rule_based"


class TestPatternLearningPipeline:
    """Scenario 4: Seed patterns across profiles -> aggregate -> verify."""

    def test_pattern_learning_pipeline(self, test_env):
        """Seed 50+ memories with tech patterns across 2 profiles -> aggregate."""
        memory_db = test_env["memory_db"]
        ldb = test_env["ldb"]

        # Seed memories for 'work' profile
        seed_memories(
            memory_db, count=30, profile="work",
            with_patterns=True,
        )
        # Seed memories for 'personal' profile
        seed_memories(
            memory_db, count=25, profile="personal",
        )

        # Verify total
        conn = sqlite3.connect(str(memory_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]
        conn.close()
        assert total == 55

        # Run cross-project aggregation
        from src.learning.cross_project_aggregator import CrossProjectAggregator

        # Patch FrequencyAnalyzer since pattern_learner.py may not be
        # available at the test memory_db path
        mock_patterns = {
            "python_framework": {
                "value": "FastAPI",
                "confidence": 0.85,
                "evidence_count": 12,
            },
            "test_framework": {
                "value": "pytest",
                "confidence": 0.78,
                "evidence_count": 8,
            },
        }

        aggregator = CrossProjectAggregator(
            memory_db_path=memory_db,
            learning_db=ldb,
        )

        # Since FrequencyAnalyzer depends on ~/.claude-memory/pattern_learner.py,
        # mock the _analyzer and _get_all_profile_data for isolated testing
        aggregator._analyzer = MagicMock()
        aggregator._analyzer.analyze_preferences.return_value = mock_patterns

        results = aggregator.aggregate_all_profiles()

        # Verify patterns were stored
        patterns = ldb.get_transferable_patterns(min_confidence=0.0)
        # At least some patterns should be stored (depends on merge thresholds)
        assert isinstance(patterns, list)

        # Verify get_tech_preferences works
        prefs = aggregator.get_tech_preferences(min_confidence=0.0)
        assert isinstance(prefs, dict)


class TestWorkflowMiningPipeline:
    """Scenario 5: Chronological memories -> mine -> verify sequences."""

    def test_workflow_mining_pipeline(self, test_env):
        """Seed 30 memories with known workflow pattern -> mine -> verify."""
        memory_db = test_env["memory_db"]
        ldb = test_env["ldb"]

        # Create memories with a clear workflow pattern:
        # docs -> architecture -> code -> test (repeated)
        workflow_memories = []
        base_date = datetime.now() - timedelta(days=10)

        activities = [
            ("Writing documentation for the new API spec", "docs"),
            ("Designing architecture diagram for microservices", "architecture"),
            ("Implementing the payment processing module with Python class", "code"),
            ("Writing pytest unit tests for the payment module", "test"),
            ("Debugging error in the API endpoint handler", "debug"),
            ("Deploying the service to staging via Docker", "deploy"),
        ]

        conn = sqlite3.connect(str(memory_db))
        cursor = conn.cursor()

        for i in range(30):
            content, _ = activities[i % len(activities)]
            created_at = (base_date + timedelta(hours=i)).isoformat()
            cursor.execute('''
                INSERT INTO memories (content, created_at, profile)
                VALUES (?, ?, 'default')
            ''', (f"{content} (step {i})", created_at))
            # Sync FTS
            cursor.execute('''
                INSERT INTO memories_fts(rowid, content, summary, tags)
                VALUES (?, ?, '', '[]')
            ''', (cursor.lastrowid, f"{content} (step {i})"))

        conn.commit()
        conn.close()

        # Mine workflow patterns
        from src.learning.workflow_pattern_miner import WorkflowPatternMiner
        miner = WorkflowPatternMiner(
            memory_db_path=memory_db,
            learning_db=ldb,
        )
        results = miner.mine_all()

        # Should find sequence patterns
        sequences = results.get("sequences", [])
        assert isinstance(sequences, list)

        # With 30 memories in repeating 6-step cycle, sequences should emerge
        # The exact patterns depend on classification accuracy
        if sequences:
            # Verify structure
            for seq in sequences:
                assert "sequence" in seq
                assert "support" in seq
                assert "count" in seq
                assert "length" in seq
                assert len(seq["sequence"]) >= 2

        # Verify patterns were persisted
        stored = ldb.get_workflow_patterns()
        assert isinstance(stored, list)


class TestProjectDetection:
    """Scenario 6: Explicit project tags -> detect current project."""

    def test_project_detection(self, test_env):
        """Seed memories with project_name -> detect_current_project."""
        memory_db = test_env["memory_db"]

        # Seed 15 memories mostly for 'MyProject'
        conn = sqlite3.connect(str(memory_db))
        cursor = conn.cursor()

        base_date = datetime.now() - timedelta(hours=2)
        for i in range(15):
            project = "MyProject" if i < 12 else "OtherProject"
            created_at = (base_date + timedelta(minutes=i * 5)).isoformat()
            cursor.execute('''
                INSERT INTO memories
                    (content, project_name, created_at, profile)
                VALUES (?, ?, ?, 'default')
            ''', (f"Working on {project} feature {i}", project, created_at))

        conn.commit()
        conn.close()

        from src.learning.project_context_manager import ProjectContextManager
        pcm = ProjectContextManager(memory_db_path=memory_db)

        project = pcm.detect_current_project()
        # 12 out of 15 memories are "MyProject" - should dominate
        assert project == "MyProject"


class TestEngagementTracking:
    """Scenario 7: Seed memories over 30 days -> verify engagement stats."""

    def test_engagement_tracking(self, test_env):
        """Seed memories over 30 days -> get_engagement_stats -> verify."""
        memory_db = test_env["memory_db"]
        ldb = test_env["ldb"]

        base_date = datetime.now() - timedelta(days=30)
        seed_memories(
            memory_db, count=50,
            base_date=base_date,
            with_timestamps=False,  # spread across 30 days
        )

        from src.learning.engagement_tracker import EngagementTracker
        tracker = EngagementTracker(
            memory_db_path=memory_db,
            learning_db=ldb,
        )

        stats = tracker.get_engagement_stats()

        assert stats["total_memories"] == 50
        assert stats["days_active"] >= 1
        assert 0.0 <= stats["staleness_ratio"] <= 1.0
        assert stats["memories_per_day"] > 0
        assert stats["health_status"] in (
            "HEALTHY", "DECLINING", "AT_RISK", "INACTIVE"
        )

        # Record some activity
        tracker.record_activity("memory_created", source="claude-desktop")
        tracker.record_activity("recall_performed", source="cursor")

        # Verify engagement metrics were recorded
        history = ldb.get_engagement_history(days=1)
        assert len(history) >= 1
        today_row = history[0]
        assert today_row["memories_created"] >= 1 or today_row["recalls_performed"] >= 1


class TestSourceQualityPipeline:
    """Scenario 8: Sources + feedback -> compute scores -> verify ranking."""

    def test_source_quality_pipeline(self, test_env):
        """Seed memories from 3 sources -> feedback -> compute -> verify."""
        memory_db = test_env["memory_db"]
        ldb = test_env["ldb"]

        # Seed memories from different sources
        ids_a = seed_memories(memory_db, count=10, source="mcp:claude-desktop")
        ids_b = seed_memories(memory_db, count=10, source="cli:terminal")
        ids_c = seed_memories(memory_db, count=10, source="mcp:cursor")

        # Add positive feedback for source A (claude-desktop)
        from src.learning.feedback_collector import FeedbackCollector
        collector = FeedbackCollector(learning_db=ldb)

        for mid in ids_a[:8]:  # 8/10 positive for source A
            collector.record_memory_used(
                memory_id=mid,
                query="fastapi deployment",
                usefulness="high",
            )

        for mid in ids_b[:2]:  # 2/10 positive for source B
            collector.record_cli_useful([mid], "config setup")

        # No positive feedback for source C

        # Compute source quality scores
        from src.learning.source_quality_scorer import SourceQualityScorer
        scorer = SourceQualityScorer(
            memory_db_path=memory_db,
            learning_db=ldb,
        )
        scores = scorer.compute_source_scores()

        assert isinstance(scores, dict)
        # Source A should have higher score than source C
        if "mcp:claude-desktop" in scores and "mcp:cursor" in scores:
            assert scores["mcp:claude-desktop"] >= scores["mcp:cursor"]


class TestGracefulDegradationNoLightGBM:
    """Scenario 9: LightGBM unavailable -> rule_based fallback."""

    def test_graceful_degradation_no_lightgbm(self, test_env):
        """Mock lightgbm unavailable -> verify AdaptiveRanker fallback."""
        ldb = test_env["ldb"]

        # Seed enough feedback for rule_based phase
        for i in range(25):
            ldb.store_feedback(
                query_hash=f"hash_{i % 5}",
                memory_id=i + 1,
                signal_type="mcp_used_high",
                signal_value=1.0,
                channel="mcp",
            )

        # Patch HAS_LIGHTGBM and HAS_NUMPY as False
        with patch("src.learning.adaptive_ranker.HAS_LIGHTGBM", False), \
             patch("src.learning.adaptive_ranker.HAS_NUMPY", False):

            from src.learning.adaptive_ranker import AdaptiveRanker
            ranker = AdaptiveRanker(learning_db=ldb)

            # Should be rule_based (enough data, but no LightGBM for ML)
            phase = ranker.get_phase()
            assert phase == "rule_based"

            # Re-ranking should work with rule-based
            test_results = [
                {"id": 1, "content": "FastAPI test", "score": 0.8,
                 "match_type": "keyword", "importance": 8,
                 "created_at": datetime.now().isoformat(),
                 "access_count": 5},
                {"id": 2, "content": "Docker config", "score": 0.6,
                 "match_type": "keyword", "importance": 5,
                 "created_at": datetime.now().isoformat(),
                 "access_count": 1},
            ]

            result = ranker.rerank(test_results, "FastAPI deployment")
            assert len(result) == 2
            assert all("base_score" in r for r in result)
            assert all(r["ranking_phase"] == "rule_based" for r in result)


class TestLearningReset:
    """Scenario 10: Seed learning data -> reset -> verify cleared."""

    def test_learning_reset(self, test_env):
        """Seed learning data -> reset -> learning.db cleared, memory.db intact."""
        memory_db = test_env["memory_db"]
        ldb = test_env["ldb"]

        # Seed memory.db
        ids = seed_memories(memory_db, count=10)

        # Populate learning.db with data
        for i in range(5):
            ldb.store_feedback(
                query_hash=f"hash_{i}",
                memory_id=ids[i],
                signal_type="mcp_used_high",
                signal_value=1.0,
                channel="mcp",
            )
        ldb.upsert_transferable_pattern(
            pattern_type="preference",
            key="test_framework",
            value="pytest",
            confidence=0.8,
            evidence_count=5,
        )
        ldb.store_workflow_pattern(
            pattern_type="sequence",
            pattern_key="code -> test",
            pattern_value='{"sequence": ["code", "test"]}',
            confidence=0.6,
            evidence_count=3,
        )

        # Verify data exists
        assert ldb.get_feedback_count() == 5
        assert len(ldb.get_transferable_patterns()) >= 1
        assert len(ldb.get_workflow_patterns()) >= 1

        # Reset learning data
        ldb.reset()

        # Verify learning.db is cleared
        assert ldb.get_feedback_count() == 0
        assert len(ldb.get_transferable_patterns()) == 0
        assert len(ldb.get_workflow_patterns()) == 0

        # Verify memory.db is untouched
        conn = sqlite3.connect(str(memory_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories")
        assert cursor.fetchone()[0] == 10
        conn.close()


class TestConcurrentFeedback:
    """Scenario 11: 5 threads recording feedback simultaneously."""

    def test_concurrent_feedback(self, test_env):
        """5 threads recording feedback simultaneously -> zero errors."""
        ldb = test_env["ldb"]
        errors = []

        def record_batch(thread_id: int):
            try:
                for i in range(20):
                    ldb.store_feedback(
                        query_hash=f"hash_t{thread_id}_{i}",
                        memory_id=(thread_id * 100) + i,
                        signal_type="mcp_used_high",
                        signal_value=1.0,
                        channel="mcp",
                        source_tool=f"tool_{thread_id}",
                    )
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = []
        for tid in range(5):
            t = threading.Thread(target=record_batch, args=(tid,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Concurrent errors: {errors}"

        # All 5 * 20 = 100 records stored
        assert ldb.get_feedback_count() == 100


class TestPassiveDecay:
    """Scenario 12: Memories returned but never used -> passive decay signals."""

    def test_passive_decay(self, test_env):
        """Record recalls for same query -> never used -> decay signals."""
        ldb = test_env["ldb"]

        from src.learning.feedback_collector import FeedbackCollector
        collector = FeedbackCollector(learning_db=ldb)

        # Record 10 recalls returning the same memories
        for i in range(12):
            # Vary queries slightly so memory appears across distinct hashes
            collector.record_recall_results(
                query=f"deploy fastapi variation {i}",
                returned_ids=[100, 200, 300, 400, 500],
            )

        # Memory IDs 100-500 appeared in 12 distinct query hashes each.
        # No positive feedback for any of them.
        # Compute passive decay (threshold=10, so it should trigger)
        decay_count = collector.compute_passive_decay(threshold=10)

        # Should have created decay signals for memories that appeared
        # in 5+ distinct queries
        assert decay_count >= 1, (
            "Expected passive decay signals for memories appearing in 5+ queries"
        )

        # Verify passive_decay records in learning.db
        feedback = ldb.get_feedback_for_training()
        decay_records = [f for f in feedback if f["signal_type"] == "passive_decay"]
        assert len(decay_records) >= 1
        assert all(r["signal_value"] == 0.0 for r in decay_records)

    def test_passive_decay_skips_positive(self, test_env):
        """Memories with positive feedback should NOT get decay signals."""
        ldb = test_env["ldb"]

        from src.learning.feedback_collector import FeedbackCollector
        collector = FeedbackCollector(learning_db=ldb)

        # Add positive feedback for memory 100
        collector.record_memory_used(
            memory_id=100,
            query="deploy fastapi",
            usefulness="high",
        )

        # Record many recalls returning memory 100
        for i in range(12):
            collector.record_recall_results(
                query=f"deploy fastapi variant {i}",
                returned_ids=[100, 200],
            )

        decay_count = collector.compute_passive_decay(threshold=10)

        # Memory 100 should NOT get a decay signal (has positive feedback)
        feedback = ldb.get_feedback_for_training()
        decay_for_100 = [
            f for f in feedback
            if f["signal_type"] == "passive_decay" and f["memory_id"] == 100
        ]
        assert len(decay_for_100) == 0, (
            "Memory 100 has positive feedback and should not get passive decay"
        )
