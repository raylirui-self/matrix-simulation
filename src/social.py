"""
Social system — bond formation, decay, and management.
"""
from __future__ import annotations

import math
import random
from src.agents import Agent, Bond


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def process_bonds(agents: list[Agent], tick: int, cfg) -> dict:
    """Run one tick of social dynamics. Returns stats."""
    social_cfg = cfg.social
    alive = [a for a in agents if a.alive]

    bonds_formed = 0
    bonds_decayed = 0

    # Build spatial index — grid-based for O(n) instead of O(n²)
    grid = {}
    bucket_size = social_cfg.friend_formation_distance * 2
    for a in alive:
        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        grid.setdefault(key, []).append(a)

    # Friend formation — check nearby agents
    for a in alive:
        if a.traits.sociability < social_cfg.friend_min_sociability:
            continue

        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        nearby = []
        for dk_r in [-1, 0, 1]:
            for dk_c in [-1, 0, 1]:
                nearby.extend(grid.get((key[0] + dk_r, key[1] + dk_c), []))

        for b in nearby:
            if b.id <= a.id or not b.alive:  # avoid double-processing
                continue
            if b.traits.sociability < social_cfg.friend_min_sociability:
                continue

            dist = spatial_distance(a, b)
            if dist > social_cfg.friend_formation_distance:
                # Reset proximity counter
                a.proximity_ticks.pop(b.id, None)
                b.proximity_ticks.pop(a.id, None)
                continue

            # Increment proximity tick counter
            a.proximity_ticks[b.id] = a.proximity_ticks.get(b.id, 0) + 1
            b.proximity_ticks[a.id] = b.proximity_ticks.get(a.id, 0) + 1

            # Check if enough time has passed to form a friendship
            if a.proximity_ticks[b.id] >= social_cfg.friend_ticks_to_form:
                existing_a = a.has_bond_with(b.id)
                existing_b = b.has_bond_with(a.id)

                if not existing_a or existing_a.bond_type != "friend":
                    strength = min(1.0, (a.traits.sociability + b.traits.sociability) / 2)
                    if a.add_bond(Bond(b.id, "friend", strength, tick), social_cfg.bond_capacity):
                        bonds_formed += 1
                if not existing_b or existing_b.bond_type != "friend":
                    strength = min(1.0, (a.traits.sociability + b.traits.sociability) / 2)
                    b.add_bond(Bond(a.id, "friend", strength, tick), social_cfg.bond_capacity)

    # Rival formation — aggressive agents in close proximity with no friendly bond
    rival_distance = social_cfg.friend_formation_distance  # same range as friend formation
    for a in alive:
        if a.traits.aggression < social_cfg.rival_min_resilience:
            continue
        if a.phase in ("infant", "child"):
            continue

        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        nearby = []
        for dk_r in [-1, 0, 1]:
            for dk_c in [-1, 0, 1]:
                nearby.extend(grid.get((key[0] + dk_r, key[1] + dk_c), []))

        for b in nearby:
            if b.id <= a.id or not b.alive or b.phase in ("infant", "child"):
                continue
            if b.traits.aggression < social_cfg.rival_min_resilience:
                continue
            dist = spatial_distance(a, b)
            if dist > rival_distance:
                continue
            # Don't form rival bond if already bonded
            existing = a.has_bond_with(b.id)
            if existing:
                continue
            # Different factions create tension
            faction_tension = (a.faction_id is not None and b.faction_id is not None
                               and a.faction_id != b.faction_id)
            # High aggression + proximity + no bond = rival chance
            chance = (a.traits.aggression + b.traits.aggression) * 0.08
            if faction_tension:
                chance *= 2.5
            # Overcrowding breeds contempt
            key_cell = (int(a.x / bucket_size), int(a.y / bucket_size))
            crowding = len(grid.get(key_cell, []))
            if crowding > 5:
                chance *= 1.0 + (crowding - 5) * 0.15
            if random.random() < chance:
                strength = min(0.6, (a.traits.aggression + b.traits.aggression) / 3)
                a.add_bond(Bond(b.id, "rival", strength, tick), social_cfg.bond_capacity)
                b.add_bond(Bond(a.id, "rival", strength, tick), social_cfg.bond_capacity)
                bonds_formed += 1

    # Bond decay — use dict lookup instead of O(n) search
    decay_rates = cfg.social.decay_rates
    alive_by_id = {a.id: a for a in alive}
    for a in alive:
        to_remove = []
        for bond in a.bonds:
            if bond.bond_type == "family":
                continue  # family bonds don't decay

            rate = getattr(decay_rates, bond.bond_type, 0.01)

            # Check distance to target — decay faster when far apart
            target = alive_by_id.get(bond.target_id)

            if target is None:
                # Target is dead — decay faster
                bond.strength -= rate * 3
            else:
                dist = spatial_distance(a, target)
                if dist > 0.3:
                    # Far apart — accelerated decay
                    bond.strength -= rate * 2.0
                elif dist > 0.1:
                    # Medium distance — normal decay
                    bond.strength -= rate
                # Close proximity (< 0.1) — no decay but also no reinforcement
                # (reinforcement happens through interaction in other systems)

            if bond.strength <= 0:
                to_remove.append(bond)
                bonds_decayed += 1

        for bond in to_remove:
            a.bonds.remove(bond)

    return {"bonds_formed": bonds_formed, "bonds_decayed": bonds_decayed}