"""
Unit tests for [src/social.py](../src/social.py).

Covers L-7 (prior L-1) in [docs/code_review.md](../docs/code_review.md) —
`src/social.py` was previously at ~6% line coverage because tests
exercised it only transitively through the engine tick loop.

These tests hit `process_bonds` directly with crafted agent sets
so that bond formation, decay, and rival dynamics each have a
focused regression signal.
"""
from __future__ import annotations

import pytest

from src.agents import Agent, Bond, Traits
from src.config_loader import SimConfig
from src.social import process_bonds, spatial_distance


@pytest.fixture
def cfg():
    return SimConfig.load()


def _mk(aid: int, x: float, y: float, *, sociability: float = 0.8,
        aggression: float = 0.1, age: int = 25) -> Agent:
    """Build an adult agent positioned at (x, y) with tunable traits."""
    traits = Traits(sociability=sociability, aggression=aggression, resilience=0.5)
    a = Agent(id=aid, sex="F", age=age, phase="adult", health=1.0,
              traits=traits, x=x, y=y)
    return a


# ─── Bond formation ───────────────────────────────────────────────────────────

def test_friends_form_after_sustained_proximity(cfg):
    """Two nearby sociable agents become friends after enough ticks."""
    a = _mk(1, 0.5, 0.5, sociability=0.9)
    b = _mk(2, 0.51, 0.5, sociability=0.9)
    agents = [a, b]

    # Run enough ticks to pass friend_ticks_to_form
    ticks_needed = cfg.social.friend_ticks_to_form + 2
    for tick in range(ticks_needed):
        process_bonds(agents, tick, cfg)

    assert a.has_bond_with(b.id) is not None
    assert a.has_bond_with(b.id).bond_type == "friend"


def test_friends_do_not_form_across_distance(cfg):
    """Agents further apart than friend_formation_distance never bond."""
    far = cfg.social.friend_formation_distance * 3
    a = _mk(1, 0.1, 0.1, sociability=0.9)
    b = _mk(2, 0.1 + far, 0.1, sociability=0.9)
    agents = [a, b]

    for tick in range(cfg.social.friend_ticks_to_form + 5):
        process_bonds(agents, tick, cfg)

    assert a.has_bond_with(b.id) is None


def test_low_sociability_agents_do_not_befriend(cfg):
    """Agents below `friend_min_sociability` are skipped entirely."""
    a = _mk(1, 0.5, 0.5, sociability=0.0)
    b = _mk(2, 0.5, 0.5, sociability=0.0)
    agents = [a, b]

    for tick in range(cfg.social.friend_ticks_to_form + 5):
        process_bonds(agents, tick, cfg)

    assert a.has_bond_with(b.id) is None


# ─── Bond decay ───────────────────────────────────────────────────────────────

def test_friend_bond_decays_when_target_dies(cfg):
    """A friend bond to a dead agent decays at 3× the normal rate."""
    a = _mk(1, 0.5, 0.5)
    dead = _mk(2, 0.5, 0.5)
    dead.alive = False

    # Pre-seed a friend bond
    bond = Bond(target_id=dead.id, bond_type="friend", strength=1.0, formed_at=0)
    a.bonds.append(bond)

    for tick in range(500):
        process_bonds([a, dead], tick, cfg)
        if not a.has_bond_with(dead.id):
            break

    assert a.has_bond_with(dead.id) is None, "Bond should have decayed to zero"


def test_family_bonds_do_not_decay(cfg):
    """Family bonds are excluded from decay regardless of distance."""
    a = _mk(1, 0.1, 0.1)
    b = _mk(2, 0.9, 0.9)
    a.bonds.append(Bond(target_id=b.id, bond_type="family", strength=0.5, formed_at=0))

    for tick in range(200):
        process_bonds([a, b], tick, cfg)

    family = a.has_bond_with(b.id)
    assert family is not None
    assert family.strength == 0.5, "Family bond strength must be invariant"


# ─── Spatial index / edge cases ───────────────────────────────────────────────

def test_empty_agent_list_returns_zero_stats(cfg):
    """No agents → no crashes, no work."""
    stats = process_bonds([], tick=0, cfg=cfg)
    assert stats == {"bonds_formed": 0, "bonds_decayed": 0}


def test_only_dead_agents_is_a_no_op(cfg):
    """Filter-to-alive must produce an empty working set without division errors."""
    a = _mk(1, 0.5, 0.5)
    a.alive = False
    stats = process_bonds([a], tick=0, cfg=cfg)
    assert stats["bonds_formed"] == 0


def test_spatial_distance_is_symmetric():
    a = _mk(1, 0.2, 0.3)
    b = _mk(2, 0.7, 0.8)
    assert spatial_distance(a, b) == pytest.approx(spatial_distance(b, a))
    assert spatial_distance(a, a) == 0.0
