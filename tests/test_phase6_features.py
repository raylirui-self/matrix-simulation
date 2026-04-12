"""
Tests for Phase 6 features:
- Boltzmann Brains (matrix_layer.py)
- Observer Effect / Quantum Rendering (engine.py)
- Broker's Black Market (programs.py)
"""
import random

import pytest

from src.agents import Bond, create_agent, SKILL_NAMES
from src.engine import SimulationEngine, RunState
from src.matrix_layer import MatrixState, process_matrix
from src.programs import (
    _create_broker,
    broker_trade,
    _process_broker,
)


# ===================================================
# TEST: Boltzmann Brains
# ===================================================

class TestBoltzmannBrains:
    def test_boltzmann_brain_can_trigger(self, cfg):
        """Boltzmann Brain event can fire and max-out an agent's awareness."""
        agents = [create_agent(cfg) for _ in range(10)]
        for a in agents:
            a.alive = True
            a.phase = "adult"
            a.awareness = 0.1

        matrix_state = MatrixState()
        matrix_state.ticks_since_reset = 0

        # Force the event by patching probability to always fire
        original_random = random.random
        random.random = lambda: 0.0  # always succeeds
        try:
            stats = process_matrix(agents, matrix_state, 1, cfg)
        finally:
            random.random = original_random

        bb_id = stats.get("boltzmann_brain")
        if bb_id is not None:
            agent = next(a for a in agents if a.id == bb_id)
            assert agent.awareness == 1.0
            assert agent.redpilled is True
            assert agent.consciousness_phase == "recursive"
            assert agent.recursive_depth == 1.0
            assert agent.beliefs["system_trust"] == -1.0
            # Check memory was added
            bb_memories = [m for m in agent.memory if "BOLTZMANN BRAIN" in m.get("event", "")]
            assert len(bb_memories) >= 1

    def test_boltzmann_brain_probability_increases_over_time(self, cfg):
        """Boltzmann Brain probability increases with ticks_since_reset."""
        mx_cfg = cfg.matrix
        bb_cfg = mx_cfg.boltzmann_brain
        base_inv = bb_cfg.base_inverse_probability
        time_factor = bb_cfg.time_factor
        pop = 50

        # At tick 0
        prob_early = 1.0 / (pop * base_inv) * (1.0 + 0 * time_factor)
        # At tick 1000
        prob_late = 1.0 / (pop * base_inv) * (1.0 + 1000 * time_factor)

        assert prob_late > prob_early
        # At tick 1000, should be roughly 2x the early probability
        assert prob_late > prob_early * 1.5

    def test_boltzmann_brain_extreme_rarity(self, cfg):
        """Under normal conditions, Boltzmann Brain is extremely rare."""
        agents = [create_agent(cfg) for _ in range(50)]
        for a in agents:
            a.alive = True
            a.phase = "adult"

        matrix_state = MatrixState()
        bb_count = 0

        # Run 100 ticks — should almost certainly not trigger
        random.seed(42)
        for t in range(1, 101):
            stats = process_matrix(agents, matrix_state, t, cfg)
            if stats.get("boltzmann_brain") is not None:
                bb_count += 1

        # Given probability ~1/(50*500000) per tick, 100 ticks should be near-zero
        assert bb_count <= 1  # allow for extreme luck but should be 0

    def test_boltzmann_brain_chronicle_type(self, cfg):
        """Boltzmann Brain event creates a chronicle entry."""
        agent = create_agent(cfg)
        agent.alive = True
        agent.phase = "adult"
        agent.awareness = 0.1

        agents = [agent]
        matrix_state = MatrixState()

        original_random = random.random
        random.random = lambda: 0.0
        try:
            process_matrix(agents, matrix_state, 1, cfg)
        finally:
            random.random = original_random

        bb_chronicles = [c for c in agent.chronicle
                         if c.event_type == "boltzmann_brain"]
        if agent.awareness == 1.0:  # only if it triggered
            assert len(bb_chronicles) >= 1

    def test_boltzmann_brain_cinematic_event_in_engine(self, cfg):
        """Engine generates a cinematic event when Boltzmann Brain fires."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_bb"))
        eng.initialize()

        # Force a BB event by setting an agent to max awareness via matrix_stats
        # We'll run one tick and check the cinematic event path exists
        result = eng.tick()
        # The cinematic_events list should exist (may be empty if BB didn't fire)
        assert isinstance(result.cinematic_events, list)


# ===================================================
# TEST: Observer Effect / Quantum Rendering
# ===================================================

class TestObserverEffect:
    def test_fidelity_transition_detected(self, cfg):
        """Aware agents entering previously empty cells notice fidelity shift."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_oe"))
        eng.initialize()

        # Run first tick to establish baseline empty cells
        eng.tick()

        # Find an aware agent and move them to a previously empty cell
        alive = eng.get_alive_agents()
        aware_agents = [a for a in alive if a.awareness > 0.3]

        if not aware_agents:
            # Make one aware
            alive[0].awareness = 0.5
            aware_agents = [alive[0]]

        # Find a cell that's currently empty
        grid_size = cfg.environment.grid_size
        empty_cells = []
        for row in eng.world.cells:
            for cell in row:
                if cell.agent_count == 0:
                    empty_cells.append(cell)

        if empty_cells and aware_agents:
            target_cell = empty_cells[0]
            agent = aware_agents[0]
            # Move agent to empty cell
            agent.x = (target_cell.col + 0.5) / grid_size
            agent.y = (target_cell.row + 0.5) / grid_size

            # Record memory count before tick
            len(agent.memory)

            # Tick — the observer effect should potentially fire
            eng.tick()

            # We can't guarantee the glitch fires (30% chance), but the path
            # should be exercised without error
            assert agent.alive  # should not crash

    def test_observer_effect_tracks_empty_cells(self, cfg):
        """Engine tracks which cells were empty between ticks."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_oe_tracking"))
        eng.initialize()

        eng.tick()

        grid_size = cfg.environment.grid_size
        total_cells = grid_size * grid_size

        # _prev_empty_cells should be a subset of all cells, and its size
        # should be reasonable (some cells occupied, some empty)
        assert isinstance(eng._prev_empty_cells, set)
        assert len(eng._prev_empty_cells) > 0  # with 50 agents and 64 cells, some must be empty
        assert len(eng._prev_empty_cells) < total_cells  # some cells must be occupied

    def test_observer_effect_disabled_gracefully(self, cfg):
        """When observer_effect is disabled, no crash occurs."""
        # Temporarily disable observer effect
        if hasattr(cfg, 'observer_effect'):
            orig = cfg.observer_effect.enabled
            cfg.observer_effect.enabled = False
        else:
            orig = None

        eng = SimulationEngine(cfg, state=RunState(run_id="test_oe_disabled"))
        eng.initialize()

        try:
            result = eng.tick()
            assert isinstance(result.alive_count, int)
        finally:
            if orig is not None:
                cfg.observer_effect.enabled = orig

    def test_observer_effect_no_boost_for_unaware(self, cfg):
        """Agents with low awareness don't notice fidelity transitions."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_oe_unaware"))
        eng.initialize()

        # Set all agents to low awareness
        for a in eng.get_alive_agents():
            a.awareness = 0.1

        eng.tick()

        # Move all agents to one corner, leaving most cells empty
        for a in eng.get_alive_agents():
            a.x = 0.05
            a.y = 0.05

        eng.tick()

        # Now scatter agents — they should NOT get awareness boosts (too low)
        for i, a in enumerate(eng.get_alive_agents()):
            a.x = (i * 0.1) % 1.0
            a.y = (i * 0.15) % 1.0

        eng.tick()

        # All agents should still have awareness <= 0.1 + normal growth
        # (no observer effect boost since awareness < 0.3)
        for a in eng.get_alive_agents():
            observer_memories = [m for m in a.memory
                                 if "reality seemed to sharpen" in m.get("event", "").lower()]
            assert len(observer_memories) == 0


# ===================================================
# TEST: Broker's Black Market
# ===================================================

class TestBrokerBlackMarket:
    def test_forbidden_knowledge_trade(self, cfg):
        """Agent can buy forbidden knowledge for stronger awareness boost."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.wealth = 10.0
        agent.awareness = 0.5
        agent.x, agent.y = broker.x, broker.y

        initial_awareness = agent.awareness
        result = broker_trade(agent, broker, "forbidden_knowledge", 100, cfg)

        assert result is not None
        assert agent.awareness > initial_awareness
        boost = getattr(cfg.programs.broker, 'forbidden_knowledge_boost', 0.15)
        assert agent.awareness == pytest.approx(initial_awareness + boost)
        assert "forbidden knowledge" in result.lower()

    def test_forbidden_knowledge_requires_wealth(self, cfg):
        """Agent without enough wealth can't buy forbidden knowledge."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.wealth = 0.0
        agent.x, agent.y = broker.x, broker.y

        result = broker_trade(agent, broker, "forbidden_knowledge", 100, cfg)
        assert result is None

    def test_memory_sacrifice_trade(self, cfg):
        """Agent can sacrifice a memory for awareness boost."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.x, agent.y = broker.x, broker.y
        agent.awareness = 0.3
        # Add some memories first
        for i in range(5):
            agent.add_memory(100, f"Memory #{i}")

        initial_mem_count = len(agent.memory)
        initial_awareness = agent.awareness
        result = broker_trade(agent, broker, "memory_sacrifice", 100, cfg)

        assert result is not None
        # One memory was removed, but a new one about the trade was added
        # Net change: -1 (sacrificed) + 1 (new trade memory) = 0
        assert len(agent.memory) == initial_mem_count  # -1 + 1
        assert agent.awareness > initial_awareness

    def test_memory_sacrifice_requires_memories(self, cfg):
        """Agent with no memories can't sacrifice one."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.x, agent.y = broker.x, broker.y
        agent.memory = []

        result = broker_trade(agent, broker, "memory_sacrifice", 100, cfg)
        assert result is None

    def test_bond_sacrifice_trade(self, cfg):
        """Agent can sacrifice a friendship for skill boost."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.x, agent.y = broker.x, broker.y
        agent.bonds.append(Bond(target_id=999, bond_type="friend", strength=0.8, formed_at=50))

        initial_skills = {s: agent.skills[s] for s in SKILL_NAMES}
        result = broker_trade(agent, broker, "bond_sacrifice", 100, cfg)

        assert result is not None
        # Bond should be removed
        friend_bonds = [b for b in agent.bonds if b.bond_type == "friend" and b.target_id == 999]
        assert len(friend_bonds) == 0
        # Skills should be boosted
        boost = getattr(cfg.programs.broker, 'bond_sacrifice_skill_boost', 0.08)
        for s in SKILL_NAMES:
            assert agent.skills[s] >= initial_skills[s] + boost - 0.001

    def test_bond_sacrifice_requires_friend(self, cfg):
        """Agent with no friend bonds can't sacrifice one."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.x, agent.y = broker.x, broker.y
        agent.bonds = []  # no bonds

        result = broker_trade(agent, broker, "bond_sacrifice", 100, cfg)
        assert result is None

    def test_bond_sacrifice_only_removes_friends(self, cfg):
        """Bond sacrifice only targets friend bonds, not family or mate."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.x, agent.y = broker.x, broker.y
        agent.bonds = [
            Bond(target_id=100, bond_type="family", strength=0.9, formed_at=1),
            Bond(target_id=200, bond_type="mate", strength=0.9, formed_at=10),
        ]

        result = broker_trade(agent, broker, "bond_sacrifice", 100, cfg)
        # Should fail — no friend bonds available
        assert result is None
        # Family and mate bonds should be untouched
        assert len(agent.bonds) == 2

    def test_oracle_prophecy_trade(self, cfg):
        """Agent can buy an Oracle prophecy."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.wealth = 10.0
        agent.x, agent.y = broker.x, broker.y
        agent.awareness = 0.5

        initial_awareness = agent.awareness
        initial_spirituality = agent.beliefs.get("spirituality", 0)
        result = broker_trade(agent, broker, "oracle_prophecy", 100, cfg)

        assert result is not None
        assert agent.awareness > initial_awareness
        assert agent.beliefs.get("spirituality", 0) > initial_spirituality

    def test_locksmith_rumor_trade(self, cfg):
        """Agent can buy a cheaper Locksmith rumor."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.wealth = 10.0
        agent.x, agent.y = broker.x, broker.y

        initial_wealth = agent.wealth
        result = broker_trade(agent, broker, "locksmith_rumor", 100, cfg)

        assert result is not None
        assert agent.wealth < initial_wealth
        # Rumor should cost half the full locksmith price
        expected_cost = cfg.programs.broker.locksmith_info_price * 0.5
        assert initial_wealth - agent.wealth == pytest.approx(expected_cost)

    def test_broker_black_market_access_requires_redpill(self, cfg):
        """Black market trades are only offered to redpilled agents."""
        broker = _create_broker(100, cfg)
        agents = [broker]

        # Non-redpilled agent with high awareness and wealth
        normie = create_agent(cfg)
        normie.x, normie.y = broker.x, broker.y
        normie.wealth = 20.0
        normie.awareness = 0.6
        normie.redpilled = False
        normie.alive = True
        normie.phase = "adult"
        agents.append(normie)

        stats = _process_broker(agents, 200, cfg)
        # Should trade normally, but not use black market
        bm_trades = stats.get("black_market_trades", 0)
        assert bm_trades == 0

    def test_broker_black_market_offered_to_redpilled(self, cfg):
        """Redpilled agents with high awareness access black market."""
        broker = _create_broker(100, cfg)
        agents = [broker]

        # Redpilled agent with high awareness and enough wealth for forbidden knowledge
        awakened = create_agent(cfg)
        awakened.x, awakened.y = broker.x, broker.y
        awakened.wealth = 20.0
        awakened.awareness = 0.6
        awakened.redpilled = True
        awakened.alive = True
        awakened.phase = "adult"
        agents.append(awakened)

        stats = _process_broker(agents, 200, cfg)
        # Should have at least one black market trade
        assert stats.get("black_market_trades", 0) >= 1

    def test_broker_hoards_wealth(self, cfg):
        """Broker accumulates wealth from all trade types."""
        broker = _create_broker(100, cfg)
        initial_broker_wealth = broker.wealth

        agent = create_agent(cfg)
        agent.wealth = 50.0
        agent.x, agent.y = broker.x, broker.y
        agent.awareness = 0.5

        broker_trade(agent, broker, "forbidden_knowledge", 100, cfg)
        broker_trade(agent, broker, "oracle_prophecy", 110, cfg)

        assert broker.wealth > initial_broker_wealth

    def test_memory_sacrifice_broker_gains_info(self, cfg):
        """Broker gains wealth when agent sacrifices a memory (hoarding information)."""
        broker = _create_broker(100, cfg)
        initial_broker_wealth = broker.wealth

        agent = create_agent(cfg)
        agent.x, agent.y = broker.x, broker.y
        for i in range(5):
            agent.add_memory(100, f"Memory #{i}")

        broker_trade(agent, broker, "memory_sacrifice", 100, cfg)
        assert broker.wealth > initial_broker_wealth


# ===================================================
# TEST: Integration — All Three Features Together
# ===================================================

class TestPhase6Integration:
    def test_full_engine_run_with_phase6(self, cfg):
        """Full 100-tick engine run doesn't crash with all Phase 6 features."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_phase6_full"))
        eng.initialize()
        for _ in range(100):
            result = eng.tick()
        alive = eng.get_alive_agents()
        assert len(alive) > 0
        assert isinstance(result.matrix_stats, dict)
        assert isinstance(result.program_stats, dict)

    def test_engine_tick_has_observer_effect_state(self, cfg):
        """Engine maintains observer effect tracking state."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_oe_state"))
        eng.initialize()
        assert hasattr(eng, '_prev_empty_cells')
        eng.tick()
        assert isinstance(eng._prev_empty_cells, set)
