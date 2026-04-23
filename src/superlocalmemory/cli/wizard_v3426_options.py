# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Setup-wizard extensions for v3.4.26.

Keeps the user-facing surface tiny: one yes/no prompt for the queue.
Everything else defaults; advanced users edit ``v3426_options.json``.

Also validates the chosen data directory at install time so cloud-sync
folders (iCloud, Dropbox, OneDrive, …) fail loud BEFORE the user stores
their first memory.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from superlocalmemory.core.safe_fs import SafeFsError, validate_data_dir

logger = logging.getLogger(__name__)


# Defaults tuned for a commodity laptop with 4 concurrent IDEs
# (Claude Code, Cursor, Antigravity, VS Code). See the release notes
# for the reasoning behind the numbers.
_DEFAULT_QUEUE_ENABLED = True
_DEFAULT_RATE_PER_PID = 30
_DEFAULT_RATE_PER_AGENT = 10
_DEFAULT_RATE_GLOBAL = 100


@dataclass(frozen=True)
class V3426Options:
    queue_enabled: bool
    rate_limit_per_pid: int
    rate_limit_per_agent: int
    rate_limit_global: int


def _default_options() -> V3426Options:
    return V3426Options(
        queue_enabled=_DEFAULT_QUEUE_ENABLED,
        rate_limit_per_pid=_DEFAULT_RATE_PER_PID,
        rate_limit_per_agent=_DEFAULT_RATE_PER_AGENT,
        rate_limit_global=_DEFAULT_RATE_GLOBAL,
    )


def prompt_v3426_options(interactive: bool) -> V3426Options:
    """Return user-chosen (or default) v3.4.26 options.

    Non-interactive / EOFError (pipe) returns the defaults silently.
    Ctrl-C propagates so the user can actually abort install.
    """
    if not interactive:
        return _default_options()

    try:
        answer = input(
            "Enable SLM's concurrent-recall queue (recommended)? [Y/n]: "
        ).strip().lower()
    except EOFError:
        return _default_options()

    queue_enabled = answer not in ("n", "no")
    return V3426Options(
        queue_enabled=queue_enabled,
        rate_limit_per_pid=_DEFAULT_RATE_PER_PID,
        rate_limit_per_agent=_DEFAULT_RATE_PER_AGENT,
        rate_limit_global=_DEFAULT_RATE_GLOBAL,
    )


def validate_install_data_dir(path: Path) -> tuple[bool, str]:
    """Return (ok, reason). Empty reason on success."""
    try:
        validate_data_dir(path)
    except SafeFsError as exc:
        return False, str(exc)
    return True, ""


def persist_v3426_options(opts: V3426Options, home_dir: Path) -> Path:
    """Write the options JSON with 0600 perms and atomic replace.

    Atomic: a crash mid-write leaves either the old file or nothing,
    never a truncated JSON that the daemon can't parse on boot.
    0600: rate-limit config is not sensitive per se, but the file
    also carries future secrets — enforce the tight mode now.
    """
    home_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        try:
            os.chmod(home_dir, 0o700)
        except OSError as exc:
            logger.warning("could not tighten %s to 0700: %s", home_dir, exc)
    target = home_dir / "v3426_options.json"
    payload = (json.dumps(asdict(opts), indent=2) + "\n").encode("utf-8")
    tmp = home_dir / f"v3426_options.json.tmp.{os.getpid()}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(tmp, flags, 0o600)
        try:
            os.write(fd, payload)
        finally:
            os.close(fd)
        os.replace(tmp, target)
        if sys.platform != "win32":
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass
    except OSError:
        # Fallback for odd filesystems that don't support O_NOFOLLOW
        # or the perm bits — log + emit something rather than crash.
        logger.warning(
            "atomic write of %s failed; falling back to write_text", target,
        )
        target.write_text(
            json.dumps(asdict(opts), indent=2) + "\n", encoding="utf-8",
        )
    return target
