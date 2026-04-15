"""Phase 7: verify the WebSocket tick protocol exposes the new fields
required by the frontend visual overhaul (consciousness phases, program
flags, dream state, haven summary, nested sims, Boltzmann events)."""
from __future__ import annotations

from src.config_loader import SimConfig
from src.engine import SimulationEngine
from gui.backend.api.routes.websocket import (
    build_tick_message,
    capture_prev_state,
)
from gui.backend.api.state import EngineManager


def _bootstrap_engine() -> SimulationEngine:
    cfg = SimConfig.load()
    engine = SimulationEngine(cfg)
    engine.initialize()
    return engine


def _run_one_tick(engine: SimulationEngine):
    """Run a tick directly on the engine (no DB) and return (result, delta_data)."""
    prev_alive_ids, prev_agents = capture_prev_state(engine)
    result = engine.tick()
    mgr = EngineManager.__new__(EngineManager)  # skip __init__ (no DB needed)
    delta_data = mgr.compute_delta(engine, prev_alive_ids, prev_agents)
    return result, delta_data


def test_agent_deltas_include_phase7_fields():
    engine = _bootstrap_engine()
    # Warm up to accumulate some movement
    for _ in range(3):
        _run_one_tick(engine)
    result, delta_data = _run_one_tick(engine)
    deltas = delta_data["agent_deltas"]
    assert deltas, "expected at least one agent delta after movement"
    # Find a non-death, non-birth delta
    movers = [d for d in deltas if not d.get("died")]
    assert movers, "expected move/birth deltas"
    sample = movers[0]
    required = {
        "consciousness_phase",
        "free_will_index",
        "incarnation_count",
        "soul_trap_broken",
        "past_life_memories",
        "is_enforcer",
        "is_broker",
        "is_guardian",
        "is_locksmith",
        "teleport_keys",
        "pleroma_glimpses",
        "location",
    }
    missing = required - set(sample.keys())
    assert not missing, f"delta missing Phase 7 fields: {missing}"


def test_build_tick_message_contains_new_top_level_keys():
    engine = _bootstrap_engine()
    result, delta_data = _run_one_tick(engine)
    msg = build_tick_message(engine, result, delta_data)
    for key in ("dream", "haven", "nested_sims", "boltzmann_events"):
        assert key in msg, f"missing top-level key: {key}"
    # Dream sub-shape
    assert "is_dreaming" in msg["dream"]
    assert "ghosts" in msg["dream"]
    assert "lucid_agent_ids" in msg["dream"]
    # Nested sims count is numeric
    assert isinstance(msg["nested_sims"]["count"], int)
    # Boltzmann events is list
    assert isinstance(msg["boltzmann_events"], list)
    # Matrix still includes demiurge / archons
    assert "demiurge" in msg["matrix"]
    assert "archons" in msg["matrix"]


def test_capture_prev_state_tracks_consciousness_and_program_flags():
    engine = _bootstrap_engine()
    prev_alive_ids, prev_agents = capture_prev_state(engine)
    assert prev_alive_ids, "engine should have alive agents after initialize"
    sample_id = next(iter(prev_alive_ids))
    snap = prev_agents[sample_id]
    assert "consciousness_phase" in snap
    assert "program_flags" in snap
    assert isinstance(snap["program_flags"], tuple)
    assert len(snap["program_flags"]) == 4


def test_world_route_exposes_artifact_flag():
    """Cells returned by /world must carry has_artifact + artifact_count for
    the cycle-reset cinematic overlay to highlight artifact locations."""
    from gui.backend.api.routes import world as world_route

    engine = _bootstrap_engine()
    # Seed an artifact onto a cell so the flag has something to report
    from src.world import Artifact, next_artifact_id
    cell = engine.world.cells[0][0]
    cell.artifacts.append(
        Artifact(
            artifact_id=next_artifact_id(),
            faction_name="test",
            era_tick=0,
            cycle_number=1,
            awareness_level=0.0,
            tech_level=0.0,
            artifact_type="ruin",
        )
    )

    # Register engine so the route can find it
    mgr = world_route.manager
    mgr._engines["test-run"] = engine
    try:
        data = world_route.get_world("test-run")
    finally:
        mgr._engines.pop("test-run", None)

    cells = data["cells"]
    assert any("has_artifact" in c and "artifact_count" in c for c in cells)
    seeded = next(c for c in cells if c["row"] == 0 and c["col"] == 0)
    assert seeded["has_artifact"] is True
    assert seeded["artifact_count"] >= 1


def test_delta_emission_on_consciousness_phase_change():
    """If an agent's consciousness_phase changes with zero movement, a
    delta should still be emitted."""
    engine = _bootstrap_engine()
    prev_alive_ids, prev_agents = capture_prev_state(engine)
    # Mutate one agent's consciousness_phase without moving it
    target = next(a for a in engine.agents if a.alive)
    target.consciousness_phase = "self_aware" if target.consciousness_phase != "self_aware" else "lucid"

    mgr = EngineManager.__new__(EngineManager)
    delta_data = mgr.compute_delta(engine, prev_alive_ids, prev_agents)
    ids_with_delta = {d["id"] for d in delta_data["agent_deltas"] if not d.get("died")}
    assert target.id in ids_with_delta, (
        "phase change should force a delta emission even without movement"
    )
