"""
SuperLocalMemory V3 — LangChain Integration
============================================
Provides BaseChatMessageHistory and a retriever-style memory
for use with LangChain LCEL (RunnableWithMessageHistory).

Install:
    npm install -g superlocalmemory   # install SLM
    pip install langchain-core        # langchain dependency

Usage:
    from superlocalmemory.integrations.langchain_memory import (
        SuperLocalMemoryChatHistory,
        SuperLocalMemoryRetriever,
    )

    # Conversation history (per-session)
    history = SuperLocalMemoryChatHistory(session_id="my-project")

    # With RunnableWithMessageHistory
    from langchain_core.runnables.history import RunnableWithMessageHistory
    chain_with_memory = RunnableWithMessageHistory(
        chain,
        lambda session_id: SuperLocalMemoryChatHistory(session_id=session_id),
        input_messages_key="input",
        history_messages_key="history",
    )

Part of Qualixar | Author: Varun Pratap Bhardwaj (qualixar.com)
Paper: https://arxiv.org/abs/2603.14588
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    messages_from_dict,
    messages_to_dict,
)


def _run_slm(args: list[str]) -> dict[str, Any]:
    """Run a slm CLI command and return parsed JSON output."""
    result = subprocess.run(
        ["slm"] + args + ["--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


class SuperLocalMemoryChatHistory(BaseChatMessageHistory):
    """
    LangChain chat message history backed by SuperLocalMemory V3.

    Stores each message as a tagged fact so it is searchable and
    persists across sessions. Retrieves conversation history by
    recalling facts tagged with the session_id.

    Args:
        session_id: Unique identifier for this conversation session.
            Used to scope memories so different sessions don't mix.
        agent_id: Identifier logged in the SLM audit trail.
        max_messages: Maximum messages to return from history (default 50).
    """

    def __init__(
        self,
        session_id: str = "default",
        agent_id: str = "langchain",
        max_messages: int = 50,
    ) -> None:
        self.session_id = session_id
        self.agent_id = agent_id
        self.max_messages = max_messages
        self._messages: list[BaseMessage] = []

    @property
    def messages(self) -> list[BaseMessage]:
        """Retrieve conversation messages from SuperLocalMemory."""
        result = _run_slm([
            "recall",
            f"conversation session:{self.session_id}",
            "--limit", str(self.max_messages),
        ])
        facts = result.get("results", [])
        messages: list[BaseMessage] = []
        for fact in facts:
            content = fact.get("content", "")
            if content.startswith("[human] "):
                messages.append(HumanMessage(content=content[8:]))
            elif content.startswith("[ai] "):
                messages.append(AIMessage(content=content[5:]))
            elif content.startswith("[system] "):
                messages.append(SystemMessage(content=content[9:]))
        return messages

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        """Persist new messages to SuperLocalMemory."""
        for msg in messages:
            prefix = {
                "human": "[human]",
                "ai": "[ai]",
                "system": "[system]",
            }.get(msg.type, f"[{msg.type}]")
            content = f"{prefix} {msg.content} [session:{self.session_id}]"
            subprocess.run(
                ["slm", "remember", content],
                capture_output=True,
                timeout=10,
            )

    def clear(self) -> None:
        """Clear all messages for this session from SuperLocalMemory."""
        result = _run_slm([
            "recall",
            f"session:{self.session_id}",
            "--limit", "200",
        ])
        for fact in result.get("results", []):
            fact_id = fact.get("fact_id")
            if fact_id:
                subprocess.run(
                    ["slm", "delete", fact_id, "--yes"],
                    capture_output=True,
                    timeout=10,
                )


class SuperLocalMemoryRetriever:
    """
    Retriever-style interface for querying SuperLocalMemory V3.

    Use this for RAG-style memory augmentation where you want to
    inject relevant past context into a prompt rather than full
    conversation history.

    Args:
        limit: Maximum number of memories to retrieve per query.
        agent_id: Identifier for the calling agent.

    Example:
        retriever = SuperLocalMemoryRetriever(limit=5)
        context = retriever.get_relevant_memories("auth middleware patterns")
        # Returns list of strings to inject into prompt
    """

    def __init__(self, limit: int = 5, agent_id: str = "langchain") -> None:
        self.limit = limit
        self.agent_id = agent_id

    def get_relevant_memories(self, query: str) -> list[str]:
        """Return a list of relevant memory strings for the query."""
        result = _run_slm(["recall", query, "--limit", str(self.limit)])
        return [
            fact.get("content", "")
            for fact in result.get("results", [])
            if fact.get("content")
        ]

    def as_context_string(self, query: str) -> str:
        """Return relevant memories as a formatted context block."""
        memories = self.get_relevant_memories(query)
        if not memories:
            return ""
        lines = ["[Relevant memories from SuperLocalMemory:]"]
        lines.extend(f"- {m}" for m in memories)
        return "\n".join(lines)
