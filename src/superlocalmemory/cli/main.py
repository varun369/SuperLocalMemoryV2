# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — CLI entry point.

Usage: slm <command> [options]

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    """Parse CLI arguments and dispatch to command handlers."""
    parser = argparse.ArgumentParser(prog="slm", description="SuperLocalMemory V3")
    sub = parser.add_subparsers(dest="command")

    # Setup
    sub.add_parser("setup", help="Run setup wizard")

    # Mode
    mode_p = sub.add_parser("mode", help="Get or set operating mode")
    mode_p.add_argument(
        "value", nargs="?", choices=["a", "b", "c"], help="Mode to set",
    )

    # Provider
    provider_p = sub.add_parser("provider", help="Get or set LLM provider")
    provider_p.add_argument(
        "action", nargs="?", choices=["set"], help="Action",
    )

    # Connect
    connect_p = sub.add_parser("connect", help="Configure IDE integrations")
    connect_p.add_argument("ide", nargs="?", help="Specific IDE to configure")
    connect_p.add_argument(
        "--list", action="store_true", help="List all supported IDEs",
    )

    # Migrate
    migrate_p = sub.add_parser("migrate", help="Migrate from V2")
    migrate_p.add_argument(
        "--rollback", action="store_true", help="Rollback migration",
    )

    # Memory ops
    remember_p = sub.add_parser("remember", help="Store a memory")
    remember_p.add_argument("content", help="Content to remember")
    remember_p.add_argument("--tags", default="", help="Comma-separated tags")

    recall_p = sub.add_parser("recall", help="Search memories")
    recall_p.add_argument("query", help="Search query")
    recall_p.add_argument("--limit", type=int, default=10, help="Max results")

    forget_p = sub.add_parser("forget", help="Delete memories matching query")
    forget_p.add_argument("query", help="Query to match")

    # Status & diagnostics
    sub.add_parser("status", help="System status")
    sub.add_parser("health", help="Math layer health")

    trace_p = sub.add_parser("trace", help="Recall with channel breakdown")
    trace_p.add_argument("query", help="Search query")

    # Warmup (pre-download model)
    sub.add_parser("warmup", help="Pre-download embedding model (~500MB)")

    # Dashboard
    dashboard_p = sub.add_parser("dashboard", help="Open web dashboard")
    dashboard_p.add_argument(
        "--port", type=int, default=8765, help="Port (default 8765)",
    )

    # Profiles
    profile_p = sub.add_parser("profile", help="Profile management")
    profile_p.add_argument(
        "action", choices=["list", "switch", "create"], help="Action",
    )
    profile_p.add_argument("name", nargs="?", help="Profile name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    from superlocalmemory.cli.commands import dispatch

    dispatch(args)


if __name__ == "__main__":
    main()
