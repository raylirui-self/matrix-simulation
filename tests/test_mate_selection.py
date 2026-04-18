"""
Unit tests for [src/mate_selection.py](../src/mate_selection.py).

Covers L-7 (prior L-1) in [docs/code_review.md](../docs/code_review.md) —
`src/mate_selection.py` was previously at ~9% line coverage.

These tests exercise `process_reproduction` directly and pin the
scoring helpers (`competitive_fitness`, `trait_compatibility`) so
refactors of the weight-blending math produce loud regressions.
"""
from __future__ import annotations

import random

import pytest

from src.agents import Agent, Traits, set_id_counter
from src.config_loader import SimConfig
from src.mate_selection import (
    competitive_fitness,
    process_reproduction,
    spatial_distance,
    trait_compatibility,
)


@pytest.fixture
def cfg():
    return SimConfig.load()


def _mk(aid: int, sex: str, x: float, y: float, *,
        age: int = 25, health: float = 0.9,
        sociability: float = 0.7, resilience: float = 0.6) -> Agent:
    """Build an eligible agent at (x, y)."""
    traits = Traits(sociability=sociability, resilience=resilience,
                    aggression=0.2, curiosity=0.5, learning_rate=0.5)
    a = Agent(id=aid, sex=sex, age=age, phase="adult", health=health,
              traits=traits, x=x, y=y, intelligence=0.5)
    a.skills = {s: 0.5 for s in a.skills}
    return a


# ─── Guard conditions: no eligible pairings ──────────────────────────────────

def test_no_reproduction_when_only_females(cfg):
    females = [_mk(i, "F", 0.5, 0.5) for i in range(1, 5)]
    assert process_reproduction(females, tick=0, cfg=cfg) == []


def test_no_reproduction_when_only_males(cfg):
    males = [_mk(i, "M", 0.5, 0.5) for i in range(1, 5)]
    assert process_reproduction(males, tick=0, cfg=cfg) == []


def test_no_reproduction_when_all_too_young(cfg):
    agents = [
        _mk(1, "F", 0.5, 0.5, age=cfg.mate_selection.min_age - 1),
        _mk(2, "M", 0.5, 0.5, age=cfg.mate_selection.min_age - 1),
    ]
    assert process_reproduction(agents, tick=0, cfg=cfg) == []


def test_no_reproduction_when_unhealthy(cfg):
    agents = [
        _mk(1, "F", 0.5, 0.5, health=cfg.mate_selection.min_health - 0.01),
        _mk(2, "M", 0.5, 0.5, health=cfg.mate_selection.min_health - 0.01),
    ]
    assert process_reproduction(agents, tick=0, cfg=cfg) == []


def test_no_reproduction_when_pair_is_out_of_search_radius(cfg):
    far = cfg.mate_selection.search_radius + 0.1
    agents = [
        _mk(1, "F", 0.1, 0.1),
        _mk(2, "M", 0.1 + far, 0.1),
    ]
    assert process_reproduction(agents, tick=0, cfg=cfg) == []


# ─── Happy path: successful pairing ──────────────────────────────────────────

def test_reproduction_produces_child_when_guaranteed(cfg):
    """Force reproduction by raising base_reproduction_chance to 1.0."""
    cfg2 = cfg.override({"mate_selection": {"base_reproduction_chance": 1.0}})
    # Advance the module-level id counter past our hand-assigned ids
    # so create_offspring issues a fresh id, not a collision.
    set_id_counter(100)
    female = _mk(1, "F", 0.5, 0.5, health=1.0)
    male = _mk(2, "M", 0.5, 0.5, health=1.0)

    random.seed(0)
    children = process_reproduction([female, male], tick=10, cfg=cfg2)

    assert len(children) == 1
    child = children[0]
    assert child.id > 100, "child should have received a fresh id from the counter"
    assert set(child.parent_ids) == {female.id, male.id}
    # Mate bonds recorded
    assert female.has_bond_with(male.id) is not None
    assert female.has_bond_with(male.id).bond_type == "mate"


def test_each_agent_only_mates_once_per_tick(cfg):
    """`mated_this_tick` should prevent double-pairing."""
    cfg2 = cfg.override({"mate_selection": {"base_reproduction_chance": 1.0}})
    set_id_counter(100)
    # One female, two males — female can only pair with one
    female = _mk(1, "F", 0.5, 0.5)
    male_a = _mk(2, "M", 0.5, 0.5)
    male_b = _mk(3, "M", 0.5, 0.5)

    random.seed(42)
    children = process_reproduction([female, male_a, male_b], tick=0, cfg=cfg2)

    assert len(children) == 1


# ─── Scoring helpers ─────────────────────────────────────────────────────────

def test_competitive_fitness_is_weighted_sum_of_traits():
    a = _mk(1, "M", 0, 0, resilience=0.8)
    a.intelligence = 0.6
    a.health = 0.7
    # avg_skill is dynamic — pin it via skills dict
    a.skills = {s: 0.4 for s in a.skills}

    weights = {"resilience": 0.25, "intelligence": 0.25, "health": 0.25, "avg_skill": 0.25}
    expected = 0.25 * 0.8 + 0.25 * 0.6 + 0.25 * 0.7 + 0.25 * a.avg_skill
    assert competitive_fitness(a, weights) == pytest.approx(expected)


def test_competitive_fitness_uses_embedded_defaults_for_missing_keys():
    """`weights.get(k, default)` provides per-key fallbacks.

    An empty dict should NOT raise KeyError; it should use the
    defaults baked into the function (resilience=0.3, intelligence=0.3,
    health=0.2, avg_skill=0.2). This pins that contract.
    """
    a = _mk(1, "M", 0, 0, resilience=0.5)
    a.intelligence = 0.5
    a.health = 0.5
    a.skills = {s: 0.5 for s in a.skills}
    # All traits are 0.5 → with default weights summing to 1.0, fitness = 0.5
    assert competitive_fitness(a, {}) == pytest.approx(0.5)


def test_trait_compatibility_disassortative_vs_assortative():
    """Assortative mode rewards similarity; disassortative rewards difference."""
    similar_a = _mk(1, "F", 0, 0)
    similar_a.traits.learning_rate = 0.5
    similar_a.traits.resilience = 0.5
    similar_a.traits.curiosity = 0.5

    similar_b = _mk(2, "M", 0, 0)
    similar_b.traits.learning_rate = 0.5
    similar_b.traits.resilience = 0.5
    similar_b.traits.curiosity = 0.5

    diff_b = _mk(3, "M", 0, 0)
    diff_b.traits.learning_rate = 0.1
    diff_b.traits.resilience = 0.9
    diff_b.traits.curiosity = 0.1

    assert trait_compatibility(similar_a, similar_b, "assortative") > \
           trait_compatibility(similar_a, diff_b, "assortative")

    assert trait_compatibility(similar_a, diff_b, "disassortative") > \
           trait_compatibility(similar_a, similar_b, "disassortative")


def test_spatial_distance_matches_euclidean():
    a = _mk(1, "F", 0.0, 0.0)
    b = _mk(2, "M", 0.3, 0.4)
    assert spatial_distance(a, b) == pytest.approx(0.5)
