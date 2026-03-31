# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 -- PID File Manager.

Atomic JSON-based PID tracking. Records which SLM processes are running
and their parent PIDs for orphan detection.

File format: {"pids": [{"pid": 1234, "ppid": 5678, "started_at": "2026-03-30T14:25:01"}]}
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PidRecord -- frozen dataclass for a single process entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PidRecord:
    """A single PID record stored in the PID file."""

    pid: int
    ppid: int
    started_at: str

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "pid": self.pid,
            "ppid": self.ppid,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> PidRecord:
        """Deserialize from a dictionary (as read from JSON)."""
        return PidRecord(
            pid=int(d["pid"]),
            ppid=int(d["ppid"]),
            started_at=str(d["started_at"]),
        )


# ---------------------------------------------------------------------------
# PidManager -- atomic JSON PID file management
# ---------------------------------------------------------------------------

class PidManager:
    """Manage a JSON file tracking running SLM process PIDs.

    Uses atomic temp-file-then-rename writes so the file is never
    corrupted by a crash mid-write.
    """

    def __init__(self, pid_file_path: Path) -> None:
        self._path = pid_file_path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # -- Read ---------------------------------------------------------------

    def read_all(self) -> list[PidRecord]:
        """Read all PID records from the PID file.

        Returns empty list if the file is missing, corrupt, or malformed.
        Corrupt files are deleted so the next write starts clean.
        """
        if not self._path.exists():
            return []

        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)

            if not isinstance(data, dict) or "pids" not in data:
                logger.warning("Malformed PID file %s, resetting", self._path)
                return []

            return [
                PidRecord.from_dict(entry)
                for entry in data["pids"]
                if isinstance(entry, dict)
            ]

        except json.JSONDecodeError:
            logger.warning("Corrupt PID file %s, deleting", self._path)
            try:
                self._path.unlink(missing_ok=True)
            except OSError:
                pass
            return []

        except OSError as exc:
            logger.warning("Cannot read PID file %s: %s", self._path, exc)
            return []

    # -- Write (atomic) -----------------------------------------------------

    def _write_all(self, records: list[PidRecord]) -> None:
        """Atomically write all PID records to the PID file.

        Uses temp-file-then-rename pattern:
        - Write to a temp file in the same directory
        - os.replace() is atomic on POSIX (single inode swap)
        - On crash: either old file or new file, never corruption
        """
        data = {"pids": [r.to_dict() for r in records]}
        content = json.dumps(data, indent=2)

        tmp_path: str | None = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._path.parent),
                suffix=".tmp",
                prefix="slm-pids-",
            )
            os.write(fd, content.encode("utf-8"))
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp_path, str(self._path))
            tmp_path = None  # Consumed by replace, no cleanup needed

        except OSError as exc:
            logger.warning("Cannot write PID file %s: %s", self._path, exc)

        finally:
            if tmp_path is not None:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    pass

    # -- Register / Remove --------------------------------------------------

    def register(self, pid: int, ppid: int) -> None:
        """Add current process to PID file (replaces stale entry for same PID)."""
        records = self.read_all()
        records = [r for r in records if r.pid != pid]

        new_record = PidRecord(
            pid=pid,
            ppid=ppid,
            started_at=datetime.now(UTC).isoformat(),
        )
        records.append(new_record)
        self._write_all(records)

    def remove(self, pid: int) -> bool:
        """Remove a PID from the file. Returns True if found and removed."""
        records = self.read_all()
        new_records = [r for r in records if r.pid != pid]

        if len(new_records) == len(records):
            return False

        self._write_all(new_records)
        return True

    # -- Housekeeping -------------------------------------------------------

    def cleanup_dead(self) -> int:
        """Remove all PIDs that are no longer running.

        Returns number of dead PIDs removed.
        """
        records = self.read_all()
        alive: list[PidRecord] = []
        removed = 0

        for r in records:
            try:
                os.kill(r.pid, 0)
                alive.append(r)
            except ProcessLookupError:
                removed += 1
            except PermissionError:
                alive.append(r)  # Exists but owned by another user

        if removed > 0:
            self._write_all(alive)

        return removed
