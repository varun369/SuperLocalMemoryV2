# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""CodeGraphService — the main orchestrator.

Lazy initialization. DB created on first access.
Other phases flesh out the methods.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from superlocalmemory.code_graph.config import CodeGraphConfig
from superlocalmemory.code_graph.database import CodeGraphDatabase

logger = logging.getLogger(__name__)


class CodeGraphNotEnabledError(Exception):
    """Raised when code graph operations are attempted but config.enabled=False."""


class CodeGraphService:
    """Main entry point for the CodeGraph module.

    Provides lazy DB initialization and delegates to sub-modules
    (parser, graph_engine, search, bridge) as they are implemented.
    """

    def __init__(
        self,
        config: CodeGraphConfig,
        slm_base_dir: Path | None = None,
    ) -> None:
        self._config = config
        self._slm_base_dir = slm_base_dir
        self._db: CodeGraphDatabase | None = None

    @property
    def config(self) -> CodeGraphConfig:
        return self._config

    @property
    def db(self) -> CodeGraphDatabase:
        """Lazy DB access. Creates code_graph.db on first call."""
        if self._db is None:
            db_path = self._config.get_db_path(self._slm_base_dir)
            self._db = CodeGraphDatabase(db_path)
            logger.info("CodeGraph DB initialized at %s", db_path)
        return self._db

    def ensure_enabled(self) -> None:
        """Guard: raise if code graph is not enabled."""
        if not self._config.enabled:
            raise CodeGraphNotEnabledError(
                "Code graph not enabled. Set code_graph.enabled = true in config."
            )

    def get_stats(self) -> dict[str, Any]:
        """Graph statistics. Works even if graph not built (returns zeros)."""
        if self._db is None:
            db_path = self._config.get_db_path(self._slm_base_dir)
            if not db_path.exists():
                return {"nodes": 0, "edges": 0, "files": 0, "built": False}
            # DB exists but not loaded yet — load it
            _ = self.db

        stats = self.db.get_stats()
        stats["built"] = stats["nodes"] > 0 or stats["files"] > 0
        stats["db_path"] = str(self.db.db_path)
        stats["repo_root"] = str(self._config.repo_root)
        return stats

    # ------------------------------------------------------------------
    # Placeholder methods for future phases
    # ------------------------------------------------------------------

    # Phase 1: Parser
    # def build(self, repo_path: Path | None = None) -> dict: ...
    # def update(self, changed_files: list[str] | None = None) -> dict: ...

    # Phase 2: Graph Engine
    # def get_blast_radius(self, changed_files: list[str], ...) -> dict: ...
    # def query(self, pattern: str, target: str, ...) -> dict: ...

    # Phase 3: Search & Analysis
    # def search(self, query: str, ...) -> dict: ...
    # def detect_changes(self, ...) -> dict: ...

    # Phase 4: Bridge
    # def resolve_entities(self, fact_text: str, ...) -> list: ...
