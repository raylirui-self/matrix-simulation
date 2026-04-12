"""WebSocket real-time tick streaming with delta protocol."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gui.backend.api.state import manager

router = APIRouter(tags=["websocket"])


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
                    cmd = json.loads(msg)
                    if cmd.get("command") == "stop":
                        auto_running = False
                        await websocket.send_json({"type": "stopped"})
                    elif cmd.get("command") == "auto":
                        auto_speed_ms = max(50, cmd.get("speed", 200))
                except asyncio.TimeoutError:
                    pass
            else:
                # Wait for commands
                msg = await websocket.receive_text()
                cmd = json.loads(msg)
                command = cmd.get("command", "")

                if command == "tick":
                    count = min(cmd.get("count", 1), 100)
                    for _ in range(count):
                        delta = await _run_and_send_tick(websocket, run_id, engine)
                        if delta and delta.get("alive_count", 1) == 0:
                            await websocket.send_json({"type": "extinction"})
                            break

                elif command == "auto":
                    auto_running = True
                    auto_speed_ms = max(50, cmd.get("speed", 200))
                    await websocket.send_json({"type": "auto_started", "speed": auto_speed_ms})

                elif command == "state":
                    await _send_full_state(websocket, engine)

                elif command == "stop":
                    auto_running = False

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


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
    ds = getattr(engine, 'dream_state', None)
    dream_payload = {}
    if ds is not None:
        dream_payload = {
            "is_dreaming": bool(ds.is_dreaming),
            "dream_start_tick": ds.dream_start_tick,
            "ghosts": [g.to_dict() for g in getattr(ds, 'ghosts', []) or []],
            "lucid_agent_ids": list(getattr(ds, 'lucid_agent_ids', []) or []),
        }
    if result.dream_stats:
        dream_payload["stats"] = result.dream_stats

    # Haven state summary
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
        haven_payload = {
            "population": len(haven_agents),
            "active_missions": len(active_missions),
            "last_vote_tick": getattr(hs, 'last_vote_tick', 0),
            "stats": result.haven_stats or {},
        }

    # Nested simulations
    nested_payload = {
        "count": len(getattr(engine, 'world_engines', []) or []),
        "stats": result.nested_sim_stats or {},
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
    }


async def _run_and_send_tick(websocket: WebSocket, run_id: str, engine) -> dict:
    """Run one tick and send the delta to the client."""
    prev_alive_ids, prev_agents = capture_prev_state(engine)

    # Run tick
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
