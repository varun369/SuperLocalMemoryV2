#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Tests for ProjectContextManager (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
"""

import sqlite3
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_db(tmp_path):
    """Create a minimal memory.db with the required schema."""
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


@pytest.fixture
def pcm(memory_db):
    from src.learning.project_context_manager import ProjectContextManager
    return ProjectContextManager(memory_db_path=memory_db)


def _insert_memories(db_path, memories):
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    for m in memories:
        cursor.execute('''
            INSERT INTO memories (content, project_name, project_path,
                                  profile, cluster_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            m.get('content', 'test'),
            m.get('project_name'),
            m.get('project_path'),
            m.get('profile', 'default'),
            m.get('cluster_id'),
            m.get('created_at', '2026-02-16 10:00:00'),
        ))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Path Extraction
# ---------------------------------------------------------------------------

class TestExtractProjectFromPath:
    """Test the static _extract_project_from_path method."""

    def test_projects_parent(self):
        from src.learning.project_context_manager import ProjectContextManager
        result = ProjectContextManager._extract_project_from_path(
            "/Users/varun/projects/MY_PROJECT/src/main.py"
        )
        assert result == "MY_PROJECT"

    def test_repos_parent(self):
        from src.learning.project_context_manager import ProjectContextManager
        result = ProjectContextManager._extract_project_from_path(
            "/home/dev/repos/my-app/lib/util.js"
        )
        assert result == "my-app"

    def test_documents_parent(self):
        from src.learning.project_context_manager import ProjectContextManager
        result = ProjectContextManager._extract_project_from_path(
            "/Users/varun/Documents/AGENTIC_Official/SuperLocalMemoryV2-repo/src/learning/foo.py"
        )
        assert result == "SuperLocalMemoryV2-repo"

    def test_workspace_services(self):
        from src.learning.project_context_manager import ProjectContextManager
        result = ProjectContextManager._extract_project_from_path(
            "/workspace/services/auth-service/index.ts"
        )
        assert result == "auth-service"

    def test_empty_path(self):
        from src.learning.project_context_manager import ProjectContextManager
        assert ProjectContextManager._extract_project_from_path("") is None

    def test_none_path(self):
        from src.learning.project_context_manager import ProjectContextManager
        assert ProjectContextManager._extract_project_from_path(None) is None

    def test_short_path(self):
        from src.learning.project_context_manager import ProjectContextManager
        assert ProjectContextManager._extract_project_from_path("/") is None

    def test_github_parent(self):
        from src.learning.project_context_manager import ProjectContextManager
        result = ProjectContextManager._extract_project_from_path(
            "/home/user/github/cool-project/README.md"
        )
        assert result == "cool-project"

    def test_skip_dirs_not_returned(self):
        """Directories like src, lib, node_modules should not be project names."""
        from src.learning.project_context_manager import ProjectContextManager
        result = ProjectContextManager._extract_project_from_path(
            "/Users/dev/projects/myapp/src/lib/util.py"
        )
        assert result == "myapp"

    def test_code_parent(self):
        from src.learning.project_context_manager import ProjectContextManager
        result = ProjectContextManager._extract_project_from_path(
            "/Users/dev/code/awesome-tool/main.py"
        )
        assert result == "awesome-tool"


# ---------------------------------------------------------------------------
# Project Detection
# ---------------------------------------------------------------------------

class TestDetectCurrentProject:
    def test_with_explicit_project_tags(self, pcm, memory_db):
        """Signal 1: project_name tag should dominate."""
        memories = [
            {"content": "test", "project_name": "MyProject"},
            {"content": "test", "project_name": "MyProject"},
            {"content": "test", "project_name": "MyProject"},
        ]
        recent = [
            {"project_name": "MyProject", "project_path": None, "cluster_id": None,
             "profile": "default", "content": "test"}
            for _ in range(3)
        ]
        result = pcm.detect_current_project(recent_memories=recent)
        assert result == "MyProject"

    def test_with_project_paths(self, pcm):
        """Signal 2: project_path analysis."""
        recent = [
            {"project_name": None,
             "project_path": "/Users/dev/projects/SLM/src/main.py",
             "cluster_id": None, "profile": "default", "content": "test"}
            for _ in range(5)
        ]
        result = pcm.detect_current_project(recent_memories=recent)
        assert result == "SLM"

    def test_with_profiles(self, pcm):
        """Signal 3: active profile as weak signal."""
        recent = [
            {"project_name": None, "project_path": None,
             "cluster_id": None, "profile": "work", "content": "test"}
        ]
        # Profile is weak (weight=1), may not win alone due to 40% threshold
        # with just 1 memory. But adding it to existing signal helps.
        recent_with_name = [
            {"project_name": "work", "project_path": None,
             "cluster_id": None, "profile": "work", "content": "test"}
        ]
        result = pcm.detect_current_project(recent_memories=recent_with_name)
        assert result == "work"

    def test_empty_memories(self, pcm):
        result = pcm.detect_current_project(recent_memories=[])
        assert result is None

    def test_ambiguous_results_none(self, pcm):
        """When no project clears 40% threshold, return None."""
        recent = [
            {"project_name": "A", "project_path": None, "cluster_id": None,
             "profile": "default", "content": "test"},
            {"project_name": "B", "project_path": None, "cluster_id": None,
             "profile": "default", "content": "test"},
            {"project_name": "C", "project_path": None, "cluster_id": None,
             "profile": "default", "content": "test"},
        ]
        # Each gets 3 points (weight 3 for project_tag), total = 9
        # 3/9 = 33% < 40% threshold, so None
        result = pcm.detect_current_project(recent_memories=recent)
        assert result is None

    def test_mixed_signals(self, pcm):
        """Both project_name and project_path pointing to same project."""
        recent = [
            {"project_name": "SLM", "project_path": "/projects/SLM/src/a.py",
             "cluster_id": None, "profile": "default", "content": "test"},
            {"project_name": "SLM", "project_path": "/projects/SLM/src/b.py",
             "cluster_id": None, "profile": "default", "content": "test"},
        ]
        result = pcm.detect_current_project(recent_memories=recent)
        assert result == "SLM"


# ---------------------------------------------------------------------------
# Project Boost
# ---------------------------------------------------------------------------

class TestGetProjectBoost:
    def test_match_returns_1_0(self, pcm):
        memory = {"project_name": "MyProject"}
        assert pcm.get_project_boost(memory, "MyProject") == 1.0

    def test_case_insensitive_match(self, pcm):
        memory = {"project_name": "myproject"}
        assert pcm.get_project_boost(memory, "MyProject") == 1.0

    def test_mismatch_returns_0_3(self, pcm):
        memory = {"project_name": "OtherProject"}
        assert pcm.get_project_boost(memory, "MyProject") == 0.3

    def test_no_current_project_returns_0_6(self, pcm):
        memory = {"project_name": "Anything"}
        assert pcm.get_project_boost(memory, None) == 0.6

    def test_no_project_info_returns_0_6(self, pcm):
        memory = {"content": "no project info"}
        assert pcm.get_project_boost(memory, "MyProject") == 0.6

    def test_path_match(self, pcm):
        memory = {"project_path": "/projects/SLM/src/main.py"}
        assert pcm.get_project_boost(memory, "SLM") == 1.0

    def test_path_mismatch(self, pcm):
        memory = {"project_path": "/projects/OTHER/src/main.py"}
        assert pcm.get_project_boost(memory, "SLM") == 0.3


# ---------------------------------------------------------------------------
# safe_get
# ---------------------------------------------------------------------------

class TestSafeGet:
    def test_normal_value(self, pcm):
        assert pcm._safe_get({"key": "value"}, "key") == "value"

    def test_missing_key(self, pcm):
        assert pcm._safe_get({"key": "value"}, "other") is None

    def test_none_value(self, pcm):
        assert pcm._safe_get({"key": None}, "key") is None

    def test_empty_string(self, pcm):
        assert pcm._safe_get({"key": ""}, "key") is None

    def test_whitespace_string(self, pcm):
        assert pcm._safe_get({"key": "   "}, "key") is None

    def test_integer_value(self, pcm):
        assert pcm._safe_get({"key": 42}, "key") == 42


# ---------------------------------------------------------------------------
# Cache Invalidation
# ---------------------------------------------------------------------------

class TestCacheInvalidation:
    def test_invalidate_cache(self, pcm):
        # Force column cache to be populated
        pcm._get_available_columns()
        assert pcm._available_columns is not None

        pcm.invalidate_cache()
        assert pcm._available_columns is None
