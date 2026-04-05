# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""CommunityDetector — file-based community detection.

Groups nodes by file path prefix / directory for MVP.
igraph/Leiden can be added later for more sophisticated detection.
Stores community_id on graph_nodes via UPDATE.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from superlocalmemory.code_graph.database import CodeGraphDatabase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommunityInfo:
    """Detected code community."""
    community_id: int
    name: str
    directory: str
    size: int
    dominant_language: str | None
    file_count: int
    cohesion: float
    node_ids: tuple[str, ...]


@dataclass(frozen=True)
class CouplingWarning:
    """Warning about high coupling between communities."""
    source_community: str
    target_community: str
    edge_count: int
    severity: str  # "low", "medium", "high"


@dataclass(frozen=True)
class ArchitectureOverview:
    """Architecture overview with communities and coupling warnings."""
    communities: tuple[CommunityInfo, ...]
    coupling_warnings: tuple[CouplingWarning, ...]
    total_nodes: int
    total_communities: int


# ---------------------------------------------------------------------------
# CommunityDetector
# ---------------------------------------------------------------------------

class CommunityDetector:
    """File-based community detection.

    Groups nodes by directory (file path prefix).
    Each unique directory becomes a community.
    """

    def __init__(self, db: CodeGraphDatabase) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_communities(self) -> list[CommunityInfo]:
        """Detect communities by grouping nodes by directory.

        Updates community_id on graph_nodes.

        Returns:
            List of CommunityInfo sorted by size (largest first).
        """
        # Load all nodes
        rows = self._db.execute(
            "SELECT node_id, name, kind, file_path, language FROM graph_nodes",
            (),
        )
        if not rows:
            return []

        # Group by directory
        dir_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            directory = _extract_directory(row["file_path"])
            dir_groups[directory].append(dict(row))

        # Build communities
        communities: list[CommunityInfo] = []
        for comm_id, (directory, nodes) in enumerate(sorted(dir_groups.items())):
            node_ids = tuple(n["node_id"] for n in nodes)
            languages = [n["language"] for n in nodes if n.get("language")]
            dominant_lang = _dominant_language(languages)
            file_paths = {n["file_path"] for n in nodes}

            community = CommunityInfo(
                community_id=comm_id,
                name=_generate_community_name(directory, nodes),
                directory=directory,
                size=len(nodes),
                dominant_language=dominant_lang,
                file_count=len(file_paths),
                cohesion=1.0,  # Trivially cohesive for file-based
                node_ids=node_ids,
            )
            communities.append(community)

        # Update community_id on nodes
        self._update_node_communities(communities)

        # Sort by size descending
        communities.sort(key=lambda c: -c.size)

        # Store in metadata
        self._store_communities(communities)

        return communities

    def get_architecture_overview(self) -> ArchitectureOverview:
        """Return community summary with coupling warnings.

        Returns:
            ArchitectureOverview with communities and cross-community coupling.
        """
        # Load or detect communities
        communities = self._load_communities()
        if not communities:
            communities = self.detect_communities()

        # Compute coupling warnings
        warnings = self._compute_coupling_warnings(communities)

        total_nodes = sum(c.size for c in communities)

        return ArchitectureOverview(
            communities=tuple(communities),
            coupling_warnings=tuple(warnings),
            total_nodes=total_nodes,
            total_communities=len(communities),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_node_communities(
        self, communities: list[CommunityInfo]
    ) -> None:
        """Update community_id on graph_nodes."""
        for community in communities:
            if not community.node_ids:
                continue
            placeholders = ",".join("?" for _ in community.node_ids)
            self._db.execute_write(
                f"""UPDATE graph_nodes SET community_id = ?
                    WHERE node_id IN ({placeholders})""",
                (community.community_id, *community.node_ids),
            )

    def _compute_coupling_warnings(
        self, communities: list[CommunityInfo]
    ) -> list[CouplingWarning]:
        """Find cross-community edges and generate coupling warnings."""
        # Build node_id -> community_name map
        node_to_community: dict[str, str] = {}
        for comm in communities:
            for nid in comm.node_ids:
                node_to_community[nid] = comm.name

        # Count cross-community edges
        cross_edges: dict[tuple[str, str], int] = defaultdict(int)

        edges = self._db.execute(
            "SELECT source_node_id, target_node_id FROM graph_edges",
            (),
        )
        for row in edges:
            src_comm = node_to_community.get(row["source_node_id"])
            tgt_comm = node_to_community.get(row["target_node_id"])
            if src_comm and tgt_comm and src_comm != tgt_comm:
                pair = (
                    min(src_comm, tgt_comm),
                    max(src_comm, tgt_comm),
                )
                cross_edges[pair] += 1

        # Generate warnings
        warnings: list[CouplingWarning] = []
        for (src, tgt), count in sorted(
            cross_edges.items(), key=lambda x: -x[1]
        ):
            if count >= 10:
                severity = "high"
            elif count >= 5:
                severity = "medium"
            else:
                severity = "low"

            warnings.append(CouplingWarning(
                source_community=src,
                target_community=tgt,
                edge_count=count,
                severity=severity,
            ))

        return warnings

    def _store_communities(self, communities: list[CommunityInfo]) -> None:
        """Store communities in graph_metadata as JSON."""
        data = [
            {
                "community_id": c.community_id,
                "name": c.name,
                "directory": c.directory,
                "size": c.size,
                "dominant_language": c.dominant_language,
                "file_count": c.file_count,
                "cohesion": c.cohesion,
                "node_ids": list(c.node_ids),
            }
            for c in communities
        ]
        self._db.set_metadata("communities", json.dumps(data))

    def _load_communities(self) -> list[CommunityInfo]:
        """Load communities from graph_metadata."""
        raw = self._db.get_metadata("communities")
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

        return [
            CommunityInfo(
                community_id=c["community_id"],
                name=c["name"],
                directory=c["directory"],
                size=c["size"],
                dominant_language=c.get("dominant_language"),
                file_count=c["file_count"],
                cohesion=c["cohesion"],
                node_ids=tuple(c["node_ids"]),
            )
            for c in data
        ]


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _extract_directory(file_path: str) -> str:
    """Extract the directory from a file path."""
    parent = str(PurePosixPath(file_path).parent)
    return parent if parent != "." else "root"


def _generate_community_name(
    directory: str, nodes: list[dict[str, Any]]
) -> str:
    """Generate a human-readable community name.

    Uses directory name + most common class name (if any).
    """
    # Extract most common class name
    class_names = [
        n["name"] for n in nodes
        if n.get("kind") == "class"
    ]
    if class_names:
        most_common = Counter(class_names).most_common(1)[0][0]
        return f"{directory}/{most_common}"

    # Fall back to directory name
    parts = directory.rstrip("/").split("/")
    return parts[-1] if parts else directory


def _dominant_language(languages: list[str]) -> str | None:
    """Find the most common language."""
    if not languages:
        return None
    counts = Counter(languages)
    return counts.most_common(1)[0][0]
