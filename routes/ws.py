"""
SuperLocalMemory V2 - WebSocket Routes
Copyright (c) 2026 Varun Pratap Bhardwaj — MIT License

Routes: /ws/updates
"""

from typing import Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        self.active_connections -= disconnected


manager = ConnectionManager()


@router.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time memory updates."""
    await manager.connect(websocket)

    try:
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": datetime.now().isoformat()
        })

        while True:
            try:
                data = await websocket.receive_json()

                if data.get('type') == 'ping':
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })

                elif data.get('type') == 'get_stats':
                    await websocket.send_json({
                        "type": "stats_update",
                        "message": "Use /api/stats endpoint for stats",
                        "timestamp": datetime.now().isoformat()
                    })

            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })

    finally:
        manager.disconnect(websocket)
