"""
Mate selection — competitive blend with configurable weights.
"""
from __future__ import annotations

import math
import random
from src.agents import Agent, Bond, create_offspring


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def competitive_fitness(agent: Agent, weights: dict) -> float:
    """Score an agent's competitive fitness."""
    return (
        agent.traits.resilience * weights.get("resilience", 0.3) +
        agent.intelligence * weights.get("intelligence", 0.3) +
        agent.health * weights.get("health", 0.2) +
        agent.avg_skill * weights.get("avg_skill", 0.2)
    )


def trait_compatibility(a: Agent, b: Agent, mode: str = "disassortative") -> float:
    """How well two agents' traits complement each other."""
    diff = (
        abs(a.traits.learning_rate - b.traits.learning_rate) +
        abs(a.traits.resilience - b.traits.resilience) +
        abs(a.traits.curiosity - b.traits.curiosity)
    ) / 3.0
    if mode == "assortative":
        return 1.0 - diff
    return diff  # disassortative: more different = more compatible


def process_reproduction(agents: list[Agent], tick: int, cfg) -> list[Agent]:
    """Run mate selection and reproduction for one tick. Returns new children."""
    ms = cfg.mate_selection
    alive = [a for a in agents if a.alive]

    # Find eligible agents by sex
    eligible_f = [
        a for a in alive
        if a.sex == "F" and ms.min_age <= a.age <= ms.max_age and a.health > ms.min_health
    ]
    eligible_m = [
        a for a in alive
        if a.sex == "M" and ms.min_age <= a.age <= ms.max_age and a.health > ms.min_health
    ]

    if not eligible_f or not eligible_m:
        return []

    new_children = []
    mated_this_tick = set()

    random.shuffle(eligible_f)
    for female in eligible_f:
        if female.id in mated_this_tick:
            continue

        # Find male candidates within search radius
        candidates = [
            m for m in eligible_m
            if m.id not in mated_this_tick
            and spatial_distance(female, m) < ms.search_radius
        ]
        if not candidates:
            continue

        # Score candidates — normalize weights so they always sum to 1.0
        weights = ms.weights
        w_sum = weights.competition + weights.compatibility + weights.proximity + weights.bond
        if w_sum > 0:
            w_comp = weights.competition / w_sum
            w_compat = weights.compatibility / w_sum
            w_prox = weights.proximity / w_sum
            w_bond = weights.bond / w_sum
        else:
            w_comp = w_compat = w_prox = w_bond = 0.25

        compat_mode = ms.compatibility_mode
        fitness_w = ms.fitness_weights

        scored = []
        for male in candidates:
            score = (
                w_comp * competitive_fitness(male, fitness_w._data if hasattr(fitness_w, '_data') else {"resilience": 0.3, "intelligence": 0.3, "health": 0.2, "avg_skill": 0.2}) +
                w_compat * trait_compatibility(female, male, compat_mode) +
                w_prox * (1.0 - spatial_distance(female, male) / ms.search_radius) +
                w_bond * (0.5 if female.has_bond_with(male.id) else 0.0)
            )
            scored.append((male, score))

        scored.sort(key=lambda x: -x[1])

        # Stochastic selection from top N
        top_n = min(ms.top_n_stochastic, len(scored))
        pool = scored[:top_n]
        if not pool:
            continue

        # Weighted random from top pool
        total_score = sum(s for _, s in pool)
        if total_score <= 0:
            selected_male = pool[0][0]
        else:
            r = random.uniform(0, total_score)
            cumulative = 0
            selected_male = pool[0][0]
            for male, score in pool:
                cumulative += score
                if cumulative >= r:
                    selected_male = male
                    break

        # Reproduction probability gate
        repro_chance = ms.base_reproduction_chance
        # Adjust by health — healthier parents are more likely to reproduce
        repro_chance *= (female.health + selected_male.health) / 2
        if random.random() > repro_chance:
            # Create rival bonds for losers
            for male, score in scored[1:]:
                if male.traits.resilience >= cfg.social.rival_min_resilience:
                    male.add_bond(
                        Bond(selected_male.id, "rival", 0.4, tick),
                        cfg.social.bond_capacity,
                    )
            continue

        # Create child
        child = create_offspring(
            female, selected_male, tick, cfg.genetics.mutation_rate
        )
        new_children.append(child)
        mated_this_tick.add(female.id)
        mated_this_tick.add(selected_male.id)

        # Mate bonds
        female.add_bond(Bond(selected_male.id, "mate", 0.7, tick), cfg.social.bond_capacity)
        selected_male.add_bond(Bond(female.id, "mate", 0.7, tick), cfg.social.bond_capacity)

        female.add_memory(tick, f"Had child #{child.id} with #{selected_male.id}")
        selected_male.add_memory(tick, f"Had child #{child.id} with #{female.id}")

        # Rival bonds for losers
        for male, score in scored:
            if male.id == selected_male.id:
                continue
            if male.traits.resilience >= cfg.social.rival_min_resilience:
                male.add_bond(
                    Bond(selected_male.id, "rival", 0.3, tick),
                    cfg.social.bond_capacity,
                )
                male.add_memory(tick, f"Lost mating competition to #{selected_male.id}")

    return new_children