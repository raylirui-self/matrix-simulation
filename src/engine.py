"""
Core simulation engine — orchestrates all eleven systems per tick.

Systems 1-5: Original (Social, Reproduction, Knowledge, Environment, Agency)
Systems 6-11: New (Emotions, Beliefs, Economy, Matrix, Conflict, Communication)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from src.config_loader import SimConfig
from src.agents import (
    Agent, SKILL_NAMES, PHASES, create_agent,
)
from src.world import ResourceGrid, TechBreakthrough, Artifact, next_artifact_id
from src.knowledge import CulturalMemory, parent_teaching, social_transfer_multiplier
from src.social import process_bonds
from src.mate_selection import process_reproduction
from src.agency import compute_move, auto_select_protagonists, build_spatial_index
from src.emotions import (
    process_emotions, on_agent_death_emotions, on_birth_emotions,
    on_breakthrough_emotions,
)
from src.beliefs import (
    Faction, process_beliefs, get_faction_bonuses,
)
from src.economy import process_economy, process_inheritance
from src.matrix_layer import (
    MatrixState, process_matrix, check_cycle_reset,
    DemiurgeState, Archon, update_demiurge, init_archons,
    process_archons, get_chaos_multiplier, process_sophia,
    process_pleroma,
)
from src.conflict import FactionWar, process_conflict
from src.communication import (
    InfoObject, LanguageArtifact, process_communication,
    process_language_evolution, create_language_artifact,
    process_language_artifact_discovery,
    apply_communication_archon_chaos,
)
from src.haven import HavenState, init_haven, process_haven
from src.programs import process_programs
from src.mythology import (
    MythologyState, generate_era_summary, classify_events_for_myths,
    generate_faction_myths, identify_legendary_candidates,
    create_legendary_figure, process_legend_discoveries,
)
from src.dreams import (
    DreamState, process_dreams, get_dream_movement_multiplier,
    get_dream_terrain_reduction,
)
from src.nested_sim import (
    WorldEngine, create_world_engine, process_nested_simulations,
)


@dataclass
class WorldEvent:
    tick: int
    name: str
    description: str
    effects: dict

    def to_dict(self) -> dict:
        return {
            "tick": self.tick, "name": self.name,
            "description": self.description, "effects": self.effects,
        }

    @classmethod
    def from_dict(cls, d: dict) -> WorldEvent:
        return cls(**d)


@dataclass
class TickResult:
    tick: int
    alive_count: int
    births: int
    deaths: int
    avg_intelligence: float
    avg_health: float
    avg_generation: float
    phase_counts: dict
    bonds_formed: int = 0
    bonds_decayed: int = 0
    breakthroughs: list = field(default_factory=list)
    world_summary: dict = field(default_factory=dict)
    # New system stats
    emotion_stats: dict = field(default_factory=dict)
    belief_stats: dict = field(default_factory=dict)
    economy_stats: dict = field(default_factory=dict)
    matrix_stats: dict = field(default_factory=dict)
    conflict_stats: dict = field(default_factory=dict)
    communication_stats: dict = field(default_factory=dict)
    haven_stats: dict = field(default_factory=dict)
    program_stats: dict = field(default_factory=dict)
    death_causes: dict = field(default_factory=dict)
    age_distribution: dict = field(default_factory=dict)
    tech_progress: dict = field(default_factory=dict)
    cinematic_events: list = field(default_factory=list)
    mythology_stats: dict = field(default_factory=dict)
    dream_stats: dict = field(default_factory=dict)
    nested_sim_stats: dict = field(default_factory=dict)


@dataclass
class RunState:
    run_id: str = ""
    current_tick: int = 0
    total_born: int = 0
    total_died: int = 0


class SimulationEngine:
    """Core engine orchestrating all eleven systems."""

    def __init__(self, cfg: SimConfig, agents: Optional[list[Agent]] = None,
                 state: Optional[RunState] = None,
                 world: Optional[ResourceGrid] = None,
                 cultural_memory: Optional[CulturalMemory] = None):
        self.cfg = cfg
        self.agents = agents or []
        self.state = state or RunState()
        self.world = world or ResourceGrid(cfg)
        self.cultural_memory = cultural_memory or CulturalMemory.from_config(cfg)
        self.event_queue: list[WorldEvent] = []
        self.recent_events: list[dict] = []
        self.protagonist_ids: list[int] = []

        # ── New system state ──
        self.factions: list[Faction] = []
        self.wars: list[FactionWar] = []
        self.matrix_state: MatrixState = MatrixState()
        self.info_objects: list[InfoObject] = []
        self.agent_info: dict[int, set] = {}  # agent_id -> set of info_ids

        # ── Haven (The Real World) ──
        self.haven_state: Optional[HavenState] = None
        if getattr(cfg, 'haven', None) and getattr(cfg.haven, 'enabled', False):
            self.haven_state = init_haven(cfg)

        # ── Mythology (procedural narrative) ──
        self.mythology_state: MythologyState = MythologyState()

        # ── Dreams (simulation dream cycles) ──
        self.dream_state: DreamState = DreamState()

        # ── Language artifacts (dead faction languages) ──
        self.language_artifacts: list[LanguageArtifact] = []

        # ── Nested Simulations (World Engines) ──
        self.world_engines: list[WorldEngine] = []

        # ── Cinematic tracking (persists across ticks) ──
        self._prev_enforcer_count: int = 0

        # ── Soul Trap: captured consciousness pool for recycling into newborns ──
        self._soul_pool: list[dict] = []  # list of {memories, awareness, beliefs, skills, ...}

    def initialize(self):
        """Create initial population, apply era starting beliefs and pre-unlocked tech."""
        era = self.cfg.era_metadata
        starting_beliefs = era.get("starting_beliefs") if era else None

        for _ in range(self.cfg.population.initial_size):
            a = create_agent(self.cfg, randomize_age=True,
                             starting_beliefs=starting_beliefs)
            self.cultural_memory.apply_to_newborn(a)
            self.agents.append(a)
        self.state.total_born = len(self.agents)
        self.world.update_agent_counts(self.agents)

        # Pre-unlock technologies specified by the era
        pre_tech = era.get("pre_unlocked_tech", []) if era else []
        if pre_tech:
            self._apply_pre_unlocked_tech(pre_tech)

    def _apply_pre_unlocked_tech(self, tech_names: list[str]):
        """Grant technologies to all cells at tick 0 (era starting condition)."""
        bt_cfg = self.cfg.environment.tech_breakthroughs
        if not bt_cfg.enabled:
            return
        # Build lookup from config thresholds
        tech_defs = {}
        for threshold in bt_cfg.thresholds:
            tech_defs[threshold["name"]] = threshold

        for name in tech_names:
            if name not in tech_defs:
                continue
            defn = tech_defs[name]
            # Only apply to cells matching terrain requirement (or all if null)
            for row in self.world.cells:
                for cell in row:
                    existing = {t.name for t in cell.unlocked_techs}
                    if name in existing:
                        continue
                    terrain_req = defn.get("terrain")
                    if terrain_req and cell.terrain != terrain_req:
                        continue
                    bt = TechBreakthrough(
                        name=name,
                        unlocked_at=0,
                        resource_bonus=defn["resource_bonus"],
                        capacity_bonus=defn.get("capacity_bonus", 0),
                    )
                    cell.unlocked_techs.append(bt)
                    self.world.global_techs.add(name)

    def _perform_cycle_reset(self, tick: int):
        """Reset the Matrix — partial memory preservation, awareness wipe, new cycle."""
        alive = self.get_alive_agents()
        non_sentinels = [a for a in alive if not a.is_sentinel]

        # Log the reset
        self.recent_events.append({
            "tick": tick, "name": "MATRIX CYCLE RESET",
            "description": f"Cycle {self.matrix_state.cycle_number} ended. The Architect reloads the simulation.",
            "effects": {"cycle": self.matrix_state.cycle_number},
        })

        # ── Partial awareness wipe — high-awareness agents retain echoes ──
        for a in non_sentinels:
            old_awareness = a.awareness
            if a.soul_trap_broken:
                # Broke the soul trap: retain 50% awareness
                a.awareness = old_awareness * 0.5
            elif old_awareness >= 0.6:
                # High awareness: retain 35% — déjà vu of awakening
                a.awareness = old_awareness * 0.35
            elif old_awareness >= 0.3:
                # Moderate awareness: retain 20%
                a.awareness = old_awareness * 0.2
            else:
                # Low awareness: full wipe
                a.awareness = 0.0
            a.redpilled = False
            a.is_anomaly = False
            a.is_exile = False
            # Partial memory wipe — keep last 3 memories, add reset event
            a.memory = a.memory[-3:]
            a.add_memory(tick, f"CYCLE RESET: The world shuddered and rebuilt (Cycle {self.matrix_state.cycle_number + 1})")
            a.add_chronicle(tick, "cycle_reset", f"Survived cycle reset into Cycle {self.matrix_state.cycle_number + 1}",
                            cycle=self.matrix_state.cycle_number + 1)
            # System trust gets boosted (fresh start) — but less for those who remember
            trust_boost = 0.15 if old_awareness >= 0.3 else 0.3
            a.beliefs["system_trust"] = min(1.0, a.beliefs.get("system_trust", 0) + trust_boost)
            # Emotions stabilize
            a.emotions["fear"] = max(0.0, a.emotions.get("fear", 0) - 0.3)
            a.emotions["hope"] = min(1.0, a.emotions.get("hope", 0) + 0.1)
            a.trauma = max(0.0, a.trauma - 0.2)

        # ── Remove all sentinels ──
        for a in alive:
            if a.is_sentinel:
                a.alive = False

        # ── Partial cultural memory preservation ──
        # Floors decay by 30% but don't fully reset — knowledge echoes across cycles
        for skill in self.cultural_memory.skill_floors:
            self.cultural_memory.skill_floors[skill] *= 0.7
            self.cultural_memory.knowledge_pool[skill] *= 0.5

        # ── Reset Matrix state ──
        self.matrix_state.cycle_number += 1
        self.matrix_state.control_index = 1.0
        self.matrix_state.total_awareness = 0.0
        self.matrix_state.anomaly_id = None
        self.matrix_state.oracle_target_id = None
        self.matrix_state.sentinels_deployed = 0
        self.matrix_state.glitches_this_cycle = 0
        self.matrix_state.ticks_since_reset = 0
        # Reset Gnostic layer: Demiurge calms, Archons regenerate, systems re-controlled
        self.matrix_state.demiurge = DemiurgeState()
        self.matrix_state.archons.clear()
        self.matrix_state.released_systems.clear()
        self.matrix_state.pleroma_glimpses.clear()

        # ── Dissolve wars ──
        self.wars.clear()

        # ── Regenerate world resources (artifacts survive reset) ──
        for row in self.world.cells:
            for cell in row:
                cell.current_resources = cell.base_resources
                # Artifacts persist across cycles — this is the archaeological record

    def _capture_soul(self, dead_agent: Agent, tick: int):
        """Soul Trap: capture consciousness/memories from a dying agent for recycling."""
        soul = {
            "memories": list(dead_agent.memory[-10:]),
            "memory_summary": dead_agent.memory_summary,
            "awareness": dead_agent.awareness,
            "consciousness_phase": dead_agent.consciousness_phase,
            "beliefs": dict(dead_agent.beliefs),
            "skills": dict(dead_agent.skills),
            "faction_id": dead_agent.faction_id,
            "redpilled": dead_agent.redpilled,
            "soul_trap_broken": dead_agent.soul_trap_broken,
            "incarnation_count": dead_agent.incarnation_count,
            "tick_captured": tick,
            "source_id": dead_agent.id,
        }
        self._soul_pool.append(soul)
        # Cap pool size
        if len(self._soul_pool) > 100:
            self._soul_pool = self._soul_pool[-100:]

    def _apply_soul_to_newborn(self, agent: Agent, tick: int):
        """Soul Trap: recycle captured consciousness into a newborn.
        Memory preservation depends on the soul's awareness level."""
        if not self._soul_pool:
            return

        soul = self._soul_pool.pop(0)  # FIFO — oldest soul first
        agent.incarnation_count = soul["incarnation_count"] + 1

        awareness = soul["awareness"]
        was_broken = soul["soul_trap_broken"]

        if was_broken:
            # Broke the trap: full memory preservation
            agent.past_life_memories = soul["memories"]
            agent.awareness = min(0.6, awareness * 0.8)
            agent.soul_trap_broken = True
            agent.beliefs = {k: v * 0.8 for k, v in soul["beliefs"].items()}
            for skill, val in soul["skills"].items():
                if skill in agent.skills:
                    agent.skills[skill] = max(agent.skills[skill], val * 0.5)
            agent.add_memory(tick, f"INCARNATION #{agent.incarnation_count}: I remember everything. I have lived before.")
            agent.add_chronicle(tick, "soul_recycled",
                                f"Reincarnated with full memories (incarnation #{agent.incarnation_count})",
                                source_id=soul["source_id"], memories_preserved="full")
        elif awareness >= 0.4:
            # Moderate-to-high awareness: partial memory preservation
            kept = soul["memories"][-3:]
            agent.past_life_memories = kept
            agent.awareness = min(0.3, awareness * 0.4)
            # Faint echoes of beliefs
            for axis in agent.beliefs:
                if axis in soul["beliefs"]:
                    agent.beliefs[axis] = agent.beliefs[axis] * 0.7 + soul["beliefs"][axis] * 0.3
            agent.add_memory(tick, f"INCARNATION #{agent.incarnation_count}: Faint echoes of a past life linger...")
            agent.add_chronicle(tick, "soul_recycled",
                                f"Reincarnated with partial memories (incarnation #{agent.incarnation_count})",
                                source_id=soul["source_id"], memories_preserved="partial")
        else:
            # Default: memories wiped (normal reincarnation)
            agent.past_life_memories = []
            agent.incarnation_count = soul["incarnation_count"] + 1
            # Residual awareness — something feels off
            agent.awareness = min(0.1, awareness * 0.2)
            agent.add_chronicle(tick, "soul_recycled",
                                f"Reincarnated with wiped memories (incarnation #{agent.incarnation_count})",
                                source_id=soul["source_id"], memories_preserved="none")

    def _create_artifact(self, dead_agent: Agent, tick: int):
        """Create an artifact in the cell where the agent died."""
        # Only notable agents leave artifacts
        if dead_agent.awareness < 0.1 and dead_agent.avg_skill < 0.2:
            return

        cell = self.world.get_cell(dead_agent.x, dead_agent.y)

        # Determine artifact type
        if dead_agent.avg_skill > 0.5:
            artifact_type = "tech_remnant"
        elif dead_agent.awareness > 0.4:
            artifact_type = "inscription"
        else:
            artifact_type = "ruin"

        # Gather key events from chronicle
        key_events = []
        for entry in dead_agent.chronicle[-5:]:
            key_events.append(entry.description)

        faction_name = "unknown"
        if dead_agent.faction_id is not None:
            faction = next((f for f in self.factions if f.id == dead_agent.faction_id), None)
            if faction:
                faction_name = faction.name

        artifact = Artifact(
            artifact_id=next_artifact_id(),
            faction_name=faction_name,
            era_tick=tick,
            cycle_number=self.matrix_state.cycle_number,
            awareness_level=dead_agent.awareness,
            tech_level=dead_agent.skills.get("tech", 0.0),
            key_events=key_events,
            artifact_type=artifact_type,
        )
        cell.artifacts.append(artifact)
        # Cap artifacts per cell
        max_artifacts = 20
        if len(cell.artifacts) > max_artifacts:
            cell.artifacts = cell.artifacts[-max_artifacts:]

    def _process_artifact_discovery(self, agents: list, tick: int) -> int:
        """Agents in cells with artifacts may discover them.
        Returns number of discoveries."""
        discoveries = 0
        discovery_chance = getattr(
            getattr(self.cfg, 'archaeology', None),
            'discovery_chance', 0.01
        ) if hasattr(self.cfg, 'archaeology') else 0.01

        for a in agents:
            if not a.alive or a.is_sentinel:
                continue
            cell = self.world.get_cell(a.x, a.y)
            if not cell.artifacts:
                continue

            # Discovery probability: base * (curiosity + logic) / 2
            chance = discovery_chance * (a.traits.curiosity + a.skills.get("logic", 0.0)) / 2
            if random.random() > chance:
                continue

            # Discover the oldest artifact in the cell
            artifact = cell.artifacts[0]

            # Knowledge boost
            for skill in a.skills:
                a.skills[skill] = min(1.0, a.skills[skill] + artifact.tech_level * 0.02)
            a.intelligence = sum(a.skills.values()) / len(a.skills)

            # Awareness clue from artifacts — any artifact with awareness echoes
            if artifact.awareness_level > 0.1:
                awareness_boost = artifact.awareness_level * 0.15
                a.awareness = min(1.0, a.awareness + awareness_boost)

            a.add_memory(tick,
                         f"Discovered {artifact.artifact_type} from {artifact.faction_name} "
                         f"(Cycle {artifact.cycle_number}): {artifact.key_events[0] if artifact.key_events else 'ancient remnant'}")
            a.add_chronicle(tick, "artifact_discovered",
                            f"Discovered {artifact.artifact_type} from Cycle {artifact.cycle_number}",
                            artifact_id=artifact.artifact_id,
                            faction=artifact.faction_name)
            discoveries += 1

        return discoveries

    def get_alive_agents(self) -> list[Agent]:
        return [a for a in self.agents if a.alive]

    def _agents_by_id(self) -> dict[int, Agent]:
        return {a.id: a for a in self.agents if a.alive}

    def tick(self) -> TickResult:
        """Process one simulation tick — all eleven systems."""
        self.state.current_tick += 1
        tick = self.state.current_tick
        alive = self.get_alive_agents()
        # Simulation systems only process agents inside the simulation
        sim_alive = [a for a in alive if a.location == "simulation"]
        agents_by_id = self._agents_by_id()

        deaths = 0
        births = 0
        tick_breakthroughs = []
        cinematic_events = []

        # Track pre-tick state for cinematic triggers
        _prev_anomaly_id = self.matrix_state.anomaly_id
        _prev_cycle = self.matrix_state.cycle_number

        # ── Dreams: process dream state (must run before movement for modifiers) ──
        dream_stats = process_dreams(
            sim_alive, self.agents, self.dream_state, tick, self.cfg,
            recent_events=self.recent_events,
        )

        # ── System 5: Agency — Move agents ──
        # Rebuild spatial index for O(1) neighbor lookups
        build_spatial_index(sim_alive, self.cfg)

        # Apply dream movement multiplier if dreaming
        dream_move_mult = get_dream_movement_multiplier(self.dream_state, self.cfg)

        for a in sim_alive:
            if a.is_sentinel:
                continue  # Sentinels move via matrix_layer
            # During dreams, temporarily boost movement speed
            if dream_move_mult != 1.0:
                orig_speed = self.cfg.agency.movement_speed
                self.cfg.agency.movement_speed = orig_speed * dream_move_mult
                new_x, new_y = compute_move(a, self.world, sim_alive, self.cfg)
                self.cfg.agency.movement_speed = orig_speed
            else:
                new_x, new_y = compute_move(a, self.world, sim_alive, self.cfg)
            a.x, a.y = new_x, new_y

        # ── Update spatial grid ──
        self.world.update_agent_counts(self.agents)

        # ── System 1: Social — Process bonds ──
        social_stats = process_bonds(self.agents, tick, self.cfg)

        # ── System 2: Mate Selection — Reproduction ──
        # Suppress reproduction when at or above population cap
        current_pop = len(sim_alive)
        max_pop = self.cfg.population.max_size
        if current_pop >= max_pop:
            new_children = []
        else:
            new_children = process_reproduction(self.agents, tick, self.cfg)
        for child in new_children:
            self.cultural_memory.apply_to_newborn(child)
            # Soul Trap: recycle captured consciousness into newborn
            if self._soul_pool:
                self._apply_soul_to_newborn(child, tick)
            self.agents.append(child)
            births += 1
            # System 6: Emotional response to birth
            parent_a = agents_by_id.get(child.parent_ids[0]) if child.parent_ids else None
            parent_b = agents_by_id.get(child.parent_ids[1]) if len(child.parent_ids) > 1 else None
            if parent_a and parent_b:
                on_birth_emotions(parent_a, parent_b, child, tick)
        self.state.total_born += births

        # ── Aging & Phase Transitions ──
        phase_ages = self.cfg.lifecycle.phase_ages
        for a in alive:
            a.age += 1
            if a.age >= phase_ages.elder:
                a.phase = "elder"
            elif a.age >= phase_ages.adult:
                a.phase = "adult"
            elif a.age >= phase_ages.adolescent:
                a.phase = "adolescent"
            elif a.age >= phase_ages.child:
                a.phase = "child"
            else:
                a.phase = "infant"

        # ── System 3: Knowledge Transfer ──
        growth_mults = self.cfg.skills.phase_growth_multipliers
        dim_factor = self.cfg.skills.diminishing_returns_factor
        learning_mult = self.cfg.skills.learning_multiplier

        for a in sim_alive:
            if a.is_sentinel:
                continue
            phase_mult = getattr(growth_mults, a.phase, 0.5)
            social_mult = social_transfer_multiplier(a, self.cfg)
            cell = self.world.get_cell(a.x, a.y)

            teaching_bonus = parent_teaching(a, agents_by_id, tick, self.cfg)

            # Faction bonuses
            faction = next((f for f in self.factions if f.id == a.faction_id), None)
            faction_bonuses = get_faction_bonuses(a, faction, self.cfg)
            faction_learning = faction_bonuses.get("learning_boost", 0.0)

            for skill in SKILL_NAMES:
                base = a.traits.learning_rate * 0.005 * learning_mult
                base *= phase_mult
                base *= (1.0 - a.skills[skill] * dim_factor)
                if skill in ("creativity", "tech"):
                    base *= (1.0 + a.traits.curiosity * 0.3)
                if skill == "social":
                    base *= (1.0 + a.traits.sociability * 0.3)
                if cell.skill_bonus == skill:
                    base += cell.skill_bonus_amount
                base += teaching_bonus.get(skill, 0.0)
                base *= social_mult
                base += faction_learning

                # Grief slows learning
                if a.emotions.get("grief", 0) > 0.5:
                    base *= (1.0 - a.emotions["grief"] * 0.3)

                a.skills[skill] = min(1.0, a.skills[skill] + max(0, base))

            a.intelligence = sum(a.skills.values()) / len(a.skills)

        # ── Health Decay & Death ──
        base_decay = self.cfg.lifecycle.base_health_decay
        elder_mult = self.cfg.lifecycle.elder_decay_multiplier
        harshness = self.cfg.environment.harshness

        # During dreams, terrain effects are reduced
        dream_terrain_mult = get_dream_terrain_reduction(self.dream_state, self.cfg)

        newly_dead = []
        for a in alive:
            if a.is_sentinel:
                if a.health <= 0:
                    a.alive = False
                    deaths += 1
                continue

            # Haven agents have their own health decay in process_haven
            if a.location == "haven":
                continue

            cell = self.world.get_cell(a.x, a.y)
            decay = base_decay * harshness * cell.harshness_modifier * dream_terrain_mult

            resource_factor = 1.5 - cell.effective_resources
            decay *= resource_factor

            age_factor = 1.0 + (a.age / a.traits.max_age) * 0.5
            decay *= age_factor

            if a.phase == "elder":
                decay *= elder_mult

            decay *= (1.0 - a.traits.resilience * 0.3)

            # Wealth health bonus already applied in economy system
            a.health -= decay

            if a.health <= 0 or a.age >= a.traits.max_age:
                if a.age >= a.traits.max_age:
                    a.death_cause = "old_age"
                elif not a.death_cause:
                    a.death_cause = "starvation"
                a.alive = False
                a.health = 0
                deaths += 1
                self.cultural_memory.on_agent_death(a)
                a.add_memory(tick, "Died")
                a.add_chronicle(tick, "death", f"Died: {a.death_cause}", cause=a.death_cause, age=a.age)
                newly_dead.append(a)

        self.state.total_died += deaths

        # ── Population floor: spawn immigrants if below minimum ──
        pop_floor = getattr(self.cfg.population, 'min_floor', 0)
        if pop_floor > 0:
            alive_after_deaths = [a for a in self.agents if a.alive]
            immigrants_needed = pop_floor - len(alive_after_deaths)
            if immigrants_needed > 0:
                for _ in range(immigrants_needed):
                    immigrant = create_agent(self.cfg, randomize_age=True)
                    self.cultural_memory.apply_to_newborn(immigrant)
                    if self._soul_pool:
                        self._apply_soul_to_newborn(immigrant, tick)
                    immigrant.add_memory(tick, "Immigrated to the settlement")
                    self.agents.append(immigrant)
                    births += 1
                self.state.total_born += immigrants_needed

        # System 6: Emotional response to deaths
        for dead in newly_dead:
            on_agent_death_emotions(dead, self.agents, tick, self.cfg)
            # System 8: Inheritance
            process_inheritance(dead, self.agents, tick, self.cfg)
            # Check if agent breaks the soul trap before death
            # Requires: recursive consciousness + high awareness + broken free or high reality_testing
            if (dead.consciousness_phase == "recursive"
                    and dead.awareness >= 0.9
                    and (dead.soul_trap_broken or dead.reality_testing >= 0.7)):
                dead.soul_trap_broken = True
                dead.add_chronicle(tick, "soul_trap_broken",
                                   "Broke free of the soul trap — memories will persist across incarnations")
            # Soul Trap: capture consciousness for recycling
            self._capture_soul(dead, tick)
            # Archaeology: leave artifacts
            self._create_artifact(dead, tick)
            # Revenge: mate seeks vengeance for killed partner
            if dead.killed_by is not None:
                for bond in dead.bonds:
                    if bond.bond_type == "mate":
                        mate = next(
                            (a for a in self.agents if a.id == bond.target_id and a.alive),
                            None,
                        )
                        if mate:
                            mate.current_goal = "HUNT_ENEMY"
                            mate.goal_target_id = dead.killed_by
                            mate.goal_ticks = 0
                            mate.emotions["anger"] = min(
                                1.0, mate.emotions.get("anger", 0) + 0.4
                            )

        # ── Apply queued world events ──
        for event in self.event_queue:
            self._apply_event(event)
        self.event_queue.clear()

        # ── Resource depletion & regeneration ──
        self.world.tick_resources()

        # ── Cultural memory tick ──
        self.cultural_memory.tick()

        # ── Tech breakthroughs ──
        alive_now = self.get_alive_agents()
        bt_min_pop = getattr(self.cfg.environment, 'breakthrough_min_pop', 3)
        for row in self.world.cells:
            for cell in row:
                if cell.agent_count < bt_min_pop:
                    continue
                cell_agents = [
                    a for a in alive_now
                    if self.world.get_cell(a.x, a.y) == cell
                ]
                if not cell_agents:
                    continue
                avg_tech = sum(a.skills.get("tech", 0) for a in cell_agents) / len(cell_agents)
                avg_social = sum(a.skills.get("social", 0) for a in cell_agents) / len(cell_agents)
                avg_logic = sum(a.skills.get("logic", 0) for a in cell_agents) / len(cell_agents)
                bt = self.world.check_breakthroughs(cell, avg_tech, avg_social, tick, avg_logic=avg_logic)
                if bt:
                    tick_breakthroughs.append(bt.name)
                    for a in cell_agents:
                        a.add_memory(tick, f"Witnessed breakthrough: {bt.name}")
                        a.add_chronicle(tick, "breakthrough", f"Witnessed breakthrough: {bt.name}", tech=bt.name)
                    on_breakthrough_emotions(cell_agents, tick)

        # ── Nested Simulations: World Engine creation on computational_theory ──
        ns_cfg = getattr(self.cfg, 'nested_simulation', None)
        ns_enabled = getattr(ns_cfg, 'enabled', False) if ns_cfg else False
        max_engines = getattr(ns_cfg, 'max_world_engines', 3) if ns_cfg else 3
        if ns_enabled and "computational_theory" in tick_breakthroughs:
            if len(self.world_engines) < max_engines:
                # Find the cell that just unlocked computational_theory
                for row in self.world.cells:
                    for cell in row:
                        if any(t.name == "computational_theory" and t.unlocked_at == tick
                               for t in cell.unlocked_techs):
                            # Pick the highest-tech agent in the cell as builder
                            cell_agents = [
                                a for a in alive_now
                                if self.world.get_cell(a.x, a.y) == cell and a.alive
                            ]
                            if cell_agents:
                                builder = max(cell_agents, key=lambda a: a.skills.get("tech", 0))
                                engine = create_world_engine(
                                    cell.row, cell.col, tick, builder.id, self.cfg,
                                )
                                self.world_engines.append(engine)
                                builder.add_memory(tick, "Built a World Engine — a simulation within the simulation")
                                builder.add_chronicle(
                                    tick, "world_engine_built",
                                    f"Built World Engine #{engine.engine_id} in cell ({cell.row},{cell.col})",
                                    engine_id=engine.engine_id,
                                )
                                cinematic_events.append({
                                    "type": "world_engine_built",
                                    "title": "WORLD ENGINE CONSTRUCTED",
                                    "subtitle": f"Agent #{builder.id} built a simulation within the simulation",
                                    "agent_id": builder.id,
                                    "cell": (cell.row, cell.col),
                                    "tick": tick,
                                })

        # ── Nested Simulations: process sub-sim ticks ──
        nested_sim_stats = {}
        if ns_enabled and self.world_engines:
            nested_sim_stats = process_nested_simulations(
                self.world_engines, sim_alive, tick, self.cfg,
            )
            # Cinematic events for recursive paradox
            if nested_sim_stats.get("total_recursive_events", 0) > 0:
                cinematic_events.append({
                    "type": "recursive_awareness_paradox",
                    "title": "RECURSIVE AWARENESS PARADOX",
                    "subtitle": "A sub-simulation agent questions its reality — and no one can answer",
                    "tick": tick,
                    "count": nested_sim_stats["total_recursive_events"],
                })

        # ── Artifact discovery (Agent Archaeology) ──
        artifact_discoveries = self._process_artifact_discovery(sim_alive, tick)

        # ── Protagonist management ──
        self.protagonist_ids = auto_select_protagonists(
            self.agents, self.cfg, self.protagonist_ids
        )

        # ══════════════════════════════════
        # NEW SYSTEMS (6-11)
        # ══════════════════════════════════

        # ── System 6: Emotions ──
        emotion_stats = process_emotions(sim_alive, tick, self.cfg, world=self.world)

        # ── System 7: Beliefs & Factions ──
        _pre_faction_ids = {f.id for f in self.factions}
        belief_stats = process_beliefs(sim_alive, self.factions, tick, self.cfg)
        _post_faction_ids = {f.id for f in self.factions}
        # Create language artifacts for dissolved factions
        dissolved_ids = _pre_faction_ids - _post_faction_ids
        for fid in dissolved_ids:
            # Build a minimal faction-like object for the artifact creator
            class _DeadFaction:
                def __init__(self, fid):
                    self.id = fid
                    self.name = f"Faction #{fid}"
                    self.alive = False
            la = create_language_artifact(
                _DeadFaction(fid), self.agents, tick,
                self.world, self.matrix_state.cycle_number, self.cfg,
            )
            if la:
                self.language_artifacts.append(la)
        # Ensure faction memory pools exist for all factions
        for faction in self.factions:
            self.cultural_memory.ensure_faction_memory(faction.id)
        # Apply faction-specific knowledge to members
        self.cultural_memory.apply_faction_knowledge(alive_now)

        # ── System 8: Economy ──
        economy_stats = process_economy(sim_alive, tick, self.cfg, self.world, factions=self.factions)

        # ── System 9: Matrix Meta-Layer ──
        matrix_stats = process_matrix(sim_alive, self.matrix_state, tick, self.cfg)

        # ── Gnostic Mythology Layer ──
        # Update Demiurge psychology (influences sentinel deployment within process_matrix)
        demiurge_stats = update_demiurge(self.matrix_state, sim_alive, tick, self.cfg)
        matrix_stats["demiurge"] = demiurge_stats.get("demiurge", {})

        # Initialize and process Archons
        init_archons(self.matrix_state, self.cfg)
        archon_stats = process_archons(sim_alive, self.matrix_state, tick, self.cfg)
        matrix_stats["archons"] = archon_stats

        # Sophia synchronicities
        sophia_stats = process_sophia(
            sim_alive, self.agents, self.matrix_state,
            self.dream_state, tick, self.cfg,
        )
        matrix_stats["sophia"] = sophia_stats

        # Pleroma glimpses
        pleroma_stats = process_pleroma(
            sim_alive, self.matrix_state, self.dream_state, tick, self.cfg,
        )
        matrix_stats["pleroma"] = pleroma_stats

        # Check for Matrix cycle reset
        if check_cycle_reset(self.matrix_state, self.agents, self.cfg):
            self._perform_cycle_reset(tick)
            matrix_stats["cycle_reset"] = True

        matrix_stats["artifact_discoveries"] = artifact_discoveries
        matrix_stats["soul_pool_size"] = len(self._soul_pool)

        # ── Programs: First-Class Entities (Enforcer, Broker, Guardian, Locksmith) ──
        program_stats = process_programs(
            self.agents, tick, self.cfg,
            oracle_target_id=self.matrix_state.oracle_target_id,
        )

        # ── System 10: Conflict ──
        conflict_stats = process_conflict(
            sim_alive, self.factions, self.wars, tick, self.cfg, self.world,
            propaganda_reach=getattr(self, '_prev_propaganda_reach', {})
        )

        # Wartime innovation bonus: factions at war develop tech and survival faster
        warring_faction_ids = set()
        for w in self.wars:
            warring_faction_ids.add(w.faction_a_id)
            warring_faction_ids.add(w.faction_b_id)
        if warring_faction_ids:
            war_bonus = getattr(self.cfg.conflict, 'wartime_innovation_bonus', 0.002)
            for a in alive_now:
                if a.alive and a.faction_id in warring_faction_ids:
                    a.skills["tech"] = min(1.0, a.skills["tech"] + war_bonus)
                    a.skills["survival"] = min(1.0, a.skills["survival"] + war_bonus)

        # ── System 11: Communication ──
        communication_stats = process_communication(
            sim_alive, self.info_objects, self.agent_info, tick, self.cfg
        )
        self._prev_propaganda_reach = communication_stats.get("propaganda_reach", {})

        # ── Language Evolution ──
        language_stats = process_language_evolution(
            sim_alive, self.info_objects, self.factions, tick, self.cfg,
        )
        communication_stats["language"] = language_stats

        # Apply Communication Archon chaos (accelerates language divergence)
        comm_chaos = get_chaos_multiplier("communication", self.matrix_state, self.cfg)
        if comm_chaos > 1.0:
            apply_communication_archon_chaos(communication_stats, comm_chaos)

        # ── Language Artifact Discovery ──
        if self.language_artifacts:
            for a in sim_alive:
                if not a.alive or a.is_sentinel:
                    continue
                grid_size = getattr(self.cfg.environment, 'grid_size', 8)
                a_row = min(grid_size - 1, max(0, int(a.y * grid_size)))
                a_col = min(grid_size - 1, max(0, int(a.x * grid_size)))
                for la in self.language_artifacts:
                    if la.cell_row == a_row and la.cell_col == a_col:
                        if random.random() < (a.traits.curiosity + a.skills.get("logic", 0)) * 0.005:
                            effects = process_language_artifact_discovery(a, la, tick, self.cfg)
                            communication_stats.setdefault("language_discoveries", 0)
                            communication_stats["language_discoveries"] += 1
                            break  # one discovery per agent per tick

        # ── Haven tick (The Real World) ──
        haven_stats = {}
        if self.haven_state is not None:
            haven_stats = process_haven(self.agents, self.haven_state, tick, self.cfg)

        # ── Cinematic events ──
        # Anomaly emergence
        if self.matrix_state.anomaly_id and self.matrix_state.anomaly_id != _prev_anomaly_id:
            anomaly = next((a for a in self.agents if a.id == self.matrix_state.anomaly_id), None)
            cinematic_events.append({
                "type": "anomaly_emergence",
                "title": "THE ONE HAS EMERGED",
                "subtitle": f"Agent #{self.matrix_state.anomaly_id} has become the Anomaly",
                "agent_id": self.matrix_state.anomaly_id,
                "tick": tick,
            })

        # Cycle reset
        if self.matrix_state.cycle_number != _prev_cycle:
            cinematic_events.append({
                "type": "cycle_reset",
                "title": "MATRIX CYCLE RESET",
                "subtitle": f"Cycle {_prev_cycle} has ended. The Architect reloads the simulation.",
                "cycle": self.matrix_state.cycle_number,
                "tick": tick,
            })

        # Enforcer swarm critical mass (>= 5 enforcers, crossing threshold)
        enforcer_critical = getattr(
            getattr(getattr(self.cfg, 'programs', None), 'enforcer', None),
            'max_copies', 20
        ) if hasattr(self.cfg, 'programs') else 20
        enforcer_threshold = max(5, enforcer_critical // 2)
        current_enforcer_count = sum(1 for a in self.get_alive_agents() if a.is_enforcer)
        if current_enforcer_count >= enforcer_threshold and self._prev_enforcer_count < enforcer_threshold:
            cinematic_events.append({
                "type": "enforcer_swarm",
                "title": "ENFORCER SWARM",
                "subtitle": f"{current_enforcer_count} Enforcers active — the system is overwhelming the resistance",
                "enforcer_count": current_enforcer_count,
                "tick": tick,
            })
        self._prev_enforcer_count = current_enforcer_count

        # ── Mythology: Era Summaries, Myths, Legends ──
        mythology_stats = {}
        myth_cfg = getattr(self.cfg, 'mythology', None)
        era_interval = getattr(myth_cfg, 'era_summary_interval', 100) if myth_cfg else 100
        myth_interval = getattr(myth_cfg, 'myth_check_interval', 50) if myth_cfg else 50
        legend_interval = getattr(myth_cfg, 'legend_check_interval', 100) if myth_cfg else 100
        discovery_chance = getattr(myth_cfg, 'legend_discovery_chance', 0.005) if myth_cfg else 0.005

        # Era summary generation
        if tick - self.mythology_state.last_era_summary_tick >= era_interval:
            summary = self.get_population_summary()
            era = generate_era_summary(
                self.mythology_state.last_era_summary_tick + 1, tick,
                summary, self.recent_events,
                narrator=getattr(self, '_narrator', None),
            )
            self.mythology_state.era_summaries.append(era)
            self.mythology_state.last_era_summary_tick = tick
            mythology_stats["era_summary_generated"] = True

        # Myth generation on cycle reset or at intervals
        cycle_reset_this_tick = self.matrix_state.cycle_number != _prev_cycle
        if cycle_reset_this_tick or (tick - self.mythology_state.last_myth_check_tick >= myth_interval):
            summary = self.get_population_summary()
            triggers = classify_events_for_myths(
                self.recent_events, summary, cycle_reset=cycle_reset_this_tick,
            )
            max_myths = getattr(myth_cfg, 'max_myths_per_trigger', 5) if myth_cfg else 5
            new_myths = []
            for trigger in triggers[:2]:  # max 2 trigger types per check
                myths = generate_faction_myths(
                    trigger["archetype"], trigger["source_event"],
                    trigger["trigger_type"], tick,
                    factions=self.factions, wars=self.wars,
                    narrator=getattr(self, '_narrator', None),
                    stats_snapshot=summary,
                )
                new_myths.extend(myths[:max_myths])
            self.mythology_state.myths.extend(new_myths)
            self.mythology_state.last_myth_check_tick = tick
            mythology_stats["myths_generated"] = len(new_myths)

        # Legendary figure identification
        if tick % legend_interval == 0 and tick > 0:
            max_legends = getattr(myth_cfg, 'max_legends', 20) if myth_cfg else 20
            if len(self.mythology_state.legends) < max_legends:
                candidates = identify_legendary_candidates(
                    self.agents, self.mythology_state.known_legend_agent_ids,
                )
                for agent, legend_type in candidates[:3]:  # max 3 new legends per check
                    if len(self.mythology_state.legends) >= max_legends:
                        break
                    legend = create_legendary_figure(
                        agent, legend_type, tick,
                        cycle_number=self.matrix_state.cycle_number,
                        narrator=getattr(self, '_narrator', None),
                    )
                    self.mythology_state.legends.append(legend)
                    self.mythology_state.known_legend_agent_ids.add(agent.id)
                mythology_stats["legends_created"] = len(candidates[:3])

        # Legend discoveries
        discoveries = process_legend_discoveries(
            self.agents, self.mythology_state.legends, tick,
            discovery_chance=discovery_chance,
        )
        if discoveries:
            mythology_stats["legend_discoveries"] = len(discoveries)

        # ── Compile stats ──
        alive_final = self.get_alive_agents()
        phase_counts = {p: 0 for p in PHASES}
        for a in alive_final:
            phase_counts[a.phase] = phase_counts.get(a.phase, 0) + 1

        avg_intel = (sum(a.intelligence for a in alive_final) / len(alive_final)) if alive_final else 0
        avg_health = (sum(a.health for a in alive_final) / len(alive_final)) if alive_final else 0
        avg_gen = (sum(a.generation for a in alive_final) / len(alive_final)) if alive_final else 0

        # ── Death cause tracking (Item 14) ──
        tick_death_causes = {}
        for a in newly_dead:
            tick_death_causes[a.death_cause] = tick_death_causes.get(a.death_cause, 0) + 1

        # ── Age distribution (Item 15) ──
        age_dist = {}
        for a in alive_final:
            bucket = f"{(a.age // 10) * 10}s"
            key = f"{a.sex}_{bucket}"
            age_dist[key] = age_dist.get(key, 0) + 1

        # ── Tech progress indicators (Item 16) ──
        tech_progress = {}
        bt_cfg = self.cfg.environment.tech_breakthroughs
        if bt_cfg.enabled:
            for threshold in bt_cfg.thresholds:
                name = threshold["name"]
                if name in self.world.global_techs:
                    tech_progress[name] = 1.0  # already unlocked
                else:
                    # Find max tech skill proximity across all cells with enough population
                    max_prox = 0.0
                    for row in self.world.cells:
                        for cell in row:
                            if cell.agent_count > 0:
                                cell_agents = [a for a in alive_final if self.world.get_cell(a.x, a.y) == cell]
                                if cell_agents:
                                    avg_tech = sum(a.skills.get("tech", 0) for a in cell_agents) / len(cell_agents)
                                    prox = avg_tech / threshold["tech_level"] if threshold["tech_level"] > 0 else 0
                                    max_prox = max(max_prox, prox)
                    tech_progress[name] = min(1.0, max_prox)

        # ── Belief evolution data (Item 18) ──
        faction_belief_means = {}
        for f in self.factions:
            members = [a for a in alive_final if a.faction_id == f.id]
            if members:
                means = {}
                for axis in ["individualism", "tradition", "system_trust", "spirituality"]:
                    means[axis] = round(sum(m.beliefs.get(axis, 0) for m in members) / len(members), 4)
                faction_belief_means[f.id] = means
        belief_stats["faction_belief_means"] = faction_belief_means

        return TickResult(
            tick=tick,
            alive_count=len(alive_final),
            births=births, deaths=deaths,
            avg_intelligence=round(avg_intel, 4),
            avg_health=round(avg_health, 4),
            avg_generation=round(avg_gen, 2),
            phase_counts=phase_counts,
            bonds_formed=social_stats["bonds_formed"],
            bonds_decayed=social_stats["bonds_decayed"],
            breakthroughs=tick_breakthroughs,
            world_summary=self.world.summary(),
            emotion_stats=emotion_stats,
            belief_stats=belief_stats,
            economy_stats=economy_stats,
            matrix_stats=matrix_stats,
            conflict_stats=conflict_stats,
            communication_stats=communication_stats,
            haven_stats=haven_stats,
            program_stats=program_stats,
            death_causes=tick_death_causes,
            age_distribution=age_dist,
            tech_progress=tech_progress,
            cinematic_events=cinematic_events,
            mythology_stats=mythology_stats,
            dream_stats=dream_stats,
            nested_sim_stats=nested_sim_stats,
        )

    def _apply_event(self, event: WorldEvent):
        """Apply a world event's effects to the population."""
        effects = event.effects
        target = effects.get("target", "all")
        alive = self.get_alive_agents()

        for a in alive:
            if target == "elders" and a.phase != "elder":
                continue
            if target == "children" and a.phase not in ("infant", "child"):
                continue
            if target == "adults" and a.phase != "adult":
                continue

            hdelta = effects.get("health_delta", 0)
            if hdelta < 0:
                hdelta *= (1.0 - a.traits.resilience * 0.3)
            a.health = max(0.0, min(1.0, a.health + hdelta))

            skill = effects.get("skill_boost")
            if skill and skill in a.skills:
                amount = effects.get("skill_boost_amount", 0.03)
                a.skills[skill] = min(1.0, a.skills[skill] + amount)

            a.add_memory(event.tick, f"Event: {event.name}")

            # Emotional response to events
            if hdelta < -0.1:
                a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + abs(hdelta) * 0.5)
                a.emotions["anger"] = min(1.0, a.emotions.get("anger", 0) + abs(hdelta) * 0.3)
            elif hdelta > 0.05:
                a.emotions["happiness"] = min(1.0, a.emotions.get("happiness", 0) + hdelta * 0.5)
                a.emotions["hope"] = min(1.0, a.emotions.get("hope", 0) + hdelta * 0.3)

        self.recent_events.append(event.to_dict())
        if len(self.recent_events) > 20:
            self.recent_events = self.recent_events[-20:]

    def queue_event(self, event: WorldEvent):
        self.event_queue.append(event)

    def get_population_summary(self) -> dict:
        """Build a summary dict for the narrator."""
        alive = self.get_alive_agents()
        non_sentinels = [a for a in alive if not a.is_sentinel]

        if not non_sentinels:
            return {
                "tick": self.state.current_tick, "alive": 0,
                "total_born": self.state.total_born, "total_died": self.state.total_died,
                "phases": {}, "avg_skills": {}, "avg_traits": {},
                "avg_health": 0, "avg_intelligence": 0, "max_generation": 0,
                "recent_events": [e["name"] for e in self.recent_events[-5:]],
                "cultural_floors": self.cultural_memory.skill_floors,
                "world": self.world.summary(),
                "factions": [], "wars": [], "matrix": self.matrix_state.to_dict(),
            }

        phases = {}
        for a in non_sentinels:
            phases[a.phase] = phases.get(a.phase, 0) + 1

        avg_skills = {s: 0.0 for s in SKILL_NAMES}
        avg_traits = {"learning_rate": 0, "resilience": 0, "curiosity": 0, "sociability": 0,
                      "charisma": 0, "aggression": 0}
        for a in non_sentinels:
            for s in SKILL_NAMES:
                avg_skills[s] += a.skills[s]
            for t in avg_traits:
                avg_traits[t] += getattr(a.traits, t, 0)

        n = len(non_sentinels)
        avg_skills = {k: round(v / n, 4) for k, v in avg_skills.items()}
        avg_traits = {k: round(v / n, 4) for k, v in avg_traits.items()}

        # Average emotions
        avg_emotions = {}
        for emo in ["happiness", "fear", "anger", "grief", "hope"]:
            avg_emotions[emo] = round(sum(a.emotions.get(emo, 0) for a in non_sentinels) / n, 4)

        return {
            "tick": self.state.current_tick,
            "alive": n,
            "total_born": self.state.total_born,
            "total_died": self.state.total_died,
            "phases": phases,
            "avg_skills": avg_skills,
            "avg_traits": avg_traits,
            "avg_health": round(sum(a.health for a in non_sentinels) / n, 4),
            "avg_intelligence": round(sum(a.intelligence for a in non_sentinels) / n, 4),
            "max_generation": max(a.generation for a in non_sentinels),
            "recent_events": [e["name"] for e in self.recent_events[-5:]],
            "cultural_floors": {k: round(v, 4) for k, v in self.cultural_memory.skill_floors.items()},
            "world": self.world.summary(),
            "protagonist_ids": self.protagonist_ids,
            # New
            "avg_emotions": avg_emotions,
            "factions": [f.to_dict() for f in self.factions],
            "wars": [w.to_dict() for w in self.wars],
            "matrix": self.matrix_state.to_dict(),
            "avg_wealth": round(sum(a.wealth for a in non_sentinels) / n, 3),
            "avg_awareness": round(sum(a.awareness for a in non_sentinels) / n, 4),
            "redpilled_count": sum(1 for a in non_sentinels if a.redpilled),
            "sentinels": sum(1 for a in alive if a.is_sentinel),
        }
