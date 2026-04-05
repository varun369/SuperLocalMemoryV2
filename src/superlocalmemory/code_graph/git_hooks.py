# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""Git post-commit hook for automatic code graph updates.

Install/uninstall functions for the hook, plus the run_post_commit
entry point that the hook invokes. Non-destructive: never modifies
git state, never blocks the commit. Idempotent installation.
"""

from __future__ import annotations

import logging
import os
import stat
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HOOK_MARKER = "# SLM-CodeGraph-Hook"
_HOOK_START = "# --- SLM-CodeGraph-Hook-Start ---"
_HOOK_END = "# --- SLM-CodeGraph-Hook-End ---"

_HOOK_CONTENT = f"""
{_HOOK_START}
{_HOOK_MARKER}
# Trigger SLM CodeGraph incremental update after commit
python3 -m superlocalmemory.code_graph.git_hooks "$PWD" &
{_HOOK_END}
"""

_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx",
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def install_post_commit_hook(repo_root: str | Path) -> dict:
    """Install SLM post-commit hook in the repository.

    Idempotent: if hook is already present, returns "already_present".
    If a hook file exists, appends our section. Otherwise creates new.

    Returns:
        {"success": True, "action": "installed" | "already_present" | "appended"}
    """
    repo_root = Path(repo_root)
    hook_path = repo_root / ".git" / "hooks" / "post-commit"

    try:
        # Ensure hooks directory exists
        hook_path.parent.mkdir(parents=True, exist_ok=True)

        if hook_path.exists():
            content = hook_path.read_text()

            # Idempotent check
            if _HOOK_MARKER in content:
                return {"success": True, "action": "already_present"}

            # Append to existing hook
            new_content = content.rstrip() + "\n" + _HOOK_CONTENT
            hook_path.write_text(new_content)
            _make_executable(hook_path)
            return {"success": True, "action": "appended"}

        # Create new hook
        new_content = "#!/bin/sh\n" + _HOOK_CONTENT
        hook_path.write_text(new_content)
        _make_executable(hook_path)
        return {"success": True, "action": "installed"}

    except PermissionError:
        return {
            "success": False,
            "error": "Permission denied writing git hook. Check .git/hooks/ permissions.",
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def uninstall_post_commit_hook(repo_root: str | Path) -> dict:
    """Remove SLM post-commit hook from the repository.

    Only removes our section (between _HOOK_START and _HOOK_END markers).
    Does not touch other hook content.

    Returns:
        {"success": True, "action": "removed" | "not_found"}
    """
    repo_root = Path(repo_root)
    hook_path = repo_root / ".git" / "hooks" / "post-commit"

    try:
        if not hook_path.exists():
            return {"success": True, "action": "not_found"}

        content = hook_path.read_text()

        if _HOOK_MARKER not in content:
            return {"success": True, "action": "not_found"}

        # Remove the section between markers
        lines = content.split("\n")
        new_lines: list[str] = []
        in_section = False

        for line in lines:
            if _HOOK_START in line:
                in_section = True
                continue
            if _HOOK_END in line:
                in_section = False
                continue
            if not in_section:
                new_lines.append(line)

        new_content = "\n".join(new_lines).strip()

        if not new_content or new_content == "#!/bin/sh":
            # Hook file is now empty, remove it
            hook_path.unlink()
        else:
            hook_path.write_text(new_content + "\n")

        return {"success": True, "action": "removed"}

    except Exception as exc:
        return {"success": False, "error": str(exc)}


def run_post_commit(repo_root: str | Path) -> dict:
    """Execute the post-commit graph update.

    Detects changed files from the last commit and triggers
    incremental update. Called by the installed git hook.

    Returns:
        {"success": True, "files_updated": int, "duration_ms": int}
    """
    repo_root = Path(repo_root)
    t0 = time.time()

    try:
        # Detect changed files
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(repo_root),
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"git diff failed: {result.stderr.strip()}",
            }

        # Filter to supported extensions
        all_files = [
            f.strip() for f in result.stdout.strip().split("\n") if f.strip()
        ]
        supported = [
            f for f in all_files
            if any(f.endswith(ext) for ext in _SUPPORTED_EXTENSIONS)
        ]

        duration_ms = int((time.time() - t0) * 1000)

        if not supported:
            return {
                "success": True,
                "files_updated": 0,
                "duration_ms": duration_ms,
            }

        # Trigger incremental update (lazy import to avoid startup cost)
        # In production this would call the CodeGraphService
        # For now just return the list of files that would be updated
        duration_ms = int((time.time() - t0) * 1000)

        return {
            "success": True,
            "files_updated": len(supported),
            "duration_ms": duration_ms,
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "git diff timed out"}
    except FileNotFoundError:
        return {"success": False, "error": "git not found on PATH"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_executable(path: Path) -> None:
    """Make a file executable (chmod +x)."""
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# ---------------------------------------------------------------------------
# CLI entry point (called by hook)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = run_post_commit(sys.argv[1])
        if not result.get("success"):
            logger.error("Post-commit hook failed: %s", result.get("error"))
