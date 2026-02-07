#!/usr/bin/env python3
"""
EmbeddingEngine - Local Embedding Generation for SuperLocalMemory V2

Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
Repository: https://github.com/varun369/SuperLocalMemoryV2

Implements local embedding generation using sentence-transformers:
- all-MiniLM-L6-v2 model (384 dimensions, 80MB)
- Batch processing for efficiency
- GPU acceleration with automatic detection
- Disk caching for repeated queries
- Graceful fallback to TF-IDF if unavailable

All processing is local - no external APIs required.

LIMITS:
- MAX_BATCH_SIZE: 128 (prevents memory exhaustion)
- MAX_TEXT_LENGTH: 10,000 characters per input
- CACHE_MAX_SIZE: 10,000 entries (LRU eviction)
"""

# SECURITY: Embedding generation limits to prevent resource exhaustion
MAX_BATCH_SIZE = 128
MAX_TEXT_LENGTH = 10_000
CACHE_MAX_SIZE = 10_000

import sqlite3
import json
import time
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple
from collections import OrderedDict
import numpy as np

# Optional sentence-transformers dependency
SENTENCE_TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    # Graceful degradation - will use TF-IDF fallback

# Fallback: TF-IDF vectorization
SKLEARN_AVAILABLE = False
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# GPU detection
TORCH_AVAILABLE = False
CUDA_AVAILABLE = False
MPS_AVAILABLE = False  # Apple Silicon

try:
    import torch
    TORCH_AVAILABLE = True
    CUDA_AVAILABLE = torch.cuda.is_available()
    MPS_AVAILABLE = hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
except ImportError:
    pass

MEMORY_DIR = Path.home() / ".claude-memory"
EMBEDDING_CACHE_PATH = MEMORY_DIR / "embedding_cache.json"
MODEL_CACHE_PATH = MEMORY_DIR / "models"  # Local model storage

logger = logging.getLogger(__name__)


class LRUCache:
    """Simple LRU cache for embeddings."""

    def __init__(self, max_size: int = CACHE_MAX_SIZE):
        self.cache = OrderedDict()
        self.max_size = max_size

    def get(self, key: str) -> Optional[np.ndarray]:
        """Get item from cache, moving to end (most recent)."""
        if key not in self.cache:
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return np.array(self.cache[key])

    def set(self, key: str, value: np.ndarray):
        """Set item in cache, evicting oldest if full."""
        if key in self.cache:
            # Update existing
            self.cache.move_to_end(key)
            self.cache[key] = value.tolist()
        else:
            # Add new
            if len(self.cache) >= self.max_size:
                # Evict oldest
                self.cache.popitem(last=False)
            self.cache[key] = value.tolist()

    def save(self, path: Path):
        """Save cache to disk."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(dict(self.cache), f)
            logger.debug(f"Saved {len(self.cache)} cached embeddings")
        except Exception as e:
            logger.error(f"Failed to save embedding cache: {e}")

    def load(self, path: Path):
        """Load cache from disk."""
        if not path.exists():
            return

        try:
            with open(path, 'r') as f:
                data = json.load(f)
                self.cache = OrderedDict(data)
            logger.info(f"Loaded {len(self.cache)} cached embeddings")
        except Exception as e:
            logger.error(f"Failed to load embedding cache: {e}")
            self.cache = OrderedDict()


class EmbeddingEngine:
    """
    Local embedding generation using sentence-transformers.

    Features:
    - all-MiniLM-L6-v2 model (384 dimensions, 80MB, fast)
    - Batch processing for efficiency (up to 128 texts)
    - GPU acceleration (CUDA/MPS) with automatic detection
    - LRU cache for repeated queries (10K entries)
    - Graceful fallback to TF-IDF if dependencies unavailable

    Performance:
    - CPU: ~100 embeddings/sec
    - GPU (CUDA): ~1000 embeddings/sec
    - Apple Silicon (MPS): ~500 embeddings/sec
    - Cache hit: ~0.001ms
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
        cache_path: Optional[Path] = None,
        model_cache_path: Optional[Path] = None,
        use_cache: bool = True
    ):
        """
        Initialize embedding engine.

        Args:
            model_name: Sentence transformer model name (default: all-MiniLM-L6-v2)
            device: Device to use ('cuda', 'mps', 'cpu', or None for auto)
            cache_path: Custom path for embedding cache
            model_cache_path: Custom path for model storage
            use_cache: Whether to use LRU cache

        Available models:
        - all-MiniLM-L6-v2: 384 dim, 80MB, fast, recommended
        - all-mpnet-base-v2: 768 dim, 420MB, more accurate
        - paraphrase-multilingual: 384 dim, 420MB, multilingual
        """
        self.model_name = model_name
        self.cache_path = cache_path or EMBEDDING_CACHE_PATH
        self.model_cache_path = model_cache_path or MODEL_CACHE_PATH
        self.use_cache = use_cache

        # Auto-detect device
        if device is None:
            if CUDA_AVAILABLE:
                device = 'cuda'
                logger.info("Using CUDA GPU acceleration")
            elif MPS_AVAILABLE:
                device = 'mps'
                logger.info("Using Apple Silicon (MPS) GPU acceleration")
            else:
                device = 'cpu'
                logger.info("Using CPU (consider GPU for faster processing)")
        self.device = device

        # Initialize model
        self.model = None
        self.dimension = 384  # Default for all-MiniLM-L6-v2
        self.use_transformers = SENTENCE_TRANSFORMERS_AVAILABLE

        # Initialize cache
        self.cache = LRUCache(max_size=CACHE_MAX_SIZE) if use_cache else None

        # Load cache from disk
        if self.cache:
            self.cache.load(self.cache_path)

        # Fallback: TF-IDF vectorizer
        self.tfidf_vectorizer = None
        self.tfidf_fitted = False

        # Load model
        self._load_model()

    def _load_model(self):
        """Load sentence transformer model or fallback to TF-IDF."""
        if not self.use_transformers:
            logger.warning(
                "sentence-transformers unavailable. Install with: "
                "pip install sentence-transformers"
            )
            self._init_fallback()
            return

        try:
            # Create model cache directory
            self.model_cache_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"Loading model: {self.model_name}")
            start_time = time.time()

            # Load model with local cache
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=str(self.model_cache_path)
            )

            # Get actual dimension
            self.dimension = self.model.get_sentence_embedding_dimension()

            elapsed = time.time() - start_time
            logger.info(
                f"Loaded {self.model_name} ({self.dimension}D) in {elapsed:.2f}s"
            )

        except Exception as e:
            logger.error(f"Failed to load sentence transformer: {e}")
            logger.info("Falling back to TF-IDF")
            self.use_transformers = False
            self._init_fallback()

    def _init_fallback(self):
        """Initialize TF-IDF fallback."""
        if not SKLEARN_AVAILABLE:
            logger.error(
                "sklearn unavailable - no fallback available. "
                "Install: pip install scikit-learn"
            )
            return

        logger.info("Using TF-IDF fallback (dimension will be dynamic)")
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=384,  # Match sentence transformer dimension
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        self.dimension = 384

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single text or list of texts
            batch_size: Batch size for processing (max: 128)
            show_progress: Show progress bar for large batches
            normalize: Normalize embeddings to unit length

        Returns:
            Array of shape (n_texts, dimension) or (dimension,) for single text

        Raises:
            ValueError: If input validation fails
        """
        # Convert single text to list
        single_input = isinstance(texts, str)
        if single_input:
            texts = [texts]

        # SECURITY: Input validation
        if len(texts) == 0:
            return np.array([])

        batch_size = min(batch_size, MAX_BATCH_SIZE)

        # Validate text length
        for i, text in enumerate(texts):
            if not isinstance(text, str):
                raise ValueError(f"Text at index {i} is not a string")
            if len(text) > MAX_TEXT_LENGTH:
                logger.warning(f"Text {i} truncated from {len(text)} to {MAX_TEXT_LENGTH} chars")
                texts[i] = text[:MAX_TEXT_LENGTH]

        # Check cache for hits
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        if self.cache:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                cached = self.cache.get(cache_key)

                if cached is not None:
                    embeddings.append((i, cached))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))

        # Generate embeddings for uncached texts
        if uncached_texts:
            if self.use_transformers and self.model:
                # Use sentence transformer
                uncached_embeddings = self._encode_transformer(
                    uncached_texts,
                    batch_size=batch_size,
                    show_progress=show_progress
                )
            elif self.tfidf_vectorizer:
                # Use TF-IDF fallback
                uncached_embeddings = self._encode_tfidf(uncached_texts)
            else:
                raise RuntimeError("No embedding method available")

            # Add to cache and results
            for i, text, embedding in zip(uncached_indices, uncached_texts, uncached_embeddings):
                if self.cache:
                    cache_key = self._get_cache_key(text)
                    self.cache.set(cache_key, embedding)
                embeddings.append((i, embedding))

        # Sort by original index and extract embeddings
        embeddings.sort(key=lambda x: x[0])
        result = np.array([emb for _, emb in embeddings])

        # Normalize if requested
        if normalize and len(result) > 0:
            norms = np.linalg.norm(result, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            result = result / norms

        # Return single embedding if single input
        if single_input:
            return result[0]

        return result

    def _encode_transformer(
        self,
        texts: List[str],
        batch_size: int,
        show_progress: bool
    ) -> np.ndarray:
        """Generate embeddings using sentence transformer."""
        try:
            start_time = time.time()

            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=False  # We'll normalize separately
            )

            elapsed = time.time() - start_time
            rate = len(texts) / elapsed if elapsed > 0 else 0
            logger.debug(f"Encoded {len(texts)} texts in {elapsed:.2f}s ({rate:.0f} texts/sec)")

            return embeddings

        except Exception as e:
            logger.error(f"Transformer encoding failed: {e}")
            raise

    def _encode_tfidf(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using TF-IDF fallback."""
        try:
            if not self.tfidf_fitted:
                # Fit on first use
                logger.info("Fitting TF-IDF vectorizer...")
                self.tfidf_vectorizer.fit(texts)
                self.tfidf_fitted = True

            embeddings = self.tfidf_vectorizer.transform(texts).toarray()

            # Pad or truncate to target dimension
            if embeddings.shape[1] < self.dimension:
                padding = np.zeros((embeddings.shape[0], self.dimension - embeddings.shape[1]))
                embeddings = np.hstack([embeddings, padding])
            elif embeddings.shape[1] > self.dimension:
                embeddings = embeddings[:, :self.dimension]

            return embeddings

        except Exception as e:
            logger.error(f"TF-IDF encoding failed: {e}")
            raise

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Convenience method for batch encoding with progress.

        Args:
            texts: List of texts to encode
            batch_size: Batch size for processing
            show_progress: Show progress bar

        Returns:
            Array of shape (n_texts, dimension)
        """
        return self.encode(texts, batch_size=batch_size, show_progress=show_progress)

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score in [0, 1] (higher = more similar)
        """
        # Normalize
        emb1 = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
        emb2 = embedding2 / (np.linalg.norm(embedding2) + 1e-8)

        # Cosine similarity
        similarity = np.dot(emb1, emb2)

        # Clamp to [0, 1]
        return float(max(0.0, min(1.0, similarity)))

    def save_cache(self):
        """Save embedding cache to disk."""
        if self.cache:
            self.cache.save(self.cache_path)

    def clear_cache(self):
        """Clear embedding cache."""
        if self.cache:
            self.cache.cache.clear()
            logger.info("Cleared embedding cache")

    def get_stats(self) -> Dict[str, any]:
        """
        Get embedding engine statistics.

        Returns:
            Dictionary with engine stats
        """
        return {
            'sentence_transformers_available': SENTENCE_TRANSFORMERS_AVAILABLE,
            'use_transformers': self.use_transformers,
            'sklearn_available': SKLEARN_AVAILABLE,
            'torch_available': TORCH_AVAILABLE,
            'cuda_available': CUDA_AVAILABLE,
            'mps_available': MPS_AVAILABLE,
            'device': self.device,
            'model_name': self.model_name,
            'dimension': self.dimension,
            'cache_enabled': self.cache is not None,
            'cache_size': len(self.cache.cache) if self.cache else 0,
            'cache_max_size': CACHE_MAX_SIZE,
            'model_loaded': self.model is not None or self.tfidf_vectorizer is not None
        }

    def add_to_database(
        self,
        db_path: Path,
        embedding_column: str = 'embedding',
        batch_size: int = 32
    ):
        """
        Generate embeddings for all memories in database.

        Args:
            db_path: Path to SQLite database
            embedding_column: Column name to store embeddings
            batch_size: Batch size for processing
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # Check if embedding column exists
            cursor.execute("PRAGMA table_info(memories)")
            columns = {row[1] for row in cursor.fetchall()}

            if embedding_column not in columns:
                # Add column
                logger.info(f"Adding '{embedding_column}' column to database")
                cursor.execute(f'ALTER TABLE memories ADD COLUMN {embedding_column} TEXT')
                conn.commit()

            # Get memories without embeddings
            cursor.execute(f'''
                SELECT id, content, summary
                FROM memories
                WHERE {embedding_column} IS NULL OR {embedding_column} = ''
            ''')
            rows = cursor.fetchall()

            if not rows:
                logger.info("All memories already have embeddings")
                conn.close()
                return

            logger.info(f"Generating embeddings for {len(rows)} memories...")

            # Process in batches
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                memory_ids = [row[0] for row in batch]

                # Combine content and summary
                texts = []
                for row in batch:
                    content = row[1] or ""
                    summary = row[2] or ""
                    text = f"{content} {summary}".strip()
                    texts.append(text)

                # Generate embeddings
                embeddings = self.encode(texts, batch_size=batch_size)

                # Store in database
                for mem_id, embedding in zip(memory_ids, embeddings):
                    embedding_json = json.dumps(embedding.tolist())
                    cursor.execute(
                        f'UPDATE memories SET {embedding_column} = ? WHERE id = ?',
                        (embedding_json, mem_id)
                    )

                conn.commit()
                logger.info(f"Processed {min(i+batch_size, len(rows))}/{len(rows)} memories")

            # Save cache
            self.save_cache()

            logger.info(f"Successfully generated embeddings for {len(rows)} memories")

        finally:
            conn.close()


# CLI interface for testing
if __name__ == "__main__":
    import sys

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    if len(sys.argv) < 2:
        print("EmbeddingEngine CLI - Local Embedding Generation")
        print("\nCommands:")
        print("  python embedding_engine.py stats              # Show engine statistics")
        print("  python embedding_engine.py generate           # Generate embeddings for database")
        print("  python embedding_engine.py test               # Run performance test")
        print("  python embedding_engine.py clear-cache        # Clear embedding cache")
        sys.exit(0)

    command = sys.argv[1]

    if command == "stats":
        engine = EmbeddingEngine()
        stats = engine.get_stats()
        print(json.dumps(stats, indent=2))

    elif command == "generate":
        db_path = MEMORY_DIR / "memory.db"
        if not db_path.exists():
            print(f"Database not found at {db_path}")
            sys.exit(1)

        print("Generating embeddings for all memories...")
        engine = EmbeddingEngine()
        engine.add_to_database(db_path)
        print("Generation complete!")
        print(json.dumps(engine.get_stats(), indent=2))

    elif command == "clear-cache":
        engine = EmbeddingEngine()
        engine.clear_cache()
        engine.save_cache()
        print("Cache cleared!")

    elif command == "test":
        print("Running embedding performance test...")

        engine = EmbeddingEngine()

        # Test single encoding
        print("\nTest 1: Single text encoding")
        text = "This is a test sentence for embedding generation."
        start = time.time()
        embedding = engine.encode(text)
        elapsed = time.time() - start
        print(f"  Time: {elapsed*1000:.2f}ms")
        print(f"  Dimension: {len(embedding)}")
        print(f"  Sample values: {embedding[:5]}")

        # Test batch encoding
        print("\nTest 2: Batch encoding (100 texts)")
        texts = [f"This is test sentence number {i} with some content." for i in range(100)]
        start = time.time()
        embeddings = engine.encode(texts, batch_size=32)
        elapsed = time.time() - start
        print(f"  Time: {elapsed*1000:.2f}ms ({100/elapsed:.0f} texts/sec)")
        print(f"  Shape: {embeddings.shape}")

        # Test cache
        print("\nTest 3: Cache performance")
        start = time.time()
        embedding_cached = engine.encode(text)
        elapsed = time.time() - start
        print(f"  Cache hit time: {elapsed*1000:.4f}ms")
        print(f"  Speedup: {(elapsed*1000):.0f}x faster")

        # Test similarity
        print("\nTest 4: Similarity computation")
        text1 = "The weather is nice today."
        text2 = "It's a beautiful day outside."
        text3 = "Python is a programming language."

        emb1 = engine.encode(text1)
        emb2 = engine.encode(text2)
        emb3 = engine.encode(text3)

        sim_12 = engine.similarity(emb1, emb2)
        sim_13 = engine.similarity(emb1, emb3)

        print(f"  Similarity (weather vs beautiful day): {sim_12:.3f}")
        print(f"  Similarity (weather vs programming): {sim_13:.3f}")

        # Print stats
        print("\nEngine statistics:")
        print(json.dumps(engine.get_stats(), indent=2))

        # Save cache
        engine.save_cache()
        print("\nCache saved!")

    else:
        print(f"Unknown command: {command}")
        print("Run without arguments to see available commands.")
