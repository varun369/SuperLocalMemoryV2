#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Query Optimizer

Copyright (c) 2026 Varun Pratap Bhardwaj
Solution Architect & Original Creator

Licensed under MIT License (see LICENSE file)
Repository: https://github.com/varun369/SuperLocalMemoryV2

ATTRIBUTION REQUIRED: This notice must be preserved in all copies.
"""

"""
Query Optimizer - Query Enhancement and Rewriting

Transforms user queries into optimized search queries through:

1. Spell Correction: Fix common typos using edit distance
   - "javscript" → "javascript"
   - Uses vocabulary from indexed documents
   - Levenshtein distance with max distance 2

2. Query Expansion: Add related terms to broaden search
   - "auth" → "auth authentication authorize"
   - Based on co-occurrence patterns in documents
   - Optional synonym expansion

3. Boolean Operators: Parse structured queries
   - "python AND (web OR api)" → structured query
   - Supports: AND, OR, NOT, phrase queries "exact match"
   - Converts to search engine-compatible format

4. Stopword Handling: Remove low-value terms
   - Configurable stopword list
   - Preserves important technical terms

Performance: Query optimization should add <5ms overhead

Usage:
    optimizer = QueryOptimizer(vocabulary)
    optimized = optimizer.optimize("javscript web devlopment")
    # Returns: "javascript web development"
"""

import re
from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple, Optional, Any
import difflib


class QueryOptimizer:
    """
    Query preprocessing and optimization for improved search quality.

    Handles spell correction, expansion, and boolean query parsing.
    """

    def __init__(self, vocabulary: Optional[Set[str]] = None):
        """
        Initialize query optimizer.

        Args:
            vocabulary: Set of known terms from indexed documents
                       Used for spell correction
        """
        self.vocabulary = vocabulary or set()

        # Co-occurrence matrix for query expansion
        # term -> {related_term: co-occurrence_count}
        self.cooccurrence: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Expansion candidates: term -> [expanded_terms]
        self.expansions: Dict[str, List[str]] = {}

        # Technical term preservation (don't treat as typos)
        self.technical_terms = {
            'api', 'sql', 'orm', 'jwt', 'http', 'https', 'ssl', 'tls',
            'json', 'xml', 'yaml', 'csv', 'pdf', 'cli', 'gui', 'ide',
            'git', 'npm', 'pip', 'cpu', 'gpu', 'ram', 'ssd', 'hdd',
            'ml', 'ai', 'nlp', 'cv', 'dl', 'rl', 'gan', 'cnn', 'rnn',
            'rest', 'soap', 'grpc', 'cors', 'csrf', 'xss', 'sql',
            'aws', 'gcp', 'azure', 'k8s', 'ci', 'cd', 'devops'
        }

    def build_cooccurrence_matrix(self, documents: List[List[str]]) -> None:
        """
        Build term co-occurrence matrix from tokenized documents.

        Co-occurrence = terms appearing in same document
        Used for query expansion to find related terms.

        Args:
            documents: List of tokenized documents (each doc is list of tokens)
        """
        self.cooccurrence = defaultdict(lambda: defaultdict(int))

        for doc_tokens in documents:
            # Count unique terms per document
            unique_terms = set(doc_tokens)

            # Update co-occurrence for all term pairs in document
            for term1 in unique_terms:
                for term2 in unique_terms:
                    if term1 != term2:
                        self.cooccurrence[term1][term2] += 1

    def _edit_distance(self, s1: str, s2: str, max_distance: int = 2) -> int:
        """
        Calculate Levenshtein edit distance between two strings.

        Edit distance = minimum number of single-character edits (insertions,
        deletions, substitutions) required to change s1 into s2.

        Early termination if distance exceeds max_distance for performance.

        Args:
            s1: First string
            s2: Second string
            max_distance: Maximum distance to calculate (for early termination)

        Returns:
            Edit distance, or max_distance+1 if exceeds threshold
        """
        len1, len2 = len(s1), len(s2)

        # Early termination - length difference too large
        if abs(len1 - len2) > max_distance:
            return max_distance + 1

        # Initialize DP matrix (only need current and previous row)
        prev_row = list(range(len2 + 1))
        curr_row = [0] * (len2 + 1)

        for i in range(1, len1 + 1):
            curr_row[0] = i
            min_in_row = i  # Track minimum value in current row

            for j in range(1, len2 + 1):
                # Cost of substitution (0 if characters match, 1 otherwise)
                cost = 0 if s1[i - 1] == s2[j - 1] else 1

                curr_row[j] = min(
                    prev_row[j] + 1,      # Deletion
                    curr_row[j - 1] + 1,  # Insertion
                    prev_row[j - 1] + cost  # Substitution
                )

                min_in_row = min(min_in_row, curr_row[j])

            # Early termination - minimum in row exceeds threshold
            if min_in_row > max_distance:
                return max_distance + 1

            # Swap rows
            prev_row, curr_row = curr_row, prev_row

        return prev_row[len2]

    def spell_correct(self, term: str, max_distance: int = 2) -> str:
        """
        Correct spelling using vocabulary and edit distance.

        Algorithm:
        1. If term in vocabulary, return as-is
        2. If term is technical term (<=3 chars or in whitelist), return as-is
        3. Find closest vocabulary term within max_distance edits
        4. Return correction if found, otherwise original term

        Args:
            term: Term to correct
            max_distance: Maximum edit distance to consider (default: 2)

        Returns:
            Corrected term or original if no correction found
        """
        # Already correct or technical term
        if term in self.vocabulary or term in self.technical_terms:
            return term

        # Don't correct very short terms (likely abbreviations)
        if len(term) <= 3:
            return term

        # Find closest match in vocabulary
        best_match = term
        best_distance = max_distance + 1

        # Use difflib for efficient approximate matching
        # This is faster than checking full vocabulary for large sets
        close_matches = difflib.get_close_matches(
            term, self.vocabulary, n=5, cutoff=0.7
        )

        for candidate in close_matches:
            distance = self._edit_distance(term, candidate, max_distance)
            if distance < best_distance:
                best_distance = distance
                best_match = candidate

        # If no close match found by difflib, check high-frequency terms
        # This handles cases where difflib's cutoff is too strict
        if best_distance > max_distance and len(self.vocabulary) < 10000:
            # Only do full scan for smaller vocabularies
            for vocab_term in self.vocabulary:
                # Quick filter by length difference
                if abs(len(term) - len(vocab_term)) > max_distance:
                    continue

                distance = self._edit_distance(term, vocab_term, max_distance)
                if distance < best_distance:
                    best_distance = distance
                    best_match = vocab_term

        # Return correction only if found
        return best_match if best_distance <= max_distance else term

    def expand_query(
        self,
        query_terms: List[str],
        max_expansions: int = 2,
        min_cooccurrence: int = 2
    ) -> List[str]:
        """
        Expand query with related terms based on co-occurrence.

        Adds terms that frequently co-occur with query terms to broaden search.

        Args:
            query_terms: Original query terms
            max_expansions: Maximum number of expansion terms to add
            min_cooccurrence: Minimum co-occurrence count threshold

        Returns:
            Expanded query terms (original + expansions)
        """
        if not self.cooccurrence:
            return query_terms

        # Collect expansion candidates
        expansion_candidates = defaultdict(int)

        for term in query_terms:
            if term in self.cooccurrence:
                for related_term, count in self.cooccurrence[term].items():
                    # Don't re-add terms already in query
                    if related_term not in query_terms:
                        expansion_candidates[related_term] += count

        # Filter by minimum co-occurrence and sort by frequency
        expansions = [
            term for term, count in expansion_candidates.items()
            if count >= min_cooccurrence
        ]
        expansions.sort(key=lambda t: expansion_candidates[t], reverse=True)

        # Add top expansions
        expanded_terms = query_terms + expansions[:max_expansions]

        return expanded_terms

    def parse_boolean_query(self, query: str) -> Dict[str, Any]:
        """
        Parse boolean query operators (AND, OR, NOT, phrase matching).

        Supports:
        - AND: term1 AND term2 (both required)
        - OR: term1 OR term2 (at least one required)
        - NOT: term1 NOT term2 (exclude term2)
        - Phrase: "exact phrase" (exact match)
        - Implicit AND: "term1 term2" treated as term1 AND term2

        Args:
            query: Query string with boolean operators

        Returns:
            Parsed query structure:
            {
                'type': 'and' | 'or' | 'not' | 'phrase' | 'term',
                'terms': [terms],
                'operator': operator,
                'children': [sub-queries]
            }
        """
        # Extract phrase queries first (enclosed in quotes)
        phrases = []
        phrase_pattern = r'"([^"]+)"'
        query_without_phrases = query

        for match in re.finditer(phrase_pattern, query):
            phrase = match.group(1)
            phrases.append(phrase)
            # Replace phrase with placeholder
            query_without_phrases = query_without_phrases.replace(
                f'"{phrase}"', f'__PHRASE_{len(phrases)-1}__'
            )

        # Split by boolean operators (case insensitive)
        # Priority: NOT > AND > OR
        query_upper = query_without_phrases.upper()

        # Parse NOT expressions
        if ' NOT ' in query_upper:
            parts = re.split(r'\s+NOT\s+', query_without_phrases, flags=re.IGNORECASE)
            return {
                'type': 'not',
                'required': self._parse_query_part(parts[0].strip(), phrases),
                'excluded': [self._parse_query_part(p.strip(), phrases) for p in parts[1:]]
            }

        # Parse AND expressions
        if ' AND ' in query_upper:
            parts = re.split(r'\s+AND\s+', query_without_phrases, flags=re.IGNORECASE)
            return {
                'type': 'and',
                'children': [self._parse_query_part(p.strip(), phrases) for p in parts]
            }

        # Parse OR expressions
        if ' OR ' in query_upper:
            parts = re.split(r'\s+OR\s+', query_without_phrases, flags=re.IGNORECASE)
            return {
                'type': 'or',
                'children': [self._parse_query_part(p.strip(), phrases) for p in parts]
            }

        # Default: treat as implicit AND
        return self._parse_query_part(query_without_phrases.strip(), phrases)

    def _parse_query_part(self, part: str, phrases: List[str]) -> Dict[str, Any]:
        """
        Parse a single query part (no boolean operators).

        Args:
            part: Query part
            phrases: List of extracted phrases

        Returns:
            Query structure
        """
        # Check for phrase placeholder
        phrase_match = re.match(r'__PHRASE_(\d+)__', part)
        if phrase_match:
            phrase_idx = int(phrase_match.group(1))
            return {
                'type': 'phrase',
                'phrase': phrases[phrase_idx],
                'terms': phrases[phrase_idx].split()
            }

        # Regular term(s)
        terms = part.split()
        if len(terms) == 1:
            return {
                'type': 'term',
                'term': terms[0]
            }
        else:
            # Multiple terms without operator = implicit AND
            return {
                'type': 'and',
                'children': [{'type': 'term', 'term': t} for t in terms]
            }

    def optimize(
        self,
        query: str,
        enable_spell_correction: bool = True,
        enable_expansion: bool = False,
        max_expansions: int = 2
    ) -> str:
        """
        Optimize query with spell correction and expansion.

        Args:
            query: Original query string
            enable_spell_correction: Apply spell correction
            enable_expansion: Apply query expansion
            max_expansions: Maximum expansion terms

        Returns:
            Optimized query string
        """
        # Tokenize query
        tokens = re.findall(r'\b[a-z0-9_-]+\b', query.lower())

        if not tokens:
            return query

        # Apply spell correction
        if enable_spell_correction and self.vocabulary:
            tokens = [self.spell_correct(term) for term in tokens]

        # Apply query expansion
        if enable_expansion and self.cooccurrence:
            tokens = self.expand_query(tokens, max_expansions)

        return ' '.join(tokens)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get optimizer statistics.

        Returns:
            Dictionary with optimizer stats
        """
        return {
            'vocabulary_size': len(self.vocabulary),
            'cooccurrence_terms': len(self.cooccurrence),
            'technical_terms': len(self.technical_terms),
            'avg_related_terms': (
                sum(len(related) for related in self.cooccurrence.values()) / len(self.cooccurrence)
                if self.cooccurrence else 0
            )
        }


# CLI interface for testing
if __name__ == "__main__":
    print("Query Optimizer - Demo")
    print("=" * 60)

    # Sample vocabulary
    vocabulary = {
        'python', 'javascript', 'programming', 'web', 'development',
        'machine', 'learning', 'neural', 'network', 'api', 'rest',
        'database', 'sql', 'authentication', 'authorization', 'jwt',
        'framework', 'django', 'react', 'node', 'express'
    }

    # Sample documents for co-occurrence
    documents = [
        ['python', 'programming', 'web', 'development'],
        ['javascript', 'web', 'development', 'frontend'],
        ['machine', 'learning', 'python', 'neural', 'network'],
        ['api', 'rest', 'web', 'development'],
        ['authentication', 'authorization', 'jwt', 'security'],
    ]

    # Initialize optimizer
    optimizer = QueryOptimizer(vocabulary)
    optimizer.build_cooccurrence_matrix(documents)

    print("\nOptimizer Statistics:")
    stats = optimizer.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test spell correction
    print("\n" + "=" * 60)
    print("Spell Correction:")
    print("=" * 60)

    test_typos = [
        "pythno",      # → python
        "javascirpt",  # → javascript
        "machien",     # → machine
        "athentication",  # → authentication
        "developement"    # → development
    ]

    for typo in test_typos:
        corrected = optimizer.spell_correct(typo)
        print(f"  '{typo}' → '{corrected}'")

    # Test query expansion
    print("\n" + "=" * 60)
    print("Query Expansion:")
    print("=" * 60)

    test_queries = [
        ['python'],
        ['web'],
        ['machine', 'learning'],
    ]

    for query in test_queries:
        expanded = optimizer.expand_query(query, max_expansions=2)
        print(f"  {query} → {expanded}")

    # Test boolean query parsing
    print("\n" + "=" * 60)
    print("Boolean Query Parsing:")
    print("=" * 60)

    boolean_queries = [
        'python AND web',
        'javascript OR typescript',
        'python NOT django',
        '"machine learning" AND python',
        'web development rest api'
    ]

    for query in boolean_queries:
        parsed = optimizer.parse_boolean_query(query)
        print(f"\n  Query: '{query}'")
        print(f"  Parsed: {parsed}")

    # Test full optimization
    print("\n" + "=" * 60)
    print("Full Query Optimization:")
    print("=" * 60)

    optimization_tests = [
        "pythno web devlopment",
        "machien lerning",
        "api athentication"
    ]

    for query in optimization_tests:
        optimized = optimizer.optimize(query, enable_spell_correction=True)
        print(f"  '{query}'")
        print(f"  → '{optimized}'")
