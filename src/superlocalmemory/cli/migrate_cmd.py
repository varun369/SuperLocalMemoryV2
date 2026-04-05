# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Migration CLI command implementation."""

from __future__ import annotations


def cmd_migrate(args):
    """Run V2 to V3 migration or rollback."""
    from superlocalmemory.storage.v2_migrator import V2Migrator

    migrator = V2Migrator()

    if getattr(args, "rollback", False):
        print("Rolling back V3 migration...")
        result = migrator.rollback()
        if result.get("success"):
            for step in result.get("steps", []):
                print(f"  [ok] {step}")
            print("Rollback complete. V2 restored.")
        else:
            print(f"Rollback failed: {result.get('error', 'unknown')}")
        return

    if not migrator.detect_v2():
        print("No V2 installation found. Nothing to migrate.")
        return

    if migrator.is_already_migrated():
        print("Already migrated to V3.")
        return

    stats = migrator.get_v2_stats()
    print("V2 installation found:")
    print(f"  Memories: {stats.get('memory_count', 'unknown')}")
    print(f"  Size: {stats.get('db_size_mb', '?')} MB")
    print()

    import sys
    if sys.stdin.isatty():
        confirm = input("Proceed with migration? [Y/n] ").strip().lower()
        if confirm not in ("", "y", "yes"):
            print("Migration cancelled.")
            return

    result = migrator.migrate()
    if result.get("success"):
        for step in result.get("steps", []):
            print(f"  [ok] {step}")
        print()
        print("Migration complete!")
    else:
        print(f"Migration failed: {result.get('error', 'unknown')}")
