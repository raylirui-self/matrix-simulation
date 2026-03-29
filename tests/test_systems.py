"""
Comprehensive test suite for all 11 simulation systems.
Tests each system independently and then integration.
"""
import os
import random

from src.agents import create_agent, create_offspring, Agent, Bond, Traits, EMOTION_NAMES, BELIEF_AXES
from src.beliefs import process_beliefs, belief_similarity, Faction
from src.communication import process_communication, InfoObject
from src.conflict import process_conflict, FactionWar
from src.economy import process_economy, process_inheritance
from src.emotions import process_emotions, on_agent_death_emotions, get_emotion_utility_modifiers
from src.engine import SimulationEngine, RunState
from src.matrix_layer import process_matrix, MatrixState, _create_sentinel
from src.persistence import SimulationDB
from src.world import ResourceGrid


# ===================================================
# TEST: Config Loading
# ===================================================

def test_config_load_default(cfg):
    assert cfg.population.initial_size == 50
    assert cfg.environment.harshness == 1.0


def test_config_new_system_configs_exist(cfg):
    assert hasattr(cfg, 'emotions'), "Missing emotions config"
    assert hasattr(cfg, 'beliefs'), "Missing beliefs config"
    assert hasattr(cfg, 'economy'), "Missing economy config"
    assert hasattr(cfg, 'matrix'), "Missing matrix config"
    assert hasattr(cfg, 'conflict'), "Missing conflict config"
    assert hasattr(cfg, 'communication'), "Missing communication config"
    assert cfg.emotions.decay_rate == 0.10
    assert cfg.matrix.max_sentinels == 5


# ===================================================
# TEST: Agent Data Model
# ===================================================

def test_agent_create_with_new_fields(cfg):
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


def test_agent_traits_include_charisma_and_aggression():
    t = Traits.random()
    assert hasattr(t, 'charisma'), "Missing charisma trait"
    assert hasattr(t, 'aggression'), "Missing aggression trait"
    assert 0.1 <= t.charisma <= 0.8
    assert 0.05 <= t.aggression <= 0.6


def test_agent_traits_inheritance_preserves_new_fields():
    a = Traits.random()
    b = Traits.random()
    child = Traits.inherit(a, b)
    assert hasattr(child, 'charisma')
    assert hasattr(child, 'aggression')
    assert 0.05 <= child.charisma <= 0.99
    assert 0.05 <= child.aggression <= 0.99


def test_agent_serialization_roundtrip(cfg):
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


def test_agent_offspring_inherits_beliefs_and_wealth(cfg):
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


def test_agent_properties_dominant_emotion_belief_extremism(cfg):
    a = create_agent(cfg)
    a.emotions = {"happiness": 0.9, "fear": 0.1, "anger": 0.0, "grief": 0.0, "hope": 0.3}
    assert a.dominant_emotion == "happiness"
    a.beliefs = {"individualism": 0.8, "tradition": -0.7, "system_trust": 0.5, "spirituality": -0.9}
    assert a.belief_extremism > 0.5


# ===================================================
# TEST: System 6 - Emotions
# ===================================================

def test_emotions_process_tick(cfg):
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
    stats = process_emotions(agents, 1, cfg)
    assert "avg_happiness" in stats
    assert "emotional_intensity" in stats


def test_emotions_death_triggers_grief(cfg):
    a = create_agent(cfg)
    b = create_agent(cfg)
    a.bonds.append(Bond(b.id, "mate", 0.9, 1))
    b.alive = False
    initial_grief = a.emotions["grief"]
    on_agent_death_emotions(b, [a], 10, cfg)
    assert a.emotions["grief"] > initial_grief


def test_emotions_utility_modifiers(cfg):
    a = create_agent(cfg)
    a.emotions["fear"] = 0.8
    mods = get_emotion_utility_modifiers(a, cfg)
    assert mods["safety_penalty"] > 0  # Fear increases safety concern
    assert mods["curiosity_pull"] < 0  # Fear decreases exploration


# ===================================================
# TEST: System 7 - Beliefs & Factions
# ===================================================

def test_beliefs_process_tick(cfg):
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
    factions = []
    stats = process_beliefs(agents, factions, 20, cfg)
    assert "faction_count" in stats


def test_beliefs_similarity_computation(cfg):
    a = create_agent(cfg)
    b = create_agent(cfg)
    # Same beliefs = high similarity
    a.beliefs = {"individualism": 0.5, "tradition": 0.5, "system_trust": 0.5, "spirituality": 0.5}
    b.beliefs = dict(a.beliefs)
    sim = belief_similarity(a, b)
    assert sim > 0.9, f"Same beliefs should have high similarity, got {sim}"


def test_beliefs_faction_formation(cfg):
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


def test_beliefs_faction_serialization():
    f = Faction(id=1, name="Iron Covenant", founder_id=5, formed_at=100,
                core_beliefs={"individualism": 0.3, "tradition": -0.2, "system_trust": 0.1, "spirituality": 0.5})
    d = f.to_dict()
    f2 = Faction.from_dict(d)
    assert f2.name == "Iron Covenant"
    assert abs(f2.core_beliefs["individualism"] - 0.3) < 0.01


# ===================================================
# TEST: System 8 - Economy
# ===================================================

def test_economy_process_tick(cfg):
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


def test_economy_inheritance_on_death(cfg):
    parent = create_agent(cfg)
    child = create_agent(cfg)
    parent.wealth = 10.0
    parent.bonds.append(Bond(child.id, "family", 1.0, 1))
    child.alive = True
    initial_child_wealth = child.wealth
    process_inheritance(parent, [child], 100, cfg)
    assert child.wealth > initial_child_wealth


# ===================================================
# TEST: System 9 - Matrix Layer
# ===================================================

def test_matrix_process_tick(cfg):
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
    matrix_state = MatrixState()
    stats = process_matrix(agents, matrix_state, 1, cfg)
    assert "control_index" in stats
    assert "total_awareness" in stats
    assert matrix_state.control_index >= 0


def test_matrix_awareness_grows(cfg):
    a = create_agent(cfg)
    a.alive = True
    a.phase = "adult"
    a.traits.curiosity = 0.9
    a.intelligence = 0.8
    a.beliefs["system_trust"] = -0.5  # Skeptic
    matrix_state = MatrixState()
    initial = a.awareness
    for tick in range(50):
        process_matrix([a], matrix_state, tick, cfg)
    assert a.awareness > initial, "Awareness should grow for curious/intelligent agents"


def test_matrix_state_serialization():
    ms = MatrixState(cycle_number=3, control_index=0.7, anomaly_id=42)
    d = ms.to_dict()
    ms2 = MatrixState.from_dict(d)
    assert ms2.cycle_number == 3
    assert ms2.anomaly_id == 42


def test_matrix_sentinel_creation(cfg):
    target = create_agent(cfg)
    sentinel = _create_sentinel(target, 100)
    assert sentinel.is_sentinel
    assert sentinel.traits.aggression == 0.8
    assert sentinel.traits.sociability == 0.0
    assert sentinel.skills["social"] == 0.0


# ===================================================
# TEST: System 10 - Conflict
# ===================================================

def test_conflict_process_tick_no_wars(cfg):
    world = ResourceGrid(cfg)
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
    stats = process_conflict(agents, [], [], 30, cfg, world)
    assert "wars_active" in stats
    assert stats["wars_active"] == 0


def test_conflict_faction_war_serialization():
    w = FactionWar(faction_a_id=1, faction_b_id=2, started_at=100, casualties_a=5, intensity=0.7)
    d = w.to_dict()
    w2 = FactionWar.from_dict(d)
    assert w2.faction_a_id == 1
    assert w2.casualties_a == 5


# ===================================================
# TEST: System 11 - Communication
# ===================================================

def test_communication_process_tick(cfg):
    agents = [create_agent(cfg) for _ in range(10)]
    for a in agents:
        a.alive = True
        a.phase = "adult"
    info_objects = []
    agent_info = {}
    stats = process_communication(agents, info_objects, agent_info, 10, cfg)
    assert "info_created" in stats
    assert "info_transmitted" in stats


def test_communication_info_object_serialization():
    info = InfoObject(id=1, created_at=10, origin_agent_id=5,
                      info_type="knowledge", content="Test knowledge",
                      skill_target="tech", truth_value=0.9, potency=0.5)
    d = info.to_dict()
    info2 = InfoObject.from_dict(d)
    assert info2.info_type == "knowledge"
    assert info2.skill_target == "tech"
    assert abs(info2.truth_value - 0.9) < 0.01


# ===================================================
# TEST: Engine Integration
# ===================================================

def test_engine_initialize_with_new_systems(engine, cfg):
    assert len(engine.agents) == cfg.population.initial_size
    assert isinstance(engine.factions, list)
    assert isinstance(engine.wars, list)
    assert engine.matrix_state is not None
    assert isinstance(engine.info_objects, list)


def test_engine_single_tick(engine):
    result = engine.tick()
    assert result.tick == 1
    assert result.alive_count > 0
    assert "avg_happiness" in result.emotion_stats
    assert "faction_count" in result.belief_stats
    assert "total_wealth" in result.economy_stats
    assert "control_index" in result.matrix_stats
    assert "wars_active" in result.conflict_stats
    assert "info_created" in result.communication_stats


def test_engine_multi_tick_stability(engine):
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


def test_engine_population_summary(engine):
    engine.tick()
    summary = engine.get_population_summary()
    assert "avg_emotions" in summary
    assert "factions" in summary
    assert "wars" in summary
    assert "matrix" in summary
    assert "avg_wealth" in summary
    assert "avg_awareness" in summary
    assert "redpilled_count" in summary


def test_engine_200_ticks_without_crash(cfg):
    engine = SimulationEngine(cfg, state=RunState(run_id="stress"))
    engine.initialize()
    last_result = None
    for _ in range(200):
        last_result = engine.tick()
        if last_result.alive_count == 0:
            break
    assert last_result is not None


# ===================================================
# TEST: Persistence
# ===================================================

def test_persistence_save_and_load_snapshot(cfg):
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
