"""
System 10: Conflict & Warfare — aggression, faction wars, territorial claims,
casualties, and peace negotiations.

In Matrix terms: the machines engineer wars to keep humans divided and
prevent unified awareness.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from src.agents import Agent, Bond


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


@dataclass
class FactionWar:
    """An active conflict between two factions."""
    faction_a_id: int
    faction_b_id: int
    started_at: int
    casualties_a: int = 0
    casualties_b: int = 0
    intensity: float = 0.5  # 0-1, escalation level

    def to_dict(self) -> dict:
        return {
            "faction_a_id": self.faction_a_id,
            "faction_b_id": self.faction_b_id,
            "started_at": self.started_at,
            "casualties_a": self.casualties_a,
            "casualties_b": self.casualties_b,
            "intensity": round(self.intensity, 3),
        }

    @classmethod
    def from_dict(cls, d: dict) -> FactionWar:
        return cls(**d)


def _get_faction_norms(agent: Agent, faction_map: dict) -> dict:
    """Get the norms dict for an agent's faction, or empty dict."""
    if agent.faction_id is None:
        return {}
    faction = faction_map.get(agent.faction_id)
    if faction is None:
        return {}
    return getattr(faction, "norms", {}) or {}


def process_conflict(agents: list[Agent], factions: list, wars: list[FactionWar],
                     tick: int, cfg, world, propaganda_reach=None) -> dict:
    """Run one tick of conflict dynamics. Returns stats."""
    alive = [a for a in agents if a.alive]
    conflict_cfg = cfg.conflict

    stats = {
        "wars_active": len(wars), "wars_started": 0, "wars_ended": 0,
        "combat_casualties": 0, "territorial_disputes": 0,
        "peace_negotiations": 0,
    }

    if not alive:
        return stats

    faction_map = {f.id: f for f in factions}

    # ── Phase 1: Individual aggression (proximity combat) ──
    aggression_threshold = conflict_cfg.aggression_combat_threshold
    combat_radius = conflict_cfg.combat_radius

    # Build spatial index
    bucket_size = combat_radius * 2
    grid = {}
    for a in alive:
        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        grid.setdefault(key, []).append(a)

    for a in alive:
        if a.is_sentinel:
            continue
        # Aggression check: trait + anger + rival/enemy bonds
        rival_bond_count = sum(1 for b in a.bonds if b.bond_type in ("rival", "enemy"))
        effective_aggression = (
            a.traits.aggression * 0.6 +
            a.emotions.get("anger", 0) * 0.3 +
            min(0.3, rival_bond_count * 0.1)
        )
        # Fear reduces aggression but never fully cancels it — cap fear penalty at 50%
        fear = a.emotions.get("fear", 0)
        if fear > 0.3:
            effective_aggression *= max(0.5, 1.0 - (fear - 0.3) * 0.5)
        # Faction norms: pacifist factions raise the threshold
        a_norms = _get_faction_norms(a, faction_map)
        agent_threshold = aggression_threshold
        if a_norms.get("pacifist"):
            agent_threshold += 0.2

        # Minimum combat chance: agents with rival/enemy bonds always have a chance
        has_enemies = rival_bond_count > 0
        if effective_aggression < agent_threshold and not has_enemies:
            continue
        # Agents with enemies but below threshold get a random chance to fight
        if effective_aggression < agent_threshold and has_enemies:
            if random.random() > 0.3:  # 30% chance to fight anyway
                continue

        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        nearby = []
        for dk_r in [-1, 0, 1]:
            for dk_c in [-1, 0, 1]:
                nearby.extend(grid.get((key[0] + dk_r, key[1] + dk_c), []))

        for b in nearby:
            if b.id == a.id or not b.alive or b.is_sentinel:
                continue
            dist = spatial_distance(a, b)
            if dist > combat_radius:
                continue

            # Only fight enemies, rivals, or faction enemies
            bond = a.has_bond_with(b.id)
            is_enemy = bond and bond.bond_type in ("rival", "enemy")
            is_faction_enemy = (
                a.faction_id is not None and b.faction_id is not None
                and a.faction_id != b.faction_id
                and _factions_at_war(a.faction_id, b.faction_id, wars)
            )

            if not is_enemy and not is_faction_enemy:
                continue

            # Combat! Resolved by aggression + resilience + health + survival (weights sum to 1.0)
            a_power = (a.traits.aggression * 0.30 + a.traits.resilience * 0.25 +
                       a.health * 0.25 + a.skills.get("survival", 0) * 0.20)
            b_power = (b.traits.aggression * 0.30 + b.traits.resilience * 0.25 +
                       b.health * 0.25 + b.skills.get("survival", 0) * 0.20)

            # Faction norms: warrior_bonus adds to combat power
            a_warrior = _get_faction_norms(a, faction_map).get("warrior_bonus", 0)
            b_warrior = _get_faction_norms(b, faction_map).get("warrior_bonus", 0)
            a_power += a_warrior
            b_power += b_warrior

            # Both take damage
            damage_to_b = a_power * conflict_cfg.combat_damage * random.uniform(0.5, 1.5)
            damage_to_a = b_power * conflict_cfg.combat_damage * random.uniform(0.5, 1.5)

            a.health = max(0.0, a.health - damage_to_a)
            b.health = max(0.0, b.health - damage_to_b)

            # Track killed_by and death cause for revenge system
            if a.health <= 0:
                a.killed_by = b.id
                a.death_cause = "combat"
            if b.health <= 0:
                b.killed_by = a.id
                b.death_cause = "combat"

            # Emotional effects
            a.emotions["anger"] = min(1.0, a.emotions.get("anger", 0) + 0.1)
            b.emotions["anger"] = min(1.0, b.emotions.get("anger", 0) + 0.1)
            a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + 0.05)
            b.emotions["fear"] = min(1.0, b.emotions.get("fear", 0) + 0.05)

            # Track war casualties
            if is_faction_enemy:
                for war in wars:
                    if _war_involves(war, a.faction_id, b.faction_id):
                        if a.health <= 0:
                            war.casualties_a += 1
                            stats["combat_casualties"] += 1
                        if b.health <= 0:
                            war.casualties_b += 1
                            stats["combat_casualties"] += 1
                        war.intensity = min(1.0, war.intensity + 0.01)

            # Revenge: loser sets HUNT_ENEMY goal (only if both survive)
            if a.health > 0 and b.health > 0:
                if a.health < b.health:
                    a.current_goal = "HUNT_ENEMY"
                    a.goal_target_id = b.id
                    a.goal_ticks = 0
                else:
                    b.current_goal = "HUNT_ENEMY"
                    b.goal_target_id = a.id
                    b.goal_ticks = 0

            a.add_memory(tick, f"Fought #{b.id}", x=a.x, y=a.y)
            b.add_memory(tick, f"Fought #{a.id}", x=b.x, y=b.y)

            # Create/strengthen enemy bonds
            if not is_enemy:
                a.add_bond(Bond(b.id, "enemy", 0.5, tick), 10)
                b.add_bond(Bond(a.id, "enemy", 0.5, tick), 10)

            break  # One fight per agent per tick

    # ── Phase 2: Faction war triggers ──
    if tick % conflict_cfg.war_check_interval == 0:
        for i, fa in enumerate(factions):
            for fb in factions[i + 1:]:
                if _factions_at_war(fa.id, fb.id, wars):
                    continue

                # War conditions: ideological distance + territorial overlap + mutual rivalry
                if fa.member_count < 3 or fb.member_count < 3:
                    continue

                belief_dist = _faction_belief_distance(fa, fb)
                rivalry_count = _mutual_enemy_count(
                    [a for a in alive if a.faction_id == fa.id],
                    [a for a in alive if a.faction_id == fb.id],
                )
                territorial_overlap = _territorial_overlap(
                    [a for a in alive if a.faction_id == fa.id],
                    [a for a in alive if a.faction_id == fb.id],
                    world,
                )

                war_score = (
                    belief_dist * conflict_cfg.war_ideology_weight +
                    rivalry_count * conflict_cfg.war_rivalry_weight +
                    territorial_overlap * conflict_cfg.war_territory_weight
                )

                if propaganda_reach:
                    prop_a = propaganda_reach.get(fa.id, 0)
                    prop_b = propaganda_reach.get(fb.id, 0)
                    propaganda_factor = (prop_a + prop_b) * 0.005
                    war_score += propaganda_factor

                if war_score > conflict_cfg.war_threshold:
                    war = FactionWar(
                        faction_a_id=fa.id, faction_b_id=fb.id,
                        started_at=tick,
                        intensity=min(1.0, war_score / 2.0),
                    )
                    wars.append(war)
                    stats["wars_started"] += 1

                    # Notify members
                    for a in alive:
                        if a.faction_id == fa.id:
                            a.add_memory(tick, f"WAR declared against {fb.name}")
                            a.emotions["anger"] = min(1.0, a.emotions.get("anger", 0) + 0.2)
                            a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + 0.1)
                        elif a.faction_id == fb.id:
                            a.add_memory(tick, f"WAR declared against {fa.name}")
                            a.emotions["anger"] = min(1.0, a.emotions.get("anger", 0) + 0.2)
                            a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + 0.1)

    # ── Phase 3: War escalation and de-escalation ──
    for war in list(wars):
        fa = faction_map.get(war.faction_a_id)
        fb = faction_map.get(war.faction_b_id)
        if not fa or not fb:
            wars.remove(war)
            stats["wars_ended"] += 1
            continue

        members_a = [a for a in alive if a.faction_id == fa.id]
        members_b = [a for a in alive if a.faction_id == fb.id]

        # War destroys resources in contested zones
        for a in members_a + members_b:
            cell = world.get_cell(a.x, a.y)
            cell.current_resources = max(0.0, cell.current_resources - 0.005 * war.intensity)

        # Check for peace conditions
        total_casualties = war.casualties_a + war.casualties_b
        war_duration = tick - war.started_at

        # Leaders with high social skill can negotiate peace
        leader_a = next((a for a in members_a if a.id == fa.leader_id), None)
        leader_b = next((a for a in members_b if a.id == fb.leader_id), None)

        peace_chance = 0.0
        if leader_a and leader_b:
            avg_social = (leader_a.skills.get("social", 0) + leader_b.skills.get("social", 0)) / 2
            avg_intel = (leader_a.intelligence + leader_b.intelligence) / 2
            peace_chance = avg_social * avg_intel * 0.1

        # War weariness increases peace chance
        if war_duration > 50:
            peace_chance += (war_duration - 50) / 500.0
        if total_casualties > 10:
            peace_chance += total_casualties * 0.01

        # One side destroyed
        if not members_a or not members_b:
            wars.remove(war)
            stats["wars_ended"] += 1
            continue

        if random.random() < peace_chance:
            wars.remove(war)
            stats["wars_ended"] += 1
            stats["peace_negotiations"] += 1
            for a in members_a + members_b:
                a.add_memory(tick, "Peace declared. The war is over.")
                a.emotions["hope"] = min(1.0, a.emotions.get("hope", 0) + 0.15)
            continue

        # Natural de-escalation
        war.intensity = max(0.1, war.intensity - 0.002)

    stats["wars_active"] = len(wars)
    return stats


# ── Private helpers ──

def _factions_at_war(fa_id: int, fb_id: int, wars: list[FactionWar]) -> bool:
    for w in wars:
        if (w.faction_a_id == fa_id and w.faction_b_id == fb_id) or \
           (w.faction_a_id == fb_id and w.faction_b_id == fa_id):
            return True
    return False


def _war_involves(war: FactionWar, fa_id: int, fb_id: int) -> bool:
    return (war.faction_a_id in (fa_id, fb_id) and
            war.faction_b_id in (fa_id, fb_id))


def _faction_belief_distance(fa, fb) -> float:
    from src.agents import BELIEF_AXES
    return math.sqrt(sum(
        (fa.core_beliefs.get(ax, 0) - fb.core_beliefs.get(ax, 0)) ** 2
        for ax in BELIEF_AXES
    ))


def _mutual_enemy_count(members_a: list[Agent], members_b: list[Agent]) -> float:
    """Count mutual enemy bonds between two groups."""
    b_ids = {a.id for a in members_b}
    count = 0
    for a in members_a:
        for bond in a.bonds:
            if bond.bond_type in ("rival", "enemy") and bond.target_id in b_ids:
                count += 1
    return count / max(1, len(members_a))


def _territorial_overlap(members_a: list[Agent], members_b: list[Agent], world) -> float:
    """How much two factions' territories overlap (0-1)."""
    cells_a = set()
    cells_b = set()
    for a in members_a:
        cell = world.get_cell(a.x, a.y)
        cells_a.add((cell.row, cell.col))
    for b in members_b:
        cell = world.get_cell(b.x, b.y)
        cells_b.add((cell.row, cell.col))

    overlap = cells_a & cells_b
    total = cells_a | cells_b
    return len(overlap) / max(1, len(total))
