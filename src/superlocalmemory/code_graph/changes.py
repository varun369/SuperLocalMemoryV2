# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""ChangeAnalyzer — git diff to risk-scored change analysis.

Parses git diff output, maps changed line ranges to graph nodes,
computes 5-factor risk scores, and produces review context.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from superlocalmemory.code_graph.database import CodeGraphDatabase
from superlocalmemory.code_graph.models import EdgeKind

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SECURITY_KEYWORDS: frozenset[str] = frozenset([
    "auth", "login", "password", "token", "session", "crypt", "secret",
    "credential", "permission", "sql", "query", "execute", "connect",
    "socket", "request", "http", "sanitize", "validate", "encrypt",
    "decrypt", "hash", "sign", "verify", "admin", "privilege",
])

_GIT_TIMEOUT_SECONDS = 30
_HUNK_HEADER_RE = re.compile(r'\+(\d+)(?:,(\d+))?')


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DiffHunk:
    """A single changed line range in a file."""
    file_path: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class ChangedNode:
    """A graph node affected by a change, with risk score."""
    node_id: str
    name: str
    kind: str
    file_path: str
    line_start: int
    line_end: int
    risk_score: float


@dataclass(frozen=True)
class ReviewContext:
    """Token-optimized review context for changed files."""
    summary: str
    changed_nodes: tuple[ChangedNode, ...]
    test_gaps: tuple[ChangedNode, ...]
    review_priorities: tuple[ChangedNode, ...]
    overall_risk: float


# ---------------------------------------------------------------------------
# ChangeAnalyzer
# ---------------------------------------------------------------------------

class ChangeAnalyzer:
    """Analyze git changes and map to graph nodes with risk scores.

    All git operations use subprocess with timeout for safety.
    """

    def __init__(self, db: CodeGraphDatabase) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_changes(
        self, changed_files: list[str], repo_root: Path | None = None
    ) -> ReviewContext:
        """Analyze changed files and produce risk-scored review context.

        Args:
            changed_files: List of relative file paths that changed.
            repo_root: Optional repo root for git diff parsing.

        Returns:
            ReviewContext with scored nodes and review priorities.
        """
        if not changed_files:
            return ReviewContext(
                summary="No changes detected.",
                changed_nodes=(),
                test_gaps=(),
                review_priorities=(),
                overall_risk=0.0,
            )

        # Map changed files to affected nodes
        all_changed: dict[str, ChangedNode] = {}
        for file_path in changed_files:
            nodes = self._find_nodes_in_file(file_path)
            for node in nodes:
                risk = self.compute_risk_score(node)
                scored_node = ChangedNode(
                    node_id=node["node_id"],
                    name=node["name"],
                    kind=node["kind"],
                    file_path=node["file_path"],
                    line_start=node["line_start"],
                    line_end=node["line_end"],
                    risk_score=risk,
                )
                all_changed[node["node_id"]] = scored_node

        changed_list = tuple(sorted(
            all_changed.values(), key=lambda n: -n.risk_score
        ))

        # Find test gaps (changed non-test nodes without TESTED_BY)
        test_gaps = tuple(
            n for n in changed_list
            if n.kind not in ("file", "module")
            and not self._has_test_coverage(n.node_id)
        )

        # Top review priorities
        review_priorities = changed_list[:10]

        # Overall risk
        overall_risk = max(
            (n.risk_score for n in changed_list), default=0.0
        )

        summary = (
            f"{len(changed_list)} changed nodes across "
            f"{len(changed_files)} files. "
            f"{len(test_gaps)} untested changes. "
            f"Overall risk: {overall_risk:.2f}."
        )

        return ReviewContext(
            summary=summary,
            changed_nodes=changed_list,
            test_gaps=test_gaps,
            review_priorities=review_priorities,
            overall_risk=overall_risk,
        )

    def compute_risk_score(self, node: dict[str, Any]) -> float:
        """5-factor risk scoring for a single node.

        Factors:
        1. flow_participation (max 0.25)
        2. community_crossing (max 0.15)
        3. test_coverage (0.05 if tested, 0.30 if untested)
        4. security_keywords (0 or 0.20)
        5. caller_count (max 0.10)
        """
        node_id = node["node_id"]
        name = node.get("name", "")

        # 1. Flow participation
        flow_score = self._flow_participation_score(node_id)

        # 2. Community crossing
        cross_score = self._community_crossing_score(node_id)

        # 3. Test coverage
        has_test = self._has_test_coverage(node_id)
        test_score = 0.05 if has_test else 0.30

        # 4. Security sensitivity
        security_score = (
            0.20
            if any(kw in name.lower() for kw in SECURITY_KEYWORDS)
            else 0.0
        )

        # 5. Caller count
        caller_score = self._caller_count_score(node_id)

        return flow_score + cross_score + test_score + security_score + caller_score

    def get_review_context(
        self, changed_files: list[str], repo_root: Path | None = None
    ) -> ReviewContext:
        """Token-optimized review context.

        Same as analyze_changes but designed for LLM consumption.
        """
        return self.analyze_changes(changed_files, repo_root)

    # ------------------------------------------------------------------
    # Static: git diff parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_git_diff(
        repo_root: Path, base: str = "HEAD~1", timeout: int = _GIT_TIMEOUT_SECONDS
    ) -> list[DiffHunk]:
        """Parse git diff to get changed line ranges.

        Args:
            repo_root: Path to the git repository root.
            base: Git ref to diff against.
            timeout: Subprocess timeout in seconds.

        Returns:
            List of DiffHunk with file paths and line ranges.
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--unified=0", base, "--"],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
                timeout=timeout,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            logger.warning("git diff failed: %s", exc)
            return []

        if result.returncode != 0:
            logger.debug("git diff returned %d: %s", result.returncode, result.stderr)
            return []

        return _parse_diff_output(result.stdout)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_nodes_in_file(self, file_path: str) -> list[dict[str, Any]]:
        """Find all graph nodes in a file."""
        rows = self._db.execute(
            """SELECT node_id, name, kind, file_path, line_start, line_end
               FROM graph_nodes
               WHERE file_path = ?
               ORDER BY line_start""",
            (file_path,),
        )
        return [dict(row) for row in rows]

    def _has_test_coverage(self, node_id: str) -> bool:
        """Check if a node has TESTED_BY edges or is called by test nodes."""
        # Check outgoing TESTED_BY
        rows = self._db.execute(
            """SELECT COUNT(*) as cnt FROM graph_edges
               WHERE source_node_id = ? AND kind = ?""",
            (node_id, EdgeKind.TESTED_BY.value),
        )
        if rows and rows[0]["cnt"] > 0:
            return True

        # Check incoming CALLS from test nodes
        rows = self._db.execute(
            """SELECT COUNT(*) as cnt FROM graph_edges ge
               JOIN graph_nodes gn ON ge.source_node_id = gn.node_id
               WHERE ge.target_node_id = ?
                 AND ge.kind = ?
                 AND gn.is_test = 1""",
            (node_id, EdgeKind.CALLS.value),
        )
        return bool(rows and rows[0]["cnt"] > 0)

    def _flow_participation_score(self, node_id: str) -> float:
        """Score based on how many flows this node participates in.

        Uses stored flows from graph_metadata. Max 0.25.
        """
        import json
        raw = self._db.get_metadata("flows")
        if not raw:
            return 0.0
        try:
            flows = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return 0.0

        count = sum(
            1 for f in flows
            if node_id in f.get("path_node_ids", [])
        )
        return min(count * 0.05, 0.25)

    def _community_crossing_score(self, node_id: str) -> float:
        """Score based on cross-community callers. Max 0.15."""
        # Get this node's community
        node_rows = self._db.execute(
            "SELECT community_id FROM graph_nodes WHERE node_id = ?",
            (node_id,),
        )
        if not node_rows:
            return 0.0
        my_community = node_rows[0]["community_id"]

        # Get callers and their communities
        callers = self._db.execute(
            """SELECT gn.community_id
               FROM graph_edges ge
               JOIN graph_nodes gn ON ge.source_node_id = gn.node_id
               WHERE ge.target_node_id = ?
                 AND ge.kind = ?""",
            (node_id, EdgeKind.CALLS.value),
        )
        cross_count = sum(
            1 for row in callers
            if row["community_id"] is not None
            and row["community_id"] != my_community
        )
        return min(cross_count * 0.05, 0.15)

    def _caller_count_score(self, node_id: str) -> float:
        """Score based on number of callers. Max 0.10."""
        rows = self._db.execute(
            """SELECT COUNT(*) as cnt FROM graph_edges
               WHERE target_node_id = ? AND kind = ?""",
            (node_id, EdgeKind.CALLS.value),
        )
        count = rows[0]["cnt"] if rows else 0
        return min(count / 20.0, 0.10)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _parse_diff_output(diff_text: str) -> list[DiffHunk]:
    """Parse unified diff output into DiffHunk list."""
    hunks: list[DiffHunk] = []
    current_file: str | None = None

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@"):
            match = _HUNK_HEADER_RE.search(line)
            if match and current_file:
                start = int(match.group(1))
                count = int(match.group(2) or "1")
                if count > 0:
                    hunks.append(DiffHunk(
                        file_path=current_file,
                        start_line=start,
                        end_line=start + count - 1,
                    ))

    return hunks
