"""Agent query endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from gui.backend.api.state import manager

router = APIRouter(prefix="/api/sim/{run_id}/agents", tags=["agents"])


@router.get("")
def list_agents(
    run_id: str,
    alive_only: bool = True,
    phase: Optional[str] = None,
    faction_id: Optional[int] = None,
    min_awareness: Optional[float] = None,
    protagonist_only: bool = False,
    sort_by: str = "id",
    offset: int = 0,
    limit: int = 100,
):
    """List agents with filtering and pagination."""
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    agents = engine.agents
    if alive_only:
        agents = [a for a in agents if a.alive]
    if phase:
        agents = [a for a in agents if a.phase == phase]
    if faction_id is not None:
        agents = [a for a in agents if a.faction_id == faction_id]
    if min_awareness is not None:
        agents = [a for a in agents if a.awareness >= min_awareness]
    if protagonist_only:
        agents = [a for a in agents if a.is_protagonist]

    # Sort
    sort_keys = {
        "id": lambda a: a.id,
        "age": lambda a: a.age,
        "health": lambda a: -a.health,
        "intelligence": lambda a: -a.intelligence,
        "awareness": lambda a: -a.awareness,
        "wealth": lambda a: -a.wealth,
        "generation": lambda a: -a.generation,
    }
    key_fn = sort_keys.get(sort_by, sort_keys["id"])
    agents.sort(key=key_fn)

    total = len(agents)
    page = agents[offset:offset + limit]

    return {
        "agents": [_agent_brief(a) for a in page],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{agent_id}")
def get_agent(run_id: str, agent_id: int):
    """Get full agent details."""
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    agent = next((a for a in engine.agents if a.id == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Resolve bond target names for display
    agents_by_id = {a.id: a for a in engine.agents}
    bonds = []
    for b in agent.bonds:
        target = agents_by_id.get(b.target_id)
        bonds.append({
            **b.to_dict(),
            "target_alive": target.alive if target else False,
            "target_name": target.protagonist_name if target and target.is_protagonist else None,
        })

    # Find family
    parents = [agents_by_id.get(pid) for pid in agent.parent_ids]
    children = [agents_by_id.get(cid) for cid in agent.child_ids]

    return {
        **agent.to_dict(),
        "dominant_emotion": agent.dominant_emotion,
        "emotional_intensity": round(agent.emotional_intensity, 3),
        "belief_extremism": round(agent.belief_extremism, 3),
        "bonds_resolved": bonds,
        "family": {
            "parents": [
                {"id": p.id, "alive": p.alive, "name": p.protagonist_name}
                for p in parents if p
            ],
            "children": [
                {"id": c.id, "alive": c.alive, "age": c.age, "name": c.protagonist_name}
                for c in children if c
            ],
        },
    }


def _agent_brief(a) -> dict:
    """Compact agent representation for list endpoints."""
    return {
        "id": a.id,
        "x": round(a.x, 4),
        "y": round(a.y, 4),
        "sex": a.sex,
        "age": a.age,
        "phase": a.phase,
        "health": round(a.health, 4),
        "intelligence": round(a.intelligence, 4),
        "generation": a.generation,
        "emotion": a.dominant_emotion,
        "awareness": round(a.awareness, 4),
        "redpilled": a.redpilled,
        "is_anomaly": a.is_anomaly,
        "is_sentinel": a.is_sentinel,
        "is_protagonist": a.is_protagonist,
        "protagonist_name": a.protagonist_name,
        "faction_id": a.faction_id,
        "wealth": round(a.wealth, 3),
        "bonds_count": len(a.bonds),
    }
