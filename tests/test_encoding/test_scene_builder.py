# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for superlocalmemory.encoding.scene_builder.

Covers:
  - SceneBuilder.assign_to_scene() — new scene creation
  - SceneBuilder.assign_to_scene() — assign to existing scene
  - SceneBuilder.get_scene_for_fact()
  - SceneBuilder.get_all_scenes()
  - Persistence via DB
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from superlocalmemory.encoding.scene_builder import SceneBuilder, _cosine
from superlocalmemory.storage import schema as real_schema
from superlocalmemory.storage.database import DatabaseManager
from superlocalmemory.storage.models import AtomicFact, MemoryScene


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path: Path) -> DatabaseManager:
    db_path = tmp_path / "test.db"
    mgr = DatabaseManager(db_path)
    mgr.initialize(real_schema)
    return mgr


def _make_fact(
    fact_id: str = "f1", content: str = "Alice works at Google",
    canonical_entities: list[str] | None = None,
) -> AtomicFact:
    return AtomicFact(
        fact_id=fact_id, content=content,
        canonical_entities=canonical_entities or [],
    )


# ---------------------------------------------------------------------------
# _cosine
# ---------------------------------------------------------------------------

class TestCosine:
    def test_identical(self) -> None:
        assert _cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_zero(self) -> None:
        assert _cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


# ---------------------------------------------------------------------------
# New scene creation
# ---------------------------------------------------------------------------

class TestCreateScene:
    def test_creates_scene_no_embedder(self, db: DatabaseManager) -> None:
        builder = SceneBuilder(db=db, embedder=None)
        fact = _make_fact("f1", "Alice works at Google", ["ent_alice"])
        scene = builder.assign_to_scene(fact, "default")
        assert isinstance(scene, MemoryScene)
        assert "f1" in scene.fact_ids
        assert scene.profile_id == "default"

    def test_creates_scene_no_existing_scenes(self, db: DatabaseManager) -> None:
        embedder = MagicMock()
        embedder.embed.return_value = [1.0, 0.0, 0.0]
        builder = SceneBuilder(db=db, embedder=embedder)
        fact = _make_fact("f1", "Alice works at Google")
        scene = builder.assign_to_scene(fact, "default")
        assert "f1" in scene.fact_ids

    def test_scene_persisted(self, db: DatabaseManager) -> None:
        builder = SceneBuilder(db=db, embedder=None)
        fact = _make_fact("f1", "Alice works at Google")
        scene = builder.assign_to_scene(fact, "default")
        # Verify persisted in DB
        rows = db.execute(
            "SELECT * FROM memory_scenes WHERE scene_id = ?",
            (scene.scene_id,),
        )
        assert len(rows) == 1

    def test_theme_is_content(self, db: DatabaseManager) -> None:
        builder = SceneBuilder(db=db, embedder=None)
        fact = _make_fact("f1", "Alice works at Google as an engineer")
        scene = builder.assign_to_scene(fact, "default")
        assert "Alice works at Google" in scene.theme


# ---------------------------------------------------------------------------
# Assign to existing scene
# ---------------------------------------------------------------------------

class TestAssignToExistingScene:
    def test_assigns_to_similar_scene(self, db: DatabaseManager) -> None:
        embedder = MagicMock()
        # Both facts produce similar embeddings
        embedder.embed.return_value = [1.0, 0.0, 0.0]

        builder = SceneBuilder(db=db, embedder=embedder)
        fact1 = _make_fact("f1", "Alice works at Google")
        scene1 = builder.assign_to_scene(fact1, "default")

        fact2 = _make_fact("f2", "Alice loves Google")
        scene2 = builder.assign_to_scene(fact2, "default")

        # Since embeddings are identical (sim=1.0 > 0.6), should merge
        assert scene2.scene_id == scene1.scene_id
        assert "f1" in scene2.fact_ids
        assert "f2" in scene2.fact_ids

    def test_creates_new_for_dissimilar(self, db: DatabaseManager) -> None:
        call_count = [0]
        def embed(text: str) -> list[float]:
            call_count[0] += 1
            if call_count[0] <= 2:  # First scene creation + comparison
                return [1.0, 0.0, 0.0]
            return [0.0, 0.0, 1.0]  # Very different

        embedder = MagicMock()
        embedder.embed = embed

        builder = SceneBuilder(db=db, embedder=embedder)
        fact1 = _make_fact("f1", "Alice works at Google")
        scene1 = builder.assign_to_scene(fact1, "default")

        fact2 = _make_fact("f2", "Cats are mammals")
        scene2 = builder.assign_to_scene(fact2, "default")

        assert scene2.scene_id != scene1.scene_id


# ---------------------------------------------------------------------------
# get_scene_for_fact
# ---------------------------------------------------------------------------

class TestGetSceneForFact:
    def test_finds_scene(self, db: DatabaseManager) -> None:
        builder = SceneBuilder(db=db, embedder=None)
        fact = _make_fact("f1", "Alice works at Google")
        scene = builder.assign_to_scene(fact, "default")
        found = builder.get_scene_for_fact("f1", "default")
        assert found is not None
        assert found.scene_id == scene.scene_id

    def test_returns_none_for_missing(self, db: DatabaseManager) -> None:
        builder = SceneBuilder(db=db, embedder=None)
        found = builder.get_scene_for_fact("nonexistent", "default")
        assert found is None


# ---------------------------------------------------------------------------
# get_all_scenes
# ---------------------------------------------------------------------------

class TestGetAllScenes:
    def test_returns_all(self, db: DatabaseManager) -> None:
        builder = SceneBuilder(db=db, embedder=None)
        builder.assign_to_scene(_make_fact("f1", "Alice at Google"), "default")
        builder.assign_to_scene(_make_fact("f2", "Bob at Apple"), "default")
        scenes = builder.get_all_scenes("default")
        assert len(scenes) == 2

    def test_empty_profile(self, db: DatabaseManager) -> None:
        builder = SceneBuilder(db=db, embedder=None)
        scenes = builder.get_all_scenes("default")
        assert scenes == []

    def test_profile_isolation(self, db: DatabaseManager) -> None:
        db.execute(
            "INSERT OR IGNORE INTO profiles (profile_id, name) VALUES ('work', 'Work')"
        )
        builder = SceneBuilder(db=db, embedder=None)
        builder.assign_to_scene(_make_fact("f1", "Default fact"), "default")
        builder.assign_to_scene(_make_fact("f2", "Work fact"), "work")
        default_scenes = builder.get_all_scenes("default")
        work_scenes = builder.get_all_scenes("work")
        assert len(default_scenes) == 1
        assert len(work_scenes) == 1
