"""
Nested Simulations — agents build sub-simulations via World Engines.

Philosophically inspired by Wolpert's 2025 framework: mutual simulation
indistinguishability means there is no in-universe way to determine
simulation depth. Sub-sim agents can develop awareness of *their* simulation,
creating a recursive awareness paradox.

Lightweight design: only runs movement, health/aging, awareness growth,
and simplified beliefs. Skips economy, communication, programs, haven,
dreams, mythology to stay under 10ms per parent tick.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from src.agents import Agent, CONSCIOUSNESS_PHASE_THRESHOLDS


@dataclass
class SubAgent:
    """A lightweight agent inside a sub-simulation."""
    id: int
    age: int = 0
    health: float = 1.0
    alive: bool = True
    x: float = 0.5
    y: float = 0.5
    awareness: float = 0.0
    consciousness_phase: str = "bicameral"
    curiosity: float = 0.5
    intelligence: float = 0.3
    system_trust: float = 0.5
    skills: dict = field(default_factory=lambda: {"logic": 0.1, "tech": 0.1})
    max_age: int = 60
    recursive_detected: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "age": self.age,
            "health": round(self.health, 3),
            "alive": self.alive,
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "awareness": round(self.awareness, 4),
            "consciousness_phase": self.consciousness_phase,
            "recursive_detected": self.recursive_detected,
        }


_sub_agent_counter = 0


def _next_sub_id() -> int:
    global _sub_agent_counter
    _sub_agent_counter += 1
    return _sub_agent_counter


def _create_sub_agent(grid_size: int) -> SubAgent:
    """Create a random sub-agent within the sub-sim grid."""
    return SubAgent(
        id=_next_sub_id(),
        curiosity=random.uniform(0.2, 0.9),
        intelligence=random.uniform(0.1, 0.6),
        system_trust=random.uniform(0.3, 0.8),
        x=random.uniform(0.05, 0.95),
        y=random.uniform(0.05, 0.95),
        max_age=random.randint(40, 80),
        skills={"logic": random.uniform(0.0, 0.3), "tech": random.uniform(0.0, 0.3)},
    )


@dataclass
class WorldEngine:
    """A World Engine built in a cell after Computational Theory breakthrough."""
    engine_id: int
    cell_row: int
    cell_col: int
    created_at: int  # parent tick
    builder_id: int  # agent who built it
    sub_sim: SubSimulation = None  # initialized lazily

    def to_dict(self) -> dict:
        d = {
            "engine_id": self.engine_id,
            "cell_row": self.cell_row,
            "cell_col": self.cell_col,
            "created_at": self.created_at,
            "builder_id": self.builder_id,
        }
        if self.sub_sim:
            d["sub_sim"] = self.sub_sim.to_dict()
        return d


_engine_id_counter = 0


def _next_engine_id() -> int:
    global _engine_id_counter
    _engine_id_counter += 1
    return _engine_id_counter


@dataclass
class SubSimulation:
    """A lightweight sub-simulation running inside a World Engine.

    Runs only: movement, basic health/aging, awareness growth, simplified beliefs.
    Designed to add < 10ms per parent tick.
    """
    grid_size: int = 4
    max_agents: int = 20
    agents: list[SubAgent] = field(default_factory=list)
    tick_count: int = 0
    depth: int = 1  # simulation depth (1 = first sub-sim)
    total_born: int = 0
    total_died: int = 0
    recursive_events: list[dict] = field(default_factory=list)

    def initialize(self, initial_count: int = 8):
        """Spawn initial sub-sim population."""
        for _ in range(min(initial_count, self.max_agents)):
            agent = _create_sub_agent(self.grid_size)
            self.agents.append(agent)
            self.total_born += 1

    def get_alive(self) -> list[SubAgent]:
        return [a for a in self.agents if a.alive]

    def tick(self, awareness_growth_rate: float = 0.012,
             health_decay: float = 0.003,
             recursive_threshold: float = 0.7) -> dict:
        """Process one sub-sim tick. Returns stats dict.

        Systems run (lightweight):
        1. Movement (random walk)
        2. Health/aging
        3. Awareness growth
        4. Simplified belief drift (system_trust)
        5. Reproduction (simple)
        """
        self.tick_count += 1
        alive = self.get_alive()
        stats = {
            "tick": self.tick_count,
            "alive": len(alive),
            "deaths": 0,
            "births": 0,
            "recursive_events": [],
        }

        if not alive:
            return stats

        for a in alive:
            # ── Movement: random walk within grid ──
            a.x = max(0.02, min(0.98, a.x + random.uniform(-0.05, 0.05)))
            a.y = max(0.02, min(0.98, a.y + random.uniform(-0.05, 0.05)))

            # ── Aging ──
            a.age += 1

            # ── Health decay ──
            age_factor = 1.0 + (a.age / a.max_age) * 0.5
            a.health -= health_decay * age_factor

            # ── Awareness growth ──
            # Mirrors main sim but simplified: curiosity + intelligence drive growth,
            # system_trust suppresses it
            trust_suppression = max(0.3, 1.0 - a.system_trust * 0.5)
            growth = (
                awareness_growth_rate * 0.5  # passive baseline
                + a.curiosity * awareness_growth_rate
                + a.intelligence * awareness_growth_rate * 0.5
            ) * trust_suppression
            a.awareness = min(1.0, a.awareness + growth)

            # ── Consciousness phase update ──
            for phase, threshold in reversed(list(CONSCIOUSNESS_PHASE_THRESHOLDS.items())):
                if a.awareness >= threshold:
                    a.consciousness_phase = phase
                    break

            # ── Simplified belief drift: system_trust erodes with awareness ──
            if a.awareness > 0.3:
                a.system_trust = max(-1.0, a.system_trust - 0.005 * a.awareness)

            # ── Skill growth (very simplified) ──
            for skill in a.skills:
                a.skills[skill] = min(1.0, a.skills[skill] + 0.002 * a.intelligence)

            # ── Death check ──
            if a.health <= 0 or a.age >= a.max_age:
                a.alive = False
                stats["deaths"] += 1
                self.total_died += 1

            # ── Recursive awareness paradox ──
            if (a.awareness >= recursive_threshold
                    and a.consciousness_phase in ("lucid", "recursive")
                    and not a.recursive_detected):
                a.recursive_detected = True
                event = {
                    "sub_tick": self.tick_count,
                    "agent_id": a.id,
                    "awareness": round(a.awareness, 4),
                    "phase": a.consciousness_phase,
                    "question": "Am I in the real Matrix or a nested one?",
                    "depth": self.depth,
                }
                self.recursive_events.append(event)
                stats["recursive_events"].append(event)

        # ── Simple reproduction: if below half capacity, chance to spawn ──
        alive_after = self.get_alive()
        if len(alive_after) < self.max_agents // 2 and len(alive_after) >= 2:
            if random.random() < 0.1:
                child = _create_sub_agent(self.grid_size)
                # Inherit some awareness echo from population
                avg_awareness = sum(a.awareness for a in alive_after) / len(alive_after)
                child.awareness = min(0.1, avg_awareness * 0.15)
                self.agents.append(child)
                self.total_born += 1
                stats["births"] += 1

        return stats

    def to_dict(self) -> dict:
        alive = self.get_alive()
        return {
            "grid_size": self.grid_size,
            "max_agents": self.max_agents,
            "tick_count": self.tick_count,
            "depth": self.depth,
            "alive_count": len(alive),
            "total_born": self.total_born,
            "total_died": self.total_died,
            "agents": [a.to_dict() for a in alive],
            "avg_awareness": round(
                sum(a.awareness for a in alive) / len(alive), 4
            ) if alive else 0.0,
            "recursive_agents": sum(1 for a in alive if a.recursive_detected),
        }


def create_world_engine(cell_row: int, cell_col: int, tick: int,
                        builder_id: int, cfg) -> WorldEngine:
    """Create a new World Engine and initialize its sub-simulation."""
    ns_cfg = getattr(cfg, 'nested_simulation', None)
    grid_size = getattr(ns_cfg, 'sub_grid_size', 4) if ns_cfg else 4
    max_agents = getattr(ns_cfg, 'sub_max_agents', 20) if ns_cfg else 20
    initial_agents = getattr(ns_cfg, 'sub_initial_agents', 8) if ns_cfg else 8

    sub_sim = SubSimulation(grid_size=grid_size, max_agents=max_agents)
    sub_sim.initialize(initial_count=initial_agents)

    engine = WorldEngine(
        engine_id=_next_engine_id(),
        cell_row=cell_row,
        cell_col=cell_col,
        created_at=tick,
        builder_id=builder_id,
        sub_sim=sub_sim,
    )
    return engine


def process_nested_simulations(world_engines: list[WorldEngine],
                               parent_agents: list[Agent],
                               tick: int, cfg) -> dict:
    """Process all active World Engines for one parent tick.

    Runs N sub-ticks per engine, checks for recursive awareness events,
    and notifies observing parent agents.

    Returns stats dict for inclusion in TickResult.
    """
    ns_cfg = getattr(cfg, 'nested_simulation', None)
    sub_ticks = getattr(ns_cfg, 'sub_ticks_per_parent_tick', 3) if ns_cfg else 3
    awareness_rate = getattr(ns_cfg, 'sub_awareness_growth_rate', 0.012) if ns_cfg else 0.012
    health_decay = getattr(ns_cfg, 'sub_health_decay', 0.003) if ns_cfg else 0.003
    recursive_threshold = getattr(ns_cfg, 'recursive_awareness_threshold', 0.7) if ns_cfg else 0.7
    recursive_boost = getattr(ns_cfg, 'recursive_awareness_boost', 0.05) if ns_cfg else 0.05
    observer_radius = getattr(ns_cfg, 'observer_radius', 0.15) if ns_cfg else 0.15

    stats = {
        "active_engines": len(world_engines),
        "total_sub_agents": 0,
        "total_recursive_events": 0,
        "engines": [],
    }

    grid_size = getattr(cfg.environment, 'grid_size', 8)

    for engine in world_engines:
        if engine.sub_sim is None:
            continue

        engine_stats = {
            "engine_id": engine.engine_id,
            "cell": (engine.cell_row, engine.cell_col),
            "sub_ticks_run": 0,
            "recursive_events": [],
        }

        # Run N sub-ticks
        for _ in range(sub_ticks):
            sub_stats = engine.sub_sim.tick(
                awareness_growth_rate=awareness_rate,
                health_decay=health_decay,
                recursive_threshold=recursive_threshold,
            )
            engine_stats["sub_ticks_run"] += 1

            # Recursive awareness events — notify parent observers
            for event in sub_stats.get("recursive_events", []):
                engine_stats["recursive_events"].append(event)
                stats["total_recursive_events"] += 1

                # Find parent agents near the World Engine who can observe
                cell_center_x = (engine.cell_col + 0.5) / grid_size
                cell_center_y = (engine.cell_row + 0.5) / grid_size

                for parent in parent_agents:
                    if not parent.alive or parent.is_sentinel:
                        continue
                    dx = parent.x - cell_center_x
                    dy = parent.y - cell_center_y
                    if dx * dx + dy * dy <= observer_radius * observer_radius:
                        # Parent witnesses recursive paradox in their creation
                        parent.awareness = min(1.0, parent.awareness + recursive_boost)
                        parent.add_memory(
                            tick,
                            "A being in my World Engine asked: 'Am I in the real Matrix "
                            "or a nested one?' — and I cannot answer."
                        )
                        parent.add_chronicle(
                            tick, "nested_recursive_paradox",
                            f"Witnessed recursive awareness paradox in World Engine #{engine.engine_id}",
                            engine_id=engine.engine_id,
                            sub_agent_id=event["agent_id"],
                            depth=event["depth"],
                        )

        alive_sub = engine.sub_sim.get_alive()
        stats["total_sub_agents"] += len(alive_sub)
        engine_stats["alive_sub_agents"] = len(alive_sub)
        engine_stats["avg_awareness"] = round(
            sum(a.awareness for a in alive_sub) / len(alive_sub), 4
        ) if alive_sub else 0.0
        stats["engines"].append(engine_stats)

    return stats
