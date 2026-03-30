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


async def _run_and_send_tick(websocket: WebSocket, run_id: str, engine) -> dict:
    """Run one tick and send the delta to the client."""
    # Capture pre-tick state
    prev_agents = {}
    prev_alive_ids = set()
    for a in engine.agents:
        if a.alive:
            prev_agents[a.id] = {"x": a.x, "y": a.y, "health": a.health}
            prev_alive_ids.add(a.id)

    # Run tick
    result = manager.run_tick(run_id)
    if not result:
        return {"alive_count": 0}

    # Compute deltas
    delta_data = manager.compute_delta(engine, prev_alive_ids, prev_agents)

    # Build bond deltas (simplified — send bonds formed/broken count)
    bond_summary = {
        "formed": result.bonds_formed,
        "decayed": result.bonds_decayed,
    }

    # Build tick message
    msg = {
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
    }

    await websocket.send_json(msg)
    return {"alive_count": result.alive_count}


async def _send_full_state(websocket: WebSocket, engine):
    """Send a complete state sync."""
    alive = engine.get_alive_agents()
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
        })

    msg = {
        "type": "state_sync",
        "tick": engine.state.current_tick,
        "agents": agents,
        "matrix": engine.matrix_state.to_dict(),
        "factions": [f.to_dict() for f in engine.factions],
        "world_summary": engine.world.summary(),
        "protagonist_ids": engine.protagonist_ids,
    }
    await websocket.send_json(msg)
