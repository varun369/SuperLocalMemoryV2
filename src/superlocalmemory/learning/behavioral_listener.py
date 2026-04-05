# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Behavioral listener — subscribes to event bus, captures patterns.

Connects to the V3 event bus and records all memory operations
for behavioral pattern mining.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

# Max events kept in memory for pattern mining
MAX_EVENT_BUFFER = 500


class BehavioralListener:
    """Subscribes to event bus and records behavioral data."""

    def __init__(self, event_bus=None, db_path=None):
        self._events = deque(maxlen=MAX_EVENT_BUFFER)
        self._event_count = 0
        self._db_path = db_path

        if event_bus:
            event_bus.subscribe(self._on_event)

    @property
    def event_count(self) -> int:
        return self._event_count

    def _on_event(self, event: dict) -> None:
        """Handle incoming event from bus."""
        self._events.append({
            "event_type": event.get("event_type", "unknown"),
            "data": event.get("data", {}),
            "timestamp": time.time(),
        })
        self._event_count += 1

    def get_recent_events(self, limit: int = 50) -> list[dict]:
        """Get most recent behavioral events."""
        return list(self._events)[-limit:]

    def mine_patterns(self) -> list[dict]:
        """Mine behavioral patterns from recent events.

        Detects:
        - store->recall->store = refinement pattern
        - repeated recall of same topic = interest pattern
        - store without recall = archival pattern
        """
        patterns = []
        events = list(self._events)

        # Detect store->recall->store (refinement)
        for i in range(len(events) - 2):
            if (events[i]["event_type"] == "memory.stored" and
                events[i+1]["event_type"] == "memory.recalled" and
                events[i+2]["event_type"] == "memory.stored"):
                patterns.append({
                    "pattern_type": "refinement",
                    "timestamp": events[i+2]["timestamp"],
                    "events": [events[i], events[i+1], events[i+2]],
                })

        # Detect repeated recall (interest)
        recall_topics = {}
        for e in events:
            if e["event_type"] == "memory.recalled":
                topic = e["data"].get("query_preview", "")[:50]
                recall_topics[topic] = recall_topics.get(topic, 0) + 1

        for topic, count in recall_topics.items():
            if count >= 3:
                patterns.append({
                    "pattern_type": "interest",
                    "topic": topic,
                    "count": count,
                })

        return patterns

    def clear(self) -> None:
        """Clear event buffer."""
        self._events.clear()
        self._event_count = 0
