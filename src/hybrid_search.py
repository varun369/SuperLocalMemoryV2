#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Hybrid Search System

Copyright (c) 2026 Varun Pratap Bhardwaj
Solution Architect & Original Creator

Licensed under MIT License (see LICENSE file)
Repository: https://github.com/varun369/SuperLocalMemoryV2

ATTRIBUTION REQUIRED: This notice must be preserved in all copies.
"""

"""
Hybrid Search System - Multi-Method Retrieval Fusion

Combines multiple search methods for optimal retrieval quality:

1. BM25 Keyword Search: Lexical matching with relevance ranking
   - Fast exact term matching
   - Good for technical queries with specific terms
   - Weight: 0.4 (40%)

2. Graph-Based Traversal: Relationship-aware search
   - Finds related memories via knowledge graph
   - Good for conceptual/thematic queries
   - Weight: 0.3 (30%)

3. TF-IDF Semantic Search: Distributional similarity
   - Captures semantic relationships
   - Good for natural language queries
   - Weight: 0.3 (30%)

4. Optional Embedding Search: Dense vector similarity
   - Best semantic understanding (if available)
   - Requires sentence-transformers
   - Can replace or augment TF-IDF

Fusion Methods:
- Reciprocal Rank Fusion (RRF): Rank-based combination
- Weighted Score Fusion: Normalized score combination
- Hybrid: Adaptive based on query characteristics

Performance Target: <50ms for 1K memories (hybrid mode)

Usage:
    hybrid = HybridSearchEngine(memory_store, bm25_engine, graph_engine)
    results = hybrid.search(
        query="authentication bug",
        method="weighted",
        weights={'bm25': 0.4, 'graph': 0.3, 'semantic': 0.3}
    )
"""

import time
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Optional, Any, Set
from pathlib import Path
import sqlite3

# Import local modules
from search_engine_v2 import BM25SearchEngine
from query_optimizer import QueryOptimizer
from cache_manager import CacheManager


class HybridSearchEngine:
    """
    Hybrid search combining BM25, graph traversal, and semantic search.

    Provides flexible retrieval strategies based on query type and
    available resources.
    """

    def __init__(
        self,
        db_path: Path,
        bm25_engine: Optional[BM25SearchEngine] = None,
        query_optimizer: Optional[QueryOptimizer] = None,
        cache_manager: Optional[CacheManager] = None,
        enable_cache: bool = True
    ):
        """
        Initialize hybrid search engine.

        Args:
            db_path: Path to memory database
            bm25_engine: Pre-configured BM25 engine (will create if None)
            query_optimizer: Query optimizer instance (will create if None)
            cache_manager: Cache manager instance (will create if None)
            enable_cache: Enable result caching
        """
        self.db_path = db_path

        # Initialize components
        self.bm25 = bm25_engine or BM25SearchEngine()
        self.optimizer = query_optimizer or QueryOptimizer()
        self.cache = cache_manager if enable_cache else None

        # Graph engine (lazy load to avoid circular dependencies)
        self._graph_engine = None

        # TF-IDF fallback (from memory_store_v2)
        self._tfidf_vectorizer = None
        self._tfidf_vectors = None
        self._memory_ids = []

        # Performance tracking
        self.last_search_time = 0.0
        self.last_fusion_time = 0.0

        # Load index
        self._load_index()

    def _load_index(self):
        """
        Load documents from database and build search indexes.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Fetch all memories
        cursor.execute('''
            SELECT id, content, summary, tags
            FROM memories
            ORDER BY id
        ''')

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return

        # Build BM25 index
        doc_ids = [row[0] for row in rows]
        documents = []
        vocabulary = set()

        for row in rows:
            # Combine content + summary + tags for indexing
            text_parts = [row[1]]  # content

            if row[2]:  # summary
                text_parts.append(row[2])

            if row[3]:  # tags (JSON)
                import json
                try:
                    tags = json.loads(row[3])
                    text_parts.extend(tags)
                except:
                    pass

            doc_text = ' '.join(text_parts)
            documents.append(doc_text)

            # Build vocabulary for spell correction
            tokens = self.bm25._tokenize(doc_text)
            vocabulary.update(tokens)

        # Index with BM25
        self.bm25.index_documents(documents, doc_ids)
        self._memory_ids = doc_ids

        # Initialize optimizer with vocabulary
        self.optimizer.vocabulary = vocabulary

        # Build co-occurrence for query expansion
        tokenized_docs = [self.bm25._tokenize(doc) for doc in documents]
        self.optimizer.build_cooccurrence_matrix(tokenized_docs)

        # Try to load TF-IDF (optional semantic search)
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            self._tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            self._tfidf_vectors = self._tfidf_vectorizer.fit_transform(documents)

        except ImportError:
            # sklearn not available - skip semantic search
            pass

    def _load_graph_engine(self):
        """Lazy load graph engine to avoid circular imports."""
        if self._graph_engine is None:
            try:
                from graph_engine import GraphEngine
                self._graph_engine = GraphEngine(self.db_path)
            except ImportError:
                # Graph engine not available
                pass
        return self._graph_engine

    def search_bm25(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.0
    ) -> List[Tuple[int, float]]:
        """
        Search using BM25 keyword matching.

        Args:
            query: Search query
            limit: Maximum results
            score_threshold: Minimum score threshold

        Returns:
            List of (memory_id, score) tuples
        """
        # Optimize query
        optimized = self.optimizer.optimize(
            query,
            enable_spell_correction=True,
            enable_expansion=False  # Expansion can hurt precision
        )

        # Search with BM25
        results = self.bm25.search(optimized, limit, score_threshold)

        return results

    def search_semantic(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.05
    ) -> List[Tuple[int, float]]:
        """
        Search using TF-IDF semantic similarity.

        Args:
            query: Search query
            limit: Maximum results
            score_threshold: Minimum similarity threshold

        Returns:
            List of (memory_id, score) tuples
        """
        if self._tfidf_vectorizer is None or self._tfidf_vectors is None:
            return []

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            # Vectorize query
            query_vec = self._tfidf_vectorizer.transform([query])

            # Calculate similarities
            similarities = cosine_similarity(query_vec, self._tfidf_vectors).flatten()

            # Get top results above threshold
            results = []
            for idx, score in enumerate(similarities):
                if score >= score_threshold:
                    memory_id = self._memory_ids[idx]
                    results.append((memory_id, float(score)))

            # Sort by score and limit
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

        except Exception as e:
            # Fallback gracefully
            return []

    def search_graph(
        self,
        query: str,
        limit: int = 10,
        max_depth: int = 2
    ) -> List[Tuple[int, float]]:
        """
        Search using graph traversal from initial matches.

        Strategy:
        1. Get seed memories from BM25
        2. Traverse graph to find related memories
        3. Score by distance from seed nodes

        Args:
            query: Search query
            limit: Maximum results
            max_depth: Maximum graph traversal depth

        Returns:
            List of (memory_id, score) tuples
        """
        graph = self._load_graph_engine()
        if graph is None:
            return []

        # Get seed memories from BM25
        seed_results = self.search_bm25(query, limit=5)
        if not seed_results:
            return []

        seed_ids = [mem_id for mem_id, _ in seed_results]

        # Traverse graph from seed nodes
        visited = set(seed_ids)
        results = []

        # BFS traversal
        queue = [(mem_id, 1.0, 0) for mem_id in seed_ids]  # (id, score, depth)

        while queue and len(results) < limit:
            current_id, current_score, depth = queue.pop(0)

            if depth > max_depth:
                continue

            # Add to results
            if current_id not in [r[0] for r in results]:
                results.append((current_id, current_score))

            # Get related memories from graph
            try:
                related = graph.get_related_memories(current_id, limit=5)

                for rel_id, similarity in related:
                    if rel_id not in visited:
                        visited.add(rel_id)
                        # Decay score by depth
                        new_score = current_score * similarity * (0.7 ** depth)
                        queue.append((rel_id, new_score, depth + 1))

            except:
                # Graph operation failed - skip
                continue

        return results[:limit]

    def _normalize_scores(
        self,
        results: List[Tuple[int, float]]
    ) -> List[Tuple[int, float]]:
        """
        Normalize scores to [0, 1] range using min-max normalization.

        Args:
            results: List of (id, score) tuples

        Returns:
            Normalized results
        """
        if not results:
            return []

        scores = [score for _, score in results]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            # All scores equal - return uniform scores
            return [(id, 1.0) for id, _ in results]

        normalized = []
        for mem_id, score in results:
            norm_score = (score - min_score) / (max_score - min_score)
            normalized.append((mem_id, norm_score))

        return normalized

    def _reciprocal_rank_fusion(
        self,
        results_list: List[List[Tuple[int, float]]],
        k: int = 60
    ) -> List[Tuple[int, float]]:
        """
        Combine multiple result lists using Reciprocal Rank Fusion.

        RRF formula: score(d) = Σ 1 / (k + rank(d))

        RRF is rank-based and doesn't depend on score magnitudes,
        making it robust to different scoring scales.

        Args:
            results_list: List of result lists from different methods
            k: RRF constant (default: 60, standard value)

        Returns:
            Fused results sorted by RRF score
        """
        # Build rank maps for each method
        rrf_scores = defaultdict(float)

        for results in results_list:
            for rank, (mem_id, _) in enumerate(results, start=1):
                rrf_scores[mem_id] += 1.0 / (k + rank)

        # Convert to sorted list
        fused = [(mem_id, score) for mem_id, score in rrf_scores.items()]
        fused.sort(key=lambda x: x[1], reverse=True)

        return fused

    def _weighted_fusion(
        self,
        results_dict: Dict[str, List[Tuple[int, float]]],
        weights: Dict[str, float]
    ) -> List[Tuple[int, float]]:
        """
        Combine results using weighted score fusion.

        Normalizes scores from each method then combines with weights.

        Args:
            results_dict: Dictionary mapping method name to results
            weights: Dictionary mapping method name to weight

        Returns:
            Fused results sorted by combined score
        """
        # Normalize scores for each method
        normalized = {}
        for method, results in results_dict.items():
            normalized[method] = self._normalize_scores(results)

        # Combine with weights
        combined_scores = defaultdict(float)
        max_weight_sum = defaultdict(float)  # Track possible max score per doc

        for method, results in normalized.items():
            weight = weights.get(method, 0.0)

            for mem_id, score in results:
                combined_scores[mem_id] += weight * score
                max_weight_sum[mem_id] += weight

        # Normalize by actual weights (some docs may not appear in all methods)
        fused = []
        for mem_id, score in combined_scores.items():
            normalized_score = score / max_weight_sum[mem_id] if max_weight_sum[mem_id] > 0 else 0
            fused.append((mem_id, normalized_score))

        fused.sort(key=lambda x: x[1], reverse=True)

        return fused

    def search(
        self,
        query: str,
        limit: int = 10,
        method: str = "hybrid",
        weights: Optional[Dict[str, float]] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search with multiple retrieval methods.

        Args:
            query: Search query
            limit: Maximum results
            method: Fusion method ("hybrid", "weighted", "rrf", "bm25", "semantic", "graph")
            weights: Custom weights for weighted fusion (default: balanced)
            use_cache: Use cache for results

        Returns:
            List of memory dictionaries with scores and match details
        """
        start_time = time.time()

        # Check cache
        if use_cache and self.cache:
            cached = self.cache.get(query, limit=limit, method=method)
            if cached is not None:
                self.last_search_time = time.time() - start_time
                return cached

        # Default weights
        if weights is None:
            weights = {
                'bm25': 0.4,
                'semantic': 0.3,
                'graph': 0.3
            }

        # Single method search
        if method == "bm25":
            raw_results = self.search_bm25(query, limit)
        elif method == "semantic":
            raw_results = self.search_semantic(query, limit)
        elif method == "graph":
            raw_results = self.search_graph(query, limit)

        # Multi-method fusion
        else:
            fusion_start = time.time()

            # Get results from all methods
            results_dict = {}

            if weights.get('bm25', 0) > 0:
                results_dict['bm25'] = self.search_bm25(query, limit=limit*2)

            if weights.get('semantic', 0) > 0:
                results_dict['semantic'] = self.search_semantic(query, limit=limit*2)

            if weights.get('graph', 0) > 0:
                results_dict['graph'] = self.search_graph(query, limit=limit*2)

            # Fusion
            if method == "rrf":
                raw_results = self._reciprocal_rank_fusion(list(results_dict.values()))
            else:  # weighted or hybrid
                raw_results = self._weighted_fusion(results_dict, weights)

            self.last_fusion_time = time.time() - fusion_start

        # Limit results
        raw_results = raw_results[:limit]

        # Fetch full memory details
        results = self._fetch_memory_details(raw_results, query)

        # Cache results
        if use_cache and self.cache:
            self.cache.put(query, results, limit=limit, method=method)

        self.last_search_time = time.time() - start_time

        return results

    def _fetch_memory_details(
        self,
        raw_results: List[Tuple[int, float]],
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch full memory details for result IDs.

        Args:
            raw_results: List of (memory_id, score) tuples
            query: Original query (for context)

        Returns:
            List of memory dictionaries with full details
        """
        if not raw_results:
            return []

        memory_ids = [mem_id for mem_id, _ in raw_results]
        id_to_score = {mem_id: score for mem_id, score in raw_results}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Fetch memories
        placeholders = ','.join(['?'] * len(memory_ids))
        cursor.execute(f'''
            SELECT id, content, summary, project_path, project_name, tags,
                   category, parent_id, tree_path, depth, memory_type,
                   importance, created_at, cluster_id, last_accessed, access_count
            FROM memories
            WHERE id IN ({placeholders})
        ''', memory_ids)

        rows = cursor.fetchall()
        conn.close()

        # Build result dictionaries
        results = []
        for row in rows:
            import json

            mem_id = row[0]
            results.append({
                'id': mem_id,
                'content': row[1],
                'summary': row[2],
                'project_path': row[3],
                'project_name': row[4],
                'tags': json.loads(row[5]) if row[5] else [],
                'category': row[6],
                'parent_id': row[7],
                'tree_path': row[8],
                'depth': row[9],
                'memory_type': row[10],
                'importance': row[11],
                'created_at': row[12],
                'cluster_id': row[13],
                'last_accessed': row[14],
                'access_count': row[15],
                'score': id_to_score.get(mem_id, 0.0),
                'match_type': 'hybrid'
            })

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get hybrid search statistics.

        Returns:
            Dictionary with performance stats
        """
        stats = {
            'bm25': self.bm25.get_stats(),
            'optimizer': self.optimizer.get_stats(),
            'last_search_time_ms': self.last_search_time * 1000,
            'last_fusion_time_ms': self.last_fusion_time * 1000,
            'tfidf_available': self._tfidf_vectorizer is not None,
            'graph_available': self._graph_engine is not None
        }

        if self.cache:
            stats['cache'] = self.cache.get_stats()

        return stats


# CLI interface for testing
if __name__ == "__main__":
    import sys
    from pathlib import Path

    print("Hybrid Search Engine - Demo")
    print("=" * 60)

    # Use test database or default
    db_path = Path.home() / ".claude-memory" / "memory.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Please run memory_store_v2.py to create database first.")
        sys.exit(1)

    # Initialize hybrid search
    print(f"\nInitializing hybrid search engine...")
    print(f"Database: {db_path}")

    hybrid = HybridSearchEngine(db_path, enable_cache=True)

    stats = hybrid.get_stats()
    print(f"\n✓ Indexed {stats['bm25']['num_documents']} memories")
    print(f"  Vocabulary: {stats['bm25']['vocabulary_size']} terms")
    print(f"  TF-IDF: {'Available' if stats['tfidf_available'] else 'Not available'}")
    print(f"  Graph: {'Available' if stats['graph_available'] else 'Not available'}")

    # Test search
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
    else:
        query = "python web development"

    print("\n" + "=" * 60)
    print(f"Search Query: '{query}'")
    print("=" * 60)

    # Test different methods
    methods = ["bm25", "hybrid"]

    for method in methods:
        print(f"\nMethod: {method.upper()}")
        results = hybrid.search(query, limit=5, method=method)

        print(f"  Found {len(results)} results in {hybrid.last_search_time*1000:.2f}ms")

        for i, mem in enumerate(results, 1):
            print(f"\n  [{i}] Score: {mem['score']:.3f} | ID: {mem['id']}")
            if mem.get('category'):
                print(f"      Category: {mem['category']}")
            if mem.get('tags'):
                print(f"      Tags: {', '.join(mem['tags'][:3])}")
            print(f"      Content: {mem['content'][:100]}...")

    # Display final stats
    print("\n" + "=" * 60)
    print("Performance Summary:")
    print("=" * 60)

    final_stats = hybrid.get_stats()
    print(f"  Last search time: {final_stats['last_search_time_ms']:.2f}ms")
    print(f"  Last fusion time: {final_stats['last_fusion_time_ms']:.2f}ms")
    print(f"  Target: <50ms for 1K memories {'✓' if final_stats['last_search_time_ms'] < 50 else '✗'}")

    if 'cache' in final_stats:
        cache_stats = final_stats['cache']
        print(f"\n  Cache hit rate: {cache_stats['hit_rate']*100:.1f}%")
        print(f"  Cache size: {cache_stats['current_size']}/{cache_stats['max_size']}")
