# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Embedding migration on mode/model switch.

When a user switches modes (e.g., Mode B Ollama -> Mode A sentence-transformers),
the embeddings live in different vector spaces. This module detects the mismatch
and flags facts for progressive re-embedding.

Key table: ``embedding_metadata.model_name`` stores the model used for each fact.
A config-level field in ``config.json`` stores the current model signature.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from superlocalmemory.core.config import SLMConfig

logger = logging.getLogger(__name__)

# Sentinel stored in config.json when no model has been set yet.
_NO_MODEL = ""

# Batch size for progressive re-embedding.
_REINDEX_BATCH_SIZE = 50


def _model_signature(config: SLMConfig) -> str:
    """Derive a deterministic signature from the active embedding config.

    The signature combines provider + model_name + dimension so that
    any change in embedding source is detected.
    """
    emb = config.embedding
    return f"{emb.provider}::{emb.model_name}::{emb.dimension}"


def _read_stored_signature(config_dir: Path) -> str:
    """Read the last-used embedding model signature from config.json."""
    config_path = config_dir / "config.json"
    if not config_path.exists():
        return _NO_MODEL
    try:
        data = json.loads(config_path.read_text())
        return data.get("embedding_signature", _NO_MODEL)
    except (json.JSONDecodeError, OSError):
        return _NO_MODEL


def _write_stored_signature(config_dir: Path, signature: str) -> None:
    """Persist the current embedding model signature to config.json."""
    config_path = config_dir / "config.json"
    data: dict[str, Any] = {}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    data["embedding_signature"] = signature
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2))


def check_embedding_migration(config: SLMConfig) -> bool:
    """Check if embedding model changed since last run.

    Returns True if re-indexing is needed (model signature differs).
    Returns False if signatures match or this is the first run.
    """
    current_sig = _model_signature(config)
    stored_sig = _read_stored_signature(config.base_dir)

    if stored_sig == _NO_MODEL:
        # First run — store signature, no migration needed.
        _write_stored_signature(config.base_dir, current_sig)
        logger.info("Embedding signature initialized: %s", current_sig)
        return False

    if stored_sig == current_sig:
        return False

    logger.warning(
        "Embedding model changed: %s -> %s. Re-indexing required.",
        stored_sig, current_sig,
    )
    return True


def run_embedding_migration(
    config: SLMConfig,
    db: Any,
    embedder: Any,
) -> int:
    """Re-embed all facts with the current model. Returns count re-embedded.

    Processes facts in batches to avoid memory spikes. Updates the
    embedding_metadata table and vector store for each fact.

    This is idempotent — can be interrupted and resumed safely.
    """
    if embedder is None:
        logger.warning("No embedder available. Skipping re-indexing.")
        return 0

    current_sig = _model_signature(config)
    profile_id = config.active_profile

    # Get all fact IDs that need re-embedding (all facts for the profile).
    rows = db.execute(
        "SELECT fact_id, content FROM atomic_facts "
        "WHERE profile_id = ? ORDER BY created_at",
        (profile_id,),
    )
    facts = [(dict(r)["fact_id"], dict(r)["content"]) for r in rows]
    total = len(facts)

    if total == 0:
        _write_stored_signature(config.base_dir, current_sig)
        return 0

    logger.info(
        "Re-embedding %d facts with model %s (batch_size=%d)",
        total, current_sig, _REINDEX_BATCH_SIZE,
    )

    reindexed = 0
    for i in range(0, total, _REINDEX_BATCH_SIZE):
        batch = facts[i : i + _REINDEX_BATCH_SIZE]
        texts = [content for _, content in batch]
        fact_ids = [fid for fid, _ in batch]

        try:
            vectors = embedder.embed_batch(texts)
        except Exception as exc:
            logger.error(
                "Re-embedding batch %d-%d failed: %s. Stopping migration.",
                i, i + len(batch), exc,
            )
            break

        for j, (fid, vec) in enumerate(zip(fact_ids, vectors)):
            if vec is None:
                continue
            # Update embedding in the database (embedding column on atomic_facts).
            try:
                embedding_json = json.dumps(vec)
                db.execute(
                    "UPDATE atomic_facts SET embedding = ? WHERE fact_id = ?",
                    (embedding_json, fid),
                )
                # Update embedding_metadata with new model name.
                db.execute(
                    "UPDATE embedding_metadata SET model_name = ? "
                    "WHERE fact_id = ?",
                    (config.embedding.model_name, fid),
                )
                reindexed += 1
            except Exception as exc:
                logger.warning(
                    "Failed to update embedding for fact %s: %s",
                    fid[:16], exc,
                )

    # Update stored signature after successful migration.
    _write_stored_signature(config.base_dir, current_sig)
    logger.info(
        "Embedding migration complete: %d/%d facts re-embedded.",
        reindexed, total,
    )
    return reindexed
