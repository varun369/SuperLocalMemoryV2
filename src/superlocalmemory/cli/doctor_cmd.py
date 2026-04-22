# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""slm doctor — preflight and health checks.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

_DEFAULT_DATA_DIR = Path.home() / ".superlocalmemory"


def _check_python() -> dict[str, Any]:
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 10)
    return {
        "name": "python",
        "status": "ok" if ok else "error",
        "detail": f"Python {v.major}.{v.minor}.{v.micro}",
        "hint": None if ok else "SLM requires Python >= 3.10",
    }


def _check_platform() -> dict[str, Any]:
    return {
        "name": "platform",
        "status": "ok",
        "detail": f"{platform.system()} {platform.release()} {platform.machine()}",
        "hint": None,
    }


def _check_portalocker() -> dict[str, Any]:
    try:
        import portalocker  # noqa: F401
        return {
            "name": "portalocker",
            "status": "ok",
            "detail": "installed",
            "hint": None,
        }
    except ImportError:
        return {
            "name": "portalocker",
            "status": "error",
            "detail": "not installed",
            "hint": "pip install --upgrade superlocalmemory",
        }


def _check_data_dir(data_dir: Path) -> dict[str, Any]:
    from superlocalmemory.core import safe_fs
    try:
        safe_fs.validate_data_dir(data_dir)
        return {
            "name": "data directory",
            "status": "ok",
            "detail": str(data_dir),
            "hint": None,
        }
    except safe_fs.SafeFsError as exc:
        return {
            "name": "data directory",
            "status": "error",
            "detail": str(data_dir),
            "hint": str(exc),
        }


def _check_migration(data_dir: Path) -> dict[str, Any]:
    from superlocalmemory.migrations.v3_4_25_to_v3_4_26 import is_ready
    ok = is_ready(data_dir)
    return {
        "name": "v3.4.26 migration",
        "status": "ok" if ok else "warn",
        "detail": "ready" if ok else "not migrated yet",
        "hint": None if ok else
        "Run once: python -m superlocalmemory.migrations.v3_4_25_to_v3_4_26",
    }


def _check_queue_db(data_dir: Path) -> dict[str, Any]:
    queue = data_dir / "recall_queue.db"
    if queue.exists():
        return {
            "name": "queue database",
            "status": "ok",
            "detail": f"{queue} ({queue.stat().st_size} bytes)",
            "hint": None,
        }
    return {
        "name": "queue database",
        "status": "warn",
        "detail": "not yet created",
        "hint": "The daemon will create this on first use.",
    }


def run_checks(*, data_dir: Path | None = None) -> dict[str, Any]:
    dd = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_DIR
    checks = [
        _check_python(),
        _check_platform(),
        _check_portalocker(),
        _check_data_dir(dd),
        _check_migration(dd),
        _check_queue_db(dd),
    ]
    has_error = any(c["status"] == "error" for c in checks)
    exit_code = 1 if has_error else 0
    return {
        "data_dir": str(dd),
        "checks": checks,
        "exit_code": exit_code,
    }


def _print_report(report: dict[str, Any]) -> None:
    glyphs = {"ok": "\u2713", "warn": "\u26a0", "error": "\u2717"}
    print(f"SLM doctor — data dir: {report['data_dir']}\n")
    for c in report["checks"]:
        g = glyphs.get(c["status"], "?")
        print(f" {g} {c['name']:<20} {c['detail']}")
        if c.get("hint"):
            print(f"      {c['hint']}")
    print(f"\nExit code: {report['exit_code']}")


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="slm-doctor")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    report = run_checks(data_dir=args.data_dir)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report)
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
