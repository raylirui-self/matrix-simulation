"""God mode action endpoints."""
from __future__ import annotations

import random
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gui.backend.api.state import manager
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
    if not cfg:
        raise HTTPException(status_code=500, detail="Config not found")
    tick = engine.state.current_tick

    if req.action == "spawn":
        a = create_agent(cfg)
        a.x = max(0.0, min(1.0, req.params.get("x", 0.5)))
        a.y = max(0.0, min(1.0, req.params.get("y", 0.5)))
        engine.agents.append(a)
        engine.state.total_born += 1
        return {"status": "ok", "message": f"Spawned agent #{a.id}", "agent_id": a.id}

    elif req.action == "spawn_n":
        count = min(req.params.get("count", 10), 50)
        ids = []
        for _ in range(count):
            a = create_agent(cfg)
            a.x = random.random()
            a.y = random.random()
            engine.agents.append(a)
            engine.state.total_born += 1
            ids.append(a.id)
        return {"status": "ok", "message": f"Spawned {count} agents", "agent_ids": ids}

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
        if "wealth_add" in mods:
            agent.wealth = max(0.0, agent.wealth + mods["wealth_add"])
        if "redpilled" in mods:
            agent.redpilled = bool(mods["redpilled"])
        for emo in ["happiness", "fear", "anger", "grief", "hope"]:
            if emo in mods:
                agent.emotions[emo] = max(0.0, min(1.0, mods[emo]))
        return {"status": "ok", "message": f"Modified agent #{req.target_id}"}

    elif req.action == "prophet":
        if not req.target_id:
            raise HTTPException(status_code=400, detail="target_id required")
        agent = next((a for a in engine.agents if a.id == req.target_id and a.alive), None)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        agent.traits.charisma = 0.95
        strongest_axis = max(agent.beliefs, key=lambda k: abs(agent.beliefs[k]))
        direction = 1.0 if agent.beliefs[strongest_axis] >= 0 else -1.0
        agent.beliefs[strongest_axis] = direction * 0.95
        agent.add_memory(tick, "A vision of absolute truth. I must spread the word.")
        return {"status": "ok", "message": f"Agent #{req.target_id} is now a prophet"}

    elif req.action == "protagonist":
        if not req.target_id:
            raise HTTPException(status_code=400, detail="target_id required")
        agent = next((a for a in engine.agents if a.id == req.target_id), None)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        if req.target_id not in engine.protagonist_ids:
            engine.protagonist_ids.append(req.target_id)
            if len(engine.protagonist_ids) > 5:
                removed = engine.protagonist_ids.pop(0)
                old = next((a for a in engine.agents if a.id == removed), None)
                if old:
                    old.is_protagonist = False
        agent.is_protagonist = True
        if not agent.protagonist_name:
            agent.protagonist_name = f"Agent-{agent.id}"
        return {"status": "ok", "message": f"Now tracking agent #{req.target_id} as protagonist"}

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

    elif req.action == "bounty":
        amount = req.params.get("amount", 0.5)
        for row in engine.world.cells:
            for cell in row:
                cell.current_resources = min(2.0, cell.current_resources + amount)
        return {"status": "ok", "message": f"Bounty granted: +{amount} resources to all cells"}

    elif req.action == "famine":
        resource_factor = req.params.get("resource_factor", 0.3)
        for row in engine.world.cells:
            for cell in row:
                cell.current_resources *= resource_factor
        event = WorldEvent(
            tick=tick, name="Great Famine",
            description="Resources vanish across the land.",
            effects={"health_delta": -0.15, "target": "all"},
        )
        engine.queue_event(event)
        return {"status": "ok", "message": f"Famine strikes (resources to {resource_factor * 100:.0f}%)"}

    elif req.action == "meteor":
        grid_size = engine.world.size
        row = random.randint(0, grid_size - 1)
        col = random.randint(0, grid_size - 1)
        # Destroy target cell
        engine.world.cells[row][col].current_resources = 0.0
        # Damage neighbors
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < grid_size and 0 <= nc < grid_size and (dr != 0 or dc != 0):
                    engine.world.cells[nr][nc].current_resources *= 0.5
        event = WorldEvent(
            tick=tick, name="Meteor Strike",
            description=f"A meteor slams into cell ({row},{col})!",
            effects={"health_delta": -0.2, "target": "all"},
        )
        engine.queue_event(event)
        return {"status": "ok", "message": f"Meteor struck cell ({row},{col})"}

    elif req.action == "blessing":
        for a in engine.get_alive_agents():
            a.health = min(1.0, a.health + 0.2)
            for skill in a.skills:
                a.skills[skill] = min(1.0, a.skills[skill] + 0.02)
        return {"status": "ok", "message": "Divine blessing bestowed on all agents"}

    elif req.action == "plague":
        severity = min(1.0, max(0.0, req.params.get("severity", 0.3)))
        event = WorldEvent(
            tick=tick, name="Divine Plague",
            description="A mysterious illness sweeps the land.",
            effects={"health_delta": -severity, "target": "all"},
        )
        engine.queue_event(event)
        return {"status": "ok", "message": f"Plague unleashed (severity: {severity})"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")
