#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Intelligent Local Memory System
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Repository: https://github.com/varun369/SuperLocalMemoryV2
Author: Varun Pratap Bhardwaj (Solution Architect)

NOTICE: This software is protected by MIT License.
Attribution must be preserved in all copies or derivatives.
"""

"""
MemoryStore V2 - Extended Memory System with Tree and Graph Support
Maintains backward compatibility with V1 API while adding:
- Tree hierarchy (parent_id, tree_path, depth)
- Categories and clusters
- Tier-based progressive summarization
- Enhanced search with tier filtering
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# TF-IDF for local semantic search (no external APIs)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

MEMORY_DIR = Path.home() / ".claude-memory"
DB_PATH = MEMORY_DIR / "memory.db"
VECTORS_PATH = MEMORY_DIR / "vectors"


class MemoryStoreV2:
    """
    Extended memory store with hierarchical tree and graph integration.

    Key Features:
    - Tree hierarchy via parent_id and materialized paths
    - Category-based organization
    - GraphRAG cluster integration
    - Tier-based access tracking
    - Backward compatible with V1 API
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize MemoryStore V2.

        Args:
            db_path: Optional custom database path (defaults to ~/.claude-memory/memory.db)
        """
        self.db_path = db_path or DB_PATH
        self.vectors_path = VECTORS_PATH
        self._init_db()
        self.vectorizer = None
        self.vectors = None
        self.memory_ids = []
        self._load_vectors()

    def _init_db(self):
        """Initialize SQLite database with V2 schema extensions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if we need to add V2 columns to existing table
        cursor.execute("PRAGMA table_info(memories)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Main memories table (V1 compatible + V2 extensions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                summary TEXT,

                -- Organization
                project_path TEXT,
                project_name TEXT,
                tags TEXT,
                category TEXT,

                -- Hierarchy (Layer 2 link)
                parent_id INTEGER,
                tree_path TEXT,
                depth INTEGER DEFAULT 0,

                -- Metadata
                memory_type TEXT DEFAULT 'session',
                importance INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0,

                -- Deduplication
                content_hash TEXT UNIQUE,

                -- Graph (Layer 3 link)
                cluster_id INTEGER,

                FOREIGN KEY (parent_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        ''')

        # Add missing V2 columns to existing table (migration support)
        v2_columns = {
            'category': 'TEXT',
            'parent_id': 'INTEGER',
            'tree_path': 'TEXT',
            'depth': 'INTEGER DEFAULT 0',
            'last_accessed': 'TIMESTAMP',
            'access_count': 'INTEGER DEFAULT 0',
            'cluster_id': 'INTEGER'
        }

        for col_name, col_type in v2_columns.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE memories ADD COLUMN {col_name} {col_type}')
                except sqlite3.OperationalError:
                    # Column might already exist from concurrent migration
                    pass

        # Sessions table (V1 compatible)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                project_path TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                summary TEXT
            )
        ''')

        # Full-text search index (V1 compatible)
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(content, summary, tags, content='memories', content_rowid='id')
        ''')

        # FTS Triggers (V1 compatible)
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, summary, tags)
                VALUES (new.id, new.content, new.summary, new.tags);
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, summary, tags)
                VALUES('delete', old.id, old.content, old.summary, old.tags);
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, summary, tags)
                VALUES('delete', old.id, old.content, old.summary, old.tags);
                INSERT INTO memories_fts(rowid, content, summary, tags)
                VALUES (new.id, new.content, new.summary, new.tags);
            END
        ''')

        # Create indexes for V2 fields
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_project ON memories(project_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON memories(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tree_path ON memories(tree_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cluster ON memories(cluster_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_accessed ON memories(last_accessed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parent_id ON memories(parent_id)')

        conn.commit()
        conn.close()

    def _content_hash(self, content: str) -> str:
        """Generate hash for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    # SECURITY: Input validation limits
    MAX_CONTENT_SIZE = 1_000_000    # 1MB max content
    MAX_SUMMARY_SIZE = 10_000       # 10KB max summary
    MAX_TAG_LENGTH = 50             # 50 chars per tag
    MAX_TAGS = 20                   # 20 tags max

    def add_memory(
        self,
        content: str,
        summary: Optional[str] = None,
        project_path: Optional[str] = None,
        project_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        parent_id: Optional[int] = None,
        memory_type: str = "session",
        importance: int = 5
    ) -> int:
        """
        Add a new memory with V2 enhancements.

        Args:
            content: Memory content (required, max 1MB)
            summary: Optional summary (max 10KB)
            project_path: Project absolute path
            project_name: Human-readable project name
            tags: List of tags (max 20 tags, 50 chars each)
            category: High-level category (e.g., "frontend", "backend")
            parent_id: Parent memory ID for hierarchical nesting
            memory_type: Type of memory ('session', 'long-term', 'reference')

        Raises:
            TypeError: If content is not a string
            ValueError: If content is empty or exceeds size limits

        Returns:
            Memory ID (int), or existing ID if duplicate detected
        """
        # SECURITY: Input validation
        if not isinstance(content, str):
            raise TypeError("Content must be a string")

        content = content.strip()
        if not content:
            raise ValueError("Content cannot be empty")

        if len(content) > self.MAX_CONTENT_SIZE:
            raise ValueError(f"Content exceeds maximum size of {self.MAX_CONTENT_SIZE} bytes")

        if summary and len(summary) > self.MAX_SUMMARY_SIZE:
            raise ValueError(f"Summary exceeds maximum size of {self.MAX_SUMMARY_SIZE} bytes")

        if tags:
            if len(tags) > self.MAX_TAGS:
                raise ValueError(f"Too many tags (max {self.MAX_TAGS})")
            for tag in tags:
                if len(tag) > self.MAX_TAG_LENGTH:
                    raise ValueError(f"Tag '{tag[:20]}...' exceeds max length of {self.MAX_TAG_LENGTH}")

        if importance < 1 or importance > 10:
            importance = max(1, min(10, importance))  # Clamp to valid range

        content_hash = self._content_hash(content)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Calculate tree_path and depth
            tree_path, depth = self._calculate_tree_position(cursor, parent_id)

            cursor.execute('''
                INSERT INTO memories (
                    content, summary, project_path, project_name, tags, category,
                    parent_id, tree_path, depth,
                    memory_type, importance, content_hash,
                    last_accessed, access_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content,
                summary,
                project_path,
                project_name,
                json.dumps(tags) if tags else None,
                category,
                parent_id,
                tree_path,
                depth,
                memory_type,
                importance,
                content_hash,
                datetime.now().isoformat(),
                0
            ))
            memory_id = cursor.lastrowid

            # Update tree_path with actual memory_id
            if tree_path:
                tree_path = f"{tree_path}.{memory_id}"
            else:
                tree_path = str(memory_id)

            cursor.execute('UPDATE memories SET tree_path = ? WHERE id = ?', (tree_path, memory_id))

            conn.commit()

            # Rebuild vectors after adding
            self._rebuild_vectors()

            return memory_id

        except sqlite3.IntegrityError:
            # Duplicate content
            cursor.execute('SELECT id FROM memories WHERE content_hash = ?', (content_hash,))
            result = cursor.fetchone()
            return result[0] if result else -1
        finally:
            conn.close()

    def _calculate_tree_position(self, cursor: sqlite3.Cursor, parent_id: Optional[int]) -> Tuple[str, int]:
        """
        Calculate tree_path and depth for a new memory.

        Args:
            cursor: Database cursor
            parent_id: Parent memory ID (None for root level)

        Returns:
            Tuple of (tree_path, depth)
        """
        if parent_id is None:
            return ("", 0)

        cursor.execute('SELECT tree_path, depth FROM memories WHERE id = ?', (parent_id,))
        result = cursor.fetchone()

        if result:
            parent_path, parent_depth = result
            return (parent_path, parent_depth + 1)
        else:
            # Parent not found, treat as root
            return ("", 0)

    def search(
        self,
        query: str,
        limit: int = 5,
        project_path: Optional[str] = None,
        memory_type: Optional[str] = None,
        category: Optional[str] = None,
        cluster_id: Optional[int] = None,
        min_importance: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memories with enhanced V2 filtering.

        Args:
            query: Search query string
            limit: Maximum results to return
            project_path: Filter by project path
            memory_type: Filter by memory type
            category: Filter by category
            cluster_id: Filter by graph cluster
            min_importance: Minimum importance score

        Returns:
            List of memory dictionaries with scores
        """
        results = []

        # Method 1: TF-IDF semantic search
        if SKLEARN_AVAILABLE and self.vectorizer is not None and self.vectors is not None:
            try:
                query_vec = self.vectorizer.transform([query])
                similarities = cosine_similarity(query_vec, self.vectors).flatten()
                top_indices = np.argsort(similarities)[::-1][:limit * 2]

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                for idx in top_indices:
                    if idx < len(self.memory_ids):
                        memory_id = self.memory_ids[idx]
                        score = float(similarities[idx])

                        if score > 0.05:  # Minimum relevance threshold
                            cursor.execute('''
                                SELECT id, content, summary, project_path, project_name, tags,
                                       category, parent_id, tree_path, depth,
                                       memory_type, importance, created_at, cluster_id,
                                       last_accessed, access_count
                                FROM memories WHERE id = ?
                            ''', (memory_id,))
                            row = cursor.fetchone()

                            if row and self._apply_filters(row, project_path, memory_type,
                                                          category, cluster_id, min_importance):
                                results.append(self._row_to_dict(row, score, 'semantic'))

                conn.close()
            except Exception as e:
                print(f"Semantic search error: {e}")

        # Method 2: FTS fallback/supplement
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clean query for FTS
        import re
        fts_query = ' OR '.join(re.findall(r'\w+', query))

        if fts_query:
            cursor.execute('''
                SELECT m.id, m.content, m.summary, m.project_path, m.project_name,
                       m.tags, m.category, m.parent_id, m.tree_path, m.depth,
                       m.memory_type, m.importance, m.created_at, m.cluster_id,
                       m.last_accessed, m.access_count
                FROM memories m
                JOIN memories_fts fts ON m.id = fts.rowid
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            ''', (fts_query, limit))

            existing_ids = {r['id'] for r in results}

            for row in cursor.fetchall():
                if row[0] not in existing_ids:
                    if self._apply_filters(row, project_path, memory_type,
                                          category, cluster_id, min_importance):
                        results.append(self._row_to_dict(row, 0.5, 'keyword'))

        conn.close()

        # Update access tracking for returned results
        self._update_access_tracking([r['id'] for r in results])

        # Sort by score and limit
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]

    def _apply_filters(
        self,
        row: tuple,
        project_path: Optional[str],
        memory_type: Optional[str],
        category: Optional[str],
        cluster_id: Optional[int],
        min_importance: Optional[int]
    ) -> bool:
        """Apply filter criteria to a database row."""
        # Row indices: project_path=3, category=6, memory_type=10, importance=11, cluster_id=13
        if project_path and row[3] != project_path:
            return False
        if memory_type and row[10] != memory_type:
            return False
        if category and row[6] != category:
            return False
        if cluster_id is not None and row[13] != cluster_id:
            return False
        if min_importance is not None and (row[11] or 0) < min_importance:
            return False
        return True

    def _row_to_dict(self, row: tuple, score: float, match_type: str) -> Dict[str, Any]:
        """Convert database row to memory dictionary."""
        return {
            'id': row[0],
            'content': row[1],
            'summary': row[2],
            'project_path': row[3],
            'project_name': row[4],
            'tags': json.loads(row[5]) if row[5] else [],
            'category': row[6],
            'parent_id': row[7],
            'tree_path': row[8],
            'depth': row[9],
            'memory_type': row[10],
            'importance': row[11],
            'created_at': row[12],
            'cluster_id': row[13],
            'last_accessed': row[14],
            'access_count': row[15],
            'score': score,
            'match_type': match_type
        }

    def _update_access_tracking(self, memory_ids: List[int]):
        """Update last_accessed and access_count for retrieved memories."""
        if not memory_ids:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        for mem_id in memory_ids:
            cursor.execute('''
                UPDATE memories
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
            ''', (now, mem_id))

        conn.commit()
        conn.close()

    def get_tree(self, parent_id: Optional[int] = None, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        Get hierarchical tree structure of memories.

        Args:
            parent_id: Root parent ID (None for top-level)
            max_depth: Maximum depth to retrieve

        Returns:
            List of memories with tree structure
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if parent_id is None:
            # Get root level memories
            cursor.execute('''
                SELECT id, content, summary, project_path, project_name, tags,
                       category, parent_id, tree_path, depth, memory_type, importance,
                       created_at, cluster_id, last_accessed, access_count
                FROM memories
                WHERE parent_id IS NULL AND depth <= ?
                ORDER BY tree_path
            ''', (max_depth,))
        else:
            # Get subtree under specific parent
            cursor.execute('''
                SELECT tree_path FROM memories WHERE id = ?
            ''', (parent_id,))
            result = cursor.fetchone()

            if not result:
                conn.close()
                return []

            parent_path = result[0]
            cursor.execute('''
                SELECT id, content, summary, project_path, project_name, tags,
                       category, parent_id, tree_path, depth, memory_type, importance,
                       created_at, cluster_id, last_accessed, access_count
                FROM memories
                WHERE tree_path LIKE ? AND depth <= ?
                ORDER BY tree_path
            ''', (f"{parent_path}.%", max_depth))

        results = []
        for row in cursor.fetchall():
            results.append(self._row_to_dict(row, 1.0, 'tree'))

        conn.close()
        return results

    def update_tier(self, memory_id: int, new_tier: str, compressed_summary: Optional[str] = None):
        """
        Update memory tier for progressive summarization.

        Args:
            memory_id: Memory ID to update
            new_tier: New tier level ('hot', 'warm', 'cold', 'archived')
            compressed_summary: Optional compressed summary for higher tiers
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if compressed_summary:
            cursor.execute('''
                UPDATE memories
                SET memory_type = ?, summary = ?, updated_at = ?
                WHERE id = ?
            ''', (new_tier, compressed_summary, datetime.now().isoformat(), memory_id))
        else:
            cursor.execute('''
                UPDATE memories
                SET memory_type = ?, updated_at = ?
                WHERE id = ?
            ''', (new_tier, datetime.now().isoformat(), memory_id))

        conn.commit()
        conn.close()

    def get_by_cluster(self, cluster_id: int) -> List[Dict[str, Any]]:
        """
        Get all memories in a specific graph cluster.

        Args:
            cluster_id: Graph cluster ID

        Returns:
            List of memories in the cluster
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, content, summary, project_path, project_name, tags,
                   category, parent_id, tree_path, depth, memory_type, importance,
                   created_at, cluster_id, last_accessed, access_count
            FROM memories
            WHERE cluster_id = ?
            ORDER BY importance DESC, created_at DESC
        ''', (cluster_id,))

        results = []
        for row in cursor.fetchall():
            results.append(self._row_to_dict(row, 1.0, 'cluster'))

        conn.close()
        return results

    # ========== V1 Backward Compatible Methods ==========

    def _load_vectors(self):
        """Load vectors by rebuilding from database (V1 compatible)."""
        self._rebuild_vectors()

    def _rebuild_vectors(self):
        """Rebuild TF-IDF vectors from all memories (V1 compatible)."""
        if not SKLEARN_AVAILABLE:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, content, summary FROM memories')
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            self.vectorizer = None
            self.vectors = None
            self.memory_ids = []
            return

        self.memory_ids = [row[0] for row in rows]
        texts = [f"{row[1]} {row[2] or ''}" for row in rows]

        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.vectors = self.vectorizer.fit_transform(texts)

        # Save memory IDs as JSON (safe serialization)
        self.vectors_path.mkdir(exist_ok=True)
        with open(self.vectors_path / "memory_ids.json", 'w') as f:
            json.dump(self.memory_ids, f)

    def get_recent(self, limit: int = 10, project_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get most recent memories (V1 compatible)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if project_path:
            cursor.execute('''
                SELECT id, content, summary, project_path, project_name, tags,
                       category, parent_id, tree_path, depth, memory_type, importance,
                       created_at, cluster_id, last_accessed, access_count
                FROM memories
                WHERE project_path = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (project_path, limit))
        else:
            cursor.execute('''
                SELECT id, content, summary, project_path, project_name, tags,
                       category, parent_id, tree_path, depth, memory_type, importance,
                       created_at, cluster_id, last_accessed, access_count
                FROM memories
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))

        results = []
        for row in cursor.fetchall():
            results.append(self._row_to_dict(row, 1.0, 'recent'))

        conn.close()
        return results

    def get_by_id(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific memory by ID (V1 compatible)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, content, summary, project_path, project_name, tags,
                   category, parent_id, tree_path, depth, memory_type, importance,
                   created_at, cluster_id, last_accessed, access_count
            FROM memories WHERE id = ?
        ''', (memory_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Update access tracking
        self._update_access_tracking([memory_id])

        return self._row_to_dict(row, 1.0, 'direct')

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a specific memory (V1 compatible)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if deleted:
            self._rebuild_vectors()

        return deleted

    def list_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all memories with short previews (V1 compatible)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, content, summary, project_path, project_name, tags,
                   category, parent_id, tree_path, depth, memory_type, importance,
                   created_at, cluster_id, last_accessed, access_count
            FROM memories
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))

        results = []
        for row in cursor.fetchall():
            mem_dict = self._row_to_dict(row, 1.0, 'list')

            # Add title field for V1 compatibility
            content = row[1]
            first_line = content.split('\n')[0][:60]
            mem_dict['title'] = first_line + ('...' if len(content) > 60 else '')

            results.append(mem_dict)

        conn.close()
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics (V1 compatible with V2 extensions)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM memories')
        total_memories = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(DISTINCT project_path) FROM memories WHERE project_path IS NOT NULL')
        total_projects = cursor.fetchone()[0]

        cursor.execute('SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type')
        by_type = dict(cursor.fetchall())

        cursor.execute('SELECT category, COUNT(*) FROM memories WHERE category IS NOT NULL GROUP BY category')
        by_category = dict(cursor.fetchall())

        cursor.execute('SELECT MIN(created_at), MAX(created_at) FROM memories')
        date_range = cursor.fetchone()

        cursor.execute('SELECT COUNT(DISTINCT cluster_id) FROM memories WHERE cluster_id IS NOT NULL')
        total_clusters = cursor.fetchone()[0]

        cursor.execute('SELECT MAX(depth) FROM memories')
        max_depth = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'total_memories': total_memories,
            'total_projects': total_projects,
            'total_clusters': total_clusters,
            'max_tree_depth': max_depth,
            'by_type': by_type,
            'by_category': by_category,
            'date_range': {'earliest': date_range[0], 'latest': date_range[1]},
            'sklearn_available': SKLEARN_AVAILABLE
        }

    def export_for_context(self, query: str, max_tokens: int = 4000) -> str:
        """Export relevant memories formatted for Claude context injection (V1 compatible)."""
        memories = self.search(query, limit=10)

        if not memories:
            return "No relevant memories found."

        output = ["## Relevant Memory Context\n"]
        char_count = 0
        max_chars = max_tokens * 4  # Rough token to char conversion

        for mem in memories:
            entry = f"\n### Memory (Score: {mem['score']:.2f})\n"
            if mem.get('project_name'):
                entry += f"**Project:** {mem['project_name']}\n"
            if mem.get('category'):
                entry += f"**Category:** {mem['category']}\n"
            if mem.get('summary'):
                entry += f"**Summary:** {mem['summary']}\n"
            entry += f"**Content:**\n{mem['content'][:1000]}...\n" if len(mem['content']) > 1000 else f"**Content:**\n{mem['content']}\n"

            if char_count + len(entry) > max_chars:
                break

            output.append(entry)
            char_count += len(entry)

        return ''.join(output)


# CLI interface (V1 compatible + V2 extensions)
if __name__ == "__main__":
    import sys

    store = MemoryStoreV2()

    if len(sys.argv) < 2:
        print("MemoryStore V2 CLI")
        print("\nV1 Compatible Commands:")
        print("  python memory_store_v2.py add <content> [--project <path>] [--tags tag1,tag2]")
        print("  python memory_store_v2.py search <query>")
        print("  python memory_store_v2.py list [limit]")
        print("  python memory_store_v2.py get <id>")
        print("  python memory_store_v2.py recent [limit]")
        print("  python memory_store_v2.py stats")
        print("  python memory_store_v2.py context <query>")
        print("  python memory_store_v2.py delete <id>")
        print("\nV2 Extensions:")
        print("  python memory_store_v2.py tree [parent_id]")
        print("  python memory_store_v2.py cluster <cluster_id>")
        sys.exit(0)

    command = sys.argv[1]

    if command == "tree":
        parent_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
        results = store.get_tree(parent_id)

        if not results:
            print("No memories in tree.")
        else:
            for r in results:
                indent = "  " * r['depth']
                print(f"{indent}[{r['id']}] {r['content'][:50]}...")
                if r.get('category'):
                    print(f"{indent}    Category: {r['category']}")

    elif command == "cluster" and len(sys.argv) >= 3:
        cluster_id = int(sys.argv[2])
        results = store.get_by_cluster(cluster_id)

        if not results:
            print(f"No memories in cluster {cluster_id}.")
        else:
            print(f"Cluster {cluster_id} - {len(results)} memories:")
            for r in results:
                print(f"\n[{r['id']}] Importance: {r['importance']}")
                print(f"  {r['content'][:200]}...")

    elif command == "stats":
        stats = store.get_stats()
        print(json.dumps(stats, indent=2))

    elif command == "add":
        # Parse content and options
        if len(sys.argv) < 3:
            print("Error: Content required")
            print("Usage: python memory_store_v2.py add <content> [--project <path>] [--tags tag1,tag2]")
            sys.exit(1)

        content = sys.argv[2]
        project_path = None
        tags = []

        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == '--project' and i + 1 < len(sys.argv):
                project_path = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--tags' and i + 1 < len(sys.argv):
                tags = [t.strip() for t in sys.argv[i + 1].split(',')]
                i += 2
            else:
                i += 1

        mem_id = store.add_memory(content, project_path=project_path, tags=tags)
        print(f"Memory added with ID: {mem_id}")

    elif command == "search":
        if len(sys.argv) < 3:
            print("Error: Search query required")
            print("Usage: python memory_store_v2.py search <query>")
            sys.exit(1)

        query = sys.argv[2]
        results = store.search(query, limit=5)

        if not results:
            print("No results found.")
        else:
            for r in results:
                print(f"\n[{r['id']}] Score: {r['score']:.2f}")
                if r.get('project_name'):
                    print(f"Project: {r['project_name']}")
                if r.get('tags'):
                    print(f"Tags: {', '.join(r['tags'])}")
                print(f"Content: {r['content'][:200]}...")
                print(f"Created: {r['created_at']}")

    elif command == "recent":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        results = store.get_recent(limit)

        if not results:
            print("No memories found.")
        else:
            for r in results:
                print(f"\n[{r['id']}] {r['created_at']}")
                if r.get('project_name'):
                    print(f"Project: {r['project_name']}")
                if r.get('tags'):
                    print(f"Tags: {', '.join(r['tags'])}")
                print(f"Content: {r['content'][:200]}...")

    elif command == "list":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        results = store.get_recent(limit)

        if not results:
            print("No memories found.")
        else:
            for r in results:
                print(f"[{r['id']}] {r['content'][:100]}...")

    elif command == "get":
        if len(sys.argv) < 3:
            print("Error: Memory ID required")
            print("Usage: python memory_store_v2.py get <id>")
            sys.exit(1)

        mem_id = int(sys.argv[2])
        memory = store.get_memory(mem_id)

        if not memory:
            print(f"Memory {mem_id} not found.")
        else:
            print(f"\nID: {memory['id']}")
            print(f"Content: {memory['content']}")
            if memory.get('summary'):
                print(f"Summary: {memory['summary']}")
            if memory.get('project_name'):
                print(f"Project: {memory['project_name']}")
            if memory.get('tags'):
                print(f"Tags: {', '.join(memory['tags'])}")
            print(f"Created: {memory['created_at']}")
            print(f"Importance: {memory['importance']}")
            print(f"Access Count: {memory['access_count']}")

    elif command == "context":
        if len(sys.argv) < 3:
            print("Error: Query required")
            print("Usage: python memory_store_v2.py context <query>")
            sys.exit(1)

        query = sys.argv[2]
        context = store.export_for_context(query)
        print(context)

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: Memory ID required")
            print("Usage: python memory_store_v2.py delete <id>")
            sys.exit(1)

        mem_id = int(sys.argv[2])
        store.delete_memory(mem_id)
        print(f"Memory {mem_id} deleted.")

    else:
        print(f"Unknown command: {command}")
        print("Run without arguments to see available commands.")
