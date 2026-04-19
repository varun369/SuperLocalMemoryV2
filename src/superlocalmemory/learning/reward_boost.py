# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory v3.4.21 — F4.A Stage-8 H-06/H-18 fix

"""Strong-memory boost + reward-aware fact selection.

Nudges ``atomic_facts.retrieval_prior`` upward for facts with recurring
high reward, capped at 0.5 (LLD-12 §5). Also exposes
``select_high_reward_fact_ids`` for the soft-prompt generator.

H-06 regression fix: outcome lookups now use the JSON1-backed
``fact_outcome_joins`` helper instead of the fragile
``fact_ids_json LIKE '%"<fid>"%'`` pattern that leaked substring matches
across overlapping fact_id prefixes.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from superlocalmemory.learning.fact_outcome_joins import (
    aggregate_reward_for_fact,
)

logger = logging.getLogger(__name__)


STRONG_BOOST_INCREMENT: float = 0.1
STRONG_BOOST_CAP: float = 0.5
STRONG_BOOST_MIN_OUTCOMES: int = 3
STRONG_BOOST_MIN_MEAN: float = 0.7


__all__ = (
    "apply_strong_memory_boost",
    "select_high_reward_fact_ids",
    "STRONG_BOOST_INCREMENT",
    "STRONG_BOOST_CAP",
    "STRONG_BOOST_MIN_OUTCOMES",
    "STRONG_BOOST_MIN_MEAN",
)


def apply_strong_memory_boost(
    memory_db_path: str | Path, profile_id: str,
) -> int:
    """Nudge retrieval_prior up for high-reward facts, capped at 0.5.

    Eligibility: ≥ MIN_OUTCOMES outcomes with mean reward > MIN_MEAN.
    Effect: retrieval_prior = MIN(retrieval_prior + INCREMENT, CAP).

    Returns number of rows boosted.
    """
    conn = sqlite3.connect(str(memory_db_path), timeout=10.0)
    conn.execute("PRAGMA busy_timeout=2000")
    boosted = 0
    try:
        rows = conn.execute(
            "SELECT fact_id FROM atomic_facts WHERE profile_id=? "
            "  AND (archive_status IS NULL OR archive_status='live')",
            (profile_id,),
        ).fetchall()
        if not rows:
            return 0

        conn.execute("BEGIN IMMEDIATE")
        for (fid,) in rows:
            # H-06 fix: JSON1 aggregate instead of LIKE substring.
            count, mean = aggregate_reward_for_fact(conn, profile_id, fid)
            if count < STRONG_BOOST_MIN_OUTCOMES:
                continue
            if mean <= STRONG_BOOST_MIN_MEAN:
                continue
            conn.execute(
                "UPDATE atomic_facts "
                "SET retrieval_prior = MIN(COALESCE(retrieval_prior, 0) + ?, ?) "
                "WHERE fact_id=?",
                (STRONG_BOOST_INCREMENT, STRONG_BOOST_CAP, fid),
            )
            boosted += 1
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        logger.warning("apply_strong_memory_boost rollback: %s", exc)
    finally:
        conn.close()
    return boosted


def select_high_reward_fact_ids(
    memory_db_path: str | Path,
    profile_id: str,
    *,
    min_reward: float = 0.6,
    min_outcomes: int = 1,
) -> list[str]:
    """Return fact_ids whose mean outcome reward ≥ ``min_reward``.

    Used by ``soft_prompt_generator`` to mine only high-reward facts
    (LLD-12 §6). JSON1-backed — no substring false positives.
    """
    conn = sqlite3.connect(str(memory_db_path), timeout=10.0)
    try:
        fact_rows = conn.execute(
            "SELECT fact_id FROM atomic_facts WHERE profile_id=? "
            "  AND (archive_status IS NULL OR archive_status='live')",
            (profile_id,),
        ).fetchall()
        out: list[str] = []
        for (fid,) in fact_rows:
            count, mean = aggregate_reward_for_fact(conn, profile_id, fid)
            if count < min_outcomes:
                continue
            if mean >= min_reward:
                out.append(fid)
        return out
    finally:
        conn.close()
