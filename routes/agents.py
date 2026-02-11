"""
SuperLocalMemory V2 - Agent Registry + Trust Routes (v2.5)
Copyright (c) 2026 Varun Pratap Bhardwaj — MIT License

Routes: /api/agents, /api/agents/stats, /api/trust/stats, /api/trust/signals/{agent_id}
Progressive enhancement: routes return empty data if agent registry is unavailable.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .helpers import DB_PATH

router = APIRouter()

# Feature flag
try:
    from agent_registry import AgentRegistry
    from trust_scorer import TrustScorer
    AGENT_REGISTRY_AVAILABLE = True
except ImportError:
    AGENT_REGISTRY_AVAILABLE = False


@router.get("/api/agents")
async def get_agents(
    protocol: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """List registered agents with optional protocol filter."""
    if not AGENT_REGISTRY_AVAILABLE:
        return {"agents": [], "count": 0, "message": "Agent registry not available"}
    try:
        registry = AgentRegistry.get_instance(DB_PATH)
        agents = registry.list_agents(protocol=protocol, limit=limit)
        stats = registry.get_stats()
        return {"agents": agents, "count": len(agents), "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent registry error: {str(e)}")


@router.get("/api/agents/stats")
async def get_agent_stats():
    """Get agent registry statistics."""
    if not AGENT_REGISTRY_AVAILABLE:
        return {"total_agents": 0, "message": "Agent registry not available"}
    try:
        registry = AgentRegistry.get_instance(DB_PATH)
        return registry.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent stats error: {str(e)}")


@router.get("/api/trust/stats")
async def get_trust_stats():
    """Get trust scoring statistics."""
    if not AGENT_REGISTRY_AVAILABLE:
        return {"total_signals": 0, "message": "Trust scorer not available"}
    try:
        scorer = TrustScorer.get_instance(DB_PATH)
        return scorer.get_trust_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trust stats error: {str(e)}")


@router.get("/api/trust/signals/{agent_id}")
async def get_agent_trust_signals(agent_id: str, limit: int = Query(50, ge=1, le=200)):
    """Get trust signal history for a specific agent."""
    if not AGENT_REGISTRY_AVAILABLE:
        return {"signals": [], "count": 0}
    try:
        scorer = TrustScorer.get_instance(DB_PATH)
        signals = scorer.get_signals(agent_id, limit=limit)
        score = scorer.get_trust_score(agent_id)
        return {"agent_id": agent_id, "trust_score": score, "signals": signals, "count": len(signals)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trust signals error: {str(e)}")
