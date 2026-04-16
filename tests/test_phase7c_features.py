"""
Tests for Phase 7C features:
- Nested simulation window data in tick payload
- Artifact details in world endpoint response
- Reincarnation events in tick payload / TickResult
- Language tree endpoint data
"""
from src.agents import create_agent
from src.nested_sim import create_world_engine, SubSimulation
from src.communication import (
    get_language_state,
    set_language_state,
    LanguageArtifact,
)
from src.world import Artifact


class TestNestedSimPayload:
    """Nested sim window data flows through the tick payload."""

    def test_world_engine_to_dict_includes_sub_sim(self, cfg):
        """WorldEngine.to_dict() exposes sub-sim state."""
        we = create_world_engine(0, 0, 10, builder_id=1, cfg=cfg)
        d = we.to_dict()
        assert "sub_sim" in d
        assert d["sub_sim"]["grid_size"] == 4
        assert d["sub_sim"]["alive_count"] > 0

    def test_sub_sim_agents_have_positions(self, cfg):
        """Sub-agents expose x, y, awareness for miniature grid rendering."""
        ss = SubSimulation(grid_size=4, max_agents=10)
        ss.initialize(initial_count=5)
        d = ss.to_dict()
        assert len(d["agents"]) == 5
        for sa in d["agents"]:
            assert "x" in sa
            assert "y" in sa
            assert "awareness" in sa

    def test_sub_sim_tracks_recursive_detected(self, cfg):
        """Sub-sim reports recursive paradox detection."""
        ss = SubSimulation(grid_size=4, max_agents=10)
        ss.initialize(initial_count=3)
        # Force a sub-agent to high awareness
        alive = ss.get_alive()
        alive[0].awareness = 0.9
        alive[0].consciousness_phase = "recursive"
        stats = ss.tick(recursive_threshold=0.7)
        assert alive[0].recursive_detected is True
        assert len(stats["recursive_events"]) > 0

    def test_tick_result_has_nested_sim_stats(self, engine):
        """TickResult includes nested_sim_stats field."""
        result = engine.tick()
        assert hasattr(result, "nested_sim_stats")


class TestArtifactDetails:
    """Artifact details are available for terrain rendering."""

    def test_artifact_to_dict_has_type_and_cycle(self):
        """Artifact.to_dict() includes type and cycle_number for frontend."""
        art = Artifact(
            artifact_id=1,
            faction_name="TestFaction",
            era_tick=50,
            cycle_number=2,
            awareness_level=0.5,
            tech_level=0.6,
            artifact_type="inscription",
        )
        d = art.to_dict()
        assert d["artifact_type"] == "inscription"
        assert d["cycle_number"] == 2
        assert d["faction_name"] == "TestFaction"

    def test_cell_artifacts_list_available(self, engine):
        """Cells store artifact objects that can be serialized."""
        # Create an artifact in a cell
        cell = engine.world.cells[0][0]
        art = Artifact(
            artifact_id=99,
            faction_name="Ancients",
            era_tick=10,
            cycle_number=1,
            awareness_level=0.3,
            tech_level=0.4,
            artifact_type="ruin",
        )
        cell.artifacts.append(art)
        assert len(cell.artifacts) == 1
        assert cell.artifacts[0].to_dict()["artifact_type"] == "ruin"


class TestReincarnationEvents:
    """Reincarnation arc data flows through TickResult."""

    def test_tick_result_has_reincarnation_events(self, engine):
        """TickResult has reincarnation_events field."""
        result = engine.tick()
        assert hasattr(result, "reincarnation_events")
        assert isinstance(result.reincarnation_events, list)

    def test_soul_capture_includes_death_position(self, engine, cfg):
        """Soul capture stores death_x/death_y for ghost trail arcs."""
        agent = create_agent(cfg)
        agent.alive = True
        agent.x = 0.3
        agent.y = 0.7
        agent.awareness = 0.5
        engine.agents.append(agent)
        engine._capture_soul(agent, tick=10)
        assert len(engine._soul_pool) > 0
        soul = engine._soul_pool[-1]
        assert soul["death_x"] == 0.3
        assert soul["death_y"] == 0.7

    def test_apply_soul_records_reincarnation_event(self, engine, cfg):
        """Applying a soul to a newborn creates a reincarnation event."""
        # Seed the soul pool
        dead = create_agent(cfg)
        dead.x = 0.2
        dead.y = 0.8
        dead.awareness = 0.1
        dead.incarnation_count = 1
        engine.agents.append(dead)
        engine._capture_soul(dead, tick=5)

        # Create newborn and apply soul
        engine._reincarnation_events.clear()
        newborn = create_agent(cfg)
        newborn.x = 0.6
        newborn.y = 0.4
        engine._apply_soul_to_newborn(newborn, tick=10)

        assert len(engine._reincarnation_events) == 1
        evt = engine._reincarnation_events[0]
        assert evt["death_x"] == 0.2
        assert evt["death_y"] == 0.8
        assert evt["birth_x"] == 0.6
        assert evt["birth_y"] == 0.4
        assert evt["incarnation_count"] == 2


class TestLanguageTreeData:
    """Language state is structured for tree visualization."""

    def test_get_language_state_returns_dict(self):
        """get_language_state() returns all fields needed for the tree."""
        state = get_language_state()
        assert "faction_concept_usage" in state
        assert "faction_dialects" in state
        assert "resistance_encryption_level" in state
        assert "sentinel_decryption_level" in state

    def test_set_and_get_language_state_roundtrips(self):
        """Setting and getting language state preserves data."""
        test_state = {
            "faction_concept_usage": {"1": {"knowledge": 5, "propaganda": 3}},
            "faction_dialects": {"1": 0.15, "2": -0.08},
            "resistance_encryption_level": 0.7,
            "sentinel_decryption_level": 0.4,
        }
        set_language_state(test_state)
        restored = get_language_state()
        assert restored["faction_dialects"]["1"] == 0.15
        assert restored["faction_dialects"]["2"] == -0.08
        assert restored["resistance_encryption_level"] == 0.7

    def test_language_artifact_to_dict(self):
        """LanguageArtifact.to_dict() includes all fields needed by the tree."""
        la = LanguageArtifact(
            id=1,
            faction_name="Old Tongue",
            faction_id=5,
            cell_row=2,
            cell_col=3,
            encoding_complexity=0.6,
            concept_count=12,
            cycle_number=2,
            created_at=100,
            contains_awareness_clues=True,
        )
        d = la.to_dict()
        assert d["faction_name"] == "Old Tongue"
        assert d["cycle_number"] == 2
        assert d["contains_awareness_clues"] is True
        assert d["concept_count"] == 12
