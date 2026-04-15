"""Simulation CRUD and tick endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gui.backend.api.state import manager

router = APIRouter(prefix="/api/sim", tags=["simulation"])


class CreateSimRequest(BaseModel):
    era: Optional[str] = None
    scenario: Optional[str] = None


class TickRequest(BaseModel):
    count: int = 1


@router.post("")
def create_simulation(req: CreateSimRequest):
    """Create a new simulation run."""
    try:
        run_id, engine = manager.create_sim(era=req.era, scenario=req.scenario)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))

    alive = engine.get_alive_agents()
    return {
        "run_id": run_id,
        "tick": engine.state.current_tick,
        "alive_count": len(alive),
        "total_born": engine.state.total_born,
    }


@router.get("/{run_id}")
def get_simulation(run_id: str):
    """Get simulation metadata."""
    engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    alive = engine.get_alive_agents()
    cfg = manager.get_config(run_id)
    return {
        "run_id": run_id,
        "tick": engine.state.current_tick,
        "alive_count": len(alive),
        "total_born": engine.state.total_born,
        "total_died": engine.state.total_died,
        "era_metadata": cfg.era_metadata if cfg else {},
    }


@router.post("/{run_id}/tick")
def advance_ticks(run_id: str, req: TickRequest):
    """Advance the simulation by N ticks. Returns the final tick result."""
    engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    results = []
    for _ in range(min(req.count, 500)):
        result = manager.run_tick(run_id)
        if not result:
            break
        results.append(result)
        if result.alive_count == 0:
            break

    if not results:
        raise HTTPException(status_code=500, detail="Tick failed")

    last = results[-1]
    return {
        "ticks_run": len(results),
        "tick": last.tick,
        "alive_count": last.alive_count,
        "births": sum(r.births for r in results),
        "deaths": sum(r.deaths for r in results),
        "avg_intelligence": last.avg_intelligence,
        "avg_health": last.avg_health,
        "avg_generation": last.avg_generation,
        "phase_counts": last.phase_counts,
        "breakthroughs": [bt for r in results for bt in r.breakthroughs],
        "world_summary": last.world_summary,
        "emotion_stats": last.emotion_stats,
        "belief_stats": last.belief_stats,
        "economy_stats": last.economy_stats,
        "matrix_stats": last.matrix_stats,
        "conflict_stats": last.conflict_stats,
        "communication_stats": last.communication_stats,
    }


@router.get("/{run_id}/state")
def get_full_state(run_id: str):
    """Get the complete simulation state snapshot."""
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    alive = engine.get_alive_agents()
    return {
        "tick": engine.state.current_tick,
        "total_born": engine.state.total_born,
        "total_died": engine.state.total_died,
        "agents": [_agent_summary(a) for a in alive],
        "dead_count": sum(1 for a in engine.agents if not a.alive),
        "world": engine.world.to_dict(),
        "factions": [f.to_dict() for f in engine.factions],
        "wars": [w.to_dict() for w in engine.wars],
        "matrix": engine.matrix_state.to_dict(),
        "protagonist_ids": engine.protagonist_ids,
        "cultural_memory": {
            "skill_floors": {k: round(v, 4) for k, v in engine.cultural_memory.skill_floors.items()},
        },
        "summary": engine.get_population_summary(),
    }


@router.get("/{run_id}/history")
def get_tick_history(run_id: str, offset: int = 0, limit: int = 500):
    """Get tick stat history."""
    history = manager.db.get_tick_history(run_id)
    return {"history": history[offset:offset + limit], "total": len(history)}


# Keys that are safe to mutate mid-run. Anything touching population floors,
# phase-age thresholds, or tech breakthrough tables must go through a fresh
# engine creation because those values are cached at engine construction.
RUNTIME_CONFIG_WHITELIST = {
    "narrator",       # narration cadence / provider
    "emotions",       # decay & contagion tuning
    "beliefs",        # memetic drift rates
    "environment",    # harshness slider (read per-tick)
    "matrix",         # awareness growth / glitch rates (read per-tick)
    "dreams",         # dream cadence
    "observer_effect",
    "archaeology",
}


@router.put("/{run_id}/config")
def update_config(run_id: str, overrides: dict):
    """Update simulation config with runtime overrides.

    Only a whitelisted set of top-level sections may be tweaked mid-run.
    Other sections (population, lifecycle, skills, agency) feed into state
    that is cached at engine construction and cannot be safely mutated
    without a full re-initialization.
    """
    engine = manager.get_engine(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    cfg = manager.get_config(run_id)
    if not cfg:
        raise HTTPException(status_code=500, detail="Config not found")

    if not isinstance(overrides, dict):
        raise HTTPException(status_code=400, detail="overrides must be a JSON object")

    rejected = sorted(k for k in overrides if k not in RUNTIME_CONFIG_WHITELIST)
    if rejected:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update config keys mid-run: {rejected}. "
                   f"Allowed: {sorted(RUNTIME_CONFIG_WHITELIST)}",
        )

    new_cfg = cfg.override(overrides)
    with manager._lock:
        engine.cfg = new_cfg
        manager._configs[run_id] = new_cfg

    return {"status": "ok", "message": "Config updated", "updated_sections": sorted(overrides.keys())}


def _agent_summary(a) -> dict:
    """Lightweight agent representation for the state endpoint.

    Uses ``getattr`` defaults so agents loaded from older snapshots (missing
    Phase 6/7 fields like ``trauma`` or ``dominant_emotion``) still serialize.
    """
    return {
        "id": a.id,
        "x": round(getattr(a, "x", 0.0), 4),
        "y": round(getattr(a, "y", 0.0), 4),
        "sex": getattr(a, "sex", "f"),
        "age": getattr(a, "age", 0),
        "phase": getattr(a, "phase", "adult"),
        "health": round(getattr(a, "health", 0.0), 4),
        "intelligence": round(getattr(a, "intelligence", 0.0), 4),
        "generation": getattr(a, "generation", 0),
        "emotion": getattr(a, "dominant_emotion", "neutral"),
        "awareness": round(getattr(a, "awareness", 0.0), 4),
        "redpilled": getattr(a, "redpilled", False),
        "is_anomaly": getattr(a, "is_anomaly", False),
        "is_sentinel": getattr(a, "is_sentinel", False),
        "is_exile": getattr(a, "is_exile", False),
        "is_protagonist": getattr(a, "is_protagonist", False),
        "protagonist_name": getattr(a, "protagonist_name", None),
        "faction_id": getattr(a, "faction_id", None),
        "wealth": round(getattr(a, "wealth", 0.0), 3),
        "trauma": round(getattr(a, "trauma", 0.0), 3),
        "bonds_count": len(getattr(a, "bonds", []) or []),
    }
