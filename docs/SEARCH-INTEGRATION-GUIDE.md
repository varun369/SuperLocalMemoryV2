# Search Engine Integration Guide

**Version:** 2.2.0
**Author:** Varun Pratap Bhardwaj

---

## Quick Start

### 5-Minute Setup

```bash
# 1. Install dependencies
pip install scikit-learn numpy

# 2. Test BM25 engine
python src/search_engine_v2.py

# 3. Test hybrid search
python src/hybrid_search.py "your search query"
```

---

## Basic Usage

### Option 1: Use Existing API (No Changes)

```python
from memory_store_v2 import MemoryStoreV2

store = MemoryStoreV2()

# Add memories
store.add_memory("Python web development with Django", tags=['python', 'web'])
store.add_memory("JavaScript React frontend", tags=['javascript', 'react'])

# Search (uses existing TF-IDF + FTS)
results = store.search("Python web", limit=5)

for mem in results:
    print(f"Score: {mem['score']:.3f}")
    print(f"Content: {mem['content'][:100]}")
```

**Result:** Works exactly as before. No changes required.

---

### Option 2: Use New Hybrid Search (Recommended)

```python
from pathlib import Path
from hybrid_search import HybridSearchEngine

# Initialize hybrid search
db_path = Path.home() / ".claude-memory" / "memory.db"
hybrid = HybridSearchEngine(db_path, enable_cache=True)

# Search with BM25 (fastest, keyword-focused)
results = hybrid.search("Python web", method="bm25", limit=5)

# Search with hybrid fusion (best relevance)
results = hybrid.search("Python web", method="hybrid", limit=5)

# Display results
for mem in results:
    print(f"[{mem['id']}] Score: {mem['score']:.3f}")
    print(f"Category: {mem.get('category', 'N/A')}")
    print(f"Content: {mem['content'][:100]}...")
    print()
```

**Benefits:**
- 3x faster search
- Better relevance ranking
- Query optimization (spell correction)
- Result caching

---

## Integration Patterns

### Pattern 1: Drop-In Replacement

Replace existing search calls with hybrid search:

**Before:**
```python
results = store.search(query, limit=10)
```

**After:**
```python
results = hybrid.search(query, method="hybrid", limit=10)
```

**Changes:** None to result format - both return same dictionary structure.

---

### Pattern 2: Fallback Strategy

Use hybrid search with fallback:

```python
def smart_search(query, limit=10):
    """Search with hybrid engine, fallback to store."""
    try:
        # Try hybrid search first
        return hybrid.search(query, method="hybrid", limit=limit)
    except Exception as e:
        # Fallback to store search
        print(f"Hybrid search failed: {e}")
        return store.search(query, limit=limit)

results = smart_search("Python web")
```

---

### Pattern 3: Query-Adaptive Selection

Choose method based on query type:

```python
import re

def adaptive_search(query, limit=10):
    """Select search method based on query characteristics."""

    # Detect query type
    has_quotes = '"' in query
    has_boolean = any(op in query.upper() for op in ['AND', 'OR', 'NOT'])
    word_count = len(query.split())

    # Select method
    if has_quotes or has_boolean:
        # Exact matching - use BM25
        method = "bm25"
        weights = None
    elif word_count <= 2:
        # Short query - use BM25 (keyword-focused)
        method = "weighted"
        weights = {'bm25': 0.7, 'semantic': 0.3, 'graph': 0.0}
    else:
        # Long query - use hybrid (balanced)
        method = "hybrid"
        weights = None

    return hybrid.search(query, method=method, weights=weights, limit=limit)

# Examples
results = adaptive_search('"Python Django"')  # Uses BM25
results = adaptive_search('Python')            # Uses BM25-heavy
results = adaptive_search('how to build REST API')  # Uses hybrid
```

---

### Pattern 4: Progressive Enhancement

Use cache-aware search with progressive methods:

```python
def progressive_search(query, limit=10, use_cache=True):
    """Try fast methods first, fall back to comprehensive."""

    # Try cache first
    if use_cache:
        cached = hybrid.cache.get(query, limit=limit)
        if cached:
            print(f"Cache hit! ({len(cached)} results)")
            return cached

    # Try BM25 first (fastest)
    results = hybrid.search(query, method="bm25", limit=limit)

    # If insufficient results, try hybrid
    if len(results) < limit // 2:
        print(f"BM25 returned only {len(results)} results, trying hybrid...")
        results = hybrid.search(query, method="hybrid", limit=limit)

    # Cache results
    if use_cache:
        hybrid.cache.put(query, results, limit=limit)

    return results
```

---

## Advanced Integration

### Custom Weight Configuration

```python
class SearchEngine:
    """Wrapper with custom search strategies."""

    def __init__(self, db_path):
        self.hybrid = HybridSearchEngine(db_path, enable_cache=True)

        # Define search strategies
        self.strategies = {
            'keyword': {'bm25': 0.8, 'semantic': 0.2, 'graph': 0.0},
            'semantic': {'bm25': 0.2, 'semantic': 0.5, 'graph': 0.3},
            'balanced': {'bm25': 0.4, 'semantic': 0.3, 'graph': 0.3},
            'graph': {'bm25': 0.1, 'semantic': 0.3, 'graph': 0.6},
        }

    def search(self, query, strategy='balanced', limit=10):
        """Search with named strategy."""
        weights = self.strategies.get(strategy, self.strategies['balanced'])
        return self.hybrid.search(
            query,
            method='weighted',
            weights=weights,
            limit=limit
        )

    def keyword_search(self, query, limit=10):
        """Optimized for exact term matching."""
        return self.search(query, strategy='keyword', limit=limit)

    def semantic_search(self, query, limit=10):
        """Optimized for meaning-based search."""
        return self.search(query, strategy='semantic', limit=limit)

    def graph_search(self, query, limit=10):
        """Optimized for conceptual/related search."""
        return self.search(query, strategy='graph', limit=limit)

# Usage
engine = SearchEngine(db_path)

# Different search modes
results = engine.keyword_search("Python Django REST")
results = engine.semantic_search("how to authenticate users")
results = engine.graph_search("related to performance optimization")
```

---

### Query Optimization Pipeline

```python
from query_optimizer import QueryOptimizer

class OptimizedSearchEngine:
    """Search engine with query preprocessing."""

    def __init__(self, db_path):
        self.hybrid = HybridSearchEngine(db_path)
        self.optimizer = self.hybrid.optimizer

    def search_with_correction(self, query, limit=10):
        """Search with automatic spell correction."""

        # Optimize query
        optimized = self.optimizer.optimize(
            query,
            enable_spell_correction=True,
            enable_expansion=False
        )

        print(f"Original: {query}")
        print(f"Optimized: {optimized}")

        # Search with optimized query
        results = self.hybrid.search(optimized, method="hybrid", limit=limit)

        return results

    def search_with_expansion(self, query, limit=10):
        """Search with query expansion."""

        # Parse and expand
        tokens = self.optimizer.optimize(
            query,
            enable_spell_correction=True,
            enable_expansion=True,
            max_expansions=2
        )

        print(f"Expanded query: {tokens}")

        return self.hybrid.search(tokens, method="hybrid", limit=limit)

# Usage
engine = OptimizedSearchEngine(db_path)

# Auto-corrects "pythno" → "python"
results = engine.search_with_correction("pythno web devlopment")

# Expands "auth" → "auth authentication authorize"
results = engine.search_with_expansion("auth")
```

---

## Performance Optimization

### 1. Cache Configuration

```python
from cache_manager import CacheManager

# High-traffic application
cache = CacheManager(
    max_size=1000,        # Large cache
    ttl_seconds=600,      # 10 minute TTL
    thread_safe=True      # Enable for concurrent access
)

hybrid = HybridSearchEngine(db_path, cache_manager=cache)
```

### 2. Method Selection for Speed

```python
# Fastest: BM25 only (~15ms)
results = hybrid.search(query, method="bm25")

# Fast: BM25 + Semantic (~25ms)
results = hybrid.search(
    query,
    method="weighted",
    weights={'bm25': 0.6, 'semantic': 0.4, 'graph': 0.0}
)

# Comprehensive: All methods (~35ms)
results = hybrid.search(query, method="hybrid")
```

### 3. Limit Results Early

```python
# Request fewer results for speed
results = hybrid.search(query, limit=5)   # Fast

# Request more for completeness
results = hybrid.search(query, limit=50)  # Slower
```

### 4. Cache Warming

```python
def warm_cache(common_queries):
    """Pre-populate cache with common queries."""
    for query in common_queries:
        hybrid.search(query, limit=10, use_cache=True)

    stats = hybrid.cache.get_stats()
    print(f"Cache warmed: {stats['current_size']} entries")

# Common queries
common_queries = [
    "python web",
    "javascript react",
    "authentication",
    "database optimization",
]

warm_cache(common_queries)
```

---

## Testing Integration

### Unit Tests

```python
import unittest
from pathlib import Path
import tempfile
import shutil

class TestSearchIntegration(unittest.TestCase):

    def setUp(self):
        """Create temp database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"

        # Create store and add test data
        from memory_store_v2 import MemoryStoreV2
        store = MemoryStoreV2(db_path=self.db_path)

        store.add_memory("Python web development", tags=['python', 'web'])
        store.add_memory("JavaScript frontend", tags=['javascript'])

        # Initialize hybrid search
        self.hybrid = HybridSearchEngine(self.db_path)

    def tearDown(self):
        """Cleanup temp database."""
        shutil.rmtree(self.temp_dir)

    def test_bm25_search(self):
        """Test BM25 search returns results."""
        results = self.hybrid.search("Python", method="bm25", limit=5)
        self.assertGreater(len(results), 0)
        self.assertIn('score', results[0])

    def test_hybrid_search(self):
        """Test hybrid search returns results."""
        results = self.hybrid.search("Python", method="hybrid", limit=5)
        self.assertGreater(len(results), 0)

    def test_cache_hit(self):
        """Test cache working."""
        # First query - cache miss
        self.hybrid.search("Python", method="bm25")

        # Second query - cache hit
        self.hybrid.search("Python", method="bm25")

        stats = self.hybrid.cache.get_stats()
        self.assertGreater(stats['hits'], 0)

if __name__ == '__main__':
    unittest.main()
```

---

## Migration Checklist

### From V2.1.0 to V2.2.0

- [ ] Install dependencies: `pip install scikit-learn numpy`
- [ ] Test existing search: `python -c "from memory_store_v2 import MemoryStoreV2; store = MemoryStoreV2(); print(store.search('test'))"`
- [ ] Test new BM25: `python src/search_engine_v2.py`
- [ ] Test hybrid search: `python src/hybrid_search.py "test query"`
- [ ] Run test suite: `python test_search_engine.py`
- [ ] Update application code (optional)
- [ ] Monitor performance improvements
- [ ] Adjust weights if needed

---

## Troubleshooting

### Issue: Import Error

```python
ImportError: No module named 'sklearn'
```

**Solution:**
```bash
pip install scikit-learn numpy
```

### Issue: Slow Search

**Check:**
1. Database size: `SELECT COUNT(*) FROM memories`
2. Cache stats: `hybrid.cache.get_stats()`
3. Search method: Try `method="bm25"` for speed

**Solutions:**
- Use BM25 only for keyword queries
- Enable caching
- Reduce result limit

### Issue: Poor Relevance

**Solutions:**
1. Try hybrid search: `method="hybrid"`
2. Adjust weights for query type
3. Enable query expansion for short queries
4. Use spell correction for typos

---

## Best Practices

1. **Use hybrid search by default** - Best balance of speed and relevance
2. **Enable caching** - 30-50% performance improvement on repeated queries
3. **Choose method based on query** - Use adaptive_search pattern
4. **Monitor cache stats** - Optimize cache size based on hit rate
5. **Test different weights** - Fine-tune for your specific use case
6. **Keep vocabulary updated** - Rebuild index when adding many memories

---

## Support

**Documentation:**
- [Search Engine V2.2.0](SEARCH-ENGINE-V2.2.0.md)
- [API Reference](API-REFERENCE.md)
- [Main README](../README.md)

**Issues:** [GitHub Issues](https://github.com/varun369/SuperLocalMemoryV2/issues)

---

**Created by:** Varun Pratap Bhardwaj
**License:** MIT
