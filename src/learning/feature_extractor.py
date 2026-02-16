#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Feature Extractor (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Repository: https://github.com/varun369/SuperLocalMemoryV2
Author: Varun Pratap Bhardwaj (Solution Architect)

NOTICE: This software is protected by MIT License.
Attribution must be preserved in all copies or derivatives.
"""

"""
FeatureExtractor — Extracts 12-dimensional feature vectors for candidate memories.

Each memory retrieved during recall gets a feature vector that feeds into
the AdaptiveRanker. In Phase 1 (rule-based), features drive boosting weights.
In Phase 2 (ML), features become LightGBM input columns.

Feature Vector (12 dimensions):
    [0]  bm25_score          — Existing retrieval score from search results
    [1]  tfidf_score         — TF-IDF cosine similarity from search results
    [2]  tech_match          — Does memory match user's tech preferences?
    [3]  project_match       — Is memory from the current project?
    [4]  workflow_fit        — Does memory fit current workflow phase?
    [5]  source_quality      — Quality score of the source that created this memory
    [6]  importance_norm     — Normalized importance (importance / 10.0)
    [7]  recency_score       — Exponential decay based on age (180-day half-life)
    [8]  access_frequency    — How often this memory was accessed (capped at 1.0)
    [9]  pattern_confidence  — Max Beta-Binomial confidence from learned patterns
    [10] signal_count        — Number of feedback signals for this memory (v2.7.4)
    [11] avg_signal_value    — Average signal value for this memory (v2.7.4)

Design Principles:
    - All features normalized to [0.0, 1.0] range for ML compatibility
    - Graceful defaults when data is missing (0.5 = "unknown/neutral")
    - No external API calls — everything computed locally
    - Context (tech preferences, current project) set once per recall batch
    - Thread-safe: no shared mutable state after set_context()

v2.7.4: Expanded from 10 to 12 features. Auto-retrain triggered on mismatch.
"""

import logging
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("superlocalmemory.learning.feature_extractor")

# ============================================================================
# Feature Name Registry
# ============================================================================

FEATURE_NAMES = [
    'bm25_score',          # 0: Existing retrieval score (from search results)
    'tfidf_score',         # 1: TF-IDF cosine similarity (from search results)
    'tech_match',          # 2: Does memory match user's tech preferences?
    'project_match',       # 3: Is memory from the current project?
    'workflow_fit',        # 4: Does memory fit current workflow phase?
    'source_quality',      # 5: Quality score of the source that created this memory
    'importance_norm',     # 6: Normalized importance (importance / 10.0)
    'recency_score',       # 7: Exponential decay based on age
    'access_frequency',    # 8: How often this memory was accessed (capped at 1.0)
    'pattern_confidence',  # 9: Max Beta-Binomial confidence from learned patterns
    'signal_count',        # 10: Number of feedback signals for this memory (v2.7.4)
    'avg_signal_value',    # 11: Average signal value for this memory (v2.7.4)
]

NUM_FEATURES = len(FEATURE_NAMES)

# Workflow phase keywords — maps workflow phase to content signals
_WORKFLOW_PHASE_KEYWORDS = {
    'planning': [
        'architecture', 'design', 'plan', 'roadmap', 'decision',
        'approach', 'strategy', 'requirement', 'spec', 'rfc',
    ],
    'coding': [
        'implement', 'function', 'class', 'method', 'api',
        'code', 'module', 'refactor', 'pattern', 'library',
    ],
    'testing': [
        'test', 'assert', 'mock', 'fixture', 'coverage',
        'pytest', 'jest', 'spec', 'validation', 'regression',
    ],
    'debugging': [
        'bug', 'error', 'fix', 'issue', 'traceback',
        'debug', 'crash', 'exception', 'stack', 'log',
    ],
    'deployment': [
        'deploy', 'docker', 'kubernetes', 'ci/cd', 'pipeline',
        'release', 'production', 'staging', 'env', 'config',
    ],
    'review': [
        'review', 'pr', 'merge', 'feedback', 'comment',
        'approve', 'change', 'diff', 'suggestion', 'lint',
    ],
}

# Half-life for recency decay (in days)
_RECENCY_HALF_LIFE_DAYS = 180.0

# Maximum access count before capping to 1.0
_MAX_ACCESS_COUNT = 10


class FeatureExtractor:
    """
    Extracts 12-dimensional feature vectors for candidate memories.

    Usage:
        extractor = FeatureExtractor()
        extractor.set_context(
            source_scores={'claude-desktop': 0.8, 'cursor': 0.6},
            tech_preferences={'python': {'confidence': 0.9}, 'react': {'confidence': 0.7}},
            current_project='SuperLocalMemoryV2',
            workflow_phase='testing',
            signal_stats={'42': {'count': 5, 'avg_value': 0.8}},
        )
        features = extractor.extract_batch(memories, query="search optimization")
        # features is List[List[float]], shape (n_memories, 12)
    """

    FEATURE_NAMES = FEATURE_NAMES

    def __init__(self):
        """Initialize FeatureExtractor with empty context."""
        self._source_scores: Dict[str, float] = {}
        self._tech_preferences: Dict[str, dict] = {}
        self._tech_keywords_lower: List[str] = []
        self._current_project: Optional[str] = None
        self._current_project_lower: Optional[str] = None
        self._workflow_phase: Optional[str] = None
        self._workflow_keywords: List[str] = []
        # Pattern confidence cache: maps lowercased pattern value -> confidence
        self._pattern_cache: Dict[str, float] = {}
        # Signal stats cache: maps str(memory_id) -> {count, avg_value} (v2.7.4)
        self._signal_stats: Dict[str, Dict[str, float]] = {}

    def set_context(
        self,
        source_scores: Optional[Dict[str, float]] = None,
        tech_preferences: Optional[Dict[str, dict]] = None,
        current_project: Optional[str] = None,
        workflow_phase: Optional[str] = None,
        pattern_confidences: Optional[Dict[str, float]] = None,
        signal_stats: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        """
        Set context for feature extraction. Called once per recall query.

        These values are expensive to compute (require DB lookups in learning_db),
        so they are set once and reused across all candidate memories in a batch.

        Args:
            source_scores: Map of source_id -> quality score (0.0-1.0).
                           From learning_db.get_source_scores().
            tech_preferences: Map of tech_name -> {confidence, evidence_count, ...}.
                              From cross_project_aggregator or pattern_learner.
            current_project: Name of the currently active project (if detected).
            workflow_phase: Current workflow phase (planning, coding, testing, etc).
            pattern_confidences: Map of lowercased pattern value -> confidence (0.0-1.0).
                                 From pattern_learner.PatternStore.get_patterns().
                                 Used for feature [9] pattern_confidence.
            signal_stats: Map of str(memory_id) -> {count: int, avg_value: float}.
                          From learning_db feedback aggregation. Used for features [10-11].
        """
        self._source_scores = source_scores or {}
        self._tech_preferences = tech_preferences or {}

        # Pre-compute lowercased tech keywords for faster matching
        self._tech_keywords_lower = [
            k.lower() for k in self._tech_preferences.keys()
        ]

        self._current_project = current_project
        self._current_project_lower = (
            current_project.lower() if current_project else None
        )

        self._workflow_phase = workflow_phase
        self._workflow_keywords = (
            _WORKFLOW_PHASE_KEYWORDS.get(workflow_phase, [])
            if workflow_phase else []
        )

        # Cache pattern confidences for feature [9]
        self._pattern_cache = pattern_confidences or {}

        # Cache signal stats for features [10-11] (v2.7.4)
        self._signal_stats = signal_stats or {}

    def extract_features(self, memory: dict, query: str) -> List[float]:
        """
        Extract 12-dimensional feature vector for a single memory.

        Args:
            memory: Memory dict from search results. Expected keys:
                    id, content, score, match_type, importance, created_at,
                    access_count, project_name, tags, created_by (optional).
            query: The recall query string.

        Returns:
            List of 12 floats in [0.0, 1.0] range, one per feature.
        """
        return [
            self._compute_bm25_score(memory),
            self._compute_tfidf_score(memory),
            self._compute_tech_match(memory),
            self._compute_project_match(memory),
            self._compute_workflow_fit(memory),
            self._compute_source_quality(memory),
            self._compute_importance_norm(memory),
            self._compute_recency_score(memory),
            self._compute_access_frequency(memory),
            self._compute_pattern_confidence(memory),
            self._compute_signal_count(memory),
            self._compute_avg_signal_value(memory),
        ]

    def extract_batch(
        self,
        memories: List[dict],
        query: str,
    ) -> List[List[float]]:
        """
        Extract feature vectors for all candidate memories.

        Args:
            memories: List of memory dicts from search results.
            query: The recall query string.

        Returns:
            List of feature vectors (List[List[float]]), shape (n, 12).
            Returns empty list if memories is empty.
        """
        if not memories:
            return []

        return [self.extract_features(m, query) for m in memories]

    # ========================================================================
    # Individual Feature Computations
    # ========================================================================

    def _compute_bm25_score(self, memory: dict) -> float:
        """
        Use 'score' field from search results for keyword-based retrieval.

        BM25/FTS5 rank scores are not naturally bounded to [0,1], so we
        apply a simple normalization. For keyword matches, score is
        typically set to 0.5 by MemoryStoreV2._row_to_dict(). For semantic
        matches, score is already in [0,1] from cosine similarity.

        We use match_type to distinguish: 'keyword' -> treat as BM25 signal,
        'semantic'/'hnsw' -> set to 0.0 (not a BM25 signal).
        """
        match_type = memory.get('match_type', '')
        if match_type == 'keyword':
            # FTS5 keyword match — normalize the rank score
            score = memory.get('score', 0.0)
            # FTS5 rank is negative (lower = better), score field is already
            # mapped to 0.5 by _row_to_dict, so use it directly
            return max(0.0, min(float(score), 1.0))
        # Not a keyword match — no BM25 signal
        return 0.0

    def _compute_tfidf_score(self, memory: dict) -> float:
        """
        Use cosine similarity score from TF-IDF semantic search.

        For semantic matches, the score field contains the cosine
        similarity (already in [0,1]). For keyword-only matches,
        this returns 0.0.
        """
        match_type = memory.get('match_type', '')
        if match_type in ('semantic', 'hnsw'):
            score = memory.get('score', 0.0)
            return max(0.0, min(float(score), 1.0))
        return 0.0

    def _compute_tech_match(self, memory: dict) -> float:
        """
        Check if memory content mentions user's preferred technologies.

        Returns:
            1.0 if strong match (2+ tech keywords found)
            0.5 if weak match (1 tech keyword found)
            0.0 if no match or no tech preferences set
        """
        if not self._tech_keywords_lower:
            return 0.5  # No preferences known — neutral

        content = memory.get('content', '')
        if not content:
            return 0.0

        content_lower = content.lower()
        tags_str = ''
        tags = memory.get('tags', [])
        if isinstance(tags, list):
            tags_str = ' '.join(t.lower() for t in tags)
        elif isinstance(tags, str):
            tags_str = tags.lower()

        searchable = content_lower + ' ' + tags_str
        match_count = 0

        for tech_kw in self._tech_keywords_lower:
            # Word-boundary check for short keywords to avoid false positives
            # e.g., "go" matching "google" — require word boundary
            if len(tech_kw) <= 3:
                if re.search(r'\b' + re.escape(tech_kw) + r'\b', searchable):
                    match_count += 1
            else:
                if tech_kw in searchable:
                    match_count += 1

        if match_count >= 2:
            return 1.0
        elif match_count == 1:
            return 0.5
        return 0.0

    def _compute_project_match(self, memory: dict) -> float:
        """
        Check if memory belongs to the currently active project.

        Returns:
            1.0 if memory's project_name matches current_project
            0.6 if no current project detected (neutral — don't penalize)
            0.3 if memory is from a different project
            0.5 if memory has no project_name (unknown)
        """
        if self._current_project_lower is None:
            # No current project context — neutral for all
            return 0.6

        memory_project = memory.get('project_name', '')
        if not memory_project:
            return 0.5  # Memory has no project — slightly neutral

        if memory_project.lower() == self._current_project_lower:
            return 1.0
        return 0.3

    def _compute_workflow_fit(self, memory: dict) -> float:
        """
        Check if memory content aligns with the current workflow phase.

        Returns:
            0.8 if strong fit (3+ keywords match)
            0.6 if moderate fit (1-2 keywords match)
            0.5 if unknown workflow phase (neutral)
            0.3 if no fit at all
        """
        if not self._workflow_keywords:
            return 0.5  # No workflow phase known — neutral

        content = memory.get('content', '')
        if not content:
            return 0.3

        content_lower = content.lower()
        match_count = sum(
            1 for kw in self._workflow_keywords
            if kw in content_lower
        )

        if match_count >= 3:
            return 0.8
        elif match_count >= 1:
            return 0.6
        return 0.3

    def _compute_source_quality(self, memory: dict) -> float:
        """
        Look up source quality from cached scores.

        Returns:
            The source's quality score if known (0.0-1.0)
            0.5 for unknown sources (neutral default)
        """
        # Try created_by first (v2.5+ provenance), then source_tool
        source_id = memory.get('created_by') or memory.get('source_tool', '')
        if not source_id:
            return 0.5  # Unknown source — neutral

        return self._source_scores.get(source_id, 0.5)

    def _compute_importance_norm(self, memory: dict) -> float:
        """
        Normalize importance to [0.0, 1.0].

        importance is stored as 1-10 integer in memory.db.
        Dividing by 10.0 gives clean normalization.
        """
        importance = memory.get('importance', 5)
        if importance is None:
            importance = 5
        try:
            importance = int(importance)
        except (ValueError, TypeError):
            importance = 5
        # Clamp to valid range before normalizing
        importance = max(1, min(importance, 10))
        return importance / 10.0

    def _compute_recency_score(self, memory: dict) -> float:
        """
        Exponential decay based on memory age.

        Formula: exp(-age_days / half_life)
        With 180-day half-life:
            - 0 days old -> 1.0
            - 30 days old -> ~0.85
            - 90 days old -> ~0.61
            - 180 days old -> ~0.37
            - 365 days old -> ~0.13

        Handles missing, None, or malformed created_at gracefully.
        """
        created_at = memory.get('created_at')
        if not created_at:
            return 0.5  # Unknown age — neutral

        try:
            # Parse the timestamp — handle multiple formats
            if isinstance(created_at, str):
                # Try ISO format first (most common in SQLite)
                created_at = created_at.replace('Z', '+00:00')
                try:
                    created_dt = datetime.fromisoformat(created_at)
                except ValueError:
                    # Fallback: try common SQLite format
                    created_dt = datetime.strptime(
                        created_at, '%Y-%m-%d %H:%M:%S'
                    )
            elif isinstance(created_at, (int, float)):
                created_dt = datetime.fromtimestamp(created_at)
            else:
                return 0.5

            # Make timezone-naive for comparison
            if created_dt.tzinfo is not None:
                created_dt = created_dt.replace(tzinfo=None)

            now = datetime.now()
            age_days = max(0, (now - created_dt).total_seconds() / 86400.0)

            # Exponential decay: e^(-age / half_life)
            score = math.exp(-age_days / _RECENCY_HALF_LIFE_DAYS)
            return max(0.0, min(score, 1.0))

        except (ValueError, TypeError, OverflowError, OSError) as e:
            logger.debug("Failed to parse created_at for recency: %s", e)
            return 0.5  # Parse failure — neutral

    def _compute_access_frequency(self, memory: dict) -> float:
        """
        Normalize access_count to [0.0, 1.0], capped at MAX_ACCESS_COUNT.

        access_count tracks how many times a memory has been recalled.
        Capping prevents frequently-accessed memories from dominating.
        """
        access_count = memory.get('access_count', 0)
        if access_count is None:
            access_count = 0
        try:
            access_count = int(access_count)
        except (ValueError, TypeError):
            access_count = 0

        return min(access_count / float(_MAX_ACCESS_COUNT), 1.0)


    def _compute_signal_count(self, memory: dict) -> float:
        """
        Number of feedback signals for this memory, normalized to [0, 1].

        Uses cached signal_stats from learning.db. Capped at 10 signals.
        Memories with more feedback signals are more "known" to the system.

        Returns:
            min(count / 10.0, 1.0) — 0.0 if no signals, 1.0 if 10+ signals
            0.0 if no signal stats available (v2.7.3 or earlier)
        """
        memory_id = str(memory.get('id', ''))
        if not memory_id or not self._signal_stats:
            return 0.0

        stats = self._signal_stats.get(memory_id, {})
        count = stats.get('count', 0)
        return min(count / 10.0, 1.0)

    def _compute_avg_signal_value(self, memory: dict) -> float:
        """
        Average signal value for this memory.

        Uses cached signal_stats from learning.db. Gives the ranker a direct
        view of whether this memory's feedback is positive (>0.5) or negative (<0.5).

        Returns:
            Average signal value (0.0-1.0), or 0.5 (neutral) if no data.
        """
        memory_id = str(memory.get('id', ''))
        if not memory_id or not self._signal_stats:
            return 0.5  # Neutral default

        stats = self._signal_stats.get(memory_id, {})
        avg = stats.get('avg_value', 0.5)
        return max(0.0, min(float(avg), 1.0))

    def _compute_pattern_confidence(self, memory: dict) -> float:
        """
        Compute max Beta-Binomial confidence from learned patterns matching this memory.

        Looks up the cached pattern_confidences (set via set_context) and checks
        if any pattern value appears in the memory's content or tags. Returns the
        maximum confidence among all matching patterns.

        Returns:
            Max confidence (0.0-1.0) from matching patterns
            0.5 if no patterns loaded (neutral — unknown)
            0.0 if patterns loaded but none match
        """
        if not self._pattern_cache:
            return 0.5  # No patterns available — neutral

        content = memory.get('content', '')
        if not content:
            return 0.0

        content_lower = content.lower()

        # Also check tags
        tags_str = ''
        tags = memory.get('tags', [])
        if isinstance(tags, list):
            tags_str = ' '.join(t.lower() for t in tags)
        elif isinstance(tags, str):
            tags_str = tags.lower()

        searchable = content_lower + ' ' + tags_str

        max_confidence = 0.0
        for pattern_value, confidence in self._pattern_cache.items():
            # Pattern values are already lowercased in the cache
            pattern_lower = pattern_value.lower() if pattern_value else ''
            if not pattern_lower:
                continue
            # Word-boundary check for short patterns to avoid false positives
            if len(pattern_lower) <= 3:
                if re.search(r'\b' + re.escape(pattern_lower) + r'\b', searchable):
                    max_confidence = max(max_confidence, confidence)
            else:
                if pattern_lower in searchable:
                    max_confidence = max(max_confidence, confidence)

        return max(0.0, min(max_confidence, 1.0))


# ============================================================================
# Module-level convenience functions
# ============================================================================

def get_feature_names() -> List[str]:
    """Return ordered list of feature names (matches vector indices)."""
    return list(FEATURE_NAMES)


def get_num_features() -> int:
    """Return the number of features in the vector."""
    return NUM_FEATURES
