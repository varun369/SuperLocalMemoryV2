# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Claude Code hook handlers — zero-dependency, cross-platform.

All handlers use ONLY Python stdlib (sys, os, json, tempfile, subprocess, time).
No SLM imports in the hot path. Called via:  slm hook <start|gate|init-done|checkpoint|stop>

The main() entry point in cli/main.py has a fast path that dispatches here
BEFORE argparse or any heavy imports.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

# ---------------------------------------------------------------------------
# Cross-platform temp paths
# ---------------------------------------------------------------------------
_TMP = tempfile.gettempdir()
_MARKER = os.path.join(_TMP, "slm-session-initialized")
_START_TIME = os.path.join(_TMP, "slm-session-start-time")
_ACTIVITY_LOG = os.path.join(_TMP, "slm-session-activity")
_LAST_CONSOLIDATION = os.path.join(
    os.path.expanduser("~"), ".superlocalmemory", ".last-consolidation",
)


def handle_hook(action: str) -> None:
    """Dispatch to the appropriate hook handler. Called from main() fast path."""
    handlers = {
        "start": _hook_start,
        "gate": _hook_gate,
        "init-done": _hook_init_done,
        "checkpoint": _hook_checkpoint,
        "stop": _hook_stop,
    }
    handler = handlers.get(action)
    if handler is None:
        print(f"Unknown hook action: {action}", file=sys.stderr)
        sys.exit(1)
    handler()


# ---------------------------------------------------------------------------
# 1. SESSION START — SessionStart hook
# ---------------------------------------------------------------------------

def _hook_start() -> None:
    """Clean markers, inject SQL-fast context, print session_init mandate."""
    # Clean stale markers from previous sessions
    for f in (_MARKER, _START_TIME, _ACTIVITY_LOG):
        try:
            os.remove(f)
        except OSError:
            pass

    # Record session start time
    with open(_START_TIME, "w") as f:
        f.write(str(int(time.time())))

    # Initialize activity log
    with open(_ACTIVITY_LOG, "w") as f:
        f.write("")

    # Reap orphan MCP processes (background, best-effort)
    try:
        if sys.platform != "win32":
            subprocess.Popen(
                ["sh", "-c",
                 "ps -eo pid,args 2>/dev/null"
                 " | grep -E 'node.*\\.bin/|node.*slm |uv tool uvx'"
                 " | grep -v grep"
                 " | awk '{print $1, $NF}'"
                 " | sort -k2,2 -k1,1rn"
                 " | awk '{if($2==p)print $1; p=$2}'"
                 " | xargs kill 2>/dev/null"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass

    # Print session context (SQL-fast path, <500ms)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    project_name = os.path.basename(project_dir)
    try:
        result = subprocess.run(
            ["slm", "session-context", project_name],
            capture_output=True, text=True, timeout=12,
        )
        if result.stdout.strip():
            print(result.stdout.strip())
    except Exception:
        print("# SLM Session Context — unavailable")

    # Mandatory session_init instruction
    print()
    print("## MANDATORY: SLM Session Init")
    print("BEFORE your first response, call:")
    print(f"  mcp__superlocalmemory__session_init with project_path='{project_dir}'"
          " and a topic from the user's first message")
    print("session_init returns both context AND memories — no separate recall needed.")


# ---------------------------------------------------------------------------
# 2. GATE — PreToolUse hook (default, enforces session_init)
# ---------------------------------------------------------------------------

def _hook_gate() -> None:
    """Block non-SLM tools until session_init has been called.

    Fast path (~30ms): marker file exists → exit 0.
    Slow path (~80ms): parse JSON stdin, allow SLM tools, block rest.
    """
    # Fast path: already initialized
    if os.path.exists(_MARKER):
        sys.exit(0)

    # Safety: if session-start never ran, don't gate (avoid lockout)
    if not os.path.exists(_START_TIME):
        sys.exit(0)

    # Parse tool name from stdin
    tool_name = ""
    if not sys.stdin.isatty():
        try:
            data = json.load(sys.stdin)
            tool_name = data.get("tool_name", "")
        except Exception:
            # Can't parse input — don't block (safety)
            sys.exit(0)

    # Allow SLM tools through (needed to call session_init itself)
    if tool_name.startswith("mcp__superlocalmemory__"):
        sys.exit(0)

    # Allow ToolSearch through (needed to fetch SLM tool schemas)
    if tool_name == "ToolSearch":
        sys.exit(0)

    # Block everything else
    print("[SLM-GATE] BLOCKED: Call mcp__superlocalmemory__session_init"
          " before using other tools.")
    sys.exit(2)


# ---------------------------------------------------------------------------
# 3. INIT DONE — PostToolUse hook for session_init
# ---------------------------------------------------------------------------

def _hook_init_done() -> None:
    """Create marker file to lift the gate for the rest of the session."""
    with open(_MARKER, "w") as f:
        f.write(str(int(time.time())))
    sys.exit(0)


# ---------------------------------------------------------------------------
# 4. CHECKPOINT — PostToolUse hook for Write|Edit
# ---------------------------------------------------------------------------

_OBSERVE_COOLDOWN = 300   # 5 minutes per file
_RECALL_INTERVAL = 900    # 15 minutes
_LEARN_INTERVAL = 1800    # 30 minutes


def _hook_checkpoint() -> None:
    """Auto-observe file changes + periodic recall/learn reminders.

    1. Directly calls `slm observe` for file change tracking (no Claude needed)
    2. Suggests richer observe to Claude
    3. Periodic recall refresh reminder
    4. Periodic learn/patterns reminder
    """
    now = int(time.time())

    # Parse file_path from stdin
    file_path = ""
    if not sys.stdin.isatty():
        try:
            data = json.load(sys.stdin)
            tool_input = data.get("tool_input", {})
            if isinstance(tool_input, dict):
                file_path = tool_input.get("file_path", "")
        except Exception:
            pass

    # --- Auto-observe file change (direct, no Claude needed) ---
    if file_path:
        basename = os.path.basename(file_path)
        lock_file = os.path.join(_TMP, f"slm-obs-{_safe_hash(file_path)}")

        if _cooldown_elapsed(lock_file, _OBSERVE_COOLDOWN, now):
            _write_timestamp(lock_file, now)

            # Direct observe — SLM records the change even if Claude ignores
            try:
                subprocess.Popen(
                    ["slm", "observe", f"File changed: {basename}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

            # Log to session activity
            try:
                with open(_ACTIVITY_LOG, "a") as f:
                    f.write(f"{now}|{basename}\n")
            except Exception:
                pass

            # Suggest richer observe to Claude (with semantic context)
            print(f"[SLM-AUTO] File changed: {basename}"
                  " — Call mcp__superlocalmemory__observe with a 1-line"
                  " summary of what was changed and why.")

    # --- Periodic recall reminder (every 15 min) ---
    recall_lock = os.path.join(_TMP, "slm-recall-reminder")
    if _cooldown_elapsed(recall_lock, _RECALL_INTERVAL, now):
        _write_timestamp(recall_lock, now)
        print("[SLM] 15+ min since last context refresh."
              " Call mcp__superlocalmemory__recall with current work topic.")

    # --- Periodic learn reminder (every 30 min) ---
    learn_lock = os.path.join(_TMP, "slm-learn-reminder")
    if _cooldown_elapsed(learn_lock, _LEARN_INTERVAL, now):
        _write_timestamp(learn_lock, now)
        print("[SLM] Call mcp__superlocalmemory__get_learned_patterns"
              " to adapt to learned preferences.")

    sys.exit(0)


# ---------------------------------------------------------------------------
# 5. STOP — Stop hook (session end)
# ---------------------------------------------------------------------------

def _hook_stop() -> None:
    """Save rich session summary + trigger auto-consolidation."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    project_name = os.path.basename(project_dir)
    timestamp = time.strftime("%Y-%m-%d %H:%M")

    # --- Git context ---
    git_branch = _run_quiet(["git", "-C", project_dir, "branch", "--show-current"])
    git_diff = _run_quiet(
        ["git", "-C", project_dir, "diff", "--stat"],
        postprocess=lambda s: s.strip().rsplit("\n", 1)[-1].strip() if s.strip() else "",
    )
    recent_commits = _run_quiet(
        ["git", "-C", project_dir, "log", "--oneline", "-5", "--since=3 hours ago"],
    )

    # --- Files from activity log ---
    modified = ""
    try:
        if os.path.exists(_ACTIVITY_LOG):
            with open(_ACTIVITY_LOG) as f:
                files = sorted({line.split("|", 1)[1].strip()
                                for line in f if "|" in line})
            modified = ", ".join(files[:20])
    except Exception:
        pass

    # --- Build summary ---
    parts = [f"[{project_name}] session ended {timestamp}"]
    if git_branch:
        parts.append(f"branch: {git_branch}")
    if git_diff:
        parts.append(f"uncommitted: {git_diff}")
    if recent_commits:
        commits = "; ".join(recent_commits.strip().split("\n")[:5])
        parts.append(f"recent: {commits}")
    if modified:
        parts.append(f"files: {modified}")

    summary = " | ".join(parts)

    # --- Save to SLM ---
    try:
        subprocess.run(
            ["slm", "observe", summary],
            capture_output=True, timeout=8,
        )
    except Exception:
        try:
            subprocess.run(
                ["slm", "remember", summary],
                capture_output=True, timeout=8,
            )
        except Exception:
            pass

    # --- Auto-consolidation (if >24h since last run) ---
    _maybe_consolidate()

    # --- Clean up session markers ---
    for f in (_MARKER, _START_TIME, _ACTIVITY_LOG):
        try:
            os.remove(f)
        except OSError:
            pass

    # Clean rate-limit locks
    for name in os.listdir(_TMP):
        if name.startswith("slm-obs-") or name.startswith("slm-recall-") or name.startswith("slm-learn-"):
            try:
                os.remove(os.path.join(_TMP, name))
            except OSError:
                pass

    sys.exit(0)


# ---------------------------------------------------------------------------
# Helpers (stdlib only)
# ---------------------------------------------------------------------------

def _safe_hash(s: str) -> str:
    """Simple string hash for rate-limit lock file names."""
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return format(h, "08x")


def _cooldown_elapsed(lock_file: str, interval: int, now: int) -> bool:
    """Check if enough time has passed since last timestamp in lock_file."""
    try:
        if os.path.exists(lock_file):
            with open(lock_file) as f:
                last = int(f.read().strip())
            return (now - last) >= interval
    except (ValueError, OSError):
        pass
    return True


def _write_timestamp(path: str, ts: int) -> None:
    """Write a unix timestamp to a file."""
    try:
        with open(path, "w") as f:
            f.write(str(ts))
    except OSError:
        pass


def _run_quiet(cmd: list[str], timeout: int = 5, postprocess=None) -> str:
    """Run a command quietly, return stdout or empty string."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = result.stdout.strip()
        if postprocess and out:
            out = postprocess(out)
        return out
    except Exception:
        return ""


def _maybe_consolidate() -> None:
    """Run cognitive consolidation if last run was >24h ago. Non-blocking."""
    try:
        last_ts = 0
        if os.path.exists(_LAST_CONSOLIDATION):
            with open(_LAST_CONSOLIDATION) as f:
                last_ts = int(f.read().strip())

        now = int(time.time())
        if (now - last_ts) < 86400:  # 24 hours
            return

        # Update timestamp FIRST to prevent concurrent runs
        os.makedirs(os.path.dirname(_LAST_CONSOLIDATION), exist_ok=True)
        with open(_LAST_CONSOLIDATION, "w") as f:
            f.write(str(now))

        # Run consolidation in background (don't block session end)
        subprocess.Popen(
            ["slm", "consolidate", "--cognitive"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
