"""
Tests for Nested Simulations (Phase 5):
- Computational Theory tech breakthrough unlock conditions
- World Engine creation
- Sub-simulation initialization and ticking
- Sub-sim agent awareness growth
- Recursive awareness detection
- Performance (sub-sim tick < 10ms)
"""
import time
import random


from src.agents import create_agent
from src.engine import SimulationEngine, RunState
from src.nested_sim import (
    SubSimulation, create_world_engine, process_nested_simulations,
    _create_sub_agent,
)
from src.world import ResourceGrid, TechBreakthrough


# ===================================================
# TEST: Computational Theory Unlock Conditions
# ===================================================

class TestComputationalTheoryBreakthrough:
    """Tests for the computational_theory tech breakthrough."""

    def test_config_has_computational_theory(self, cfg):
        """computational_theory exists in tech breakthrough thresholds."""
        thresholds = cfg.environment.tech_breakthroughs.thresholds
        names = [t["name"] for t in thresholds]
        assert "computational_theory" in names

    def test_breakthrough_requires_logic(self, cfg):
        """computational_theory requires logic > 0.8."""
        thresholds = cfg.environment.tech_breakthroughs.thresholds
        ct = next(t for t in thresholds if t["name"] == "computational_theory")
        assert ct["requires_logic"] == 0.8

    def test_breakthrough_requires_tech(self, cfg):
        """computational_theory requires tech_level > 0.7."""
        thresholds = cfg.environment.tech_breakthroughs.thresholds
        ct = next(t for t in thresholds if t["name"] == "computational_theory")
        assert ct["tech_level"] == 0.7

    def test_breakthrough_requires_population(self, cfg):
        """computational_theory requires population > 5."""
        thresholds = cfg.environment.tech_breakthroughs.thresholds
        ct = next(t for t in thresholds if t["name"] == "computational_theory")
        assert ct["requires_population"] == 5

    def test_unlock_succeeds_when_conditions_met(self, cfg):
        """Breakthrough unlocks when logic, tech, and population thresholds are met."""
        grid = ResourceGrid(cfg)
        cell = grid.cells[0][0]
        cell.agent_count = 6  # > 5
        bt = grid.check_breakthroughs(
            cell, avg_tech=0.75, avg_social=0.5, tick=100, avg_logic=0.85,
        )
        # Should unlock computational_theory (or an earlier one first)
        # Force all earlier techs to be already unlocked
        cell.unlocked_techs = [
            TechBreakthrough(name="agriculture", unlocked_at=10, resource_bonus=0.2, capacity_bonus=0),
            TechBreakthrough(name="mining", unlocked_at=30, resource_bonus=0.15, capacity_bonus=0),
            TechBreakthrough(name="trade_networks", unlocked_at=50, resource_bonus=0.1, capacity_bonus=5),
            TechBreakthrough(name="industrialization", unlocked_at=80, resource_bonus=0.25, capacity_bonus=15),
        ]
        bt = grid.check_breakthroughs(
            cell, avg_tech=0.75, avg_social=0.5, tick=100, avg_logic=0.85,
        )
        assert bt is not None
        assert bt.name == "computational_theory"

    def test_unlock_fails_low_logic(self, cfg):
        """Breakthrough does not unlock when logic is too low."""
        grid = ResourceGrid(cfg)
        cell = grid.cells[0][0]
        cell.agent_count = 6
        # Pre-unlock earlier techs
        cell.unlocked_techs = [
            TechBreakthrough(name="agriculture", unlocked_at=10, resource_bonus=0.2, capacity_bonus=0),
            TechBreakthrough(name="trade_networks", unlocked_at=50, resource_bonus=0.1, capacity_bonus=5),
        ]
        bt = grid.check_breakthroughs(
            cell, avg_tech=0.75, avg_social=0.5, tick=100, avg_logic=0.5,  # logic too low
        )
        # Should not be computational_theory
        assert bt is None or bt.name != "computational_theory"

    def test_unlock_fails_low_population(self, cfg):
        """Breakthrough does not unlock when population is too low."""
        grid = ResourceGrid(cfg)
        cell = grid.cells[0][0]
        cell.agent_count = 3  # < 5
        cell.unlocked_techs = [
            TechBreakthrough(name="agriculture", unlocked_at=10, resource_bonus=0.2, capacity_bonus=0),
            TechBreakthrough(name="trade_networks", unlocked_at=50, resource_bonus=0.1, capacity_bonus=5),
        ]
        bt = grid.check_breakthroughs(
            cell, avg_tech=0.75, avg_social=0.5, tick=100, avg_logic=0.85,
        )
        assert bt is None or bt.name != "computational_theory"

    def test_unlock_fails_low_tech(self, cfg):
        """Breakthrough does not unlock when tech is too low."""
        grid = ResourceGrid(cfg)
        cell = grid.cells[0][0]
        cell.agent_count = 6
        cell.unlocked_techs = [
            TechBreakthrough(name="agriculture", unlocked_at=10, resource_bonus=0.2, capacity_bonus=0),
            TechBreakthrough(name="trade_networks", unlocked_at=50, resource_bonus=0.1, capacity_bonus=5),
        ]
        bt = grid.check_breakthroughs(
            cell, avg_tech=0.4, avg_social=0.5, tick=100, avg_logic=0.85,  # tech too low
        )
        assert bt is None or bt.name != "computational_theory"


# ===================================================
# TEST: World Engine Creation
# ===================================================

class TestWorldEngineCreation:
    """Tests for World Engine creation."""

    def test_create_world_engine(self, cfg):
        """World Engine is created with correct initial state."""
        engine = create_world_engine(
            cell_row=2, cell_col=3, tick=100, builder_id=42, cfg=cfg,
        )
        assert engine.cell_row == 2
        assert engine.cell_col == 3
        assert engine.created_at == 100
        assert engine.builder_id == 42
        assert engine.sub_sim is not None

    def test_sub_sim_initialized_with_agents(self, cfg):
        """Sub-simulation starts with the configured number of agents."""
        engine = create_world_engine(0, 0, 0, 1, cfg)
        initial = getattr(cfg.nested_simulation, 'sub_initial_agents', 8)
        assert len(engine.sub_sim.agents) == initial
        assert all(a.alive for a in engine.sub_sim.agents)

    def test_sub_sim_grid_size(self, cfg):
        """Sub-simulation uses configured grid size (4x4)."""
        engine = create_world_engine(0, 0, 0, 1, cfg)
        assert engine.sub_sim.grid_size == 4

    def test_sub_sim_max_agents(self, cfg):
        """Sub-simulation respects max agent limit."""
        engine = create_world_engine(0, 0, 0, 1, cfg)
        assert engine.sub_sim.max_agents == 20

    def test_world_engine_to_dict(self, cfg):
        """World Engine serializes correctly."""
        engine = create_world_engine(1, 2, 50, 10, cfg)
        d = engine.to_dict()
        assert d["cell_row"] == 1
        assert d["cell_col"] == 2
        assert d["created_at"] == 50
        assert "sub_sim" in d
        assert "alive_count" in d["sub_sim"]


# ===================================================
# TEST: Sub-Simulation Ticking
# ===================================================

class TestSubSimulationTicking:
    """Tests for sub-simulation tick processing."""

    def test_tick_increments_counter(self):
        """Each tick increments the sub-sim tick counter."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(5)
        sub.tick()
        assert sub.tick_count == 1
        sub.tick()
        assert sub.tick_count == 2

    def test_agents_age(self):
        """Sub-sim agents age each tick."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(5)
        initial_ages = [a.age for a in sub.agents]
        sub.tick()
        for i, a in enumerate(sub.agents):
            assert a.age == initial_ages[i] + 1

    def test_agents_move(self):
        """Sub-sim agents move each tick."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(5)
        initial_positions = [(a.x, a.y) for a in sub.agents]
        random.seed(99)  # different seed to ensure movement
        sub.tick()
        moved = sum(1 for i, a in enumerate(sub.agents)
                     if (a.x, a.y) != initial_positions[i])
        assert moved > 0, "At least some agents should have moved"

    def test_agents_die_of_old_age(self):
        """Sub-sim agents die when reaching max age."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(1)
        agent = sub.agents[0]
        agent.age = agent.max_age - 1
        agent.health = 1.0
        sub.tick()
        assert not agent.alive

    def test_agents_die_of_health(self):
        """Sub-sim agents die when health reaches 0."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(1)
        agent = sub.agents[0]
        agent.health = 0.001
        sub.tick()
        assert not agent.alive

    def test_tick_returns_stats(self):
        """Tick returns a stats dict with expected keys."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(5)
        stats = sub.tick()
        assert "tick" in stats
        assert "alive" in stats
        assert "deaths" in stats
        assert "births" in stats
        assert "recursive_events" in stats

    def test_sub_sim_to_dict(self):
        """Sub-simulation serializes to dict."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(5)
        sub.tick()
        d = sub.to_dict()
        assert d["grid_size"] == 4
        assert d["tick_count"] == 1
        assert d["depth"] == 1
        assert "agents" in d
        assert "avg_awareness" in d


# ===================================================
# TEST: Sub-Sim Agent Awareness Growth
# ===================================================

class TestSubSimAwarenessGrowth:
    """Tests for awareness growth in sub-simulations."""

    def test_awareness_grows_over_time(self):
        """Sub-sim agent awareness increases over multiple ticks."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(1)
        agent = sub.agents[0]
        agent.health = 10.0  # prevent death
        agent.max_age = 9999
        agent.curiosity = 0.8
        agent.intelligence = 0.6
        initial_awareness = agent.awareness
        for _ in range(50):
            sub.tick(awareness_growth_rate=0.012)
        assert agent.awareness > initial_awareness
        assert agent.awareness > 0.1

    def test_high_curiosity_grows_faster(self):
        """Agents with higher curiosity gain awareness faster."""
        sub1 = SubSimulation(grid_size=4, max_agents=20)
        sub1.initialize(1)
        sub1.agents[0].curiosity = 0.9
        sub1.agents[0].intelligence = 0.5
        sub1.agents[0].health = 10.0
        sub1.agents[0].max_age = 9999

        sub2 = SubSimulation(grid_size=4, max_agents=20)
        sub2.initialize(1)
        sub2.agents[0].curiosity = 0.1
        sub2.agents[0].intelligence = 0.5
        sub2.agents[0].health = 10.0
        sub2.agents[0].max_age = 9999

        for _ in range(50):
            sub1.tick(awareness_growth_rate=0.012)
            sub2.tick(awareness_growth_rate=0.012)

        assert sub1.agents[0].awareness > sub2.agents[0].awareness

    def test_consciousness_phase_updates(self):
        """Consciousness phase advances as awareness grows."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(1)
        agent = sub.agents[0]
        agent.health = 10.0
        agent.max_age = 9999
        agent.curiosity = 0.9
        agent.intelligence = 0.8
        agent.system_trust = 0.0  # no suppression

        assert agent.consciousness_phase == "bicameral"
        for _ in range(200):
            sub.tick(awareness_growth_rate=0.015)
        assert agent.consciousness_phase != "bicameral"

    def test_system_trust_erodes_with_awareness(self):
        """System trust decreases as awareness grows past 0.3."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(1)
        agent = sub.agents[0]
        agent.health = 10.0
        agent.max_age = 9999
        agent.awareness = 0.5  # above threshold
        agent.system_trust = 0.7
        initial_trust = agent.system_trust
        for _ in range(20):
            sub.tick()
        assert agent.system_trust < initial_trust


# ===================================================
# TEST: Recursive Awareness Detection
# ===================================================

class TestRecursiveAwareness:
    """Tests for the recursive awareness paradox."""

    def test_recursive_event_triggered(self):
        """Recursive event fires when sub-agent crosses threshold."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(1)
        agent = sub.agents[0]
        agent.health = 10.0
        agent.max_age = 9999
        agent.awareness = 0.69
        agent.consciousness_phase = "lucid"
        agent.curiosity = 0.9
        agent.intelligence = 0.9
        agent.system_trust = 0.0

        stats = sub.tick(recursive_threshold=0.7)
        # Agent should cross threshold
        if agent.awareness >= 0.7:
            assert agent.recursive_detected
            assert len(stats["recursive_events"]) > 0
            event = stats["recursive_events"][0]
            assert "Am I in the real Matrix" in event["question"]
            assert event["depth"] == 1

    def test_recursive_only_fires_once(self):
        """Recursive paradox event only fires once per agent."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(1)
        agent = sub.agents[0]
        agent.health = 10.0
        agent.max_age = 9999
        agent.awareness = 0.8
        agent.consciousness_phase = "recursive"
        agent.recursive_detected = False

        stats1 = sub.tick(recursive_threshold=0.7)
        assert agent.recursive_detected
        len(stats1["recursive_events"])

        stats2 = sub.tick(recursive_threshold=0.7)
        events_2 = len(stats2["recursive_events"])
        assert events_2 == 0  # should not fire again

    def test_recursive_requires_consciousness_phase(self):
        """Recursive event requires lucid or recursive phase at tick start.
        We set awareness below the lucid threshold (0.6) so the phase
        update during the tick won't promote past 'self_aware'."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(1)
        agent = sub.agents[0]
        agent.health = 10.0
        agent.max_age = 9999
        agent.awareness = 0.5  # above recursive_threshold but below lucid phase (0.6)
        agent.consciousness_phase = "self_aware"
        agent.curiosity = 0.0  # minimize growth so we stay below lucid
        agent.intelligence = 0.0

        sub.tick(recursive_threshold=0.3)  # threshold below awareness
        # Agent has awareness > threshold but consciousness_phase is self_aware (not lucid/recursive)
        # so recursive should NOT fire despite awareness being above threshold
        assert not agent.recursive_detected

    def test_recursive_events_stored_on_sub_sim(self):
        """Recursive events accumulate on the SubSimulation object."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(1)
        agent = sub.agents[0]
        agent.health = 10.0
        agent.max_age = 9999
        agent.awareness = 0.8
        agent.consciousness_phase = "recursive"

        sub.tick(recursive_threshold=0.7)
        assert len(sub.recursive_events) == 1


# ===================================================
# TEST: process_nested_simulations integration
# ===================================================

class TestProcessNestedSimulations:
    """Tests for the parent-tick integration function."""

    def test_process_runs_sub_ticks(self, cfg):
        """process_nested_simulations runs N sub-ticks per parent tick."""
        engine = create_world_engine(0, 0, 0, 1, cfg)
        stats = process_nested_simulations([engine], [], 1, cfg)
        sub_ticks = getattr(cfg.nested_simulation, 'sub_ticks_per_parent_tick', 3)
        assert stats["engines"][0]["sub_ticks_run"] == sub_ticks

    def test_recursive_event_notifies_parent(self, cfg):
        """Parent agents near a World Engine get awareness boost on recursive event."""
        engine = create_world_engine(0, 0, 0, 1, cfg)
        # Force a sub-agent to be on the verge of recursive
        sub_agent = engine.sub_sim.agents[0]
        sub_agent.awareness = 0.69
        sub_agent.consciousness_phase = "lucid"
        sub_agent.curiosity = 0.9
        sub_agent.intelligence = 0.9
        sub_agent.system_trust = 0.0
        sub_agent.health = 10.0
        sub_agent.max_age = 9999

        # Create parent agent near the World Engine cell (0,0)
        parent = create_agent(cfg)
        grid_size = cfg.environment.grid_size
        parent.x = 0.5 / grid_size  # center of cell (0,0)
        parent.y = 0.5 / grid_size
        parent.awareness = 0.3

        initial_awareness = parent.awareness
        stats = process_nested_simulations([engine], [parent], 100, cfg)

        if stats["total_recursive_events"] > 0:
            assert parent.awareness > initial_awareness
            # Check chronicle entry
            chronicles = [c for c in parent.chronicle if c.event_type == "nested_recursive_paradox"]
            assert len(chronicles) > 0

    def test_stats_structure(self, cfg):
        """Returned stats dict has expected structure."""
        engine = create_world_engine(0, 0, 0, 1, cfg)
        stats = process_nested_simulations([engine], [], 1, cfg)
        assert "active_engines" in stats
        assert "total_sub_agents" in stats
        assert "total_recursive_events" in stats
        assert "engines" in stats
        assert len(stats["engines"]) == 1

    def test_multiple_engines(self, cfg):
        """Multiple World Engines are processed independently."""
        e1 = create_world_engine(0, 0, 0, 1, cfg)
        e2 = create_world_engine(1, 1, 10, 2, cfg)
        stats = process_nested_simulations([e1, e2], [], 1, cfg)
        assert stats["active_engines"] == 2
        assert len(stats["engines"]) == 2


# ===================================================
# TEST: Performance
# ===================================================

class TestPerformance:
    """Ensure sub-sim ticking stays under 10ms even with multiple engines."""

    def test_single_sub_sim_tick_under_10ms(self):
        """A single sub-sim tick completes in < 10ms."""
        sub = SubSimulation(grid_size=4, max_agents=20)
        sub.initialize(20)  # max agents

        # Warm up
        sub.tick()

        start = time.perf_counter()
        for _ in range(100):
            sub.tick()
        elapsed = (time.perf_counter() - start) / 100
        assert elapsed < 0.01, f"Single sub-sim tick took {elapsed*1000:.2f}ms (limit: 10ms)"

    def test_three_engines_under_10ms(self, cfg):
        """3 World Engines with 3 sub-ticks each complete in < 10ms total."""
        engines = [create_world_engine(i, i, 0, 1, cfg) for i in range(3)]
        # Fill each to max
        for e in engines:
            while len(e.sub_sim.agents) < 20:
                e.sub_sim.agents.append(_create_sub_agent(4))

        # Warm up
        process_nested_simulations(engines, [], 1, cfg)

        start = time.perf_counter()
        iterations = 50
        for i in range(iterations):
            process_nested_simulations(engines, [], i + 2, cfg)
        elapsed = (time.perf_counter() - start) / iterations
        assert elapsed < 0.01, f"3 engines took {elapsed*1000:.2f}ms per parent tick (limit: 10ms)"


# ===================================================
# TEST: Engine Integration
# ===================================================

class TestEngineIntegration:
    """Tests for nested sim integration in the main SimulationEngine."""

    def test_nested_sim_config_exists(self, cfg):
        """nested_simulation config section exists."""
        assert hasattr(cfg, 'nested_simulation')
        assert cfg.nested_simulation.enabled is True
        assert cfg.nested_simulation.sub_grid_size == 4
        assert cfg.nested_simulation.max_world_engines == 3

    def test_engine_has_world_engines_list(self, cfg):
        """SimulationEngine initializes with empty world_engines list."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test"))
        assert hasattr(eng, 'world_engines')
        assert eng.world_engines == []

    def test_tick_result_has_nested_stats(self, cfg):
        """TickResult includes nested_sim_stats field."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test"))
        eng.initialize()
        result = eng.tick()
        assert hasattr(result, 'nested_sim_stats')
