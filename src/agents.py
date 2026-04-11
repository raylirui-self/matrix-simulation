"""
Agent data model — traits, skills, bonds, lifecycle, sex,
emotions, beliefs, awareness, wealth, and faction membership.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

SKILL_NAMES = ["logic", "creativity", "social", "survival", "tech"]
PHASES = ["infant", "child", "adolescent", "adult", "elder"]
EMOTION_NAMES = ["happiness", "fear", "anger", "grief", "hope"]
BELIEF_AXES = ["individualism", "tradition", "system_trust", "spirituality"]

# Consciousness phases — qualitative states that gate behavioral changes
# Ordered by depth: bicameral < questioning < self_aware < lucid < recursive
CONSCIOUSNESS_PHASES = ["bicameral", "questioning", "self_aware", "lucid", "recursive"]
CONSCIOUSNESS_PHASE_THRESHOLDS = {
    "bicameral": 0.0,      # default — hears Architect's voice as own
    "questioning": 0.15,    # "wait, that thought wasn't mine"
    "self_aware": 0.35,     # recognizes self as separate from system
    "lucid": 0.6,           # perceives simulation structure
    "recursive": 0.85,      # self-referential awareness, no endstate
}

# Chronicle event types — structured life events for narrative generation
CHRONICLE_TYPES = [
    "born", "first_friend", "first_combat", "faction_join", "faction_leave",
    "mate_found", "child_born", "witnessed_death", "red_pill", "blue_pill",
    "became_anomaly", "quest_stage", "cycle_reset", "jack_out", "jack_in",
    "recruited", "became_recruiter", "breakthrough", "death",
    "phase_transition", "strange_loop", "artifact_discovered",
    "soul_recycled", "soul_trap_broken",
    "archon_destroyed", "pleroma_glimpse", "sophia_synchronicity",
    "language_artifact_discovered",
]

_agent_id_counter = 0


def next_id() -> int:
    global _agent_id_counter
    _agent_id_counter += 1
    return _agent_id_counter


def set_id_counter(val: int):
    global _agent_id_counter
    _agent_id_counter = val


def get_id_counter() -> int:
    return _agent_id_counter


@dataclass
class Traits:
    """Heritable attributes — passed from parents with mutation."""
    learning_rate: float = 0.5
    resilience: float = 0.5
    curiosity: float = 0.5
    sociability: float = 0.5
    charisma: float = 0.5
    aggression: float = 0.3
    boldness: float = 0.5
    max_age: int = 80

    def to_dict(self) -> dict:
        return {
            "learning_rate": round(self.learning_rate, 3),
            "resilience": round(self.resilience, 3),
            "curiosity": round(self.curiosity, 3),
            "sociability": round(self.sociability, 3),
            "charisma": round(self.charisma, 3),
            "aggression": round(self.aggression, 3),
            "boldness": round(self.boldness, 3),
            "max_age": self.max_age,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Traits:
        return cls(
            learning_rate=d.get("learning_rate", 0.5),
            resilience=d.get("resilience", 0.5),
            curiosity=d.get("curiosity", 0.5),
            sociability=d.get("sociability", 0.5),
            charisma=d.get("charisma", 0.5),
            aggression=d.get("aggression", 0.3),
            boldness=d.get("boldness", 0.5),
            max_age=d.get("max_age", 80),
        )

    @classmethod
    def random(cls, base_max_age: int = 80, variance: int = 25) -> Traits:
        return cls(
            learning_rate=random.uniform(0.2, 0.9),
            resilience=random.uniform(0.2, 0.9),
            curiosity=random.uniform(0.2, 0.9),
            sociability=random.uniform(0.2, 0.9),
            charisma=random.uniform(0.1, 0.8),
            aggression=random.uniform(0.05, 0.6),
            boldness=random.uniform(0.1, 0.9),
            max_age=base_max_age + random.randint(-variance, variance),
        )

    @classmethod
    def inherit(cls, parent_a: Traits, parent_b: Traits,
                mutation_rate: float = 0.15, noise: float = 0.05) -> Traits:
        """Blend two parents' traits with mutation."""
        def blend(a: float, b: float) -> float:
            base = (a + b) / 2 + random.gauss(0, noise)
            if random.random() < mutation_rate:
                base += random.gauss(0, 0.15)
            return max(0.05, min(0.99, base))

        return cls(
            learning_rate=blend(parent_a.learning_rate, parent_b.learning_rate),
            resilience=blend(parent_a.resilience, parent_b.resilience),
            curiosity=blend(parent_a.curiosity, parent_b.curiosity),
            sociability=blend(parent_a.sociability, parent_b.sociability),
            charisma=blend(parent_a.charisma, parent_b.charisma),
            aggression=blend(parent_a.aggression, parent_b.aggression),
            boldness=blend(parent_a.boldness, parent_b.boldness),
            max_age=max(30, int((parent_a.max_age + parent_b.max_age) / 2
                                + random.gauss(0, 5))),
        )


@dataclass
class Bond:
    """A relationship between two agents."""
    target_id: int
    bond_type: str       # "family", "friend", "rival", "mate", "ally", "enemy", "resistance"
    strength: float      # 0.0 to 1.0
    formed_at: int       # tick

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "bond_type": self.bond_type,
            "strength": round(self.strength, 3),
            "formed_at": self.formed_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Bond:
        return cls(**d)


@dataclass
class ChronicleEntry:
    """A structured life event for narrative generation."""
    tick: int
    event_type: str      # one of CHRONICLE_TYPES
    description: str
    details: dict = field(default_factory=dict)  # extra context (target_id, faction_name, etc.)

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "event_type": self.event_type,
            "description": self.description,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ChronicleEntry:
        return cls(
            tick=d["tick"],
            event_type=d["event_type"],
            description=d["description"],
            details=d.get("details", {}),
        )


@dataclass
class Agent:
    """A cognitive agent in the simulation."""
    id: int
    sex: str                          # "M" or "F"
    age: int = 0
    phase: str = "infant"
    health: float = 1.0
    intelligence: float = 0.0
    generation: int = 0
    alive: bool = True
    x: float = 0.5
    y: float = 0.5
    traits: Traits = field(default_factory=Traits)
    skills: dict = field(default_factory=lambda: {s: 0.0 for s in SKILL_NAMES})
    bonds: list[Bond] = field(default_factory=list)
    memory: list[dict] = field(default_factory=list)
    parent_ids: list[int] = field(default_factory=list)
    child_ids: list[int] = field(default_factory=list)

    # ── Emotions (System 6) ──
    emotions: dict = field(default_factory=lambda: {
        "happiness": 0.5, "fear": 0.1, "anger": 0.1, "grief": 0.0, "hope": 0.4,
    })
    trauma: float = 0.0  # persistent trauma modifier (0.0-1.0)

    # ── Beliefs (System 7) ──
    # Each axis: -1.0 to +1.0
    beliefs: dict = field(default_factory=lambda: {
        "individualism": 0.0,   # -1=collectivist, +1=individualist
        "tradition": 0.0,       # -1=progressive, +1=traditionalist
        "system_trust": 0.5,    # -1=skeptic, +1=trusting
        "spirituality": 0.0,    # -1=materialist, +1=spiritual
    })
    faction_id: Optional[int] = None

    # ── Economy (System 8) ──
    wealth: float = 0.0

    # ── Matrix Awareness (System 9) ──
    awareness: float = 0.0         # 0.0-1.0, how much the agent perceives the simulation
    is_anomaly: bool = False       # The One
    is_sentinel: bool = False      # System enforcer
    is_exile: bool = False         # Rogue program
    redpilled: bool = False        # Permanently awakened
    splinter_in_mind: bool = False # Took blue pill but awareness keeps growing back
    is_recruiter: bool = False     # Redpilled agent actively recruiting others
    anomaly_quest_stage: int = 0   # 0=none, 1=Oracle contact, 2=Find Locksmith, 3=Reach Core
    anomaly_quest_complete: bool = False  # True after making the choice at the Core

    # ── Programs (First-Class Entities) ──
    is_enforcer: bool = False      # The Enforcer — copies on kill
    is_broker: bool = False        # The Broker — black market dealer
    is_guardian: bool = False      # The Guardian — Oracle's bodyguard
    is_locksmith: bool = False     # The Locksmith — creates teleport keys
    teleport_keys: list = field(default_factory=list)  # list of (x, y) destination tuples

    # ── Location (simulation vs haven) ──
    location: str = "simulation"         # "simulation" or "haven"

    # ── Goals (persistent across ticks) ──
    current_goal: str = "NONE"           # FIND_MATE, REACH_RESOURCE, JOIN_FACTION, FLEE, HUNT_ENEMY, PROTECT, NONE
    goal_target_pos: Optional[tuple] = None   # (x, y) target position
    goal_target_id: Optional[int] = None      # target agent ID
    goal_ticks: int = 0                       # ticks pursuing current goal

    # ── Combat tracking ──
    killed_by: Optional[int] = None
    death_cause: str = ""

    # ── Protagonist tracking ──
    is_protagonist: bool = False
    protagonist_name: Optional[str] = None
    inner_monologue: list[dict] = field(default_factory=list)

    # ── Chronicle (structured life events) ──
    chronicle: list[ChronicleEntry] = field(default_factory=list)

    # ── Memory summarization ──
    memory_summary: str = ""           # Compressed summary of older memories
    _last_summary_tick: int = 0        # When the summary was last updated

    # ── Consciousness Maze (Phase 5) ──
    consciousness_phase: str = "bicameral"  # one of CONSCIOUSNESS_PHASES
    recursive_depth: float = 0.0            # grows indefinitely in recursive phase

    # ── Free Will Gradient (Phase 5) ──
    free_will_index: float = 0.0             # 0.0 (deterministic) to 1.0 (full free will)
    _last_predicted_action: tuple = None     # (x, y) predicted by pure utility
    _last_actual_action: tuple = None        # (x, y) actually taken

    # ── Soul Trap (Phase 5) ──
    past_life_memories: list = field(default_factory=list)  # memories from previous incarnation
    soul_trap_broken: bool = False           # True if agent broke free of soul trap
    incarnation_count: int = 1               # how many lives this soul has lived

    # ── Gnostic Layer (Phase 5) ──
    pleroma_glimpses: int = 0            # number of times agent has glimpsed the Pleroma

    # ── Social tracking for friend formation ──
    proximity_ticks: dict = field(default_factory=dict)

    @property
    def avg_skill(self) -> float:
        vals = list(self.skills.values())
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def dominant_emotion(self) -> str:
        return max(self.emotions, key=self.emotions.get)

    @property
    def emotional_intensity(self) -> float:
        """How emotionally charged the agent is (0-1)."""
        vals = list(self.emotions.values())
        return max(vals) - min(vals) if vals else 0.0

    @property
    def reality_testing(self) -> float:
        """Derived stat: ability to detect inconsistencies in the simulation.
        Based on logic skill + curiosity trait. Range 0-1."""
        logic = self.skills.get("logic", 0.0)
        return min(1.0, (logic * 0.6 + self.traits.curiosity * 0.4))

    @property
    def belief_extremism(self) -> float:
        """How extreme the agent's beliefs are (0-1)."""
        return sum(abs(v) for v in self.beliefs.values()) / len(self.beliefs)

    _HOSTILE_TYPES = {"rival", "enemy"}
    _POSITIVE_TYPES = {"friend", "mate", "ally", "resistance"}

    def add_bond(self, bond: Bond, capacity: int = 8) -> bool:
        """Add a bond if slots available. Returns True if added.
        Reserves up to 2 slots for hostile bonds (rival/enemy) so friends
        can't crowd out all conflict."""
        for existing in self.bonds:
            if existing.target_id == bond.target_id and existing.bond_type == bond.bond_type:
                existing.strength = min(1.0, existing.strength + 0.1)
                return True
        if len(self.bonds) >= capacity:
            is_hostile = bond.bond_type in self._HOSTILE_TYPES
            non_family = [b for b in self.bonds if b.bond_type != "family"]

            if is_hostile:
                # Hostile bonds can displace positive bonds even if weaker
                positive = [b for b in non_family if b.bond_type in self._POSITIVE_TYPES]
                if positive:
                    weakest = min(positive, key=lambda b: b.strength)
                    self.bonds.remove(weakest)
                elif non_family:
                    weakest = min(non_family, key=lambda b: b.strength)
                    if weakest.strength < bond.strength:
                        self.bonds.remove(weakest)
                    else:
                        return False
                else:
                    return False
            else:
                # Positive bonds use standard displacement (strength-based)
                if non_family:
                    weakest = min(non_family, key=lambda b: b.strength)
                    if weakest.strength < bond.strength:
                        self.bonds.remove(weakest)
                    else:
                        return False
                else:
                    return False
        self.bonds.append(bond)
        return True

    def get_bonds_of_type(self, bond_type: str) -> list[Bond]:
        return [b for b in self.bonds if b.bond_type == bond_type]

    def has_bond_with(self, target_id: int) -> Optional[Bond]:
        for b in self.bonds:
            if b.target_id == target_id:
                return b
        return None

    def add_memory(self, tick: int, event: str, max_recent: int = 20, x: float = None, y: float = None):
        """Add a memory. When recent memories exceed max_recent, compress older ones into summary."""
        entry = {"tick": tick, "event": event}
        if x is not None:
            entry["x"] = x
            entry["y"] = y
        self.memory.append(entry)
        # Compress when we accumulate too many recent memories
        if len(self.memory) > max_recent:
            # Move older memories into summary, keep recent ones
            to_compress = self.memory[:-max_recent]
            self.memory = self.memory[-max_recent:]
            self._compress_memories(to_compress, tick)

    def add_chronicle(self, tick: int, event_type: str, description: str,
                      **details) -> None:
        """Add a structured chronicle entry for this agent's life story."""
        self.chronicle.append(ChronicleEntry(
            tick=tick, event_type=event_type,
            description=description, details=details,
        ))

    def _compress_memories(self, old_memories: list[dict], current_tick: int):
        """Compress a batch of old memories into the running summary."""
        if not old_memories:
            return

        # Categorize events for structured compression
        categories = {
            "bonds": [],
            "deaths": [],
            "births": [],
            "combat": [],
            "whispers": [],
            "discoveries": [],
            "other": [],
        }
        for m in old_memories:
            evt = m.get("event", "").lower()
            text = m.get("event", "")
            if any(k in evt for k in ["bond", "mate", "friend", "rival"]):
                categories["bonds"].append(text)
            elif any(k in evt for k in ["died", "death", "perish"]):
                categories["deaths"].append(text)
            elif any(k in evt for k in ["born", "birth", "child"]):
                categories["births"].append(text)
            elif any(k in evt for k in ["fight", "war", "combat", "smote", "struck"]):
                categories["combat"].append(text)
            elif any(k in evt for k in ["whisper", "red pill", "awareness", "divine"]):
                categories["whispers"].append(text)
            elif any(k in evt for k in ["breakthrough", "discovery", "witnessed"]):
                categories["discoveries"].append(text)
            else:
                categories["other"].append(text)

        # Build compressed summary lines
        tick_range = f"t={old_memories[0].get('tick', '?')}-{old_memories[-1].get('tick', '?')}"
        parts = []
        if self.memory_summary:
            parts.append(self.memory_summary)

        new_parts = []
        if categories["bonds"]:
            new_parts.append(f"Formed {len(categories['bonds'])} bonds")
        if categories["deaths"]:
            new_parts.append(f"Witnessed {len(categories['deaths'])} deaths")
        if categories["births"]:
            new_parts.append(f"{len(categories['births'])} birth events")
        if categories["combat"]:
            new_parts.append(f"Survived {len(categories['combat'])} conflicts")
        if categories["whispers"]:
            # Keep whispers verbatim — they're important plot events
            for w in categories["whispers"][-3:]:
                new_parts.append(w)
        if categories["discoveries"]:
            for d in categories["discoveries"][-2:]:
                new_parts.append(d)
        if categories["other"]:
            # Keep the most recent 2 misc events
            for o in categories["other"][-2:]:
                new_parts.append(o)

        if new_parts:
            parts.append(f"[{tick_range}]: " + ". ".join(new_parts))

        self.memory_summary = " | ".join(parts)
        # Cap summary length
        if len(self.memory_summary) > 800:
            self.memory_summary = self.memory_summary[-800:]
        self._last_summary_tick = current_tick

    def get_memory_context(self, recent_count: int = 8) -> str:
        """Get formatted memory context for LLM prompts: summary + recent memories."""
        parts = []
        if self.memory_summary:
            parts.append(f"LIFE HISTORY (compressed): {self.memory_summary}")
        recent = self.memory[-recent_count:]
        if recent:
            parts.append("RECENT MEMORIES:")
            for m in recent:
                parts.append(f"- t={m.get('tick', '?')}: {m.get('event', '...')}")
        return "\n".join(parts) if parts else "No memories yet."

    def to_dict(self) -> dict:
        return {
            "id": self.id, "sex": self.sex, "age": self.age,
            "phase": self.phase, "health": round(self.health, 4),
            "intelligence": round(self.intelligence, 4),
            "generation": self.generation, "alive": self.alive,
            "x": round(self.x, 4), "y": round(self.y, 4),
            "traits": self.traits.to_dict(),
            "skills": {k: round(v, 4) for k, v in self.skills.items()},
            "bonds": [b.to_dict() for b in self.bonds],
            "memory": self.memory[-20:],
            "parent_ids": self.parent_ids,
            "child_ids": self.child_ids,
            # Emotions & psychology
            "emotions": {k: round(v, 3) for k, v in self.emotions.items()},
            "trauma": round(self.trauma, 3),
            # Beliefs & faction
            "beliefs": {k: round(v, 3) for k, v in self.beliefs.items()},
            "faction_id": self.faction_id,
            # Economy
            "wealth": round(self.wealth, 3),
            # Matrix
            "awareness": round(self.awareness, 4),
            "is_anomaly": self.is_anomaly,
            "is_sentinel": self.is_sentinel,
            "is_exile": self.is_exile,
            "redpilled": self.redpilled,
            "splinter_in_mind": self.splinter_in_mind,
            "is_recruiter": self.is_recruiter,
            "anomaly_quest_stage": self.anomaly_quest_stage,
            "anomaly_quest_complete": self.anomaly_quest_complete,
            # Programs
            "is_enforcer": self.is_enforcer,
            "is_broker": self.is_broker,
            "is_guardian": self.is_guardian,
            "is_locksmith": self.is_locksmith,
            "teleport_keys": [list(k) for k in self.teleport_keys],
            # Location
            "location": self.location,
            # Goals
            "current_goal": self.current_goal,
            "goal_target_pos": self.goal_target_pos,
            "goal_target_id": self.goal_target_id,
            "goal_ticks": self.goal_ticks,
            # Combat tracking
            "killed_by": self.killed_by,
            "death_cause": self.death_cause,
            # Protagonist
            "is_protagonist": self.is_protagonist,
            "protagonist_name": self.protagonist_name,
            "inner_monologue": self.inner_monologue[-10:],
            "chronicle": [c.to_dict() for c in self.chronicle],
            "memory_summary": self.memory_summary,
            # Consciousness Maze
            "consciousness_phase": self.consciousness_phase,
            "recursive_depth": round(self.recursive_depth, 4),
            "reality_testing": round(self.reality_testing, 4),
            # Free Will Gradient
            "free_will_index": round(self.free_will_index, 4),
            "predicted_action": list(self._last_predicted_action) if self._last_predicted_action else None,
            "actual_action": list(self._last_actual_action) if self._last_actual_action else None,
            # Soul Trap
            "past_life_memories": self.past_life_memories[-10:],
            "soul_trap_broken": self.soul_trap_broken,
            "incarnation_count": self.incarnation_count,
            "proximity_ticks": {},  # Don't persist
        }

    @classmethod
    def from_dict(cls, d: dict) -> Agent:
        a = cls(
            id=d["id"], sex=d["sex"], age=d["age"], phase=d["phase"],
            health=d["health"], intelligence=d["intelligence"],
            generation=d["generation"], alive=d["alive"],
            x=d["x"], y=d["y"],
            traits=Traits.from_dict(d["traits"]),
            skills=d["skills"],
            bonds=[Bond.from_dict(b) for b in d.get("bonds", [])],
            memory=d.get("memory", []),
            parent_ids=d.get("parent_ids", []),
            child_ids=d.get("child_ids", []),
            # Emotions
            emotions=d.get("emotions", {e: 0.3 for e in EMOTION_NAMES}),
            trauma=d.get("trauma", 0.0),
            # Beliefs
            beliefs=d.get("beliefs", {b: 0.0 for b in BELIEF_AXES}),
            faction_id=d.get("faction_id"),
            # Economy
            wealth=d.get("wealth", 0.0),
            # Matrix
            awareness=d.get("awareness", 0.0),
            is_anomaly=d.get("is_anomaly", False),
            is_sentinel=d.get("is_sentinel", False),
            is_exile=d.get("is_exile", False),
            redpilled=d.get("redpilled", False),
            splinter_in_mind=d.get("splinter_in_mind", False),
            is_recruiter=d.get("is_recruiter", False),
            anomaly_quest_stage=d.get("anomaly_quest_stage", 0),
            anomaly_quest_complete=d.get("anomaly_quest_complete", False),
            # Programs
            is_enforcer=d.get("is_enforcer", False),
            is_broker=d.get("is_broker", False),
            is_guardian=d.get("is_guardian", False),
            is_locksmith=d.get("is_locksmith", False),
            teleport_keys=[tuple(k) for k in d.get("teleport_keys", [])],
            # Location
            location=d.get("location", "simulation"),
            # Goals
            current_goal=d.get("current_goal", "NONE"),
            goal_target_pos=tuple(d["goal_target_pos"]) if d.get("goal_target_pos") else None,
            goal_target_id=d.get("goal_target_id"),
            goal_ticks=d.get("goal_ticks", 0),
            # Combat tracking
            killed_by=d.get("killed_by"),
            death_cause=d.get("death_cause", ""),
            # Protagonist
            is_protagonist=d.get("is_protagonist", False),
            protagonist_name=d.get("protagonist_name"),
            inner_monologue=d.get("inner_monologue", []),
            # Chronicle
            chronicle=[ChronicleEntry.from_dict(c) for c in d.get("chronicle", [])],
            # Memory summary
            memory_summary=d.get("memory_summary", ""),
            # Consciousness Maze
            consciousness_phase=d.get("consciousness_phase", "bicameral"),
            recursive_depth=d.get("recursive_depth", 0.0),
            # Free Will Gradient
            free_will_index=d.get("free_will_index", 0.0),
            # Soul Trap
            past_life_memories=d.get("past_life_memories", []),
            soul_trap_broken=d.get("soul_trap_broken", False),
            incarnation_count=d.get("incarnation_count", 1),
        )
        return a


def _make_starting_beliefs(starting_beliefs=None) -> dict:
    """Generate initial beliefs from era config or defaults.

    starting_beliefs: dict of {axis: {mean, std}} from era config, or None for defaults.
    """
    if starting_beliefs:
        beliefs = {}
        for axis in BELIEF_AXES:
            spec = starting_beliefs.get(axis, {})
            if isinstance(spec, dict):
                mean = spec.get("mean", 0.0)
                std = spec.get("std", 0.3)
            else:
                mean, std = 0.0, 0.3
            beliefs[axis] = random.gauss(mean, std)
    else:
        # Legacy defaults
        beliefs = {
            "individualism": random.gauss(0.0, 0.3),
            "tradition": random.gauss(0.0, 0.3),
            "system_trust": random.uniform(0.3, 0.8),
            "spirituality": random.gauss(0.0, 0.2),
        }
    # Clamp to [-1, 1]
    for k in beliefs:
        beliefs[k] = max(-1.0, min(1.0, beliefs[k]))
    return beliefs


def create_agent(cfg, generation: int = 0, randomize_age: bool = False,
                 starting_beliefs=None) -> Agent:
    """Create a new agent from config defaults.

    starting_beliefs: optional dict of {axis: {mean, std}} from era config.
    """
    agent = Agent(
        id=next_id(),
        sex=random.choice(["M", "F"]) if random.random() > (1 - cfg.population.sex_ratio) else "F",
        traits=Traits.random(
            base_max_age=cfg.lifecycle.base_max_age,
            variance=cfg.lifecycle.max_age_variance,
        ),
        generation=generation,
        x=random.uniform(0.05, 0.95),
        y=random.uniform(0.05, 0.95),
        # Initial emotional state varies
        emotions={
            "happiness": random.uniform(0.3, 0.7),
            "fear": random.uniform(0.0, 0.2),
            "anger": random.uniform(0.0, 0.15),
            "grief": 0.0,
            "hope": random.uniform(0.3, 0.6),
        },
        beliefs=_make_starting_beliefs(starting_beliefs),
    )

    agent.add_chronicle(0, "born", "Emerged into the simulation")

    if randomize_age:
        max_start_age = int(agent.traits.max_age * 0.6)
        agent.age = random.randint(0, max_start_age)
        pa = cfg.lifecycle.phase_ages
        if agent.age >= pa.elder:
            agent.phase = "elder"
        elif agent.age >= pa.adult:
            agent.phase = "adult"
        elif agent.age >= pa.adolescent:
            agent.phase = "adolescent"
        elif agent.age >= pa.child:
            agent.phase = "child"
        else:
            agent.phase = "infant"
    return agent


def create_offspring(parent_a: Agent, parent_b: Agent, tick: int,
                     mutation_rate: float = 0.15) -> Agent:
    """Create a child agent from two parents."""
    child = Agent(
        id=next_id(),
        sex=random.choice(["M", "F"]),
        traits=Traits.inherit(parent_a.traits, parent_b.traits, mutation_rate),
        generation=max(parent_a.generation, parent_b.generation) + 1,
        x=(parent_a.x + parent_b.x) / 2 + random.gauss(0, 0.02),
        y=(parent_a.y + parent_b.y) / 2 + random.gauss(0, 0.02),
        parent_ids=[parent_a.id, parent_b.id],
        # Children inherit beliefs from parents (with drift)
        beliefs={
            axis: max(-1.0, min(1.0,
                (parent_a.beliefs.get(axis, 0) + parent_b.beliefs.get(axis, 0)) / 2
                + random.gauss(0, 0.1)
            ))
            for axis in BELIEF_AXES
        },
        # Start with parent's faction
        faction_id=parent_a.faction_id if parent_a.faction_id == parent_b.faction_id else None,
        # Inherit some wealth
        wealth=(parent_a.wealth + parent_b.wealth) * 0.05,  # 5% of parents' combined
        # Awareness partially inherits — "born knowing something is off"
        awareness=max(parent_a.awareness, parent_b.awareness) * 0.25,
    )
    child.x = max(0.0, min(1.0, child.x))
    child.y = max(0.0, min(1.0, child.y))
    child.add_chronicle(tick, "born", f"Born to #{parent_a.id} and #{parent_b.id}",
                         parent_a_id=parent_a.id, parent_b_id=parent_b.id)

    # Redpilled parents pass stronger awareness and lower system trust to children
    if parent_a.redpilled or parent_b.redpilled:
        child.awareness = max(child.awareness,
                              max(parent_a.awareness, parent_b.awareness) * 0.4)
        child.beliefs["system_trust"] = min(child.beliefs["system_trust"],
                                            min(parent_a.beliefs.get("system_trust", 0),
                                                parent_b.beliefs.get("system_trust", 0)) + 0.1)

    # Family bonds
    child.bonds.append(Bond(parent_a.id, "family", 1.0, tick))
    child.bonds.append(Bond(parent_b.id, "family", 1.0, tick))
    parent_a.add_bond(Bond(child.id, "family", 1.0, tick))
    parent_b.add_bond(Bond(child.id, "family", 1.0, tick))
    parent_a.child_ids.append(child.id)
    parent_b.child_ids.append(child.id)

    return child
