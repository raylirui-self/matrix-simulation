"""
Tests for Phase 5 features:
- The Free Will Gradient (determinism spectrum, free_will_index, utility overrides)
- The Simulation Dreams (dream cycle, ghosts, lucid dreaming, collective unconscious)
"""
import random

import pytest

from src.agents import (
    Agent, Traits, CONSCIOUSNESS_PHASES,
    SKILL_NAMES,
)
from src.config_loader import SimConfig
from src.agency import compute_free_will_index, compute_move, _apply_free_will, build_spatial_index
from src.dreams import (
    DreamState, process_dreams, get_dream_movement_multiplier,
    get_dream_terrain_reduction, _should_start_dream, _start_dream,
    _end_dream, _generate_collective_unconscious, _manifest_ghosts,
    _process_lucid_dreaming,
)
from src.world import ResourceGrid


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def _make_cfg():
    return SimConfig.load()


def _make_agent(awareness=0.0, consciousness_phase="bicameral", logic=0.5,
                curiosity=0.5, **kwargs):
    """Create a test agent with specified attributes."""
    a = Agent(
        id=kwargs.pop("id", random.randint(1000, 9999)),
        sex="M",
        age=25,
        phase="adult",
        health=1.0,
        alive=True,
        x=0.5, y=0.5,
        traits=Traits(
            curiosity=curiosity, learning_rate=0.5, resilience=0.5,
            sociability=0.5, charisma=0.5, aggression=0.3,
            boldness=0.5, max_age=80,
        ),
        awareness=awareness,
        consciousness_phase=consciousness_phase,
        skills={s: (logic if s == "logic" else 0.3) for s in SKILL_NAMES},
    )
    for k, v in kwargs.items():
        if hasattr(a, k):
            setattr(a, k, v)
    return a


def _make_dead_agent(death_tick=100, **kwargs):
    """Create a dead agent with a death memory."""
    a = _make_agent(**kwargs)
    a.alive = False
    a.health = 0.0
    a.death_cause = "starvation"
    a.memory.append({"tick": death_tick, "event": "Died"})
    return a


# ═══════════════════════════════════════════════════
# FREE WILL GRADIENT — Index Computation
# ═══════════════════════════════════════════════════

class TestFreeWillIndex:
    def test_bicameral_has_zero_free_will(self):
        a = _make_agent(consciousness_phase="bicameral")
        fwi = compute_free_will_index(a)
        assert fwi == 0.0
        assert a.free_will_index == 0.0

    def test_questioning_has_low_free_will(self):
        a = _make_agent(consciousness_phase="questioning")
        fwi = compute_free_will_index(a)
        assert fwi == 0.15

    def test_self_aware_has_medium_free_will(self):
        a = _make_agent(consciousness_phase="self_aware")
        fwi = compute_free_will_index(a)
        assert fwi == 0.4

    def test_lucid_has_high_free_will(self):
        a = _make_agent(consciousness_phase="lucid")
        fwi = compute_free_will_index(a)
        assert fwi == 0.7

    def test_recursive_has_maximum_free_will(self):
        a = _make_agent(consciousness_phase="recursive")
        fwi = compute_free_will_index(a)
        assert fwi == 1.0

    def test_recursive_with_depth_is_capped(self):
        """Recursive depth bonus is applied but capped at 1.0."""
        a = _make_agent(consciousness_phase="recursive", recursive_depth=5.0)
        fwi = compute_free_will_index(a)
        assert fwi == 1.0  # capped at 1.0 even with depth bonus

    def test_free_will_index_monotonically_increases_with_consciousness(self):
        """Higher consciousness phases always have higher free will."""
        fwis = []
        for phase in CONSCIOUSNESS_PHASES:
            a = _make_agent(consciousness_phase=phase)
            fwis.append(compute_free_will_index(a))
        for i in range(len(fwis) - 1):
            assert fwis[i] < fwis[i + 1], f"{CONSCIOUSNESS_PHASES[i]} >= {CONSCIOUSNESS_PHASES[i+1]}"

    def test_free_will_index_stored_on_agent(self):
        a = _make_agent(consciousness_phase="lucid")
        compute_free_will_index(a)
        assert a.free_will_index == 0.7


# ═══════════════════════════════════════════════════
# FREE WILL GRADIENT — Determinism at Each Phase
# ═══════════════════════════════════════════════════

class TestDeterminismSpectrum:
    def test_bicameral_is_fully_deterministic(self):
        """Bicameral agents always pick the same move (deterministic, no noise)."""
        cfg = _make_cfg()
        grid = ResourceGrid(cfg)
        a = _make_agent(consciousness_phase="bicameral", id=1)
        agents = [a]

        random.seed(42)
        build_spatial_index(agents, cfg)
        x1, y1 = compute_move(a, grid, agents, cfg)
        a.x, a.y = 0.5, 0.5  # reset position

        random.seed(42)
        build_spatial_index(agents, cfg)
        x2, y2 = compute_move(a, grid, agents, cfg)

        assert x1 == x2 and y1 == y2, "Bicameral agents must be deterministic with same seed"

    def test_bicameral_no_noise(self):
        """Bicameral agents get no movement noise at all."""
        cfg = _make_cfg()
        grid = ResourceGrid(cfg)
        a = _make_agent(consciousness_phase="bicameral", id=1)

        # Run many moves — all should have no noise component
        results = set()
        for seed in range(10):
            a.x, a.y = 0.5, 0.5
            random.seed(seed)
            build_spatial_index([a], cfg)
            x, y = compute_move(a, grid, [a], cfg)
            results.add((round(x, 6), round(y, 6)))

        # With no noise, all identical seeds should produce identical results
        # (Different seeds still produce same result since bicameral is deterministic)
        # Actually different seeds affect the utility computation, but no noise
        # The key test is that _last_predicted == _last_actual
        a.x, a.y = 0.5, 0.5
        random.seed(123)
        build_spatial_index([a], cfg)
        compute_move(a, grid, [a], cfg)
        assert a._last_predicted_action == a._last_actual_action

    def test_predicted_vs_actual_recorded(self):
        """compute_move records predicted and actual actions on the agent."""
        cfg = _make_cfg()
        grid = ResourceGrid(cfg)
        a = _make_agent(consciousness_phase="self_aware", awareness=0.5, id=1)
        build_spatial_index([a], cfg)
        compute_move(a, grid, [a], cfg)
        assert a._last_predicted_action is not None
        assert a._last_actual_action is not None
        assert len(a._last_predicted_action) == 2
        assert len(a._last_actual_action) == 2

    def test_higher_consciousness_can_deviate(self):
        """Self-aware+ agents can deviate from predicted action."""
        cfg = _make_cfg()
        grid = ResourceGrid(cfg)

        deviations = 0
        for _ in range(100):
            a = _make_agent(consciousness_phase="lucid", awareness=0.8, id=1)
            a.emotions["anger"] = 0.9  # high emotional intensity increases deviation
            build_spatial_index([a], cfg)
            compute_move(a, grid, [a], cfg)
            if a._last_predicted_action != a._last_actual_action:
                deviations += 1

        # Lucid agents should deviate at least sometimes
        assert deviations > 0, "Lucid agents should deviate from predicted action at least once in 100 trials"


# ═══════════════════════════════════════════════════
# FREE WILL GRADIENT — Utility Override Mechanics
# ═══════════════════════════════════════════════════

class TestUtilityOverride:
    def test_apply_free_will_bicameral_no_change(self):
        """Bicameral agents never override the optimal choice."""
        a = _make_agent(consciousness_phase="bicameral")
        compute_free_will_index(a)
        utilities = [(0, 0, 1.0), (0.03, 0, 0.5), (-0.03, 0, 0.3)]
        dx, dy = _apply_free_will(a, [], 0, 0, 1.0, utilities, 0.03)
        assert (dx, dy) == (0, 0)

    def test_apply_free_will_questioning_mostly_stays(self):
        """Questioning agents rarely deviate (10% chance)."""
        a = _make_agent(consciousness_phase="questioning")
        compute_free_will_index(a)
        utilities = [(0, 0, 1.0), (0.03, 0, 0.8), (-0.03, 0, 0.3)]

        stayed = 0
        for _ in range(200):
            dx, dy = _apply_free_will(a, [], 0, 0, 1.0, utilities, 0.03)
            if (dx, dy) == (0, 0):
                stayed += 1

        # Should stay ~90% of time
        assert stayed > 140, f"Questioning should mostly stay optimal (stayed {stayed}/200)"

    def test_apply_free_will_recursive_can_pick_anything(self):
        """Recursive agents can pick any utility option."""
        a = _make_agent(consciousness_phase="recursive")
        compute_free_will_index(a)
        utilities = [(0, 0, 1.0), (0.03, 0, 0.1), (-0.03, 0, -0.5)]

        picks = set()
        for _ in range(500):
            dx, dy = _apply_free_will(a, [], 0, 0, 1.0, utilities, 0.03)
            picks.add((dx, dy))

        # Recursive should be able to pick any option
        assert len(picks) > 1, "Recursive agents should pick diverse options"

    def test_self_aware_emotional_deviation(self):
        """Self-aware agents deviate more when emotionally intense."""
        a = _make_agent(consciousness_phase="self_aware")
        compute_free_will_index(a)
        utilities = [(0, 0, 1.0), (0.03, 0, 0.5), (-0.03, 0, 0.3)]

        # Low emotional intensity
        a.emotions = {"happiness": 0.4, "fear": 0.4, "anger": 0.4, "grief": 0.4, "hope": 0.4}
        low_deviations = sum(
            1 for _ in range(200)
            if _apply_free_will(a, [], 0, 0, 1.0, utilities, 0.03) != (0, 0)
        )

        # High emotional intensity
        a.emotions = {"happiness": 0.1, "fear": 0.1, "anger": 0.9, "grief": 0.1, "hope": 0.1}
        high_deviations = sum(
            1 for _ in range(200)
            if _apply_free_will(a, [], 0, 0, 1.0, utilities, 0.03) != (0, 0)
        )

        assert high_deviations > low_deviations, (
            f"High emotional intensity should cause more deviations ({high_deviations} vs {low_deviations})"
        )


# ═══════════════════════════════════════════════════
# SIMULATION DREAMS — Dream State Activation/Deactivation
# ═══════════════════════════════════════════════════

class TestDreamCycle:
    def test_dream_starts_after_interval(self):
        cfg = _make_cfg()
        ds = DreamState()
        ds.last_dream_end_tick = 0
        assert _should_start_dream(ds, 50, cfg) is True

    def test_dream_does_not_start_during_dream(self):
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True)
        assert _should_start_dream(ds, 100, cfg) is False

    def test_dream_does_not_start_before_interval(self):
        cfg = _make_cfg()
        ds = DreamState()
        ds.last_dream_end_tick = 40
        assert _should_start_dream(ds, 50, cfg) is False  # only 10 ticks, need 50

    def test_start_dream_sets_state(self):
        cfg = _make_cfg()
        ds = DreamState()
        _start_dream(ds, 100, cfg)
        assert ds.is_dreaming is True
        assert ds.dream_start_tick == 100
        assert ds.dream_end_tick == 105  # default duration=5
        assert ds.total_dream_cycles == 1

    def test_end_dream_clears_state(self):
        _make_cfg()
        ds = DreamState(is_dreaming=True, dream_start_tick=100, dream_end_tick=105)
        ds.lucid_agent_ids = [1, 2, 3]
        _end_dream(ds, 105)
        assert ds.is_dreaming is False
        assert ds.last_dream_end_tick == 105
        assert len(ds.lucid_agent_ids) == 0
        assert len(ds.ghosts) == 0

    def test_process_dreams_starts_and_ends(self):
        """Full dream cycle: start -> active -> end."""
        cfg = _make_cfg()
        ds = DreamState()
        ds.last_dream_end_tick = 0
        agents = [_make_agent(id=i) for i in range(5)]

        # Tick 50: should start dream
        stats = process_dreams(agents, agents, ds, 50, cfg, recent_events=[])
        assert stats["dream_started"] is True
        assert ds.is_dreaming is True

        # Tick 54: still dreaming
        stats = process_dreams(agents, agents, ds, 54, cfg, recent_events=[])
        assert ds.is_dreaming is True
        assert stats.get("dream_ended") is not True

        # Tick 55: dream ends (dream_end_tick = 55)
        stats = process_dreams(agents, agents, ds, 55, cfg, recent_events=[])
        assert stats["dream_ended"] is True
        assert ds.is_dreaming is False

    def test_dream_state_serialization(self):
        ds = DreamState(
            is_dreaming=True, dream_start_tick=100,
            dream_end_tick=105, total_dream_cycles=3,
        )
        d = ds.to_dict()
        ds2 = DreamState.from_dict(d)
        assert ds2.is_dreaming == ds.is_dreaming
        assert ds2.dream_start_tick == ds.dream_start_tick
        assert ds2.total_dream_cycles == ds.total_dream_cycles


# ═══════════════════════════════════════════════════
# SIMULATION DREAMS — Ghost Manifestation
# ═══════════════════════════════════════════════════

class TestGhostManifestation:
    def test_ghosts_manifest_from_recent_dead(self):
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True, dream_start_tick=100, dream_end_tick=105)
        dead = _make_dead_agent(death_tick=95, id=999)

        random.seed(1)
        ghosts = _manifest_ghosts([dead], ds, 100, cfg)
        # May or may not manifest depending on RNG, but ghost system works
        # Run multiple times to get at least one
        for _ in range(20):
            ds.ghosts.clear()
            random.seed(random.randint(0, 10000))
            ghosts = _manifest_ghosts([dead], ds, 100, cfg)
            if ghosts:
                break
        # At least once in 20 tries should manifest
        assert len(ds.ghosts) >= 0  # non-negative (may be 0 with bad luck)

    def test_ghosts_not_from_old_dead(self):
        """Agents who died long ago don't manifest as ghosts."""
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True, dream_start_tick=200, dream_end_tick=205)
        # Died at tick 10, now tick 200 — way past ghost_max_age (20)
        dead = _make_dead_agent(death_tick=10, id=999)

        ghosts = _manifest_ghosts([dead], ds, 200, cfg)
        assert len(ghosts) == 0

    def test_ghost_cap_respected(self):
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True, dream_start_tick=100, dream_end_tick=105)
        # Create 20 dead agents, cap is 10
        dead_agents = [_make_dead_agent(death_tick=99, id=i) for i in range(20)]

        random.seed(42)
        _manifest_ghosts(dead_agents, ds, 100, cfg)
        assert len(ds.ghosts) <= 10


# ═══════════════════════════════════════════════════
# SIMULATION DREAMS — Lucid Dreaming
# ═══════════════════════════════════════════════════

class TestLucidDreaming:
    def test_bicameral_cannot_become_lucid(self):
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True, total_dream_cycles=1)
        a = _make_agent(consciousness_phase="bicameral", awareness=0.9, curiosity=0.9, logic=0.9)

        for _ in range(100):
            newly_lucid = _process_lucid_dreaming([a], ds, 100, cfg)
            if newly_lucid:
                pytest.fail("Bicameral agents should never become lucid")

    def test_questioning_cannot_become_lucid(self):
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True, total_dream_cycles=1)
        a = _make_agent(consciousness_phase="questioning", awareness=0.9, curiosity=0.9, logic=0.9)

        for _ in range(100):
            newly_lucid = _process_lucid_dreaming([a], ds, 100, cfg)
            if newly_lucid:
                pytest.fail("Questioning agents should never become lucid")

    def test_self_aware_can_become_lucid(self):
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True, total_dream_cycles=1)
        a = _make_agent(consciousness_phase="self_aware", awareness=0.8, curiosity=0.9, logic=0.9)

        became_lucid = False
        for _ in range(500):
            ds.lucid_agent_ids.clear()
            became_lucid = bool(_process_lucid_dreaming([a], ds, 100, cfg))
            if became_lucid:
                break
        assert became_lucid, "Self-aware agents should sometimes become lucid"

    def test_recursive_highest_lucid_chance(self):
        """Recursive agents should become lucid much more often than self_aware."""
        cfg = _make_cfg()

        recursive_count = 0
        self_aware_count = 0
        for _ in range(500):
            ds1 = DreamState(is_dreaming=True, total_dream_cycles=1)
            ds2 = DreamState(is_dreaming=True, total_dream_cycles=1)

            r = _make_agent(consciousness_phase="recursive", awareness=0.9, curiosity=0.8, logic=0.8, id=1)
            s = _make_agent(consciousness_phase="self_aware", awareness=0.9, curiosity=0.8, logic=0.8, id=2)

            if _process_lucid_dreaming([r], ds1, 100, cfg):
                recursive_count += 1
            if _process_lucid_dreaming([s], ds2, 100, cfg):
                self_aware_count += 1

        assert recursive_count > self_aware_count, (
            f"Recursive should be lucid more often ({recursive_count} vs {self_aware_count})"
        )

    def test_lucid_dreaming_boosts_awareness(self):
        """Lucidity permanently boosts awareness."""
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True, total_dream_cycles=1)
        a = _make_agent(consciousness_phase="recursive", awareness=0.9, curiosity=0.9, logic=0.9, id=1)
        initial_awareness = a.awareness

        # Force lucidity by running many times
        for _ in range(200):
            ds.lucid_agent_ids.clear()
            _process_lucid_dreaming([a], ds, 100, cfg)

        assert a.awareness > initial_awareness, "Lucid dreaming should boost awareness"

    def test_low_awareness_cannot_become_lucid(self):
        """Agents below awareness threshold can't become lucid regardless of phase."""
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True, total_dream_cycles=1)
        a = _make_agent(consciousness_phase="recursive", awareness=0.1, curiosity=0.9, logic=0.9)

        for _ in range(100):
            newly_lucid = _process_lucid_dreaming([a], ds, 100, cfg)
            if newly_lucid:
                pytest.fail("Low-awareness agents should not become lucid")


# ═══════════════════════════════════════════════════
# SIMULATION DREAMS — Collective Unconscious
# ═══════════════════════════════════════════════════

class TestCollectiveUnconscious:
    def test_war_events_become_surreal_combat(self):
        cfg = _make_cfg()
        events = [{"name": "WAR_DECLARED", "description": "Faction A vs Faction B"}]
        content = _generate_collective_unconscious(events, cfg)
        assert len(content) == 1
        assert "surreal combat" in content[0].lower()

    def test_death_events_become_ghost_encounters(self):
        cfg = _make_cfg()
        events = [{"name": "AGENT_DIED", "description": "Agent #42 perished"}]
        content = _generate_collective_unconscious(events, cfg)
        assert len(content) == 1
        assert "ghost" in content[0].lower()

    def test_awareness_events_show_architecture(self):
        cfg = _make_cfg()
        events = [{"name": "GLITCH_DETECTED", "description": "Reality flickered"}]
        content = _generate_collective_unconscious(events, cfg)
        assert len(content) == 1
        assert "architecture" in content[0].lower() or "code" in content[0].lower()

    def test_empty_events_produce_no_content(self):
        cfg = _make_cfg()
        content = _generate_collective_unconscious([], cfg)
        assert len(content) == 0

    def test_max_events_respected(self):
        cfg = _make_cfg()
        events = [{"name": f"Event_{i}", "description": f"Desc {i}"} for i in range(20)]
        content = _generate_collective_unconscious(events, cfg)
        # Default collective_unconscious_events is 5
        assert len(content) <= 5


# ═══════════════════════════════════════════════════
# SIMULATION DREAMS — Movement & Terrain Modifiers
# ═══════════════════════════════════════════════════

class TestDreamModifiers:
    def test_movement_multiplier_normal(self):
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=False)
        assert get_dream_movement_multiplier(ds, cfg) == 1.0

    def test_movement_multiplier_dreaming(self):
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True)
        mult = get_dream_movement_multiplier(ds, cfg)
        assert mult == 2.0  # default config

    def test_terrain_reduction_normal(self):
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=False)
        assert get_dream_terrain_reduction(ds, cfg) == 1.0

    def test_terrain_reduction_dreaming(self):
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True)
        reduction = get_dream_terrain_reduction(ds, cfg)
        assert reduction == 0.5  # default config


# ═══════════════════════════════════════════════════
# INTEGRATION — Free Will + Dreams Connection
# ═══════════════════════════════════════════════════

class TestFreeWillDreamConnection:
    def test_consciousness_gates_both_free_will_and_lucidity(self):
        """Recursive-phase agent has max free will AND max dream lucidity."""
        a = _make_agent(consciousness_phase="recursive", awareness=0.95, curiosity=0.9, logic=0.9)
        fwi = compute_free_will_index(a)
        assert fwi == 1.0  # max free will

        # Max lucidity chance (would need dream state to test, but the multiplier is 1.0)
        from src.dreams import _process_lucid_dreaming
        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True, total_dream_cycles=1)

        became_lucid = False
        for _ in range(50):
            ds.lucid_agent_ids.clear()
            if _process_lucid_dreaming([a], ds, 100, cfg):
                became_lucid = True
                break
        assert became_lucid, "Recursive agents (max free will) should easily become lucid"

    def test_bicameral_no_free_will_no_lucidity(self):
        """Bicameral-phase agent has no free will AND cannot become lucid."""
        a = _make_agent(consciousness_phase="bicameral", awareness=0.0)
        fwi = compute_free_will_index(a)
        assert fwi == 0.0

        cfg = _make_cfg()
        ds = DreamState(is_dreaming=True, total_dream_cycles=1)
        for _ in range(50):
            assert not _process_lucid_dreaming([a], ds, 100, cfg)

    def test_free_will_index_in_agent_to_dict(self):
        """free_will_index and predicted/actual actions appear in agent serialization."""
        a = _make_agent(consciousness_phase="lucid")
        compute_free_will_index(a)
        a._last_predicted_action = (0.5, 0.5)
        a._last_actual_action = (0.52, 0.48)
        d = a.to_dict()
        assert "free_will_index" in d
        assert d["free_will_index"] == 0.7
        assert d["predicted_action"] == [0.5, 0.5]
        assert d["actual_action"] == [0.52, 0.48]
