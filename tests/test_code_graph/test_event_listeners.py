# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file

"""Tests for BridgeEventListeners — registration, dispatch, error isolation."""

from __future__ import annotations

from typing import Any, Callable
from unittest.mock import MagicMock, patch

import pytest

from superlocalmemory.code_graph.bridge.event_listeners import BridgeEventListeners
from superlocalmemory.code_graph.bridge.entity_resolver import EntityResolver
from superlocalmemory.code_graph.bridge.fact_enricher import FactEnricher
from superlocalmemory.code_graph.bridge.hebbian_linker import HebbianLinker
from superlocalmemory.code_graph.bridge.temporal_checker import TemporalChecker
from superlocalmemory.code_graph.database import CodeGraphDatabase
from superlocalmemory.code_graph.graph_engine import GraphEngine
from superlocalmemory.code_graph.graph_store import GraphStore
from superlocalmemory.code_graph.models import CodeMemoryLink, LinkType


# ---------------------------------------------------------------------------
# Fake event bus for testing
# ---------------------------------------------------------------------------

class FakeEventBus:
    """Minimal event bus for testing listener registration."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[..., Any]]] = {}

    def subscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        self._listeners.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        if event_type in self._listeners:
            self._listeners[event_type] = [
                cb for cb in self._listeners[event_type] if cb is not callback
            ]

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        for cb in self._listeners.get(event_type, []):
            cb({"event_type": event_type, "payload": payload})

    def listener_count(self, event_type: str) -> int:
        return len(self._listeners.get(event_type, []))


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def store(db: CodeGraphDatabase) -> GraphStore:
    return GraphStore(db)


@pytest.fixture
def engine(store: GraphStore) -> GraphEngine:
    return GraphEngine(store)


@pytest.fixture
def resolver(db: CodeGraphDatabase) -> EntityResolver:
    return EntityResolver(db)


@pytest.fixture
def enricher(db: CodeGraphDatabase) -> FactEnricher:
    return FactEnricher(db)


@pytest.fixture
def linker(db: CodeGraphDatabase, engine: GraphEngine) -> HebbianLinker:
    return HebbianLinker(db, engine)


@pytest.fixture
def checker(db: CodeGraphDatabase) -> TemporalChecker:
    return TemporalChecker(db)


@pytest.fixture
def listeners(
    resolver: EntityResolver,
    enricher: FactEnricher,
    linker: HebbianLinker,
    checker: TemporalChecker,
    db: CodeGraphDatabase,
) -> BridgeEventListeners:
    return BridgeEventListeners(
        entity_resolver=resolver,
        fact_enricher=enricher,
        hebbian_linker=linker,
        temporal_checker=checker,
        code_graph_db=db,
    )


class TestRegistration:
    """Test listener registration and unregistration."""

    def test_start_registers_listeners(
        self, listeners: BridgeEventListeners, fake_bus: FakeEventBus,
    ) -> None:
        listeners.start(fake_bus)

        assert fake_bus.listener_count("memory.stored") == 1
        assert fake_bus.listener_count("code_graph.node_deleted") == 1
        assert fake_bus.listener_count("code_graph.node_changed") == 1
        assert listeners.is_started is True

    def test_start_idempotent(
        self, listeners: BridgeEventListeners, fake_bus: FakeEventBus,
    ) -> None:
        listeners.start(fake_bus)
        listeners.start(fake_bus)  # Should not double-register

        assert fake_bus.listener_count("memory.stored") == 1

    def test_stop_unregisters_listeners(
        self, listeners: BridgeEventListeners, fake_bus: FakeEventBus,
    ) -> None:
        listeners.start(fake_bus)
        listeners.stop()

        assert fake_bus.listener_count("memory.stored") == 0
        assert fake_bus.listener_count("code_graph.node_deleted") == 0
        assert fake_bus.listener_count("code_graph.node_changed") == 0
        assert listeners.is_started is False

    def test_stop_without_start(self, listeners: BridgeEventListeners) -> None:
        """Should not crash."""
        listeners.stop()
        assert listeners.is_started is False


class TestMemoryStoredListener:
    """Test on_memory_stored handler."""

    def test_triggers_resolution(
        self,
        db: CodeGraphDatabase,
        listeners: BridgeEventListeners,
        fake_bus: FakeEventBus,
    ) -> None:
        """memory.stored with content should trigger entity resolution."""
        from superlocalmemory.code_graph.models import GraphNode, NodeKind
        db.upsert_node(GraphNode(
            node_id="n1", kind=NodeKind.FUNCTION,
            name="authenticate_user",
            qualified_name="auth.py::authenticate_user",
            file_path="auth.py", language="python",
        ))

        listeners.start(fake_bus)
        fake_bus.emit("memory.stored", {
            "fact_id": "fact-100",
            "content_preview": "Fixed authenticate_user function",
        })

        # Verify link was created
        links = db.get_links_for_fact("fact-100")
        assert len(links) == 1

    def test_no_fact_id_skips(
        self, listeners: BridgeEventListeners, fake_bus: FakeEventBus,
    ) -> None:
        """Missing fact_id should skip without error."""
        listeners.start(fake_bus)
        # Should not raise
        fake_bus.emit("memory.stored", {"content_preview": "some text"})

    def test_empty_content_skips(
        self, listeners: BridgeEventListeners, fake_bus: FakeEventBus,
    ) -> None:
        """Empty content should skip without error."""
        listeners.start(fake_bus)
        fake_bus.emit("memory.stored", {"fact_id": "f1", "content_preview": ""})


class TestNodeDeletedListener:
    """Test on_code_node_deleted handler."""

    def test_marks_links_stale(
        self,
        db: CodeGraphDatabase,
        listeners: BridgeEventListeners,
        fake_bus: FakeEventBus,
    ) -> None:
        from superlocalmemory.code_graph.models import GraphNode, NodeKind
        db.upsert_node(GraphNode(
            node_id="n1", kind=NodeKind.FUNCTION,
            name="old_func", qualified_name="m.py::old_func",
            file_path="m.py", language="python",
        ))
        db.upsert_link(CodeMemoryLink(
            link_id="L1", code_node_id="n1", slm_fact_id="fact-200",
            link_type=LinkType.MENTIONS, confidence=0.9,
            created_at="2026-01-01", is_stale=False,
        ))

        listeners.start(fake_bus)
        fake_bus.emit("code_graph.node_deleted", {
            "node_id": "n1",
            "qualified_name": "m.py::old_func",
        })

        links = db.get_links_for_node("n1")
        assert all(link.is_stale for link in links)

    def test_no_node_id_skips(
        self, listeners: BridgeEventListeners, fake_bus: FakeEventBus,
    ) -> None:
        listeners.start(fake_bus)
        fake_bus.emit("code_graph.node_deleted", {})


class TestNodeChangedListener:
    """Test on_code_node_changed handler."""

    def test_clears_last_verified(
        self,
        db: CodeGraphDatabase,
        listeners: BridgeEventListeners,
        fake_bus: FakeEventBus,
    ) -> None:
        from superlocalmemory.code_graph.models import GraphNode, NodeKind
        db.upsert_node(GraphNode(
            node_id="n1", kind=NodeKind.FUNCTION,
            name="changed_func", qualified_name="m.py::changed_func",
            file_path="m.py", language="python",
        ))
        db.upsert_link(CodeMemoryLink(
            link_id="L2", code_node_id="n1", slm_fact_id="fact-300",
            link_type=LinkType.MENTIONS, confidence=0.9,
            created_at="2026-01-01", last_verified="2026-01-01",
            is_stale=False,
        ))

        listeners.start(fake_bus)
        fake_bus.emit("code_graph.node_changed", {"node_id": "n1"})

        links = db.get_links_for_node("n1")
        assert len(links) == 1
        assert links[0].last_verified is None


class TestErrorIsolation:
    """Test HR-5: listeners NEVER raise."""

    def test_memory_stored_error_isolated(
        self, listeners: BridgeEventListeners, fake_bus: FakeEventBus,
    ) -> None:
        """Even if entity_resolver raises, listener should not propagate."""
        listeners._entity_resolver = MagicMock()
        listeners._entity_resolver.resolve.side_effect = RuntimeError("boom")

        listeners.start(fake_bus)
        # Should NOT raise
        fake_bus.emit("memory.stored", {
            "fact_id": "f1", "content_preview": "test text",
        })

    def test_node_deleted_error_isolated(
        self, listeners: BridgeEventListeners, fake_bus: FakeEventBus,
    ) -> None:
        listeners._temporal_checker = MagicMock()
        listeners._temporal_checker.mark_links_stale.side_effect = RuntimeError("boom")

        listeners.start(fake_bus)
        fake_bus.emit("code_graph.node_deleted", {"node_id": "n1"})

    def test_node_changed_error_isolated(
        self,
        db: CodeGraphDatabase,
        listeners: BridgeEventListeners,
        fake_bus: FakeEventBus,
    ) -> None:
        """Even if DB write fails, listener should not propagate."""
        listeners.start(fake_bus)

        # Mock db to raise on execute_write
        original = db.execute_write
        db.execute_write = MagicMock(side_effect=RuntimeError("db error"))

        # Should NOT raise
        fake_bus.emit("code_graph.node_changed", {"node_id": "n1"})

        # Restore
        db.execute_write = original
