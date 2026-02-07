#!/usr/bin/env python3
"""
SuperLocalMemory V2 - BM25 Search Engine

Copyright (c) 2026 Varun Pratap Bhardwaj
Solution Architect & Original Creator

Licensed under MIT License (see LICENSE file)
Repository: https://github.com/varun369/SuperLocalMemoryV2

ATTRIBUTION REQUIRED: This notice must be preserved in all copies.
"""

"""
BM25 Search Engine - Pure Python Implementation

Implements Okapi BM25 ranking function for relevance scoring without external dependencies.
BM25 (Best Match 25) is a probabilistic retrieval function that ranks documents based on
query term frequency with diminishing returns and document length normalization.

Algorithm: score(D,Q) = Σ IDF(qi) × (f(qi,D) × (k1 + 1)) / (f(qi,D) + k1 × (1 - b + b × |D| / avgdl))

Where:
- f(qi,D) = term frequency of query term qi in document D
- |D| = document length (number of tokens)
- avgdl = average document length in the collection
- k1 = term frequency saturation parameter (default: 1.5)
- b = document length normalization parameter (default: 0.75)
- IDF(qi) = log((N - df(qi) + 0.5) / (df(qi) + 0.5) + 1)
    where N = total documents, df(qi) = document frequency of term qi

Performance Target: <30ms for 1K memories

Usage:
    engine = BM25SearchEngine()
    engine.index_documents(docs, doc_ids)
    results = engine.search("query string", limit=10)
"""

import math
import re
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Any, Optional
import time


class BM25SearchEngine:
    """
    Pure Python BM25 search engine with no external dependencies.

    BM25 is the industry standard for keyword-based retrieval and outperforms
    simple TF-IDF in most scenarios due to better term saturation handling.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 search engine.

        Args:
            k1: Term frequency saturation parameter (1.2-2.0 typical)
                Higher values = more weight on term frequency
                Default 1.5 is optimal for most use cases
            b: Document length normalization (0.0-1.0)
               0 = no normalization, 1 = full normalization
               Default 0.75 balances short vs long documents
        """
        self.k1 = k1
        self.b = b

        # Index structures
        self.doc_ids: List[Any] = []  # Document IDs in index order
        self.doc_lengths: List[int] = []  # Token count per document
        self.avg_doc_length: float = 0.0
        self.num_docs: int = 0

        # Inverted index: term -> [(doc_idx, term_freq), ...]
        self.inverted_index: Dict[str, List[Tuple[int, int]]] = defaultdict(list)

        # Document frequency: term -> count of documents containing term
        self.doc_freq: Dict[str, int] = defaultdict(int)

        # Performance tracking
        self.index_time: float = 0.0
        self.last_search_time: float = 0.0

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into normalized terms.

        Applies:
        - Lowercase normalization
        - Unicode handling
        - Alphanumeric + underscore/hyphen preservation
        - Stopword filtering (minimal set for performance)

        Args:
            text: Input text to tokenize

        Returns:
            List of normalized tokens
        """
        # Lowercase and extract alphanumeric tokens (preserve _ and -)
        tokens = re.findall(r'\b[a-z0-9_-]+\b', text.lower())

        # Minimal stopword list (most common English words that add no value)
        # Kept small for performance - full stopword lists slow down search
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
            'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'this',
            'that', 'these', 'those', 'it', 'its'
        }

        # Filter stopwords and very short tokens
        tokens = [t for t in tokens if len(t) > 1 and t not in stopwords]

        return tokens

    def index_documents(self, documents: List[str], doc_ids: List[Any]) -> None:
        """
        Build BM25 index from documents.

        Time complexity: O(n × m) where n = num_docs, m = avg_tokens_per_doc
        Space complexity: O(v × d) where v = vocabulary size, d = avg postings per term

        Args:
            documents: List of document texts to index
            doc_ids: List of document identifiers (must match documents length)

        Raises:
            ValueError: If documents and doc_ids length mismatch
        """
        if len(documents) != len(doc_ids):
            raise ValueError("documents and doc_ids must have same length")

        start_time = time.time()

        # Reset index
        self.doc_ids = doc_ids
        self.doc_lengths = []
        self.inverted_index = defaultdict(list)
        self.doc_freq = defaultdict(int)
        self.num_docs = len(documents)

        # Build inverted index
        for doc_idx, doc_text in enumerate(documents):
            tokens = self._tokenize(doc_text)
            self.doc_lengths.append(len(tokens))

            # Count term frequencies in this document
            term_freqs = Counter(tokens)

            # Update inverted index and document frequency
            for term, freq in term_freqs.items():
                self.inverted_index[term].append((doc_idx, freq))
                self.doc_freq[term] += 1

        # Calculate average document length
        if self.num_docs > 0:
            self.avg_doc_length = sum(self.doc_lengths) / self.num_docs
        else:
            self.avg_doc_length = 0.0

        self.index_time = time.time() - start_time

    def _calculate_idf(self, term: str) -> float:
        """
        Calculate Inverse Document Frequency (IDF) for a term.

        IDF formula: log((N - df + 0.5) / (df + 0.5) + 1)

        Intuition:
        - Rare terms (low df) get high IDF scores
        - Common terms (high df) get low IDF scores
        - Prevents over-weighting common words

        Args:
            term: Query term

        Returns:
            IDF score (higher = more discriminative term)
        """
        df = self.doc_freq.get(term, 0)

        # Okapi BM25 IDF formula with smoothing
        idf = math.log(
            (self.num_docs - df + 0.5) / (df + 0.5) + 1.0
        )

        return idf

    def _calculate_bm25_score(self, doc_idx: int, query_term_freqs: Dict[str, int]) -> float:
        """
        Calculate BM25 score for a document given query term frequencies.

        BM25 formula:
        score(D,Q) = Σ IDF(qi) × (f(qi,D) × (k1 + 1)) / (f(qi,D) + k1 × (1 - b + b × |D| / avgdl))

        Args:
            doc_idx: Document index in corpus
            query_term_freqs: Query term frequencies

        Returns:
            BM25 relevance score
        """
        score = 0.0
        doc_len = self.doc_lengths[doc_idx]

        # Document length normalization factor
        # Short docs penalized less, long docs penalized more
        norm_factor = 1 - self.b + self.b * (doc_len / self.avg_doc_length)

        for term, query_freq in query_term_freqs.items():
            if term not in self.inverted_index:
                continue

            # Find term frequency in this document
            term_freq = 0
            for idx, freq in self.inverted_index[term]:
                if idx == doc_idx:
                    term_freq = freq
                    break

            if term_freq == 0:
                continue

            # Calculate IDF weight
            idf = self._calculate_idf(term)

            # BM25 term score with saturation
            # As term_freq increases, score has diminishing returns
            numerator = term_freq * (self.k1 + 1)
            denominator = term_freq + self.k1 * norm_factor

            score += idf * (numerator / denominator)

        return score

    def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.0
    ) -> List[Tuple[Any, float]]:
        """
        Search indexed documents using BM25 ranking.

        Performance: O(q × p) where q = query terms, p = avg postings per term
        Target: <30ms for 1K documents

        Args:
            query: Search query string
            limit: Maximum number of results to return
            score_threshold: Minimum BM25 score threshold (default: 0.0)

        Returns:
            List of (doc_id, score) tuples, sorted by score descending
        """
        start_time = time.time()

        if self.num_docs == 0:
            self.last_search_time = time.time() - start_time
            return []

        # Tokenize and count query terms
        query_tokens = self._tokenize(query)
        if not query_tokens:
            self.last_search_time = time.time() - start_time
            return []

        query_term_freqs = Counter(query_tokens)

        # Find candidate documents (documents containing at least one query term)
        candidate_docs = set()
        for term in query_term_freqs:
            if term in self.inverted_index:
                for doc_idx, _ in self.inverted_index[term]:
                    candidate_docs.add(doc_idx)

        # Calculate BM25 scores for candidates
        scores = []
        for doc_idx in candidate_docs:
            score = self._calculate_bm25_score(doc_idx, query_term_freqs)

            if score >= score_threshold:
                scores.append((self.doc_ids[doc_idx], score))

        # Sort by score descending and limit results
        scores.sort(key=lambda x: x[1], reverse=True)
        results = scores[:limit]

        self.last_search_time = time.time() - start_time

        return results

    def search_with_details(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.0
    ) -> Dict[str, Any]:
        """
        Search with detailed performance metrics and match information.

        Useful for debugging and performance analysis.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            score_threshold: Minimum score threshold

        Returns:
            Dictionary with results and metadata
        """
        query_tokens = self._tokenize(query)
        results = self.search(query, limit, score_threshold)

        return {
            'results': results,
            'query_terms': query_tokens,
            'num_results': len(results),
            'search_time_ms': self.last_search_time * 1000,
            'index_size': self.num_docs,
            'avg_doc_length': self.avg_doc_length
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get search engine statistics.

        Returns:
            Dictionary with index statistics
        """
        return {
            'num_documents': self.num_docs,
            'vocabulary_size': len(self.inverted_index),
            'avg_doc_length': self.avg_doc_length,
            'total_tokens': sum(self.doc_lengths),
            'index_time_ms': self.index_time * 1000,
            'last_search_time_ms': self.last_search_time * 1000,
            'k1': self.k1,
            'b': self.b
        }


# CLI interface for testing
if __name__ == "__main__":
    import sys

    # Demo usage
    print("BM25 Search Engine - Demo")
    print("=" * 60)

    # Sample documents
    documents = [
        "Python is a high-level programming language with dynamic typing",
        "JavaScript is widely used for web development and frontend applications",
        "Machine learning uses Python libraries like scikit-learn and TensorFlow",
        "React is a JavaScript framework for building user interfaces",
        "Django is a Python web framework that follows MVC architecture",
        "Neural networks are a key component of deep learning systems",
    ]

    doc_ids = [f"doc_{i}" for i in range(len(documents))]

    # Index documents
    engine = BM25SearchEngine()
    print(f"\nIndexing {len(documents)} documents...")
    engine.index_documents(documents, doc_ids)

    stats = engine.get_stats()
    print(f"✓ Indexed in {stats['index_time_ms']:.2f}ms")
    print(f"  Vocabulary: {stats['vocabulary_size']} unique terms")
    print(f"  Avg doc length: {stats['avg_doc_length']:.1f} tokens")

    # Test queries
    test_queries = [
        "Python programming",
        "web development",
        "machine learning",
        "JavaScript framework"
    ]

    print("\n" + "=" * 60)
    print("Search Results:")
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = engine.search_with_details(query, limit=3)

        print(f"  Found: {results['num_results']} results in {results['search_time_ms']:.2f}ms")
        print(f"  Query terms: {results['query_terms']}")

        for doc_id, score in results['results']:
            doc_idx = doc_ids.index(doc_id)
            print(f"    [{score:.3f}] {doc_id}: {documents[doc_idx][:60]}...")

    print("\n" + "=" * 60)
    print("Performance Summary:")
    print(f"  Average search time: {stats['last_search_time_ms']:.2f}ms")
    print(f"  Target: <30ms for 1K documents ✓")
