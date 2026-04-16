"""WebSocket real-time tick streaming with delta protocol."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gui.backend.api.state import manager

logger = logging.getLogger("nexus.websocket")

router = APIRouter(tags=["websocket"])


async def _safe_send_error(ws: WebSocket, code: str, detail: str = "") -> None:
    """Best-effort error frame — swallow send failures (socket may be closed)."""
    try:
        await ws.send_json({"type": "error", "code": code, "detail": detail})
    except Exception:
        pass


def _parse_command(raw: str, run_id: str) -> dict | None:
    """Parse a client frame as JSON. Returns None on malformed input."""
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            logger.warning("ws run_id=%s non-object frame: %r", run_id, raw[:200])
            return None
        return obj
    except json.JSONDecodeError as exc:
        logger.warning("ws run_id=%s invalid json: %s frame=%r", run_id, exc, raw[:200])
        return None


@router.websocket("/ws/sim/{run_id}")
async def sim_websocket(websocket: WebSocket, run_id: str):
    """Real-time simulation tick stream.

    Client sends: {"command": "tick", "count": 1}
                  {"command": "auto", "speed": 100}  (ms between ticks)
                  {"command": "stop"}
                  {"command": "state"}  (request full state sync)
    Server sends: tick deltas, events, matrix state per tick.
    """
    await websocket.accept()

    engine = manager.load_sim(run_id)
    if not engine:
        await websocket.send_json({"type": "error", "message": "Simulation not found"})
        await websocket.close()
        return

    auto_running = False
    auto_speed_ms = 200

    try:
        while True:
            if auto_running:
                # Run a tick and send delta
                delta = await _run_and_send_tick(websocket, run_id, engine)
                if delta and delta.get("alive_count", 1) == 0:
                    auto_running = False
                    await websocket.send_json({"type": "extinction"})

                # Check for incoming commands without blocking
                try:
                    msg = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=auto_speed_ms / 1000.0,
                    )
                except asyncio.TimeoutError:
                    continue
                cmd = _parse_command(msg, run_id)
                if cmd is None:
                    await _safe_send_error(websocket, "invalid_json", "command frame was not valid JSON")
                    continue
                if cmd.get("command") == "stop":
                    auto_running = False
                    await websocket.send_json({"type": "stopped"})
                elif cmd.get("command") == "auto":
                    auto_speed_ms = max(50, int(cmd.get("speed", 200)))
            else:
                # Wait for commands
                msg = await websocket.receive_text()
                cmd = _parse_command(msg, run_id)
                if cmd is None:
                    await _safe_send_error(websocket, "invalid_json", "command frame was not valid JSON")
                    continue
                command = cmd.get("command", "")

                if command == "tick":
                    count = min(int(cmd.get("count", 1)), 100)
                    for _ in range(count):
                        delta = await _run_and_send_tick(websocket, run_id, engine)
                        if delta and delta.get("alive_count", 1) == 0:
                            await websocket.send_json({"type": "extinction"})
                            break

                elif command == "auto":
                    auto_running = True
                    auto_speed_ms = max(50, int(cmd.get("speed", 200)))
                    await websocket.send_json({"type": "auto_started", "speed": auto_speed_ms})

                elif command == "state":
                    await _send_full_state(websocket, engine)

                elif command == "stop":
                    auto_running = False

                else:
                    await _safe_send_error(websocket, "unknown_command", f"unknown command: {command!r}")

    except WebSocketDisconnect:
        logger.info("ws run_id=%s client disconnected", run_id)
    except Exception:
        logger.exception("ws run_id=%s unhandled error in tick loop", run_id)
        await _safe_send_error(websocket, "internal_error", "see server logs")


def capture_prev_state(engine) -> tuple[set, dict]:
    """Snapshot per-agent state used to gate delta emission next tick."""
    prev_agents: dict = {}
    prev_alive_ids: set = set()
    for a in engine.agents:
        if a.alive:
            prev_agents[a.id] = {
                "x": a.x,
                "y": a.y,
                "health": a.health,
                "consciousness_phase": getattr(a, 'consciousness_phase', 'bicameral'),
                "program_flags": (
                    getattr(a, 'is_enforcer', False),
                    getattr(a, 'is_broker', False),
                    getattr(a, 'is_guardian', False),
                    getattr(a, 'is_locksmith', False),
                ),
            }
            prev_alive_ids.add(a.id)
    return prev_alive_ids, prev_agents


def build_tick_message(engine, result, delta_data: dict) -> dict:
    """Assemble the WebSocket tick payload. Pure function for testability."""
    bond_summary = {
        "formed": result.bonds_formed,
        "decayed": result.bonds_decayed,
    }

    # Dream state (from engine.dream_state + result.dream_stats)
    # Phase 7B: enrich each ghost dict with `bonded_living_ids` so the frontend
    # can draw the memory-transfer threads to living bonded agents without
    # doing a second round-trip for bond data. Only computed when ghosts are
    # present (cheap O(N) index over living agents).
    ds = getattr(engine, 'dream_state', None)
    dream_payload = {}
    if ds is not None:
        ghost_list = getattr(ds, 'ghosts', []) or []
        ghost_dicts = [g.to_dict() for g in ghost_list]
        if ghost_dicts:
            bonded_to: dict[int, list[int]] = {}
            for a in engine.agents:
                if not getattr(a, 'alive', False):
                    continue
                seen: set = set()
                for b in getattr(a, 'bonds', []) or []:
                    tgt = getattr(b, 'target_id', None)
                    if tgt is None or tgt in seen:
                        continue
                    seen.add(tgt)
                    bonded_to.setdefault(tgt, []).append(a.id)
            for gd in ghost_dicts:
                gd["bonded_living_ids"] = bonded_to.get(gd["source_agent_id"], [])
        dream_payload = {
            "is_dreaming": bool(ds.is_dreaming),
            "dream_start_tick": ds.dream_start_tick,
            "ghosts": ghost_dicts,
            "lucid_agent_ids": list(getattr(ds, 'lucid_agent_ids', []) or []),
        }
    if result.dream_stats:
        dream_payload["stats"] = result.dream_stats

    # Haven state summary
    # Phase 7B: also emit a simplified grid (cells + size + agent counts) and
    # `last_vote_outcome` so the Haven PiP can render without extra REST calls.
    haven_payload = None
    hs = getattr(engine, 'haven_state', None)
    if hs is not None:
        haven_agents = [
            a for a in engine.agents
            if getattr(a, 'alive', False)
            and getattr(a, 'location', 'simulation') == 'haven'
        ]
        active_missions = [
            m for m in getattr(hs, 'missions', []) or []
            if not getattr(m, 'completed', False) and not getattr(m, 'failed', False)
        ]
        grid = getattr(hs, 'grid', None)
        grid_size = getattr(grid, 'size', 0) if grid is not None else 0
        # Live per-cell agent count keyed by (row, col)
        cell_counts: dict[tuple[int, int], int] = {}
        if grid_size > 0:
            for a in haven_agents:
                r = min(grid_size - 1, max(0, int(a.y * grid_size)))
                c = min(grid_size - 1, max(0, int(a.x * grid_size)))
                cell_counts[(r, c)] = cell_counts.get((r, c), 0) + 1
        grid_cells: list[dict] = []
        if grid is not None:
            for row in grid.cells:
                for cell in row:
                    grid_cells.append({
                        "row": cell.row,
                        "col": cell.col,
                        "resources": round(cell.current_resources, 3),
                        "base_resources": round(cell.base_resources, 3),
                        "harshness": cell.harshness,
                        "agent_count": cell_counts.get((cell.row, cell.col), 0),
                    })
        cv = getattr(hs, 'council_votes', []) or []
        last_vote_outcome = cv[-1].outcome if cv else None
        haven_payload = {
            "population": len(haven_agents),
            "active_missions": len(active_missions),
            "last_vote_tick": getattr(hs, 'last_vote_tick', 0),
            "last_vote_outcome": last_vote_outcome,
            "grid_size": grid_size,
            "grid_cells": grid_cells,
            "agents": [
                {
                    "id": a.id,
                    "x": round(a.x, 4),
                    "y": round(a.y, 4),
                    "emotion": getattr(a, 'dominant_emotion', 'happiness'),
                    "health": round(a.health, 4),
                }
                for a in haven_agents
            ],
            "stats": result.haven_stats or {},
        }

    # Nested simulations — Phase 7C: include per-engine detail for miniature
    # window rendering.  Only the top-3 by max sub-agent awareness are sent.
    world_engines = getattr(engine, 'world_engines', []) or []
    engine_details: list[dict] = []
    grid_size = engine.world.size if hasattr(engine, 'world') else 8
    for we in world_engines:
        ss = we.sub_sim
        if ss is None:
            continue
        alive_sub = ss.get_alive()
        max_aw = max((a.awareness for a in alive_sub), default=0.0)
        has_paradox = any(a.recursive_detected for a in alive_sub)
        # Look up builder agent position (may be dead)
        builder = next(
            (a for a in engine.agents if a.id == we.builder_id), None
        )
        bx = round(builder.x, 4) if builder else (we.cell_col + 0.5) / grid_size
        by = round(builder.y, 4) if builder else (we.cell_row + 0.5) / grid_size
        # Lightweight sub-agent grid (positions + awareness only)
        sub_agents = [
            {"x": round(a.x, 3), "y": round(a.y, 3), "aw": round(a.awareness, 3)}
            for a in alive_sub[:20]
        ]
        engine_details.append({
            "engine_id": we.engine_id,
            "builder_id": we.builder_id,
            "builder_x": bx,
            "builder_y": by,
            "cell_row": we.cell_row,
            "cell_col": we.cell_col,
            "sub_grid_size": ss.grid_size,
            "alive_count": len(alive_sub),
            "max_awareness": round(max_aw, 4),
            "has_paradox": has_paradox,
            "sub_agents": sub_agents,
        })
    # Sort by max_awareness desc, keep top 3
    engine_details.sort(key=lambda e: -e["max_awareness"])
    engine_details = engine_details[:3]

    nested_payload = {
        "count": len(world_engines),
        "stats": result.nested_sim_stats or {},
        "engines": engine_details,
    }

    # Boltzmann brain events (pulled out of matrix_stats)
    boltzmann_events = []
    bb_id = (result.matrix_stats or {}).get("boltzmann_brain")
    if bb_id is not None:
        boltzmann_events.append({"agent_id": bb_id, "tick": result.tick})

    return {
        "type": "tick",
        "tick": result.tick,
        "stats": {
            "alive_count": result.alive_count,
            "births": result.births,
            "deaths": result.deaths,
            "avg_intelligence": result.avg_intelligence,
            "avg_health": result.avg_health,
            "avg_generation": result.avg_generation,
            "phase_counts": result.phase_counts,
        },
        "agent_deltas": delta_data["agent_deltas"],
        "bonds": bond_summary,
        "breakthroughs": result.breakthroughs,
        "matrix": result.matrix_stats,
        "emotions": result.emotion_stats,
        "economy": result.economy_stats,
        "conflict": result.conflict_stats,
        "wars": [w.to_dict() for w in engine.wars],
        "death_causes": result.death_causes,
        "age_distribution": result.age_distribution,
        "tech_progress": result.tech_progress,
        "belief_stats": result.belief_stats,
        "cinematic_events": result.cinematic_events,
        "communication": result.communication_stats,
        "dream": dream_payload,
        "haven": haven_payload,
        "nested_sims": nested_payload,
        "boltzmann_events": boltzmann_events,
        "reincarnation_events": result.reincarnation_events or [],
    }


async def _run_and_send_tick(websocket: WebSocket, run_id: str, engine) -> dict:
    """Run one tick and send the delta to the client.

    Holds the per-run async lock across snapshot -> tick -> delta computation
    so two WebSocket clients sharing a run_id cannot interleave ticks.
    """
    async with manager.get_engine_lock_async(run_id):
        prev_alive_ids, prev_agents = capture_prev_state(engine)

        # Run tick (manager.run_tick also holds the sync lock for REST callers)
        result = manager.run_tick(run_id)
        if not result:
            return {"alive_count": 0}

        delta_data = manager.compute_delta(engine, prev_alive_ids, prev_agents)
        msg = build_tick_message(engine, result, delta_data)

    await websocket.send_json(msg)
    return {"alive_count": result.alive_count}


async def _send_full_state(websocket: WebSocket, engine):
    """Send a complete state sync."""
    alive = engine.get_alive_agents()
    glimpse_counts: dict[int, int] = {}
    for g in getattr(engine.matrix_state, 'pleroma_glimpses', []) or []:
        aid = getattr(g, 'agent_id', None)
        if aid is None and isinstance(g, dict):
            aid = g.get('agent_id')
        if aid is not None:
            glimpse_counts[aid] = glimpse_counts.get(aid, 0) + 1

    agents = []
    for a in alive:
        agents.append({
            "id": a.id,
            "x": round(a.x, 4), "y": round(a.y, 4),
            "sex": a.sex, "age": a.age, "phase": a.phase,
            "health": round(a.health, 4),
            "intelligence": round(a.intelligence, 4),
            "generation": a.generation,
            "emotion": a.dominant_emotion,
            "awareness": round(a.awareness, 4),
            "redpilled": a.redpilled,
            "is_anomaly": a.is_anomaly,
            "is_sentinel": a.is_sentinel,
            "is_exile": a.is_exile,
            "is_protagonist": a.is_protagonist,
            "protagonist_name": a.protagonist_name,
            "faction_id": a.faction_id,
            "wealth": round(a.wealth, 3),
            "trauma": round(a.trauma, 3),
            "consciousness_phase": getattr(a, 'consciousness_phase', 'bicameral'),
            "free_will_index": round(getattr(a, 'free_will_index', 0.0), 3),
            "incarnation_count": getattr(a, 'incarnation_count', 1),
            "soul_trap_broken": getattr(a, 'soul_trap_broken', False),
            "past_life_memories": len(getattr(a, 'past_life_memories', []) or []),
            "is_enforcer": getattr(a, 'is_enforcer', False),
            "is_broker": getattr(a, 'is_broker', False),
            "is_guardian": getattr(a, 'is_guardian', False),
            "is_locksmith": getattr(a, 'is_locksmith', False),
            "teleport_keys": len(getattr(a, 'teleport_keys', []) or []),
            "location": getattr(a, 'location', 'simulation'),
            "pleroma_glimpses": glimpse_counts.get(a.id, 0),
        })

    ds = getattr(engine, 'dream_state', None)
    dream_payload = ds.to_dict() if ds is not None else {}

    hs = getattr(engine, 'haven_state', None)
    haven_payload = None
    if hs is not None:
        haven_agents = [a for a in engine.agents if a.alive and getattr(a, 'location', 'simulation') == 'haven']
        haven_payload = {
            "population": len(haven_agents),
            "active_missions": sum(
                1 for m in getattr(hs, 'missions', []) or []
                if not getattr(m, 'completed', False) and not getattr(m, 'failed', False)
            ),
            "last_vote_tick": getattr(hs, 'last_vote_tick', 0),
        }

    msg = {
        "type": "state_sync",
        "tick": engine.state.current_tick,
        "agents": agents,
        "matrix": engine.matrix_state.to_dict(),
        "factions": [f.to_dict() for f in engine.factions],
        "wars": [w.to_dict() for w in engine.wars],
        "world_summary": engine.world.summary(),
        "protagonist_ids": engine.protagonist_ids,
        "dream": dream_payload,
        "haven": haven_payload,
        "nested_sims": {"count": len(getattr(engine, 'world_engines', []) or [])},
    }
    await websocket.send_json(msg)
