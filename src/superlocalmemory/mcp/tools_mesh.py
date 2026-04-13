# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SLM Mesh MCP Tools — P2P agent communication via the unified daemon.

v3.4.4: These tools ship WITH SuperLocalMemory, no separate slm-mesh install needed.
End users get full mesh functionality from `pip install superlocalmemory`.

All tools communicate with the daemon's Python mesh broker on port 8765.
Auto-heartbeat keeps the session alive as long as the MCP server is running.

8 tools: mesh_summary, mesh_peers, mesh_send, mesh_inbox,
         mesh_state, mesh_lock, mesh_events, mesh_status
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from typing import Callable

logger = logging.getLogger(__name__)

# Unique peer ID for this MCP server session
_PEER_ID = str(uuid.uuid4())[:12]
_SESSION_SUMMARY = ""
_HEARTBEAT_INTERVAL = 25  # seconds (broker marks stale at 30s, dead at 60s)
_HEARTBEAT_THREAD: threading.Thread | None = None
_REGISTERED = False


def _daemon_url() -> str:
    """Get the daemon base URL."""
    port = 8765
    try:
        port_file = os.path.join(os.path.expanduser("~"), ".superlocalmemory", "daemon.port")
        if os.path.exists(port_file):
            port = int(open(port_file).read().strip())
    except Exception:
        pass
    return f"http://127.0.0.1:{port}"


def _mesh_request(method: str, path: str, body: dict | None = None) -> dict | None:
    """Send request to daemon mesh broker."""
    import urllib.request
    url = f"{_daemon_url()}/mesh{path}"
    try:
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"} if data else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("Mesh request failed: %s %s — %s", method, path, exc)
        return None


def _ensure_registered() -> None:
    """Register this session with the mesh broker if not already."""
    global _REGISTERED
    if _REGISTERED:
        return

    result = _mesh_request("POST", "/register", {
        "peer_id": _PEER_ID,
        "session_id": os.environ.get("CLAUDE_SESSION_ID", _PEER_ID),
        "summary": _SESSION_SUMMARY or "SLM MCP session",
    })
    if result:
        _REGISTERED = True
        _start_heartbeat()


def _start_heartbeat() -> None:
    """Background thread that sends heartbeat to keep session alive."""
    global _HEARTBEAT_THREAD
    if _HEARTBEAT_THREAD is not None:
        return

    def heartbeat_loop():
        while True:
            time.sleep(_HEARTBEAT_INTERVAL)
            try:
                _mesh_request("POST", "/heartbeat", {"peer_id": _PEER_ID})
            except Exception:
                pass

    _HEARTBEAT_THREAD = threading.Thread(target=heartbeat_loop, daemon=True, name="mesh-heartbeat")
    _HEARTBEAT_THREAD.start()
    logger.info("Mesh heartbeat started (peer_id=%s, interval=%ds)", _PEER_ID, _HEARTBEAT_INTERVAL)


def register_mesh_tools(server, get_engine: Callable) -> None:
    """Register all 8 mesh MCP tools."""

    @server.tool()
    async def mesh_summary(summary: str = "") -> dict:
        """Register this session and describe what you're working on.

        Call this at the start of every session. Other agents can see your summary
        and send you messages. The session stays alive via automatic heartbeat.

        Args:
            summary: What this session is working on (e.g. "Fixing auth bug in api.py")
        """
        global _SESSION_SUMMARY
        _SESSION_SUMMARY = summary or "Active session"

        _ensure_registered()

        # Update summary
        result = _mesh_request("POST", "/summary", {
            "peer_id": _PEER_ID,
            "summary": _SESSION_SUMMARY,
        })

        return {
            "peer_id": _PEER_ID,
            "summary": _SESSION_SUMMARY,
            "registered": True,
            "heartbeat_active": _HEARTBEAT_THREAD is not None,
            "broker_response": result,
        }

    @server.tool()
    async def mesh_peers() -> dict:
        """List all active peer sessions on this machine.

        Shows other Claude Code, Cursor, or AI agent sessions that are
        connected to the same SLM mesh network.
        """
        _ensure_registered()
        result = _mesh_request("GET", "/peers")
        peers = (result or {}).get("peers", [])
        return {
            "peers": peers,
            "count": len(peers),
            "my_peer_id": _PEER_ID,
        }

    @server.tool()
    async def mesh_send(to: str, message: str) -> dict:
        """Send a message to another peer session.

        Args:
            to: The peer_id of the recipient (from mesh_peers)
            message: The message content to send
        """
        _ensure_registered()
        result = _mesh_request("POST", "/send", {
            "from_peer": _PEER_ID,
            "to_peer": to,
            "content": message,
        })
        return result or {"error": "Failed to send message"}

    @server.tool()
    async def mesh_inbox() -> dict:
        """Read messages sent to this session.

        Returns unread messages from other peer sessions.
        Messages are marked as read after retrieval.
        """
        _ensure_registered()
        messages = _mesh_request("GET", f"/inbox/{_PEER_ID}")
        if messages:
            # Mark as read
            _mesh_request("POST", f"/inbox/{_PEER_ID}/read")
        return messages or {"messages": [], "count": 0}

    @server.tool()
    async def mesh_state(key: str = "", value: str = "", action: str = "get") -> dict:
        """Get or set shared state across all sessions.

        Shared state is visible to all peers. Use for coordinating work:
        server IPs, API keys, feature flags, task assignments.

        Args:
            key: State key name
            value: Value to set (only for action="set")
            action: "get" (read all or one key), "set" (write a key)
        """
        _ensure_registered()

        if action == "set" and key:
            result = _mesh_request("POST", "/state", {
                "key": key,
                "value": value,
                "set_by": _PEER_ID,
            })
            return result or {"error": "Failed to set state"}

        if key:
            result = _mesh_request("GET", f"/state/{key}")
            return result or {"key": key, "value": None}

        result = _mesh_request("GET", "/state")
        return result or {"state": {}}

    @server.tool()
    async def mesh_lock(
        file_path: str,
        action: str = "query",
    ) -> dict:
        """Manage file locks across sessions.

        Before editing a shared file, check if another session has it locked.

        Args:
            file_path: Path to the file
            action: "query" (check lock), "acquire" (lock file), "release" (unlock)
        """
        _ensure_registered()
        result = _mesh_request("POST", "/lock", {
            "file_path": file_path,
            "action": action,
            "locked_by": _PEER_ID,
        })
        return result or {"error": "Lock operation failed"}

    @server.tool()
    async def mesh_events() -> dict:
        """Get recent mesh events (peer joins, leaves, messages, state changes).

        Shows the activity log of the mesh network.
        """
        result = _mesh_request("GET", "/events")
        return result or {"events": []}

    @server.tool()
    async def mesh_status() -> dict:
        """Get mesh broker health and statistics.

        Shows broker uptime, peer count, and connection status.
        """
        result = _mesh_request("GET", "/status")
        if result:
            result["my_peer_id"] = _PEER_ID
            result["heartbeat_active"] = _HEARTBEAT_THREAD is not None
        return result or {
            "broker_up": False,
            "error": "Cannot reach mesh broker. Is the daemon running? (slm serve start)",
        }
