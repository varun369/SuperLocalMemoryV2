# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Post-install script for npm package.

Runs after `npm install -g superlocalmemory`. Detects V2 installations,
prompts for migration, and runs the setup wizard for new users.
"""

from __future__ import annotations

import sys
from pathlib import Path


def run_post_install():
    """Main post-install entry point."""
    print()
    print("SuperLocalMemory V3")
    print("=" * 30)
    print()

    # Step 1: Check for V2 installation
    from superlocalmemory.storage.v2_migrator import V2Migrator

    migrator = V2Migrator()

    if migrator.detect_v2() and not migrator.is_already_migrated():
        _handle_v2_upgrade(migrator)
    else:
        _handle_fresh_install()


def _handle_v2_upgrade(migrator):
    """Handle upgrade from V2."""
    stats = migrator.get_v2_stats()

    print("Existing V2 installation detected!")
    print(f"  Database: {stats.get('db_path', '~/.superlocalmemory/memory.db')}")
    print(f"  Memories: {stats.get('memory_count', 'unknown')}")
    print(f"  Profiles: {stats.get('profile_count', 1)}")
    print()
    print("V3 requires a one-time migration to upgrade your database.")
    print("Your data will be preserved. A backup is created automatically.")
    print("You can rollback anytime within 30 days.")
    print()

    choice = input("Run migration now? [Y/n]: ").strip().lower()

    if choice in ("", "y", "yes"):
        print()
        print("Migrating...")
        result = migrator.migrate()

        if result.get("success"):
            print()
            for step in result.get("steps", []):
                print(f"  [ok] {step}")
            print()
            print("Migration complete!")
            print(f"  V3 database: {result.get('v3_db', '')}")
            print(f"  Backup: {result.get('backup_db', '')}")
            print()
            # Run setup wizard after migration
            _run_setup()
        else:
            print(f"Migration failed: {result.get('error', 'unknown')}")
            print("Your V2 data is untouched. Run `slm migrate` to try again.")
            sys.exit(1)
    else:
        print()
        print("Migration skipped. Run `slm migrate` when ready.")
        print("Note: V3 features are unavailable until you migrate.")


def _handle_fresh_install():
    """Handle fresh install (no V2 detected)."""
    from superlocalmemory.storage.v2_migrator import V2Migrator

    migrator = V2Migrator()

    if migrator.is_already_migrated():
        print("V3 already configured. Run `slm setup` to reconfigure.")
        return

    print("Welcome! Let's set up SuperLocalMemory V3.")
    _run_setup()


def _run_setup():
    """Run the interactive setup wizard."""
    from superlocalmemory.cli.setup_wizard import run_wizard

    run_wizard()


if __name__ == "__main__":
    run_post_install()
