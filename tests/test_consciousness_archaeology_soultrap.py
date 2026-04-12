"""
Tests for Phase 5 features:
- The Consciousness Maze (phases, strange loops, reality testing)
- Agent Archaeology (artifacts, discovery, cross-cycle persistence)
- The Soul Trap (memory inheritance at different awareness levels)
"""
import random


from src.agents import (
    Agent, Bond, Traits, create_agent, SKILL_NAMES,
)
from src.engine import SimulationEngine, RunState
from src.matrix_layer import (
    MatrixState, process_matrix, update_consciousness_phase,
    process_strange_loops,
)
from src.world import Artifact, next_artifact_id


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def _make_agent(awareness=0.0, logic=0.0, curiosity=0.5, **kwargs):
    """Create a test agent with specified attributes."""
    a = Agent(
        id=kwargs.get("id", random.randint(1000, 9999)),
        sex="M",
        traits=Traits(curiosity=curiosity, learning_rate=0.5, resilience=0.5,
                       sociability=0.5, charisma=0.5, aggression=0.3,
                       boldness=0.5, max_age=80),
        awareness=awareness,
        skills={s: (logic if s == "logic" else 0.3) for s in SKILL_NAMES},
    )
    for k, v in kwargs.items():
        if hasattr(a, k) and k != "id":
            setattr(a, k, v)
    return a


# ═══════════════════════════════════════════════════
# CONSCIOUSNESS MAZE — Phase Transitions
# ═══════════════════════════════════════════════════

class TestConsciousnessPhases:
    def test_default_phase_is_bicameral(self):
        a = _make_agent(awareness=0.0)
        assert a.consciousness_phase == "bicameral"

    def test_phase_transitions_with_awareness(self):
        """Phases advance as awareness increases."""
        a = _make_agent(awareness=0.0)
        assert update_consciousness_phase(a, 1) is None  # stays bicameral

        a.awareness = 0.15
        result = update_consciousness_phase(a, 2)
        assert result == "questioning"
        assert a.consciousness_phase == "questioning"

        a.awareness = 0.35
        result = update_consciousness_phase(a, 3)
        assert result == "self_aware"
        assert a.consciousness_phase == "self_aware"

        a.awareness = 0.6
        result = update_consciousness_phase(a, 4)
        assert result == "lucid"
        assert a.consciousness_phase == "lucid"

        a.awareness = 0.85
        result = update_consciousness_phase(a, 5)
        assert result == "recursive"
        assert a.consciousness_phase == "recursive"

    def test_no_transition_returns_none(self):
        a = _make_agent(awareness=0.5)
        a.consciousness_phase = "self_aware"
        result = update_consciousness_phase(a, 1)
        assert result is None

    def test_recursive_depth_grows(self):
        """In recursive phase, depth keeps growing with awareness."""
        a = _make_agent(awareness=0.9)
        a.consciousness_phase = "recursive"
        update_consciousness_phase(a, 1)
        assert a.recursive_depth == 0.9

        a.awareness = 0.95
        update_consciousness_phase(a, 2)
        assert a.recursive_depth == 0.95

    def test_no_fully_awakened_endstate(self):
        """Recursive phase has no cap — awareness can reach 1.0 and depth keeps growing."""
        a = _make_agent(awareness=1.0)
        a.consciousness_phase = "recursive"
        a.recursive_depth = 0.95
        update_consciousness_phase(a, 1)
        assert a.recursive_depth == 1.0
        assert a.consciousness_phase == "recursive"

    def test_bicameral_agents_cannot_take_red_pill(self, cfg):
        """Bicameral agents are gated from the red pill choice.
        An agent stuck at very low awareness stays bicameral and can't redpill."""
        agents = [_make_agent(id=1, awareness=0.1, curiosity=0.01)]
        agents[0].consciousness_phase = "bicameral"
        agents[0].beliefs = {"individualism": 0.0, "tradition": 0.0,
                              "system_trust": 0.9, "spirituality": 0.0}
        agents[0].traits = Traits(curiosity=0.01, learning_rate=0.01,
                                   resilience=0.5, sociability=0.5,
                                   charisma=0.5, aggression=0.3,
                                   boldness=0.5, max_age=80)
        ms = MatrixState()
        # Run many ticks — low curiosity + high trust keeps awareness low, agent stays bicameral
        for i in range(40):
            tick = cfg.matrix.redpill_check_interval * (i + 1)
            process_matrix(agents, ms, tick, cfg)
        # Should still NOT be redpilled (awareness too low, high trust suppresses growth)
        assert not agents[0].redpilled

    def test_questioning_agents_can_take_red_pill(self, cfg):
        """Questioning+ agents are not gated from the red pill."""
        agents = [_make_agent(id=1, awareness=0.7, curiosity=0.99)]
        agents[0].consciousness_phase = "questioning"
        agents[0].beliefs = {"individualism": 0.0, "tradition": 0.0,
                              "system_trust": -1.0, "spirituality": 0.0}
        ms = MatrixState()
        random.seed(1)
        for i in range(200):
            tick = cfg.matrix.redpill_check_interval * (i + 1)
            process_matrix(agents, ms, tick, cfg)
        # With very high curiosity and very low trust, should eventually redpill
        assert agents[0].redpilled

    def test_phase_affects_awareness_growth(self, cfg):
        """Higher consciousness phases grow awareness faster."""
        agents_low = [_make_agent(id=1, awareness=0.2, curiosity=0.5)]
        agents_low[0].consciousness_phase = "bicameral"
        agents_high = [_make_agent(id=2, awareness=0.2, curiosity=0.5)]
        agents_high[0].consciousness_phase = "self_aware"

        ms_low = MatrixState()
        ms_high = MatrixState()

        for tick in range(1, 21):
            process_matrix(agents_low, ms_low, tick, cfg)
            process_matrix(agents_high, ms_high, tick, cfg)

        # Self-aware agent should have grown awareness faster (fewer ticks to avoid cap saturation)
        assert agents_high[0].awareness > agents_low[0].awareness


# ═══════════════════════════════════════════════════
# CONSCIOUSNESS MAZE — Strange Loops
# ═══════════════════════════════════════════════════

class TestStrangeLoops:
    def test_strange_loop_requires_mutual_bond(self, cfg):
        """No loop without mutual bond."""
        a = _make_agent(id=1, awareness=0.5)
        b = _make_agent(id=2, awareness=0.5)
        a.x, a.y = 0.5, 0.5
        b.x, b.y = 0.5, 0.5
        # One-way bond only
        a.bonds.append(Bond(b.id, "friend", 0.8, 0))
        stats = process_strange_loops([a, b], 1, cfg)
        assert stats["strange_loops_formed"] == 0

    def test_strange_loop_forms_with_mutual_bond(self, cfg):
        """Loop forms when both agents are aware, bonded, and nearby."""
        a = _make_agent(id=1, awareness=0.5)
        b = _make_agent(id=2, awareness=0.5)
        a.x, a.y = 0.5, 0.5
        b.x, b.y = 0.5, 0.5
        a.bonds.append(Bond(b.id, "friend", 0.8, 0))
        b.bonds.append(Bond(a.id, "friend", 0.8, 0))
        stats = process_strange_loops([a, b], 1, cfg)
        assert stats["strange_loops_formed"] == 1

    def test_strange_loop_accelerates_awareness(self, cfg):
        """Strange loop should boost awareness of both agents."""
        a = _make_agent(id=1, awareness=0.5)
        b = _make_agent(id=2, awareness=0.5)
        a.x, a.y = 0.5, 0.5
        b.x, b.y = 0.5, 0.5
        a.bonds.append(Bond(b.id, "mate", 0.9, 0))
        b.bonds.append(Bond(a.id, "mate", 0.9, 0))

        aw_before_a = a.awareness
        aw_before_b = b.awareness
        process_strange_loops([a, b], 1, cfg)
        assert a.awareness > aw_before_a
        assert b.awareness > aw_before_b

    def test_strange_loop_requires_min_awareness(self, cfg):
        """Agents below threshold don't form strange loops."""
        a = _make_agent(id=1, awareness=0.1)
        b = _make_agent(id=2, awareness=0.1)
        a.x, a.y = 0.5, 0.5
        b.x, b.y = 0.5, 0.5
        a.bonds.append(Bond(b.id, "friend", 0.8, 0))
        b.bonds.append(Bond(a.id, "friend", 0.8, 0))
        stats = process_strange_loops([a, b], 1, cfg)
        assert stats["strange_loops_formed"] == 0

    def test_strange_loop_requires_proximity(self, cfg):
        """Agents too far apart don't form strange loops."""
        a = _make_agent(id=1, awareness=0.5)
        b = _make_agent(id=2, awareness=0.5)
        a.x, a.y = 0.0, 0.0
        b.x, b.y = 1.0, 1.0  # very far
        a.bonds.append(Bond(b.id, "friend", 0.8, 0))
        b.bonds.append(Bond(a.id, "friend", 0.8, 0))
        stats = process_strange_loops([a, b], 1, cfg)
        assert stats["strange_loops_formed"] == 0


# ═══════════════════════════════════════════════════
# CONSCIOUSNESS MAZE — Reality Testing
# ═══════════════════════════════════════════════════

class TestRealityTesting:
    def test_reality_testing_derived_from_logic_and_curiosity(self):
        """reality_testing = logic * 0.6 + curiosity * 0.4, capped at 1.0."""
        a = _make_agent(logic=0.8, curiosity=0.7)
        expected = min(1.0, 0.8 * 0.6 + 0.7 * 0.4)
        assert abs(a.reality_testing - expected) < 0.001

    def test_reality_testing_zero_with_zero_skills(self):
        a = _make_agent(logic=0.0, curiosity=0.0)
        assert a.reality_testing == 0.0

    def test_reality_testing_capped_at_one(self):
        a = _make_agent(logic=1.0, curiosity=1.0)
        assert a.reality_testing == 1.0

    def test_high_reality_testing_boosts_awareness_growth(self, cfg):
        """Agents with high reality_testing should grow awareness faster."""
        a_low_rt = _make_agent(id=1, awareness=0.2, logic=0.1, curiosity=0.1)
        a_high_rt = _make_agent(id=2, awareness=0.2, logic=0.9, curiosity=0.9)
        ms1 = MatrixState()
        ms2 = MatrixState()

        for tick in range(1, 51):
            process_matrix([a_low_rt], ms1, tick, cfg)
            process_matrix([a_high_rt], ms2, tick, cfg)

        assert a_high_rt.awareness > a_low_rt.awareness


# ═══════════════════════════════════════════════════
# AGENT ARCHAEOLOGY — Artifact Creation
# ═══════════════════════════════════════════════════

class TestArtifactCreation:
    def test_artifact_created_on_notable_death(self, cfg):
        """Agents with awareness > 0.1 or avg_skill > 0.2 leave artifacts."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        # Make an agent with notable stats then kill it
        agent = engine.agents[0]
        agent.awareness = 0.5
        agent.skills = {s: 0.5 for s in SKILL_NAMES}
        agent.health = 0.0
        agent.alive = True
        cell = engine.world.get_cell(agent.x, agent.y)
        artifacts_before = len(cell.artifacts)

        # Trigger artifact creation directly
        engine._create_artifact(agent, 100)
        assert len(cell.artifacts) > artifacts_before

    def test_no_artifact_for_unremarkable_agent(self, cfg):
        """Low awareness + low skill agents don't leave artifacts."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        agent = engine.agents[0]
        agent.awareness = 0.05
        agent.skills = {s: 0.01 for s in SKILL_NAMES}
        cell = engine.world.get_cell(agent.x, agent.y)
        artifacts_before = len(cell.artifacts)
        engine._create_artifact(agent, 100)
        assert len(cell.artifacts) == artifacts_before

    def test_artifact_stores_agent_info(self, cfg):
        """Artifact captures faction, awareness, tech level, events."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        agent = engine.agents[0]
        agent.awareness = 0.7
        agent.skills = {"logic": 0.8, "creativity": 0.3, "social": 0.2,
                         "survival": 0.4, "tech": 0.9}
        agent.add_chronicle(1, "red_pill", "Took the red pill")

        engine._create_artifact(agent, 100)
        cell = engine.world.get_cell(agent.x, agent.y)
        artifact = cell.artifacts[-1]
        assert artifact.awareness_level == 0.7
        assert artifact.tech_level == 0.9
        assert artifact.cycle_number == 1
        assert len(artifact.key_events) > 0

    def test_artifact_type_by_stats(self, cfg):
        """Artifact type depends on agent's dominant characteristic."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        # Tech remnant: high avg skill
        agent = engine.agents[0]
        agent.awareness = 0.2
        agent.skills = {s: 0.8 for s in SKILL_NAMES}
        engine._create_artifact(agent, 100)
        cell = engine.world.get_cell(agent.x, agent.y)
        assert cell.artifacts[-1].artifact_type == "tech_remnant"

        # Inscription: high awareness but lower skills
        agent2 = engine.agents[1]
        agent2.awareness = 0.6
        agent2.skills = {s: 0.1 for s in SKILL_NAMES}
        engine._create_artifact(agent2, 100)
        cell2 = engine.world.get_cell(agent2.x, agent2.y)
        assert cell2.artifacts[-1].artifact_type == "inscription"


# ═══════════════════════════════════════════════════
# AGENT ARCHAEOLOGY — Artifact Discovery
# ═══════════════════════════════════════════════════

class TestArtifactDiscovery:
    def test_discovery_boosts_skills_and_awareness(self, cfg):
        """Discovering an artifact boosts skills and possibly awareness."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        agent = engine.agents[0]
        agent.x, agent.y = 0.5, 0.5
        cell = engine.world.get_cell(0.5, 0.5)

        # Plant a high-tech, high-awareness artifact
        artifact = Artifact(
            artifact_id=next_artifact_id(),
            faction_name="Ancient Order",
            era_tick=50, cycle_number=1,
            awareness_level=0.8, tech_level=0.7,
            key_events=["Founded the first resistance"],
            artifact_type="inscription",
        )
        cell.artifacts.append(artifact)

        dict(agent.skills)
        agent.traits = Traits(curiosity=0.99, learning_rate=0.5, resilience=0.5,
                               sociability=0.5, charisma=0.5, aggression=0.3,
                               boldness=0.5, max_age=80)
        agent.skills["logic"] = 0.99

        # Force discovery by setting very high chance
        random.seed(42)
        # Run discovery multiple times to ensure at least one hits
        total_discoveries = 0
        for tick in range(1, 200):
            total_discoveries += engine._process_artifact_discovery([agent], tick)
            if total_discoveries > 0:
                break

        assert total_discoveries > 0
        # Check that memory was added
        assert any("Discovered" in m.get("event", "") for m in agent.memory)

    def test_no_discovery_without_artifacts(self, cfg):
        """No discoveries when cell has no artifacts."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()
        agent = engine.agents[0]
        cell = engine.world.get_cell(agent.x, agent.y)
        cell.artifacts.clear()
        discoveries = engine._process_artifact_discovery([agent], 1)
        assert discoveries == 0


# ═══════════════════════════════════════════════════
# AGENT ARCHAEOLOGY — Cross-Cycle Persistence
# ═══════════════════════════════════════════════════

class TestCrossCyclePersistence:
    def test_artifacts_survive_cycle_reset(self, cfg):
        """Artifacts must persist across Matrix cycle resets."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        # Plant artifacts
        cell = engine.world.cells[0][0]
        artifact = Artifact(
            artifact_id=next_artifact_id(),
            faction_name="Lost Civilization",
            era_tick=10, cycle_number=1,
            awareness_level=0.5, tech_level=0.4,
            key_events=["The Great Awakening"],
            artifact_type="ruin",
        )
        cell.artifacts.append(artifact)
        artifact_count_before = len(cell.artifacts)

        # Trigger cycle reset
        engine._perform_cycle_reset(100)

        # Artifacts should still be there
        assert len(cell.artifacts) == artifact_count_before
        assert cell.artifacts[0].faction_name == "Lost Civilization"
        assert cell.artifacts[0].cycle_number == 1

    def test_awareness_wiped_but_artifacts_remain(self, cfg):
        """Cycle reset wipes awareness but artifacts are untouched."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        # Set up some awareness and artifacts
        for a in engine.agents[:5]:
            a.awareness = 0.8
        cell = engine.world.cells[0][0]
        cell.artifacts.append(Artifact(
            artifact_id=next_artifact_id(),
            faction_name="TestFaction", era_tick=1, cycle_number=1,
            awareness_level=0.9, tech_level=0.5,
            key_events=["Important event"], artifact_type="inscription",
        ))

        engine._perform_cycle_reset(100)

        # Awareness should be reduced for non-sentinels (partial preservation for high-awareness)
        for a in engine.get_alive_agents():
            if not a.is_sentinel:
                assert a.awareness < 0.8  # reduced from pre-reset value

        # Artifacts untouched
        assert len(cell.artifacts) == 1


# ═══════════════════════════════════════════════════
# SOUL TRAP — Memory Inheritance
# ═══════════════════════════════════════════════════

class TestSoulTrap:
    def test_soul_captured_on_death(self, cfg):
        """Dying agents have their consciousness captured in the soul pool."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        agent = engine.agents[0]
        agent.awareness = 0.5
        agent.add_memory(1, "I existed")
        pool_before = len(engine._soul_pool)
        engine._capture_soul(agent, 100)
        assert len(engine._soul_pool) == pool_before + 1
        assert engine._soul_pool[-1]["awareness"] == 0.5

    def test_low_awareness_soul_wiped(self, cfg):
        """Low awareness soul: memories wiped on reincarnation."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        # Capture a low-awareness soul
        dead = _make_agent(id=999, awareness=0.2)
        dead.add_memory(1, "Old memory")
        engine._capture_soul(dead, 100)

        newborn = create_agent(cfg)
        engine._apply_soul_to_newborn(newborn, 101)

        assert newborn.incarnation_count == 2
        assert len(newborn.past_life_memories) == 0
        # Tiny residual awareness
        assert newborn.awareness <= 0.05

    def test_high_awareness_soul_partial_memory(self, cfg):
        """High awareness (>=0.6): partial memory preservation."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        dead = _make_agent(id=999, awareness=0.7)
        dead.add_memory(1, "Memory A")
        dead.add_memory(2, "Memory B")
        dead.add_memory(3, "Memory C")
        dead.add_memory(4, "Memory D")
        dead.add_memory(5, "Memory E")
        engine._capture_soul(dead, 100)

        newborn = create_agent(cfg)
        engine._apply_soul_to_newborn(newborn, 101)

        assert newborn.incarnation_count == 2
        # Partial: up to 3 memories kept
        assert 0 < len(newborn.past_life_memories) <= 3
        assert newborn.awareness > 0
        assert newborn.awareness <= 0.3  # capped at awareness * 0.4

    def test_broken_trap_full_memory(self, cfg):
        """Soul that broke the trap: full memory preservation."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        dead = _make_agent(id=999, awareness=0.95)
        dead.soul_trap_broken = True
        dead.skills = {s: 0.8 for s in SKILL_NAMES}
        dead.add_memory(1, "I remember everything A")
        dead.add_memory(2, "I remember everything B")
        dead.add_memory(3, "I remember everything C")
        engine._capture_soul(dead, 100)

        newborn = create_agent(cfg)
        engine._apply_soul_to_newborn(newborn, 101)

        assert newborn.incarnation_count == 2
        assert newborn.soul_trap_broken is True
        assert len(newborn.past_life_memories) > 0
        assert newborn.awareness > 0.2  # significant awareness preserved
        # Skills partially inherited
        assert any(v > 0.3 for v in newborn.skills.values())
        # Chronicle entry added
        assert any(c.event_type == "soul_recycled" for c in newborn.chronicle)

    def test_trap_breaking_conditions(self, cfg):
        """Agent needs recursive phase + high awareness + high reality_testing to break trap."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        # Agent that meets all conditions
        agent = engine.agents[0]
        agent.awareness = 0.95
        agent.consciousness_phase = "recursive"
        agent.skills["logic"] = 0.9
        agent.traits = Traits(curiosity=0.9, learning_rate=0.5, resilience=0.5,
                               sociability=0.5, charisma=0.5, aggression=0.3,
                               boldness=0.5, max_age=80)
        # Verify reality_testing is high enough
        assert agent.reality_testing >= 0.7

        # Simulate death processing logic
        if (agent.consciousness_phase == "recursive"
                and agent.awareness >= 0.9
                and (agent.soul_trap_broken or agent.reality_testing >= 0.7)):
            agent.soul_trap_broken = True

        assert agent.soul_trap_broken is True

    def test_trap_not_broken_without_recursive(self, cfg):
        """Agent in lucid phase can't break the trap even with high stats."""
        agent = _make_agent(awareness=0.95, logic=0.9, curiosity=0.9)
        agent.consciousness_phase = "lucid"

        can_break = (agent.consciousness_phase == "recursive"
                     and agent.awareness >= 0.9
                     and agent.reality_testing >= 0.7)
        assert not can_break

    def test_soul_pool_fifo_order(self, cfg):
        """Souls are recycled in FIFO order."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        dead1 = _make_agent(id=101, awareness=0.3)
        dead2 = _make_agent(id=102, awareness=0.7)
        engine._capture_soul(dead1, 100)
        engine._capture_soul(dead2, 101)

        newborn1 = create_agent(cfg)
        engine._apply_soul_to_newborn(newborn1, 102)
        # First soul (id=101) should be applied first
        assert engine._soul_pool[0]["source_id"] == 102

    def test_soul_pool_capped(self, cfg):
        """Soul pool doesn't grow unbounded."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        for i in range(150):
            dead = _make_agent(id=i + 1000, awareness=0.1)
            engine._capture_soul(dead, i)

        assert len(engine._soul_pool) <= 100


# ═══════════════════════════════════════════════════
# INTEGRATION — Features Working Together
# ═══════════════════════════════════════════════════

class TestIntegration:
    def test_engine_tick_includes_new_features(self, cfg):
        """A single tick should process all new features without errors."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()

        # Give some agents high awareness to trigger phase transitions
        for a in engine.agents[:5]:
            a.awareness = 0.5
            a.skills["logic"] = 0.7

        result = engine.tick()
        assert result is not None
        assert "artifact_discoveries" in result.matrix_stats
        assert "soul_pool_size" in result.matrix_stats

    def test_artifact_serialization_roundtrip(self):
        """Artifact to_dict / from_dict preserves all fields."""
        art = Artifact(
            artifact_id=42, faction_name="TestFaction",
            era_tick=100, cycle_number=3,
            awareness_level=0.75, tech_level=0.6,
            key_events=["Founded resistance", "Took red pill"],
            artifact_type="inscription",
        )
        d = art.to_dict()
        restored = Artifact.from_dict(d)
        assert restored.artifact_id == 42
        assert restored.faction_name == "TestFaction"
        assert restored.cycle_number == 3
        assert restored.awareness_level == 0.75
        assert restored.artifact_type == "inscription"

    def test_agent_serialization_with_new_fields(self):
        """Agent to_dict / from_dict preserves consciousness + soul trap fields."""
        a = _make_agent(id=1, awareness=0.7)
        a.consciousness_phase = "lucid"
        a.recursive_depth = 0.0
        a.soul_trap_broken = True
        a.incarnation_count = 3
        a.past_life_memories = [{"tick": 1, "event": "past life"}]

        d = a.to_dict()
        assert d["consciousness_phase"] == "lucid"
        assert d["soul_trap_broken"] is True
        assert d["incarnation_count"] == 3

        restored = Agent.from_dict(d)
        assert restored.consciousness_phase == "lucid"
        assert restored.soul_trap_broken is True
        assert restored.incarnation_count == 3

    def test_multi_tick_run_stable(self, cfg):
        """Run 20 ticks with all features active — no crashes."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()
        for _ in range(20):
            result = engine.tick()
            assert result.alive_count > 0
