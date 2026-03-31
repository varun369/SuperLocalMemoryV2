# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3 — V3-Only MCP Tools (5 tools).

set_mode, get_mode, health, consistency_check, recall_trace.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)


def register_v3_tools(server, get_engine: Callable) -> None:
    """Register 5 V3-exclusive tools on *server*."""

    # ------------------------------------------------------------------
    # 0. get_version (so IDEs can check compatibility)
    # ------------------------------------------------------------------
    @server.tool()
    async def get_version() -> dict:
        """Get SuperLocalMemory version, Python version, and platform info."""
        try:
            from importlib.metadata import version as _pkg_version
            slm_ver = _pkg_version("superlocalmemory")
        except Exception:
            slm_ver = "unknown"
        import platform
        import sys as _sys
        return {
            "success": True,
            "version": slm_ver,
            "python": _sys.version.split()[0],
            "platform": platform.system(),
            "arch": platform.machine(),
        }

    # ------------------------------------------------------------------
    # 1. set_mode
    # ------------------------------------------------------------------
    @server.tool()
    async def set_mode(mode: str) -> dict:
        """Switch operating mode (a, b, or c).

        Mode A: Local Guardian (zero LLM, EU AI Act full compliance).
        Mode B: Smart Local (local Ollama LLM, EU AI Act full).
        Mode C: Full Power (cloud LLM, best accuracy).

        Resets the engine to apply the new mode configuration.

        Args:
            mode: Target mode - 'a', 'b', or 'c'.
        """
        try:
            mode_lower = mode.strip().lower()
            if mode_lower not in ("a", "b", "c"):
                return {
                    "success": False,
                    "error": f"Invalid mode '{mode}'. Use 'a', 'b', or 'c'.",
                }
            from superlocalmemory.core.config import SLMConfig
            from superlocalmemory.storage.models import Mode
            from superlocalmemory.mcp.server import reset_engine

            mode_enum = Mode(mode_lower)
            old_config = SLMConfig.load()
            config = SLMConfig.for_mode(mode_enum)
            config.save()

            # V3.3: Check if embedding model changed — flag for re-indexing
            needs_reindex = (
                old_config.embedding.provider != config.embedding.provider
                or old_config.embedding.model_name != config.embedding.model_name
            )

            reset_engine()

            return {
                "success": True,
                "mode": mode_lower,
                "description": _mode_description(mode_lower),
                "needs_reindex": needs_reindex,
                "message": "Embedding re-indexing will run on next recall." if needs_reindex else "",
            }
        except Exception as exc:
            logger.exception("set_mode failed")
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # 2. get_mode
    # ------------------------------------------------------------------
    @server.tool()
    async def get_mode() -> dict:
        """Get current operating mode and its capabilities.

        Returns mode identifier, description, and feature flags
        (LLM availability, cross-encoder, agentic retrieval).
        """
        try:
            engine = get_engine()
            m = engine._config.mode.value
            caps = {
                "llm_available": engine._llm is not None,
                "cross_encoder": engine._config.retrieval.use_cross_encoder,
                "agentic_rounds": engine._config.retrieval.agentic_max_rounds,
                "sheaf_at_encoding": engine._config.math.sheaf_at_encoding,
            }
            return {
                "success": True,
                "mode": m,
                "description": _mode_description(m),
                "capabilities": caps,
            }
        except Exception as exc:
            logger.exception("get_mode failed")
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # 3. health
    # ------------------------------------------------------------------
    @server.tool()
    async def health() -> dict:
        """Get system health including math layer status.

        Reports on Fisher-Rao, Sheaf consistency, and Langevin dynamics
        health. Also includes database integrity and component status.
        """
        try:
            engine = get_engine()
            pid = engine.profile_id

            status: dict = {
                "success": True,
                "mode": engine._config.mode.value,
                "profile": pid,
                "components": {},
            }

            # Database health
            fact_count = engine._db.get_fact_count(pid)
            status["components"]["database"] = {
                "status": "ok",
                "fact_count": fact_count,
            }

            # Embedding service
            status["components"]["embedder"] = {
                "status": "ok" if engine._embedder else "unavailable",
                "model": engine._config.embedding.model_name,
            }

            # LLM
            status["components"]["llm"] = {
                "status": "ok" if engine._llm else "disabled",
                "provider": engine._config.llm.provider or "none",
            }

            # Fisher-Rao (math layer 1)
            fisher_facts = 0
            if fact_count > 0:
                rows = engine._db.execute(
                    "SELECT COUNT(*) AS c FROM atomic_facts "
                    "WHERE profile_id = ? AND fisher_mean IS NOT NULL",
                    (pid,),
                )
                fisher_facts = int(dict(rows[0])["c"]) if rows else 0
            status["components"]["fisher_rao"] = {
                "status": "ok" if fisher_facts > 0 else "no_data",
                "indexed_facts": fisher_facts,
                "temperature": engine._config.math.fisher_temperature,
            }

            # Sheaf consistency (math layer 2)
            status["components"]["sheaf"] = {
                "status": "active" if engine._sheaf_checker else "disabled",
                "threshold": engine._config.math.sheaf_contradiction_threshold,
            }

            # Langevin dynamics (math layer 3)
            langevin_facts = 0
            if fact_count > 0:
                rows = engine._db.execute(
                    "SELECT COUNT(*) AS c FROM atomic_facts "
                    "WHERE profile_id = ? AND langevin_position IS NOT NULL",
                    (pid,),
                )
                langevin_facts = int(dict(rows[0])["c"]) if rows else 0
            status["components"]["langevin"] = {
                "status": "ok" if langevin_facts > 0 else "no_data",
                "positioned_facts": langevin_facts,
            }

            return status
        except Exception as exc:
            logger.exception("health failed")
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # 4. consistency_check
    # ------------------------------------------------------------------
    @server.tool()
    async def consistency_check(limit: int = 100) -> dict:
        """Run sheaf consistency check on stored memories.

        Detects contradictions between facts using algebraic topology
        (sheaf cohomology). Returns pairs of contradicting facts with
        severity scores.

        Args:
            limit: Maximum facts to check (default 100).
        """
        try:
            engine = get_engine()
            pid = engine.profile_id

            if not engine._sheaf_checker:
                return {
                    "success": True,
                    "contradictions": [],
                    "note": "Sheaf checker is disabled in current configuration.",
                }

            facts = engine._db.get_all_facts(pid)[:limit]
            all_contradictions: list[dict] = []
            for fact in facts:
                if not fact.embedding or not fact.canonical_entities:
                    continue
                try:
                    contradictions = engine._sheaf_checker.check_consistency(
                        fact, pid,
                    )
                    for c in contradictions:
                        all_contradictions.append({
                            "fact_a": fact.fact_id,
                            "fact_b": c.fact_id_b,
                            "severity": round(c.severity, 3),
                            "content_a": fact.content[:80],
                        })
                except Exception:
                    continue

            return {
                "success": True,
                "facts_checked": len(facts),
                "contradictions": all_contradictions[:50],
                "total_contradictions": len(all_contradictions),
            }
        except Exception as exc:
            logger.exception("consistency_check failed")
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # 5. recall_trace
    # ------------------------------------------------------------------
    @server.tool()
    async def recall_trace(query: str, limit: int = 10) -> dict:
        """Recall with per-channel score breakdown.

        Like recall, but returns detailed channel-by-channel scores
        for debugging retrieval quality.

        Args:
            query: Natural-language search query.
            limit: Maximum results (default 10).
        """
        try:
            engine = get_engine()
            response = engine.recall(query, limit=limit)
            results = []
            for r in response.results[:limit]:
                results.append({
                    "fact_id": r.fact.fact_id,
                    "content": r.fact.content,
                    "final_score": round(r.score, 4),
                    "confidence": round(r.confidence, 3),
                    "trust_score": round(r.trust_score, 3),
                    "channel_scores": {
                        k: round(v, 4) for k, v in r.channel_scores.items()
                    },
                    "evidence_chain": r.evidence_chain,
                    "fact_type": r.fact.fact_type.value,
                    "lifecycle": r.fact.lifecycle.value,
                    "access_count": r.fact.access_count,
                })
            return {
                "success": True,
                "results": results,
                "count": len(results),
                "query_type": response.query_type,
                "channel_weights": {
                    k: round(v, 3)
                    for k, v in response.channel_weights.items()
                },
                "total_candidates": response.total_candidates,
                "retrieval_time_ms": round(response.retrieval_time_ms, 1),
            }
        except Exception as exc:
            logger.exception("recall_trace failed")
            return {"success": False, "error": str(exc)}


# -- Helpers ------------------------------------------------------------------

def _mode_description(mode: str) -> str:
    """Human-readable description for a mode."""
    descriptions = {
        "a": "Local Guardian: zero LLM, full EU AI Act compliance",
        "b": "Smart Local: local Ollama LLM, full EU AI Act compliance",
        "c": "Full Power: cloud LLM, best accuracy, partial EU AI Act",
    }
    return descriptions.get(mode, "Unknown mode")
