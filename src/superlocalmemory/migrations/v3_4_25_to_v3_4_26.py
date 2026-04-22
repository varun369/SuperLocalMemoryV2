# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Idempotent migration from v3.4.25 to v3.4.26 data layout.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

from pathlib import Path


def migrate(data_dir: Path) -> dict[str, object]:
    """Prepare v3.4.26 data directory. Safe to run any number of times.

    memory.db is untouched; the migration only provisions the new
    recall_queue.db and marks readiness with a sentinel file.
    """
    result: dict[str, object] = {
        "data_dir": str(data_dir),
        "created": [],
        "already_present": [],
    }
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    from superlocalmemory.core.recall_queue import RecallQueue

    queue_path = data_dir / "recall_queue.db"
    if queue_path.exists():
        result["already_present"].append(str(queue_path))
    else:
        result["created"].append(str(queue_path))
    q = RecallQueue(db_path=queue_path)
    q.close()

    marker = data_dir / ".slm-v3.4.26-ready"
    if marker.exists():
        result["already_present"].append(str(marker))
    else:
        marker.write_text("3.4.26\n", encoding="utf-8")
        result["created"].append(str(marker))
    return result


def is_ready(data_dir: Path) -> bool:
    return (Path(data_dir) / ".slm-v3.4.26-ready").exists()
