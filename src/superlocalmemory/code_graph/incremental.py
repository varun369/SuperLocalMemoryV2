# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory v3.4 — CodeGraph Module

"""IncrementalUpdater — hash-based change detection + dependent tracing.

Given a list of changed file paths:
1. SHA-256 hash check to skip unchanged files
2. Re-parse changed files
3. Trace dependents via IMPORTS edges
4. Re-parse dependent files (their edges may be stale)
5. Invalidate the in-memory graph cache
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from superlocalmemory.code_graph.graph_engine import GraphEngine
from superlocalmemory.code_graph.graph_store import GraphStore
from superlocalmemory.code_graph.models import (
    FileRecord,
    GraphEdge,
    GraphNode,
    ParseResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parser protocol (dependency inversion — no import of Phase 1 parser)
# ---------------------------------------------------------------------------

class ParserProtocol(Protocol):
    """Minimal interface the IncrementalUpdater needs from a parser."""

    def parse_file(self, file_path: str, repo_root: Path) -> ParseResult:
        """Parse a single file and return nodes, edges, file record."""
        ...


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UpdateResult:
    """Result of an incremental update run."""

    parsed: int = 0
    skipped: int = 0
    deleted: int = 0
    dependents_parsed: int = 0
    errors: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# IncrementalUpdater
# ---------------------------------------------------------------------------

class IncrementalUpdater:
    """Hash-based incremental graph updater.

    Usage::

        updater = IncrementalUpdater(store, engine)
        result = updater.update(
            changed_files=["src/foo.py", "src/bar.py"],
            parser=my_parser,
            repo_root=Path("/my/repo"),
        )
    """

    def __init__(self, store: GraphStore, engine: GraphEngine) -> None:
        self._store = store
        self._engine = engine

    def update(
        self,
        changed_files: list[str],
        parser: ParserProtocol,
        repo_root: Path,
    ) -> UpdateResult:
        """Run incremental update for *changed_files*.

        Parameters
        ----------
        changed_files : relative file paths (relative to repo_root)
        parser : object implementing ParserProtocol
        repo_root : absolute path to repository root

        Returns
        -------
        UpdateResult with counts of parsed/skipped/deleted/dependents_parsed.
        """
        if not changed_files:
            return UpdateResult()

        # Load stored hashes
        stored_hashes: dict[str, str] = {}
        for rec in self._store.get_all_file_records():
            stored_hashes[rec.file_path] = rec.content_hash

        # Partition files
        files_to_parse: list[tuple[str, str]] = []  # (rel_path, new_hash)
        files_to_delete: list[str] = []
        skipped = 0
        errors: list[str] = []

        for rel_path in changed_files:
            abs_path = repo_root / rel_path
            if not abs_path.exists():
                files_to_delete.append(rel_path)
                continue

            try:
                content_bytes = abs_path.read_bytes()
            except OSError as exc:
                errors.append(f"Cannot read {rel_path}: {exc}")
                continue

            new_hash = hashlib.sha256(content_bytes).hexdigest()

            if stored_hashes.get(rel_path) == new_hash:
                skipped += 1
                continue

            files_to_parse.append((rel_path, new_hash))

        # Trace dependents BEFORE modifying the store — FK cascades
        # would destroy the edges we need for dependency resolution.
        all_changing = {fp for fp, _ in files_to_parse} | set(files_to_delete)
        dependent_files: set[str] = set()
        for fp in all_changing:
            deps = self._store.find_dependents(fp)
            dependent_files.update(deps)

        # Delete removed files
        deleted = 0
        for fp in files_to_delete:
            self._store.remove_file(fp)
            deleted += 1

        # Parse changed files
        parsed = 0
        parsed_paths: set[str] = set()
        for rel_path, _new_hash in files_to_parse:
            try:
                result = parser.parse_file(rel_path, repo_root)
                self._store.store_file_nodes_edges(
                    result.file_path,
                    list(result.nodes),
                    list(result.edges),
                    result.file_record,
                )
                parsed += 1
                parsed_paths.add(rel_path)
            except Exception as exc:
                errors.append(f"Parse error {rel_path}: {exc}")
                logger.warning("Failed to parse %s: %s", rel_path, exc)

        # Remove already-handled files
        dependent_files -= parsed_paths
        dependent_files -= set(files_to_delete)

        # Re-parse dependents
        dependents_parsed = 0
        for dep_path in dependent_files:
            abs_dep = repo_root / dep_path
            if not abs_dep.exists():
                continue
            try:
                result = parser.parse_file(dep_path, repo_root)
                self._store.store_file_nodes_edges(
                    result.file_path,
                    list(result.nodes),
                    list(result.edges),
                    result.file_record,
                )
                dependents_parsed += 1
            except Exception as exc:
                errors.append(f"Dependent parse error {dep_path}: {exc}")
                logger.warning("Failed to parse dependent %s: %s", dep_path, exc)

        # Invalidate engine cache
        self._engine.invalidate()

        return UpdateResult(
            parsed=parsed,
            skipped=skipped,
            deleted=deleted,
            dependents_parsed=dependents_parsed,
            errors=tuple(errors),
        )
