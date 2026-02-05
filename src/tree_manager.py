#!/usr/bin/env python3
"""
TreeManager - Hierarchical Memory Tree Management
Implements PageIndex-style materialized path navigation for fast subtree queries.

Key Features:
- Materialized path storage (e.g., "1.2.5" for fast subtree retrieval)
- No recursive CTEs needed (SQLite compatible)
- Build hierarchical index from flat memories
- Aggregated counts and metadata at each node
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

MEMORY_DIR = Path.home() / ".claude-memory"
DB_PATH = MEMORY_DIR / "memory.db"


class TreeManager:
    """
    Manages hierarchical tree structure for memory navigation.

    Tree Structure:
        Root
        ├── Project: NextJS-App
        │   ├── Category: Frontend
        │   │   ├── Memory: React Components
        │   │   └── Memory: State Management
        │   └── Category: Backend
        │       └── Memory: API Routes
        └── Project: Python-ML

    Materialized Path Format:
        - Root: "1"
        - Project: "1.2"
        - Category: "1.2.3"
        - Memory: "1.2.3.4"

    Benefits:
        - Fast subtree queries: WHERE tree_path LIKE '1.2.%'
        - O(1) depth calculation: count dots in path
        - O(1) parent lookup: parse path
        - No recursive CTEs needed
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize TreeManager.

        Args:
            db_path: Optional custom database path
        """
        self.db_path = db_path or DB_PATH
        self._init_db()
        self.root_id = self._ensure_root()

    def _init_db(self):
        """Initialize memory_tree table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_tree (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,

                parent_id INTEGER,
                tree_path TEXT NOT NULL,
                depth INTEGER DEFAULT 0,

                memory_count INTEGER DEFAULT 0,
                total_size INTEGER DEFAULT 0,
                last_updated TIMESTAMP,

                memory_id INTEGER,

                FOREIGN KEY (parent_id) REFERENCES memory_tree(id) ON DELETE CASCADE,
                FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tree_path_layer2 ON memory_tree(tree_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_node_type ON memory_tree(node_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parent_id_tree ON memory_tree(parent_id)')

        conn.commit()
        conn.close()

    def _ensure_root(self) -> int:
        """Ensure root node exists and return its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM memory_tree WHERE node_type = ? AND parent_id IS NULL', ('root',))
        result = cursor.fetchone()

        if result:
            root_id = result[0]
        else:
            cursor.execute('''
                INSERT INTO memory_tree (node_type, name, tree_path, depth, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', ('root', 'Root', '1', 0, datetime.now().isoformat()))
            root_id = cursor.lastrowid

            # Update tree_path with actual ID
            cursor.execute('UPDATE memory_tree SET tree_path = ? WHERE id = ?', (str(root_id), root_id))
            conn.commit()

        conn.close()
        return root_id

    def build_tree(self):
        """
        Build complete tree structure from memories table.

        Process:
        1. Clear existing tree (except root)
        2. Group memories by project
        3. Group by category within projects
        4. Link individual memories as leaf nodes
        5. Update aggregated counts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clear existing tree (keep root)
        cursor.execute('DELETE FROM memory_tree WHERE node_type != ?', ('root',))

        # Step 1: Create project nodes
        cursor.execute('''
            SELECT DISTINCT project_path, project_name
            FROM memories
            WHERE project_path IS NOT NULL
            ORDER BY project_path
        ''')
        projects = cursor.fetchall()

        project_map = {}  # project_path -> node_id

        for project_path, project_name in projects:
            name = project_name or project_path.split('/')[-1]
            node_id = self.add_node('project', name, self.root_id, description=project_path)
            project_map[project_path] = node_id

        # Step 2: Create category nodes within projects
        cursor.execute('''
            SELECT DISTINCT project_path, category
            FROM memories
            WHERE project_path IS NOT NULL AND category IS NOT NULL
            ORDER BY project_path, category
        ''')
        categories = cursor.fetchall()

        category_map = {}  # (project_path, category) -> node_id

        for project_path, category in categories:
            parent_id = project_map.get(project_path)
            if parent_id:
                node_id = self.add_node('category', category, parent_id)
                category_map[(project_path, category)] = node_id

        # Step 3: Link memories as leaf nodes
        cursor.execute('''
            SELECT id, content, summary, project_path, category, importance, created_at
            FROM memories
            ORDER BY created_at DESC
        ''')
        memories = cursor.fetchall()

        for mem_id, content, summary, project_path, category, importance, created_at in memories:
            # Determine parent node
            if project_path and category and (project_path, category) in category_map:
                parent_id = category_map[(project_path, category)]
            elif project_path and project_path in project_map:
                parent_id = project_map[project_path]
            else:
                parent_id = self.root_id

            # Create memory node
            name = summary or content[:60].replace('\n', ' ')
            self.add_node('memory', name, parent_id, memory_id=mem_id, description=content[:200])

        # Step 4: Update aggregated counts
        self._update_all_counts()

        conn.commit()
        conn.close()

    def add_node(
        self,
        node_type: str,
        name: str,
        parent_id: int,
        description: Optional[str] = None,
        memory_id: Optional[int] = None
    ) -> int:
        """
        Add a new node to the tree.

        Args:
            node_type: Type of node ('root', 'project', 'category', 'memory')
            name: Display name
            parent_id: Parent node ID
            description: Optional description
            memory_id: Link to memories table (for leaf nodes)

        Returns:
            New node ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get parent path and depth
        cursor.execute('SELECT tree_path, depth FROM memory_tree WHERE id = ?', (parent_id,))
        result = cursor.fetchone()

        if not result:
            raise ValueError(f"Parent node {parent_id} not found")

        parent_path, parent_depth = result

        # Calculate new node position
        depth = parent_depth + 1

        cursor.execute('''
            INSERT INTO memory_tree (
                node_type, name, description,
                parent_id, tree_path, depth,
                memory_id, last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            node_type,
            name,
            description,
            parent_id,
            '',  # Placeholder, updated below
            depth,
            memory_id,
            datetime.now().isoformat()
        ))

        node_id = cursor.lastrowid

        # Update tree_path with actual node_id
        tree_path = f"{parent_path}.{node_id}"
        cursor.execute('UPDATE memory_tree SET tree_path = ? WHERE id = ?', (tree_path, node_id))

        conn.commit()
        conn.close()

        return node_id

    def get_tree(
        self,
        project_name: Optional[str] = None,
        max_depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get tree structure as nested dictionary.

        Args:
            project_name: Filter by specific project
            max_depth: Maximum depth to retrieve

        Returns:
            Nested dictionary representing tree structure
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query
        if project_name:
            # Find project node
            cursor.execute('''
                SELECT id, tree_path FROM memory_tree
                WHERE node_type = 'project' AND name = ?
            ''', (project_name,))
            result = cursor.fetchone()

            if not result:
                conn.close()
                return {'error': f"Project '{project_name}' not found"}

            project_id, project_path = result

            # Get subtree
            if max_depth is not None:
                cursor.execute('''
                    SELECT id, node_type, name, description, parent_id, tree_path,
                           depth, memory_count, total_size, last_updated, memory_id
                    FROM memory_tree
                    WHERE (id = ? OR tree_path LIKE ?) AND depth <= ?
                    ORDER BY tree_path
                ''', (project_id, f"{project_path}.%", max_depth))
            else:
                cursor.execute('''
                    SELECT id, node_type, name, description, parent_id, tree_path,
                           depth, memory_count, total_size, last_updated, memory_id
                    FROM memory_tree
                    WHERE id = ? OR tree_path LIKE ?
                    ORDER BY tree_path
                ''', (project_id, f"{project_path}.%"))
        else:
            # Get entire tree
            if max_depth is not None:
                cursor.execute('''
                    SELECT id, node_type, name, description, parent_id, tree_path,
                           depth, memory_count, total_size, last_updated, memory_id
                    FROM memory_tree
                    WHERE depth <= ?
                    ORDER BY tree_path
                ''', (max_depth,))
            else:
                cursor.execute('''
                    SELECT id, node_type, name, description, parent_id, tree_path,
                           depth, memory_count, total_size, last_updated, memory_id
                    FROM memory_tree
                    ORDER BY tree_path
                ''')

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {'error': 'No tree nodes found'}

        # Build nested structure
        nodes = {}
        root = None

        for row in rows:
            node = {
                'id': row[0],
                'type': row[1],
                'name': row[2],
                'description': row[3],
                'parent_id': row[4],
                'tree_path': row[5],
                'depth': row[6],
                'memory_count': row[7],
                'total_size': row[8],
                'last_updated': row[9],
                'memory_id': row[10],
                'children': []
            }
            nodes[node['id']] = node

            if node['parent_id'] is None or (project_name and node['type'] == 'project'):
                root = node
            elif node['parent_id'] in nodes:
                nodes[node['parent_id']]['children'].append(node)

        return root or {'error': 'Root node not found'}

    def get_subtree(self, node_id: int) -> List[Dict[str, Any]]:
        """
        Get all descendants of a specific node (flat list).

        Args:
            node_id: Node ID to get subtree for

        Returns:
            List of descendant nodes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get node's tree_path
        cursor.execute('SELECT tree_path FROM memory_tree WHERE id = ?', (node_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return []

        tree_path = result[0]

        # Get all descendants
        cursor.execute('''
            SELECT id, node_type, name, description, parent_id, tree_path,
                   depth, memory_count, total_size, last_updated, memory_id
            FROM memory_tree
            WHERE tree_path LIKE ?
            ORDER BY tree_path
        ''', (f"{tree_path}.%",))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'type': row[1],
                'name': row[2],
                'description': row[3],
                'parent_id': row[4],
                'tree_path': row[5],
                'depth': row[6],
                'memory_count': row[7],
                'total_size': row[8],
                'last_updated': row[9],
                'memory_id': row[10]
            })

        conn.close()
        return results

    def get_path_to_root(self, node_id: int) -> List[Dict[str, Any]]:
        """
        Get path from node to root (breadcrumb trail).

        Args:
            node_id: Starting node ID

        Returns:
            List of nodes from root to target node
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get node's tree_path
        cursor.execute('SELECT tree_path FROM memory_tree WHERE id = ?', (node_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return []

        tree_path = result[0]

        # Parse path to get all ancestor IDs
        path_ids = [int(x) for x in tree_path.split('.')]

        # Get all ancestor nodes
        placeholders = ','.join('?' * len(path_ids))
        cursor.execute(f'''
            SELECT id, node_type, name, description, parent_id, tree_path,
                   depth, memory_count, total_size, last_updated, memory_id
            FROM memory_tree
            WHERE id IN ({placeholders})
            ORDER BY depth
        ''', path_ids)

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'type': row[1],
                'name': row[2],
                'description': row[3],
                'parent_id': row[4],
                'tree_path': row[5],
                'depth': row[6],
                'memory_count': row[7],
                'total_size': row[8],
                'last_updated': row[9],
                'memory_id': row[10]
            })

        conn.close()
        return results

    def update_counts(self, node_id: int):
        """
        Update aggregated counts for a node (memory_count, total_size).
        Recursively updates all ancestors.

        Args:
            node_id: Node ID to update
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all descendant memory nodes
        cursor.execute('SELECT tree_path FROM memory_tree WHERE id = ?', (node_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return

        tree_path = result[0]

        # Count memories in subtree
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(LENGTH(m.content)), 0)
            FROM memory_tree t
            LEFT JOIN memories m ON t.memory_id = m.id
            WHERE t.tree_path LIKE ? AND t.memory_id IS NOT NULL
        ''', (f"{tree_path}%",))

        memory_count, total_size = cursor.fetchone()

        # Update node
        cursor.execute('''
            UPDATE memory_tree
            SET memory_count = ?, total_size = ?, last_updated = ?
            WHERE id = ?
        ''', (memory_count, total_size, datetime.now().isoformat(), node_id))

        # Update all ancestors
        path_ids = [int(x) for x in tree_path.split('.')]
        for ancestor_id in path_ids[:-1]:  # Exclude current node
            self.update_counts(ancestor_id)

        conn.commit()
        conn.close()

    def _update_all_counts(self):
        """Update counts for all nodes (used after build_tree)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all nodes in reverse depth order (leaves first)
        cursor.execute('''
            SELECT id FROM memory_tree
            ORDER BY depth DESC
        ''')

        node_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Update each node (will cascade to parents)
        processed = set()
        for node_id in node_ids:
            if node_id not in processed:
                self.update_counts(node_id)
                processed.add(node_id)

    def _generate_tree_path(self, parent_path: str, node_id: int) -> str:
        """Generate tree_path for a new node."""
        if parent_path:
            return f"{parent_path}.{node_id}"
        return str(node_id)

    def _calculate_depth(self, tree_path: str) -> int:
        """Calculate depth from tree_path (count dots)."""
        return tree_path.count('.')

    def delete_node(self, node_id: int) -> bool:
        """
        Delete a node and all its descendants.

        Args:
            node_id: Node ID to delete

        Returns:
            True if deleted, False if not found
        """
        if node_id == self.root_id:
            raise ValueError("Cannot delete root node")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get tree_path
        cursor.execute('SELECT tree_path, parent_id FROM memory_tree WHERE id = ?', (node_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False

        tree_path, parent_id = result

        # Delete node and all descendants (CASCADE handles children)
        cursor.execute('DELETE FROM memory_tree WHERE id = ? OR tree_path LIKE ?',
                      (node_id, f"{tree_path}.%"))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        # Update parent counts
        if deleted and parent_id:
            self.update_counts(parent_id)

        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get tree statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM memory_tree')
        total_nodes = cursor.fetchone()[0]

        cursor.execute('SELECT node_type, COUNT(*) FROM memory_tree GROUP BY node_type')
        by_type = dict(cursor.fetchall())

        cursor.execute('SELECT MAX(depth) FROM memory_tree')
        max_depth = cursor.fetchone()[0] or 0

        cursor.execute('''
            SELECT SUM(memory_count), SUM(total_size)
            FROM memory_tree
            WHERE node_type = 'root'
        ''')
        total_memories, total_size = cursor.fetchone()

        conn.close()

        return {
            'total_nodes': total_nodes,
            'by_type': by_type,
            'max_depth': max_depth,
            'total_memories': total_memories or 0,
            'total_size_bytes': total_size or 0
        }


# CLI interface
if __name__ == "__main__":
    import sys
    import json

    tree_mgr = TreeManager()

    if len(sys.argv) < 2:
        print("TreeManager CLI")
        print("\nCommands:")
        print("  python tree_manager.py build                  # Build tree from memories")
        print("  python tree_manager.py show [project] [depth] # Show tree structure")
        print("  python tree_manager.py subtree <node_id>      # Get subtree")
        print("  python tree_manager.py path <node_id>         # Get path to root")
        print("  python tree_manager.py stats                  # Show statistics")
        print("  python tree_manager.py add <type> <name> <parent_id>  # Add node")
        print("  python tree_manager.py delete <node_id>       # Delete node")
        sys.exit(0)

    command = sys.argv[1]

    if command == "build":
        print("Building tree from memories...")
        tree_mgr.build_tree()
        stats = tree_mgr.get_stats()
        print(f"Tree built: {stats['total_nodes']} nodes, {stats['total_memories']} memories")

    elif command == "show":
        project = sys.argv[2] if len(sys.argv) > 2 else None
        max_depth = int(sys.argv[3]) if len(sys.argv) > 3 else None

        tree = tree_mgr.get_tree(project, max_depth)

        def print_tree(node, indent=0):
            if 'error' in node:
                print(node['error'])
                return

            prefix = "  " * indent
            icon = {"root": "🌳", "project": "📁", "category": "📂", "memory": "📄"}.get(node['type'], "•")

            print(f"{prefix}{icon} {node['name']} (id={node['id']}, memories={node['memory_count']})")

            for child in node.get('children', []):
                print_tree(child, indent + 1)

        print_tree(tree)

    elif command == "subtree" and len(sys.argv) >= 3:
        node_id = int(sys.argv[2])
        nodes = tree_mgr.get_subtree(node_id)

        if not nodes:
            print(f"No subtree found for node {node_id}")
        else:
            print(f"Subtree of node {node_id}:")
            for node in nodes:
                indent = "  " * (node['depth'] - nodes[0]['depth'] + 1)
                print(f"{indent}- {node['name']} (id={node['id']})")

    elif command == "path" and len(sys.argv) >= 3:
        node_id = int(sys.argv[2])
        path = tree_mgr.get_path_to_root(node_id)

        if not path:
            print(f"Node {node_id} not found")
        else:
            print("Path to root:")
            print(" > ".join([f"{n['name']} (id={n['id']})" for n in path]))

    elif command == "stats":
        stats = tree_mgr.get_stats()
        print(json.dumps(stats, indent=2))

    elif command == "add" and len(sys.argv) >= 5:
        node_type = sys.argv[2]
        name = sys.argv[3]
        parent_id = int(sys.argv[4])

        node_id = tree_mgr.add_node(node_type, name, parent_id)
        print(f"Node created with ID: {node_id}")

    elif command == "delete" and len(sys.argv) >= 3:
        node_id = int(sys.argv[2])
        if tree_mgr.delete_node(node_id):
            print(f"Node {node_id} deleted")
        else:
            print(f"Node {node_id} not found")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
