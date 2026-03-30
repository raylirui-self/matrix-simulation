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
        """Compute agent deltas between ticks for WebSocket protocol."""
        agent_deltas = []
        alive_now = engine.get_alive_agents()
        alive_ids_now = {a.id for a in alive_now}

        # Newly born
        for a in alive_now:
            if a.id not in prev_alive_ids:
                agent_deltas.append({
                    "id": a.id, "born": True,
                    "x": round(a.x, 4), "y": round(a.y, 4),
                    "phase": a.phase, "sex": a.sex,
                    "health": round(a.health, 4),
                    "intelligence": round(a.intelligence, 4),
                    "emotion": a.dominant_emotion,
                    "awareness": round(a.awareness, 4),
                    "is_protagonist": a.is_protagonist,
                })
                continue

            # Existing agents — send if moved or state changed
            prev = prev_agents.get(a.id)
            if prev:
                moved = (abs(a.x - prev["x"]) > 0.001 or
                         abs(a.y - prev["y"]) > 0.001)
                health_changed = abs(a.health - prev["health"]) > 0.001
                if moved or health_changed:
                    agent_deltas.append({
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
                    })

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
