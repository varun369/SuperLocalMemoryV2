# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""FlowDetector — entry point detection and execution flow tracing.

Detects entry points (nodes with no incoming CALLS edges),
traces BFS forward through CALLS edges, and scores criticality.
Flows stored in graph_metadata as JSON.
"""

from __future__ import annotations

import json
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from superlocalmemory.code_graph.database import CodeGraphDatabase
from superlocalmemory.code_graph.models import EdgeKind, NodeKind

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FlowResult:
    """A detected execution flow."""
    name: str
    entry_node_id: str
    depth: int
    node_count: int
    file_count: int
    criticality: float
    path_node_ids: tuple[str, ...]


# ---------------------------------------------------------------------------
# Security keywords (frozen constant)
# ---------------------------------------------------------------------------

SECURITY_KEYWORDS: frozenset[str] = frozenset([
    "auth", "login", "password", "token", "session", "crypt", "secret",
    "credential", "permission", "sql", "query", "execute", "connect",
    "socket", "request", "http", "sanitize", "validate", "encrypt",
    "decrypt", "hash", "sign", "verify", "admin", "privilege",
])

# Default entry point name patterns
_DEFAULT_ENTRY_PATTERNS: tuple[str, ...] = (
    r"^main$", r"^__main__$", r"^test_", r"^Test[A-Z]",
    r"^on_", r"^handle_", r"^cli_", r"^command_",
)


# ---------------------------------------------------------------------------
# FlowDetector
# ---------------------------------------------------------------------------

class FlowDetector:
    """Detect execution flows through the code graph.

    Identifies entry points (nodes with no incoming CALLS edges or
    matching configurable patterns), traces BFS forward through CALLS
    edges, and computes criticality scores.
    """

    def __init__(
        self,
        db: CodeGraphDatabase,
        entry_patterns: tuple[str, ...] | None = None,
    ) -> None:
        self._db = db
        self._entry_patterns = entry_patterns or _DEFAULT_ENTRY_PATTERNS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_entry_points(self) -> list[str]:
        """Find nodes with no incoming CALLS edges.

        Also includes nodes matching entry point name patterns.

        Returns:
            List of node_id strings for entry points.
        """
        # Get all nodes that are functions or methods (not files/modules)
        all_nodes = self._db.execute(
            """SELECT node_id, name, kind FROM graph_nodes
               WHERE kind IN ('function', 'method')""",
            (),
        )
        if not all_nodes:
            return []

        # Get all nodes that HAVE incoming CALLS edges
        called_nodes = self._db.execute(
            """SELECT DISTINCT target_node_id
               FROM graph_edges
               WHERE kind = ?""",
            (EdgeKind.CALLS.value,),
        )
        called_ids = {row["target_node_id"] for row in called_nodes}

        entry_points: list[str] = []
        for row in all_nodes:
            node_id = row["node_id"]
            name = row["name"]

            # No incoming CALLS -> entry point
            if node_id not in called_ids:
                entry_points.append(node_id)
                continue

            # Pattern match check (even if called, these are entry points)
            if self._matches_entry_pattern(name):
                entry_points.append(node_id)

        return entry_points

    def trace_flow(
        self, entry_node_id: str, max_depth: int = 15
    ) -> FlowResult:
        """BFS forward through CALLS edges from an entry point.

        Args:
            entry_node_id: Starting node ID.
            max_depth: Maximum BFS depth.

        Returns:
            FlowResult with path, depth, and metadata.
        """
        # Load entry node info
        entry_rows = self._db.execute(
            "SELECT node_id, name, kind, file_path FROM graph_nodes WHERE node_id = ?",
            (entry_node_id,),
        )
        if not entry_rows:
            return FlowResult(
                name="unknown",
                entry_node_id=entry_node_id,
                depth=0,
                node_count=0,
                file_count=0,
                criticality=0.0,
                path_node_ids=(),
            )

        entry_name = entry_rows[0]["name"]

        # BFS forward
        visited: set[str] = {entry_node_id}
        path: list[str] = [entry_node_id]
        frontier: set[str] = {entry_node_id}
        depth = 0

        while frontier and depth < max_depth:
            next_frontier: set[str] = set()
            for nid in frontier:
                outgoing = self._db.execute(
                    """SELECT target_node_id FROM graph_edges
                       WHERE source_node_id = ? AND kind = ?""",
                    (nid, EdgeKind.CALLS.value),
                )
                for row in outgoing:
                    target = row["target_node_id"]
                    if target not in visited:
                        visited.add(target)
                        path.append(target)
                        next_frontier.add(target)
            frontier = next_frontier
            depth += 1

        # Collect file paths for file_count
        file_paths = self._get_file_paths(path)

        return FlowResult(
            name=f"flow_{entry_name}",
            entry_node_id=entry_node_id,
            depth=depth,
            node_count=len(path),
            file_count=len(file_paths),
            criticality=0.0,  # Will be computed later
            path_node_ids=tuple(path),
        )

    def trace_all_flows(self, max_depth: int = 15) -> list[FlowResult]:
        """Detect all entry points, trace each, score criticality.

        Returns:
            List of FlowResult sorted by criticality (highest first).
        """
        entry_points = self.detect_entry_points()
        flows: list[FlowResult] = []

        for ep_id in entry_points:
            flow = self.trace_flow(ep_id, max_depth)
            # Skip trivial single-node flows
            if flow.node_count < 2:
                continue
            # Compute criticality
            criticality = self._compute_criticality(flow)
            flow = FlowResult(
                name=flow.name,
                entry_node_id=flow.entry_node_id,
                depth=flow.depth,
                node_count=flow.node_count,
                file_count=flow.file_count,
                criticality=criticality,
                path_node_ids=flow.path_node_ids,
            )
            flows.append(flow)

        # Sort by criticality descending
        flows.sort(key=lambda f: -f.criticality)

        # Store in metadata
        self._store_flows(flows)

        return flows

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _matches_entry_pattern(self, name: str) -> bool:
        """Check if node name matches any entry point pattern."""
        for pattern in self._entry_patterns:
            if re.search(pattern, name):
                return True
        return False

    def _get_file_paths(self, node_ids: list[str]) -> set[str]:
        """Get unique file paths for a list of node IDs."""
        if not node_ids:
            return set()
        placeholders = ",".join("?" for _ in node_ids)
        rows = self._db.execute(
            f"SELECT DISTINCT file_path FROM graph_nodes WHERE node_id IN ({placeholders})",
            tuple(node_ids),
        )
        return {row["file_path"] for row in rows}

    def _compute_criticality(self, flow: FlowResult) -> float:
        """Compute criticality score for a flow.

        5-factor weighted score:
        - depth (0.10): deeper flows are more critical
        - node_count (0.15): more nodes = more complex
        - file_count (0.30): cross-file flows are riskier
        - test_coverage (0.20): untested paths are riskier
        - security_keywords (0.25): security-related code is critical
        """
        # Depth score (weight 0.10)
        depth_score = min(flow.depth / 10.0, 1.0) * 0.10

        # Node count score (weight 0.15)
        node_score = min(flow.node_count / 20.0, 1.0) * 0.15

        # File spread score (weight 0.30)
        file_score = min((flow.file_count - 1) / 4.0, 1.0) * 0.30

        # Test coverage gap (weight 0.20)
        tested_count = self._count_tested_nodes(flow.path_node_ids)
        coverage_score = (
            (1.0 - tested_count / max(flow.node_count, 1)) * 0.20
        )

        # Security sensitivity (weight 0.25)
        security_hits = self._count_security_nodes(flow.path_node_ids)
        security_score = (
            min(security_hits / max(flow.node_count, 1), 1.0) * 0.25
        )

        return depth_score + node_score + file_score + coverage_score + security_score

    def _count_tested_nodes(self, node_ids: tuple[str, ...]) -> int:
        """Count nodes that have TESTED_BY edges."""
        if not node_ids:
            return 0
        placeholders = ",".join("?" for _ in node_ids)
        rows = self._db.execute(
            f"""SELECT COUNT(DISTINCT source_node_id) as cnt
                FROM graph_edges
                WHERE source_node_id IN ({placeholders})
                  AND kind = ?""",
            (*node_ids, EdgeKind.TESTED_BY.value),
        )
        return rows[0]["cnt"] if rows else 0

    def _count_security_nodes(self, node_ids: tuple[str, ...]) -> int:
        """Count nodes whose names contain security keywords."""
        if not node_ids:
            return 0
        placeholders = ",".join("?" for _ in node_ids)
        rows = self._db.execute(
            f"SELECT node_id, name FROM graph_nodes WHERE node_id IN ({placeholders})",
            tuple(node_ids),
        )
        count = 0
        for row in rows:
            name_lower = row["name"].lower()
            if any(kw in name_lower for kw in SECURITY_KEYWORDS):
                count += 1
        return count

    def _store_flows(self, flows: list[FlowResult]) -> None:
        """Store flows in graph_metadata as JSON."""
        flow_data = [
            {
                "name": f.name,
                "entry_node_id": f.entry_node_id,
                "depth": f.depth,
                "node_count": f.node_count,
                "file_count": f.file_count,
                "criticality": f.criticality,
                "path_node_ids": list(f.path_node_ids),
            }
            for f in flows
        ]
        self._db.set_metadata("flows", json.dumps(flow_data))

    def get_stored_flows(self) -> list[FlowResult]:
        """Load flows from graph_metadata."""
        raw = self._db.get_metadata("flows")
        if not raw:
            return []
        try:
            flow_data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

        return [
            FlowResult(
                name=f["name"],
                entry_node_id=f["entry_node_id"],
                depth=f["depth"],
                node_count=f["node_count"],
                file_count=f["file_count"],
                criticality=f["criticality"],
                path_node_ids=tuple(f["path_node_ids"]),
            )
            for f in flow_data
        ]
