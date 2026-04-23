# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Filesystem safety helpers for SQLite DB open paths.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import os
import sqlite3
import stat
import sys
from pathlib import Path


class SafeFsError(RuntimeError):
    """Raised when a data-directory or DB-open precondition fails."""


_FORBIDDEN_COMPONENTS = (
    "iCloud Drive", "Mobile Documents", "CloudDocs",
    "Dropbox", "Google Drive", "OneDrive", "Box Sync",
    # macOS 13+ canonical cloud-storage mount point. Every modern
    # Dropbox / OneDrive / Google Drive / Box install on macOS routes
    # through here, bypassing the brand-name checks above.
    "Library/CloudStorage",
)


def validate_data_dir(path: Path) -> None:
    """Refuse paths that live under a cloud-sync folder.

    Cloud-synced directories silently corrupt SQLite WAL files.
    """
    resolved = str(path.resolve())
    lowered = resolved.lower()
    for comp in _FORBIDDEN_COMPONENTS:
        if comp.lower() in lowered:
            raise SafeFsError(
                f"SLM data directory {resolved} appears to live under "
                f"{comp!r} — cloud-synced folders are not supported "
                f"(SQLite WAL corrupts silently on replication). "
                f"Set SLM_DATA_DIR to a local path such as "
                f"{Path.home()}/.slm-local"
            )


def _ensure_parent_0700(path: Path) -> None:
    parent = path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        return
    st = parent.stat()
    if st.st_uid != os.getuid():
        raise SafeFsError(
            f"{parent} is not owned by current user (uid={os.getuid()})"
        )
    if (st.st_mode & 0o077) != 0:
        os.chmod(parent, 0o700)


def _safe_open_db(path: Path) -> sqlite3.Connection:
    """Open a SQLite DB with TOCTOU-tight symlink protection.

    Pattern:
      1. Enforce parent directory 0700.
      2. lstat the DB path; refuse if it's already a symlink.
      3. Open with O_NOFOLLOW to catch a last-moment swap.
      4. fstat and compare inode with the pre-open lstat.
      5. Close the fd and let sqlite3.connect reopen by path so WAL
         and SHM sibling files can be created naturally.
    """
    _ensure_parent_0700(path)
    if sys.platform != "win32":
        if path.exists():
            pre_st = os.lstat(str(path))
            if stat.S_ISLNK(pre_st.st_mode):
                raise SafeFsError(f"{path} is a symlink — refused")
            if pre_st.st_uid != os.getuid():
                raise SafeFsError(f"{path} not owned by current user")
            if (pre_st.st_mode & 0o077) != 0:
                os.chmod(str(path), 0o600)
        else:
            pre_st = None
        try:
            flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
            fd = os.open(str(path), flags, 0o600)
        except OSError as exc:
            raise SafeFsError(f"Cannot safely open {path}: {exc}") from exc
        try:
            post_st = os.fstat(fd)
            if pre_st is not None and (
                (pre_st.st_ino, pre_st.st_dev)
                != (post_st.st_ino, post_st.st_dev)
            ):
                raise SafeFsError(
                    f"{path} changed between lstat and open — refused"
                )
        finally:
            os.close(fd)
    conn = sqlite3.connect(
        str(path), isolation_level=None, timeout=5.0, check_same_thread=False,
    )
    return conn
