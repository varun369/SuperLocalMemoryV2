# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — MCP Server.

Clean MCP server calling V3 MemoryEngine. Supports all MCP-compatible IDEs.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

# CRITICAL: Set BEFORE any torch/transformers import to prevent Metal/MPS
# GPU memory reservation on Apple Silicon.
import os as _os
_os.environ.setdefault('PYTORCH_MPS_HIGH_WATERMARK_RATIO', '0.0')
_os.environ.setdefault('PYTORCH_MPS_MEM_LIMIT', '0')
_os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')
_os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
_os.environ.setdefault('TORCH_DEVICE', 'cpu')

import logging
import sys

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

server = FastMCP("SuperLocalMemory V3")

# Lazy engine singleton -------------------------------------------------------

_engine = None


def get_engine():
    """Return (or create) the singleton MemoryEngine."""
    global _engine
    if _engine is None:
        from superlocalmemory.core.config import SLMConfig
        from superlocalmemory.core.engine import MemoryEngine

        config = SLMConfig.load()
        _engine = MemoryEngine(config)
        _engine.initialize()
    return _engine


def reset_engine():
    """Reset engine singleton (for testing or mode switch)."""
    global _engine
    _engine = None


# Register tools and resources -------------------------------------------------
#
# V3.3.19: Trimmed from 38 tools to 15 essential tools.
# IDEs cap at 50-100 tools total (Cursor, Antigravity, Windsurf).
# 38 tools from SLM alone crowds out other MCP servers.
#
# Essential 15: the tools an AI agent actually needs during a session.
# Admin/diagnostics tools remain available via CLI (`slm <command>`).
# Set SLM_MCP_ALL_TOOLS=1 to enable all 38 tools (power users).

import os as _os_reg

_ESSENTIAL_TOOLS: frozenset[str] = frozenset({
    # Core memory operations (8)
    "remember", "recall", "search", "fetch",
    "list_recent", "delete_memory", "update_memory", "get_status",
    # Session lifecycle (3)
    "session_init", "observe", "close_session",
    # Memory management (2)
    "forget", "run_maintenance",
    # Infinite memory + learning (4)
    "consolidate_cognitive", "get_soft_prompts",
    "set_mode", "report_outcome",
})

_all_tools = _os_reg.environ.get("SLM_MCP_ALL_TOOLS") == "1"


class _FilteredServer:
    """Wraps FastMCP to only register essential tools.

    Non-essential tools are silently skipped (not registered on the MCP
    server). They remain available via CLI. When SLM_MCP_ALL_TOOLS=1,
    all tools are registered (bypass filter).
    """
    __slots__ = ("_server", "_allowed")

    def __init__(self, real_server: FastMCP, allowed: frozenset[str]) -> None:
        self._server = real_server
        self._allowed = allowed

    def tool(self, *args, **kwargs):
        def decorator(func):
            if func.__name__ in self._allowed:
                return self._server.tool(*args, **kwargs)(func)
            return func  # Skip registration — still importable, just not MCP-visible
        return decorator

    def __getattr__(self, name):
        return getattr(self._server, name)


# Choose full or filtered registration target
_target = server if _all_tools else _FilteredServer(server, _ESSENTIAL_TOOLS)

from superlocalmemory.mcp.tools_core import register_core_tools
from superlocalmemory.mcp.tools_v28 import register_v28_tools
from superlocalmemory.mcp.tools_v3 import register_v3_tools
from superlocalmemory.mcp.tools_active import register_active_tools
from superlocalmemory.mcp.tools_v33 import register_v33_tools
from superlocalmemory.mcp.resources import register_resources
from superlocalmemory.mcp.tools_code_graph import register_code_graph_tools

register_core_tools(_target, get_engine)
register_v28_tools(_target, get_engine)
register_v3_tools(_target, get_engine)
register_active_tools(_target, get_engine)
register_v33_tools(_target, get_engine)
register_resources(server, get_engine)  # Resources always registered (not tools)
register_code_graph_tools(_target, get_engine)  # CodeGraph: filtered like other tools (SLM_MCP_ALL_TOOLS=1 to show all)


# V3.3.21: Eager engine warmup — start initializing BEFORE first tool call.
# The MCP server process starts when the IDE launches. Previously, the engine
# was lazy-loaded on first tool call → 23s cold start for the user.
# Now: engine starts warming in a background thread immediately. By the time
# the first tool call arrives (1-2s later), the engine is already warm.
# This applies to ALL IDEs: Claude Code, Cursor, Antigravity, Gemini CLI, etc.
def _eager_warmup() -> None:
    """Pre-warm engine in background thread."""
    import logging
    _logger = logging.getLogger(__name__)
    try:
        get_engine()
        _logger.info("MCP engine pre-warmed successfully")
    except Exception as exc:
        _logger.debug("MCP engine pre-warmup failed (non-fatal): %s", exc)

import threading
_warmup_thread = threading.Thread(target=_eager_warmup, daemon=True, name="mcp-warmup")
_warmup_thread.start()


if __name__ == "__main__":
    server.run(transport="stdio")
