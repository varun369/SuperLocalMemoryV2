#!/usr/bin/env python3
"""
SuperLocalMemory V2 - LlamaIndex Chat Store Backend
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Implements LlamaIndex's BaseChatStore backed by SuperLocalMemory V2's
local SQLite storage. All data stays on-device — zero cloud, zero telemetry.

Usage:
    from llama_index.storage.chat_store.superlocalmemory import SuperLocalMemoryChatStore
    from llama_index.core.memory import ChatMemoryBuffer

    chat_store = SuperLocalMemoryChatStore()
    memory = ChatMemoryBuffer.from_defaults(chat_store=chat_store, chat_store_key="user-123")
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.storage.chat_store.base import BaseChatStore

# ---------------------------------------------------------------------------
# Locate and import SuperLocalMemory V2's MemoryStoreV2
# ---------------------------------------------------------------------------
_SLM_PATH = Path.home() / ".claude-memory"
if str(_SLM_PATH) not in sys.path:
    sys.path.insert(0, str(_SLM_PATH))

# Also support the source tree layout (for development / tests that pass db_path)
_SLM_SRC_PATH = Path(__file__).resolve().parents[6] / "src"
if _SLM_SRC_PATH.exists() and str(_SLM_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SLM_SRC_PATH))

try:
    from memory_store_v2 import MemoryStoreV2
except ImportError as exc:
    raise ImportError(
        "SuperLocalMemory V2 is not installed. "
        "Run: curl -fsSL https://raw.githubusercontent.com/varun369/SuperLocalMemoryV2/main/install.sh | bash\n"
        "Or visit: https://github.com/varun369/SuperLocalMemoryV2"
    ) from exc


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Tag format: "li:chat:<hash>" where hash is a 24-char SHA-256 prefix of the key.
# Total tag length = 8 + 24 = 32 chars, well under SLM's 50-char MAX_TAG_LENGTH.
# The full session key is stored inside the serialized content JSON so get_keys()
# can reconstruct the original key even when the tag is hash-based.
_TAG_PREFIX = "li:chat:"
_PROJECT_NAME = "llamaindex"
_IMPORTANCE = 3
_LIST_LIMIT = 10000  # Upper bound when listing all memories for filtering
_HASH_LEN = 24  # Characters of SHA-256 hex digest to use in tags


def _key_hash(key: str) -> str:
    """Produce a deterministic short hash of a session key for use in SLM tags."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:_HASH_LEN]


def _make_tag(key: str) -> str:
    """Build the SLM tag for a chat session key.

    Uses a hash of the key to guarantee the tag never exceeds SLM's
    50-character limit regardless of key length or content.
    """
    return f"{_TAG_PREFIX}{_key_hash(key)}"


def _serialize_message(key: str, message: ChatMessage) -> str:
    """Serialize a ChatMessage to JSON string for SLM content storage.

    The session *key* is embedded in the payload so that ``get_keys()`` can
    reconstruct the original key from stored memories (the tag only contains
    a hash).
    """
    return json.dumps(
        {
            "key": key,
            "role": message.role.value,
            "content": message.content or "",
            "additional_kwargs": message.additional_kwargs,
        },
        ensure_ascii=False,
    )


def _deserialize_message(content: str) -> Optional[ChatMessage]:
    """Deserialize a JSON string back to a ChatMessage.

    Returns None if the content is not valid chat message JSON.
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict) or "role" not in data:
        return None

    try:
        role = MessageRole(data["role"])
    except ValueError:
        role = MessageRole.USER

    return ChatMessage(
        role=role,
        content=data.get("content", ""),
        additional_kwargs=data.get("additional_kwargs", {}),
    )


def _extract_key(content: str) -> Optional[str]:
    """Extract the session key from a serialized memory content string."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(data, dict):
        return data.get("key")
    return None


class SuperLocalMemoryChatStore(BaseChatStore):
    """LlamaIndex chat store backed by SuperLocalMemory V2.

    Stores chat messages in SuperLocalMemory's local SQLite database,
    keeping all data on-device with zero cloud calls.

    Each message is stored as a separate SLM memory entry tagged with
    ``li:chat:<hash>`` so different conversation sessions are cleanly
    isolated. The full session key is preserved inside the serialized
    content JSON for lossless round-tripping.

    Args:
        db_path: Optional path to the SQLite database file.
                 Defaults to ``~/.claude-memory/memory.db``.
    """

    # Pydantic fields ---------------------------------------------------
    # We store the db_path as a string so the model stays JSON-serializable.
    _db_path: Optional[str] = None
    _store: Any = None  # MemoryStoreV2 — not serializable, set in __init__

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, db_path: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize SuperLocalMemoryChatStore.

        Args:
            db_path: Optional path to the SLM SQLite database.
                     If None, uses the default ``~/.claude-memory/memory.db``.
        """
        super().__init__(**kwargs)
        self._db_path = db_path
        if db_path:
            self._store = MemoryStoreV2(db_path=Path(db_path))
        else:
            self._store = MemoryStoreV2()

    @classmethod
    def class_name(cls) -> str:
        """Get class name."""
        return "SuperLocalMemoryChatStore"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_memories_for_key(self, key: str) -> List[Dict[str, Any]]:
        """Retrieve all SLM memories that belong to a chat session *key*.

        Returns memories sorted by ``created_at`` ascending (oldest first)
        to preserve conversation order.
        """
        tag = _make_tag(key)
        all_memories = self._store.list_all(limit=_LIST_LIMIT)

        matched: List[Dict[str, Any]] = []
        for mem in all_memories:
            mem_tags = mem.get("tags", [])
            if isinstance(mem_tags, str):
                try:
                    mem_tags = json.loads(mem_tags)
                except (json.JSONDecodeError, TypeError):
                    mem_tags = [t.strip() for t in mem_tags.split(",") if t.strip()]
            if tag in (mem_tags or []):
                matched.append(mem)

        # Sort by created_at ascending for correct conversation order
        matched.sort(key=lambda m: m.get("created_at", ""))
        return matched

    def _memories_to_messages(
        self, memories: List[Dict[str, Any]]
    ) -> List[ChatMessage]:
        """Convert a list of SLM memory dicts to ChatMessage objects."""
        messages: List[ChatMessage] = []
        for mem in memories:
            msg = _deserialize_message(mem.get("content", ""))
            if msg is not None:
                messages.append(msg)
        return messages

    # ------------------------------------------------------------------
    # BaseChatStore abstract method implementations
    # ------------------------------------------------------------------

    def set_messages(self, key: str, messages: List[ChatMessage]) -> None:
        """Set messages for a key (replaces any existing messages)."""
        self.delete_messages(key)
        for message in messages:
            self.add_message(key, message)

    def get_messages(self, key: str) -> List[ChatMessage]:
        """Get messages for a key, ordered by creation time."""
        memories = self._get_memories_for_key(key)
        return self._memories_to_messages(memories)

    def add_message(self, key: str, message: ChatMessage) -> None:
        """Add a single message for a key."""
        content = _serialize_message(key, message)
        tag = _make_tag(key)
        self._store.add_memory(
            content=content,
            tags=[tag],
            project_name=_PROJECT_NAME,
            importance=_IMPORTANCE,
        )

    def delete_messages(self, key: str) -> Optional[List[ChatMessage]]:
        """Delete all messages for a key.

        Returns the deleted messages, or None if the key had no messages.
        """
        memories = self._get_memories_for_key(key)
        if not memories:
            return None

        messages = self._memories_to_messages(memories)

        for mem in memories:
            self._store.delete_memory(mem["id"])

        return messages

    def delete_message(self, key: str, idx: int) -> Optional[ChatMessage]:
        """Delete specific message for a key by index.

        Args:
            key: The session key.
            idx: Zero-based index of the message to delete.

        Returns:
            The deleted ChatMessage, or None if index is out of range.
        """
        memories = self._get_memories_for_key(key)
        if not memories or idx < 0 or idx >= len(memories):
            return None

        target = memories[idx]
        msg = _deserialize_message(target.get("content", ""))
        self._store.delete_memory(target["id"])
        return msg

    def delete_last_message(self, key: str) -> Optional[ChatMessage]:
        """Delete the last (most recent) message for a key.

        Returns:
            The deleted ChatMessage, or None if the key has no messages.
        """
        memories = self._get_memories_for_key(key)
        if not memories:
            return None

        last = memories[-1]
        msg = _deserialize_message(last.get("content", ""))
        self._store.delete_memory(last["id"])
        return msg

    def get_keys(self) -> List[str]:
        """Get all unique session keys that have stored messages.

        Keys are extracted from the serialized content JSON (the ``key``
        field) rather than from tags, because tags contain only a hash of
        the key for length-safety.
        """
        all_memories = self._store.list_all(limit=_LIST_LIMIT)
        keys_seen: set[str] = set()

        for mem in all_memories:
            # Only consider memories whose tags indicate they belong to us
            mem_tags = mem.get("tags", [])
            if isinstance(mem_tags, str):
                try:
                    mem_tags = json.loads(mem_tags)
                except (json.JSONDecodeError, TypeError):
                    mem_tags = [t.strip() for t in mem_tags.split(",") if t.strip()]

            is_ours = any(
                isinstance(t, str) and t.startswith(_TAG_PREFIX)
                for t in (mem_tags or [])
            )
            if not is_ours:
                continue

            key = _extract_key(mem.get("content", ""))
            if key is not None:
                keys_seen.add(key)

        return sorted(keys_seen)
