# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com
"""Tests for V3 Event Bus -- Task 2 of V3 build."""
import pytest
from pathlib import Path
from superlocalmemory.infra.event_bus import EventBus, VALID_EVENT_TYPES


@pytest.fixture
def bus(tmp_path):
    """Create a fresh EventBus for each test."""
    EventBus.reset_instance(tmp_path / "test.db")
    return EventBus.get_instance(tmp_path / "test.db")


def test_v3_event_types_present():
    assert "memory.stored" in VALID_EVENT_TYPES
    assert "trust.signal" in VALID_EVENT_TYPES
    assert "compliance.audit" in VALID_EVENT_TYPES
    assert "learning.feedback" in VALID_EVENT_TYPES


def test_publish_and_subscribe(bus):
    received = []
    bus.subscribe(lambda e: received.append(e))
    bus.publish("memory.stored", {"fact_id": "f1"})
    assert len(received) == 1
    assert received[0]["event_type"] == "memory.stored"


def test_emit_and_add_listener_aliases(bus):
    received = []
    bus.add_listener(lambda e: received.append(e))
    bus.emit("memory.recalled", {"query": "test"})
    assert len(received) == 1


def test_multiple_subscribers(bus):
    results = []
    bus.subscribe(lambda e: results.append("a"))
    bus.subscribe(lambda e: results.append("b"))
    bus.publish("memory.stored", {})
    assert results == ["a", "b"]


def test_unsubscribe(bus):
    received = []
    handler = lambda e: received.append(e)
    bus.subscribe(handler)
    bus.unsubscribe(handler)
    bus.publish("memory.stored", {})
    assert len(received) == 0


def test_subscriber_error_does_not_crash(bus):
    bus.subscribe(lambda e: 1/0)
    bus.publish("memory.stored", {})  # should not raise


def test_events_persisted(bus):
    bus.publish("memory.stored", {"fact_id": "f1"})
    bus.publish("memory.recalled", {"query": "test"})
    events = bus.get_recent_events(limit=10)
    assert len(events) >= 2


def test_event_stats(bus):
    bus.publish("memory.stored", {})
    bus.publish("memory.stored", {})
    bus.publish("memory.recalled", {})
    stats = bus.get_event_stats()
    assert stats.get("memory.stored", 0) >= 2
    assert stats.get("memory.recalled", 0) >= 1


def test_buffered_events(bus):
    bus.publish("memory.stored", {"n": 1})
    bus.publish("memory.stored", {"n": 2})
    buffered = bus.get_buffered_events(since_seq=0)
    assert len(buffered) >= 2


def test_singleton_pattern(tmp_path):
    db = tmp_path / "singleton.db"
    EventBus.reset_instance(db)
    bus1 = EventBus.get_instance(db)
    bus2 = EventBus.get_instance(db)
    assert bus1 is bus2
