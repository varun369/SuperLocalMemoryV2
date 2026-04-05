# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""HybridSearch — FTS5 + vec0 + Reciprocal Rank Fusion.

Provides text search (FTS5 BM25), optional semantic search (vec0 cosine),
and hybrid fusion via RRF (k=60). Kind boosting for functions/methods.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from superlocalmemory.code_graph.database import CodeGraphDatabase
from superlocalmemory.code_graph.models import NodeKind

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SearchResult:
    """Single hybrid search result."""
    node_id: str
    qualified_name: str
    name: str
    kind: str
    file_path: str
    line_start: int
    score: float
    match_source: str  # "fts5", "vector", "both", "keyword"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RRF_K = 60
_FTS5_META_CHARS = re.compile(r'([*"():\^{}+|])')
_MAX_QUERY_LEN = 500

# Kind boost multipliers
_KIND_BOOST: dict[str, float] = {
    NodeKind.FUNCTION.value: 1.3,
    NodeKind.METHOD.value: 1.3,
    NodeKind.CLASS.value: 1.1,
    NodeKind.FILE.value: 0.8,
    NodeKind.MODULE.value: 0.9,
}


# ---------------------------------------------------------------------------
# HybridSearch
# ---------------------------------------------------------------------------

class HybridSearch:
    """FTS5 + vec0 hybrid search over graph nodes.

    Falls back gracefully:
    - If vec0 unavailable: FTS5-only
    - If FTS5 returns nothing: keyword LIKE fallback
    - If graph is empty: returns []
    """

    def __init__(self, db: CodeGraphDatabase) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 20) -> list[SearchResult]:
        """FTS5 text search on graph_nodes_fts.

        Args:
            query: Search query string.
            limit: Maximum results to return.

        Returns:
            List of SearchResult sorted by BM25 rank (best first).
        """
        if not query or not query.strip():
            return []

        fts_results = self._fts5_search(query)
        if not fts_results:
            return self._keyword_fallback(query, limit)

        return self._build_results(
            scores=fts_results,
            fts_ids=set(fts_results.keys()),
            vec_ids=set(),
            limit=limit,
        )

    def search_semantic(
        self, query_embedding: list[float], limit: int = 20
    ) -> list[SearchResult]:
        """vec0 cosine similarity search (if embeddings exist).

        Args:
            query_embedding: Pre-computed query embedding vector.
            limit: Maximum results to return.

        Returns:
            List of SearchResult sorted by cosine similarity.
        """
        vec_results = self._vec0_search(query_embedding)
        if not vec_results:
            return []

        return self._build_results(
            scores=vec_results,
            fts_ids=set(),
            vec_ids=set(vec_results.keys()),
            limit=limit,
        )

    def search_hybrid(
        self,
        query: str,
        limit: int = 20,
        query_embedding: list[float] | None = None,
    ) -> list[SearchResult]:
        """FTS5 + vec0 merged via Reciprocal Rank Fusion (k=60).

        Args:
            query: Text query for FTS5.
            limit: Maximum results to return.
            query_embedding: Optional embedding for vec0 search.

        Returns:
            List of SearchResult with RRF-fused scores.
        """
        if not query or not query.strip():
            return []

        fts_results = self._fts5_search(query)
        vec_results: dict[str, float] = {}
        if query_embedding is not None:
            vec_results = self._vec0_search(query_embedding)

        fts_ids = set(fts_results.keys())
        vec_ids = set(vec_results.keys())

        # If both empty, fall back to keyword
        if not fts_results and not vec_results:
            return self._keyword_fallback(query, limit)

        # RRF fusion
        rrf_scores = self._rrf_fuse(fts_results, vec_results)

        # Kind boosting
        rrf_scores = self._apply_kind_boost(rrf_scores, query)

        return self._build_results(
            scores=rrf_scores,
            fts_ids=fts_ids,
            vec_ids=vec_ids,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Internal: FTS5
    # ------------------------------------------------------------------

    def _fts5_search(self, query: str) -> dict[str, float]:
        """Run FTS5 BM25 search. Returns {node_id: score}."""
        sanitized = _sanitize_fts_query(query)
        if not sanitized:
            return {}

        try:
            rows = self._db.execute(
                """SELECT gn.node_id, gn.name, gn.kind, fts.rank
                   FROM graph_nodes_fts fts
                   JOIN graph_nodes gn ON gn.rowid = fts.rowid
                   WHERE graph_nodes_fts MATCH ?
                   ORDER BY fts.rank
                   LIMIT 100""",
                (sanitized,),
            )
        except Exception as exc:
            logger.debug("FTS5 search failed: %s", exc)
            return {}

        # rank is negative in FTS5 (lower = better), negate for higher=better
        results: dict[str, float] = {}
        for row in rows:
            results[row["node_id"]] = -row["rank"]
        return results

    # ------------------------------------------------------------------
    # Internal: vec0
    # ------------------------------------------------------------------

    def _vec0_search(self, embedding: list[float]) -> dict[str, float]:
        """Run vec0 cosine similarity search. Returns {node_id: similarity}."""
        try:
            import json
            rows = self._db.execute(
                """SELECT node_id, distance
                   FROM code_node_embeddings
                   WHERE embedding MATCH ?
                   ORDER BY distance
                   LIMIT 100""",
                (json.dumps(embedding),),
            )
        except Exception as exc:
            logger.debug("vec0 search failed (expected if no embeddings): %s", exc)
            return {}

        results: dict[str, float] = {}
        for row in rows:
            # cosine distance: 0=identical, 2=opposite. similarity = 1.0 - distance
            results[row["node_id"]] = 1.0 - row["distance"]
        return results

    # ------------------------------------------------------------------
    # Internal: Keyword fallback
    # ------------------------------------------------------------------

    def _keyword_fallback(self, query: str, limit: int) -> list[SearchResult]:
        """LIKE-based keyword search as last resort."""
        words = query.lower().split()[:10]  # Cap at 10 words
        if not words:
            return []

        conditions = []
        params: list[str] = []
        for word in words:
            conditions.append(
                "(LOWER(name) LIKE ? OR LOWER(qualified_name) LIKE ?)"
            )
            pattern = f"%{word}%"
            params.extend([pattern, pattern])

        where_clause = " AND ".join(conditions)

        try:
            rows = self._db.execute(
                f"""SELECT node_id, name, qualified_name, kind, file_path, line_start
                    FROM graph_nodes
                    WHERE {where_clause}
                    LIMIT 100""",
                tuple(params),
            )
        except Exception as exc:
            logger.debug("Keyword fallback failed: %s", exc)
            return []

        results: list[SearchResult] = []
        for row in rows:
            score = _keyword_score(row["name"], row["qualified_name"], words)
            results.append(SearchResult(
                node_id=row["node_id"],
                qualified_name=row["qualified_name"],
                name=row["name"],
                kind=row["kind"],
                file_path=row["file_path"],
                line_start=row["line_start"],
                score=score,
                match_source="keyword",
            ))

        results.sort(key=lambda r: -r.score)
        return results[:limit]

    # ------------------------------------------------------------------
    # Internal: RRF fusion
    # ------------------------------------------------------------------

    def _rrf_fuse(
        self,
        fts_results: dict[str, float],
        vec_results: dict[str, float],
    ) -> dict[str, float]:
        """Reciprocal Rank Fusion with k=60."""
        rrf_scores: dict[str, float] = defaultdict(float)

        # Sort FTS results by score descending
        fts_ranked = sorted(fts_results.items(), key=lambda x: -x[1])
        for rank_pos, (node_id, _) in enumerate(fts_ranked):
            rrf_scores[node_id] += 1.0 / (_RRF_K + rank_pos + 1)

        # Sort vec results by score descending
        vec_ranked = sorted(vec_results.items(), key=lambda x: -x[1])
        for rank_pos, (node_id, _) in enumerate(vec_ranked):
            rrf_scores[node_id] += 1.0 / (_RRF_K + rank_pos + 1)

        return dict(rrf_scores)

    # ------------------------------------------------------------------
    # Internal: Kind boosting
    # ------------------------------------------------------------------

    def _apply_kind_boost(
        self, scores: dict[str, float], query: str
    ) -> dict[str, float]:
        """Apply kind-based score boosting."""
        if not scores:
            return scores

        # Load kind info for scored nodes
        node_ids = list(scores.keys())
        kind_map = self._load_node_kinds(node_ids)

        boosted = dict(scores)
        for node_id, score in scores.items():
            kind = kind_map.get(node_id)
            if kind:
                boost = _KIND_BOOST.get(kind, 1.0)
                boosted[node_id] = score * boost

        # Additional pattern-based boosts
        is_pascal = bool(re.match(r'^[A-Z][a-z]+([A-Z][a-z]+)+$', query))
        is_snake = bool(re.match(r'^[a-z]+(_[a-z]+)+$', query))

        if is_pascal:
            for node_id in boosted:
                if kind_map.get(node_id) == NodeKind.CLASS.value:
                    boosted[node_id] *= 1.5

        if is_snake:
            for node_id in boosted:
                kind = kind_map.get(node_id)
                if kind in (NodeKind.FUNCTION.value, NodeKind.METHOD.value):
                    boosted[node_id] *= 1.5

        return boosted

    def _load_node_kinds(self, node_ids: list[str]) -> dict[str, str]:
        """Load kind for a list of node IDs."""
        if not node_ids:
            return {}

        placeholders = ",".join("?" for _ in node_ids)
        try:
            rows = self._db.execute(
                f"SELECT node_id, kind FROM graph_nodes WHERE node_id IN ({placeholders})",
                tuple(node_ids),
            )
        except Exception:
            return {}

        return {row["node_id"]: row["kind"] for row in rows}

    # ------------------------------------------------------------------
    # Internal: Build results
    # ------------------------------------------------------------------

    def _build_results(
        self,
        scores: dict[str, float],
        fts_ids: set[str],
        vec_ids: set[str],
        limit: int,
    ) -> list[SearchResult]:
        """Load node data and build SearchResult list."""
        if not scores:
            return []

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:limit]
        node_ids = [nid for nid, _ in ranked]

        # Load node details
        node_map = self._load_node_details(node_ids)

        results: list[SearchResult] = []
        for node_id, score in ranked:
            node = node_map.get(node_id)
            if node is None:
                continue

            if node_id in fts_ids and node_id in vec_ids:
                match_source = "both"
            elif node_id in fts_ids:
                match_source = "fts5"
            elif node_id in vec_ids:
                match_source = "vector"
            else:
                match_source = "keyword"

            results.append(SearchResult(
                node_id=node_id,
                qualified_name=node["qualified_name"],
                name=node["name"],
                kind=node["kind"],
                file_path=node["file_path"],
                line_start=node["line_start"],
                score=score,
                match_source=match_source,
            ))

        return results

    def _load_node_details(self, node_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Load details for a set of node IDs."""
        if not node_ids:
            return {}

        placeholders = ",".join("?" for _ in node_ids)
        try:
            rows = self._db.execute(
                f"""SELECT node_id, name, qualified_name, kind, file_path, line_start
                    FROM graph_nodes WHERE node_id IN ({placeholders})""",
                tuple(node_ids),
            )
        except Exception:
            return {}

        return {row["node_id"]: dict(row) for row in rows}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _sanitize_fts_query(query: str) -> str:
    """Sanitize query for FTS5 MATCH.

    Escapes metacharacters, wraps each token in double quotes,
    truncates to _MAX_QUERY_LEN.
    """
    # Strip control chars
    cleaned = "".join(ch for ch in query if ch >= " ")
    # Escape FTS5 metacharacters
    cleaned = _FTS5_META_CHARS.sub(r'"\1"', cleaned)
    # Split and wrap tokens
    tokens = cleaned.split()
    if not tokens:
        return ""
    wrapped = " ".join(f'"{t}"' for t in tokens[:20])
    return wrapped[:_MAX_QUERY_LEN]


def _keyword_score(name: str, qualified_name: str, words: list[str]) -> float:
    """Compute a keyword match score."""
    score = 0.0
    name_lower = name.lower()
    qname_lower = qualified_name.lower()
    for word in words:
        if word == name_lower:
            score += 3.0
        elif name_lower.startswith(word):
            score += 2.0
        elif word in name_lower:
            score += 1.0
        if word in qname_lower:
            score += 0.5
    return score
