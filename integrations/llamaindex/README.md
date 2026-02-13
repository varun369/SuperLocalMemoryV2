# LlamaIndex Chat Store — SuperLocalMemory V2

A LlamaIndex `BaseChatStore` implementation backed by [SuperLocalMemory V2](https://github.com/varun369/SuperLocalMemoryV2). All chat history stays **100% local** on your machine — zero cloud calls, zero telemetry, zero API keys.

## Prerequisites

- Python 3.9+
- SuperLocalMemory V2 installed (`~/.claude-memory/` must exist)

```bash
# Install SuperLocalMemory V2 (one-time)
curl -fsSL https://raw.githubusercontent.com/varun369/SuperLocalMemoryV2/main/install.sh | bash
```

## Installation

```bash
pip install llama-index-storage-chat-store-superlocalmemory
```

## Quick Start

```python
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.storage.chat_store.superlocalmemory import SuperLocalMemoryChatStore

# Create the chat store (uses default SLM database)
chat_store = SuperLocalMemoryChatStore()

# Use with ChatMemoryBuffer for automatic conversation management
memory = ChatMemoryBuffer.from_defaults(
    chat_store=chat_store,
    chat_store_key="user-123",
    token_limit=3000,
)

# Or use directly for manual message management
chat_store.add_message("session-1", ChatMessage(role=MessageRole.USER, content="Hello!"))
chat_store.add_message("session-1", ChatMessage(role=MessageRole.ASSISTANT, content="Hi there!"))

messages = chat_store.get_messages("session-1")
print(messages)  # [ChatMessage(role=user, content="Hello!"), ChatMessage(role=assistant, content="Hi there!")]

# List all session keys
keys = chat_store.get_keys()

# Delete a session
chat_store.delete_messages("session-1")
```

## Features

- **100% Local** — All data stored in SQLite at `~/.claude-memory/memory.db`
- **Zero Cloud** — No API keys, no subscriptions, no data leaves your machine
- **Shared Memory** — Chat history is accessible from Claude, Cursor, Windsurf, and 16+ other AI tools via SuperLocalMemory
- **Session Isolation** — Each chat key is cleanly isolated using SLM tags
- **Persistent** — Survives process restarts (SQLite-backed, not in-memory)
- **Full BaseChatStore API** — `set_messages`, `get_messages`, `add_message`, `delete_messages`, `delete_message`, `delete_last_message`, `get_keys`
- **Async Support** — Async methods inherited from BaseChatStore (delegates to sync via `asyncio.to_thread`)

## How It Works

Each chat message is stored as a separate memory entry in SuperLocalMemory V2:
- **Content**: JSON-serialized `{role, content, additional_kwargs}`
- **Tag**: `llamaindex:chat:<session_key>` for session isolation
- **Project**: `llamaindex` for easy identification
- **Importance**: 3 (low, since chat messages are transient)

## Custom Database Path

```python
# Use a custom database file
chat_store = SuperLocalMemoryChatStore(db_path="/path/to/custom/memory.db")
```

## Links

- [SuperLocalMemory V2](https://github.com/varun369/SuperLocalMemoryV2)
- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [LlamaIndex Chat Stores Guide](https://docs.llamaindex.ai/en/stable/module_guides/storing/chat_stores/)
