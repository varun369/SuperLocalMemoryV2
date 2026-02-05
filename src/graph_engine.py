#!/usr/bin/env python3
"""
GraphEngine - Knowledge Graph Clustering for SuperLocalMemory

Implements GraphRAG with Leiden community detection to:
- Extract entities from memories (TF-IDF keyword extraction)
- Build similarity-based edges between memories
- Detect thematic clusters using Leiden algorithm
- Enable graph traversal for related memory discovery

All processing is local - no external APIs.
"""

import sqlite3
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from collections import Counter

# Core dependencies
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    raise ImportError("scikit-learn is required. Install: pip install scikit-learn")

# Graph dependencies - lazy import to avoid conflicts with compression module
IGRAPH_AVAILABLE = False
try:
    # Import only when needed to avoid module conflicts
    import importlib
    ig_module = importlib.import_module('igraph')
    leiden_module = importlib.import_module('leidenalg')
    IGRAPH_AVAILABLE = True
except ImportError:
    pass  # Will raise error when building clusters if not available

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MEMORY_DIR = Path.home() / ".claude-memory"
DB_PATH = MEMORY_DIR / "memory.db"


class EntityExtractor:
    """Extract key entities/concepts from memory content using TF-IDF."""

    def __init__(self, max_features: int = 20, min_df: int = 1):
        """
        Initialize entity extractor.

        Args:
            max_features: Top N keywords to extract per memory
            min_df: Minimum document frequency (ignore very rare terms)
        """
        self.max_features = max_features
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words='english',
            ngram_range=(1, 2),  # Unigrams + bigrams
            min_df=min_df,
            lowercase=True,
            token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z0-9_-]*\b'  # Alphanumeric tokens
        )

    def extract_entities(self, contents: List[str]) -> Tuple[List[List[str]], np.ndarray]:
        """
        Extract entities from multiple contents.

        Args:
            contents: List of memory content strings

        Returns:
            Tuple of (entities_per_content, tfidf_vectors)
        """
        if not contents:
            return [], np.array([])

        try:
            # Fit and transform all contents
            vectors = self.vectorizer.fit_transform(contents)
            feature_names = self.vectorizer.get_feature_names_out()

            # Extract top entities for each content
            all_entities = []
            for idx in range(len(contents)):
                scores = vectors[idx].toarray()[0]

                # Get indices of top features
                top_indices = np.argsort(scores)[::-1]

                # Extract entities with score > 0
                entities = [
                    feature_names[i]
                    for i in top_indices
                    if scores[i] > 0.05  # Minimum threshold
                ][:self.max_features]

                all_entities.append(entities)

            return all_entities, vectors.toarray()

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return [[] for _ in contents], np.zeros((len(contents), 1))


class EdgeBuilder:
    """Build similarity edges between memories based on entity overlap."""

    def __init__(self, db_path: Path, min_similarity: float = 0.3):
        """
        Initialize edge builder.

        Args:
            db_path: Path to SQLite database
            min_similarity: Minimum cosine similarity to create edge
        """
        self.db_path = db_path
        self.min_similarity = min_similarity

    def build_edges(self, memory_ids: List[int], vectors: np.ndarray,
                   entities_list: List[List[str]]) -> int:
        """
        Build edges between similar memories.

        Args:
            memory_ids: List of memory IDs
            vectors: TF-IDF vectors (n x features)
            entities_list: List of entity lists per memory

        Returns:
            Number of edges created
        """
        if len(memory_ids) < 2:
            logger.warning("Need at least 2 memories to build edges")
            return 0

        # Compute pairwise cosine similarity
        similarity_matrix = cosine_similarity(vectors)

        edges_added = 0
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            for i in range(len(memory_ids)):
                for j in range(i + 1, len(memory_ids)):
                    sim = similarity_matrix[i, j]

                    if sim >= self.min_similarity:
                        # Find shared entities
                        entities_i = set(entities_list[i])
                        entities_j = set(entities_list[j])
                        shared = list(entities_i & entities_j)

                        # Classify relationship type
                        rel_type = self._classify_relationship(sim, shared)

                        # Insert edge (or update if exists)
                        cursor.execute('''
                            INSERT OR REPLACE INTO graph_edges
                            (source_memory_id, target_memory_id, relationship_type,
                             weight, shared_entities, similarity_score)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            memory_ids[i],
                            memory_ids[j],
                            rel_type,
                            float(sim),
                            json.dumps(shared),
                            float(sim)
                        ))

                        edges_added += 1

            conn.commit()
            logger.info(f"Created {edges_added} edges")
            return edges_added

        except Exception as e:
            logger.error(f"Edge building failed: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def _classify_relationship(self, similarity: float, shared_entities: List[str]) -> str:
        """
        Classify edge type based on similarity and shared entities.

        Args:
            similarity: Cosine similarity score
            shared_entities: List of shared entity strings

        Returns:
            Relationship type: 'similar', 'depends_on', or 'related_to'
        """
        # Check for dependency keywords
        dependency_keywords = {'dependency', 'require', 'import', 'use', 'need'}
        has_dependency = any(
            any(kw in entity.lower() for kw in dependency_keywords)
            for entity in shared_entities
        )

        if similarity > 0.7:
            return 'similar'
        elif has_dependency:
            return 'depends_on'
        else:
            return 'related_to'


class ClusterBuilder:
    """Detect memory communities using Leiden algorithm."""

    def __init__(self, db_path: Path):
        """Initialize cluster builder."""
        self.db_path = db_path

    def detect_communities(self) -> int:
        """
        Run Leiden algorithm to find memory clusters.

        Returns:
            Number of clusters created
        """
        # Import igraph modules here to avoid conflicts
        try:
            import igraph as ig
            import leidenalg
        except ImportError:
            raise ImportError("python-igraph and leidenalg required. Install: pip install python-igraph leidenalg")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Load all edges
            edges = cursor.execute('''
                SELECT source_memory_id, target_memory_id, weight
                FROM graph_edges
            ''').fetchall()

            if not edges:
                logger.warning("No edges found - cannot build clusters")
                return 0

            # Build memory ID mapping
            memory_ids = set()
            for source, target, _ in edges:
                memory_ids.add(source)
                memory_ids.add(target)

            memory_ids = sorted(list(memory_ids))
            memory_id_to_vertex = {mid: idx for idx, mid in enumerate(memory_ids)}
            vertex_to_memory_id = {idx: mid for mid, idx in memory_id_to_vertex.items()}

            # Create igraph graph
            g = ig.Graph()
            g.add_vertices(len(memory_ids))

            # Add edges with weights
            edge_list = []
            edge_weights = []

            for source, target, weight in edges:
                edge_list.append((
                    memory_id_to_vertex[source],
                    memory_id_to_vertex[target]
                ))
                edge_weights.append(weight)

            g.add_edges(edge_list)

            # Run Leiden algorithm
            logger.info(f"Running Leiden on {len(memory_ids)} nodes, {len(edges)} edges")
            partition = leidenalg.find_partition(
                g,
                leidenalg.ModularityVertexPartition,
                weights=edge_weights,
                n_iterations=100,
                seed=42  # Reproducible
            )

            # Process communities
            clusters_created = 0

            for cluster_idx, community in enumerate(partition):
                if len(community) < 2:  # Skip singleton clusters
                    continue

                # Get memory IDs in this cluster
                cluster_memory_ids = [vertex_to_memory_id[v] for v in community]

                # Calculate cluster stats
                avg_importance = self._get_avg_importance(cursor, cluster_memory_ids)

                # Auto-generate cluster name
                cluster_name = self._generate_cluster_name(cursor, cluster_memory_ids)

                # Insert cluster
                result = cursor.execute('''
                    INSERT INTO graph_clusters (name, member_count, avg_importance)
                    VALUES (?, ?, ?)
                ''', (cluster_name, len(cluster_memory_ids), avg_importance))

                cluster_id = result.lastrowid

                # Update memories with cluster_id
                cursor.executemany('''
                    UPDATE memories SET cluster_id = ? WHERE id = ?
                ''', [(cluster_id, mid) for mid in cluster_memory_ids])

                clusters_created += 1
                logger.info(f"Cluster {cluster_id}: '{cluster_name}' ({len(cluster_memory_ids)} members)")

            conn.commit()
            logger.info(f"Created {clusters_created} clusters")
            return clusters_created

        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

    def _get_avg_importance(self, cursor, memory_ids: List[int]) -> float:
        """Calculate average importance for cluster."""
        placeholders = ','.join('?' * len(memory_ids))
        result = cursor.execute(f'''
            SELECT AVG(importance) FROM memories WHERE id IN ({placeholders})
        ''', memory_ids).fetchone()

        return result[0] if result and result[0] else 5.0

    def _generate_cluster_name(self, cursor, memory_ids: List[int]) -> str:
        """Generate cluster name from member entities (TF-IDF approach)."""
        # Get all entities from cluster members
        placeholders = ','.join('?' * len(memory_ids))
        nodes = cursor.execute(f'''
            SELECT entities FROM graph_nodes WHERE memory_id IN ({placeholders})
        ''', memory_ids).fetchall()

        all_entities = []
        for node in nodes:
            if node[0]:
                all_entities.extend(json.loads(node[0]))

        if not all_entities:
            return f"Cluster (ID auto-assigned)"

        # Count entity frequencies
        entity_counts = Counter(all_entities)

        # Top 2-3 most common entities
        top_entities = [e for e, _ in entity_counts.most_common(3)]

        # Build name
        if len(top_entities) >= 2:
            name = f"{top_entities[0].title()} & {top_entities[1].title()}"
        elif len(top_entities) == 1:
            name = f"{top_entities[0].title()} Contexts"
        else:
            name = "Mixed Contexts"

        return name[:100]  # Limit length


class ClusterNamer:
    """Enhanced cluster naming with optional LLM support (future)."""

    @staticmethod
    def generate_name_tfidf(entities: List[str]) -> str:
        """Generate name from entity list (TF-IDF fallback)."""
        if not entities:
            return "Unnamed Cluster"

        entity_counts = Counter(entities)
        top_entities = [e for e, _ in entity_counts.most_common(2)]

        if len(top_entities) >= 2:
            return f"{top_entities[0].title()} & {top_entities[1].title()}"
        else:
            return f"{top_entities[0].title()} Contexts"


class GraphEngine:
    """Main graph engine coordinating all graph operations."""

    def __init__(self, db_path: Path = DB_PATH):
        """Initialize graph engine."""
        self.db_path = db_path
        self.entity_extractor = EntityExtractor(max_features=20)
        self.edge_builder = EdgeBuilder(db_path)
        self.cluster_builder = ClusterBuilder(db_path)
        self._ensure_graph_tables()

    def _ensure_graph_tables(self):
        """Create graph tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Graph nodes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER UNIQUE NOT NULL,
                entities TEXT,
                embedding_vector TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        ''')

        # Graph edges table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_memory_id INTEGER NOT NULL,
                target_memory_id INTEGER NOT NULL,
                relationship_type TEXT,
                weight REAL DEFAULT 1.0,
                shared_entities TEXT,
                similarity_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
                FOREIGN KEY (target_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
                UNIQUE(source_memory_id, target_memory_id)
            )
        ''')

        # Graph clusters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS graph_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                member_count INTEGER DEFAULT 0,
                avg_importance REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add cluster_id to memories if not exists
        try:
            cursor.execute('ALTER TABLE memories ADD COLUMN cluster_id INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_graph_source ON graph_edges(source_memory_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_graph_target ON graph_edges(target_memory_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cluster_members ON memories(cluster_id)')

        conn.commit()
        conn.close()
        logger.info("Graph tables initialized")

    def build_graph(self, min_similarity: float = 0.3) -> Dict[str, any]:
        """
        Build complete knowledge graph from all memories.

        Args:
            min_similarity: Minimum cosine similarity for edge creation

        Returns:
            Dictionary with build statistics
        """
        start_time = time.time()
        logger.info("Starting full graph build...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Clear existing graph data
            cursor.execute('DELETE FROM graph_edges')
            cursor.execute('DELETE FROM graph_nodes')
            cursor.execute('DELETE FROM graph_clusters')
            cursor.execute('UPDATE memories SET cluster_id = NULL')
            conn.commit()

            # Load all memories
            memories = cursor.execute('''
                SELECT id, content, summary FROM memories
                ORDER BY id
            ''').fetchall()

            if len(memories) < 2:
                logger.warning("Need at least 2 memories to build graph")
                return {
                    'success': False,
                    'message': 'Need at least 2 memories',
                    'memories': len(memories)
                }

            logger.info(f"Processing {len(memories)} memories")

            # Extract entities and vectors
            memory_ids = [m[0] for m in memories]
            contents = [f"{m[1]} {m[2] or ''}" for m in memories]  # Combine content + summary

            entities_list, vectors = self.entity_extractor.extract_entities(contents)

            # Store nodes
            for memory_id, entities, vector in zip(memory_ids, entities_list, vectors):
                cursor.execute('''
                    INSERT INTO graph_nodes (memory_id, entities, embedding_vector)
                    VALUES (?, ?, ?)
                ''', (
                    memory_id,
                    json.dumps(entities),
                    json.dumps(vector.tolist())
                ))

            conn.commit()
            logger.info(f"Stored {len(memory_ids)} graph nodes")

            # Build edges
            edges_count = self.edge_builder.build_edges(
                memory_ids, vectors, entities_list
            )

            # Detect communities
            clusters_count = self.cluster_builder.detect_communities()

            elapsed = time.time() - start_time

            stats = {
                'success': True,
                'memories': len(memories),
                'nodes': len(memory_ids),
                'edges': edges_count,
                'clusters': clusters_count,
                'time_seconds': round(elapsed, 2)
            }

            logger.info(f"Graph build complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Graph build failed: {e}")
            conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()

    def extract_entities(self, memory_id: int) -> List[str]:
        """
        Extract entities for a single memory.

        Args:
            memory_id: Memory ID

        Returns:
            List of entity strings
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get memory content
            memory = cursor.execute('''
                SELECT content, summary FROM memories WHERE id = ?
            ''', (memory_id,)).fetchone()

            if not memory:
                return []

            content = f"{memory[0]} {memory[1] or ''}"
            entities_list, _ = self.entity_extractor.extract_entities([content])

            return entities_list[0] if entities_list else []

        finally:
            conn.close()

    def get_related(self, memory_id: int, max_hops: int = 2) -> List[Dict]:
        """
        Get memories connected to this memory via graph edges.

        Args:
            memory_id: Source memory ID
            max_hops: Maximum traversal depth (1 or 2)

        Returns:
            List of related memory dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get 1-hop neighbors
            edges = cursor.execute('''
                SELECT target_memory_id, relationship_type, weight, shared_entities
                FROM graph_edges
                WHERE source_memory_id = ?
                UNION
                SELECT source_memory_id, relationship_type, weight, shared_entities
                FROM graph_edges
                WHERE target_memory_id = ?
            ''', (memory_id, memory_id)).fetchall()

            results = []
            seen_ids = {memory_id}

            for target_id, rel_type, weight, shared_entities in edges:
                if target_id in seen_ids:
                    continue

                seen_ids.add(target_id)

                # Get memory details
                memory = cursor.execute('''
                    SELECT id, summary, importance, tags
                    FROM memories WHERE id = ?
                ''', (target_id,)).fetchone()

                if memory:
                    results.append({
                        'id': memory[0],
                        'summary': memory[1],
                        'importance': memory[2],
                        'tags': json.loads(memory[3]) if memory[3] else [],
                        'relationship': rel_type,
                        'weight': weight,
                        'shared_entities': json.loads(shared_entities) if shared_entities else [],
                        'hops': 1
                    })

            # If max_hops == 2, get 2-hop neighbors
            if max_hops >= 2:
                for result in results[:]:  # Copy to avoid modification during iteration
                    second_hop = cursor.execute('''
                        SELECT target_memory_id, relationship_type, weight
                        FROM graph_edges
                        WHERE source_memory_id = ?
                        UNION
                        SELECT source_memory_id, relationship_type, weight
                        FROM graph_edges
                        WHERE target_memory_id = ?
                    ''', (result['id'], result['id'])).fetchall()

                    for target_id, rel_type, weight in second_hop:
                        if target_id in seen_ids:
                            continue

                        seen_ids.add(target_id)

                        memory = cursor.execute('''
                            SELECT id, summary, importance, tags
                            FROM memories WHERE id = ?
                        ''', (target_id,)).fetchone()

                        if memory:
                            results.append({
                                'id': memory[0],
                                'summary': memory[1],
                                'importance': memory[2],
                                'tags': json.loads(memory[3]) if memory[3] else [],
                                'relationship': rel_type,
                                'weight': weight,
                                'shared_entities': [],
                                'hops': 2
                            })

            # Sort by weight (strongest connections first)
            results.sort(key=lambda x: (-x['hops'], -x['weight']))

            return results

        finally:
            conn.close()

    def get_cluster_members(self, cluster_id: int) -> List[Dict]:
        """
        Get all memories in a cluster.

        Args:
            cluster_id: Cluster ID

        Returns:
            List of memory dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            memories = cursor.execute('''
                SELECT id, summary, importance, tags, created_at
                FROM memories
                WHERE cluster_id = ?
                ORDER BY importance DESC
            ''', (cluster_id,)).fetchall()

            return [
                {
                    'id': m[0],
                    'summary': m[1],
                    'importance': m[2],
                    'tags': json.loads(m[3]) if m[3] else [],
                    'created_at': m[4]
                }
                for m in memories
            ]

        finally:
            conn.close()

    def add_memory_incremental(self, memory_id: int) -> bool:
        """
        Add single memory to existing graph (incremental update).

        Args:
            memory_id: New memory ID to add

        Returns:
            Success status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get new memory content
            memory = cursor.execute('''
                SELECT content, summary FROM memories WHERE id = ?
            ''', (memory_id,)).fetchone()

            if not memory:
                return False

            # Extract entities for new memory
            content = f"{memory[0]} {memory[1] or ''}"
            entities_list, vector = self.entity_extractor.extract_entities([content])

            if not entities_list:
                return False

            new_entities = entities_list[0]
            new_vector = vector[0]

            # Store node
            cursor.execute('''
                INSERT OR REPLACE INTO graph_nodes (memory_id, entities, embedding_vector)
                VALUES (?, ?, ?)
            ''', (memory_id, json.dumps(new_entities), json.dumps(new_vector.tolist())))

            # Compare to existing memories
            existing = cursor.execute('''
                SELECT memory_id, embedding_vector, entities
                FROM graph_nodes
                WHERE memory_id != ?
            ''', (memory_id,)).fetchall()

            edges_added = 0

            for existing_id, existing_vector_json, existing_entities_json in existing:
                existing_vector = np.array(json.loads(existing_vector_json))

                # Compute similarity
                sim = cosine_similarity([new_vector], [existing_vector])[0][0]

                if sim >= self.edge_builder.min_similarity:
                    # Find shared entities
                    existing_entities = json.loads(existing_entities_json)
                    shared = list(set(new_entities) & set(existing_entities))

                    # Classify relationship
                    rel_type = self.edge_builder._classify_relationship(sim, shared)

                    # Insert edge
                    cursor.execute('''
                        INSERT OR REPLACE INTO graph_edges
                        (source_memory_id, target_memory_id, relationship_type,
                         weight, shared_entities, similarity_score)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        memory_id,
                        existing_id,
                        rel_type,
                        float(sim),
                        json.dumps(shared),
                        float(sim)
                    ))

                    edges_added += 1

            conn.commit()
            logger.info(f"Added memory {memory_id} to graph with {edges_added} edges")

            # Optionally re-cluster if significant change
            if edges_added > 5:
                logger.info("Significant graph change - consider re-clustering")

            return True

        except Exception as e:
            logger.error(f"Incremental add failed: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, any]:
        """Get graph statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            nodes = cursor.execute('SELECT COUNT(*) FROM graph_nodes').fetchone()[0]
            edges = cursor.execute('SELECT COUNT(*) FROM graph_edges').fetchone()[0]
            clusters = cursor.execute('SELECT COUNT(*) FROM graph_clusters').fetchone()[0]

            # Cluster breakdown
            cluster_info = cursor.execute('''
                SELECT name, member_count, avg_importance
                FROM graph_clusters
                ORDER BY member_count DESC
                LIMIT 10
            ''').fetchall()

            return {
                'nodes': nodes,
                'edges': edges,
                'clusters': clusters,
                'top_clusters': [
                    {
                        'name': c[0],
                        'members': c[1],
                        'avg_importance': round(c[2], 1)
                    }
                    for c in cluster_info
                ]
            }

        finally:
            conn.close()


def main():
    """CLI interface for manual graph operations."""
    import argparse

    parser = argparse.ArgumentParser(description='GraphEngine - Knowledge Graph Management')
    parser.add_argument('command', choices=['build', 'stats', 'related', 'cluster'],
                       help='Command to execute')
    parser.add_argument('--memory-id', type=int, help='Memory ID for related/add commands')
    parser.add_argument('--cluster-id', type=int, help='Cluster ID for cluster command')
    parser.add_argument('--min-similarity', type=float, default=0.3,
                       help='Minimum similarity for edges (default: 0.3)')
    parser.add_argument('--hops', type=int, default=2, help='Max hops for related (default: 2)')

    args = parser.parse_args()

    engine = GraphEngine()

    if args.command == 'build':
        print("Building knowledge graph...")
        stats = engine.build_graph(min_similarity=args.min_similarity)
        print(json.dumps(stats, indent=2))

    elif args.command == 'stats':
        print("Graph Statistics:")
        stats = engine.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.command == 'related':
        if not args.memory_id:
            print("Error: --memory-id required for 'related' command")
            return

        print(f"Finding memories related to #{args.memory_id}...")
        related = engine.get_related(args.memory_id, max_hops=args.hops)

        if not related:
            print("No related memories found")
        else:
            for idx, mem in enumerate(related, 1):
                print(f"\n{idx}. Memory #{mem['id']} ({mem['hops']}-hop, weight={mem['weight']:.3f})")
                print(f"   Relationship: {mem['relationship']}")
                summary = mem['summary'] or '[No summary]'
                print(f"   Summary: {summary[:100]}...")
                if mem['shared_entities']:
                    print(f"   Shared: {', '.join(mem['shared_entities'][:5])}")

    elif args.command == 'cluster':
        if not args.cluster_id:
            print("Error: --cluster-id required for 'cluster' command")
            return

        print(f"Cluster #{args.cluster_id} members:")
        members = engine.get_cluster_members(args.cluster_id)

        for idx, mem in enumerate(members, 1):
            print(f"\n{idx}. Memory #{mem['id']} (importance={mem['importance']})")
            summary = mem['summary'] or '[No summary]'
            print(f"   {summary[:100]}...")


if __name__ == '__main__':
    main()
