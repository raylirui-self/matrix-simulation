"""World state endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from gui.backend.api.state import manager

router = APIRouter(prefix="/api/sim/{run_id}/world", tags=["world"])


@router.get("")
def get_world(run_id: str):
    """Get full world grid state."""
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    grid = engine.world
    cells = []
    for row_idx, row in enumerate(grid.cells):
        for col_idx, cell in enumerate(row):
            cells.append({
                "row": row_idx,
                "col": col_idx,
                "terrain": cell.terrain,
                "resources": round(cell.current_resources, 3),
                "effective_resources": round(cell.effective_resources, 3),
                "base_resources": round(cell.base_resources, 3),
                "carrying_capacity": cell.carrying_capacity,
                "effective_capacity": cell.effective_capacity,
                "agent_count": cell.agent_count,
                "pressure": round(cell.pressure, 3),
                "harshness_modifier": round(cell.harshness_modifier, 3),
                "skill_bonus": cell.skill_bonus,
                "unlocked_techs": [t.name for t in cell.unlocked_techs],
            })

    # Agents grouped by cell
    alive = engine.get_alive_agents()
    grid_size = grid.size
    agent_positions = []
    for a in alive:
        row = max(0, min(grid_size - 1, int(a.y * grid_size)))
        col = max(0, min(grid_size - 1, int(a.x * grid_size)))
        agent_positions.append({
            "id": a.id,
            "row": row, "col": col,
            "x": round(a.x, 4), "y": round(a.y, 4),
            "phase": a.phase,
            "intelligence": round(a.intelligence, 4),
            "emotion": a.dominant_emotion,
            "awareness": round(a.awareness, 4),
            "is_protagonist": a.is_protagonist,
            "is_sentinel": a.is_sentinel,
        })

    return {
        "grid_size": grid_size,
        "cells": cells,
        "global_techs": list(grid.global_techs),
        "summary": grid.summary(),
        "agent_positions": agent_positions,
    }


@router.get("/bonds")
def get_bonds(run_id: str, min_strength: float = 0.1, limit: int = 200):
    """Get top bonds for network visualization."""
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    alive = engine.get_alive_agents()
    alive_ids = {a.id for a in alive}
    pos_lookup = {a.id: (a.x, a.y) for a in alive}

    all_bonds = []
    seen = set()
    for a in alive:
        for b in a.bonds:
            if b.strength < min_strength:
                continue
            if b.target_id not in alive_ids:
                continue
            pair = tuple(sorted((a.id, b.target_id)))
            if pair in seen:
                continue
            seen.add(pair)
            tx, ty = pos_lookup.get(b.target_id, (0, 0))
            all_bonds.append({
                "source_id": a.id,
                "target_id": b.target_id,
                "type": b.bond_type,
                "strength": round(b.strength, 3),
                "source_x": round(a.x, 4), "source_y": round(a.y, 4),
                "target_x": round(tx, 4), "target_y": round(ty, 4),
            })

    # Sort by strength descending, take top N
    all_bonds.sort(key=lambda b: -b["strength"])
    return {"bonds": all_bonds[:limit], "total": len(all_bonds)}
