# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for superlocalmemory.core.profiles — ProfileManager CRUD.

Covers:
  - Create + list + switch + delete + rename + update + export
  - Validation (bad names rejected)
  - Cannot delete "default"
  - Switch fires on_profile_switch callback
  - Persistence across instances
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from superlocalmemory.core.profiles import ProfileManager
from superlocalmemory.storage.models import Mode, Profile


@pytest.fixture()
def pm(tmp_path: Path) -> ProfileManager:
    """Fresh ProfileManager in a temp directory."""
    return ProfileManager(tmp_path)


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------

class TestCreateProfile:
    def test_create_returns_profile(self, pm: ProfileManager) -> None:
        p = pm.create_profile("work", description="Work profile")
        assert isinstance(p, Profile)
        assert p.name == "work"
        assert p.description == "Work profile"
        assert p.mode == Mode.A

    def test_create_with_mode_b(self, pm: ProfileManager) -> None:
        p = pm.create_profile("research", mode=Mode.B)
        assert p.mode == Mode.B

    def test_create_duplicate_raises(self, pm: ProfileManager) -> None:
        pm.create_profile("dup")
        with pytest.raises(ValueError, match="already exists"):
            pm.create_profile("dup")

    def test_create_default_name_raises(self, pm: ProfileManager) -> None:
        """'default' already exists — creating again should raise."""
        with pytest.raises(ValueError, match="already exists"):
            pm.create_profile("default")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestNameValidation:
    def test_empty_name_rejected(self, pm: ProfileManager) -> None:
        with pytest.raises(ValueError):
            pm.create_profile("")

    def test_too_long_name_rejected(self, pm: ProfileManager) -> None:
        with pytest.raises(ValueError):
            pm.create_profile("a" * 51)

    def test_special_chars_rejected(self, pm: ProfileManager) -> None:
        with pytest.raises(ValueError):
            pm.create_profile("bad name!")

    def test_starts_with_dash_rejected(self, pm: ProfileManager) -> None:
        with pytest.raises(ValueError):
            pm.create_profile("-invalid")

    def test_valid_names_accepted(self, pm: ProfileManager) -> None:
        pm.create_profile("valid-name")
        pm.create_profile("also_valid")
        pm.create_profile("CamelCase123")
        assert len(pm.list_profiles()) == 4  # default + 3


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

class TestListProfiles:
    def test_default_always_present(self, pm: ProfileManager) -> None:
        profiles = pm.list_profiles()
        assert len(profiles) >= 1
        assert profiles[0].name == "default"

    def test_sorted_default_first(self, pm: ProfileManager) -> None:
        pm.create_profile("zzz")
        pm.create_profile("aaa")
        profiles = pm.list_profiles()
        assert profiles[0].name == "default"
        assert profiles[1].name == "aaa"
        assert profiles[2].name == "zzz"


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

class TestGetProfile:
    def test_get_existing(self, pm: ProfileManager) -> None:
        pm.create_profile("test_get")
        p = pm.get_profile("test_get")
        assert p is not None
        assert p.name == "test_get"

    def test_get_nonexistent_returns_none(self, pm: ProfileManager) -> None:
        assert pm.get_profile("ghost") is None

    def test_get_active_profile_default(self, pm: ProfileManager) -> None:
        active = pm.get_active_profile()
        assert active.name == "default"


# ---------------------------------------------------------------------------
# Switch
# ---------------------------------------------------------------------------

class TestSwitchProfile:
    def test_switch_updates_active(self, pm: ProfileManager) -> None:
        pm.create_profile("switch_target")
        result = pm.switch_profile("switch_target")
        assert result.name == "switch_target"
        assert pm.get_active_profile().name == "switch_target"

    def test_switch_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(KeyError, match="does not exist"):
            pm.switch_profile("nonexistent")

    def test_switch_fires_callback(self, pm: ProfileManager) -> None:
        called_with: list[Profile] = []
        pm.on_profile_switch = lambda p: called_with.append(p)

        pm.create_profile("callback_target")
        pm.switch_profile("callback_target")

        assert len(called_with) == 1
        assert called_with[0].name == "callback_target"

    def test_switch_updates_last_used(self, pm: ProfileManager) -> None:
        pm.create_profile("lu_test")
        result = pm.switch_profile("lu_test")
        assert result.last_used is not None


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class TestDeleteProfile:
    def test_cannot_delete_default(self, pm: ProfileManager) -> None:
        with pytest.raises(ValueError, match="Cannot delete"):
            pm.delete_profile("default")

    def test_delete_existing(self, pm: ProfileManager) -> None:
        pm.create_profile("to_delete")
        pm.delete_profile("to_delete")
        assert pm.get_profile("to_delete") is None

    def test_delete_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(KeyError, match="does not exist"):
            pm.delete_profile("ghost")

    def test_delete_active_falls_back_to_default(self, pm: ProfileManager) -> None:
        pm.create_profile("active_del")
        pm.switch_profile("active_del")
        pm.delete_profile("active_del")
        assert pm.get_active_profile().name == "default"


# ---------------------------------------------------------------------------
# Rename
# ---------------------------------------------------------------------------

class TestRenameProfile:
    def test_rename_succeeds(self, pm: ProfileManager) -> None:
        pm.create_profile("old_name")
        pm.rename_profile("old_name", "new_name")
        assert pm.get_profile("old_name") is None
        assert pm.get_profile("new_name") is not None

    def test_cannot_rename_default(self, pm: ProfileManager) -> None:
        with pytest.raises(ValueError, match="Cannot rename"):
            pm.rename_profile("default", "not_default")

    def test_rename_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(KeyError, match="does not exist"):
            pm.rename_profile("ghost", "new")

    def test_rename_to_existing_raises(self, pm: ProfileManager) -> None:
        pm.create_profile("src")
        pm.create_profile("dst")
        with pytest.raises(ValueError, match="already exists"):
            pm.rename_profile("src", "dst")

    def test_rename_active_profile_updates_active(self, pm: ProfileManager) -> None:
        pm.create_profile("active_rename")
        pm.switch_profile("active_rename")
        pm.rename_profile("active_rename", "renamed_active")
        assert pm.get_active_profile().name == "renamed_active"


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    def test_update_description(self, pm: ProfileManager) -> None:
        pm.create_profile("upd")
        updated = pm.update_profile("upd", description="new desc")
        assert updated.description == "new desc"

    def test_update_mode(self, pm: ProfileManager) -> None:
        pm.create_profile("upd_mode")
        updated = pm.update_profile("upd_mode", mode=Mode.C)
        assert updated.mode == Mode.C

    def test_update_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(KeyError, match="does not exist"):
            pm.update_profile("ghost", description="nope")

    def test_update_ignores_disallowed_fields(self, pm: ProfileManager) -> None:
        pm.create_profile("upd_safe")
        original_id = pm.get_profile("upd_safe").profile_id
        updated = pm.update_profile("upd_safe", profile_id="hacked")
        # profile_id should NOT change (not in allowed set)
        assert updated.profile_id == original_id


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class TestExportProfile:
    def test_export_returns_dict(self, pm: ProfileManager) -> None:
        pm.create_profile("exp", description="exported")
        data = pm.export_profile("exp")
        assert isinstance(data, dict)
        assert data["name"] == "exp"
        assert data["description"] == "exported"

    def test_export_nonexistent_raises(self, pm: ProfileManager) -> None:
        with pytest.raises(KeyError, match="does not exist"):
            pm.export_profile("ghost")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_survives_reload(self, tmp_path: Path) -> None:
        pm1 = ProfileManager(tmp_path)
        pm1.create_profile("persistent", description="survives")
        pm1.switch_profile("persistent")

        # Create a second instance pointing to same directory
        pm2 = ProfileManager(tmp_path)
        p = pm2.get_profile("persistent")
        assert p is not None
        assert p.description == "survives"
        assert pm2.get_active_profile().name == "persistent"

    def test_profiles_json_exists(self, tmp_path: Path) -> None:
        ProfileManager(tmp_path)
        json_path = tmp_path / "profiles.json"
        assert json_path.exists()
