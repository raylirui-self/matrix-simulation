"""
System 11: Communication & Information — information objects, network propagation,
rumors, misinformation, propaganda, and secrets.

In Matrix terms: the system injects control narratives that suppress awareness
and reinforce faction conflicts.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from src.agents import Agent


@dataclass
class InfoObject:
    """A piece of information that propagates through the network."""
    id: int
    created_at: int
    origin_agent_id: int
    info_type: str         # "knowledge", "rumor", "warning", "propaganda", "secret", "system_narrative"
    content: str           # Human-readable description
    skill_target: Optional[str] = None  # Which skill this relates to
    truth_value: float = 1.0           # 0=false, 1=true (degrades with transmission)
    potency: float = 1.0              # How strongly this affects recipients
    hops: int = 0                      # How many times it's been transmitted
    max_hops: int = 10                 # Dies after this many transmissions
    faction_id: Optional[int] = None   # If faction-specific
    is_secret: bool = False            # Only shared through specific bond types

    def to_dict(self) -> dict:
        return {
            "id": self.id, "created_at": self.created_at,
            "origin_agent_id": self.origin_agent_id,
            "info_type": self.info_type, "content": self.content,
            "skill_target": self.skill_target,
            "truth_value": round(self.truth_value, 3),
            "potency": round(self.potency, 3),
            "hops": self.hops, "max_hops": self.max_hops,
            "faction_id": self.faction_id,
            "is_secret": self.is_secret,
        }

    @classmethod
    def from_dict(cls, d: dict) -> InfoObject:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


_info_id_counter = 0


def _next_info_id() -> int:
    global _info_id_counter
    _info_id_counter += 1
    return _info_id_counter


def set_info_id_counter(val: int):
    global _info_id_counter
    _info_id_counter = val


def get_info_id_counter() -> int:
    return _info_id_counter


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def process_communication(agents: list[Agent], info_objects: list[InfoObject],
                          agent_info: dict, tick: int, cfg) -> dict:
    """Run one tick of information propagation.

    agent_info: dict mapping agent_id -> set of info_ids they know about.

    Returns stats.
    """
    alive = [a for a in agents if a.alive and not a.is_sentinel]
    comm_cfg = cfg.communication

    stats = {
        "info_created": 0, "info_transmitted": 0,
        "info_mutated": 0, "info_expired": 0,
        "propaganda_spread": 0, "rumors_active": 0,
    }

    if not alive:
        return stats

    # ── Phase 1: Natural information creation ──
    if tick % comm_cfg.info_creation_interval == 0:
        for a in alive:
            # High-intelligence agents create knowledge
            if a.intelligence > 0.5 and random.random() < a.intelligence * 0.1:
                # Find their best skill
                best_skill = max(a.skills, key=a.skills.get)
                info = InfoObject(
                    id=_next_info_id(),
                    created_at=tick,
                    origin_agent_id=a.id,
                    info_type="knowledge",
                    content=f"Insight about {best_skill} (from #{a.id})",
                    skill_target=best_skill,
                    truth_value=0.8 + a.intelligence * 0.2,
                    potency=a.intelligence * 0.5,
                )
                info_objects.append(info)
                agent_info.setdefault(a.id, set()).add(info.id)
                stats["info_created"] += 1

            # Prophets / faction leaders create propaganda
            if (a.faction_id is not None and a.traits.charisma > 0.6
                    and random.random() < a.traits.charisma * 0.05):
                info = InfoObject(
                    id=_next_info_id(),
                    created_at=tick,
                    origin_agent_id=a.id,
                    info_type="propaganda",
                    content=f"Faction #{a.faction_id} ideology (by #{a.id})",
                    faction_id=a.faction_id,
                    truth_value=0.5,  # Propaganda is half-truth
                    potency=a.traits.charisma,
                )
                info_objects.append(info)
                agent_info.setdefault(a.id, set()).add(info.id)
                stats["info_created"] += 1

    # ── Phase 2: Information propagation through bonds ──
    transmission_radius = comm_cfg.transmission_radius

    # Build spatial index
    bucket_size = transmission_radius * 2
    grid = {}
    for a in alive:
        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        grid.setdefault(key, []).append(a)

    for a in alive:
        known = agent_info.get(a.id, set())
        if not known:
            continue

        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        nearby = []
        for dk_r in [-1, 0, 1]:
            for dk_c in [-1, 0, 1]:
                nearby.extend(grid.get((key[0] + dk_r, key[1] + dk_c), []))

        for b in nearby:
            if b.id == a.id or not b.alive:
                continue

            bond = a.has_bond_with(b.id)
            if not bond:
                continue

            dist = spatial_distance(a, b)
            if dist > transmission_radius:
                continue

            b_known = agent_info.setdefault(b.id, set())

            # Transmit info that b doesn't know yet
            for info_id in list(known):
                if info_id in b_known:
                    continue

                info = next((i for i in info_objects if i.id == info_id), None)
                if not info or info.hops >= info.max_hops:
                    continue

                # Secret info only through matching bond types
                if info.is_secret and bond.bond_type not in ("resistance", "family"):
                    continue

                # Faction propaganda only spreads to same faction or unaffiliated
                if info.info_type == "propaganda" and info.faction_id:
                    if b.faction_id is not None and b.faction_id != info.faction_id:
                        continue

                # Transmission chance depends on bond strength, social skill, charisma
                chance = (
                    bond.strength * 0.4 +
                    a.traits.charisma * 0.3 +
                    a.skills.get("social", 0) * 0.3
                ) * comm_cfg.transmission_rate

                if random.random() > chance:
                    continue

                # Transmit — recipient learns about this info
                b_known.add(info_id)
                stats["info_transmitted"] += 1

                # Truth degrades with each hop (telephone game)
                # We increment hops on the original — this means later recipients
                # receive a more degraded version, modeling the telephone game correctly
                info.hops += 1
                if random.random() < comm_cfg.mutation_rate:
                    degradation = random.uniform(0.05, 0.15)
                    if info.hops < info.max_hops:
                        info.truth_value = max(0.0, info.truth_value - degradation)
                        info.potency = max(0.1, info.potency * random.uniform(0.85, 1.1))
                    stats["info_mutated"] += 1

                if info.info_type == "propaganda":
                    stats["propaganda_spread"] += 1

    # ── Phase 3: Information effects on agents ──
    for a in alive:
        known = agent_info.get(a.id, set())
        for info_id in known:
            info = next((i for i in info_objects if i.id == info_id), None)
            if not info:
                continue

            # Knowledge boosts skills
            if info.info_type == "knowledge" and info.skill_target:
                boost = info.potency * info.truth_value * comm_cfg.knowledge_skill_boost
                if info.skill_target in a.skills:
                    a.skills[info.skill_target] = min(1.0, a.skills[info.skill_target] + boost)

            # Propaganda shifts beliefs toward faction
            if info.info_type == "propaganda" and info.faction_id:
                # Only affects agents in the same faction or unaffiliated
                if a.faction_id == info.faction_id or a.faction_id is None:
                    # Stubborn agents resist
                    resistance = abs(a.beliefs.get("tradition", 0)) * 0.3
                    effect = info.potency * (1.0 - resistance) * 0.01
                    # Propaganda increases system trust (or decreases, depending on faction)
                    a.beliefs["system_trust"] = max(-1.0, min(1.0,
                        a.beliefs["system_trust"] + effect * 0.1))

            # System narratives suppress awareness
            if info.info_type == "system_narrative":
                if not a.redpilled:
                    a.awareness = max(0.0, a.awareness - info.potency * 0.01)
                    a.beliefs["system_trust"] = min(1.0,
                        a.beliefs["system_trust"] + info.potency * 0.01)

            # Warnings increase fear and caution
            if info.info_type == "warning":
                a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + info.potency * 0.05)

    # ── Phase 4: System narrative injection ──
    if tick % comm_cfg.system_narrative_interval == 0:
        info = InfoObject(
            id=_next_info_id(),
            created_at=tick,
            origin_agent_id=-1,  # System-generated
            info_type="system_narrative",
            content="Everything is fine. The world is as it should be.",
            truth_value=0.0,  # Complete lie
            potency=0.5,
            max_hops=20,  # Wide reach
        )
        info_objects.append(info)
        # Inject into random agents
        for a in alive:
            if not a.redpilled and random.random() < 0.3:
                agent_info.setdefault(a.id, set()).add(info.id)
        stats["info_created"] += 1

    # ── Phase 5: Expire old info ──
    expired = [i for i in info_objects if (tick - i.created_at) > comm_cfg.info_lifetime]
    for info in expired:
        info_objects.remove(info)
        # Clean up from agent_info
        for agent_id in list(agent_info.keys()):
            agent_info[agent_id].discard(info.id)
        stats["info_expired"] += 1

    stats["rumors_active"] = len(info_objects)
    return stats
