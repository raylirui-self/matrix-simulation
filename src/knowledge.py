"""
Knowledge transfer — parent teaching, cultural memory, social amplifier.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from src.agents import Agent, SKILL_NAMES


@dataclass
class FactionMemory:
    """Faction-level knowledge pool — factions maintain independent knowledge traditions."""
    faction_id: int
    skill_floors: dict = field(default_factory=lambda: {s: 0.0 for s in SKILL_NAMES})
    knowledge_pool: dict = field(default_factory=lambda: {s: 0.0 for s in SKILL_NAMES})

    def on_member_death(self, agent: Agent, contribution_rate: float):
        """Dying faction members contribute to faction pool."""
        for skill, value in agent.skills.items():
            floor = self.skill_floors.get(skill, 0.0)
            contribution = max(0, value - floor) * contribution_rate * 1.5  # factions preserve more
            self.knowledge_pool[skill] = self.knowledge_pool.get(skill, 0.0) + contribution

    def tick(self, floor_cap: float, absorption_rate: float, drain_rate: float, decay_rate: float):
        """Update faction floors."""
        for skill in SKILL_NAMES:
            pool = self.knowledge_pool.get(skill, 0.0)
            if pool > 0:
                push = pool * absorption_rate * 1.5  # factions absorb faster
                self.skill_floors[skill] = min(floor_cap, self.skill_floors[skill] + push)
                self.knowledge_pool[skill] *= drain_rate
            self.skill_floors[skill] = max(0.0, self.skill_floors[skill] - decay_rate * 0.5)  # factions decay slower

    def apply_to_member(self, agent: Agent):
        """Boost member skills if below faction floor."""
        for skill in SKILL_NAMES:
            floor = self.skill_floors.get(skill, 0.0)
            if agent.skills[skill] < floor:
                # Don't set to floor directly — give a boost toward it
                gap = floor - agent.skills[skill]
                agent.skills[skill] += gap * 0.1

    def to_dict(self) -> dict:
        return {
            "faction_id": self.faction_id,
            "skill_floors": {k: round(v, 4) for k, v in self.skill_floors.items()},
            "knowledge_pool": {k: round(v, 4) for k, v in self.knowledge_pool.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> FactionMemory:
        return cls(
            faction_id=d["faction_id"],
            skill_floors=d.get("skill_floors", {s: 0.0 for s in SKILL_NAMES}),
            knowledge_pool=d.get("knowledge_pool", {s: 0.0 for s in SKILL_NAMES}),
        )


@dataclass
class CulturalMemory:
    """Civilization-level accumulated knowledge."""
    skill_floors: dict = field(
        default_factory=lambda: {s: 0.0 for s in SKILL_NAMES}
    )
    knowledge_pool: dict = field(
        default_factory=lambda: {s: 0.0 for s in SKILL_NAMES}
    )
    floor_cap: float = 0.5
    decay_rate: float = 0.001
    contribution_rate: float = 0.05
    absorption_rate: float = 0.001
    drain_rate: float = 0.99
    # Faction-specific cultural memory pools
    faction_memories: dict[int, FactionMemory] = field(default_factory=dict)

    def on_agent_death(self, agent: Agent):
        """Dying agents contribute knowledge above the floor."""
        for skill, value in agent.skills.items():
            floor = self.skill_floors.get(skill, 0.0)
            contribution = max(0, value - floor) * self.contribution_rate
            self.knowledge_pool[skill] = self.knowledge_pool.get(skill, 0.0) + contribution

        # Also contribute to faction memory
        if agent.faction_id is not None and agent.faction_id in self.faction_memories:
            self.faction_memories[agent.faction_id].on_member_death(agent, self.contribution_rate)

    def ensure_faction_memory(self, faction_id: int):
        """Create a faction memory pool if it doesn't exist."""
        if faction_id not in self.faction_memories:
            self.faction_memories[faction_id] = FactionMemory(faction_id=faction_id)

    def tick(self):
        """Update floors from pool, apply decay."""
        for skill in SKILL_NAMES:
            pool = self.knowledge_pool.get(skill, 0.0)
            if pool > 0:
                push = pool * self.absorption_rate
                self.skill_floors[skill] = min(
                    self.floor_cap, self.skill_floors[skill] + push
                )
                self.knowledge_pool[skill] *= self.drain_rate
            # Decay if not reinforced
            self.skill_floors[skill] = max(
                0.0, self.skill_floors[skill] - self.decay_rate
            )

        # Tick faction memories
        for fm in self.faction_memories.values():
            fm.tick(self.floor_cap, self.absorption_rate, self.drain_rate, self.decay_rate)

    def apply_to_newborn(self, agent: Agent):
        """Set newborn skills to at least the cultural floor."""
        for skill in SKILL_NAMES:
            floor = self.skill_floors.get(skill, 0.0)
            if agent.skills[skill] < floor:
                agent.skills[skill] = floor

    def apply_faction_knowledge(self, agents: list[Agent]):
        """Apply faction-specific knowledge to faction members each tick."""
        for agent in agents:
            if agent.alive and agent.faction_id is not None:
                fm = self.faction_memories.get(agent.faction_id)
                if fm:
                    fm.apply_to_member(agent)

    def to_dict(self) -> dict:
        return {
            "skill_floors": {k: round(v, 4) for k, v in self.skill_floors.items()},
            "knowledge_pool": {k: round(v, 4) for k, v in self.knowledge_pool.items()},
            "faction_memories": {str(k): v.to_dict() for k, v in self.faction_memories.items()},
        }

    @classmethod
    def from_dict(cls, d: dict, cfg) -> CulturalMemory:
        cm = cls(
            skill_floors=d.get("skill_floors", {s: 0.0 for s in SKILL_NAMES}),
            knowledge_pool=d.get("knowledge_pool", {s: 0.0 for s in SKILL_NAMES}),
            floor_cap=cfg.knowledge.cultural_memory.floor_cap,
            decay_rate=cfg.knowledge.cultural_memory.decay_rate,
            contribution_rate=cfg.knowledge.cultural_memory.contribution_on_death,
            absorption_rate=cfg.knowledge.cultural_memory.pool_absorption_rate,
            drain_rate=cfg.knowledge.cultural_memory.pool_drain_rate,
        )
        # Restore faction memories
        for fid_str, fm_data in d.get("faction_memories", {}).items():
            cm.faction_memories[int(fid_str)] = FactionMemory.from_dict(fm_data)
        return cm

    @classmethod
    def from_config(cls, cfg) -> CulturalMemory:
        cm_cfg = cfg.knowledge.cultural_memory
        return cls(
            floor_cap=cm_cfg.floor_cap,
            decay_rate=cm_cfg.decay_rate,
            contribution_rate=cm_cfg.contribution_on_death,
            absorption_rate=cm_cfg.pool_absorption_rate,
            drain_rate=cm_cfg.pool_drain_rate,
        )


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def social_transfer_multiplier(agent: Agent, cfg) -> float:
    """Social skill and network amplify knowledge absorption."""
    amp_cfg = cfg.knowledge.social_amplifier
    if not amp_cfg.enabled:
        return 1.0

    base = 1.0
    social_bonus = agent.skills.get("social", 0) * amp_cfg.social_skill_bonus
    friend_count = sum(1 for b in agent.bonds if b.bond_type == "friend")
    network_bonus = min(
        friend_count * amp_cfg.network_bonus_per_friend,
        amp_cfg.network_bonus_cap,
    )
    return base + social_bonus + network_bonus


def parent_teaching(child: Agent, agents_by_id: dict, tick: int, cfg) -> dict:
    """Apply parent teaching bonuses. Returns skill bonuses applied."""
    pt_cfg = cfg.knowledge.parent_teaching
    if not pt_cfg.enabled or child.phase not in ("infant", "child", "adolescent"):
        return {}

    bonuses = {s: 0.0 for s in SKILL_NAMES}
    for bond in child.bonds:
        if bond.bond_type != "family" or bond.target_id in child.child_ids:
            continue  # only learn from parents, not children
        parent = agents_by_id.get(bond.target_id)
        if not parent or not parent.alive:
            continue
        dist = spatial_distance(child, parent)
        if dist > pt_cfg.proximity_radius:
            continue

        # Parent teaches their top N skills
        sorted_skills = sorted(parent.skills.items(), key=lambda x: -x[1])
        for skill_name, skill_val in sorted_skills[:pt_cfg.top_skills_taught]:
            transfer = skill_val * pt_cfg.transfer_rate * bond.strength
            bonuses[skill_name] += transfer

    # Apply social amplifier
    multiplier = social_transfer_multiplier(child, cfg)
    return {k: v * multiplier for k, v in bonuses.items()}