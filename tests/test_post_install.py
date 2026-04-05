# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Tests for Post-Install & Migration CLI -- Task 19 of V3 build."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers: stub out V2Migrator so imports resolve without the real module
# ---------------------------------------------------------------------------

def _make_fake_v2_migrator_module(
    detect_v2: bool = False,
    is_already_migrated: bool = False,
    v2_stats: dict | None = None,
    migrate_result: dict | None = None,
    rollback_result: dict | None = None,
):
    """Return a fake ``superlocalmemory.storage.v2_migrator`` module."""
    if v2_stats is None:
        v2_stats = {"memory_count": 0, "profile_count": 1, "db_path": "/tmp/mem.db"}
    if migrate_result is None:
        migrate_result = {"success": True, "steps": ["backup", "schema"], "v3_db": "/tmp/v3.db", "backup_db": "/tmp/bak.db"}
    if rollback_result is None:
        rollback_result = {"success": True, "steps": ["restore"]}

    class FakeV2Migrator:
        def detect_v2(self):
            return detect_v2

        def is_already_migrated(self):
            return is_already_migrated

        def get_v2_stats(self):
            return v2_stats

        def migrate(self):
            return migrate_result

        def rollback(self):
            return rollback_result

    mod = types.ModuleType("superlocalmemory.storage.v2_migrator")
    mod.V2Migrator = FakeV2Migrator  # type: ignore[attr-defined]
    return mod


# ---------------------------------------------------------------------------
# Tests: post_install.py
# ---------------------------------------------------------------------------

class TestPostInstallImports:
    """Verify post_install module is importable and callable."""

    def test_run_post_install_importable(self):
        from superlocalmemory.cli.post_install import run_post_install

        assert callable(run_post_install)

    def test_handle_v2_upgrade_importable(self):
        from superlocalmemory.cli.post_install import _handle_v2_upgrade

        assert callable(_handle_v2_upgrade)

    def test_handle_fresh_install_importable(self):
        from superlocalmemory.cli.post_install import _handle_fresh_install

        assert callable(_handle_fresh_install)


class TestPostInstallFreshInstall:
    """Fresh install path (no V2 detected)."""

    def test_fresh_install_runs_setup(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(detect_v2=False, is_already_migrated=False)
        wizard_called = MagicMock()

        with (
            patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}),
            patch("superlocalmemory.cli.setup_wizard.run_wizard", wizard_called),
        ):
            # Re-import to pick up the patched module
            from superlocalmemory.cli.post_install import run_post_install

            run_post_install()

        captured = capsys.readouterr()
        assert "SuperLocalMemory V3" in captured.out
        wizard_called.assert_called_once()

    def test_already_migrated_skips_setup(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(detect_v2=False, is_already_migrated=True)

        with patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}):
            from superlocalmemory.cli.post_install import _handle_fresh_install

            _handle_fresh_install()

        captured = capsys.readouterr()
        assert "already configured" in captured.out


class TestPostInstallV2Upgrade:
    """V2 upgrade path."""

    def test_v2_upgrade_accepted(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(
            detect_v2=True,
            is_already_migrated=False,
            v2_stats={"db_path": "/home/.claude-memory/memory.db", "memory_count": 42, "profile_count": 2},
            migrate_result={"success": True, "steps": ["backup", "schema", "reindex"], "v3_db": "/v3.db", "backup_db": "/bak.db"},
        )
        wizard_called = MagicMock()

        with (
            patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}),
            patch("builtins.input", return_value="y"),
            patch("superlocalmemory.cli.setup_wizard.run_wizard", wizard_called),
        ):
            from superlocalmemory.cli.post_install import _handle_v2_upgrade
            from superlocalmemory.storage.v2_migrator import V2Migrator

            _handle_v2_upgrade(V2Migrator())

        captured = capsys.readouterr()
        assert "V2 installation detected" in captured.out
        assert "Migration complete" in captured.out
        assert "[ok] backup" in captured.out
        wizard_called.assert_called_once()

    def test_v2_upgrade_declined(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(detect_v2=True, is_already_migrated=False)

        with (
            patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}),
            patch("builtins.input", return_value="n"),
        ):
            from superlocalmemory.cli.post_install import _handle_v2_upgrade
            from superlocalmemory.storage.v2_migrator import V2Migrator

            _handle_v2_upgrade(V2Migrator())

        captured = capsys.readouterr()
        assert "Migration skipped" in captured.out

    def test_v2_upgrade_migration_failure(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(
            detect_v2=True,
            is_already_migrated=False,
            migrate_result={"success": False, "error": "disk full"},
        )

        with (
            patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}),
            patch("builtins.input", return_value="y"),
            pytest.raises(SystemExit),
        ):
            from superlocalmemory.cli.post_install import _handle_v2_upgrade
            from superlocalmemory.storage.v2_migrator import V2Migrator

            _handle_v2_upgrade(V2Migrator())

        captured = capsys.readouterr()
        assert "disk full" in captured.out


# ---------------------------------------------------------------------------
# Tests: migrate_cmd.py
# ---------------------------------------------------------------------------

class TestMigrateCmdImports:
    """Verify migrate_cmd module is importable."""

    def test_cmd_migrate_importable(self):
        from superlocalmemory.cli.migrate_cmd import cmd_migrate

        assert callable(cmd_migrate)


class TestMigrateCmdNoV2:
    """Migration with no V2 present."""

    def test_no_v2_reports_nothing(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(detect_v2=False)

        class FakeArgs:
            rollback = False

        with patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}):
            from superlocalmemory.cli.migrate_cmd import cmd_migrate

            cmd_migrate(FakeArgs())

        captured = capsys.readouterr()
        assert "No V2 installation found" in captured.out


class TestMigrateCmdAlreadyMigrated:
    """Migration when already on V3."""

    def test_already_migrated(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(detect_v2=True, is_already_migrated=True)

        class FakeArgs:
            rollback = False

        with patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}):
            from superlocalmemory.cli.migrate_cmd import cmd_migrate

            cmd_migrate(FakeArgs())

        captured = capsys.readouterr()
        assert "Already migrated" in captured.out


class TestMigrateCmdSuccess:
    """Successful migration run."""

    def test_migrate_success(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(
            detect_v2=True,
            is_already_migrated=False,
            v2_stats={"memory_count": 100, "db_size_mb": 5},
            migrate_result={"success": True, "steps": ["backup created", "schema extended"]},
        )

        class FakeArgs:
            rollback = False

        with patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}):
            from superlocalmemory.cli.migrate_cmd import cmd_migrate

            cmd_migrate(FakeArgs())

        captured = capsys.readouterr()
        assert "Migration complete" in captured.out
        assert "[ok] backup created" in captured.out

    def test_migrate_failure(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(
            detect_v2=True,
            is_already_migrated=False,
            v2_stats={"memory_count": 50, "db_size_mb": 2},
            migrate_result={"success": False, "error": "corrupted table"},
        )

        class FakeArgs:
            rollback = False

        with patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}):
            from superlocalmemory.cli.migrate_cmd import cmd_migrate

            cmd_migrate(FakeArgs())

        captured = capsys.readouterr()
        assert "corrupted table" in captured.out


class TestMigrateCmdRollback:
    """Rollback path."""

    def test_rollback_success(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(
            rollback_result={"success": True, "steps": ["database restored", "config reset"]},
        )

        class FakeArgs:
            rollback = True

        with patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}):
            from superlocalmemory.cli.migrate_cmd import cmd_migrate

            cmd_migrate(FakeArgs())

        captured = capsys.readouterr()
        assert "Rollback complete" in captured.out
        assert "[ok] database restored" in captured.out

    def test_rollback_failure(self, capsys):
        fake_mod = _make_fake_v2_migrator_module(
            rollback_result={"success": False, "error": "backup not found"},
        )

        class FakeArgs:
            rollback = True

        with patch.dict(sys.modules, {"superlocalmemory.storage.v2_migrator": fake_mod}):
            from superlocalmemory.cli.migrate_cmd import cmd_migrate

            cmd_migrate(FakeArgs())

        captured = capsys.readouterr()
        assert "backup not found" in captured.out


# ---------------------------------------------------------------------------
# Tests: commands.py dispatch wiring
# ---------------------------------------------------------------------------

class TestCommandsDispatchWiring:
    """Verify commands.py routes migrate and connect correctly."""

    def test_cmd_migrate_delegates(self):
        """cmd_migrate in commands.py delegates to migrate_cmd."""
        from superlocalmemory.cli import commands

        # The function body should import migrate_cmd
        import inspect

        src = inspect.getsource(commands.cmd_migrate)
        assert "migrate_cmd" in src

    def test_cmd_connect_delegates(self):
        """cmd_connect in commands.py delegates to IDEConnector."""
        from superlocalmemory.cli import commands

        import inspect

        src = inspect.getsource(commands.cmd_connect)
        assert "IDEConnector" in src
