"""
SQLite persistence — snapshots, tick stats, events, narratives.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Optional

from src.config_loader import SimConfig
from src.agents import Agent, set_id_counter, get_id_counter
from src.engine import SimulationEngine, RunState, WorldEvent, TickResult
from src.world import ResourceGrid
from src.knowledge import CulturalMemory
from src.beliefs import Faction, set_faction_id_counter, get_faction_id_counter
from src.conflict import FactionWar
from src.matrix_layer import MatrixState
from src.communication import InfoObject, set_info_id_counter, get_info_id_counter


class SimulationDB:
    def __init__(self, db_path: str = "output/simulation.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                config_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT, tick INTEGER,
                agents_json TEXT, state_json TEXT,
                world_json TEXT, cultural_json TEXT,
                id_counter INTEGER,
                extra_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tick_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT, tick INTEGER,
                alive_count INTEGER, births INTEGER, deaths INTEGER,
                avg_intelligence REAL, avg_health REAL, avg_generation REAL,
                phase_counts_json TEXT,
                bonds_formed INTEGER DEFAULT 0, bonds_decayed INTEGER DEFAULT 0,
                breakthroughs_json TEXT DEFAULT '[]',
                world_summary_json TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT, tick INTEGER,
                name TEXT, description TEXT, effects_json TEXT
            );
            CREATE TABLE IF NOT EXISTS narratives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT, tick INTEGER, text TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tick_stats_run ON tick_stats(run_id);
            CREATE INDEX IF NOT EXISTS idx_snapshots_run ON snapshots(run_id);
        """)
        self.conn.commit()
        self._migrate()

    def _migrate(self):
        """Add columns that may be missing from older databases."""
        try:
            self.conn.execute("SELECT extra_json FROM snapshots LIMIT 1")
        except sqlite3.OperationalError:
            self.conn.execute("ALTER TABLE snapshots ADD COLUMN extra_json TEXT DEFAULT '{}'")
            self.conn.commit()

    def create_run(self, cfg: SimConfig) -> str:
        run_id = uuid.uuid4().hex[:12]
        self.conn.execute(
            "INSERT INTO runs (run_id, config_json) VALUES (?, ?)",
            (run_id, json.dumps(cfg.to_dict())),
        )
        self.conn.commit()
        return run_id

    def save_snapshot(self, run_id: str, engine: SimulationEngine):
        # Pack all new system state into extra_json
        extra = {
            "protagonist_ids": engine.protagonist_ids,
            "factions": [f.to_dict() for f in engine.factions],
            "wars": [w.to_dict() for w in engine.wars],
            "matrix_state": engine.matrix_state.to_dict(),
            "info_objects": [i.to_dict() for i in engine.info_objects],
            "agent_info": {str(k): list(v) for k, v in engine.agent_info.items()},
            "event_queue": [e.to_dict() for e in engine.event_queue],
            "recent_events": engine.recent_events[-20:],
            "faction_id_counter": get_faction_id_counter(),
            "info_id_counter": get_info_id_counter(),
        }
        self.conn.execute(
            """INSERT INTO snapshots (run_id, tick, agents_json, state_json,
               world_json, cultural_json, id_counter, extra_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, engine.state.current_tick,
                json.dumps([a.to_dict() for a in engine.agents]),
                json.dumps({
                    "current_tick": engine.state.current_tick,
                    "total_born": engine.state.total_born,
                    "total_died": engine.state.total_died,
                }),
                json.dumps(engine.world.to_dict()),
                json.dumps(engine.cultural_memory.to_dict()),
                get_id_counter(),
                json.dumps(extra),
            ),
        )

    def load_latest_snapshot(self, run_id: str, cfg: SimConfig) -> Optional[SimulationEngine]:
        row = self.conn.execute(
            "SELECT * FROM snapshots WHERE run_id = ? ORDER BY tick DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        if not row:
            return None

        agents = [Agent.from_dict(d) for d in json.loads(row["agents_json"])]
        state_data = json.loads(row["state_json"])
        set_id_counter(row["id_counter"])

        state = RunState(
            run_id=run_id,
            current_tick=state_data["current_tick"],
            total_born=state_data["total_born"],
            total_died=state_data["total_died"],
        )

        # Restore world from snapshot (full fidelity)
        world_data = json.loads(row["world_json"])
        world = ResourceGrid.from_dict(world_data, cfg)

        cultural = CulturalMemory.from_dict(json.loads(row["cultural_json"]), cfg)

        engine = SimulationEngine(cfg, agents=agents, state=state,
                                   world=world, cultural_memory=cultural)
        engine.world.update_agent_counts(engine.agents)

        # ── Restore new system state from extra_json ──
        extra_raw = row["extra_json"] if "extra_json" in row.keys() else "{}"
        if extra_raw:
            try:
                extra = json.loads(extra_raw)
            except (json.JSONDecodeError, TypeError):
                extra = {}

            engine.protagonist_ids = extra.get("protagonist_ids", [])
            engine.factions = [Faction.from_dict(f) for f in extra.get("factions", [])]
            engine.wars = [FactionWar.from_dict(w) for w in extra.get("wars", [])]
            if "matrix_state" in extra:
                engine.matrix_state = MatrixState.from_dict(extra["matrix_state"])
            engine.info_objects = [InfoObject.from_dict(i) for i in extra.get("info_objects", [])]
            engine.agent_info = {int(k): set(v) for k, v in extra.get("agent_info", {}).items()}
            engine.event_queue = [WorldEvent.from_dict(e) for e in extra.get("event_queue", [])]
            engine.recent_events = extra.get("recent_events", [])

            # Restore global counters
            if "faction_id_counter" in extra:
                set_faction_id_counter(extra["faction_id_counter"])
            if "info_id_counter" in extra:
                set_info_id_counter(extra["info_id_counter"])

            # Mark protagonists
            prot_set = set(engine.protagonist_ids)
            for a in engine.agents:
                if a.id in prot_set:
                    a.is_protagonist = True

        return engine

    def save_tick_stats(self, run_id: str, result: TickResult):
        self.conn.execute(
            """INSERT INTO tick_stats
               (run_id, tick, alive_count, births, deaths,
                avg_intelligence, avg_health, avg_generation,
                phase_counts_json, bonds_formed, bonds_decayed,
                breakthroughs_json, world_summary_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, result.tick, result.alive_count,
                result.births, result.deaths,
                result.avg_intelligence, result.avg_health, result.avg_generation,
                json.dumps(result.phase_counts),
                result.bonds_formed, result.bonds_decayed,
                json.dumps(result.breakthroughs),
                json.dumps(result.world_summary),
            ),
        )

    def save_event(self, run_id: str, event: WorldEvent):
        self.conn.execute(
            "INSERT INTO events (run_id, tick, name, description, effects_json) VALUES (?,?,?,?,?)",
            (run_id, event.tick, event.name, event.description, json.dumps(event.effects)),
        )

    def save_narrative(self, run_id: str, tick: int, text: str):
        self.conn.execute(
            "INSERT INTO narratives (run_id, tick, text) VALUES (?,?,?)",
            (run_id, tick, text),
        )

    def get_tick_history(self, run_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM tick_stats WHERE run_id = ? ORDER BY tick", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_events(self, run_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT tick, name, description, effects_json FROM events WHERE run_id = ? ORDER BY tick",
            (run_id,),
        ).fetchall()
        return [{"tick": r["tick"], "name": r["name"], "description": r["description"],
                 "effects": json.loads(r["effects_json"])} for r in rows]

    def get_narratives(self, run_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT tick, text FROM narratives WHERE run_id = ? ORDER BY tick", (run_id,)
        ).fetchall()
        return [{"tick": r["tick"], "text": r["text"]} for r in rows]

    def list_runs(self) -> list[dict]:
        rows = self.conn.execute("""
            SELECT r.run_id, r.created_at,
                   COALESCE(MAX(s.tick), 0) as latest_tick
            FROM runs r LEFT JOIN snapshots s ON r.run_id = s.run_id
            GROUP BY r.run_id ORDER BY r.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

    def export_run_csv(self, run_id: str, output_path: str):
        """Export tick history, events, and agent snapshots to CSV files."""
        import csv
        import os
        os.makedirs(output_path, exist_ok=True)

        # Tick stats
        rows = self.get_tick_history(run_id)
        if rows:
            with open(os.path.join(output_path, "tick_stats.csv"), "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        # Events
        events = self.get_events(run_id)
        if events:
            with open(os.path.join(output_path, "events.csv"), "w", newline="", encoding="utf-8") as f:
                flat = []
                for e in events:
                    flat.append({
                        "tick": e["tick"], "name": e["name"],
                        "description": e["description"],
                        "effects": json.dumps(e["effects"]),
                    })
                writer = csv.DictWriter(f, fieldnames=flat[0].keys())
                writer.writeheader()
                writer.writerows(flat)

        # Narratives
        narrs = self.get_narratives(run_id)
        if narrs:
            with open(os.path.join(output_path, "narratives.csv"), "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=narrs[0].keys())
                writer.writeheader()
                writer.writerows(narrs)

        # Agent snapshot (latest)
        row = self.conn.execute(
            "SELECT agents_json FROM snapshots WHERE run_id = ? ORDER BY tick DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        if row:
            agents = json.loads(row["agents_json"])
            if agents:
                # Flatten agent data for CSV
                flat_agents = []
                for a in agents:
                    flat = {
                        "id": a["id"], "sex": a["sex"], "age": a["age"],
                        "phase": a["phase"], "generation": a["generation"],
                        "health": a["health"], "intelligence": a["intelligence"],
                        "alive": a["alive"], "x": a.get("x", 0), "y": a.get("y", 0),
                        "wealth": a.get("wealth", 0), "awareness": a.get("awareness", 0),
                        "redpilled": a.get("redpilled", False),
                        "faction_id": a.get("faction_id"),
                        "trauma": a.get("trauma", 0),
                        "is_protagonist": a.get("is_protagonist", False),
                    }
                    # Add skills
                    for sk, sv in a.get("skills", {}).items():
                        flat[f"skill_{sk}"] = sv
                    # Add traits
                    traits = a.get("traits", {})
                    for tk, tv in traits.items():
                        flat[f"trait_{tk}"] = tv
                    # Add emotions
                    for ek, ev in a.get("emotions", {}).items():
                        flat[f"emo_{ek}"] = ev
                    # Add beliefs
                    for bk, bv in a.get("beliefs", {}).items():
                        flat[f"belief_{bk}"] = bv
                    flat_agents.append(flat)

                with open(os.path.join(output_path, "agents.csv"), "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=flat_agents[0].keys())
                    writer.writeheader()
                    writer.writerows(flat_agents)

        return output_path

    def export_run_json(self, run_id: str, output_path: str):
        """Export full run data as a single JSON file."""
        import os
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        data = {
            "run_id": run_id,
            "tick_history": self.get_tick_history(run_id),
            "events": self.get_events(run_id),
            "narratives": self.get_narratives(run_id),
        }

        # Latest agent snapshot
        row = self.conn.execute(
            "SELECT agents_json, state_json, world_json, cultural_json, extra_json "
            "FROM snapshots WHERE run_id = ? ORDER BY tick DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        if row:
            data["agents"] = json.loads(row["agents_json"])
            data["state"] = json.loads(row["state_json"])
            data["world"] = json.loads(row["world_json"])
            data["cultural_memory"] = json.loads(row["cultural_json"])
            extra_raw = row["extra_json"] if "extra_json" in row.keys() else "{}"
            if extra_raw:
                try:
                    data["extra"] = json.loads(extra_raw)
                except (json.JSONDecodeError, TypeError):
                    data["extra"] = {}

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return output_path

    def flush(self):
        self.conn.commit()

    def close(self):
        self.conn.commit()
        self.conn.close()