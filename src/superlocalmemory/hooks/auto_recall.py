# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Auto-recall — inject relevant memories into AI context automatically."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AutoRecall:
    """Automatically recalls relevant context for AI sessions.

    Called at session start or before each prompt to inject
    relevant memories without user intervention.
    """

    def __init__(self, engine=None, config: dict | None = None):
        self._engine = engine
        self._config = config or {}
        self._enabled = self._config.get("enabled", True)
        self._max_memories = self._config.get("max_memories_injected", 10)
        self._threshold = self._config.get("relevance_threshold", 0.3)

    def get_session_context(self, project_path: str = "", query: str = "") -> str:
        """Get relevant context for a session or query.

        Returns a formatted string of relevant memories suitable
        for injection into an AI's system prompt.
        """
        if not self._enabled or not self._engine:
            return ""

        try:
            # Build query from project path or explicit query
            search_query = query or f"project context {project_path}"
            response = self._engine.recall(search_query, limit=self._max_memories)

            if not response.results:
                return ""

            # Filter by relevance threshold
            relevant = [r for r in response.results if r.score >= self._threshold]

            if not relevant:
                return ""

            # Format for injection
            lines = ["# Relevant Memory Context", ""]
            for r in relevant[:self._max_memories]:
                lines.append(f"- {r.fact.content[:200]}")

            return "\n".join(lines)
        except Exception as exc:
            logger.debug("Auto-recall failed: %s", exc)
            return ""

    def get_query_context(self, query: str) -> list[dict]:
        """Get relevant memories for a specific query.

        Returns structured data (not formatted string) for MCP tools.
        """
        if not self._enabled or not self._engine:
            return []

        try:
            response = self._engine.recall(query, limit=self._max_memories)
            results = []
            for r in response.results:
                if r.score >= self._threshold:
                    results.append({
                        "fact_id": r.fact.fact_id,
                        "content": r.fact.content[:300],
                        "score": round(r.score, 3),
                    })
            return results
        except Exception as exc:
            logger.debug("Auto-recall query failed: %s", exc)
            return []

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False
