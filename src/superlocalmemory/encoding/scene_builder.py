# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — Scene Builder (Memory Clustering).

Groups related facts into thematic scenes (EverMemOS MemScene pattern).
Scenes provide contextual retrieval — related facts come together.

V1 had this module but NEVER CALLED it. Now wired into the encoding pipeline.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from superlocalmemory.storage.models import AtomicFact, MemoryScene

logger = logging.getLogger(__name__)

# Similarity threshold for assigning fact to existing scene
_ASSIGN_THRESHOLD = 0.6


class SceneBuilder:
    """Cluster related facts into thematic scenes.

    When a new fact arrives:
    1. Compute similarity to existing scenes (via scene theme embedding)
    2. If above threshold: assign to nearest scene, update scene
    3. If below threshold: create new scene
    """

    def __init__(self, db, embedder=None) -> None:
        self._db = db
        self._embedder = embedder
        self._scene_embeddings_cache: dict[str, list[float]] = {}

    def assign_to_scene(
        self,
        new_fact: AtomicFact,
        profile_id: str,
    ) -> MemoryScene:
        """Assign a fact to an existing scene or create a new one.

        Always embeds the incoming fact content (when embedder is available)
        so that the embedding is ready for comparison against existing scenes.
        """
        if self._embedder is None:
            return self._create_scene(new_fact, profile_id)

        # Always compute fact embedding first — needed for comparisons
        fact_emb = self._embedder.embed(new_fact.content)

        scenes = self._get_scenes(profile_id)
        if not scenes:
            return self._create_scene(new_fact, profile_id)

        # Find best matching scene
        best_scene: MemoryScene | None = None
        best_sim = -1.0

        for scene in scenes:
            # Use cached embedding if available, otherwise compute fresh
            if scene.theme in self._scene_embeddings_cache:
                theme_emb = self._scene_embeddings_cache[scene.theme]
            else:
                theme_emb = self._embedder.embed(scene.theme)
                self._scene_embeddings_cache[scene.theme] = theme_emb
            sim = _cosine(fact_emb, theme_emb)
            if sim > best_sim:
                best_sim = sim
                best_scene = scene

        if best_scene is not None and best_sim >= _ASSIGN_THRESHOLD:
            return self._add_to_scene(best_scene, new_fact, profile_id)

        return self._create_scene(new_fact, profile_id)

    def get_scene_for_fact(self, fact_id: str, profile_id: str) -> MemoryScene | None:
        """Get the scene containing a specific fact."""
        rows = self._db.execute(
            "SELECT * FROM memory_scenes WHERE profile_id = ?", (profile_id,)
        )
        for row in rows:
            d = dict(row)
            fids = json.loads(d.get("fact_ids_json", "[]"))
            if fact_id in fids:
                return self._row_to_scene(d)
        return None

    def get_all_scenes(self, profile_id: str) -> list[MemoryScene]:
        """Get all scenes for a profile."""
        return self._get_scenes(profile_id)

    # -- Internal ----------------------------------------------------------

    def _create_scene(self, fact: AtomicFact, profile_id: str) -> MemoryScene:
        """Create a new scene from a single fact.

        Pre-computes and caches the theme embedding for efficient later
        comparisons in assign_to_scene.
        """
        theme = fact.content[:200]
        # Pre-compute theme embedding for future comparisons
        if self._embedder is not None:
            self._scene_embeddings_cache[theme] = self._embedder.embed(theme)

        scene = MemoryScene(
            profile_id=profile_id,
            theme=theme,
            fact_ids=[fact.fact_id],
            entity_ids=list(fact.canonical_entities),
            created_at=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
        )
        self._save_scene(scene)
        return scene

    def _add_to_scene(
        self, scene: MemoryScene, fact: AtomicFact, profile_id: str
    ) -> MemoryScene:
        """Add a fact to an existing scene."""
        new_fact_ids = [*scene.fact_ids, fact.fact_id]
        new_entity_ids = list(set(scene.entity_ids) | set(fact.canonical_entities))
        updated = MemoryScene(
            scene_id=scene.scene_id,
            profile_id=profile_id,
            theme=scene.theme,
            fact_ids=new_fact_ids,
            entity_ids=new_entity_ids,
            created_at=scene.created_at,
            last_updated=datetime.now(UTC).isoformat(),
        )
        self._save_scene(updated)
        return updated

    def _get_scenes(self, profile_id: str) -> list[MemoryScene]:
        """Load all scenes from DB."""
        rows = self._db.execute(
            "SELECT * FROM memory_scenes WHERE profile_id = ? ORDER BY last_updated DESC",
            (profile_id,),
        )
        return [self._row_to_scene(dict(r)) for r in rows]

    def _save_scene(self, scene: MemoryScene) -> None:
        """Upsert scene to DB."""
        self._db.execute(
            """INSERT OR REPLACE INTO memory_scenes
               (scene_id, profile_id, theme, fact_ids_json, entity_ids_json,
                created_at, last_updated)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                scene.scene_id, scene.profile_id, scene.theme,
                json.dumps(scene.fact_ids), json.dumps(scene.entity_ids),
                scene.created_at, scene.last_updated,
            ),
        )

    @staticmethod
    def _row_to_scene(d: dict) -> MemoryScene:
        return MemoryScene(
            scene_id=d["scene_id"],
            profile_id=d["profile_id"],
            theme=d.get("theme", ""),
            fact_ids=json.loads(d.get("fact_ids_json", "[]")),
            entity_ids=json.loads(d.get("entity_ids_json", "[]")),
            created_at=d.get("created_at", ""),
            last_updated=d.get("last_updated", ""),
        )


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
