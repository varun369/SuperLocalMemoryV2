# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Ingestion adapter management API — enable/disable/start/stop from dashboard.

v3.4.4: Users can manage Gmail, Calendar, Transcript adapters entirely from
the dashboard UI — no CLI needed. The best product experience.

Endpoints:
  GET  /api/adapters         — list all adapters with status
  POST /api/adapters/enable  — enable an adapter
  POST /api/adapters/disable — disable an adapter
  POST /api/adapters/start   — start a running adapter
  POST /api/adapters/stop    — stop a running adapter
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["adapters"])


class AdapterAction(BaseModel):
    name: str


@router.get("/api/adapters")
async def list_adapters_api():
    """List all adapters with their enabled/running status."""
    from superlocalmemory.ingestion.adapter_manager import list_adapters
    adapters = list_adapters()
    return {"adapters": adapters}


@router.post("/api/adapters/enable")
async def enable_adapter_api(body: AdapterAction):
    """Enable an adapter (doesn't start it yet)."""
    from superlocalmemory.ingestion.adapter_manager import enable_adapter
    return enable_adapter(body.name)


@router.post("/api/adapters/disable")
async def disable_adapter_api(body: AdapterAction):
    """Disable and stop an adapter."""
    from superlocalmemory.ingestion.adapter_manager import disable_adapter
    return disable_adapter(body.name)


@router.post("/api/adapters/start")
async def start_adapter_api(body: AdapterAction):
    """Start a running adapter subprocess."""
    from superlocalmemory.ingestion.adapter_manager import start_adapter
    return start_adapter(body.name)


@router.post("/api/adapters/stop")
async def stop_adapter_api(body: AdapterAction):
    """Stop a running adapter."""
    from superlocalmemory.ingestion.adapter_manager import stop_adapter
    return stop_adapter(body.name)
