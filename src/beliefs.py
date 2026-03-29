"""
System 7: Beliefs, Ideology & Factions — memetic transmission, faction emergence,
prophets, schisms, and the ideological landscape.

In Matrix terms: the system WANTS manageable factions to keep humans divided.
Dangerous beliefs (high skepticism) risk producing agents who question reality.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from src.agents import Agent, BELIEF_AXES


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


@dataclass
class Faction:
    """An emergent group identity formed by shared beliefs."""
    id: int
    name: str
    founder_id: int
    formed_at: int
    # Core beliefs (average of members at formation)
    core_beliefs: dict = field(default_factory=lambda: {b: 0.0 for b in BELIEF_AXES})
    member_count: int = 0
    leader_id: Optional[int] = None
    territory_cells: list[tuple[int, int]] = field(default_factory=list)
    is_resistance: bool = False  # Hidden Matrix resistance faction

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "founder_id": self.founder_id,
            "formed_at": self.formed_at,
            "core_beliefs": {k: round(v, 3) for k, v in self.core_beliefs.items()},
            "member_count": self.member_count,
            "leader_id": self.leader_id,
            "territory_cells": self.territory_cells,
            "is_resistance": self.is_resistance,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Faction:
        f = cls(
            id=d["id"], name=d["name"], founder_id=d["founder_id"],
            formed_at=d["formed_at"],
            core_beliefs=d.get("core_beliefs", {b: 0.0 for b in BELIEF_AXES}),
            member_count=d.get("member_count", 0),
            leader_id=d.get("leader_id"),
            territory_cells=[tuple(c) for c in d.get("territory_cells", [])],
            is_resistance=d.get("is_resistance", False),
        )
        return f


# Faction name generators
_FACTION_PREFIXES = [
    "Iron", "Golden", "Silver", "Shadow", "Storm", "Dawn", "Crimson",
    "Ashen", "Verdant", "Obsidian", "Azure", "Ember", "Frost", "Lunar",
    "Solar", "Stone", "River", "Thunder", "Hollow", "Bright",
]
_FACTION_SUFFIXES = [
    "Covenant", "Circle", "Order", "Pact", "Alliance", "Brotherhood",
    "Commune", "Assembly", "Syndicate", "Collective", "Union", "Creed",
    "Fellowship", "Guard", "Legion", "Accord", "Band", "Tribe", "Clan",
]
_faction_id_counter = 0


def _next_faction_id() -> int:
    global _faction_id_counter
    _faction_id_counter += 1
    return _faction_id_counter


def set_faction_id_counter(val: int):
    global _faction_id_counter
    _faction_id_counter = val


def get_faction_id_counter() -> int:
    return _faction_id_counter


_used_faction_names: set[str] = set()


def _generate_faction_name() -> str:
    """Generate a unique faction name. Falls back to numbered names if all combos exhausted."""
    for _ in range(50):
        name = f"{random.choice(_FACTION_PREFIXES)} {random.choice(_FACTION_SUFFIXES)}"
        if name not in _used_faction_names:
            _used_faction_names.add(name)
            return name
    # Fallback: append a number
    base = f"{random.choice(_FACTION_PREFIXES)} {random.choice(_FACTION_SUFFIXES)}"
    counter = 2
    while f"{base} {counter}" in _used_faction_names:
        counter += 1
    name = f"{base} {counter}"
    _used_faction_names.add(name)
    return name


def belief_similarity(a: Agent, b: Agent) -> float:
    """Cosine-like similarity between two agents' belief vectors. Returns 0-1."""
    dot = sum(a.beliefs.get(ax, 0) * b.beliefs.get(ax, 0) for ax in BELIEF_AXES)
    mag_a = math.sqrt(sum(a.beliefs.get(ax, 0) ** 2 for ax in BELIEF_AXES)) or 0.001
    mag_b = math.sqrt(sum(b.beliefs.get(ax, 0) ** 2 for ax in BELIEF_AXES)) or 0.001
    return max(0.0, min(1.0, (dot / (mag_a * mag_b) + 1.0) / 2.0))


def belief_distance(beliefs_a: dict, beliefs_b: dict) -> float:
    """Euclidean distance between two belief vectors. Lower = more similar."""
    return math.sqrt(sum(
        (beliefs_a.get(ax, 0) - beliefs_b.get(ax, 0)) ** 2
        for ax in BELIEF_AXES
    ))


def process_beliefs(agents: list[Agent], factions: list[Faction],
                    tick: int, cfg) -> dict:
    """Run one tick of belief dynamics. Returns stats."""
    alive = [a for a in agents if a.alive and not a.is_sentinel]
    belief_cfg = cfg.beliefs

    stats = {
        "factions_formed": 0, "factions_dissolved": 0,
        "conversions": 0, "schisms": 0,
        "prophets_emerged": 0, "faction_count": len(factions),
    }

    if not alive:
        return stats

    # ── Phase 1: Belief drift from experience ──
    drift_rate = belief_cfg.experience_drift_rate
    for a in alive:
        # Resource scarcity → more collectivist, more traditional
        if a.health < 0.3:
            a.beliefs["individualism"] = max(-1.0, a.beliefs["individualism"] - drift_rate)
            a.beliefs["tradition"] = min(1.0, a.beliefs["tradition"] + drift_rate * 0.5)

        # Wealth → more individualist; poverty → more collectivist
        if a.wealth > 1.0:
            a.beliefs["individualism"] = min(1.0, a.beliefs["individualism"] + drift_rate * 0.5)
        elif a.wealth < 0.2 and a.phase in ("adult", "elder"):
            a.beliefs["individualism"] = max(-1.0, a.beliefs["individualism"] - drift_rate * 0.4)

        # High awareness → system skepticism, spirituality
        if a.awareness > 0.3:
            a.beliefs["system_trust"] = max(-1.0, a.beliefs["system_trust"] - drift_rate * a.awareness)
            a.beliefs["spirituality"] = min(1.0, a.beliefs["spirituality"] + drift_rate * 0.3)

        # High curiosity → progressive
        if a.traits.curiosity > 0.7:
            a.beliefs["tradition"] = max(-1.0, a.beliefs["tradition"] - drift_rate * 0.3)

        # Trauma → system distrust, spirituality
        if a.trauma > 0.3:
            a.beliefs["system_trust"] = max(-1.0, a.beliefs["system_trust"] - drift_rate * 0.5)
            a.beliefs["spirituality"] = min(1.0, a.beliefs["spirituality"] + drift_rate * 0.3)

        # Many bonds → collectivist; few bonds → individualist
        if len(a.bonds) >= 5:
            a.beliefs["individualism"] = max(-1.0, a.beliefs["individualism"] - drift_rate * 0.3)
        elif len(a.bonds) <= 1 and a.phase in ("adult", "elder"):
            a.beliefs["individualism"] = min(1.0, a.beliefs["individualism"] + drift_rate * 0.3)

        # Combat/rivalry experience → more aggressive beliefs (tradition + individualism)
        enemy_count = sum(1 for b in a.bonds if b.bond_type in ("rival", "enemy"))
        if enemy_count >= 2:
            a.beliefs["tradition"] = min(1.0, a.beliefs["tradition"] + drift_rate * 0.3)
            a.beliefs["individualism"] = min(1.0, a.beliefs["individualism"] + drift_rate * 0.2)

    # ── Phase 2: Memetic transmission through bonds ──
    # Faction members are anchored toward core beliefs (prevents convergence across factions)
    faction_map_beliefs = {f.id: f for f in factions}
    for a in alive:
        if a.faction_id is not None:
            faction = faction_map_beliefs.get(a.faction_id)
            if faction:
                anchor_rate = belief_cfg.transmission_rate * 0.5  # faction anchoring
                for axis in BELIEF_AXES:
                    core_val = faction.core_beliefs.get(axis, 0)
                    diff = core_val - a.beliefs.get(axis, 0)
                    a.beliefs[axis] = max(-1.0, min(1.0,
                        a.beliefs[axis] + diff * anchor_rate
                    ))

    transmission_rate = belief_cfg.transmission_rate
    for a in alive:
        for bond in a.bonds:
            if bond.bond_type in ("enemy",):
                continue  # Don't adopt enemy beliefs
            target = next((ag for ag in alive if ag.id == bond.target_id), None)
            if not target:
                continue

            # Stronger bonds = more influence
            influence = transmission_rate * bond.strength
            # Charismatic agents spread beliefs more effectively
            influence *= (1.0 + target.traits.charisma * 0.5)
            # Stubborn agents (high tradition) resist change
            resistance = 1.0 - abs(a.beliefs.get("tradition", 0)) * 0.3
            # Same-faction transmission is stronger, cross-faction is weaker
            if a.faction_id is not None and target.faction_id is not None:
                if a.faction_id == target.faction_id:
                    influence *= 1.5  # echo chamber effect
                else:
                    influence *= 0.3  # cross-faction resistance

            for axis in BELIEF_AXES:
                diff = target.beliefs.get(axis, 0) - a.beliefs.get(axis, 0)
                mutation = random.gauss(0, belief_cfg.transmission_noise)
                a.beliefs[axis] = max(-1.0, min(1.0,
                    a.beliefs[axis] + diff * influence * resistance + mutation
                ))

    # ── Phase 3: Faction formation ──
    # Check for faction-less agents who cluster with similar beliefs
    factionless = [a for a in alive if a.faction_id is None]
    min_faction_size = belief_cfg.min_faction_size
    formation_threshold = belief_cfg.faction_formation_similarity

    if len(factionless) >= min_faction_size and tick % belief_cfg.faction_check_interval == 0:
        # Try to form factions from clusters
        unclaimed = set(a.id for a in factionless)

        for seed in factionless:
            if seed.id not in unclaimed:
                continue
            # Find nearby agents with similar beliefs
            cluster = [seed]
            for other in factionless:
                if other.id == seed.id or other.id not in unclaimed:
                    continue
                dist = spatial_distance(seed, other)
                sim = belief_similarity(seed, other)
                if dist < belief_cfg.faction_formation_radius and sim > formation_threshold:
                    cluster.append(other)

            if len(cluster) >= min_faction_size:
                # Form a new faction!
                faction = Faction(
                    id=_next_faction_id(),
                    name=_generate_faction_name(),
                    founder_id=seed.id,
                    formed_at=tick,
                    core_beliefs={
                        ax: sum(a.beliefs.get(ax, 0) for a in cluster) / len(cluster)
                        for ax in BELIEF_AXES
                    },
                )
                factions.append(faction)
                for a in cluster:
                    a.faction_id = faction.id
                    unclaimed.discard(a.id)
                    a.add_memory(tick, f"Joined faction: {faction.name}")
                stats["factions_formed"] += 1

    # ── Phase 4: Faction membership updates ──
    faction_map = {f.id: f for f in factions}

    for a in alive:
        if a.faction_id is None:
            continue
        faction = faction_map.get(a.faction_id)
        if not faction:
            a.faction_id = None
            continue

        # Check if agent has drifted too far from faction core beliefs
        dist = belief_distance(a.beliefs, faction.core_beliefs)
        if dist > belief_cfg.faction_leave_threshold:
            a.faction_id = None
            a.add_memory(tick, f"Left faction: {faction.name}")

    # ── Phase 5: Faction leader election ──
    for faction in factions:
        members = [a for a in alive if a.faction_id == faction.id]
        faction.member_count = len(members)

        if not members:
            continue

        # Leader = highest (bonds + wealth + intelligence + charisma)
        scored = []
        for a in members:
            score = (
                len(a.bonds) / 8.0 * 0.25 +
                min(a.wealth, 5.0) / 5.0 * 0.25 +
                a.intelligence * 0.25 +
                a.traits.charisma * 0.25
            )
            scored.append((a.id, score))
        scored.sort(key=lambda x: -x[1])
        faction.leader_id = scored[0][0]

    # ── Phase 6: Prophet emergence ──
    if tick % belief_cfg.prophet_check_interval == 0:
        for a in alive:
            if a.faction_id is not None:
                continue
            # Prophet criteria: extreme beliefs + high charisma + high intelligence
            if (a.belief_extremism > belief_cfg.prophet_extremism_threshold
                    and a.traits.charisma > belief_cfg.prophet_charisma_threshold
                    and a.intelligence > 0.4):
                # Become a prophet — found a new faction
                faction = Faction(
                    id=_next_faction_id(),
                    name=_generate_faction_name(),
                    founder_id=a.id,
                    formed_at=tick,
                    core_beliefs=dict(a.beliefs),
                )
                factions.append(faction)
                a.faction_id = faction.id
                a.add_memory(tick, f"Founded faction as prophet: {faction.name}")
                stats["prophets_emerged"] += 1

                # Nearby agents with compatible beliefs are drawn in
                for other in alive:
                    if other.faction_id is not None or other.id == a.id:
                        continue
                    if spatial_distance(a, other) < 0.15:
                        sim = belief_similarity(a, other)
                        # Charisma lowers the bar for conversion
                        threshold = 0.5 - a.traits.charisma * 0.2
                        if sim > threshold:
                            other.faction_id = faction.id
                            other.add_memory(tick, f"Converted to {faction.name}")
                            stats["conversions"] += 1

    # ── Phase 7: Schisms ──
    if tick % belief_cfg.schism_check_interval == 0:
        for faction in list(factions):
            members = [a for a in alive if a.faction_id == faction.id]
            if len(members) < belief_cfg.schism_min_size * 2:
                continue

            # Check internal belief variance
            variances = {}
            for axis in BELIEF_AXES:
                mean = sum(a.beliefs.get(axis, 0) for a in members) / len(members)
                var = sum((a.beliefs.get(axis, 0) - mean) ** 2 for a in members) / len(members)
                variances[axis] = var

            total_variance = sum(variances.values())
            if total_variance > belief_cfg.schism_variance_threshold:
                # Schism! Split by most divisive axis
                split_axis = max(variances, key=variances.get)
                median = sorted(a.beliefs.get(split_axis, 0) for a in members)[len(members) // 2]

                splinter = [a for a in members if a.beliefs.get(split_axis, 0) > median]
                if len(splinter) >= belief_cfg.schism_min_size:
                    new_faction = Faction(
                        id=_next_faction_id(),
                        name=_generate_faction_name(),
                        founder_id=splinter[0].id,
                        formed_at=tick,
                        core_beliefs={
                            ax: sum(a.beliefs.get(ax, 0) for a in splinter) / len(splinter)
                            for ax in BELIEF_AXES
                        },
                    )
                    factions.append(new_faction)
                    for a in splinter:
                        a.faction_id = new_faction.id
                        a.add_memory(tick, f"Schism: joined {new_faction.name}")
                    stats["schisms"] += 1

    # ── Phase 8: Dissolve empty factions ──
    to_remove = []
    for faction in factions:
        members = [a for a in alive if a.faction_id == faction.id]
        if len(members) < 2:
            for a in members:
                a.faction_id = None
            to_remove.append(faction)
            stats["factions_dissolved"] += 1

    for f in to_remove:
        factions.remove(f)

    stats["faction_count"] = len(factions)
    return stats


def get_faction_bonuses(agent: Agent, faction: Optional[Faction], cfg,
                        agents: list[Agent] | None = None) -> dict:
    """Return skill/resource bonuses for faction membership.
    Leader traits modify faction behavior."""
    if not faction:
        return {}
    bonuses = {}
    # Larger factions provide better bonuses (up to a point)
    size_factor = min(faction.member_count / 20.0, 1.0)

    # Collectivist factions share resources better
    if faction.core_beliefs.get("individualism", 0) < -0.3:
        bonuses["resource_sharing"] = 0.05 * size_factor

    # Progressive factions learn faster
    if faction.core_beliefs.get("tradition", 0) < -0.3:
        bonuses["learning_boost"] = 0.02 * size_factor

    # Traditional factions have better survival
    if faction.core_beliefs.get("tradition", 0) > 0.3:
        bonuses["survival_boost"] = 0.02 * size_factor

    # Leader trait effects on faction
    if agents and faction.leader_id is not None:
        leader = next((a for a in agents if a.id == faction.leader_id and a.alive), None)
        if leader:
            # Charismatic leader → recruitment bonus (faster conversion of nearby agents)
            if leader.traits.charisma > 0.6:
                bonuses["recruitment_bonus"] = leader.traits.charisma * 0.1
            # Warlike leader → lower war threshold for this faction
            if leader.traits.aggression > 0.5:
                bonuses["war_threshold_modifier"] = -leader.traits.aggression * 0.15
            # Intelligent leader → better cohesion (slower member drift)
            if leader.intelligence > 0.6:
                bonuses["cohesion_boost"] = leader.intelligence * 0.05
            # Low-intelligence leader → faster member drift
            if leader.intelligence < 0.3:
                bonuses["cohesion_penalty"] = (0.3 - leader.intelligence) * 0.1

    return bonuses
