# Python API

**Programmatic access to SuperLocalMemory V2** - Import statements, core classes, code examples, and complete API reference for developers.

---

## Installation

SuperLocalMemory V2 is already installed if you ran `./install.sh`. The Python modules are located at `~/.claude-memory/`.

```bash
# Verify installation
ls -la ~/.claude-memory/memory_store_v2.py
ls -la ~/.claude-memory/graph_engine.py
ls -la ~/.claude-memory/pattern_learner.py
```

---

## Quick Start

### Basic Usage

```python
import sys
sys.path.append('/Users/YOUR_USERNAME/.claude-memory/')

from memory_store_v2 import MemoryStoreV2

# Initialize
store = MemoryStoreV2()

# Save memory
memory_id = store.save_memory(
    content="We use FastAPI for REST APIs",
    tags=["python", "backend", "api"],
    project_name="myapp",
    importance=7
)
print(f"Saved memory ID: {memory_id}")

# Search memories
results = store.search_memories("FastAPI", limit=5)
for result in results:
    print(f"[{result['id']}] {result['content']} (Score: {result['score']:.2f})")

# List recent
recent = store.list_recent(limit=10)
for mem in recent:
    print(f"[{mem['id']}] {mem['content']}")
```

---

## Core Classes

### MemoryStoreV2

**Location:** `~/.claude-memory/memory_store_v2.py`

**Description:** Main memory management class with SQLite storage, full-text search, and semantic search.

#### Initialization

```python
from memory_store_v2 import MemoryStoreV2

# Default profile
store = MemoryStoreV2()

# Specific profile
store = MemoryStoreV2(profile="work")

# Custom database path
store = MemoryStoreV2(db_path="/custom/path/memory.db")
```

#### Methods

##### save_memory()

```python
memory_id = store.save_memory(
    content: str,
    tags: list = None,
    project_name: str = "default",
    importance: int = 5,
    parent_id: int = None
) -> int
```

**Parameters:**
- `content` (str, required): Memory content (max 1MB)
- `tags` (list, optional): List of tags
- `project_name` (str, optional): Project name (default: "default")
- `importance` (int, optional): Priority 1-10 (default: 5)
- `parent_id` (int, optional): Parent memory ID for hierarchical organization

**Returns:** Memory ID (int)

**Example:**
```python
memory_id = store.save_memory(
    content="JWT tokens expire after 24 hours",
    tags=["security", "auth", "jwt"],
    project_name="api-project",
    importance=8
)
```

##### search_memories()

```python
results = store.search_memories(
    query: str,
    limit: int = 10,
    min_score: float = 0.3,
    tags: list = None,
    project_name: str = None
) -> list[dict]
```

**Parameters:**
- `query` (str, required): Search query
- `limit` (int, optional): Max results (default: 10)
- `min_score` (float, optional): Minimum relevance 0.0-1.0 (default: 0.3)
- `tags` (list, optional): Filter by tags
- `project_name` (str, optional): Filter by project

**Returns:** List of dicts with keys: `id`, `content`, `score`, `tags`, `project_name`, `created_at`

**Example:**
```python
results = store.search_memories(
    query="authentication",
    limit=5,
    min_score=0.7,
    tags=["security"]
)

for result in results:
    print(f"[{result['id']}] Score: {result['score']:.2f}")
    print(f"  {result['content']}")
    print(f"  Tags: {', '.join(result['tags'])}")
```

##### list_recent()

```python
recent = store.list_recent(
    limit: int = 10,
    project_name: str = None
) -> list[dict]
```

**Parameters:**
- `limit` (int, optional): Number to return (default: 10)
- `project_name` (str, optional): Filter by project

**Returns:** List of dicts (same structure as search_memories)

**Example:**
```python
recent = store.list_recent(limit=20)
for mem in recent:
    print(f"[{mem['id']}] {mem['created_at']}: {mem['content'][:50]}...")
```

##### list_all()

```python
all_memories = store.list_all(
    project_name: str = None,
    tags: list = None
) -> list[dict]
```

**Parameters:**
- `project_name` (str, optional): Filter by project
- `tags` (list, optional): Filter by tags

**Returns:** List of all memories (no limit)

**Example:**
```python
# Get all memories
all_memories = store.list_all()
print(f"Total memories: {len(all_memories)}")

# Filter by project
work_memories = store.list_all(project_name="work")
```

##### get_memory()

```python
memory = store.get_memory(memory_id: int) -> dict
```

**Parameters:**
- `memory_id` (int, required): Memory ID

**Returns:** Dict with memory details or None if not found

**Example:**
```python
memory = store.get_memory(42)
if memory:
    print(f"Content: {memory['content']}")
    print(f"Tags: {memory['tags']}")
else:
    print("Memory not found")
```

##### delete_memory()

```python
success = store.delete_memory(memory_id: int) -> bool
```

**Parameters:**
- `memory_id` (int, required): Memory ID to delete

**Returns:** True if deleted, False if not found

**Example:**
```python
if store.delete_memory(42):
    print("Memory deleted")
else:
    print("Memory not found")
```

##### get_stats()

```python
stats = store.get_stats() -> dict
```

**Returns:** Dict with keys: `total_memories`, `database_size_mb`, `profiles`

**Example:**
```python
stats = store.get_stats()
print(f"Total memories: {stats['total_memories']}")
print(f"Database size: {stats['database_size_mb']:.2f} MB")
```

##### get_attribution()

```python
attribution = store.get_attribution() -> dict
```

**Returns:** Dict with creator metadata

**Example:**
```python
attr = store.get_attribution()
print(f"Creator: {attr['creator']}")
print(f"Project: {attr['project']}")
print(f"License: {attr['license']}")
```

---

### GraphEngine

**Location:** `~/.claude-memory/graph_engine.py`

**Description:** Knowledge graph management with TF-IDF entity extraction and Leiden clustering.

#### Initialization

```python
from graph_engine import GraphEngine

# Default profile
graph = GraphEngine()

# Specific profile
graph = GraphEngine(profile="work")
```

#### Methods

##### build_graph()

```python
result = graph.build_graph(
    force: bool = False,
    clustering: bool = False,
    verbose: bool = False
) -> dict
```

**Parameters:**
- `force` (bool, optional): Force complete rebuild (default: False)
- `clustering` (bool, optional): Run Leiden clustering (default: False)
- `verbose` (bool, optional): Print progress (default: False)

**Returns:** Dict with keys: `nodes`, `edges`, `clusters`, `build_time`

**Example:**
```python
result = graph.build_graph(clustering=True, verbose=True)
print(f"Nodes: {result['nodes']}")
print(f"Edges: {result['edges']}")
print(f"Clusters: {result['clusters']}")
print(f"Build time: {result['build_time']:.2f}s")
```

##### get_stats()

```python
stats = graph.get_stats() -> dict
```

**Returns:** Dict with graph statistics

**Example:**
```python
stats = graph.get_stats()
print(f"Nodes: {stats['nodes']}")
print(f"Edges: {stats['edges']}")
print(f"Density: {stats['density']:.2f}%")
print(f"Largest component: {stats['largest_component']}")
```

##### get_related_memories()

```python
related = graph.get_related_memories(
    memory_id: int,
    limit: int = 5
) -> list[tuple]
```

**Parameters:**
- `memory_id` (int, required): Source memory ID
- `limit` (int, optional): Max related memories (default: 5)

**Returns:** List of tuples: `(memory_id, similarity_score)`

**Example:**
```python
related = graph.get_related_memories(42, limit=10)
for mem_id, score in related:
    print(f"Memory {mem_id}: similarity {score:.2f}")
```

##### get_clusters()

```python
clusters = graph.get_clusters() -> list[dict]
```

**Returns:** List of clusters with keys: `id`, `name`, `size`, `top_entities`

**Example:**
```python
clusters = graph.get_clusters()
for cluster in clusters:
    print(f"Cluster {cluster['id']}: {cluster['name']}")
    print(f"  Size: {cluster['size']} memories")
    print(f"  Top entities: {', '.join(cluster['top_entities'])}")
```

---

### PatternLearner

**Location:** `~/.claude-memory/pattern_learner.py`

**Description:** Pattern learning with multi-dimensional identity extraction and confidence scoring.

#### Initialization

```python
from pattern_learner import PatternLearner

# Default profile
learner = PatternLearner()

# Specific profile
learner = PatternLearner(profile="work")
```

#### Methods

##### update_patterns()

```python
result = learner.update_patterns() -> dict
```

**Returns:** Dict with keys: `patterns_updated`, `categories`, `update_time`

**Example:**
```python
result = learner.update_patterns()
print(f"Patterns updated: {result['patterns_updated']}")
print(f"Categories: {', '.join(result['categories'])}")
```

##### get_identity_context()

```python
context = learner.get_identity_context(
    min_confidence: float = 0.5
) -> str
```

**Parameters:**
- `min_confidence` (float, optional): Minimum confidence threshold (default: 0.5)

**Returns:** Formatted identity context string

**Example:**
```python
context = learner.get_identity_context(min_confidence=0.6)
print(context)
```

##### list_patterns()

```python
patterns = learner.list_patterns(
    category: str = None
) -> list[dict]
```

**Parameters:**
- `category` (str, optional): Filter by category

**Returns:** List of dicts with keys: `category`, `pattern`, `confidence`, `frequency`

**Example:**
```python
# All patterns
all_patterns = learner.list_patterns()

# Framework patterns only
frameworks = learner.list_patterns(category="frameworks")
for pattern in frameworks:
    print(f"{pattern['pattern']}: {pattern['confidence']:.0%}")
```

##### reset_patterns()

```python
success = learner.reset_patterns() -> bool
```

**Returns:** True if reset successful

**Example:**
```python
if learner.reset_patterns():
    print("Patterns reset successfully")
```

---

## Complete Example

### Building a Memory Assistant

```python
import sys
sys.path.append('/Users/YOUR_USERNAME/.claude-memory/')

from memory_store_v2 import MemoryStoreV2
from graph_engine import GraphEngine
from pattern_learner import PatternLearner

class MemoryAssistant:
    def __init__(self, profile="default"):
        self.store = MemoryStoreV2(profile=profile)
        self.graph = GraphEngine(profile=profile)
        self.learner = PatternLearner(profile=profile)

    def remember(self, content, tags=None, importance=5):
        """Save memory and update patterns"""
        memory_id = self.store.save_memory(
            content=content,
            tags=tags or [],
            importance=importance
        )
        print(f"✓ Memory saved (ID: {memory_id})")

        # Update patterns
        self.learner.update_patterns()
        return memory_id

    def recall(self, query, limit=5, min_score=0.7):
        """Search memories with graph enhancement"""
        results = self.store.search_memories(
            query=query,
            limit=limit,
            min_score=min_score
        )

        print(f"🔍 Found {len(results)} results:\n")
        for result in results:
            print(f"[{result['id']}] Score: {result['score']:.2f}")
            print(f"  {result['content']}")
            print(f"  Tags: {', '.join(result['tags'])}")
            print()

        return results

    def get_identity(self):
        """Get learned identity context"""
        context = self.learner.get_identity_context(min_confidence=0.5)
        print("Your Coding Identity:")
        print(context)
        return context

    def build_knowledge_graph(self):
        """Build/update knowledge graph"""
        print("Building knowledge graph...")
        result = self.graph.build_graph(clustering=True, verbose=True)
        print(f"\n✓ Graph built: {result['nodes']} nodes, {result['edges']} edges")
        return result

    def find_related(self, memory_id, limit=5):
        """Find related memories"""
        related = self.graph.get_related_memories(memory_id, limit=limit)
        print(f"Related to memory {memory_id}:\n")
        for mem_id, score in related:
            memory = self.store.get_memory(mem_id)
            print(f"[{mem_id}] Similarity: {score:.2f}")
            print(f"  {memory['content'][:100]}...")
            print()
        return related

# Usage
assistant = MemoryAssistant(profile="work")

# Save memories
assistant.remember("We use FastAPI for REST APIs", tags=["python", "backend"])
assistant.remember("JWT tokens expire after 24h", tags=["security", "auth"])
assistant.remember("PostgreSQL 15 for database", tags=["database"])

# Build graph
assistant.build_knowledge_graph()

# Search
assistant.recall("authentication")

# Get identity
assistant.get_identity()

# Find related
assistant.find_related(1)
```

---

## Advanced Usage

### Context Manager

```python
from contextlib import contextmanager

@contextmanager
def memory_context(profile="default"):
    """Context manager for profile switching"""
    store = MemoryStoreV2(profile=profile)
    yield store
    # Cleanup if needed

# Usage
with memory_context("work") as store:
    store.save_memory("Work memory", tags=["work"])

with memory_context("personal") as store:
    store.save_memory("Personal memory", tags=["personal"])
```

### Batch Operations

```python
def bulk_import(memories, profile="default"):
    """Import multiple memories efficiently"""
    store = MemoryStoreV2(profile=profile)
    graph = GraphEngine(profile=profile)

    memory_ids = []
    for mem in memories:
        mem_id = store.save_memory(
            content=mem['content'],
            tags=mem.get('tags', []),
            importance=mem.get('importance', 5)
        )
        memory_ids.append(mem_id)

    # Build graph once after all imports
    graph.build_graph(force=True)

    return memory_ids

# Usage
memories = [
    {"content": "Memory 1", "tags": ["tag1"]},
    {"content": "Memory 2", "tags": ["tag2"]},
    {"content": "Memory 3", "tags": ["tag3"]}
]
bulk_import(memories)
```

### Custom Search

```python
def search_with_boost(query, boost_tags, profile="default"):
    """Search with tag boosting"""
    store = MemoryStoreV2(profile=profile)

    # Search
    results = store.search_memories(query)

    # Boost results with specific tags
    for result in results:
        if any(tag in result['tags'] for tag in boost_tags):
            result['score'] *= 1.2  # 20% boost

    # Re-sort by score
    results.sort(key=lambda x: x['score'], reverse=True)

    return results

# Usage
results = search_with_boost(
    query="authentication",
    boost_tags=["critical", "security"]
)
```

---

## Error Handling

### Common Exceptions

```python
from memory_store_v2 import MemoryStoreV2

store = MemoryStoreV2()

try:
    # Save memory
    memory_id = store.save_memory(
        content="",  # Empty content
        tags=["test"]
    )
except ValueError as e:
    print(f"Error: {e}")  # "Content cannot be empty"

try:
    # Invalid importance
    memory_id = store.save_memory(
        content="Test",
        importance=15  # Invalid (must be 1-10)
    )
except ValueError as e:
    print(f"Error: {e}")  # "Importance must be between 1 and 10"
```

---

## Type Hints

```python
from typing import List, Dict, Optional, Tuple

def save_memory_typed(
    store: MemoryStoreV2,
    content: str,
    tags: Optional[List[str]] = None,
    importance: int = 5
) -> int:
    """Type-hinted memory save function"""
    return store.save_memory(content=content, tags=tags, importance=importance)

def search_typed(
    store: MemoryStoreV2,
    query: str,
    limit: int = 10
) -> List[Dict[str, any]]:
    """Type-hinted search function"""
    return store.search_memories(query=query, limit=limit)
```

---

## Testing

```python
import unittest
from memory_store_v2 import MemoryStoreV2

class TestMemoryStore(unittest.TestCase):
    def setUp(self):
        """Create test store"""
        self.store = MemoryStoreV2(profile="test")

    def test_save_memory(self):
        """Test memory save"""
        memory_id = self.store.save_memory(
            content="Test memory",
            tags=["test"]
        )
        self.assertIsInstance(memory_id, int)
        self.assertGreater(memory_id, 0)

    def test_search_memories(self):
        """Test memory search"""
        # Save memory
        self.store.save_memory(content="FastAPI test", tags=["test"])

        # Search
        results = self.store.search_memories("FastAPI")
        self.assertGreater(len(results), 0)
        self.assertIn("FastAPI", results[0]['content'])

    def tearDown(self):
        """Cleanup test profile"""
        # Delete test profile
        pass

if __name__ == '__main__':
    unittest.main()
```

---

## Related Pages

- [Quick Start Tutorial](Quick-Start-Tutorial) - First-time setup
- [CLI Cheatsheet](CLI-Cheatsheet) - Command reference
- [Knowledge Graph Guide](Knowledge-Graph-Guide) - Graph features
- [Pattern Learning](Pattern-Learning-Explained) - Pattern learning details
- [Configuration](Configuration) - Advanced settings

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*

[GitHub](https://github.com/varun369/SuperLocalMemoryV2) • [Issues](https://github.com/varun369/SuperLocalMemoryV2/issues) • [Wiki](https://github.com/varun369/SuperLocalMemoryV2/wiki)
