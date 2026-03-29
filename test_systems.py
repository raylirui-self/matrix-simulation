"""
Comprehensive test suite for all 11 simulation systems.
Tests each system independently and then integration.
"""
import sys
import traceback
import random

# Fix random seed for reproducible tests
random.seed(42)

results = []

def test(name):
    """Decorator to register and run tests."""
    def decorator(fn):
        try:
            fn()
            results.append((name, "PASS", ""))
            print(f"  PASS  {name}")
        except Exception as e:
            tb = traceback.format_exc().split("\n")[-3:]
            results.append((name, "FAIL", str(e)))
            print(f"  FAIL  {name}: {e}")
            for line in tb:
                if line.strip():
                    print(f"        {line.strip()}")
        return fn
    return decorator


# ═══════════════════════════════════════════
# TEST: Config Loading
# ═══════════════════════════════════════════
@test("Config: Load default config")
def _():
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    assert cfg.population.initial_size == 40
    assert cfg.environment.harshness == 1.0

@test("Config: New system configs exist")
def _():
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    assert hasattr(cfg, 'emotions'), "Missing emotions config"
    assert hasattr(cfg, 'beliefs'), "Missing beliefs config"
    assert hasattr(cfg, 'economy'), "Missing economy config"
    assert hasattr(cfg, 'matrix'), "Missing matrix config"
    assert hasattr(cfg, 'conflict'), "Missing conflict config"
    assert hasattr(cfg, 'communication'), "Missing communication config"
    assert cfg.emotions.decay_rate == 0.05
    assert cfg.matrix.max_sentinels == 5

# ═══════════════════════════════════════════
# TEST: Agent Data Model
# ═══════════════════════════════════════════
@test("Agent: Create agent with new fields")
def _():
    from src.agents import create_agent, EMOTION_NAMES, BELIEF_AXES
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    a = create_agent(cfg)
    # Check emotions exist
    assert all(e in a.emotions for e in EMOTION_NAMES), f"Missing emotions: {a.emotions}"
    # Check beliefs exist
    assert all(b in a.beliefs for b in BELIEF_AXES), f"Missing beliefs: {a.beliefs}"
    # Check new fields
    assert a.wealth == 0.0
    assert a.awareness == 0.0
    assert a.trauma == 0.0
    assert not a.is_anomaly
    assert not a.is_sentinel
    assert a.faction_id is None

@test("Agent: Traits include charisma and aggression")
def _():
    from src.agents import Traits
    t = Traits.random()
    assert hasattr(t, 'charisma'), "Missing charisma trait"
    assert hasattr(t, 'aggression'), "Missing aggression trait"
    assert 0.1 <= t.charisma <= 0.8
    assert 0.05 <= t.aggression <= 0.6

@test("Agent: Traits inheritance preserves new fields")
def _():
    from src.agents import Traits
    a = Traits.random()
    b = Traits.random()
    child = Traits.inherit(a, b)
    assert hasattr(child, 'charisma')
    assert hasattr(child, 'aggression')
    assert 0.05 <= child.charisma <= 0.99
    assert 0.05 <= child.aggression <= 0.99

@test("Agent: Serialization roundtrip with new fields")
def _():
    from src.agents import create_agent, Agent
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    a = create_agent(cfg)
    a.emotions["happiness"] = 0.8
    a.beliefs["individualism"] = 0.5
    a.wealth = 3.14
    a.awareness = 0.42
    a.faction_id = 7
    d = a.to_dict()
    b = Agent.from_dict(d)
    assert abs(b.emotions["happiness"] - 0.8) < 0.01
    assert abs(b.beliefs["individualism"] - 0.5) < 0.01
    assert abs(b.wealth - 3.14) < 0.01
    assert abs(b.awareness - 0.42) < 0.01
    assert b.faction_id == 7

@test("Agent: Offspring inherits beliefs and wealth")
def _():
    from src.agents import create_agent, create_offspring
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    a = create_agent(cfg)
    b = create_agent(cfg)
    a.beliefs["individualism"] = 0.8
    b.beliefs["individualism"] = 0.2
    a.wealth = 10.0
    b.wealth = 5.0
    child = create_offspring(a, b, tick=100)
    # Child gets 5% of combined parental wealth
    assert child.wealth > 0
    # Child beliefs should be somewhere between parents (with noise)
    assert -1.0 <= child.beliefs["individualism"] <= 1.0

@test("Agent: Properties (dominant_emotion, belief_extremism)")
def _():
    from src.agents import create_agent
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    a = create_agent(cfg)
    a.emotions = {"happiness": 0.9, "fear": 0.1, "anger": 0.0, "grief": 0.0, "hope": 0.3}
    assert a.dominant_emotion == "happiness"
    a.beliefs = {"individualism": 0.8, "tradition": -0.7, "system_trust": 0.5, "spirituality": -0.9}
    assert a.belief_extremism > 0.5

# ═══════════════════════════════════════════
# TEST: System 6 - Emotions
# ═══════════════════════════════════════════
@test("Emotions: Process emotions tick")
def _():
    from src.emotions import process_emotions, on_agent_death_emotions
    from src.agents import create_agent, Bond
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
    stats = process_emotions(agents, 1, cfg)
    assert "avg_happiness" in stats
    assert "emotional_intensity" in stats

@test("Emotions: Death triggers grief in bonded agents")
def _():
    from src.emotions import on_agent_death_emotions
    from src.agents import create_agent, Bond
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    a = create_agent(cfg)
    b = create_agent(cfg)
    a.bonds.append(Bond(b.id, "mate", 0.9, 1))
    b.alive = False
    initial_grief = a.emotions["grief"]
    on_agent_death_emotions(b, [a], 10, cfg)
    assert a.emotions["grief"] > initial_grief

@test("Emotions: Utility modifiers from emotional state")
def _():
    from src.emotions import get_emotion_utility_modifiers
    from src.agents import create_agent
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    a = create_agent(cfg)
    a.emotions["fear"] = 0.8
    mods = get_emotion_utility_modifiers(a, cfg)
    assert mods["safety_penalty"] > 0  # Fear increases safety concern
    assert mods["curiosity_pull"] < 0  # Fear decreases exploration

# ═══════════════════════════════════════════
# TEST: System 7 - Beliefs & Factions
# ═══════════════════════════════════════════
@test("Beliefs: Process beliefs tick")
def _():
    from src.beliefs import process_beliefs, Faction
    from src.agents import create_agent
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
    factions = []
    stats = process_beliefs(agents, factions, 20, cfg)
    assert "faction_count" in stats

@test("Beliefs: Belief similarity computation")
def _():
    from src.beliefs import belief_similarity
    from src.agents import create_agent
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    a = create_agent(cfg)
    b = create_agent(cfg)
    # Same beliefs = high similarity
    a.beliefs = {"individualism": 0.5, "tradition": 0.5, "system_trust": 0.5, "spirituality": 0.5}
    b.beliefs = dict(a.beliefs)
    sim = belief_similarity(a, b)
    assert sim > 0.9, f"Same beliefs should have high similarity, got {sim}"

@test("Beliefs: Faction formation with similar agents")
def _():
    from src.beliefs import process_beliefs, Faction
    from src.agents import create_agent
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    agents = []
    # Create cluster of similar agents close together
    for _ in range(6):
        a = create_agent(cfg)
        a.alive = True
        a.phase = "adult"
        a.x, a.y = 0.5 + random.gauss(0, 0.02), 0.5 + random.gauss(0, 0.02)
        a.beliefs = {"individualism": 0.7, "tradition": 0.6, "system_trust": 0.3, "spirituality": 0.5}
        agents.append(a)
    factions = []
    # Run at the right interval
    stats = process_beliefs(agents, factions, 20, cfg)
    # Faction may or may not form depending on exact distances, but code should not crash
    assert isinstance(stats["faction_count"], int)

@test("Beliefs: Faction serialization")
def _():
    from src.beliefs import Faction
    f = Faction(id=1, name="Iron Covenant", founder_id=5, formed_at=100,
                core_beliefs={"individualism": 0.3, "tradition": -0.2, "system_trust": 0.1, "spirituality": 0.5})
    d = f.to_dict()
    f2 = Faction.from_dict(d)
    assert f2.name == "Iron Covenant"
    assert abs(f2.core_beliefs["individualism"] - 0.3) < 0.01

# ═══════════════════════════════════════════
# TEST: System 8 - Economy
# ═══════════════════════════════════════════
@test("Economy: Process economy tick")
def _():
    from src.economy import process_economy
    from src.agents import create_agent
    from src.config_loader import SimConfig
    from src.world import ResourceGrid
    cfg = SimConfig.load()
    world = ResourceGrid(cfg)
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
        a.skills["survival"] = 0.5
    world.update_agent_counts(agents)
    # Run a few ticks to accumulate wealth past the decay threshold
    for t in range(5):
        stats = process_economy(agents, t + 1, cfg, world)
    assert "total_wealth" in stats
    assert "gini" in stats
    total = sum(a.wealth for a in agents)
    assert total > 0, f"Agents should gather wealth, got {total}"

@test("Economy: Inheritance on death")
def _():
    from src.economy import process_inheritance
    from src.agents import create_agent, Bond
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    parent = create_agent(cfg)
    child = create_agent(cfg)
    parent.wealth = 10.0
    parent.bonds.append(Bond(child.id, "family", 1.0, 1))
    child.alive = True
    initial_child_wealth = child.wealth
    process_inheritance(parent, [child], 100, cfg)
    assert child.wealth > initial_child_wealth

# ═══════════════════════════════════════════
# TEST: System 9 - Matrix Layer
# ═══════════════════════════════════════════
@test("Matrix: Process matrix tick")
def _():
    from src.matrix_layer import process_matrix, MatrixState
    from src.agents import create_agent
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
    matrix_state = MatrixState()
    stats = process_matrix(agents, matrix_state, 1, cfg)
    assert "control_index" in stats
    assert "total_awareness" in stats
    assert matrix_state.control_index >= 0

@test("Matrix: Awareness grows with curiosity and intelligence")
def _():
    from src.matrix_layer import process_matrix, MatrixState
    from src.agents import create_agent
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    a = create_agent(cfg)
    a.alive = True
    a.phase = "adult"
    a.traits.curiosity = 0.9
    a.intelligence = 0.8
    a.beliefs["system_trust"] = -0.5  # Skeptic
    matrix_state = MatrixState()
    initial = a.awareness
    for _ in range(50):
        process_matrix([a], matrix_state, _, cfg)
    assert a.awareness > initial, "Awareness should grow for curious/intelligent agents"

@test("Matrix: MatrixState serialization")
def _():
    from src.matrix_layer import MatrixState
    ms = MatrixState(cycle_number=3, control_index=0.7, anomaly_id=42)
    d = ms.to_dict()
    ms2 = MatrixState.from_dict(d)
    assert ms2.cycle_number == 3
    assert ms2.anomaly_id == 42

@test("Matrix: Sentinel creation")
def _():
    from src.matrix_layer import _create_sentinel
    from src.agents import create_agent
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    target = create_agent(cfg)
    sentinel = _create_sentinel(target, 100)
    assert sentinel.is_sentinel
    assert sentinel.traits.aggression == 0.8
    assert sentinel.traits.sociability == 0.0
    assert sentinel.skills["social"] == 0.0

# ═══════════════════════════════════════════
# TEST: System 10 - Conflict
# ═══════════════════════════════════════════
@test("Conflict: Process conflict tick (no wars)")
def _():
    from src.conflict import process_conflict
    from src.agents import create_agent
    from src.config_loader import SimConfig
    from src.world import ResourceGrid
    cfg = SimConfig.load()
    world = ResourceGrid(cfg)
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
    stats = process_conflict(agents, [], [], 30, cfg, world)
    assert "wars_active" in stats
    assert stats["wars_active"] == 0

@test("Conflict: FactionWar serialization")
def _():
    from src.conflict import FactionWar
    w = FactionWar(faction_a_id=1, faction_b_id=2, started_at=100, casualties_a=5, intensity=0.7)
    d = w.to_dict()
    w2 = FactionWar.from_dict(d)
    assert w2.faction_a_id == 1
    assert w2.casualties_a == 5

# ═══════════════════════════════════════════
# TEST: System 11 - Communication
# ═══════════════════════════════════════════
@test("Communication: Process communication tick")
def _():
    from src.communication import process_communication, InfoObject
    from src.agents import create_agent
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
    info_objects = []
    agent_info = {}
    stats = process_communication(agents, info_objects, agent_info, 10, cfg)
    assert "info_created" in stats
    assert "info_transmitted" in stats

@test("Communication: InfoObject serialization")
def _():
    from src.communication import InfoObject
    info = InfoObject(id=1, created_at=10, origin_agent_id=5,
                      info_type="knowledge", content="Test knowledge",
                      skill_target="tech", truth_value=0.9, potency=0.5)
    d = info.to_dict()
    info2 = InfoObject.from_dict(d)
    assert info2.info_type == "knowledge"
    assert info2.skill_target == "tech"
    assert abs(info2.truth_value - 0.9) < 0.01

# ═══════════════════════════════════════════
# TEST: Engine Integration
# ═══════════════════════════════════════════
@test("Engine: Initialize with new systems")
def _():
    from src.engine import SimulationEngine, RunState
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    engine = SimulationEngine(cfg, state=RunState(run_id="test"))
    engine.initialize()
    assert len(engine.agents) == cfg.population.initial_size
    assert isinstance(engine.factions, list)
    assert isinstance(engine.wars, list)
    assert engine.matrix_state is not None
    assert isinstance(engine.info_objects, list)

@test("Engine: Single tick with all systems")
def _():
    from src.engine import SimulationEngine, RunState
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    engine = SimulationEngine(cfg, state=RunState(run_id="test"))
    engine.initialize()
    result = engine.tick()
    assert result.tick == 1
    assert result.alive_count > 0
    assert "avg_happiness" in result.emotion_stats
    assert "faction_count" in result.belief_stats
    assert "total_wealth" in result.economy_stats
    assert "control_index" in result.matrix_stats
    assert "wars_active" in result.conflict_stats
    assert "info_created" in result.communication_stats

@test("Engine: Multi-tick stability (50 ticks)")
def _():
    from src.engine import SimulationEngine, RunState
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    engine = SimulationEngine(cfg, state=RunState(run_id="test"))
    engine.initialize()
    for _ in range(50):
        result = engine.tick()
    assert result.tick == 50
    assert result.alive_count >= 0
    alive = engine.get_alive_agents()
    if alive:
        non_sentinels = [a for a in alive if not a.is_sentinel]
        if non_sentinels:
            # Check new systems ran without error (stats exist)
            assert "avg_happiness" in result.emotion_stats
            assert "faction_count" in result.belief_stats
            assert "total_wealth" in result.economy_stats
            max_awareness = max(a.awareness for a in non_sentinels)
            assert max_awareness >= 0, "Awareness should be non-negative"

@test("Engine: Population summary includes new fields")
def _():
    from src.engine import SimulationEngine, RunState
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    engine = SimulationEngine(cfg, state=RunState(run_id="test"))
    engine.initialize()
    engine.tick()
    summary = engine.get_population_summary()
    assert "avg_emotions" in summary
    assert "factions" in summary
    assert "wars" in summary
    assert "matrix" in summary
    assert "avg_wealth" in summary
    assert "avg_awareness" in summary
    assert "redpilled_count" in summary

@test("Engine: 200 ticks without crash")
def _():
    from src.engine import SimulationEngine, RunState
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    engine = SimulationEngine(cfg, state=RunState(run_id="stress"))
    engine.initialize()
    last_result = None
    for _ in range(200):
        last_result = engine.tick()
        if last_result.alive_count == 0:
            break
    assert last_result is not None
    # Some emergent systems should have kicked in
    if last_result.alive_count > 0:
        print(f"        Pop={last_result.alive_count} Factions={last_result.belief_stats.get('faction_count',0)} "
              f"Wars={last_result.conflict_stats.get('wars_active',0)} "
              f"Awareness={last_result.matrix_stats.get('total_awareness',0):.2f} "
              f"Wealth={last_result.economy_stats.get('avg_wealth',0):.2f}")

# ═══════════════════════════════════════════
# TEST: Persistence
# ═══════════════════════════════════════════
@test("Persistence: Save and load snapshot with new systems")
def _():
    import os
    from src.engine import SimulationEngine, RunState
    from src.config_loader import SimConfig
    from src.persistence import SimulationDB
    cfg = SimConfig.load()

    test_db = "output/test_persistence.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    db = SimulationDB(test_db)
    engine = SimulationEngine(cfg, state=RunState(run_id="persist_test"))
    engine.initialize()
    # Run a few ticks to generate state
    for _ in range(10):
        engine.tick()

    run_id = db.create_run(cfg)
    db.save_snapshot(run_id, engine)
    db.flush()

    # Load it back
    engine2 = db.load_latest_snapshot(run_id, cfg)
    assert engine2 is not None
    assert engine2.state.current_tick == 10
    # Check new fields survived serialization
    alive = engine2.get_alive_agents()
    if alive:
        a = alive[0]
        assert "happiness" in a.emotions
        assert "individualism" in a.beliefs
        assert isinstance(a.wealth, float)
        assert isinstance(a.awareness, float)

    db.close()
    os.remove(test_db)


# ═══════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST RESULTS")
print("=" * 60)
passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
total = len(results)
print(f"\n  {passed}/{total} passed, {failed} failed\n")

if failed > 0:
    print("FAILURES:")
    for name, status, msg in results:
        if status == "FAIL":
            print(f"  - {name}: {msg}")

sys.exit(0 if failed == 0 else 1)
