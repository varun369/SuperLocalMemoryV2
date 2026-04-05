# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for superlocalmemory.core.registry — AgentRegistry.

Covers:
  - Register + unregister + list
  - Advisory lock (ProfileLockError)
  - Persistence across instances
  - get_agent_profile
"""

from __future__ import annotations

from pathlib import Path

import pytest

from superlocalmemory.core.registry import AgentRegistry, ProfileLockError


@pytest.fixture()
def registry(tmp_path: Path) -> AgentRegistry:
    """Fresh registry with JSON persistence in temp dir."""
    return AgentRegistry(persist_path=tmp_path / "registry.json")


@pytest.fixture()
def memory_registry() -> AgentRegistry:
    """In-memory registry (no persistence)."""
    return AgentRegistry(persist_path=None)


# ---------------------------------------------------------------------------
# Register / Unregister
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_agent(self, registry: AgentRegistry) -> None:
        registry.register_agent("agent_1", "profile_a")
        agents = registry.list_agents()
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "agent_1"
        assert agents[0]["profile_id"] == "profile_a"

    def test_register_multiple_agents(self, registry: AgentRegistry) -> None:
        registry.register_agent("a1", "p1")
        registry.register_agent("a2", "p2")
        agents = registry.list_agents()
        assert len(agents) == 2

    def test_unregister_agent(self, registry: AgentRegistry) -> None:
        registry.register_agent("a_unreg", "p1")
        registry.unregister_agent("a_unreg")
        assert len(registry.list_agents()) == 0

    def test_unregister_nonexistent_is_noop(self, registry: AgentRegistry) -> None:
        # Should not raise
        registry.unregister_agent("ghost")

    def test_re_register_same_agent(self, registry: AgentRegistry) -> None:
        """Re-registering an agent should update its profile."""
        registry.register_agent("a_re", "p1")
        registry.register_agent("a_re", "p2")
        agents = registry.list_agents()
        assert len(agents) == 1
        assert agents[0]["profile_id"] == "p2"


# ---------------------------------------------------------------------------
# Advisory Lock
# ---------------------------------------------------------------------------

class TestAdvisoryLock:
    def test_second_agent_blocked_on_same_profile(
        self, registry: AgentRegistry
    ) -> None:
        registry.register_agent("a1", "shared_profile")
        with pytest.raises(ProfileLockError, match="locked by agent"):
            registry.register_agent("a2", "shared_profile")

    def test_same_agent_can_re_register_same_profile(
        self, registry: AgentRegistry
    ) -> None:
        registry.register_agent("a1", "p1")
        # Re-registering the same agent on the same profile should work
        registry.register_agent("a1", "p1")

    def test_lock_released_on_unregister(
        self, registry: AgentRegistry
    ) -> None:
        registry.register_agent("a_lock", "p_lock")
        registry.unregister_agent("a_lock")
        # Now another agent should be able to register on the same profile
        registry.register_agent("a_new", "p_lock")
        assert len(registry.list_agents()) == 1

    def test_different_profiles_no_conflict(
        self, registry: AgentRegistry
    ) -> None:
        registry.register_agent("a1", "p1")
        registry.register_agent("a2", "p2")
        assert len(registry.list_agents()) == 2


# ---------------------------------------------------------------------------
# get_agent_profile
# ---------------------------------------------------------------------------

class TestGetAgentProfile:
    def test_returns_correct_profile(self, registry: AgentRegistry) -> None:
        registry.register_agent("a_prof", "p_prof")
        assert registry.get_agent_profile("a_prof") == "p_prof"

    def test_raises_for_unregistered(self, registry: AgentRegistry) -> None:
        with pytest.raises(KeyError, match="not registered"):
            registry.get_agent_profile("unknown")


# ---------------------------------------------------------------------------
# list_agents
# ---------------------------------------------------------------------------

class TestListAgents:
    def test_empty_initially(self, registry: AgentRegistry) -> None:
        assert registry.list_agents() == []

    def test_contains_registered_at(self, registry: AgentRegistry) -> None:
        registry.register_agent("a_time", "p_time")
        agents = registry.list_agents()
        assert "registered_at" in agents[0]
        assert isinstance(agents[0]["registered_at"], float)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_survives_reload(self, tmp_path: Path) -> None:
        path = tmp_path / "reg.json"
        reg1 = AgentRegistry(persist_path=path)
        reg1.register_agent("persistent_agent", "persistent_profile")

        reg2 = AgentRegistry(persist_path=path)
        agents = reg2.list_agents()
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "persistent_agent"

    def test_lock_persists_across_reload(self, tmp_path: Path) -> None:
        path = tmp_path / "reg_lock.json"
        reg1 = AgentRegistry(persist_path=path)
        reg1.register_agent("a1", "p_locked")

        reg2 = AgentRegistry(persist_path=path)
        with pytest.raises(ProfileLockError):
            reg2.register_agent("a2", "p_locked")

    def test_in_memory_does_not_persist(self) -> None:
        reg1 = AgentRegistry(persist_path=None)
        reg1.register_agent("a1", "p1")
        # New in-memory instance starts fresh
        reg2 = AgentRegistry(persist_path=None)
        assert len(reg2.list_agents()) == 0

    def test_corrupt_file_handled(self, tmp_path: Path) -> None:
        path = tmp_path / "corrupt.json"
        path.write_text("NOT JSON", encoding="utf-8")
        reg = AgentRegistry(persist_path=path)
        # Should start fresh, not crash
        assert len(reg.list_agents()) == 0
