# LlamaIndex Integration

Use SuperLocalMemory V2 as a local-first chat store backend for LlamaIndex applications. All data stays on your machine — zero cloud calls, zero API keys for the memory layer.

## Installation

**Prerequisites:** SuperLocalMemory V2 installed (`npm install -g superlocalmemory` or `./install.sh`)

```bash
pip install llama-index-storage-chat-store-superlocalmemory
```

## Quick Start

```python
from llama_index.storage.chat_store.superlocalmemory import SuperLocalMemoryChatStore
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.llms import ChatMessage, MessageRole

# Create chat store (backed by local SQLite)
chat_store = SuperLocalMemoryChatStore()

# Use with ChatMemoryBuffer
memory = ChatMemoryBuffer.from_defaults(
    token_limit=3000,
    chat_store=chat_store,
    chat_store_key="user-123",
)
```

## Usage with SimpleChatEngine

```python
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.storage.chat_store.superlocalmemory import SuperLocalMemoryChatStore

chat_store = SuperLocalMemoryChatStore()

memory = ChatMemoryBuffer.from_defaults(
    token_limit=3000,
    chat_store=chat_store,
    chat_store_key="project-frontend",
)

chat_engine = SimpleChatEngine(
    memory=memory,
    llm=your_llm,
    prefix_messages=[],
)

response = chat_engine.chat("How do I center a div?")
```

## Direct Store Operations

```python
from llama_index.storage.chat_store.superlocalmemory import SuperLocalMemoryChatStore
from llama_index.core.llms import ChatMessage, MessageRole

store = SuperLocalMemoryChatStore()

# Add messages
store.add_message("session-1", ChatMessage(role=MessageRole.USER, content="Hello"))
store.add_message("session-1", ChatMessage(role=MessageRole.ASSISTANT, content="Hi there!"))

# Get messages
messages = store.get_messages("session-1")

# List all session keys
keys = store.get_keys()  # ["session-1"]

# Delete operations
store.delete_last_message("session-1")     # Remove last message
store.delete_message("session-1", 0)       # Remove by index
store.delete_messages("session-1")         # Remove all for key

# Replace all messages at once
store.set_messages("session-1", [
    ChatMessage(role=MessageRole.USER, content="Fresh start"),
])
```

## API Reference

### `SuperLocalMemoryChatStore`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | `Optional[str]` | `~/.claude-memory/memory.db` | Path to SQLite database |

**Methods (all 7 BaseChatStore abstract methods):**

| Method | Returns | Description |
|--------|---------|-------------|
| `set_messages(key, messages)` | `None` | Replace all messages for a key |
| `get_messages(key)` | `List[ChatMessage]` | Get messages ordered by creation time |
| `add_message(key, message)` | `None` | Add a single message |
| `delete_messages(key)` | `Optional[List[ChatMessage]]` | Delete all messages, return deleted |
| `delete_message(key, idx)` | `Optional[ChatMessage]` | Delete by zero-based index |
| `delete_last_message(key)` | `Optional[ChatMessage]` | Delete most recent message |
| `get_keys()` | `List[str]` | List all session keys with data |

## How It Works

- Each message stored as a memory entry in SLM's SQLite database
- Session keys are hashed (`SHA-256`) for tags to stay within SLM's 50-char tag limit
- Full session key is preserved inside the serialized JSON for lossless round-tripping
- All `MessageRole` types supported: USER, ASSISTANT, SYSTEM, TOOL
- Importance set to 3 (lower than user memories) to avoid crowding search results

## Links

- [GitHub Repository](https://github.com/varun369/SuperLocalMemoryV2)
- [Full Documentation](https://superlocalmemory.com/)
- [LangChain Integration](LangChain-Integration)
- [Example Script](https://github.com/varun369/SuperLocalMemoryV2/blob/main/examples/llamaindex_example.py)
