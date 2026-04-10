"""
Tests for Phase 2 Cinematic & Narrative features:
1. Cinematic event system — triggering conditions
2. Agent chronicles — structured life event accumulation
3. Obituary generation — LLM fallback
"""
import random

import pytest

from src.agents import (
    Agent, Bond, Traits, ChronicleEntry, create_agent, create_offspring,
    SKILL_NAMES, EMOTION_NAMES, BELIEF_AXES, CHRONICLE_TYPES,
)
from src.config_loader import SimConfig
from src.engine import SimulationEngine, RunState, TickResult
from src.matrix_layer import MatrixState, process_matrix
from src.narrator import Narrator, _fallback_obituary, _build_obituary_prompt


# ===================================================
# TEST: ChronicleEntry model
# ===================================================

class TestChronicleEntry:
    def test_chronicle_entry_creation(self):
        """ChronicleEntry can be created with all fields."""
        entry = ChronicleEntry(
            tick=10, event_type="born",
            description="Born into the simulation",
            details={"parent_a_id": 1, "parent_b_id": 2},
        )
        assert entry.tick == 10
        assert entry.event_type == "born"
        assert entry.details["parent_a_id"] == 1

    def test_chronicle_entry_serialization(self):
        """ChronicleEntry survives to_dict/from_dict roundtrip."""
        entry = ChronicleEntry(
            tick=42, event_type="red_pill",
            description="Took the red pill",
            details={"awareness_before": 0.7},
        )
        d = entry.to_dict()
        restored = ChronicleEntry.from_dict(d)
        assert restored.tick == 42
        assert restored.event_type == "red_pill"
        assert restored.description == "Took the red pill"
        assert restored.details["awareness_before"] == 0.7

    def test_chronicle_types_defined(self):
        """CHRONICLE_TYPES list has expected entries."""
        assert "born" in CHRONICLE_TYPES
        assert "death" in CHRONICLE_TYPES
        assert "red_pill" in CHRONICLE_TYPES
        assert "first_friend" in CHRONICLE_TYPES
        assert "faction_join" in CHRONICLE_TYPES
        assert "became_anomaly" in CHRONICLE_TYPES


# ===================================================
# TEST: Agent chronicle integration
# ===================================================

class TestAgentChronicle:
    def test_agent_has_chronicle(self, cfg):
        """Agent has chronicle list attribute."""
        agent = create_agent(cfg)
        assert hasattr(agent, 'chronicle')
        assert isinstance(agent.chronicle, list)

    def test_agent_born_chronicle(self, cfg):
        """create_agent adds a 'born' chronicle entry."""
        agent = create_agent(cfg)
        born_entries = [c for c in agent.chronicle if c.event_type == "born"]
        assert len(born_entries) == 1
        assert "simulation" in born_entries[0].description.lower() or "emerged" in born_entries[0].description.lower()

    def test_offspring_born_chronicle(self, cfg):
        """create_offspring adds a 'born' chronicle entry with parent details."""
        parent_a = create_agent(cfg)
        parent_a.phase = "adult"
        parent_a.age = 30
        parent_b = create_agent(cfg)
        parent_b.phase = "adult"
        parent_b.age = 30
        parent_b.sex = "M" if parent_a.sex == "F" else "F"

        child = create_offspring(parent_a, parent_b, tick=50)
        born_entries = [c for c in child.chronicle if c.event_type == "born"]
        assert len(born_entries) == 1
        assert born_entries[0].details.get("parent_a_id") == parent_a.id
        assert born_entries[0].details.get("parent_b_id") == parent_b.id

    def test_add_chronicle_method(self, cfg):
        """Agent.add_chronicle adds entries correctly."""
        agent = create_agent(cfg)
        initial_count = len(agent.chronicle)
        agent.add_chronicle(100, "first_combat", "First blood",
                            target_id=99)
        assert len(agent.chronicle) == initial_count + 1
        last = agent.chronicle[-1]
        assert last.event_type == "first_combat"
        assert last.tick == 100
        assert last.details["target_id"] == 99

    def test_chronicle_serialization_roundtrip(self, cfg):
        """Agent with chronicle survives to_dict/from_dict."""
        agent = create_agent(cfg)
        agent.add_chronicle(5, "first_friend", "Made a friend", target_id=42)
        agent.add_chronicle(20, "red_pill", "Woke up")
        agent.add_chronicle(30, "death", "Died of combat", cause="combat")

        d = agent.to_dict()
        assert "chronicle" in d
        assert len(d["chronicle"]) == len(agent.chronicle)

        restored = Agent.from_dict(d)
        assert len(restored.chronicle) == len(agent.chronicle)
        # Index 0 is "born" from create_agent, then our 3 additions
        types = [c.event_type for c in restored.chronicle]
        assert "first_friend" in types
        assert "red_pill" in types
        assert "death" in types
        death_entry = next(c for c in restored.chronicle if c.event_type == "death")
        assert death_entry.details["cause"] == "combat"


# ===================================================
# TEST: Chronicle accumulation across systems
# ===================================================

class TestChronicleAccumulation:
    def test_death_chronicle_in_engine(self, cfg):
        """Engine adds death chronicle entry when agent dies."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_chronicle_death"))
        eng.initialize()
        # Force an agent to die
        agent = eng.agents[0]
        agent.health = 0.01
        agent.age = agent.traits.max_age  # will die of old age

        eng.tick()

        if not agent.alive:
            death_entries = [c for c in agent.chronicle if c.event_type == "death"]
            assert len(death_entries) == 1
            assert "cause" in death_entries[0].details

    def test_chronicle_grows_over_ticks(self, cfg):
        """Running multiple ticks accumulates chronicle entries across systems."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_chronicle_growth"))
        eng.initialize()

        # All agents start with at least a 'born' entry
        for a in eng.agents:
            assert any(c.event_type == "born" for c in a.chronicle)

        # Run 30 ticks — some chronicle entries should accumulate
        for _ in range(30):
            eng.tick()

        # At least some agents should have more than just the birth entry
        agents_with_multiple = [
            a for a in eng.agents
            if len(a.chronicle) > 1
        ]
        # With 30 ticks on default config, at least some agents should have
        # accumulated events (friends, factions, breakthroughs, etc.)
        # Don't require a specific count — just that the system is working
        total_entries = sum(len(a.chronicle) for a in eng.agents)
        assert total_entries > len(eng.agents), \
            f"Expected chronicle growth: {total_entries} entries for {len(eng.agents)} agents"

    def test_faction_join_chronicle(self, cfg):
        """Faction join creates chronicle entry in beliefs system."""
        from src.beliefs import process_beliefs, Faction

        agents = []
        for _ in range(10):
            a = create_agent(cfg)
            a.alive = True
            a.phase = "adult"
            a.age = 25
            # Cluster beliefs so a faction forms
            a.beliefs = {
                "individualism": 0.8,
                "tradition": 0.7,
                "system_trust": 0.5,
                "spirituality": 0.3,
            }
            a.x = 0.5 + random.uniform(-0.05, 0.05)
            a.y = 0.5 + random.uniform(-0.05, 0.05)
            agents.append(a)

        factions = []
        # Run enough ticks for factions to form
        for tick in range(1, 50):
            process_beliefs(agents, factions, tick, cfg)

        # Check if any agent got a faction_join chronicle
        faction_joins = [
            c for a in agents for c in a.chronicle
            if c.event_type == "faction_join"
        ]
        if factions:
            assert len(faction_joins) > 0, \
                "Expected faction_join chronicle entries when factions formed"

    def test_first_combat_chronicle(self, cfg):
        """First combat creates chronicle entry in conflict system."""
        from src.conflict import process_conflict
        from src.world import ResourceGrid

        agents = []
        # Create very aggressive agents at exact same position with enemy bonds
        for _ in range(6):
            a = create_agent(cfg)
            a.alive = True
            a.phase = "adult"
            a.age = 25
            a.traits.aggression = 0.99
            a.emotions["anger"] = 0.9
            a.x = 0.5
            a.y = 0.5
            agents.append(a)

        # Add enemy bonds to ensure combat triggers
        for i in range(len(agents)):
            for j in range(len(agents)):
                if i != j:
                    agents[i].add_bond(Bond(agents[j].id, "enemy", 0.8, 0))

        world = ResourceGrid(cfg)
        for tick_num in range(1, 50):
            process_conflict(agents, [], [], tick_num, cfg, world)

        combat_chronicles = [
            c for a in agents for c in a.chronicle
            if c.event_type == "first_combat"
        ]
        # With highly aggressive enemies at same position, combat must occur
        assert len(combat_chronicles) > 0, "Expected first_combat chronicle entries"


# ===================================================
# TEST: Cinematic event system
# ===================================================

class TestCinematicEvents:
    def test_tick_result_has_cinematic_events(self, cfg):
        """TickResult includes cinematic_events field."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_cinematic"))
        eng.initialize()
        result = eng.tick()
        assert hasattr(result, 'cinematic_events')
        assert isinstance(result.cinematic_events, list)

    def test_anomaly_emergence_cinematic(self, cfg):
        """Anomaly emergence triggers a cinematic event."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_cine_anomaly"))
        eng.initialize()

        # Force an agent to become the Anomaly
        agent = eng.agents[0]
        agent.awareness = 0.95
        agent.redpilled = True
        agent.alive = True
        # Ensure no previous anomaly
        eng.matrix_state.anomaly_id = None

        result = eng.tick()

        # Check if anomaly was designated and cinematic fired
        if eng.matrix_state.anomaly_id is not None:
            anomaly_events = [
                e for e in result.cinematic_events
                if e["type"] == "anomaly_emergence"
            ]
            assert len(anomaly_events) == 1
            assert "THE ONE" in anomaly_events[0]["title"]
            assert anomaly_events[0]["agent_id"] == eng.matrix_state.anomaly_id

    def test_cycle_reset_cinematic(self, cfg):
        """Cycle reset triggers a cinematic event."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_cine_reset"))
        eng.initialize()

        # Force a cycle reset by setting core_choice (triggers reset in check_cycle_reset)
        eng.matrix_state.core_choice = "reset"
        eng.matrix_state.core_choice_outcome = "status_quo"
        prev_cycle = eng.matrix_state.cycle_number

        result = eng.tick()

        reset_events = [
            e for e in result.cinematic_events
            if e["type"] == "cycle_reset"
        ]
        assert len(reset_events) == 1
        assert "RESET" in reset_events[0]["title"]

    def test_enforcer_swarm_cinematic(self, cfg):
        """Enforcer swarm reaching critical mass triggers a cinematic event."""
        from src.programs import _create_enforcer

        eng = SimulationEngine(cfg, state=RunState(run_id="test_cine_enforcer"))
        eng.initialize()

        # Calculate the threshold
        max_copies = cfg.programs.enforcer.max_copies
        threshold = max(5, max_copies // 2)

        # Add enforcers well above threshold in one go (to ensure they survive)
        # Place them far from other agents to avoid combat deaths
        for i in range(threshold + 2):
            e = _create_enforcer(0.02, 0.02, 1, cfg)
            e.health = 1.0
            eng.agents.append(e)

        result = eng.tick()
        # The prev count was 0 (before adding), now it's above threshold
        swarm_events = [e for e in result.cinematic_events if e["type"] == "enforcer_swarm"]
        assert len(swarm_events) == 1
        assert "ENFORCER" in swarm_events[0]["title"]

    def test_no_cinematic_on_normal_tick(self, cfg):
        """Normal ticks don't generate cinematic events."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_no_cinematic"))
        eng.initialize()
        result = eng.tick()
        # On a normal first tick, no cinematic events should fire
        assert len(result.cinematic_events) == 0


# ===================================================
# TEST: Obituary generation
# ===================================================

class TestObituaryGeneration:
    def test_fallback_obituary_basic(self, cfg):
        """Fallback obituary generates text for a dead agent."""
        agent = create_agent(cfg)
        agent.alive = False
        agent.age = 55
        agent.death_cause = "old_age"

        text = _fallback_obituary(agent)
        assert isinstance(text, str)
        assert len(text) > 20
        assert f"#{agent.id}" in text
        assert "old_age" in text

    def test_fallback_obituary_with_chronicle(self, cfg):
        """Fallback obituary incorporates chronicle highlights."""
        agent = create_agent(cfg)
        agent.alive = False
        agent.age = 40
        agent.death_cause = "combat"
        agent.add_chronicle(10, "red_pill", "Took the red pill")
        agent.add_chronicle(20, "faction_join", "Joined faction",
                            faction_name="The Seekers")
        agent.add_chronicle(30, "first_combat", "First blood", target_id=99)

        text = _fallback_obituary(agent)
        assert "combat" in text
        assert "veil" in text or "red" in text.lower() or "simulation" in text

    def test_fallback_obituary_anomaly(self, cfg):
        """Fallback obituary highlights Anomaly status."""
        agent = create_agent(cfg)
        agent.alive = False
        agent.age = 60
        agent.death_cause = "starvation"
        agent.is_anomaly = True
        agent.redpilled = True
        agent.add_chronicle(5, "became_anomaly", "Became The One")

        text = _fallback_obituary(agent)
        assert "Anomaly" in text or "One" in text

    def test_fallback_obituary_no_chronicle(self, cfg):
        """Fallback obituary works for agents with empty chronicle."""
        agent = create_agent(cfg)
        agent.alive = False
        agent.age = 20
        agent.death_cause = "starvation"
        agent.chronicle = []  # clear

        text = _fallback_obituary(agent)
        assert isinstance(text, str)
        assert len(text) > 10

    def test_build_obituary_prompt(self, cfg):
        """Obituary prompt includes chronicle and key agent data."""
        agent = create_agent(cfg)
        agent.alive = False
        agent.age = 35
        agent.death_cause = "combat"
        agent.redpilled = True
        agent.add_chronicle(10, "born", "Born")
        agent.add_chronicle(20, "red_pill", "Woke up")
        agent.add_memory(30, "Died")

        prompt = _build_obituary_prompt(agent)
        assert f"#{agent.id}" in prompt
        assert "combat" in prompt
        assert "red_pill" in prompt
        assert "redpilled" in prompt
        assert "Chronicle:" in prompt

    def test_narrator_generate_obituary_fallback(self, cfg):
        """Narrator.generate_obituary falls back gracefully when LLM unavailable."""
        narrator = Narrator(enabled=False)
        agent = create_agent(cfg)
        agent.alive = False
        agent.age = 45
        agent.death_cause = "old_age"

        text = narrator.generate_obituary(agent)
        assert isinstance(text, str)
        assert len(text) > 10
        assert f"#{agent.id}" in text

    def test_narrator_generate_obituary_enabled_no_provider(self, cfg):
        """Narrator with enabled=True but no provider falls back."""
        narrator = Narrator(enabled=True, providers=[])
        agent = create_agent(cfg)
        agent.alive = False
        agent.age = 30
        agent.death_cause = "starvation"

        text = narrator.generate_obituary(agent)
        assert isinstance(text, str)
        assert len(text) > 10


# ===================================================
# TEST: Full integration
# ===================================================

class TestFullIntegration:
    def test_50_tick_run_no_crash(self, cfg):
        """50-tick engine run with chronicle + cinematic doesn't crash."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_full_phase2"))
        eng.initialize()
        all_cinematics = []
        for _ in range(50):
            result = eng.tick()
            all_cinematics.extend(result.cinematic_events)

        # Verify chronicle entries exist
        total_chronicles = sum(len(a.chronicle) for a in eng.agents)
        assert total_chronicles > 0

    def test_dead_agent_has_obituary(self, cfg):
        """Dead agents after engine run can generate obituaries."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_obituary_run"))
        eng.initialize()
        for _ in range(50):
            eng.tick()

        dead = [a for a in eng.agents if not a.alive]
        if dead:
            narrator = Narrator(enabled=False)
            for agent in dead[:3]:
                text = narrator.generate_obituary(agent)
                assert isinstance(text, str)
                assert len(text) > 10
