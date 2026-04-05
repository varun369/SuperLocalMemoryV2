# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""Code Knowledge Graph for SuperLocalMemory.

Unifies AST-derived code structure with SLM's semantic memory.
Separate code_graph.db — does not touch memory.db.

Usage:
    from superlocalmemory.code_graph import CodeGraphService, CodeGraphConfig

    config = CodeGraphConfig(enabled=True, repo_root=Path("/my/repo"))
    service = CodeGraphService(config)
    stats = service.get_stats()
"""

from superlocalmemory.code_graph.config import CodeGraphConfig
from superlocalmemory.code_graph.models import (
    CodeMemoryLink,
    EdgeKind,
    FileRecord,
    GraphEdge,
    GraphNode,
    LinkType,
    NodeKind,
    ParseResult,
)
from superlocalmemory.code_graph.service import (
    CodeGraphNotEnabledError,
    CodeGraphService,
)

__all__ = [
    "CodeGraphConfig",
    "CodeGraphService",
    "CodeGraphNotEnabledError",
    "GraphNode",
    "GraphEdge",
    "FileRecord",
    "CodeMemoryLink",
    "ParseResult",
    "NodeKind",
    "EdgeKind",
    "LinkType",
]
