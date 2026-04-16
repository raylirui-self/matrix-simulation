"""World state endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from gui.backend.api.state import manager
from src.communication import get_language_state

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
                "has_artifact": bool(cell.artifacts),
                "artifact_count": len(cell.artifacts),
                "artifacts": [
                    {
                        "type": a.artifact_type,
                        "cycle_number": a.cycle_number,
                        "faction_name": a.faction_name,
                    }
                    for a in (cell.artifacts or [])[:8]  # cap per cell
                ],
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


@router.get("/language")
def get_language_tree(run_id: str):
    """Language evolution tree: dialect divergence, concept usage, encryption arms race.

    Returns a tree structure where each faction is a branch diverging from a
    common root.  Branch thickness = living speaker count, dead factions are
    marked extinct.  Language artifacts are annotated as preserved branches.
    """
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    lang = get_language_state()
    alive = engine.get_alive_agents()
    alive_faction_ids = {a.faction_id for a in alive if a.faction_id is not None}

    # Count living speakers per faction
    speaker_counts: dict[int, int] = {}
    for a in alive:
        if a.faction_id is not None:
            speaker_counts[a.faction_id] = speaker_counts.get(a.faction_id, 0) + 1

    # Build faction lookup
    faction_map = {f.id: f for f in engine.factions}

    # Language artifact annotations (preserved dead-branch languages)
    la_by_faction: dict[int, list[dict]] = {}
    for la in getattr(engine, 'language_artifacts', []) or []:
        la_by_faction.setdefault(la.faction_id, []).append({
            "faction_name": la.faction_name,
            "cycle_number": la.cycle_number,
            "concept_count": la.concept_count,
            "contains_awareness_clues": la.contains_awareness_clues,
        })

    # Build tree branches
    branches = []
    all_dialect_ids = set(int(k) for k in lang.get("faction_dialects", {}))
    all_faction_ids = alive_faction_ids | all_dialect_ids
    for fid in sorted(all_faction_ids):
        fid_str = str(fid)
        dialect_offset = lang.get("faction_dialects", {}).get(fid_str, 0.0)
        concept_usage = lang.get("faction_concept_usage", {}).get(fid_str, {})
        speakers = speaker_counts.get(fid, 0)
        extinct = fid not in alive_faction_ids
        faction = faction_map.get(fid)
        name = getattr(faction, 'name', f"Faction #{fid}") if faction else f"Faction #{fid}"
        branches.append({
            "faction_id": fid,
            "name": name,
            "dialect_offset": round(dialect_offset, 4),
            "concept_usage": concept_usage,
            "speaker_count": speakers,
            "extinct": extinct,
            "language_artifacts": la_by_faction.get(fid, []),
        })

    return {
        "branches": branches,
        "encryption_level": round(lang.get("resistance_encryption_level", 0.5), 4),
        "decryption_level": round(lang.get("sentinel_decryption_level", 0.3), 4),
        "current_tick": engine.state.current_tick,
        "cycle_number": engine.matrix_state.cycle_number,
    }
