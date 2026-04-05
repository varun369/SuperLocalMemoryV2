# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Bridge Module

"""Event Listeners — bidirectional bridge between SLM events and code graph.

Three listeners:
- memory.stored → entity resolution + enrichment + Hebbian linking
- code_graph.node_changed → mark affected links for re-verification
- code_graph.node_deleted → mark affected links as stale

HR-5: ALL listeners catch ALL exceptions and log them — NEVER raise.
Bridge failures must not break SLM memory operations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from superlocalmemory.code_graph.bridge.entity_resolver import EntityResolver
    from superlocalmemory.code_graph.bridge.fact_enricher import FactEnricher
    from superlocalmemory.code_graph.bridge.hebbian_linker import HebbianLinker
    from superlocalmemory.code_graph.bridge.temporal_checker import TemporalChecker
    from superlocalmemory.code_graph.database import CodeGraphDatabase

logger = logging.getLogger(__name__)


class BridgeEventListeners:
    """Registers and manages bidirectional event listeners for the bridge.

    All listener callbacks are wrapped in try/except to satisfy HR-5:
    bridge failures NEVER propagate to the event bus.
    """

    def __init__(
        self,
        entity_resolver: EntityResolver,
        fact_enricher: FactEnricher,
        hebbian_linker: HebbianLinker,
        temporal_checker: TemporalChecker,
        code_graph_db: CodeGraphDatabase,
    ) -> None:
        self._entity_resolver = entity_resolver
        self._fact_enricher = fact_enricher
        self._hebbian_linker = hebbian_linker
        self._temporal_checker = temporal_checker
        self._db = code_graph_db
        self._listener_ids: list[tuple[str, Callable[..., Any]]] = []
        self._started = False

    @property
    def is_started(self) -> bool:
        """Whether listeners are currently registered."""
        return self._started

    def start(self, event_bus: Any) -> None:
        """Register all listeners on the event bus.

        Registers:
        - on_memory_stored: listens to "memory.stored"
        - on_code_node_deleted: listens to "code_graph.node_deleted"
        - on_code_node_changed: listens to "code_graph.node_changed"
        """
        if self._started:
            logger.warning("BridgeEventListeners already started")
            return

        self._event_bus = event_bus

        listeners: list[tuple[str, Callable[..., Any]]] = [
            ("memory.stored", self.on_memory_stored),
            ("code_graph.node_deleted", self.on_code_node_deleted),
            ("code_graph.node_changed", self.on_code_node_changed),
        ]

        for event_type, callback in listeners:
            try:
                event_bus.subscribe(event_type, callback)
                self._listener_ids.append((event_type, callback))
            except Exception:
                logger.error(
                    "Failed to register listener for %s",
                    event_type, exc_info=True,
                )

        self._started = True
        logger.info(
            "Bridge event listeners started (%d registered)",
            len(self._listener_ids),
        )

    def stop(self) -> None:
        """Unregister all listeners from the event bus."""
        if not self._started:
            return

        bus = getattr(self, "_event_bus", None)
        if bus is not None:
            for event_type, callback in self._listener_ids:
                try:
                    bus.unsubscribe(event_type, callback)
                except Exception:
                    logger.debug(
                        "Failed to unsubscribe %s listener",
                        event_type, exc_info=True,
                    )

        self._listener_ids.clear()
        self._started = False
        logger.info("Bridge event listeners stopped")

    # ------------------------------------------------------------------
    # Listener callbacks — NEVER raise (HR-5)
    # ------------------------------------------------------------------

    def on_memory_stored(self, event: dict[str, Any]) -> None:
        """Handle memory.stored event.

        Chains: entity_resolver → fact_enricher → hebbian_linker
        """
        try:
            payload = event.get("payload", {})
            fact_id = payload.get("fact_id")
            content = payload.get("content_preview", "")

            if not fact_id or not content:
                return

            # Step 1: Entity resolution
            links = self._entity_resolver.resolve(content, fact_id)

            if not links:
                return

            # Step 2: Fact enrichment
            matched_nodes = self._entity_resolver.get_matched_nodes(content)
            if matched_nodes:
                self._fact_enricher.enrich(
                    fact_id, matched_nodes, content,
                )

            # Step 3: Hebbian linking
            node_ids = [link.code_node_id for link in links]
            self._hebbian_linker.link(fact_id, node_ids)

        except Exception:
            logger.error(
                "Bridge: on_memory_stored failed (non-fatal)",
                exc_info=True,
            )

    def on_code_node_deleted(self, event: dict[str, Any]) -> None:
        """Handle code_graph.node_deleted event."""
        try:
            payload = event.get("payload", {})
            node_id = payload.get("node_id")

            if not node_id:
                return

            self._temporal_checker.mark_links_stale(node_id)

        except Exception:
            logger.error(
                "Bridge: on_code_node_deleted failed (non-fatal)",
                exc_info=True,
            )

    def on_code_node_changed(self, event: dict[str, Any]) -> None:
        """Handle code_graph.node_changed event.

        Flags links for re-verification by clearing last_verified.
        """
        try:
            payload = event.get("payload", {})
            node_id = payload.get("node_id")

            if not node_id:
                return

            # Mark links for re-verification
            self._db.execute_write(
                "UPDATE code_memory_links SET last_verified = NULL "
                "WHERE code_node_id = ? AND is_stale = 0",
                (node_id,),
            )

        except Exception:
            logger.error(
                "Bridge: on_code_node_changed failed (non-fatal)",
                exc_info=True,
            )
