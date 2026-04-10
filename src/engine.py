"""
Core simulation engine — orchestrates all eleven systems per tick.

Systems 1-5: Original (Social, Reproduction, Knowledge, Environment, Agency)
Systems 6-11: New (Emotions, Beliefs, Economy, Matrix, Conflict, Communication)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.config_loader import SimConfig
from src.agents import (
    Agent, SKILL_NAMES, PHASES, create_agent,
)
from src.world import ResourceGrid, TechBreakthrough
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
from src.matrix_layer import MatrixState, process_matrix, check_cycle_reset
from src.conflict import FactionWar, process_conflict
from src.communication import InfoObject, process_communication
from src.haven import HavenState, init_haven, process_haven
from src.programs import process_programs


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

        # ── Wipe awareness and Matrix-specific state ──
        for a in non_sentinels:
            a.awareness = 0.0
            a.redpilled = False
            a.is_anomaly = False
            a.is_exile = False
            # Partial memory wipe — keep last 3 memories, add reset event
            a.memory = a.memory[-3:]
            a.add_memory(tick, f"CYCLE RESET: The world shuddered and rebuilt (Cycle {self.matrix_state.cycle_number + 1})")
            # System trust gets boosted (fresh start)
            a.beliefs["system_trust"] = min(1.0, a.beliefs.get("system_trust", 0) + 0.3)
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

        # ── Dissolve wars ──
        self.wars.clear()

        # ── Regenerate world resources ──
        for row in self.world.cells:
            for cell in row:
                cell.current_resources = cell.base_resources

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

        # ── System 5: Agency — Move agents ──
        # Rebuild spatial index for O(1) neighbor lookups
        build_spatial_index(sim_alive, self.cfg)
        for a in sim_alive:
            if a.is_sentinel:
                continue  # Sentinels move via matrix_layer
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

        newly_dead = []
        for a in alive:
            if a.is_sentinel:
                if a.health <= 0:
                    a.alive = False
                    deaths += 1
                continue

            cell = self.world.get_cell(a.x, a.y)
            decay = base_decay * harshness * cell.harshness_modifier

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
                    immigrant.add_memory(tick, "Immigrated to the settlement")
                    self.agents.append(immigrant)
                    births += 1
                self.state.total_born += immigrants_needed

        # System 6: Emotional response to deaths
        for dead in newly_dead:
            on_agent_death_emotions(dead, self.agents, tick, self.cfg)
            # System 8: Inheritance
            process_inheritance(dead, self.agents, tick, self.cfg)
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
                bt = self.world.check_breakthroughs(cell, avg_tech, avg_social, tick)
                if bt:
                    tick_breakthroughs.append(bt.name)
                    for a in cell_agents:
                        a.add_memory(tick, f"Witnessed breakthrough: {bt.name}")
                    on_breakthrough_emotions(cell_agents, tick)

        # ── Protagonist management ──
        self.protagonist_ids = auto_select_protagonists(
            self.agents, self.cfg, self.protagonist_ids
        )

        # ══════════════════════════════════
        # NEW SYSTEMS (6-11)
        # ══════════════════════════════════

        # ── System 6: Emotions ──
        emotion_stats = process_emotions(self.agents, tick, self.cfg, world=self.world)

        # ── System 7: Beliefs & Factions ──
        belief_stats = process_beliefs(self.agents, self.factions, tick, self.cfg)
        # Ensure faction memory pools exist for all factions
        for faction in self.factions:
            self.cultural_memory.ensure_faction_memory(faction.id)
        # Apply faction-specific knowledge to members
        self.cultural_memory.apply_faction_knowledge(alive_now)

        # ── System 8: Economy ──
        economy_stats = process_economy(self.agents, tick, self.cfg, self.world, factions=self.factions)

        # ── System 9: Matrix Meta-Layer ──
        matrix_stats = process_matrix(self.agents, self.matrix_state, tick, self.cfg)

        # Check for Matrix cycle reset
        if check_cycle_reset(self.matrix_state, self.agents, self.cfg):
            self._perform_cycle_reset(tick)
            matrix_stats["cycle_reset"] = True

        # ── Programs: First-Class Entities (Enforcer, Broker, Guardian, Locksmith) ──
        program_stats = process_programs(
            self.agents, tick, self.cfg,
            oracle_target_id=self.matrix_state.oracle_target_id,
        )

        # ── System 10: Conflict ──
        conflict_stats = process_conflict(
            self.agents, self.factions, self.wars, tick, self.cfg, self.world,
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
            self.agents, self.info_objects, self.agent_info, tick, self.cfg
        )
        self._prev_propaganda_reach = communication_stats.get("propaganda_reach", {})

        # ── Haven tick (The Real World) ──
        haven_stats = {}
        if self.haven_state is not None:
            haven_stats = process_haven(self.agents, self.haven_state, tick, self.cfg)

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
