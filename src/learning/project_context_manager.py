#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Project Context Manager (v2.7)
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Repository: https://github.com/varun369/SuperLocalMemoryV2
Author: Varun Pratap Bhardwaj (Solution Architect)

NOTICE: This software is protected by MIT License.
Attribution must be preserved in all copies or derivatives.
"""

"""
ProjectContextManager — Layer 2: Multi-signal project detection.

Detects the current active project using 4 weighted signals, not just
the explicit project_name tag. This improves recall by boosting memories
from the currently active project context.

Signal architecture:
    1. project_tag   (weight 3) — Explicit project_name field in memories
    2. project_path  (weight 2) — File path analysis (extract project dir)
    3. active_profile (weight 1) — Profile name (weak signal)
    4. content_cluster (weight 1) — Cluster co-occurrence in recent memories

Winner-take-all with 40% threshold: the candidate project must accumulate
more than 40% of the total weighted signal to be declared the current
project. If no candidate clears the threshold, returns None (ambiguous).

Design principles:
    - Reads memory.db in READ-ONLY mode (never writes to memory.db)
    - Handles missing columns gracefully (older DBs lack project_name)
    - Thread-safe: each method opens/closes its own connection
    - Zero external dependencies (pure stdlib)
"""

import json
import logging
import sqlite3
import threading
from collections import Counter
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger("superlocalmemory.learning.project_context")

MEMORY_DIR = Path.home() / ".claude-memory"
MEMORY_DB_PATH = MEMORY_DIR / "memory.db"
PROFILES_JSON = MEMORY_DIR / "profiles.json"

# Directories commonly found as parents of project roots.
# Used by _extract_project_from_path to identify where the
# project directory begins in a file path.
_PROJECT_PARENT_DIRS = frozenset({
    "projects", "repos", "repositories", "workspace", "workspaces",
    "code", "development", "github", "gitlab",
    "bitbucket", "Documents", "sites", "apps", "services",
    "AGENTIC_Official",  # Varun's workspace convention
})

# Directories that are NOT project names (too generic / too deep).
_SKIP_DIRS = frozenset({
    "src", "lib", "bin", "node_modules", "venv", ".venv", "env",
    ".git", "__pycache__", "dist", "build", "target", "out",
    ".cache", ".config", "tmp", "temp", "logs", "test", "tests",
    "vendor", "packages", "deps",
})


class ProjectContextManager:
    """
    Detects the currently active project using multi-signal analysis.

    Usage:
        pcm = ProjectContextManager()
        project = pcm.detect_current_project()
        if project:
            boost = pcm.get_project_boost(memory, project)

    Thread-safe: safe to call from multiple agents / MCP handlers.
    """

    SIGNAL_WEIGHTS: Dict[str, int] = {
        'project_tag': 3,       # Explicit project_name field
        'project_path': 2,      # File path analysis
        'active_profile': 1,    # Profile name (weak signal)
        'content_cluster': 1,   # Cluster co-occurrence
    }

    def __init__(self, memory_db_path: Optional[Path] = None):
        """
        Initialize ProjectContextManager.

        Args:
            memory_db_path: Path to memory.db. Defaults to
                ~/.claude-memory/memory.db. Opened read-only.
        """
        self._memory_db_path = Path(memory_db_path) if memory_db_path else MEMORY_DB_PATH
        self._lock = threading.Lock()
        # Cache available columns to avoid repeated PRAGMA calls
        self._available_columns: Optional[set] = None
        logger.info(
            "ProjectContextManager initialized: db=%s",
            self._memory_db_path,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_current_project(
        self,
        recent_memories: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """
        Detect the currently active project from recent memory activity.

        Applies 4 weighted signals. The winner must accumulate >40% of the
        total weighted signal to be declared current. Returns None when
        ambiguous or insufficient data.

        Args:
            recent_memories: Pre-fetched list of memory dicts.
                If None, the last 20 memories are fetched from memory.db.

        Returns:
            Project name string or None if undetermined.
        """
        if recent_memories is None:
            recent_memories = self._get_recent_memories(limit=20)

        if not recent_memories:
            logger.debug("No recent memories — cannot detect project")
            return None

        # Accumulate weighted votes per candidate project
        votes: Counter = Counter()

        # --- Signal 1: project_tag (weight 3) ---
        for mem in recent_memories:
            pname = self._safe_get(mem, 'project_name')
            if pname:
                votes[pname] += self.SIGNAL_WEIGHTS['project_tag']

        # --- Signal 2: project_path (weight 2) ---
        for mem in recent_memories:
            ppath = self._safe_get(mem, 'project_path')
            if ppath:
                extracted = self._extract_project_from_path(ppath)
                if extracted:
                    votes[extracted] += self.SIGNAL_WEIGHTS['project_path']

        # --- Signal 3: active_profile (weight 1) ---
        # Profile is a weak signal: only contributes if it matches a
        # project name that already has some votes.
        active_profile = self._get_active_profile()
        if active_profile and active_profile != 'default':
            # If profile name coincides with an existing candidate, boost it.
            # If not, add it as a weak standalone candidate.
            votes[active_profile] += self.SIGNAL_WEIGHTS['active_profile']

        # --- Signal 4: content_cluster (weight 1) ---
        cluster_project = self._match_content_to_clusters(recent_memories)
        if cluster_project:
            votes[cluster_project] += self.SIGNAL_WEIGHTS['content_cluster']

        if not votes:
            logger.debug("No project signals detected in recent memories")
            return None

        # Winner-take-all with 40% threshold
        total_weight = sum(votes.values())
        winner, winner_weight = votes.most_common(1)[0]
        winner_ratio = winner_weight / total_weight if total_weight > 0 else 0.0

        if winner_ratio > 0.4:
            logger.debug(
                "Project detected: '%s' (%.0f%% of signal, %d total weight)",
                winner, winner_ratio * 100, total_weight,
            )
            return winner

        logger.debug(
            "No clear project winner: top='%s' at %.0f%% (threshold 40%%)",
            winner, winner_ratio * 100,
        )
        return None

    def get_project_boost(
        self,
        memory: Dict[str, Any],
        current_project: Optional[str] = None,
    ) -> float:
        """
        Return a boost factor for ranking based on project match.

        Args:
            memory: A memory dict with at least 'project_name' or
                'project_path' fields.
            current_project: The detected current project (from
                detect_current_project). If None, returns neutral.

        Returns:
            1.0  — memory matches current project (boost)
            0.6  — project unknown or memory has no project info (neutral)
            0.3  — memory belongs to a different project (penalty)
        """
        if current_project is None:
            return 0.6  # Unknown project context — neutral

        # Check explicit project_name
        mem_project = self._safe_get(memory, 'project_name')
        if mem_project:
            if mem_project.lower() == current_project.lower():
                return 1.0
            return 0.3  # Definite mismatch

        # Check project_path
        mem_path = self._safe_get(memory, 'project_path')
        if mem_path:
            extracted = self._extract_project_from_path(mem_path)
            if extracted:
                if extracted.lower() == current_project.lower():
                    return 1.0
                return 0.3  # Definite mismatch

        # Memory has no project info — neutral
        return 0.6

    # ------------------------------------------------------------------
    # Data fetching (memory.db — read-only)
    # ------------------------------------------------------------------

    def _get_recent_memories(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch the most recent memories from memory.db.

        Returns a list of dicts with available columns. Handles missing
        columns gracefully (older databases may lack project_name, etc.).
        """
        if not self._memory_db_path.exists():
            logger.debug("memory.db not found at %s", self._memory_db_path)
            return []

        available = self._get_available_columns()

        # Build SELECT with only available columns
        desired_cols = [
            'id', 'project_name', 'project_path', 'profile',
            'content', 'cluster_id', 'created_at',
        ]
        select_cols = [c for c in desired_cols if c in available]

        if not select_cols:
            logger.warning("memories table has none of the expected columns")
            return []

        # Always need at least 'id' — if missing, bail
        if 'id' not in available:
            return []

        col_list = ", ".join(select_cols)

        # Build ORDER BY using best available timestamp
        order_col = 'created_at' if 'created_at' in available else 'id'

        try:
            conn = self._open_memory_db()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT {col_list} FROM memories "
                    f"ORDER BY {order_col} DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()
                # Convert to list of dicts
                result = []
                for row in rows:
                    d = {}
                    for i, col in enumerate(select_cols):
                        d[col] = row[i]
                    result.append(d)
                return result
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.warning("Failed to read recent memories: %s", e)
            return []

    def _get_available_columns(self) -> set:
        """
        Get the set of column names in the memories table.

        Cached after first call to avoid repeated PRAGMA queries.
        """
        if self._available_columns is not None:
            return self._available_columns

        if not self._memory_db_path.exists():
            return set()

        try:
            conn = self._open_memory_db()
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(memories)")
                cols = {row[1] for row in cursor.fetchall()}
                self._available_columns = cols
                return cols
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.warning("Failed to read table schema: %s", e)
            return set()

    def _open_memory_db(self) -> sqlite3.Connection:
        """
        Open a read-only connection to memory.db.

        Uses uri=True with mode=ro to enforce read-only access.
        Falls back to regular connection if URI mode fails
        (some older Python builds do not support it).
        """
        db_str = str(self._memory_db_path)
        try:
            # Prefer URI-based read-only mode
            uri = f"file:{db_str}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=5)
        except (sqlite3.OperationalError, sqlite3.NotSupportedError):
            # Fallback: regular connection (still only reads)
            conn = sqlite3.connect(db_str, timeout=5)
        conn.execute("PRAGMA busy_timeout=3000")
        return conn

    # ------------------------------------------------------------------
    # Signal extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_project_from_path(path: str) -> Optional[str]:
        """
        Extract a project name from a file path.

        Strategy:
            1. Walk path parts looking for a directory that follows a
               known parent directory (projects/, repos/, Documents/, etc.).
            2. If found, the directory immediately after the parent is the
               project name.
            3. Fallback: use the last non-skip directory component.

        Examples:
            /Users/x/projects/MY_PROJECT/src/main.py  -> "MY_PROJECT"
            /home/x/repos/my-app/lib/util.js           -> "my-app"
            /workspace/services/auth-service/index.ts   -> "auth-service"

        Returns:
            Project name string or None if extraction fails.
        """
        if not path:
            return None

        try:
            parts = Path(path).parts
        except (ValueError, TypeError):
            return None

        if len(parts) < 2:
            return None

        # Strategy 1: find part after a known parent directory.
        # Skip consecutive parent dirs (e.g., workspace/services/ both
        # are parent dirs, so the project is the NEXT non-parent part).
        for i, part in enumerate(parts):
            if part in _PROJECT_PARENT_DIRS:
                # Walk forward past any chained parent dirs
                j = i + 1
                while j < len(parts) and parts[j] in _PROJECT_PARENT_DIRS:
                    j += 1
                if j < len(parts):
                    candidate = parts[j]
                    if (
                        candidate
                        and candidate not in _SKIP_DIRS
                        and not candidate.startswith('.')
                    ):
                        return candidate

        # Strategy 2: walk backwards to find last meaningful directory
        # Skip leaf (likely a filename) and known non-project dirs
        for part in reversed(parts[:-1]):  # exclude the last component (filename)
            if (
                part
                and part not in _SKIP_DIRS
                and part not in _PROJECT_PARENT_DIRS
                and not part.startswith('.')
                and not part.startswith('/')
                and len(part) > 1
            ):
                return part

        return None

    @staticmethod
    def _get_active_profile() -> Optional[str]:
        """
        Read the active profile name from profiles.json.

        Returns:
            Profile name string (e.g., "work", "personal") or None.
        """
        if not PROFILES_JSON.exists():
            return None

        try:
            with open(PROFILES_JSON, 'r') as f:
                config = json.load(f)
            return config.get('active_profile', 'default')
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.debug("Failed to read profiles.json: %s", e)
            return None

    def _match_content_to_clusters(
        self,
        recent_memories: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Check if recent memories converge on a single cluster.

        If the most recent 10 memories share a dominant cluster_id, look
        up that cluster's name in graph_clusters and cross-reference with
        the most common project_name within that cluster.

        Returns:
            A project name inferred from cluster dominance, or None.
        """
        # Collect cluster_ids from the most recent 10 memories
        cluster_ids = []
        for mem in recent_memories[:10]:
            cid = self._safe_get(mem, 'cluster_id')
            if cid is not None:
                cluster_ids.append(cid)

        if not cluster_ids:
            return None

        # Find dominant cluster
        cluster_counts = Counter(cluster_ids)
        dominant_id, dominant_count = cluster_counts.most_common(1)[0]

        # Require at least 40% dominance (at least 4 out of 10)
        if dominant_count < max(2, len(cluster_ids) * 0.4):
            return None

        # Look up the dominant project_name within that cluster
        return self._get_cluster_dominant_project(dominant_id)

    def _get_cluster_dominant_project(self, cluster_id: int) -> Optional[str]:
        """
        Find the most common project_name among memories in a given cluster.

        Falls back to the cluster name from graph_clusters if no explicit
        project_name is found.
        """
        if not self._memory_db_path.exists():
            return None

        available = self._get_available_columns()

        try:
            conn = self._open_memory_db()
            try:
                cursor = conn.cursor()

                # Try to find the most common project_name in this cluster
                if 'project_name' in available and 'cluster_id' in available:
                    cursor.execute(
                        "SELECT project_name, COUNT(*) as cnt "
                        "FROM memories "
                        "WHERE cluster_id = ? AND project_name IS NOT NULL "
                        "AND project_name != '' "
                        "GROUP BY project_name "
                        "ORDER BY cnt DESC LIMIT 1",
                        (cluster_id,),
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        return row[0]

                # Fallback: use the cluster name from graph_clusters
                try:
                    cursor.execute(
                        "SELECT name FROM graph_clusters WHERE id = ?",
                        (cluster_id,),
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        return row[0]
                except sqlite3.OperationalError:
                    # graph_clusters table may not exist
                    pass

                return None
            finally:
                conn.close()
        except sqlite3.Error as e:
            logger.debug(
                "Failed to query cluster %d project: %s", cluster_id, e
            )
            return None

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_get(d: Dict[str, Any], key: str) -> Any:
        """
        Safely get a value from a dict, returning None for missing keys
        or empty/whitespace-only strings.
        """
        val = d.get(key)
        if val is None:
            return None
        if isinstance(val, str) and not val.strip():
            return None
        return val

    def invalidate_cache(self):
        """
        Clear the cached column set.

        Call this if the memory.db schema may have changed at runtime
        (e.g., after a migration adds new columns).
        """
        self._available_columns = None


# ======================================================================
# Standalone testing
# ======================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    pcm = ProjectContextManager()

    # Test path extraction
    test_paths = [
        "/Users/varun/projects/SuperLocalMemoryV2/src/main.py",
        "/home/dev/repos/my-app/lib/util.js",
        "/workspace/services/auth-service/index.ts",
        "/Users/varun/Documents/AGENTIC_Official/SuperLocalMemoryV2-repo/src/learning/foo.py",
        "",
        None,
    ]
    print("=== Path Extraction Tests ===")
    for p in test_paths:
        result = ProjectContextManager._extract_project_from_path(p)
        print(f"  {p!r:60s} -> {result!r}")

    # Test full detection
    print("\n=== Project Detection ===")
    project = pcm.detect_current_project()
    print(f"  Detected project: {project!r}")

    # Test boost
    print("\n=== Boost Tests ===")
    if project:
        test_mem_match = {'project_name': project}
        test_mem_miss = {'project_name': 'other-project'}
        test_mem_none = {'content': 'no project info'}
        print(f"  Match boost:   {pcm.get_project_boost(test_mem_match, project)}")
        print(f"  Mismatch boost: {pcm.get_project_boost(test_mem_miss, project)}")
        print(f"  Unknown boost:  {pcm.get_project_boost(test_mem_none, project)}")
    else:
        print("  No project detected — all boosts return 0.6 (neutral)")
        print(f"  Neutral boost: {pcm.get_project_boost({}, None)}")
