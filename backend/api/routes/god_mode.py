"""God mode action endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.state import manager
from src.agents import create_agent
from src.engine import WorldEvent

router = APIRouter(prefix="/api/sim/{run_id}/god", tags=["god_mode"])


class GodAction(BaseModel):
    action: str
    target_id: Optional[int] = None
    params: dict = {}


@router.post("")
def god_mode(run_id: str, req: GodAction):
    """Execute a god mode action."""
    engine = manager.get_engine(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    cfg = manager.get_config(run_id)
    tick = engine.state.current_tick

    if req.action == "spawn":
        a = create_agent(cfg)
        a.x = req.params.get("x", 0.5)
        a.y = req.params.get("y", 0.5)
        engine.agents.append(a)
        engine.state.total_born += 1
        return {"status": "ok", "message": f"Spawned agent #{a.id}", "agent_id": a.id}

    elif req.action == "kill":
        if not req.target_id:
            raise HTTPException(status_code=400, detail="target_id required")
        agent = next((a for a in engine.agents if a.id == req.target_id and a.alive), None)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found or already dead")
        agent.alive = False
        agent.health = 0
        engine.state.total_died += 1
        return {"status": "ok", "message": f"Killed agent #{req.target_id}"}

    elif req.action == "event":
        name = req.params.get("name", "Divine Intervention")
        desc = req.params.get("description", "The heavens tremble.")
        effects = req.params.get("effects", {"health_delta": -0.1, "target": "all"})
        event = WorldEvent(tick=tick, name=name, description=desc, effects=effects)
        engine.queue_event(event)
        return {"status": "ok", "message": f"Queued event: {name}"}

    elif req.action == "whisper":
        if not req.target_id:
            raise HTTPException(status_code=400, detail="target_id required")
        agent = next((a for a in engine.agents if a.id == req.target_id and a.alive), None)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        message = req.params.get("message", "Wake up...")
        agent.add_memory(tick, f"[WHISPER FROM ABOVE]: {message}")
        agent.awareness = min(1.0, agent.awareness + req.params.get("awareness_boost", 0.05))
        return {"status": "ok", "message": f"Whispered to agent #{req.target_id}"}

    elif req.action == "modify":
        if not req.target_id:
            raise HTTPException(status_code=400, detail="target_id required")
        agent = next((a for a in engine.agents if a.id == req.target_id and a.alive), None)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        mods = req.params
        if "health" in mods:
            agent.health = max(0.0, min(1.0, mods["health"]))
        if "awareness" in mods:
            agent.awareness = max(0.0, min(1.0, mods["awareness"]))
        if "wealth" in mods:
            agent.wealth = max(0.0, mods["wealth"])
        if "redpilled" in mods:
            agent.redpilled = bool(mods["redpilled"])
        for emo in ["happiness", "fear", "anger", "grief", "hope"]:
            if emo in mods:
                agent.emotions[emo] = max(0.0, min(1.0, mods[emo]))
        return {"status": "ok", "message": f"Modified agent #{req.target_id}"}

    elif req.action == "add_resources":
        row = req.params.get("row", 0)
        col = req.params.get("col", 0)
        amount = req.params.get("amount", 0.5)
        try:
            cell = engine.world.cells[row][col]
            cell.current_resources = min(2.0, cell.current_resources + amount)
            return {"status": "ok", "message": f"Added {amount} resources to cell ({row},{col})"}
        except IndexError:
            raise HTTPException(status_code=400, detail="Invalid cell coordinates")

    elif req.action == "plague":
        severity = req.params.get("severity", 0.3)
        event = WorldEvent(
            tick=tick, name="Divine Plague",
            description="A mysterious illness sweeps the land.",
            effects={"health_delta": -severity, "target": "all"},
        )
        engine.queue_event(event)
        return {"status": "ok", "message": f"Plague unleashed (severity: {severity})"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")
