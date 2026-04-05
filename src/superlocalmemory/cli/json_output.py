# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Shared JSON envelope for agent-native CLI output.

Follows the 2026 agent-native CLI standard:
- Consistent envelope: success, command, version, data/error
- HATEOAS next_actions for agent guidance
- Metadata for execution context

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import json


def _get_version() -> str:
    """Read version from package.json (npm), pyproject.toml, or metadata."""
    from pathlib import Path
    pkg_root = Path(__file__).resolve().parent.parent.parent.parent
    # 1. package.json (npm installs)
    try:
        pkg_json = pkg_root / "package.json"
        if pkg_json.exists():
            with open(pkg_json) as f:
                v = json.load(f).get("version", "")
                if v:
                    return v
    except Exception:
        pass
    # 2. pyproject.toml (pip installs)
    try:
        import tomllib
        toml_path = pkg_root / "pyproject.toml"
        if toml_path.exists():
            with open(toml_path, "rb") as f:
                return tomllib.load(f)["project"]["version"]
    except Exception:
        pass
    # 3. importlib.metadata fallback
    try:
        from importlib.metadata import version
        return version("superlocalmemory")
    except Exception:
        pass
    return "unknown"


def json_print(
    command: str,
    *,
    data: dict | None = None,
    error: dict | None = None,
    next_actions: list[dict] | None = None,
    metadata: dict | None = None,
) -> None:
    """Print a standard JSON envelope to stdout.

    Success envelope:
        {"success": true, "command": "...", "version": "...", "data": {...}}

    Error envelope:
        {"success": false, "command": "...", "version": "...", "error": {...}}
    """
    envelope: dict = {
        "success": error is None,
        "command": command,
        "version": _get_version(),
    }
    if error is not None:
        envelope["error"] = error
    else:
        envelope["data"] = data if data is not None else {}
    if metadata:
        envelope["metadata"] = metadata
    if next_actions:
        envelope["next_actions"] = next_actions
    print(json.dumps(envelope, indent=2, default=str))
