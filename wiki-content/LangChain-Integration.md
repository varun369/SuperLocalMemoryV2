# LangChain Integration

Use SuperLocalMemory V2 as a local-first chat message history backend for LangChain applications. All data stays on your machine — zero cloud calls, zero API keys for the memory layer.

## Installation

**Prerequisites:** SuperLocalMemory V2 installed (`npm install -g superlocalmemory` or `./install.sh`)

```bash
pip install langchain-superlocalmemory
```

## Quick Start

```python
from langchain_superlocalmemory import SuperLocalMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

# Create a session
history = SuperLocalMemoryChatMessageHistory(session_id="my-project")

# Add messages
history.add_messages([
    HumanMessage(content="I'm building a React app with TypeScript"),
    AIMessage(content="Great choice! Do you want to use Next.js or Vite?"),
])

# Messages persist across sessions
messages = history.messages  # Returns all messages for this session
```

## Usage with RunnableWithMessageHistory

```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_superlocalmemory import SuperLocalMemoryChatMessageHistory

# Store factory — returns persistent local memory per session
store = {}

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = SuperLocalMemoryChatMessageHistory(session_id=session_id)
    return store[session_id]

# Wrap your chain with persistent memory
conversation = RunnableWithMessageHistory(
    your_chain,
    get_session_history,
)

# Each session_id gets isolated, persistent memory
response = conversation.invoke(
    "What framework am I using?",
    config={"configurable": {"session_id": "my-project"}},
)
```

## Multi-Session Support

```python
# Work project
work = SuperLocalMemoryChatMessageHistory(session_id="work-api-redesign")

# Personal project
personal = SuperLocalMemoryChatMessageHistory(session_id="personal-blog")

# Sessions are fully isolated — no cross-contamination
```

## API Reference

### `SuperLocalMemoryChatMessageHistory`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `session_id` | `str` | Required | Unique identifier for this conversation session |
| `db_path` | `Optional[str]` | `~/.claude-memory/memory.db` | Path to SQLite database |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `.messages` | `List[BaseMessage]` | All messages for this session, ordered chronologically |
| `.add_messages(messages)` | `None` | Add one or more messages to the session |
| `.clear()` | `None` | Remove all messages for this session |

## How It Works

- Each message is stored as a memory entry in SLM's SQLite database
- Messages are tagged with `langchain:session:{session_id}` for isolation
- Content is serialized via LangChain's `message_to_dict()` for perfect round-trip fidelity
- All message types supported: `HumanMessage`, `AIMessage`, `SystemMessage`, `FunctionMessage`, `ToolMessage`
- Importance is set to 3 (lower than user memories) so chat history doesn't crowd search results

## Links

- [GitHub Repository](https://github.com/varun369/SuperLocalMemoryV2)
- [Full Documentation](https://superlocalmemory.com/)
- [LlamaIndex Integration](LlamaIndex-Integration)
- [Example Script](https://github.com/varun369/SuperLocalMemoryV2/blob/main/examples/langchain_example.py)
