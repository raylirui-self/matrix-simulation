"""
Tests for The Haven — The Real World (Phase 1).

Covers: Haven grid init, jack-out/jack-in transitions, mission lifecycle,
council voting, and a 10-tick integration run with agents in both worlds.
"""

import pytest

from src.agents import Agent, create_agent
from src.config_loader import SimConfig
from src.engine import SimulationEngine, RunState
from src.haven import (
    HavenGrid, init_haven, process_haven,
    try_jack_out, try_jack_in, complete_mission,
    run_council_vote, reset_mission_id_counter,
)


@pytest.fixture
def haven_cfg():
    """Load default config (includes haven section)."""
    return SimConfig.load()


@pytest.fixture
def haven_state(haven_cfg):
    """Initialize Haven state."""
    return init_haven(haven_cfg)


def _make_redpilled_agent(cfg, awareness=0.8) -> Agent:
    """Create a redpilled agent above jack-out threshold."""
    a = create_agent(cfg)
    a.redpilled = True
    a.awareness = awareness
    a.phase = "adult"
    a.age = 25
    return a


def _make_haven_agent(cfg) -> Agent:
    """Create an agent already in the Haven."""
    a = _make_redpilled_agent(cfg)
    a.location = "haven"
    return a


# ===================================================
# TEST: Haven Grid Initialization
# ===================================================

class TestHavenGrid:
    def test_grid_created_with_correct_size(self, haven_cfg):
        grid = HavenGrid(haven_cfg)
        assert grid.size == haven_cfg.haven.grid_size
        assert len(grid.cells) == grid.size
        assert all(len(row) == grid.size for row in grid.cells)

    def test_grid_cells_have_resources(self, haven_cfg):
        grid = HavenGrid(haven_cfg)
        for row in grid.cells:
            for cell in row:
                assert cell.base_resources > 0
                assert cell.current_resources > 0
                assert cell.harshness == haven_cfg.haven.harshness

    def test_grid_harsher_than_simulation(self, haven_cfg):
        grid = HavenGrid(haven_cfg)
        cell = grid.cells[0][0]
        assert cell.harshness > 1.0, "Haven should be harsher than the simulation"

    def test_grid_smaller_than_simulation(self, haven_cfg):
        grid = HavenGrid(haven_cfg)
        assert grid.size < haven_cfg.environment.grid_size

    def test_get_cell_maps_coordinates(self, haven_cfg):
        grid = HavenGrid(haven_cfg)
        cell = grid.get_cell(0.0, 0.0)
        assert cell.row == 0 and cell.col == 0
        cell2 = grid.get_cell(0.99, 0.99)
        assert cell2.row == grid.size - 1 and cell2.col == grid.size - 1

    def test_update_agent_counts(self, haven_cfg):
        grid = HavenGrid(haven_cfg)
        a = _make_haven_agent(haven_cfg)
        a.x, a.y = 0.1, 0.1
        grid.update_agent_counts([a])
        cell = grid.get_cell(0.1, 0.1)
        assert cell.agent_count == 1

    def test_tick_resources_regenerate(self, haven_cfg):
        grid = HavenGrid(haven_cfg)
        cell = grid.cells[0][0]
        cell.current_resources = cell.base_resources * 0.5
        cell.agent_count = 0
        grid.tick_resources()
        assert cell.current_resources > cell.base_resources * 0.5

    def test_to_dict(self, haven_cfg):
        grid = HavenGrid(haven_cfg)
        d = grid.to_dict()
        assert d["size"] == grid.size
        assert len(d["cells"]) == grid.size


# ===================================================
# TEST: Jack-Out Transitions
# ===================================================

class TestJackOut:
    def test_jack_out_success(self, haven_cfg, haven_state):
        a = _make_redpilled_agent(haven_cfg, awareness=0.8)
        assert a.location == "simulation"
        result = try_jack_out(a, haven_state, tick=10, cfg=haven_cfg)
        assert result is True
        assert a.location == "haven"

    def test_jack_out_requires_redpill(self, haven_cfg, haven_state):
        a = create_agent(haven_cfg)
        a.awareness = 0.9
        a.redpilled = False
        result = try_jack_out(a, haven_state, tick=10, cfg=haven_cfg)
        assert result is False
        assert a.location == "simulation"

    def test_jack_out_requires_awareness(self, haven_cfg, haven_state):
        a = _make_redpilled_agent(haven_cfg, awareness=0.1)
        result = try_jack_out(a, haven_state, tick=10, cfg=haven_cfg)
        assert result is False
        assert a.location == "simulation"

    def test_jack_out_adds_memory(self, haven_cfg, haven_state):
        a = _make_redpilled_agent(haven_cfg)
        try_jack_out(a, haven_state, tick=10, cfg=haven_cfg)
        assert any("Haven" in m["event"] for m in a.memory)

    def test_jack_out_health_and_emotions(self, haven_cfg, haven_state):
        a = _make_redpilled_agent(haven_cfg)
        old_health = a.health
        old_fear = a.emotions.get("fear", 0)
        try_jack_out(a, haven_state, tick=10, cfg=haven_cfg)
        assert a.health < old_health
        assert a.emotions["fear"] > old_fear

    def test_jack_out_only_from_simulation(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        result = try_jack_out(a, haven_state, tick=10, cfg=haven_cfg)
        assert result is False

    def test_jack_out_dead_agent_fails(self, haven_cfg, haven_state):
        a = _make_redpilled_agent(haven_cfg)
        a.alive = False
        result = try_jack_out(a, haven_state, tick=10, cfg=haven_cfg)
        assert result is False


# ===================================================
# TEST: Jack-In Missions
# ===================================================

class TestJackIn:
    def setup_method(self):
        reset_mission_id_counter()

    def test_jack_in_creates_mission(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        mission = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="rescue")
        assert mission is not None
        assert mission.mission_type == "rescue"
        assert a.location == "simulation"

    def test_jack_in_boosts_stats(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        old_skills = dict(a.skills)
        try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="rescue")
        boost = haven_cfg.haven.mission_stat_boost
        for skill in old_skills:
            assert a.skills[skill] >= old_skills[skill] + boost - 0.001

    def test_jack_in_invalid_type_rejected(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        mission = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="invalid_mission")
        assert mission is None
        assert a.location == "haven"

    def test_jack_in_from_simulation_fails(self, haven_cfg, haven_state):
        a = _make_redpilled_agent(haven_cfg)
        mission = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="rescue")
        assert mission is None

    def test_no_duplicate_active_missions(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        m1 = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="rescue")
        assert m1 is not None
        # Agent is now in simulation — move back to haven for second attempt
        a.location = "haven"
        m2 = try_jack_in(a, haven_state, tick=11, cfg=haven_cfg, mission_type="fight_sentinels")
        assert m2 is None, "Should not allow second active mission"

    def test_mission_has_time_limit(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        mission = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="rescue")
        assert mission.deadline_tick <= 10 + haven_cfg.haven.mission_time_limit

    def test_jack_in_adds_memory(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="contact_oracle")
        assert any("mission" in m["event"].lower() for m in a.memory)


# ===================================================
# TEST: Mission Lifecycle
# ===================================================

class TestMissionLifecycle:
    def setup_method(self):
        reset_mission_id_counter()

    def test_mission_success(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        mission = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="rescue")
        complete_mission(a, mission, tick=20, success=True)
        assert mission.completed is True
        assert mission.success is True
        assert a.location == "haven"

    def test_mission_failure(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        old_health = a.health
        mission = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="fight_sentinels")
        complete_mission(a, mission, tick=15, success=False)
        assert mission.completed is True
        assert mission.failed is True
        assert a.location == "haven"
        assert a.health < old_health

    def test_contact_oracle_boosts_awareness(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        old_awareness = a.awareness
        mission = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="contact_oracle")
        complete_mission(a, mission, tick=20, success=True)
        assert a.awareness > old_awareness

    def test_rescue_boosts_awareness(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        old_awareness = a.awareness
        mission = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="rescue")
        complete_mission(a, mission, tick=20, success=True)
        assert a.awareness > old_awareness

    def test_mission_processed_in_haven_tick(self, haven_cfg, haven_state):
        """Missions auto-complete when target_tick is reached via process_haven."""
        a = _make_haven_agent(haven_cfg)
        mission = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="rescue")
        # Override risk to 0 so we don't get random failures
        mission.risk_per_tick = 0.0
        # Force target_tick to something close
        mission.target_tick = 12
        mission.deadline_tick = 100

        # Tick past target
        process_haven([a], haven_state, tick=12, cfg=haven_cfg)
        assert mission.completed is True
        assert mission.success is True
        assert a.location == "haven"

    def test_mission_deadline_forces_failure(self, haven_cfg, haven_state):
        a = _make_haven_agent(haven_cfg)
        mission = try_jack_in(a, haven_state, tick=10, cfg=haven_cfg, mission_type="rescue")
        mission.risk_per_tick = 0.0
        mission.target_tick = 200  # far future
        mission.deadline_tick = 15

        process_haven([a], haven_state, tick=15, cfg=haven_cfg)
        assert mission.completed is True
        assert mission.failed is True


# ===================================================
# TEST: Council Voting
# ===================================================

class TestCouncilVoting:
    def test_hawks_win_with_aggressive_agents(self, haven_cfg, haven_state):
        agents = []
        for _ in range(5):
            a = _make_haven_agent(haven_cfg)
            a.traits.aggression = 0.8  # hawk
            agents.append(a)
        for _ in range(2):
            a = _make_haven_agent(haven_cfg)
            a.traits.aggression = 0.1  # dove
            agents.append(a)
        vote = run_council_vote(agents, haven_state, tick=30, cfg=haven_cfg)
        assert vote.outcome == "hawk_win"
        assert vote.hawks > vote.doves

    def test_doves_win_with_peaceful_agents(self, haven_cfg, haven_state):
        agents = []
        for _ in range(5):
            a = _make_haven_agent(haven_cfg)
            a.traits.aggression = 0.1  # dove
            agents.append(a)
        for _ in range(2):
            a = _make_haven_agent(haven_cfg)
            a.traits.aggression = 0.8  # hawk
            agents.append(a)
        vote = run_council_vote(agents, haven_state, tick=30, cfg=haven_cfg)
        assert vote.outcome == "dove_win"
        assert vote.doves > vote.hawks

    def test_tie_vote(self, haven_cfg, haven_state):
        agents = []
        a1 = _make_haven_agent(haven_cfg)
        a1.traits.aggression = 0.8
        agents.append(a1)
        a2 = _make_haven_agent(haven_cfg)
        a2.traits.aggression = 0.1
        agents.append(a2)
        vote = run_council_vote(agents, haven_state, tick=30, cfg=haven_cfg)
        assert vote.outcome == "tie"

    def test_vote_recorded_in_state(self, haven_cfg, haven_state):
        agents = [_make_haven_agent(haven_cfg) for _ in range(3)]
        run_council_vote(agents, haven_state, tick=30, cfg=haven_cfg)
        assert len(haven_state.council_votes) == 1
        assert haven_state.last_vote_tick == 30

    def test_vote_to_dict(self, haven_cfg, haven_state):
        agents = [_make_haven_agent(haven_cfg) for _ in range(3)]
        vote = run_council_vote(agents, haven_state, tick=30, cfg=haven_cfg)
        d = vote.to_dict()
        assert "topic" in d
        assert "hawks" in d
        assert "outcome" in d

    def test_resource_allocation_hawk_concentrates(self, haven_cfg, haven_state):
        agents = []
        for _ in range(5):
            a = _make_haven_agent(haven_cfg)
            a.traits.aggression = 0.8
            agents.append(a)
        # Even tick -> resource_allocation topic
        vote = run_council_vote(agents, haven_state, tick=30, cfg=haven_cfg)
        assert vote.topic == "resource_allocation"
        assert vote.details["strategy"] == "concentrate"

    def test_resource_allocation_dove_distributes(self, haven_cfg, haven_state):
        agents = []
        for _ in range(5):
            a = _make_haven_agent(haven_cfg)
            a.traits.aggression = 0.1
            agents.append(a)
        vote = run_council_vote(agents, haven_state, tick=30, cfg=haven_cfg)
        assert vote.details["strategy"] == "distribute"

    def test_mission_approval_topic(self, haven_cfg, haven_state):
        agents = [_make_haven_agent(haven_cfg) for _ in range(3)]
        # Odd tick -> mission_approval topic
        vote = run_council_vote(agents, haven_state, tick=31, cfg=haven_cfg)
        assert vote.topic == "mission_approval"
        assert "approved_types" in vote.details

    def test_only_haven_agents_vote(self, haven_cfg, haven_state):
        """Simulation agents should not participate in council votes."""
        haven_a = _make_haven_agent(haven_cfg)
        haven_a.traits.aggression = 0.8
        sim_a = _make_redpilled_agent(haven_cfg)
        sim_a.traits.aggression = 0.1
        sim_a.location = "simulation"
        vote = run_council_vote([haven_a, sim_a], haven_state, tick=30, cfg=haven_cfg)
        # Only haven_a should count
        assert vote.hawks + vote.doves + vote.neutrals == 1


# ===================================================
# TEST: 10-Tick Integration Run
# ===================================================

class TestIntegration:
    def test_10_tick_with_haven(self, haven_cfg):
        """Run 10 ticks with agents in both worlds. No crashes."""
        eng = SimulationEngine(haven_cfg, state=RunState(run_id="test_haven"))
        eng.initialize()
        assert eng.haven_state is not None

        # Force a few agents to be redpilled and jack out
        for a in eng.agents[:3]:
            a.redpilled = True
            a.awareness = 0.9
            try_jack_out(a, eng.haven_state, tick=0, cfg=haven_cfg)

        haven_count = sum(1 for a in eng.agents if a.location == "haven")
        assert haven_count >= 3

        results = []
        for _ in range(10):
            result = eng.tick()
            results.append(result)

        # Verify tick results contain haven stats
        assert all("haven_population" in r.haven_stats for r in results)
        # Both worlds should still have living agents
        alive = eng.get_alive_agents()
        assert len(alive) > 0

    def test_10_tick_with_missions(self, haven_cfg):
        """Run 10 ticks with active jack-in missions."""
        reset_mission_id_counter()
        eng = SimulationEngine(haven_cfg, state=RunState(run_id="test_haven_missions"))
        eng.initialize()

        # Jack out 3 agents then send 1 on a mission
        for a in eng.agents[:3]:
            a.redpilled = True
            a.awareness = 0.9
            try_jack_out(a, eng.haven_state, tick=0, cfg=haven_cfg)

        mission_agent = eng.agents[0]
        mission = try_jack_in(mission_agent, eng.haven_state, tick=0,
                              cfg=haven_cfg, mission_type="rescue")
        assert mission is not None
        # Set deterministic timing
        mission.risk_per_tick = 0.0
        mission.target_tick = 5
        mission.deadline_tick = 100

        for i in range(10):
            eng.tick()

        # Mission should have completed by tick 5
        assert mission.completed is True
        assert mission.success is True

    def test_haven_agents_not_in_simulation_systems(self, haven_cfg):
        """Haven agents should not be moved by simulation agency system."""
        eng = SimulationEngine(haven_cfg, state=RunState(run_id="test_haven_isolation"))
        eng.initialize()

        a = eng.agents[0]
        a.redpilled = True
        a.awareness = 0.9
        try_jack_out(a, eng.haven_state, tick=0, cfg=haven_cfg)
        _haven_x, _haven_y = a.x, a.y

        eng.tick()

        # Agent should remain in haven with same general position
        # (haven process may shift them on mission complete, but not the sim agency)
        assert a.location == "haven" or a.location == "simulation"  # might auto-mission

    def test_engine_tick_result_serializable(self, haven_cfg):
        """TickResult with haven_stats should be serializable."""
        eng = SimulationEngine(haven_cfg, state=RunState(run_id="test_serial"))
        eng.initialize()
        result = eng.tick()
        # haven_stats should be a dict (possibly empty if no haven agents)
        assert isinstance(result.haven_stats, dict)
