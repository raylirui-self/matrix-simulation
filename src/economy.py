"""
System 8: Economy, Property & Power — wealth accumulation, trade,
theft, inheritance, and inequality.

In Matrix terms: the economy keeps humans busy competing with each other
instead of questioning the nature of reality.
"""
from __future__ import annotations

import math
import random
from src.agents import Agent, Bond


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def process_economy(agents: list[Agent], tick: int, cfg, world, factions=None) -> dict:
    """Run one tick of economic activity. Returns stats."""
    alive = [a for a in agents if a.alive]
    econ_cfg = cfg.economy

    stats = {
        "total_wealth": 0.0, "avg_wealth": 0.0, "max_wealth": 0.0,
        "gini": 0.0, "trades": 0, "thefts": 0,
        "wealth_top10": 0.0, "wealth_bottom50": 0.0,
    }

    if not alive:
        return stats

    # ── Phase 1: Resource gathering (wealth from environment) ──
    gather_rate = econ_cfg.gather_rate
    for a in alive:
        if a.is_sentinel:
            continue

        cell = world.get_cell(a.x, a.y)
        # Gathering efficiency depends on survival skill and cell resources
        efficiency = (0.3 + a.skills.get("survival", 0) * 0.7) * gather_rate
        gathered = cell.effective_resources * efficiency

        # Competition: more agents in cell = less per agent
        if cell.agent_count > 1:
            gathered /= math.sqrt(max(1, cell.agent_count))

        a.wealth += gathered

    # ── Phase 2: Wealth decay (maintenance costs, consumption) ──
    decay_rate = econ_cfg.wealth_decay
    for a in alive:
        if a.is_sentinel:
            continue
        # Base consumption
        a.wealth = max(0.0, a.wealth - decay_rate)
        # Children cost more (parents pay)
        child_count = sum(
            1 for c_id in a.child_ids
            if any(ag.id == c_id and ag.alive and ag.phase in ("infant", "child") for ag in agents)
        )
        if child_count > 0:
            a.wealth = max(0.0, a.wealth - child_count * decay_rate * 0.3)

    # ── Phase 3: Trade (between bonded, nearby agents) ──
    trade_radius = econ_cfg.trade_radius
    trade_rate = econ_cfg.trade_rate

    # Build spatial index
    bucket_size = trade_radius * 2
    grid = {}
    for a in alive:
        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        grid.setdefault(key, []).append(a)

    traded_this_tick = set()
    for a in alive:
        if a.is_sentinel or a.id in traded_this_tick:
            continue
        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        nearby = []
        for dk_r in [-1, 0, 1]:
            for dk_c in [-1, 0, 1]:
                nearby.extend(grid.get((key[0] + dk_r, key[1] + dk_c), []))

        for b in nearby:
            if b.id <= a.id or b.id in traded_this_tick or b.is_sentinel:
                continue
            if not b.alive:
                continue

            bond = a.has_bond_with(b.id)
            if not bond or bond.bond_type in ("rival", "enemy"):
                continue

            dist = spatial_distance(a, b)
            if dist > trade_radius:
                continue

            # Faction norm: trade_internal_only blocks cross-faction trade
            if factions:
                faction_lookup = {f.id: f for f in factions}
                a_faction = faction_lookup.get(a.faction_id) if a.faction_id else None
                b_faction = faction_lookup.get(b.faction_id) if b.faction_id else None
                if a_faction and getattr(a_faction, "norms", {}).get("trade_internal_only"):
                    if a.faction_id != b.faction_id:
                        continue
                if b_faction and getattr(b_faction, "norms", {}).get("trade_internal_only"):
                    if a.faction_id != b.faction_id:
                        continue

            # Trade: wealth flows from richer to poorer
            diff = a.wealth - b.wealth
            if abs(diff) < 0.1:
                continue

            # Trade amount depends on social skill and bond strength
            social_avg = (a.skills.get("social", 0) + b.skills.get("social", 0)) / 2
            trade_amount = abs(diff) * trade_rate * social_avg * bond.strength

            if diff > 0:
                a.wealth -= trade_amount
                b.wealth += trade_amount * 0.9  # 10% lost in transaction (value creation)
            else:
                b.wealth -= trade_amount
                a.wealth += trade_amount * 0.9

            stats["trades"] += 1
            # Trading strengthens bonds
            bond.strength = min(1.0, bond.strength + 0.01)
            # Rate-limit: each agent trades at most once per tick
            traded_this_tick.add(a.id)
            traded_this_tick.add(b.id)

    # ── Phase 4: Theft (aggressive agents steal from nearby strangers) ──
    theft_threshold = econ_cfg.theft_aggression_threshold
    for a in alive:
        if a.is_sentinel or a.traits.aggression < theft_threshold:
            continue
        # Anger increases theft likelihood — requires significant anger
        if a.emotions.get("anger", 0) < 0.4:
            continue
        if a.wealth > 1.0:  # Already wealthy, less incentive
            continue

        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        nearby = []
        for dk_r in [-1, 0, 1]:
            for dk_c in [-1, 0, 1]:
                nearby.extend(grid.get((key[0] + dk_r, key[1] + dk_c), []))

        for victim in nearby:
            if victim.id == a.id or not victim.alive or victim.is_sentinel:
                continue
            if a.has_bond_with(victim.id):
                continue  # Don't steal from bonds
            if victim.wealth < 0.5:
                continue  # Nothing to steal

            dist = spatial_distance(a, victim)
            if dist > 0.08:
                continue

            # Theft success: aggression vs victim's resilience
            success_chance = a.traits.aggression * 0.5 - victim.traits.resilience * 0.3
            if random.random() < success_chance:
                stolen = victim.wealth * random.uniform(0.1, 0.3)
                victim.wealth -= stolen
                a.wealth += stolen
                stats["thefts"] += 1

                # Create enemy bond
                victim.add_bond(Bond(a.id, "enemy", 0.6, tick), 10)
                a.add_bond(Bond(victim.id, "enemy", 0.3, tick), 10)
                victim.emotions["anger"] = min(1.0, victim.emotions.get("anger", 0) + 0.3)
                # Revenge: victim sets goal to hunt the thief
                victim.current_goal = "HUNT_ENEMY"
                victim.goal_target_id = a.id
                victim.goal_ticks = 0
                victim.add_memory(tick, f"Robbed by #{a.id}", x=victim.x, y=victim.y)
                a.add_memory(tick, f"Stole from #{victim.id}", x=a.x, y=a.y)
                break  # One theft per tick per thief

    # ── Phase 5: Faction taxation & redistribution ──
    tax_rate = econ_cfg.faction_tax_rate
    if tax_rate > 0:
        faction_pools = {}  # faction_id → collected tax
        # Build faction lookup for belief-based tax modifiers
        faction_lookup = {f.id: f for f in factions} if factions else {}
        # Track which factions skip redistribution (individualist)
        skip_redistribution = set()

        for a in alive:
            if a.faction_id is not None and a.wealth > 0.5:
                effective_tax = tax_rate
                faction = faction_lookup.get(a.faction_id)
                if faction:
                    individualism = faction.core_beliefs.get("individualism", 0.0)
                    if individualism < -0.3:
                        effective_tax = tax_rate * 1.5
                    elif individualism > 0.3:
                        effective_tax = tax_rate * 0.5
                        skip_redistribution.add(a.faction_id)
                tax = a.wealth * effective_tax
                a.wealth -= tax
                faction_pools[a.faction_id] = faction_pools.get(a.faction_id, 0) + tax

        # Redistribute equally among faction members (skip individualist factions)
        for faction_id, pool in faction_pools.items():
            if faction_id in skip_redistribution:
                continue
            members = [a for a in alive if a.faction_id == faction_id]
            if members:
                share = pool / len(members)
                for a in members:
                    a.wealth += share

    # ── Phase 6: Wealth affects health ──
    for a in alive:
        if a.is_sentinel:
            continue
        # Wealthy agents have better health recovery
        if a.wealth > 1.0:
            health_bonus = min(0.01, (a.wealth - 1.0) * 0.005)
            a.health = min(1.0, a.health + health_bonus)
        # Poor agents suffer
        if a.wealth < 0.1 and a.phase != "infant":
            a.health = max(0.0, a.health - 0.003)
            a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + 0.02)

    # ── Compute stats ──
    wealth_values = sorted(a.wealth for a in alive)
    n = len(wealth_values)
    total = sum(wealth_values)
    stats["total_wealth"] = round(total, 2)
    stats["avg_wealth"] = round(total / n, 3) if n else 0
    stats["max_wealth"] = round(max(wealth_values), 2) if wealth_values else 0

    # Gini coefficient
    if n > 1 and total > 0:
        cumulative = 0.0
        for i, w in enumerate(wealth_values):
            cumulative += w
        # Simplified Gini
        sum_of_abs_diff = sum(
            abs(wealth_values[i] - wealth_values[j])
            for i in range(n) for j in range(i + 1, n)
        )
        stats["gini"] = round(sum_of_abs_diff / (n * n * (total / n)) if total > 0 else 0, 3)

    # Top 10% vs Bottom 50%
    top_10_idx = max(1, n * 9 // 10)
    bottom_50_idx = n // 2
    stats["wealth_top10"] = round(sum(wealth_values[top_10_idx:]) / max(1, total) * 100, 1)
    stats["wealth_bottom50"] = round(sum(wealth_values[:bottom_50_idx]) / max(1, total) * 100, 1)

    return stats


def process_inheritance(dead_agent: Agent, agents: list[Agent], tick: int, cfg):
    """Distribute a dead agent's wealth to bonded family members."""
    if dead_agent.wealth <= 0:
        return

    econ_cfg = cfg.economy
    # Find living family members
    heirs = []
    for bond in dead_agent.bonds:
        if bond.bond_type == "family":
            heir = next((a for a in agents if a.id == bond.target_id and a.alive), None)
            if heir:
                heirs.append(heir)

    if heirs:
        inheritance_rate = econ_cfg.inheritance_rate
        to_distribute = dead_agent.wealth * inheritance_rate
        share = to_distribute / len(heirs)
        for heir in heirs:
            heir.wealth += share
            heir.add_memory(tick, f"Inherited {share:.2f} from #{dead_agent.id}")
    # Remaining wealth is lost (burial costs, etc.)
    dead_agent.wealth = 0.0
