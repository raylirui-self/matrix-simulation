"""In-memory simulation engine management for the API server."""
from __future__ import annotations

import threading
from typing import Optional

from src.config_loader import SimConfig
from src.engine import SimulationEngine, TickResult
from src.persistence import SimulationDB
from src.agents import set_id_counter, get_id_counter
from src.beliefs import set_faction_id_counter, get_faction_id_counter
from src.communication import set_info_id_counter, get_info_id_counter


def _action_str(action) -> str | None:
    """Normalize a stored (x, y) action tuple into a compact string."""
    if action is None:
        return None
    if isinstance(action, (tuple, list)) and len(action) >= 2:
        return f"{int(action[0])},{int(action[1])}"
    return str(action)


class EngineManager:
    """Manages simulation engine instances and persistence."""

    def __init__(self, db_path: str = "output/simulation.db"):
        self.db = SimulationDB(db_path)
        self._engines: dict[str, SimulationEngine] = {}
        self._configs: dict[str, SimConfig] = {}
        self._lock = threading.Lock()
        self._tick_listeners: dict[str, list] = {}  # run_id -> list of queues

    def create_sim(self, era: Optional[str] = None,
                   scenario: Optional[str] = None) -> tuple[str, SimulationEngine]:
        cfg = SimConfig.load(scenario=scenario, era=era)
        engine = SimulationEngine(cfg)
        engine.initialize()

        run_id = self.db.create_run(cfg)
        engine.state.run_id = run_id
        self.db.save_snapshot(run_id, engine)
        self.db.flush()

        with self._lock:
            self._engines[run_id] = engine
            self._configs[run_id] = cfg

        return run_id, engine

    def load_sim(self, run_id: str) -> Optional[SimulationEngine]:
        with self._lock:
            if run_id in self._engines:
                return self._engines[run_id]

        # Load from database
        row = self.db.conn.execute(
            "SELECT config_json FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None

        import json
        cfg = SimConfig(json.loads(row["config_json"]))
        engine = self.db.load_latest_snapshot(run_id, cfg)
        if not engine:
            return None

        engine.state.run_id = run_id
        with self._lock:
            self._engines[run_id] = engine
            self._configs[run_id] = cfg

        return engine

    def get_engine(self, run_id: str) -> Optional[SimulationEngine]:
        with self._lock:
            return self._engines.get(run_id)

    def get_config(self, run_id: str) -> Optional[SimConfig]:
        with self._lock:
            return self._configs.get(run_id)

    def _sync_id_counters(self, engine: SimulationEngine):
        """Ensure global ID counters are at least as high as what's in the engine."""
        max_agent_id = max((a.id for a in engine.agents), default=0)
        if get_id_counter() < max_agent_id:
            set_id_counter(max_agent_id)
        max_faction_id = max((f.id for f in engine.factions), default=0)
        if get_faction_id_counter() < max_faction_id:
            set_faction_id_counter(max_faction_id)
        max_info_id = max((i.id for i in engine.info_objects), default=0)
        if get_info_id_counter() < max_info_id:
            set_info_id_counter(max_info_id)

    def run_tick(self, run_id: str) -> Optional[TickResult]:
        engine = self.get_engine(run_id)
        if not engine:
            return None

        self._sync_id_counters(engine)

        result = engine.tick()
        self.db.save_tick_stats(run_id, result)

        # Snapshot periodically
        cfg = self.get_config(run_id)
        if cfg and result.tick % cfg.persistence.snapshot_interval == 0:
            self.db.save_snapshot(run_id, engine)
            self.db.flush()

        return result

    def compute_delta(self, engine: SimulationEngine,
                      prev_alive_ids: set, prev_agents: dict) -> dict:
        """Compute agent deltas between ticks for WebSocket protocol.

        Emits consciousness/program/incarnation fields whenever a delta is
        sent for an agent (either movement or an attribute change). This
        keeps the protocol simple while still being delta-gated — static
        agents that don't move or change state emit no payload.
        """
        agent_deltas = []
        alive_now = engine.get_alive_agents()
        alive_ids_now = {a.id for a in alive_now}

        # Per-agent glimpse counts (derived from MatrixState.pleroma_glimpses)
        glimpse_counts: dict[int, int] = {}
        for g in getattr(engine.matrix_state, 'pleroma_glimpses', []) or []:
            aid = getattr(g, 'agent_id', None)
            if aid is None and isinstance(g, dict):
                aid = g.get('agent_id')
            if aid is not None:
                glimpse_counts[aid] = glimpse_counts.get(aid, 0) + 1

        def _extras(a) -> dict:
            return {
                "consciousness_phase": getattr(a, 'consciousness_phase', 'bicameral'),
                "free_will_index": round(getattr(a, 'free_will_index', 0.0), 3),
                "incarnation_count": getattr(a, 'incarnation_count', 1),
                "soul_trap_broken": getattr(a, 'soul_trap_broken', False),
                "is_enforcer": getattr(a, 'is_enforcer', False),
                "is_broker": getattr(a, 'is_broker', False),
                "is_guardian": getattr(a, 'is_guardian', False),
                "is_locksmith": getattr(a, 'is_locksmith', False),
                "teleport_keys": len(getattr(a, 'teleport_keys', []) or []),
                "past_life_memories": len(getattr(a, 'past_life_memories', []) or []),
                "location": getattr(a, 'location', 'simulation'),
                "pleroma_glimpses": glimpse_counts.get(a.id, 0),
                "predicted_action": _action_str(getattr(a, '_last_predicted_action', None)),
                "actual_action": _action_str(getattr(a, '_last_actual_action', None)),
            }

        # Newly born
        for a in alive_now:
            if a.id not in prev_alive_ids:
                delta = {
                    "id": a.id, "born": True,
                    "x": round(a.x, 4), "y": round(a.y, 4),
                    "phase": a.phase, "sex": a.sex,
                    "health": round(a.health, 4),
                    "intelligence": round(a.intelligence, 4),
                    "emotion": a.dominant_emotion,
                    "awareness": round(a.awareness, 4),
                    "is_protagonist": a.is_protagonist,
                }
                delta.update(_extras(a))
                agent_deltas.append(delta)
                continue

            # Existing agents — send if moved or salient state changed
            prev = prev_agents.get(a.id)
            if prev:
                moved = (abs(a.x - prev["x"]) > 0.001 or
                         abs(a.y - prev["y"]) > 0.001)
                health_changed = abs(a.health - prev["health"]) > 0.001
                phase_changed = (
                    prev.get("consciousness_phase") !=
                    getattr(a, 'consciousness_phase', 'bicameral')
                )
                program_changed = prev.get("program_flags") != (
                    getattr(a, 'is_enforcer', False),
                    getattr(a, 'is_broker', False),
                    getattr(a, 'is_guardian', False),
                    getattr(a, 'is_locksmith', False),
                )
                if moved or health_changed or phase_changed or program_changed:
                    delta = {
                        "id": a.id,
                        "x": round(a.x, 4), "y": round(a.y, 4),
                        "health": round(a.health, 4),
                        "intelligence": round(a.intelligence, 4),
                        "emotion": a.dominant_emotion,
                        "awareness": round(a.awareness, 4),
                        "phase": a.phase,
                        "age": a.age,
                        "redpilled": a.redpilled,
                        "is_anomaly": a.is_anomaly,
                        "is_sentinel": a.is_sentinel,
                        "is_protagonist": a.is_protagonist,
                        "faction_id": a.faction_id,
                    }
                    delta.update(_extras(a))
                    agent_deltas.append(delta)

        # Deaths
        for aid in prev_alive_ids - alive_ids_now:
            agent_deltas.append({"id": aid, "died": True})

        return {"agent_deltas": agent_deltas}

    def add_tick_listener(self, run_id: str, queue):
        with self._lock:
            if run_id not in self._tick_listeners:
                self._tick_listeners[run_id] = []
            self._tick_listeners[run_id].append(queue)

    def remove_tick_listener(self, run_id: str, queue):
        with self._lock:
            if run_id in self._tick_listeners:
                self._tick_listeners[run_id] = [
                    q for q in self._tick_listeners[run_id] if q is not queue
                ]

    def notify_listeners(self, run_id: str, data: dict):
        with self._lock:
            listeners = self._tick_listeners.get(run_id, [])
        for queue in listeners:
            try:
                queue.put_nowait(data)
            except Exception:
                pass


# Singleton instance
manager = EngineManager()
