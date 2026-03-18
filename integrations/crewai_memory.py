"""
SuperLocalMemory V3 — CrewAI Integration
=========================================
Provides an ExternalMemory-compatible storage class for CrewAI,
enabling crews to use SuperLocalMemory V3 as their memory backend.

Install:
    npm install -g superlocalmemory   # install SLM
    pip install crewai                # crewai dependency

Usage:
    from superlocalmemory.integrations.crewai_memory import SuperLocalMemoryStorage
    from crewai.memory.external.external_memory import ExternalMemory
    from crewai import Crew, Process

    # Option A: Use as ExternalMemory storage backend
    external_memory = ExternalMemory(
        embedder_config={
            "provider": "superlocalmemory",
            "config": {"agent_id": "my-crew"},
        }
    )
    crew = Crew(
        agents=[...],
        tasks=[...],
        external_memory=external_memory,
    )

    # Option B: Use SuperLocalMemoryStorage directly
    from superlocalmemory.integrations.crewai_memory import SuperLocalMemoryStorage
    storage = SuperLocalMemoryStorage(agent_id="research-crew")
    storage.save("Agent found: authentication uses JWT tokens with 24h expiry")
    results = storage.search("authentication token expiry")

Part of Qualixar | Author: Varun Pratap Bhardwaj (qualixar.com)
Paper: https://arxiv.org/abs/2603.14588
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


def _slm(args: list[str], capture: bool = True) -> dict[str, Any]:
    """Run slm CLI and return parsed JSON."""
    cmd = ["slm"] + args
    if capture:
        cmd += ["--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0 or not capture:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


class SuperLocalMemoryStorage:
    """
    Drop-in memory storage for CrewAI using SuperLocalMemory V3.

    SuperLocalMemory V3 provides:
    - 74.8% on LoCoMo benchmark with zero cloud dependency
    - Fisher-Rao geometric retrieval (confidence-weighted)
    - Sheaf cohomology consistency checks
    - EU AI Act compliant (Mode A — data stays on device)

    This class matches the interface expected by CrewAI's memory system,
    allowing it to be used as a storage backend for any crew.

    Args:
        agent_id: Identifier for this crew/agent. Used to tag memories
            for isolation between different crews.
        limit: Default number of results to return per search.
    """

    def __init__(
        self,
        agent_id: str = "crewai",
        limit: int = 10,
    ) -> None:
        self.agent_id = agent_id
        self.limit = limit

    def save(self, value: str, metadata: dict[str, Any] | None = None) -> None:
        """
        Save a memory to SuperLocalMemory.

        Called automatically by CrewAI when a task completes.

        Args:
            value: The memory content to store.
            metadata: Optional metadata (currently logged but not stored separately).
        """
        content = f"[crew:{self.agent_id}] {value}"
        subprocess.run(
            ["slm", "remember", content],
            capture_output=True,
            timeout=15,
        )

    def search(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Search memories relevant to the query.

        Called automatically by CrewAI when an agent starts a task.

        Args:
            query: Natural language search query.
            limit: Max results (overrides instance default if provided).

        Returns:
            List of dicts with 'id', 'memory', and 'score' keys
            (matching CrewAI's expected search result format).
        """
        n = limit or self.limit
        result = _slm(["recall", query, "--limit", str(n)])
        return [
            {
                "id": fact.get("fact_id", ""),
                "memory": fact.get("content", ""),
                "score": fact.get("score", 0.0),
            }
            for fact in result.get("results", [])
        ]

    def reset(self) -> None:
        """
        Clear all memories for this crew/agent.

        Warning: This permanently deletes all memories tagged with
        this agent_id.
        """
        result = _slm(["recall", f"crew:{self.agent_id}", "--limit", "500"])
        for fact in result.get("results", []):
            fact_id = fact.get("fact_id")
            if fact_id:
                subprocess.run(
                    ["slm", "delete", fact_id, "--yes"],
                    capture_output=True,
                    timeout=10,
                )


def make_crewai_external_memory(
    agent_id: str = "crewai",
    limit: int = 10,
) -> "ExternalMemory":
    """
    Factory function to create a CrewAI ExternalMemory backed by SLM.

    This is the simplest way to integrate SuperLocalMemory into a crew.

    Example:
        from superlocalmemory.integrations.crewai_memory import make_crewai_external_memory
        from crewai import Crew, Process

        crew = Crew(
            agents=[researcher, writer],
            tasks=[research_task, write_task],
            external_memory=make_crewai_external_memory(agent_id="my-crew"),
            process=Process.sequential,
        )
    """
    try:
        from crewai.memory.external.external_memory import ExternalMemory
    except ImportError as e:
        raise ImportError(
            "crewai is required for this integration. "
            "Install it with: pip install crewai"
        ) from e

    storage = SuperLocalMemoryStorage(agent_id=agent_id, limit=limit)

    # CrewAI's ExternalMemory accepts a storage object directly
    # when not using the embedder_config provider pattern
    return ExternalMemory(storage=storage)
