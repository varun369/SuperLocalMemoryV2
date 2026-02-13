#!/usr/bin/env python3
"""
SuperLocalMemory V2 - LangChain Chat Message History
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Implements LangChain's BaseChatMessageHistory backed by SuperLocalMemory V2's
local SQLite storage. All data stays on your machine -- zero cloud, zero telemetry.

Usage:
    from langchain_superlocalmemory import SuperLocalMemoryChatMessageHistory

    history = SuperLocalMemoryChatMessageHistory(session_id="my-session")
    history.add_messages([HumanMessage(content="Hello")])
    print(history.messages)
"""

import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    FunctionMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    message_to_dict,
    messages_from_dict,
)

# ---------------------------------------------------------------------------
# MemoryStoreV2 import strategy
# ---------------------------------------------------------------------------
# SuperLocalMemory V2 installs to ~/.claude-memory/. We add that path so
# the MemoryStoreV2 class can be imported. If SLM is not installed, we
# raise a clear error at construction time (not import time) so the package
# itself can still be imported for introspection.
# ---------------------------------------------------------------------------

_SLM_PATH = Path.home() / ".claude-memory"
_MemoryStoreV2 = None


def _ensure_slm_imported():
    """Lazily import MemoryStoreV2, raising a clear error if unavailable."""
    global _MemoryStoreV2
    if _MemoryStoreV2 is not None:
        return _MemoryStoreV2

    slm_path_str = str(_SLM_PATH)
    if slm_path_str not in sys.path:
        sys.path.insert(0, slm_path_str)

    try:
        from memory_store_v2 import MemoryStoreV2  # type: ignore[import-untyped]

        _MemoryStoreV2 = MemoryStoreV2
        return _MemoryStoreV2
    except ImportError as exc:
        raise ImportError(
            "SuperLocalMemory V2 is not installed. "
            "Run the installer from https://github.com/varun369/SuperLocalMemoryV2 "
            "or ensure ~/.claude-memory/memory_store_v2.py exists."
        ) from exc


# ---------------------------------------------------------------------------
# Message (de)serialization helpers
# ---------------------------------------------------------------------------

# Map from LangChain message type string to the concrete class used for
# deserialization. LangChain's own `messages_from_dict` handles this, but we
# keep a lookup for the fallback path in case the dict format diverges.

_MESSAGE_TYPE_MAP = {
    "human": HumanMessage,
    "ai": AIMessage,
    "system": SystemMessage,
    "function": FunctionMessage,
    "tool": ToolMessage,
}


def _serialize_message(message: BaseMessage) -> str:
    """Serialize a LangChain BaseMessage to a JSON string for SLM storage."""
    return json.dumps(message_to_dict(message), ensure_ascii=False)


def _deserialize_messages(dicts: List[dict]) -> List[BaseMessage]:
    """Deserialize a list of message dicts back to BaseMessage instances.

    Uses LangChain's ``messages_from_dict`` which handles all known message
    types including ``additional_kwargs``.
    """
    return messages_from_dict(dicts)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class SuperLocalMemoryChatMessageHistory(BaseChatMessageHistory):
    """LangChain chat message history backed by SuperLocalMemory V2.

    Each message is stored as an individual memory entry in the SLM SQLite
    database, tagged with the session ID for isolation.  This keeps the data
    fully local and queryable via any SLM access method (MCP, CLI, Skills,
    REST API, A2A).

    Parameters
    ----------
    session_id : str
        Unique identifier for the conversation session.  Messages from
        different session IDs are completely isolated.
    db_path : str or None
        Path to the SQLite database file.  Defaults to
        ``~/.claude-memory/memory.db``.
    """

    # Tag prefix used to isolate LangChain session messages inside SLM.
    _TAG_PREFIX = "langchain:session:"

    def __init__(self, session_id: str, db_path: Optional[str] = None) -> None:
        self.session_id = session_id
        self.db_path = db_path

        MemoryStoreV2 = _ensure_slm_imported()
        store_path = Path(db_path) if db_path else None
        self._store = MemoryStoreV2(db_path=store_path)

    # -- property: messages ------------------------------------------------

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore[override]
        """Return all messages for this session, ordered chronologically."""
        session_tag = f"{self._TAG_PREFIX}{self.session_id}"

        # Retrieve a generous batch from SLM.  We filter by tag in Python
        # because list_all does not accept a tag filter parameter.
        all_memories = self._store.list_all(limit=10_000)

        # Filter to memories belonging to this session.
        session_memories = [
            m for m in all_memories if session_tag in (m.get("tags") or [])
        ]

        # list_all returns newest-first (ORDER BY created_at DESC).
        # We need chronological (oldest-first) order for chat history.
        session_memories.sort(key=lambda m: m.get("created_at", ""))

        # Deserialize each memory's content back to a BaseMessage.
        message_dicts: List[dict] = []
        for mem in session_memories:
            try:
                parsed = json.loads(mem["content"])
                message_dicts.append(parsed)
            except (json.JSONDecodeError, KeyError, TypeError):
                # Skip malformed entries silently -- they may be non-LangChain
                # memories that happen to share the tag pattern.
                continue

        if not message_dicts:
            return []

        return _deserialize_messages(message_dicts)

    # -- add_messages ------------------------------------------------------

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        """Persist messages to SuperLocalMemory V2.

        Each message becomes a separate memory entry tagged with the session
        identifier.  Importance is set to 3 (lower than typical user
        memories at 5) so LangChain history does not crowd out higher-value
        entries in search results.
        """
        session_tag = f"{self._TAG_PREFIX}{self.session_id}"

        for message in messages:
            serialized = _serialize_message(message)
            self._store.add_memory(
                content=serialized,
                tags=["langchain", session_tag],
                importance=3,
                project_name="langchain",
            )

    # -- clear -------------------------------------------------------------

    def clear(self) -> None:
        """Remove all messages for this session from the store."""
        session_tag = f"{self._TAG_PREFIX}{self.session_id}"

        all_memories = self._store.list_all(limit=10_000)

        for mem in all_memories:
            if session_tag in (mem.get("tags") or []):
                self._store.delete_memory(mem["id"])
