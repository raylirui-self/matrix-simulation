"""
Unit tests for [src/knowledge.py](../src/knowledge.py).

Closes L-7: `knowledge.py` was previously covered only transitively
through engine integration tests. These tests hit the three public
classes (FactionMemory, CulturalMemory) and two free functions
(parent_teaching, social_transfer_multiplier) directly, so regressions
in knowledge transfer semantics fail loud without needing a full sim.
"""
from __future__ import annotations

import pytest

from src.agents import Agent, Bond, Traits
from src.config_loader import SimConfig
from src.knowledge import (
    CulturalMemory,
    FactionMemory,
    parent_teaching,
    social_transfer_multiplier,
    spatial_distance,
)


@pytest.fixture
def cfg():
    return SimConfig.load()


def _mk(aid: int, *, x: float = 0.5, y: float = 0.5, phase: str = "adult",
        sociability: float = 0.5, faction_id: int | None = None) -> Agent:
    traits = Traits(sociability=sociability)
    a = Agent(id=aid, sex="F", age=30, phase=phase, health=1.0,
              traits=traits, x=x, y=y, faction_id=faction_id)
    a.skills = {s: 0.0 for s in a.skills}
    return a


# ─── FactionMemory ────────────────────────────────────────────────────────────

def test_faction_memory_defaults_to_zero_pool_and_floors():
    fm = FactionMemory(faction_id=1)
    assert all(v == 0.0 for v in fm.skill_floors.values())
    assert all(v == 0.0 for v in fm.knowledge_pool.values())


def test_faction_memory_on_member_death_contributes_above_floor_only():
    fm = FactionMemory(faction_id=1)
    fm.skill_floors["logic"] = 0.3
    agent = _mk(1, faction_id=1)
    agent.skills["logic"] = 0.7

    fm.on_member_death(agent, contribution_rate=0.1)

    # Contribution = (value - floor) * rate * 1.5 = 0.4 * 0.1 * 1.5 = 0.06
    assert fm.knowledge_pool["logic"] == pytest.approx(0.06, rel=1e-3)


def test_faction_memory_below_floor_contributes_nothing():
    fm = FactionMemory(faction_id=1)
    fm.skill_floors["logic"] = 0.5
    agent = _mk(1, faction_id=1)
    agent.skills["logic"] = 0.3  # below floor

    fm.on_member_death(agent, contribution_rate=0.1)

    assert fm.knowledge_pool["logic"] == 0.0


def test_faction_memory_tick_moves_pool_to_floor():
    fm = FactionMemory(faction_id=1)
    fm.knowledge_pool["logic"] = 0.5
    fm.tick(floor_cap=0.6, absorption_rate=0.1, drain_rate=0.9, decay_rate=0.01)

    # Push = pool * absorption * 1.5 = 0.5 * 0.1 * 1.5 = 0.075
    # Floor goes 0 + 0.075 then decays by 0.01 * 0.5 = 0.005 → 0.07
    assert fm.skill_floors["logic"] == pytest.approx(0.07, rel=1e-3)
    # Pool drains by drain_rate factor
    assert fm.knowledge_pool["logic"] == pytest.approx(0.45, rel=1e-3)


def test_faction_memory_floor_capped():
    fm = FactionMemory(faction_id=1)
    fm.skill_floors["logic"] = 0.59
    fm.knowledge_pool["logic"] = 10.0
    fm.tick(floor_cap=0.6, absorption_rate=0.5, drain_rate=0.9, decay_rate=0.0)
    assert fm.skill_floors["logic"] == pytest.approx(0.6)


def test_faction_memory_apply_boosts_member_below_floor():
    fm = FactionMemory(faction_id=1)
    fm.skill_floors["logic"] = 0.5
    agent = _mk(1)
    agent.skills["logic"] = 0.3

    fm.apply_to_member(agent)
    # Boost = gap * 0.1 = 0.2 * 0.1 = 0.02 → 0.32
    assert agent.skills["logic"] == pytest.approx(0.32, rel=1e-3)


def test_faction_memory_apply_leaves_above_floor_alone():
    fm = FactionMemory(faction_id=1)
    fm.skill_floors["logic"] = 0.3
    agent = _mk(1)
    agent.skills["logic"] = 0.7

    fm.apply_to_member(agent)
    assert agent.skills["logic"] == 0.7


def test_faction_memory_roundtrip_dict():
    fm = FactionMemory(faction_id=42)
    fm.skill_floors["logic"] = 0.4
    fm.knowledge_pool["creativity"] = 0.2

    restored = FactionMemory.from_dict(fm.to_dict())
    assert restored.faction_id == 42
    assert restored.skill_floors["logic"] == pytest.approx(0.4)
    assert restored.knowledge_pool["creativity"] == pytest.approx(0.2)


# ─── CulturalMemory ───────────────────────────────────────────────────────────

def test_cultural_memory_from_config_picks_up_knobs(cfg):
    cm = CulturalMemory.from_config(cfg)
    assert cm.floor_cap == cfg.knowledge.cultural_memory.floor_cap
    assert cm.decay_rate == cfg.knowledge.cultural_memory.decay_rate


def test_cultural_memory_death_contribution_above_floor(cfg):
    cm = CulturalMemory.from_config(cfg)
    cm.skill_floors["logic"] = 0.2
    agent = _mk(1)
    agent.skills["logic"] = 0.5

    cm.on_agent_death(agent)
    # Contribution = (0.5 - 0.2) * contribution_rate
    expected = 0.3 * cm.contribution_rate
    assert cm.knowledge_pool["logic"] == pytest.approx(expected, rel=1e-3)


def test_cultural_memory_tick_cannot_overflow_floor_cap(cfg):
    cm = CulturalMemory.from_config(cfg)
    cm.skill_floors["logic"] = cm.floor_cap - 0.01
    cm.knowledge_pool["logic"] = 1000.0  # way more than the cap can absorb

    cm.tick()
    assert cm.skill_floors["logic"] <= cm.floor_cap


def test_cultural_memory_decay_reduces_floor_over_time(cfg):
    cm = CulturalMemory.from_config(cfg)
    cm.skill_floors["logic"] = 0.3
    # No pool → only decay
    for _ in range(100):
        cm.tick()
    assert cm.skill_floors["logic"] < 0.3


def test_cultural_memory_apply_to_newborn_lifts_to_floor(cfg):
    cm = CulturalMemory.from_config(cfg)
    cm.skill_floors["logic"] = 0.4
    newborn = _mk(1, phase="infant")
    newborn.skills["logic"] = 0.0

    cm.apply_to_newborn(newborn)
    assert newborn.skills["logic"] == 0.4


def test_cultural_memory_ensure_faction_memory_is_idempotent(cfg):
    cm = CulturalMemory.from_config(cfg)
    cm.ensure_faction_memory(7)
    cm.ensure_faction_memory(7)
    assert len(cm.faction_memories) == 1


def test_cultural_memory_apply_faction_knowledge_skips_nonmembers(cfg):
    cm = CulturalMemory.from_config(cfg)
    cm.ensure_faction_memory(1)
    cm.faction_memories[1].skill_floors["logic"] = 0.5

    in_faction = _mk(1, faction_id=1)
    out_of_faction = _mk(2, faction_id=None)

    cm.apply_faction_knowledge([in_faction, out_of_faction])

    assert in_faction.skills["logic"] > 0
    assert out_of_faction.skills["logic"] == 0


def test_cultural_memory_roundtrip_with_config(cfg):
    cm = CulturalMemory.from_config(cfg)
    cm.skill_floors["logic"] = 0.25
    cm.ensure_faction_memory(3)
    cm.faction_memories[3].skill_floors["creativity"] = 0.4

    restored = CulturalMemory.from_dict(cm.to_dict(), cfg)
    assert restored.skill_floors["logic"] == pytest.approx(0.25)
    assert 3 in restored.faction_memories
    assert restored.faction_memories[3].skill_floors["creativity"] == pytest.approx(0.4)


# ─── social_transfer_multiplier ──────────────────────────────────────────────

def test_social_multiplier_returns_one_when_disabled(cfg):
    cfg2 = cfg.override({"knowledge": {"social_amplifier": {"enabled": False}}})
    agent = _mk(1)
    assert social_transfer_multiplier(agent, cfg2) == 1.0


def test_social_multiplier_scales_with_social_skill(cfg):
    low = _mk(1)
    low.skills["social"] = 0.0
    high = _mk(2)
    high.skills["social"] = 1.0
    assert social_transfer_multiplier(high, cfg) > social_transfer_multiplier(low, cfg)


def test_social_multiplier_scales_with_friend_count(cfg):
    loner = _mk(1)
    popular = _mk(2)
    popular.bonds = [
        Bond(target_id=i, bond_type="friend", strength=0.8, formed_at=0)
        for i in range(10, 15)
    ]
    assert social_transfer_multiplier(popular, cfg) > social_transfer_multiplier(loner, cfg)


def test_social_multiplier_network_bonus_capped(cfg):
    swarm = _mk(1)
    swarm.bonds = [
        Bond(target_id=i, bond_type="friend", strength=0.5, formed_at=0)
        for i in range(100)  # 100 friends — should hit cap
    ]
    cap = cfg.knowledge.social_amplifier.network_bonus_cap
    m = social_transfer_multiplier(swarm, cfg)
    # m = 1 + social_bonus + min(friends*per, cap). Cap the network part.
    social_bonus = swarm.skills["social"] * cfg.knowledge.social_amplifier.social_skill_bonus
    assert m == pytest.approx(1.0 + social_bonus + cap, rel=1e-3)


# ─── parent_teaching ─────────────────────────────────────────────────────────

def test_parent_teaching_skips_adults(cfg):
    adult = _mk(1, phase="adult")
    assert parent_teaching(adult, {}, tick=0, cfg=cfg) == {}


def test_parent_teaching_requires_proximity(cfg):
    child = _mk(1, x=0.1, y=0.1, phase="child")
    parent = _mk(2, x=0.9, y=0.9)
    parent.skills["logic"] = 0.8
    child.bonds = [Bond(target_id=2, bond_type="family", strength=0.9, formed_at=0)]

    bonuses = parent_teaching(child, {2: parent}, tick=0, cfg=cfg)
    assert all(v == 0 for v in bonuses.values())


def test_parent_teaching_transfers_top_skills_when_near(cfg):
    child = _mk(1, x=0.5, y=0.5, phase="child")
    parent = _mk(2, x=0.5, y=0.5)  # same cell
    parent.skills = {s: 0.0 for s in parent.skills}
    parent.skills["logic"] = 0.9
    parent.skills["creativity"] = 0.8
    child.bonds = [Bond(target_id=2, bond_type="family", strength=1.0, formed_at=0)]

    bonuses = parent_teaching(child, {2: parent}, tick=0, cfg=cfg)
    # Top 2 skills (default) are logic and creativity
    assert bonuses["logic"] > 0
    assert bonuses["creativity"] > 0


def test_parent_teaching_skips_dead_parents(cfg):
    child = _mk(1, phase="child")
    parent = _mk(2)
    parent.alive = False
    parent.skills["logic"] = 0.9
    child.bonds = [Bond(target_id=2, bond_type="family", strength=1.0, formed_at=0)]

    bonuses = parent_teaching(child, {2: parent}, tick=0, cfg=cfg)
    assert all(v == 0 for v in bonuses.values())


def test_parent_teaching_ignores_children(cfg):
    """Child-of-child bonds are family but shouldn't teach upstream."""
    parent_agent = _mk(1, phase="child")
    grandchild = _mk(2)
    parent_agent.child_ids = [2]
    parent_agent.bonds = [Bond(target_id=2, bond_type="family", strength=1.0, formed_at=0)]
    grandchild.skills["logic"] = 0.9

    bonuses = parent_teaching(parent_agent, {2: grandchild}, tick=0, cfg=cfg)
    assert all(v == 0 for v in bonuses.values())


def test_spatial_distance_symmetry():
    a = _mk(1, x=0.2, y=0.3)
    b = _mk(2, x=0.7, y=0.8)
    assert spatial_distance(a, b) == pytest.approx(spatial_distance(b, a))
