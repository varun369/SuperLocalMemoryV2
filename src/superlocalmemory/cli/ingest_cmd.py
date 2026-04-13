# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""CLI handler for `slm ingest` — import external observations into SLM.

Supported sources:
  --source ecc    Import ECC (Everything Claude Code) session summaries
  --source jsonl  Import generic JSONL observations

Each imported record becomes a tool_event in the behavioral learning pipeline,
so the AssertionMiner can learn from them.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MEMORY_DIR = Path.home() / ".superlocalmemory"
MEMORY_DB = MEMORY_DIR / "memory.db"


def cmd_ingest(args: Namespace) -> None:
    """Ingest external observations into SLM tool_events table."""
    source = getattr(args, "source", "ecc")
    file_path = getattr(args, "file", "")
    use_json = getattr(args, "json", False)
    dry_run = getattr(args, "dry_run", False)

    if source == "ecc":
        result = _ingest_ecc(file_path, dry_run=dry_run)
    elif source == "jsonl":
        if not file_path:
            _error("--file required for jsonl source", use_json)
            return
        result = _ingest_jsonl(file_path, dry_run=dry_run)
    else:
        _error(f"Unknown source: {source}", use_json)
        return

    if use_json:
        from superlocalmemory.cli.json_output import json_print
        json_print("ingest", data=result, next_actions=[
            {"command": "slm consolidate --cognitive", "description": "Run consolidation to mine assertions"},
        ])
        return

    if result.get("error"):
        print(f"Error: {result['error']}")
        sys.exit(1)

    print(f"Ingested: {result['ingested']} events from {source}")
    if result.get("skipped"):
        print(f"Skipped:  {result['skipped']} (duplicates/invalid)")
    if dry_run:
        print("(dry run — no data written)")


def _error(msg: str, use_json: bool) -> None:
    if use_json:
        from superlocalmemory.cli.json_output import json_print
        json_print("ingest", error={"code": "INGEST_ERROR", "message": msg})
    else:
        print(f"Error: {msg}")
    sys.exit(1)


def _ingest_ecc(file_path: str, *, dry_run: bool = False) -> dict:
    """Ingest ECC session summaries from transcript JSONL files.

    Scans the Claude projects directory for session JSONL files and
    extracts tool usage patterns from them.
    """
    result = {"source": "ecc", "ingested": 0, "skipped": 0, "dry_run": dry_run}

    # Find ECC session files
    if file_path:
        files = [Path(file_path)]
    else:
        # Auto-discover: scan Claude project session files
        claude_dir = Path.home() / ".claude" / "projects"
        if not claude_dir.exists():
            result["error"] = f"Claude projects dir not found: {claude_dir}"
            return result
        files = sorted(claude_dir.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        # Limit to recent files (last 20)
        files = files[:20]

    if not files:
        result["error"] = "No session files found"
        return result

    result["files_scanned"] = len(files)
    events = []

    for fpath in files:
        try:
            with open(fpath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        result["skipped"] += 1
                        continue

                    # Extract tool usage from ECC session records
                    extracted = _extract_tool_events_from_record(record)
                    events.extend(extracted)
        except (OSError, PermissionError):
            result["skipped"] += 1
            continue

    if dry_run:
        result["ingested"] = len(events)
        result["sample"] = events[:5]
        return result

    # Write to tool_events table
    if events:
        ingested = _write_tool_events(events)
        result["ingested"] = ingested
    else:
        result["ingested"] = 0

    return result


def _extract_tool_events_from_record(record: dict) -> list[dict]:
    """Extract tool events from a single ECC/Claude session JSONL record."""
    events = []

    # Handle ECC summary format
    if "type" in record:
        rtype = record.get("type", "")

        # Tool use records
        if rtype == "assistant" and "content" in record:
            content = record.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_name = block.get("name", "unknown")
                        events.append({
                            "tool_name": tool_name,
                            "event_type": "complete",
                            "session_id": record.get("session_id", "ecc_import"),
                            "created_at": record.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        })

            # Also extract from tool_use type directly
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_name = block.get("tool_use_id", "unknown")
                        is_error = block.get("is_error", False)
                        events.append({
                            "tool_name": tool_name,
                            "event_type": "error" if is_error else "complete",
                            "session_id": record.get("session_id", "ecc_import"),
                            "created_at": record.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        })

    # Handle direct tool event format (from hook output)
    if "tool_name" in record and "event_type" in record:
        events.append({
            "tool_name": record["tool_name"],
            "event_type": record.get("event_type", "complete"),
            "session_id": record.get("session_id", "ecc_import"),
            "created_at": record.get("created_at", datetime.now(timezone.utc).isoformat()),
        })

    return events


def _ingest_jsonl(file_path: str, *, dry_run: bool = False) -> dict:
    """Ingest generic JSONL file with tool event records."""
    result = {"source": "jsonl", "ingested": 0, "skipped": 0, "dry_run": dry_run}

    fpath = Path(file_path)
    if not fpath.exists():
        result["error"] = f"File not found: {file_path}"
        return result

    events = []
    with open(fpath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                result["skipped"] += 1
                continue

            if "tool_name" not in record:
                result["skipped"] += 1
                continue

            events.append({
                "tool_name": record["tool_name"],
                "event_type": record.get("event_type", "complete"),
                "session_id": record.get("session_id", "jsonl_import"),
                "created_at": record.get("created_at", datetime.now(timezone.utc).isoformat()),
            })

    if dry_run:
        result["ingested"] = len(events)
        return result

    if events:
        result["ingested"] = _write_tool_events(events)

    return result


def _write_tool_events(events: list[dict]) -> int:
    """Write tool events to SLM's memory.db tool_events table."""
    db_path = MEMORY_DB
    if not db_path.exists():
        return 0

    conn = sqlite3.connect(str(db_path), timeout=10)
    count = 0

    try:
        for ev in events:
            try:
                conn.execute(
                    "INSERT INTO tool_events "
                    "(session_id, profile_id, project_path, tool_name, event_type, "
                    " input_summary, output_summary, duration_ms, metadata, created_at) "
                    "VALUES (?, 'default', '', ?, ?, '', '', 0, '{}', ?)",
                    (
                        ev.get("session_id", "import"),
                        ev["tool_name"],
                        ev.get("event_type", "complete"),
                        ev.get("created_at", datetime.now(timezone.utc).isoformat()),
                    ),
                )
                count += 1
            except sqlite3.Error:
                continue
        conn.commit()
    finally:
        conn.close()

    return count
