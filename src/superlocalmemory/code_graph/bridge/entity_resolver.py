# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Bridge Module

"""Entity Resolver — match SLM fact text against code graph nodes.

Extracts code mentions from natural language using regex patterns,
then matches against graph_nodes by name, qualified_name, and file_path.
Creates code_memory_links entries in code_graph.db.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from superlocalmemory.code_graph.models import CodeMemoryLink, LinkType
from superlocalmemory.storage.models import _new_id

if TYPE_CHECKING:
    from superlocalmemory.code_graph.database import CodeGraphDatabase
    from superlocalmemory.code_graph.models import GraphNode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns (Appendix A from LLD)
# ---------------------------------------------------------------------------

RE_FILE_PATH = re.compile(
    r'(?:[\w./\\]+\.(?:py|ts|tsx|js|jsx|go|rs|java|rb|cpp|c|cs|kt|swift|php))',
    re.IGNORECASE,
)

RE_QUALIFIED_CALL = re.compile(
    r'(\w+(?:\.\w+)+)\s*\(\)',
)

RE_BACKTICK = re.compile(
    r'`(\w{3,})`',
)

RE_CAMEL_CASE = re.compile(
    r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b',
)

RE_SNAKE_CALL = re.compile(
    r'\b(\w+_\w+)\s*\(\)',
)

RE_QUOTED = re.compile(
    r"""['"]([\w]{3,})['"]""",
)

# Bare snake_case identifiers (e.g., "authenticate_user" without parens)
RE_SNAKE_BARE = re.compile(
    r'\b([a-z]\w*_\w+)\b',
)

# ---------------------------------------------------------------------------
# Link type classification keywords (Appendix B from LLD)
# ---------------------------------------------------------------------------

BUG_FIX_KEYWORDS: frozenset[str] = frozenset({
    "bug", "fix", "fixed", "broken", "error", "issue", "crash",
    "fault", "defect", "patch", "hotfix", "workaround",
})

DECISION_KEYWORDS: frozenset[str] = frozenset({
    "decided", "decision", "chose", "chosen", "should use",
    "instead of", "agreed", "approved", "selected", "opted",
})

REFACTOR_KEYWORDS: frozenset[str] = frozenset({
    "refactor", "refactored", "rename", "renamed", "extract",
    "extracted", "move", "moved", "split", "merge", "cleanup",
    "restructure", "reorganize",
})

RATIONALE_KEYWORDS: frozenset[str] = frozenset({
    "because", "reason", "rationale", "why we", "designed to",
    "purpose of", "motivation", "trade-off", "tradeoff",
})

# ---------------------------------------------------------------------------
# Confidence scores
# ---------------------------------------------------------------------------

CONF_EXACT_NAME = 0.90
CONF_QUALIFIED_CONTAINS = 0.85
CONF_FILE_PATH = 0.80
CONF_SUBSTRING = 0.60
CONF_BOOST_BACKTICK = 0.05
CONF_BOOST_CALL_SYNTAX = 0.05
CONF_CAP = 0.95

MIN_SUBSTRING_LEN = 4


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MatchedNode:
    """A code graph node matched against a fact's text."""
    node_id: str
    qualified_name: str
    kind: str
    file_path: str
    confidence: float
    match_source: str  # "exact_name" | "qualified_name" | "file_path" | "substring"


@dataclass(frozen=True)
class CandidateMention:
    """A code mention extracted from fact text."""
    text: str
    is_backtick: bool = False
    is_call_syntax: bool = False
    is_file_path: bool = False


# ---------------------------------------------------------------------------
# Node index (cached)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _NodeIndex:
    """Cached lookup structures for fast matching."""
    by_name: dict[str, list[GraphNode]]       # name.lower() -> nodes
    by_file_stem: dict[str, list[GraphNode]]   # file stem -> nodes
    all_nodes: tuple[GraphNode, ...]
    version: int


# ---------------------------------------------------------------------------
# EntityResolver
# ---------------------------------------------------------------------------

class EntityResolver:
    """Matches SLM fact text against code graph nodes."""

    def __init__(self, code_graph_db: CodeGraphDatabase) -> None:
        self._db = code_graph_db
        self._cache: _NodeIndex | None = None

    def resolve(
        self,
        fact_text: str,
        fact_id: str,
    ) -> list[CodeMemoryLink]:
        """Resolve code entity mentions in fact text and create links.

        Returns list of CodeMemoryLink objects created.
        """
        if not fact_text or not fact_id:
            return []

        index = self._get_index()
        candidates = self._extract_candidates(fact_text)
        if not candidates:
            return []

        # Match candidates against graph nodes
        matches: dict[str, MatchedNode] = {}  # node_id -> best match
        for candidate in candidates:
            matched = self._match_candidate(candidate, index)
            for m in matched:
                existing = matches.get(m.node_id)
                if existing is None or m.confidence > existing.confidence:
                    matches[m.node_id] = m

        if not matches:
            return []

        # Classify link type
        link_type = self._classify_link_type(fact_text)
        now_str = datetime.now(timezone.utc).isoformat()

        # Create links
        links: list[CodeMemoryLink] = []
        for matched_node in matches.values():
            link = CodeMemoryLink(
                link_id=_new_id(),
                code_node_id=matched_node.node_id,
                slm_fact_id=fact_id,
                slm_entity_id=None,
                link_type=link_type,
                confidence=matched_node.confidence,
                created_at=now_str,
                last_verified=now_str,
                is_stale=False,
            )
            self._db.upsert_link(link)
            links.append(link)

        logger.debug(
            "Resolved %d code entities for fact %s",
            len(links), fact_id,
        )
        return links

    def get_links_for_fact(self, fact_id: str) -> list[CodeMemoryLink]:
        """Get all code_memory_links for a given SLM fact ID."""
        return self._db.get_links_for_fact(fact_id)

    def get_links_for_node(self, node_id: str) -> list[CodeMemoryLink]:
        """Get all code_memory_links for a given code graph node."""
        return self._db.get_links_for_node(node_id)

    def invalidate_cache(self) -> None:
        """Clear the cached node lookup dict."""
        self._cache = None

    def get_matched_nodes(self, fact_text: str) -> list[MatchedNode]:
        """Extract and match code mentions without creating links.

        Useful for testing and preview operations.
        """
        if not fact_text:
            return []

        index = self._get_index()
        candidates = self._extract_candidates(fact_text)
        if not candidates:
            return []

        matches: dict[str, MatchedNode] = {}
        for candidate in candidates:
            matched = self._match_candidate(candidate, index)
            for m in matched:
                existing = matches.get(m.node_id)
                if existing is None or m.confidence > existing.confidence:
                    matches[m.node_id] = m

        return list(matches.values())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_index(self) -> _NodeIndex:
        """Get or rebuild the node index."""
        current_version = self._db.version
        if self._cache is not None and self._cache.version == current_version:
            return self._cache

        all_nodes = self._db.get_all_nodes()
        by_name: dict[str, list[GraphNode]] = {}
        by_file_stem: dict[str, list[GraphNode]] = {}

        for node in all_nodes:
            key = node.name.lower()
            by_name.setdefault(key, []).append(node)

            # Index by file stem (e.g., "handler" from "handler.py")
            if node.file_path:
                import os
                stem = os.path.splitext(os.path.basename(node.file_path))[0].lower()
                by_file_stem.setdefault(stem, []).append(node)

        self._cache = _NodeIndex(
            by_name=by_name,
            by_file_stem=by_file_stem,
            all_nodes=tuple(all_nodes),
            version=current_version,
        )
        return self._cache

    @staticmethod
    def _extract_candidates(text: str) -> list[CandidateMention]:
        """Extract code mention candidates from text using regex."""
        candidates: list[CandidateMention] = []
        seen: set[str] = set()

        def _add(raw: str, *, backtick: bool = False,
                 call: bool = False, file_path: bool = False) -> None:
            normalized = raw.strip().rstrip("()")
            if normalized and normalized not in seen:
                seen.add(normalized)
                candidates.append(CandidateMention(
                    text=normalized,
                    is_backtick=backtick,
                    is_call_syntax=call,
                    is_file_path=file_path,
                ))

        # File paths
        for m in RE_FILE_PATH.finditer(text):
            _add(m.group(0), file_path=True)

        # Qualified calls
        for m in RE_QUALIFIED_CALL.finditer(text):
            _add(m.group(1), call=True)

        # Backtick-quoted
        for m in RE_BACKTICK.finditer(text):
            _add(m.group(1), backtick=True)

        # CamelCase
        for m in RE_CAMEL_CASE.finditer(text):
            _add(m.group(1))

        # snake_case calls
        for m in RE_SNAKE_CALL.finditer(text):
            _add(m.group(1), call=True)

        # Quoted names
        for m in RE_QUOTED.finditer(text):
            _add(m.group(1))

        # Bare snake_case identifiers (lowest priority — after all specific patterns)
        for m in RE_SNAKE_BARE.finditer(text):
            _add(m.group(1))

        return candidates

    def _match_candidate(
        self, candidate: CandidateMention, index: _NodeIndex
    ) -> list[MatchedNode]:
        """Match a single candidate against the node index."""
        results: list[MatchedNode] = []
        text_lower = candidate.text.lower()

        # 1. Exact name match
        exact_matches = index.by_name.get(text_lower, [])
        for node in exact_matches:
            conf = CONF_EXACT_NAME
            if candidate.is_backtick:
                conf += CONF_BOOST_BACKTICK
            if candidate.is_call_syntax:
                conf += CONF_BOOST_CALL_SYNTAX
            conf = min(conf, CONF_CAP)
            results.append(MatchedNode(
                node_id=node.node_id,
                qualified_name=node.qualified_name,
                kind=node.kind.value,
                file_path=node.file_path,
                confidence=conf,
                match_source="exact_name",
            ))

        if results:
            return results

        # 2. File path match
        if candidate.is_file_path:
            import os
            stem = os.path.splitext(os.path.basename(candidate.text))[0].lower()
            # Match nodes whose file_path ends with the candidate
            for node in index.all_nodes:
                if node.file_path and node.file_path.endswith(candidate.text):
                    conf = CONF_FILE_PATH
                    conf = min(conf, CONF_CAP)
                    results.append(MatchedNode(
                        node_id=node.node_id,
                        qualified_name=node.qualified_name,
                        kind=node.kind.value,
                        file_path=node.file_path,
                        confidence=conf,
                        match_source="file_path",
                    ))
            # Also match by file stem in by_file_stem
            if not results:
                file_stem_matches = index.by_file_stem.get(stem, [])
                for node in file_stem_matches:
                    conf = CONF_FILE_PATH
                    results.append(MatchedNode(
                        node_id=node.node_id,
                        qualified_name=node.qualified_name,
                        kind=node.kind.value,
                        file_path=node.file_path,
                        confidence=conf,
                        match_source="file_path",
                    ))

        if results:
            return results

        # 3. Qualified name contains (substring match)
        if len(text_lower) >= MIN_SUBSTRING_LEN:
            for node in index.all_nodes:
                qname_lower = node.qualified_name.lower()
                if text_lower in qname_lower and text_lower != qname_lower:
                    conf = CONF_QUALIFIED_CONTAINS
                    if candidate.is_backtick:
                        conf += CONF_BOOST_BACKTICK
                    if candidate.is_call_syntax:
                        conf += CONF_BOOST_CALL_SYNTAX
                    conf = min(conf, CONF_CAP)
                    results.append(MatchedNode(
                        node_id=node.node_id,
                        qualified_name=node.qualified_name,
                        kind=node.kind.value,
                        file_path=node.file_path,
                        confidence=conf,
                        match_source="qualified_name",
                    ))

        if results:
            return results

        # 4. Substring match (node name is substring of candidate or vice versa)
        if len(text_lower) >= MIN_SUBSTRING_LEN:
            for node in index.all_nodes:
                name_lower = node.name.lower()
                if len(name_lower) < MIN_SUBSTRING_LEN:
                    continue
                if name_lower in text_lower or text_lower in name_lower:
                    conf = CONF_SUBSTRING
                    if candidate.is_backtick:
                        conf += CONF_BOOST_BACKTICK
                    conf = min(conf, CONF_CAP)
                    results.append(MatchedNode(
                        node_id=node.node_id,
                        qualified_name=node.qualified_name,
                        kind=node.kind.value,
                        file_path=node.file_path,
                        confidence=conf,
                        match_source="substring",
                    ))

        return results

    @staticmethod
    def _classify_link_type(fact_text: str) -> LinkType:
        """Classify the link type based on keywords in the fact text."""
        text_lower = fact_text.lower()
        words = set(text_lower.split())

        # Check multi-word keywords by testing if they appear in text
        for kw in BUG_FIX_KEYWORDS:
            if " " in kw:
                if kw in text_lower:
                    return LinkType.BUG_FIX
            elif kw in words:
                return LinkType.BUG_FIX

        for kw in DECISION_KEYWORDS:
            if " " in kw:
                if kw in text_lower:
                    return LinkType.DECISION_ABOUT
            elif kw in words:
                return LinkType.DECISION_ABOUT

        for kw in REFACTOR_KEYWORDS:
            if " " in kw:
                if kw in text_lower:
                    return LinkType.REFACTOR
            elif kw in words:
                return LinkType.REFACTOR

        for kw in RATIONALE_KEYWORDS:
            if " " in kw:
                if kw in text_lower:
                    return LinkType.DESIGN_RATIONALE
            elif kw in words:
                return LinkType.DESIGN_RATIONALE

        return LinkType.MENTIONS
