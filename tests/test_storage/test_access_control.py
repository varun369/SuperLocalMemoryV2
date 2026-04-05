# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for superlocalmemory.storage.access_control — ABAC system.

Covers:
  - Grant + check permission
  - Revoke access
  - Default profile read access
  - ABAC levels (OWNER, AGENT, READONLY, NONE)
  - require_permission raises PermissionError
  - Export + import grants
"""

from __future__ import annotations

import pytest

from superlocalmemory.storage.access_control import (
    AccessController,
    AccessGrant,
    AccessLevel,
    Permission,
)


@pytest.fixture()
def ac() -> AccessController:
    """Fresh access controller."""
    return AccessController()


# ---------------------------------------------------------------------------
# Enum coverage
# ---------------------------------------------------------------------------

class TestPermissionEnum:
    def test_all_values(self) -> None:
        expected = {"read", "write", "delete", "export", "admin"}
        assert {p.value for p in Permission} == expected


class TestAccessLevelEnum:
    def test_all_values(self) -> None:
        expected = {"owner", "agent", "readonly", "none"}
        assert {a.value for a in AccessLevel} == expected


# ---------------------------------------------------------------------------
# Grant + Check
# ---------------------------------------------------------------------------

class TestGrantAndCheck:
    def test_grant_owner_has_all_permissions(self, ac: AccessController) -> None:
        ac.grant_access("agent_1", "profile_a", AccessLevel.OWNER)
        for perm in Permission:
            assert ac.check_permission("agent_1", "profile_a", perm) is True

    def test_grant_agent_has_read_write(self, ac: AccessController) -> None:
        ac.grant_access("agent_2", "profile_b", AccessLevel.AGENT)
        assert ac.check_permission("agent_2", "profile_b", Permission.READ) is True
        assert ac.check_permission("agent_2", "profile_b", Permission.WRITE) is True
        assert ac.check_permission("agent_2", "profile_b", Permission.DELETE) is False
        assert ac.check_permission("agent_2", "profile_b", Permission.EXPORT) is False
        assert ac.check_permission("agent_2", "profile_b", Permission.ADMIN) is False

    def test_grant_readonly_has_read_only(self, ac: AccessController) -> None:
        ac.grant_access("agent_3", "profile_c", AccessLevel.READONLY)
        assert ac.check_permission("agent_3", "profile_c", Permission.READ) is True
        assert ac.check_permission("agent_3", "profile_c", Permission.WRITE) is False
        assert ac.check_permission("agent_3", "profile_c", Permission.DELETE) is False

    def test_grant_none_has_no_permissions(self, ac: AccessController) -> None:
        ac.grant_access("agent_4", "profile_d", AccessLevel.NONE)
        for perm in Permission:
            assert ac.check_permission("agent_4", "profile_d", perm) is False

    def test_grant_returns_access_grant(self, ac: AccessController) -> None:
        grant = ac.grant_access("a1", "p1", AccessLevel.OWNER, granted_by="admin")
        assert isinstance(grant, AccessGrant)
        assert grant.subject_id == "a1"
        assert grant.profile_id == "p1"
        assert grant.access_level == AccessLevel.OWNER
        assert grant.granted_by == "admin"
        assert grant.granted_at  # Non-empty


# ---------------------------------------------------------------------------
# Default profile read access
# ---------------------------------------------------------------------------

class TestDefaultProfileAccess:
    def test_unknown_agent_can_read_default(self, ac: AccessController) -> None:
        assert ac.check_permission("unknown_agent", "default", Permission.READ) is True

    def test_unknown_agent_cannot_write_default(self, ac: AccessController) -> None:
        assert ac.check_permission("unknown_agent", "default", Permission.WRITE) is False

    def test_unknown_agent_cannot_read_non_default(self, ac: AccessController) -> None:
        assert ac.check_permission("unknown_agent", "custom", Permission.READ) is False


# ---------------------------------------------------------------------------
# Revoke
# ---------------------------------------------------------------------------

class TestRevoke:
    def test_revoke_removes_access(self, ac: AccessController) -> None:
        ac.grant_access("a_rev", "p_rev", AccessLevel.OWNER)
        assert ac.check_permission("a_rev", "p_rev", Permission.READ) is True

        ac.revoke_access("a_rev", "p_rev")
        assert ac.check_permission("a_rev", "p_rev", Permission.READ) is False

    def test_revoke_nonexistent_is_noop(self, ac: AccessController) -> None:
        # Should not raise
        ac.revoke_access("ghost_agent", "ghost_profile")


# ---------------------------------------------------------------------------
# require_permission
# ---------------------------------------------------------------------------

class TestRequirePermission:
    def test_raises_on_missing_permission(self, ac: AccessController) -> None:
        with pytest.raises(PermissionError, match="lacks write"):
            ac.require_permission("no_grant_agent", "some_profile", Permission.WRITE)

    def test_passes_with_valid_permission(self, ac: AccessController) -> None:
        ac.grant_access("good_agent", "good_profile", AccessLevel.OWNER)
        # Should NOT raise
        ac.require_permission("good_agent", "good_profile", Permission.WRITE)

    def test_raises_message_includes_subject_and_profile(self, ac: AccessController) -> None:
        with pytest.raises(PermissionError) as exc_info:
            ac.require_permission("agent_x", "profile_y", Permission.DELETE)
        msg = str(exc_info.value)
        assert "agent_x" in msg
        assert "profile_y" in msg
        assert "delete" in msg


# ---------------------------------------------------------------------------
# get_access_level
# ---------------------------------------------------------------------------

class TestGetAccessLevel:
    def test_returns_granted_level(self, ac: AccessController) -> None:
        ac.grant_access("a_lvl", "p_lvl", AccessLevel.AGENT)
        assert ac.get_access_level("a_lvl", "p_lvl") == AccessLevel.AGENT

    def test_returns_none_for_unknown(self, ac: AccessController) -> None:
        assert ac.get_access_level("unknown", "unknown") == AccessLevel.NONE


# ---------------------------------------------------------------------------
# list_grants
# ---------------------------------------------------------------------------

class TestListGrants:
    def test_list_all_grants(self, ac: AccessController) -> None:
        ac.grant_access("a1", "p1", AccessLevel.OWNER)
        ac.grant_access("a2", "p2", AccessLevel.READONLY)
        grants = ac.list_grants()
        assert len(grants) == 2

    def test_list_grants_filtered_by_profile(self, ac: AccessController) -> None:
        ac.grant_access("a1", "p1", AccessLevel.OWNER)
        ac.grant_access("a2", "p2", AccessLevel.READONLY)
        grants = ac.list_grants(profile_id="p1")
        assert len(grants) == 1
        assert grants[0].subject_id == "a1"


# ---------------------------------------------------------------------------
# Export + Import
# ---------------------------------------------------------------------------

class TestExportImport:
    def test_export_returns_dicts(self, ac: AccessController) -> None:
        ac.grant_access("a_exp", "p_exp", AccessLevel.AGENT, granted_by="sys")
        data = ac.export_grants()
        assert len(data) == 1
        d = data[0]
        assert d["subject_id"] == "a_exp"
        assert d["access_level"] == "agent"
        assert d["granted_by"] == "sys"

    def test_import_restores_grants(self, ac: AccessController) -> None:
        exported = [
            {
                "subject_id": "a_imp",
                "profile_id": "p_imp",
                "access_level": "owner",
                "granted_by": "import_test",
            }
        ]
        ac.import_grants(exported)
        assert ac.check_permission("a_imp", "p_imp", Permission.ADMIN) is True

    def test_roundtrip_export_import(self, ac: AccessController) -> None:
        ac.grant_access("a_rt", "p_rt", AccessLevel.READONLY)
        exported = ac.export_grants()

        new_ac = AccessController()
        new_ac.import_grants(exported)
        assert new_ac.check_permission("a_rt", "p_rt", Permission.READ) is True
        assert new_ac.check_permission("a_rt", "p_rt", Permission.WRITE) is False
