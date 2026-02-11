"""
SuperLocalMemory V2 - Event Bus Routes (v2.5)
Copyright (c) 2026 Varun Pratap Bhardwaj — MIT License

Routes: /events/stream (SSE), /api/events, /api/events/stats
Progressive enhancement: routes only active if Event Bus is available.
"""

import json
import threading
import queue as _queue
from typing import Optional, Set
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from .helpers import DB_PATH

router = APIRouter()

# Feature flag
try:
    from event_bus import EventBus
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

# Thread-safe queue bridging sync EventBus -> async SSE
_sse_queues: Set = set()
_sse_queues_lock = threading.Lock()


def _event_to_sse_bridge(event: dict):
    """EventBus listener that pushes events to all SSE client queues."""
    with _sse_queues_lock:
        dead_queues = set()
        for q in _sse_queues:
            try:
                q.put_nowait(event)
            except _queue.Full:
                dead_queues.add(q)
        _sse_queues -= dead_queues


def register_event_listener():
    """Called by ui_server.py on startup to wire up SSE bridge."""
    if EVENT_BUS_AVAILABLE:
        try:
            bus = EventBus.get_instance(DB_PATH)
            bus.add_listener(_event_to_sse_bridge)
        except Exception:
            pass


@router.get("/events/stream")
async def event_stream(
    last_event_id: Optional[int] = Query(None, alias="Last-Event-ID"),
    event_type: Optional[str] = None,
):
    """Server-Sent Events (SSE) endpoint for real-time event streaming."""
    if not EVENT_BUS_AVAILABLE:
        return StreamingResponse(
            iter(["data: {\"error\": \"Event Bus not available\"}\n\n"]),
            media_type="text/event-stream"
        )

    import asyncio

    client_queue = _queue.Queue(maxsize=100)
    with _sse_queues_lock:
        _sse_queues.add(client_queue)

    async def generate():
        # Track last seen DB event ID for cross-process polling
        last_db_id = last_event_id or 0
        poll_counter = 0

        try:
            # Replay missed events on reconnect
            if last_event_id is not None:
                try:
                    bus = EventBus.get_instance(DB_PATH)
                    missed = bus.get_recent_events(since_id=last_event_id, limit=50, event_type=event_type)
                    for evt in missed:
                        data = json.dumps(evt)
                        yield f"id: {evt.get('id', '')}\nevent: {evt['event_type']}\ndata: {data}\n\n"
                        last_db_id = max(last_db_id, evt.get('id', 0))
                except Exception:
                    pass
            else:
                # Get the latest event ID so we don't replay old events
                try:
                    bus = EventBus.get_instance(DB_PATH)
                    recent = bus.get_recent_events(limit=1)
                    if recent:
                        last_db_id = recent[-1].get('id', 0)
                except Exception:
                    pass

            while True:
                # 1. Check in-memory queue (same-process events — instant)
                drained = False
                try:
                    while True:
                        event = client_queue.get_nowait()
                        if event_type and event.get("event_type") != event_type:
                            continue
                        data = json.dumps(event)
                        event_id = event.get("id", event.get("seq", ""))
                        yield f"id: {event_id}\nevent: {event['event_type']}\ndata: {data}\n\n"
                        last_db_id = max(last_db_id, event.get('id', 0))
                        drained = True
                except _queue.Empty:
                    pass

                # 2. Poll DB every 2 seconds for cross-process events
                #    (CLI, MCP from other IDEs, REST API — different processes)
                poll_counter += 1
                if not drained and poll_counter >= 2:
                    poll_counter = 0
                    try:
                        bus = EventBus.get_instance(DB_PATH)
                        new_events = bus.get_recent_events(
                            since_id=last_db_id, limit=10, event_type=event_type
                        )
                        for evt in new_events:
                            data = json.dumps(evt)
                            yield f"id: {evt.get('id', '')}\nevent: {evt['event_type']}\ndata: {data}\n\n"
                            last_db_id = max(last_db_id, evt.get('id', 0))
                    except Exception:
                        pass

                # 3. Keepalive + sleep
                if not drained:
                    yield f": keepalive {datetime.now().isoformat()}\n\n"
                await asyncio.sleep(1)
        finally:
            with _sse_queues_lock:
                _sse_queues.discard(client_queue)

    return StreamingResponse(
        generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


@router.get("/api/events")
async def get_events(
    since_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    event_type: Optional[str] = None,
):
    """Get recent events (polling API)."""
    if not EVENT_BUS_AVAILABLE:
        return {"events": [], "count": 0, "message": "Event Bus not available"}
    try:
        bus = EventBus.get_instance(DB_PATH)
        events = bus.get_recent_events(since_id=since_id, limit=limit, event_type=event_type)
        stats = bus.get_event_stats()
        return {"events": events, "count": len(events), "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event retrieval error: {str(e)}")


@router.get("/api/events/stats")
async def get_event_stats():
    """Get Event Bus statistics."""
    if not EVENT_BUS_AVAILABLE:
        return {"total_events": 0, "message": "Event Bus not available"}
    try:
        bus = EventBus.get_instance(DB_PATH)
        return bus.get_event_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event stats error: {str(e)}")
