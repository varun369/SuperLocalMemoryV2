# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3.1 — Active Memory MCP Tools.

session_init    — Auto-recall project context at session start.
observe         — Monitor conversation for auto-capture (decisions/bugs/prefs).
report_feedback — Record explicit feedback on recall results for learning.

These tools transform SLM from a passive database into an active
intelligence layer that learns and improves over time.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

MEMORY_DIR = Path.home() / ".superlocalmemory"
DB_PATH = MEMORY_DIR / "memory.db"


def _get_agent_id(default: str = "mcp_client") -> str:
    """Resolve the calling agent's ID for attribution.

    Each Avenger (Claude, Codex, Gemini, Kimi, GLM, Qwen, etc.) sets the
    ``SLM_AGENT_ID`` env var in its MCP server config so that memories,
    observations, and registry entries are tagged with the actual source
    agent — not the legacy ``"mcp_client"`` default.

    v3.4.39+: enables proper cross-Avenger attribution in ``session_init``,
    ``observe``, and event emissions.
    """
    return os.environ.get("SLM_AGENT_ID", default)


def _emit_event(event_type: str, payload: dict | None = None,
                source_agent: str | None = None) -> None:  # V3.3.12: see also mcp/shared.py
    """Emit an event to the EventBus (best-effort, never raises).

    Dashboard visibility is load-bearing per the v3.4.26 user contract,
    so we log on failure rather than silently dropping the signal.
    """
    resolved_agent = source_agent if source_agent is not None else _get_agent_id()
    try:
        from superlocalmemory.infra.event_bus import EventBus
        bus = EventBus.get_instance(str(DB_PATH))
        bus.emit(event_type, payload=payload, source_agent=resolved_agent,
                 source_protocol="mcp")
    except Exception as exc:
        logger.warning("event emit failed: type=%s err=%s", event_type, exc)


def _register_agent(agent_id: str, profile_id: str) -> None:
    """Register an agent in the AgentRegistry (best-effort)."""
    try:
        from superlocalmemory.core.registry import AgentRegistry
        registry_path = MEMORY_DIR / "agents.json"
        registry = AgentRegistry(persist_path=registry_path)
        registry.register_agent(agent_id, profile_id)
    except Exception as exc:
        logger.warning(
            "agent registry write failed: agent=%s err=%s", agent_id, exc,
        )


def register_active_tools(server, get_engine: Callable) -> None:
    """Register 3 active memory tools on *server*."""

    # ------------------------------------------------------------------
    # 1. session_init — Auto-recall project context at session start
    # ------------------------------------------------------------------
    @server.tool()
    async def session_init(
        project_path: str = "",
        query: str = "",
        max_results: int = 10,
    ) -> dict:
        """Initialize session with relevant memory context.

        Call this ONCE at the start of every session. Returns:
        - Recent decisions and patterns for this project
        - Top relevant memories based on project path or query
        - Learning status (signal count, ranking phase)

        The AI should call this automatically before any other work.
        """
        try:
            from superlocalmemory.hooks.auto_recall import AutoRecall
            from superlocalmemory.hooks.rules_engine import RulesEngine
            from superlocalmemory.mcp._pool_adapter import pool_recall

            engine = get_engine()
            rules = RulesEngine()

            if not rules.should_recall("session_start"):
                return {"success": True, "context": "", "memories": [], "message": "Auto-recall disabled"}

            recall_config = rules.get_recall_config()
            auto = AutoRecall(
                recall_fn=pool_recall,
                config={
                    "enabled": True,
                    "max_memories_injected": max_results,
                    "relevance_threshold": recall_config.get("relevance_threshold", 0.3),
                },
            )

            # Get formatted context for system prompt injection
            context = auto.get_session_context(project_path=project_path, query=query)

            # Get structured results for tool response
            search_query = query or f"project context {project_path}" if project_path else "recent important decisions"
            memories = auto.get_query_context(search_query)

            # Get learning status
            pid = engine.profile_id
            feedback_count = 0
            try:
                feedback_count = engine._adaptive_learner.get_feedback_count(pid)
            except Exception as exc:
                # Feedback count is a Dash-Core signal; a silent zero
                # masks wiring bugs. Log so operators see the failure.
                logger.warning(
                    "session_init feedback_count read failed: %s", exc,
                )

            # Register agent + emit event (v3.4.39: SLM_AGENT_ID env support)
            agent_id = _get_agent_id()
            _register_agent(agent_id, pid)
            _emit_event("agent.connected", {
                "agent_id": agent_id,
                "project_path": project_path,
                "memory_count": len(memories),
            })

            return {
                "success": True,
                "context": context,
                "memories": memories[:max_results],
                "memory_count": len(memories),
                "learning": {
                    "feedback_signals": feedback_count,
                    "phase": 1 if feedback_count < 50 else (2 if feedback_count < 200 else 3),
                    "status": "collecting" if feedback_count < 50 else ("learning" if feedback_count < 200 else "trained"),
                },
            }
        except Exception as exc:
            logger.exception("session_init failed")
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # 2. observe — Auto-capture decisions/bugs/preferences
    # ------------------------------------------------------------------
    @server.tool()
    async def observe(
        content: str,
        agent_id: str | None = None,
    ) -> dict:
        """Observe conversation content for automatic memory capture.

        Send conversation snippets here. The system evaluates whether
        the content contains decisions, bug fixes, or preferences worth
        storing. If so, it auto-captures them with classification metadata.

        Call this after making decisions, fixing bugs, or expressing preferences.
        The system will NOT store low-confidence or irrelevant content.

        v3.4.39: ``agent_id`` now defaults to the ``SLM_AGENT_ID`` env var
        (set by each Avenger's MCP config) so observations carry proper
        cross-Avenger attribution.
        """
        if agent_id is None:
            agent_id = _get_agent_id()
        try:
            from superlocalmemory.hooks.auto_capture import AutoCapture
            from superlocalmemory.hooks.rules_engine import RulesEngine
            from superlocalmemory.mcp._pool_adapter import pool_store

            engine = get_engine()
            rules = RulesEngine()

            auto = AutoCapture(
                store_fn=pool_store,
                config=rules.get_capture_config(),
            )

            decision = auto.evaluate(content)

            if not decision.capture:
                return {
                    "captured": False,
                    "reason": decision.reason,
                    "category": decision.category,
                    "confidence": round(decision.confidence, 3),
                }

            # Check rules engine for category-level permission
            if not rules.should_capture(decision.category, decision.confidence):
                return {
                    "captured": False,
                    "reason": f"Category '{decision.category}' disabled in rules",
                    "category": decision.category,
                    "confidence": round(decision.confidence, 3),
                }

            # Auto-store via engine
            stored = auto.capture(
                content,
                category=decision.category,
                metadata={"agent_id": agent_id, "source": "auto-observe"},
            )

            if stored:
                _emit_event("memory.created", {
                    "agent_id": agent_id,
                    "category": decision.category,
                    "content_preview": content[:80],
                    "source": "auto-observe",
                }, source_agent=agent_id)

            return {
                "captured": stored,
                "category": decision.category,
                "confidence": round(decision.confidence, 3),
                "reason": decision.reason,
            }
        except Exception as exc:
            logger.exception("observe failed")
            return {"captured": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # 3. report_feedback — Explicit feedback for learning
    # ------------------------------------------------------------------
    @server.tool()
    async def report_feedback(
        fact_id: str,
        feedback: str = "relevant",
        query: str = "",
    ) -> dict:
        """Report whether a recalled memory was useful.

        feedback: "relevant" (memory was helpful), "irrelevant" (not useful),
                  "partial" (somewhat relevant).

        This feedback trains the adaptive ranker to return better results
        over time. The more feedback, the smarter the system gets.
        """
        try:
            engine = get_engine()
            pid = engine.profile_id

            if feedback not in ("relevant", "irrelevant", "partial"):
                return {"success": False, "error": f"Invalid feedback: {feedback}. Use relevant/irrelevant/partial"}

            record = engine._adaptive_learner.record_feedback(
                query=query,
                fact_id=fact_id,
                feedback_type=feedback,
                profile_id=pid,
            )

            count = engine._adaptive_learner.get_feedback_count(pid)

            _emit_event("pattern.learned", {
                "fact_id": fact_id,
                "feedback": feedback,
                "total_signals": count,
                "phase": 1 if count < 50 else (2 if count < 200 else 3),
            })

            return {
                "success": True,
                "feedback_id": record.feedback_id,
                "total_signals": count,
                "phase": 1 if count < 50 else (2 if count < 200 else 3),
                "message": f"Feedback recorded. {count} total signals."
                + (" Phase 2 unlocked!" if count == 50 else "")
                + (" Phase 3 (ML) unlocked!" if count == 200 else ""),
            }
        except Exception as exc:
            logger.exception("report_feedback failed")
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # close_session — V3.3.12: Expose session closure via MCP
    # ------------------------------------------------------------------

    @server.tool()
    async def close_session(session_id: str = "") -> dict:
        """Close the current session and create temporal summary events.

        Aggregates facts from the session into per-entity temporal summaries,
        enabling temporal queries like "What happened in session X?"

        Args:
            session_id: Session to close. Defaults to the most recent session.
        """
        try:
            engine = get_engine()
            pid = engine.profile_id
            sid = session_id or getattr(engine, '_last_session_id', '')
            if not sid:
                return {"success": False, "error": "No session_id provided"}
            count = engine.close_session(sid)
            return {
                "success": True,
                "session_id": sid,
                "summary_events_created": count,
            }
        except Exception as exc:
            logger.exception("close_session failed")
            return {"success": False, "error": str(exc)}
