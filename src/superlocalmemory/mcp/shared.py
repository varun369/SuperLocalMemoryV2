# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3

"""Shared MCP utilities — single source of truth for helpers used
across tools_core, tools_active, tools_v28, tools_v3, tools_v33.

V3.3.12: Extracted _emit_event to eliminate code duplication.
"""

from __future__ import annotations

from pathlib import Path

_DB_PATH = Path.home() / ".superlocalmemory" / "memory.db"


def emit_event(event_type: str, payload: dict | None = None,
               source_agent: str = "mcp_client") -> None:
    """Emit an event to the EventBus (best-effort, never raises)."""
    try:
        from superlocalmemory.infra.event_bus import EventBus
        bus = EventBus.get_instance(_DB_PATH)
        bus.emit(event_type, payload=payload, source_agent=source_agent,
                 source_protocol="mcp")
    except Exception:
        pass
