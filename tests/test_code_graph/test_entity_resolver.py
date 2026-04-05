# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file

"""Tests for EntityResolver — regex extraction, matching, scoring, classification."""

from __future__ import annotations

import pytest

from superlocalmemory.code_graph.bridge.entity_resolver import (
    BUG_FIX_KEYWORDS,
    CONF_EXACT_NAME,
    CONF_FILE_PATH,
    CONF_QUALIFIED_CONTAINS,
    CONF_SUBSTRING,
    DECISION_KEYWORDS,
    RATIONALE_KEYWORDS,
    REFACTOR_KEYWORDS,
    CandidateMention,
    EntityResolver,
    MatchedNode,
)
from superlocalmemory.code_graph.database import CodeGraphDatabase
from superlocalmemory.code_graph.models import (
    GraphNode,
    LinkType,
    NodeKind,
)


@pytest.fixture
def resolver(db: CodeGraphDatabase) -> EntityResolver:
    """EntityResolver with a fresh database."""
    return EntityResolver(db)


def _insert_node(
    db: CodeGraphDatabase,
    *,
    node_id: str = "n1",
    name: str = "authenticate_user",
    qualified_name: str = "src/auth/handler.py::authenticate_user",
    file_path: str = "src/auth/handler.py",
    kind: NodeKind = NodeKind.FUNCTION,
) -> GraphNode:
    """Helper to insert a test node."""
    node = GraphNode(
        node_id=node_id,
        kind=kind,
        name=name,
        qualified_name=qualified_name,
        file_path=file_path,
        language="python",
    )
    db.upsert_node(node)
    return node


# ------------------------------------------------------------------
# Regex extraction tests
# ------------------------------------------------------------------

class TestCandidateExtraction:
    """Test _extract_candidates regex patterns."""

    def test_extracts_file_paths(self) -> None:
        candidates = EntityResolver._extract_candidates(
            "Fixed the bug in handler.py and utils.ts"
        )
        texts = {c.text for c in candidates}
        assert "handler.py" in texts
        assert "utils.ts" in texts

    def test_extracts_backtick_names(self) -> None:
        candidates = EntityResolver._extract_candidates(
            "The `authenticate_user` function is broken"
        )
        texts = {c.text for c in candidates}
        assert "authenticate_user" in texts
        # Verify backtick flag
        bt = [c for c in candidates if c.text == "authenticate_user"]
        assert bt[0].is_backtick is True

    def test_extracts_camel_case(self) -> None:
        candidates = EntityResolver._extract_candidates(
            "Check the UserService and AuthHandler classes"
        )
        texts = {c.text for c in candidates}
        assert "UserService" in texts
        assert "AuthHandler" in texts

    def test_extracts_snake_case_calls(self) -> None:
        candidates = EntityResolver._extract_candidates(
            "We should call validate_token() before proceeding"
        )
        texts = {c.text for c in candidates}
        assert "validate_token" in texts
        call = [c for c in candidates if c.text == "validate_token"]
        assert call[0].is_call_syntax is True

    def test_extracts_qualified_calls(self) -> None:
        candidates = EntityResolver._extract_candidates(
            "The auth.handler.login() method needs fixing"
        )
        texts = {c.text for c in candidates}
        assert "auth.handler.login" in texts

    def test_extracts_quoted_names(self) -> None:
        candidates = EntityResolver._extract_candidates(
            "The 'login' function has a problem"
        )
        texts = {c.text for c in candidates}
        assert "login" in texts

    def test_empty_text_returns_empty(self) -> None:
        assert EntityResolver._extract_candidates("") == []

    def test_no_code_mentions(self) -> None:
        candidates = EntityResolver._extract_candidates(
            "The weather is nice today"
        )
        assert candidates == []

    def test_deduplication_in_extraction(self) -> None:
        candidates = EntityResolver._extract_candidates(
            "`authenticate_user` calls `authenticate_user`"
        )
        texts = [c.text for c in candidates]
        assert texts.count("authenticate_user") == 1


# ------------------------------------------------------------------
# Matching tests
# ------------------------------------------------------------------

class TestMatching:
    """Test node matching logic."""

    def test_exact_name_match(self, db: CodeGraphDatabase, resolver: EntityResolver) -> None:
        _insert_node(db, name="authenticate_user")
        links = resolver.resolve(
            "Fixed `authenticate_user` function", "fact-1",
        )
        assert len(links) == 1
        assert links[0].code_node_id == "n1"

    def test_file_path_match(self, db: CodeGraphDatabase, resolver: EntityResolver) -> None:
        _insert_node(db, file_path="src/auth/handler.py", kind=NodeKind.FILE)
        links = resolver.resolve(
            "Updated handler.py to fix auth", "fact-2",
        )
        # Should match via file path
        assert len(links) >= 1

    def test_qualified_name_contains_match(
        self, db: CodeGraphDatabase, resolver: EntityResolver,
    ) -> None:
        _insert_node(
            db,
            node_id="n2",
            name="login",
            qualified_name="src/auth/handler.py::login",
        )
        links = resolver.resolve(
            "Check the `login` function for issues", "fact-3",
        )
        # "login" should match via backtick extraction + exact name
        assert len(links) >= 1

    def test_no_matches_returns_empty(
        self, db: CodeGraphDatabase, resolver: EntityResolver,
    ) -> None:
        _insert_node(db)
        links = resolver.resolve(
            "The weather is nice today", "fact-4",
        )
        assert links == []

    def test_empty_fact_text(self, resolver: EntityResolver) -> None:
        assert resolver.resolve("", "fact-5") == []

    def test_empty_fact_id(self, resolver: EntityResolver) -> None:
        assert resolver.resolve("some text", "") == []

    def test_deduplication_keeps_highest_confidence(
        self, db: CodeGraphDatabase, resolver: EntityResolver,
    ) -> None:
        """If same node matched by multiple candidates, keep highest confidence."""
        _insert_node(db, name="validate_token")
        links = resolver.resolve(
            "`validate_token` — also called as validate_token()", "fact-6",
        )
        # Should deduplicate to single link for node n1
        assert len(links) == 1
        # Backtick + exact name should give higher confidence than plain
        assert links[0].confidence >= CONF_EXACT_NAME


# ------------------------------------------------------------------
# Confidence scoring tests
# ------------------------------------------------------------------

class TestConfidenceScoring:
    """Test confidence values for different match types."""

    def test_exact_name_confidence(
        self, db: CodeGraphDatabase, resolver: EntityResolver,
    ) -> None:
        _insert_node(db, name="authenticate_user")
        matched = resolver.get_matched_nodes("authenticate_user is broken")
        assert len(matched) >= 1
        assert matched[0].confidence == CONF_EXACT_NAME
        assert matched[0].match_source == "exact_name"

    def test_backtick_boost(
        self, db: CodeGraphDatabase, resolver: EntityResolver,
    ) -> None:
        _insert_node(db, name="authenticate_user")
        matched = resolver.get_matched_nodes("`authenticate_user` is broken")
        assert len(matched) >= 1
        assert matched[0].confidence == pytest.approx(CONF_EXACT_NAME + 0.05)

    def test_call_syntax_boost(
        self, db: CodeGraphDatabase, resolver: EntityResolver,
    ) -> None:
        _insert_node(db, name="validate_token")
        matched = resolver.get_matched_nodes("Need to fix validate_token()")
        assert len(matched) >= 1
        assert matched[0].confidence == pytest.approx(CONF_EXACT_NAME + 0.05)

    def test_confidence_capped_at_095(
        self, db: CodeGraphDatabase, resolver: EntityResolver,
    ) -> None:
        """Backtick + call syntax should not exceed 0.95."""
        _insert_node(db, name="validate_token")
        # Backtick + call syntax
        matched = resolver.get_matched_nodes("`validate_token`()")
        # Even with double boost, cap at 0.95
        for m in matched:
            assert m.confidence <= 0.95


# ------------------------------------------------------------------
# Link type classification tests
# ------------------------------------------------------------------

class TestLinkTypeClassification:
    """Test link type classification based on keywords."""

    def test_bug_fix(self, db: CodeGraphDatabase, resolver: EntityResolver) -> None:
        _insert_node(db)
        links = resolver.resolve(
            "Fixed the bug in authenticate_user", "fact-10",
        )
        assert len(links) == 1
        assert links[0].link_type == LinkType.BUG_FIX

    def test_decision(self, db: CodeGraphDatabase, resolver: EntityResolver) -> None:
        _insert_node(db)
        links = resolver.resolve(
            "Decided to use authenticate_user for all auth flows", "fact-11",
        )
        assert len(links) == 1
        assert links[0].link_type == LinkType.DECISION_ABOUT

    def test_refactor(self, db: CodeGraphDatabase, resolver: EntityResolver) -> None:
        _insert_node(db)
        links = resolver.resolve(
            "Refactored authenticate_user to reduce complexity", "fact-12",
        )
        assert len(links) == 1
        assert links[0].link_type == LinkType.REFACTOR

    def test_design_rationale(self, db: CodeGraphDatabase, resolver: EntityResolver) -> None:
        _insert_node(db)
        links = resolver.resolve(
            "authenticate_user exists because of legacy constraints", "fact-13",
        )
        assert len(links) == 1
        assert links[0].link_type == LinkType.DESIGN_RATIONALE

    def test_default_mentions(self, db: CodeGraphDatabase, resolver: EntityResolver) -> None:
        _insert_node(db)
        links = resolver.resolve(
            "The authenticate_user function handles login", "fact-14",
        )
        assert len(links) == 1
        assert links[0].link_type == LinkType.MENTIONS


# ------------------------------------------------------------------
# Cache invalidation tests
# ------------------------------------------------------------------

class TestCacheInvalidation:
    """Test cache invalidation."""

    def test_invalidate_cache(
        self, db: CodeGraphDatabase, resolver: EntityResolver,
    ) -> None:
        _insert_node(db, name="old_function")
        matched1 = resolver.get_matched_nodes("old_function is here")
        assert len(matched1) == 1

        # Add a new node
        _insert_node(db, node_id="n2", name="new_function",
                     qualified_name="new.py::new_function")

        # Cache should auto-invalidate on version change
        matched2 = resolver.get_matched_nodes("new_function is here")
        assert len(matched2) == 1
        assert matched2[0].node_id == "n2"

    def test_explicit_invalidate(
        self, db: CodeGraphDatabase, resolver: EntityResolver,
    ) -> None:
        resolver.invalidate_cache()
        # Should not crash, just clears cache
        assert resolver._cache is None


# ------------------------------------------------------------------
# Link persistence tests
# ------------------------------------------------------------------

class TestLinkPersistence:
    """Test that links are persisted to code_graph.db."""

    def test_links_persisted(self, db: CodeGraphDatabase, resolver: EntityResolver) -> None:
        _insert_node(db)
        resolver.resolve("authenticate_user is important", "fact-20")

        # Verify via get_links_for_fact
        links = resolver.get_links_for_fact("fact-20")
        assert len(links) == 1
        assert links[0].slm_fact_id == "fact-20"
        assert links[0].code_node_id == "n1"

    def test_get_links_for_node(self, db: CodeGraphDatabase, resolver: EntityResolver) -> None:
        _insert_node(db)
        resolver.resolve("authenticate_user is important", "fact-21")

        links = resolver.get_links_for_node("n1")
        assert len(links) == 1
        assert links[0].slm_fact_id == "fact-21"
