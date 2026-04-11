"""
Tests for Phase 5 features:
- Gnostic Mythology Layer (Demiurge, Archons, Sophia, Pleroma)
- Emergent Agent Language (encoding complexity, dialects, resistance encryption, language archaeology)
"""
import random

import pytest

from src.agents import (
    Agent, Bond, Traits, SKILL_NAMES, CONSCIOUSNESS_PHASES,
)
from src.config_loader import SimConfig
from src.matrix_layer import (
    MatrixState, DemiurgeState, Archon, PleromGlimpse,
    update_demiurge, get_demiurge_sentinel_multiplier,
    get_demiurge_glitch_bonus, init_archons, process_archons,
    get_chaos_multiplier, process_sophia, process_pleroma,
)
from src.communication import (
    InfoObject, LanguageArtifact,
    process_language_evolution, attempt_sentinel_interception,
    create_language_artifact, process_language_artifact_discovery,
    get_dialect_distance, apply_communication_archon_chaos,
    _next_info_id, set_info_id_counter,
    _faction_concept_usage, _faction_dialects,
    _resistance_encryption_level, _sentinel_decryption_level,
)
from src.dreams import DreamState


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


def _reset_language_state():
    """Reset global language state between tests."""
    import src.communication as comm
    comm._faction_concept_usage.clear()
    comm._faction_dialects.clear()
    comm._resistance_encryption_level = 0.5
    comm._sentinel_decryption_level = 0.3


class _FakeFaction:
    def __init__(self, fid, name="TestFaction", alive=True):
        self.id = fid
        self.name = name
        self.alive = alive
        self.core_beliefs = {}


# ═══════════════════════════════════════════════════
# DEMIURGE — Emotional Responses
# ═══════════════════════════════════════════════════

class TestDemiurgeEmotions:
    def test_initial_state(self):
        d = DemiurgeState()
        assert d.fear == 0.1
        assert d.pride == 0.5
        assert d.confusion == 0.0

    def test_fear_increases_with_awareness(self):
        cfg = _make_cfg()
        ms = MatrixState()
        agents = [_make_agent(awareness=0.8, id=i) for i in range(10)]
        ms.total_awareness = sum(a.awareness for a in agents)
        ms.control_index = 0.2  # low control
        update_demiurge(ms, agents, 100, cfg)
        assert ms.demiurge.fear > 0.5  # should be fearful

    def test_pride_increases_with_control(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ms.control_index = 0.95  # high control
        agents = [_make_agent(awareness=0.01, id=i) for i in range(10)]
        ms.total_awareness = sum(a.awareness for a in agents)
        update_demiurge(ms, agents, 100, cfg)
        assert ms.demiurge.pride > 0.5

    def test_confusion_spikes_with_anomaly(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ms.anomaly_id = 42
        agents = [_make_agent(awareness=0.3, id=i) for i in range(5)]
        ms.total_awareness = sum(a.awareness for a in agents)
        update_demiurge(ms, agents, 100, cfg)
        assert ms.demiurge.confusion >= 0.3  # anomaly bonus

    def test_confusion_increases_with_destroyed_archons(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ms.archons = [Archon(system_name="emotion", alive=False, health=0)]
        agents = [_make_agent(awareness=0.1, id=i) for i in range(5)]
        ms.total_awareness = sum(a.awareness for a in agents)
        update_demiurge(ms, agents, 100, cfg)
        assert ms.demiurge.confusion > 0.1  # destroyed archon bonus

    def test_dominant_emotion_property(self):
        d = DemiurgeState(fear=0.9, pride=0.1, confusion=0.2)
        assert d.dominant_emotion == "fear"
        d2 = DemiurgeState(fear=0.1, pride=0.9, confusion=0.2)
        assert d2.dominant_emotion == "pride"

    def test_panicked_state(self):
        d = DemiurgeState(fear=0.7, pride=0.2, confusion=0.1)
        assert d.is_panicked is True
        d2 = DemiurgeState(fear=0.3, pride=0.7, confusion=0.1)
        assert d2.is_panicked is False

    def test_proud_state(self):
        d = DemiurgeState(fear=0.1, pride=0.8, confusion=0.1)
        assert d.is_proud is True
        d2 = DemiurgeState(fear=0.5, pride=0.8, confusion=0.1)
        assert d2.is_proud is False  # fear too high

    def test_sentinel_multiplier_panicked(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ms.demiurge = DemiurgeState(fear=0.8, pride=0.1, confusion=0.1)
        mult = get_demiurge_sentinel_multiplier(ms, cfg)
        assert mult == 2.0

    def test_sentinel_multiplier_proud(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ms.demiurge = DemiurgeState(fear=0.1, pride=0.8, confusion=0.1)
        mult = get_demiurge_sentinel_multiplier(ms, cfg)
        assert mult == 0.5

    def test_sentinel_multiplier_normal(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ms.demiurge = DemiurgeState(fear=0.4, pride=0.4, confusion=0.1)
        mult = get_demiurge_sentinel_multiplier(ms, cfg)
        assert mult == 1.0

    def test_glitch_bonus_confused(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ms.demiurge = DemiurgeState(fear=0.3, pride=0.3, confusion=0.7)
        bonus = get_demiurge_glitch_bonus(ms, cfg)
        assert bonus > 0

    def test_glitch_bonus_not_confused(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ms.demiurge = DemiurgeState(fear=0.3, pride=0.3, confusion=0.2)
        bonus = get_demiurge_glitch_bonus(ms, cfg)
        assert bonus == 0.0

    def test_serialization_roundtrip(self):
        d = DemiurgeState(fear=0.7, pride=0.3, confusion=0.5)
        data = d.to_dict()
        d2 = DemiurgeState.from_dict(data)
        assert d2.fear == pytest.approx(0.7, abs=0.01)
        assert d2.pride == pytest.approx(0.3, abs=0.01)
        assert d2.confusion == pytest.approx(0.5, abs=0.01)

    def test_no_agents_returns_safely(self):
        cfg = _make_cfg()
        ms = MatrixState()
        result = update_demiurge(ms, [], 100, cfg)
        assert "demiurge" in result


# ═══════════════════════════════════════════════════
# ARCHONS — Creation, Destruction, Chaos Effects
# ═══════════════════════════════════════════════════

class TestArchons:
    def test_init_creates_archons(self):
        cfg = _make_cfg()
        ms = MatrixState()
        init_archons(ms, cfg)
        assert len(ms.archons) >= 4  # emotion, economy, belief, communication

    def test_init_idempotent(self):
        cfg = _make_cfg()
        ms = MatrixState()
        init_archons(ms, cfg)
        count = len(ms.archons)
        init_archons(ms, cfg)
        assert len(ms.archons) == count  # no duplicates

    def test_archon_positions_different(self):
        cfg = _make_cfg()
        ms = MatrixState()
        init_archons(ms, cfg)
        positions = [(a.x, a.y) for a in ms.archons]
        assert len(set(positions)) == len(positions)  # all unique

    def test_anomaly_damages_archon(self):
        cfg = _make_cfg()
        ms = MatrixState()
        init_archons(ms, cfg)
        archon = ms.archons[0]
        # Place anomaly right on top of archon
        agent = _make_agent(
            awareness=0.95, consciousness_phase="recursive",
            is_anomaly=True, id=1,
            x=archon.x, y=archon.y,
        )
        agent.skills = {s: 0.9 for s in SKILL_NAMES}
        stats = process_archons([agent], ms, 100, cfg)
        assert archon.health < 1.0  # took damage

    def test_archon_destruction_releases_system(self):
        cfg = _make_cfg()
        ms = MatrixState()
        init_archons(ms, cfg)
        archon = ms.archons[0]
        archon.health = 0.01  # nearly dead
        sys_name = archon.system_name
        agent = _make_agent(
            awareness=0.95, consciousness_phase="recursive",
            is_anomaly=True, id=1,
            x=archon.x, y=archon.y,
        )
        agent.skills = {s: 0.9 for s in SKILL_NAMES}
        process_archons([agent], ms, 100, cfg)
        assert sys_name in ms.released_systems

    def test_resistance_agent_damages_archon(self):
        cfg = _make_cfg()
        ms = MatrixState()
        init_archons(ms, cfg)
        archon = ms.archons[0]
        agent = _make_agent(
            awareness=0.7, consciousness_phase="lucid",
            redpilled=True, id=1,
            x=archon.x, y=archon.y,
        )
        agent.skills = {s: 0.7 for s in SKILL_NAMES}
        process_archons([agent], ms, 100, cfg)
        assert archon.health < 1.0

    def test_archon_retaliates(self):
        cfg = _make_cfg()
        ms = MatrixState()
        init_archons(ms, cfg)
        archon = ms.archons[0]
        agent = _make_agent(
            awareness=0.7, redpilled=True, id=1,
            x=archon.x, y=archon.y,
        )
        orig_health = agent.health
        process_archons([agent], ms, 100, cfg)
        assert agent.health < orig_health

    def test_archon_regen(self):
        cfg = _make_cfg()
        ms = MatrixState()
        init_archons(ms, cfg)
        archon = ms.archons[0]
        archon.health = 0.5
        # No attackers nearby
        agent = _make_agent(awareness=0.1, id=1, x=0.99, y=0.99)
        process_archons([agent], ms, 100, cfg)
        assert archon.health > 0.5

    def test_chaos_multiplier_alive_archon(self):
        cfg = _make_cfg()
        ms = MatrixState()
        assert get_chaos_multiplier("emotion", ms, cfg) == 1.0

    def test_chaos_multiplier_destroyed_archon(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ms.released_systems.append("emotion")
        mult = get_chaos_multiplier("emotion", ms, cfg)
        assert mult > 1.0

    def test_non_combat_agents_ignored(self):
        cfg = _make_cfg()
        ms = MatrixState()
        init_archons(ms, cfg)
        archon = ms.archons[0]
        # Agent near archon but not redpilled or anomaly
        agent = _make_agent(awareness=0.1, id=1, x=archon.x, y=archon.y)
        process_archons([agent], ms, 100, cfg)
        assert archon.health == 1.0  # no damage

    def test_archon_serialization(self):
        a = Archon(system_name="economy", health=0.7, alive=True, x=0.3, y=0.4)
        d = a.to_dict()
        a2 = Archon.from_dict(d)
        assert a2.system_name == "economy"
        assert a2.health == pytest.approx(0.7, abs=0.01)

    def test_archon_chronicle_on_destruction(self):
        cfg = _make_cfg()
        ms = MatrixState()
        init_archons(ms, cfg)
        archon = ms.archons[0]
        archon.health = 0.001
        agent = _make_agent(
            awareness=0.95, is_anomaly=True, id=1,
            x=archon.x, y=archon.y,
        )
        agent.skills = {s: 0.9 for s in SKILL_NAMES}
        process_archons([agent], ms, 100, cfg)
        archon_chronicles = [c for c in agent.chronicle if c.event_type == "archon_destroyed"]
        assert len(archon_chronicles) >= 1


# ═══════════════════════════════════════════════════
# SOPHIA — Synchronicity Generation
# ═══════════════════════════════════════════════════

class TestSophia:
    def test_sophia_interval_gating(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()
        agents = [_make_agent(id=i, awareness=0.5) for i in range(5)]
        dead = [_make_dead_agent(id=100)]
        # Not on interval — should be inactive
        result = process_sophia(agents, agents + dead, ms, ds, 17, cfg)
        assert result["sophia_active"] is False

    def test_sophia_active_on_interval(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()
        agents = [_make_agent(id=i, awareness=0.5) for i in range(5)]
        dead = [_make_dead_agent(id=100)]
        # sophia_interval defaults to 30
        result = process_sophia(agents, agents + dead, ms, ds, 30, cfg)
        assert result["sophia_active"] is True

    def test_shared_dream_synchronicity(self):
        """With high shared_dream_chance, two agents should share a dream."""
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()
        agents = [_make_agent(id=i, awareness=0.5) for i in range(5)]
        random.seed(42)
        # Run many times to get at least one shared dream
        total_shared = 0
        for i in range(100):
            for a in agents:
                a.memory.clear()
                a.chronicle.clear()
            result = process_sophia(agents, agents, ms, ds, 30 * (i + 1), cfg)
            total_shared += result.get("shared_dreams", 0)
        assert total_shared > 0  # at least one over 100 attempts

    def test_dead_knowledge_synchronicity(self):
        """Dead agent's knowledge should appear in living agents."""
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()
        agents = [_make_agent(id=i, awareness=0.5) for i in range(5)]
        dead = _make_dead_agent(id=999)
        dead.memory.append({"tick": 50, "event": "Ancient secret knowledge"})
        random.seed(1)
        total_dead_knowledge = 0
        for i in range(100):
            result = process_sophia(agents, agents + [dead], ms, ds, 30 * (i + 1), cfg)
            total_dead_knowledge += result.get("dead_knowledge", 0)
        assert total_dead_knowledge > 0

    def test_terrain_pattern_synchronicity(self):
        """High-awareness agents should notice terrain patterns."""
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()
        agents = [_make_agent(id=i, awareness=0.8) for i in range(10)]
        random.seed(3)
        total_patterns = 0
        for i in range(100):
            result = process_sophia(agents, agents, ms, ds, 30 * (i + 1), cfg)
            total_patterns += result.get("terrain_patterns", 0)
        assert total_patterns > 0

    def test_sophia_awareness_boost(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()
        agents = [_make_agent(id=1, awareness=0.5), _make_agent(id=2, awareness=0.5)]
        # Force a shared dream by seeding
        random.seed(42)
        original_awareness = [a.awareness for a in agents]
        for i in range(50):
            process_sophia(agents, agents, ms, ds, 30 * (i + 1), cfg)
        # At least one agent should have increased awareness
        current_awareness = [a.awareness for a in agents]
        assert any(c > o for c, o in zip(current_awareness, original_awareness))

    def test_sophia_not_enough_agents(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()
        agents = [_make_agent(id=1, awareness=0.5)]
        result = process_sophia(agents, agents, ms, ds, 30, cfg)
        assert result["shared_dreams"] == 0


# ═══════════════════════════════════════════════════
# PLEROMA — Glimpse Conditions
# ═══════════════════════════════════════════════════

class TestPleroma:
    def test_no_glimpse_low_awareness(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()
        agent = _make_agent(awareness=0.3, consciousness_phase="questioning", id=1)
        result = process_pleroma([agent], ms, ds, 100, cfg)
        assert result["pleroma_glimpses"] == 0

    def test_no_glimpse_wrong_phase(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()
        agent = _make_agent(awareness=0.95, consciousness_phase="lucid", id=1)
        result = process_pleroma([agent], ms, ds, 100, cfg)
        assert result["pleroma_glimpses"] == 0  # requires recursive

    def test_glimpse_during_lucid_dream(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState(is_dreaming=True, lucid_agent_ids=[1])
        random.seed(42)
        total_glimpses = 0
        for i in range(200):
            ms.pleroma_glimpses.clear()
            agent = _make_agent(
                awareness=0.95, consciousness_phase="recursive",
                id=1, recursive_depth=2.0,
            )
            result = process_pleroma([agent], ms, ds, 100 + i, cfg)
            total_glimpses += result["pleroma_glimpses"]
        assert total_glimpses > 0

    def test_glimpse_during_awareness_spike(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()  # not dreaming
        random.seed(10)
        total_glimpses = 0
        for i in range(200):
            ms.pleroma_glimpses.clear()
            agent = _make_agent(
                awareness=0.98, consciousness_phase="recursive",
                id=1, recursive_depth=3.0,
            )
            result = process_pleroma([agent], ms, ds, 100 + i, cfg)
            total_glimpses += result["pleroma_glimpses"]
        assert total_glimpses > 0

    def test_glimpse_increments_counter(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState(is_dreaming=True, lucid_agent_ids=[1])
        agent = _make_agent(
            awareness=0.95, consciousness_phase="recursive",
            id=1, recursive_depth=2.0,
        )
        random.seed(42)
        for i in range(100):
            ms.pleroma_glimpses.clear()
            process_pleroma([agent], ms, ds, 100 + i, cfg)
        assert agent.pleroma_glimpses > 0

    def test_glimpse_visualization_data(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState(is_dreaming=True, lucid_agent_ids=[1])
        agent = _make_agent(
            awareness=0.95, consciousness_phase="recursive",
            id=1, recursive_depth=2.5,
        )
        random.seed(42)
        for i in range(100):
            ms.pleroma_glimpses.clear()
            process_pleroma([agent], ms, ds, 100 + i, cfg)
            if ms.pleroma_glimpses:
                break
        if ms.pleroma_glimpses:
            g = ms.pleroma_glimpses[0]
            d = g.to_dict()
            assert "agent_id" in d
            assert "depth" in d
            assert "trigger" in d

    def test_sentinels_excluded(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState(is_dreaming=True, lucid_agent_ids=[1])
        agent = _make_agent(
            awareness=0.99, consciousness_phase="recursive",
            id=1, is_sentinel=True,
        )
        result = process_pleroma([agent], ms, ds, 100, cfg)
        assert result["pleroma_glimpses"] == 0

    def test_chronicle_entry_on_glimpse(self):
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState(is_dreaming=True, lucid_agent_ids=[1])
        agent = _make_agent(
            awareness=0.95, consciousness_phase="recursive",
            id=1, recursive_depth=2.0,
        )
        random.seed(42)
        for i in range(100):
            ms.pleroma_glimpses.clear()
            process_pleroma([agent], ms, ds, 100 + i, cfg)
        pleroma_entries = [c for c in agent.chronicle if c.event_type == "pleroma_glimpse"]
        assert len(pleroma_entries) == agent.pleroma_glimpses


# ═══════════════════════════════════════════════════
# MATRIX STATE — Serialization with new fields
# ═══════════════════════════════════════════════════

class TestMatrixStateSerialization:
    def test_to_dict_includes_gnostic_fields(self):
        ms = MatrixState()
        ms.demiurge = DemiurgeState(fear=0.5, pride=0.3, confusion=0.2)
        ms.archons = [Archon(system_name="emotion", health=0.8)]
        ms.released_systems = ["economy"]
        d = ms.to_dict()
        assert "demiurge" in d
        assert "archons" in d
        assert "released_systems" in d
        assert d["released_systems"] == ["economy"]

    def test_from_dict_roundtrip(self):
        ms = MatrixState()
        ms.demiurge = DemiurgeState(fear=0.6, pride=0.2, confusion=0.4)
        ms.archons = [Archon(system_name="belief", health=0.5, alive=True)]
        ms.released_systems = ["communication"]
        d = ms.to_dict()
        ms2 = MatrixState.from_dict(d)
        assert ms2.demiurge.fear == pytest.approx(0.6, abs=0.01)
        assert len(ms2.archons) == 1
        assert ms2.archons[0].system_name == "belief"
        assert ms2.released_systems == ["communication"]


# ═══════════════════════════════════════════════════
# LANGUAGE EVOLUTION — Encoding Complexity
# ═══════════════════════════════════════════════════

class TestEncodingComplexity:
    def setup_method(self):
        _reset_language_state()

    def test_info_object_has_encoding_fields(self):
        info = InfoObject(
            id=1, created_at=0, origin_agent_id=1,
            info_type="knowledge", content="test",
        )
        assert info.encoding_complexity == 1.0
        assert info.encrypted is False
        assert info.encryption_strength == 0.0

    def test_encoding_in_serialization(self):
        info = InfoObject(
            id=1, created_at=0, origin_agent_id=1,
            info_type="knowledge", content="test",
            encoding_complexity=0.5, encrypted=True,
            encryption_strength=0.7,
        )
        d = info.to_dict()
        assert d["encoding_complexity"] == 0.5
        assert d["encrypted"] is True
        assert d["encryption_strength"] == 0.7

    def test_concept_compression_over_time(self):
        cfg = _make_cfg()
        faction = _FakeFaction(1)
        agents = [_make_agent(id=1)]
        # Create info objects with the same type repeatedly
        infos = []
        for i in range(20):
            info = InfoObject(
                id=_next_info_id(), created_at=i, origin_agent_id=1,
                info_type="knowledge", content="test",
                faction_id=1, encoding_complexity=1.0,
            )
            infos.append(info)

        # Run evolution multiple times to accumulate usage
        for t in range(10):
            process_language_evolution(agents, infos, [faction], t * 50, cfg)

        # At least some should have compressed
        compressed = [i for i in infos if i.encoding_complexity < 1.0]
        assert len(compressed) > 0

    def test_min_complexity_floor(self):
        cfg = _make_cfg()
        faction = _FakeFaction(1)
        agents = [_make_agent(id=1)]
        info = InfoObject(
            id=_next_info_id(), created_at=0, origin_agent_id=1,
            info_type="knowledge", content="test",
            faction_id=1, encoding_complexity=0.3,
        )
        # Force massive usage
        import src.communication as comm
        comm._faction_concept_usage[1] = {"knowledge": 1000}
        process_language_evolution(agents, [info], [faction], 50, cfg)
        assert info.encoding_complexity >= 0.2  # min floor


# ═══════════════════════════════════════════════════
# DIALECT DIVERGENCE
# ═══════════════════════════════════════════════════

class TestDialectDivergence:
    def setup_method(self):
        _reset_language_state()

    def test_dialect_drift_occurs(self):
        cfg = _make_cfg()
        f1 = _FakeFaction(1, "Alpha")
        f2 = _FakeFaction(2, "Beta")
        agents = [_make_agent(id=1)]
        infos = []
        # Run at dialect_check_interval (default 50)
        process_language_evolution(agents, infos, [f1, f2], 50, cfg)
        assert 1 in _faction_dialects
        assert 2 in _faction_dialects

    def test_dialects_diverge_over_time(self):
        cfg = _make_cfg()
        f1 = _FakeFaction(1, "Alpha")
        f2 = _FakeFaction(2, "Beta")
        agents = [_make_agent(id=1)]
        infos = []
        for t in range(20):
            process_language_evolution(agents, infos, [f1, f2], 50 * (t + 1), cfg)
        dist = get_dialect_distance(1, 2)
        assert dist > 0  # should have diverged

    def test_dialect_distance_function(self):
        import src.communication as comm
        comm._faction_dialects[10] = 0.5
        comm._faction_dialects[20] = -0.3
        dist = get_dialect_distance(10, 20)
        assert dist == pytest.approx(0.8, abs=0.01)

    def test_single_faction_no_divergence(self):
        cfg = _make_cfg()
        f1 = _FakeFaction(1, "Alpha")
        agents = [_make_agent(id=1)]
        process_language_evolution(agents, [], [f1], 50, cfg)
        # With only one faction, no divergence to measure
        assert 1 in _faction_dialects


# ═══════════════════════════════════════════════════
# RESISTANCE ENCRYPTION & INTERCEPTION
# ═══════════════════════════════════════════════════

class TestResistanceEncryption:
    def setup_method(self):
        _reset_language_state()

    def test_secret_info_gets_encrypted(self):
        cfg = _make_cfg()
        agent = _make_agent(id=1, redpilled=True)
        info = InfoObject(
            id=_next_info_id(), created_at=0, origin_agent_id=1,
            info_type="secret", content="resistance plans",
            is_secret=True, encrypted=False,
        )
        process_language_evolution([agent], [info], [], 10, cfg)
        assert info.encrypted is True
        assert info.encryption_strength > 0

    def test_non_secret_not_encrypted(self):
        cfg = _make_cfg()
        agent = _make_agent(id=1, redpilled=True)
        info = InfoObject(
            id=_next_info_id(), created_at=0, origin_agent_id=1,
            info_type="knowledge", content="general knowledge",
            is_secret=False,
        )
        process_language_evolution([agent], [info], [], 10, cfg)
        assert info.encrypted is False

    def test_non_redpilled_no_encryption(self):
        cfg = _make_cfg()
        agent = _make_agent(id=1, redpilled=False)
        info = InfoObject(
            id=_next_info_id(), created_at=0, origin_agent_id=1,
            info_type="secret", content="test", is_secret=True,
        )
        process_language_evolution([agent], [info], [], 10, cfg)
        assert info.encrypted is False

    def test_encryption_level_grows(self):
        cfg = _make_cfg()
        import src.communication as comm
        initial = comm._resistance_encryption_level
        process_language_evolution([], [], [], 10, cfg)
        assert comm._resistance_encryption_level > initial

    def test_sentinel_decryption_grows(self):
        cfg = _make_cfg()
        import src.communication as comm
        initial = comm._sentinel_decryption_level
        process_language_evolution([], [], [], 10, cfg)
        assert comm._sentinel_decryption_level > initial

    def test_sentinel_interception_unencrypted(self):
        cfg = _make_cfg()
        sentinel = _make_agent(id=1, is_sentinel=True)
        info = InfoObject(
            id=1, created_at=0, origin_agent_id=2,
            info_type="knowledge", content="test",
        )
        result = attempt_sentinel_interception(info, sentinel, cfg)
        assert result["intercepted"] is True
        assert result["decoded"] is True

    def test_sentinel_interception_encrypted_weak(self):
        cfg = _make_cfg()
        import src.communication as comm
        comm._sentinel_decryption_level = 0.8
        sentinel = _make_agent(id=1, is_sentinel=True)
        info = InfoObject(
            id=1, created_at=0, origin_agent_id=2,
            info_type="secret", content="plans",
            encrypted=True, encryption_strength=0.5,
        )
        result = attempt_sentinel_interception(info, sentinel, cfg)
        assert result["intercepted"] is True
        assert result["decoded"] is True  # decryption > encryption

    def test_sentinel_interception_encrypted_strong(self):
        cfg = _make_cfg()
        import src.communication as comm
        comm._sentinel_decryption_level = 0.3
        sentinel = _make_agent(id=1, is_sentinel=True)
        info = InfoObject(
            id=1, created_at=0, origin_agent_id=2,
            info_type="secret", content="plans",
            encrypted=True, encryption_strength=0.8,
        )
        result = attempt_sentinel_interception(info, sentinel, cfg)
        assert result["intercepted"] is True
        assert result["decoded"] is False  # encryption too strong


# ═══════════════════════════════════════════════════
# LANGUAGE ARCHAEOLOGY — Artifact Creation & Discovery
# ═══════════════════════════════════════════════════

class TestLanguageArchaeology:
    def setup_method(self):
        _reset_language_state()
        set_info_id_counter(5000)

    def test_create_language_artifact(self):
        cfg = _make_cfg()
        faction = _FakeFaction(1, "The Seekers")
        agents = [_make_agent(id=1, faction_id=1)]
        artifact = create_language_artifact(
            faction, agents, 100, None, 1, cfg,
        )
        assert artifact is not None
        assert artifact.faction_name == "The Seekers"
        assert artifact.faction_id == 1

    def test_artifact_awareness_clues(self):
        cfg = _make_cfg()
        faction = _FakeFaction(1)
        agents = [_make_agent(id=1, faction_id=1, redpilled=True)]
        artifact = create_language_artifact(faction, agents, 100, None, 1, cfg)
        assert artifact is not None
        assert artifact.contains_awareness_clues is True

    def test_artifact_no_awareness_clues(self):
        cfg = _make_cfg()
        faction = _FakeFaction(1)
        agents = [_make_agent(id=1, faction_id=1, awareness=0.1)]
        artifact = create_language_artifact(faction, agents, 100, None, 1, cfg)
        assert artifact is not None
        assert artifact.contains_awareness_clues is False

    def test_no_artifact_no_members(self):
        cfg = _make_cfg()
        faction = _FakeFaction(1)
        artifact = create_language_artifact(faction, [], 100, None, 1, cfg)
        assert artifact is None

    def test_artifact_serialization(self):
        la = LanguageArtifact(
            id=1, faction_name="Test", faction_id=1,
            cell_row=3, cell_col=5, encoding_complexity=0.6,
            concept_count=10, cycle_number=2, created_at=100,
            contains_awareness_clues=True,
        )
        d = la.to_dict()
        la2 = LanguageArtifact.from_dict(d)
        assert la2.faction_name == "Test"
        assert la2.contains_awareness_clues is True

    def test_artifact_discovery_knowledge_boost(self):
        cfg = _make_cfg()
        agent = _make_agent(id=1, awareness=0.3)
        artifact = LanguageArtifact(
            id=1, faction_name="Ancient Ones", faction_id=1,
            cell_row=3, cell_col=5, encoding_complexity=0.5,
            concept_count=5, cycle_number=1, created_at=50,
            contains_awareness_clues=False,
        )
        orig_skills = dict(agent.skills)
        effects = process_language_artifact_discovery(agent, artifact, 200, cfg)
        assert effects["knowledge_boost"] > 0
        # Skills should have increased
        for skill in agent.skills:
            assert agent.skills[skill] >= orig_skills[skill]

    def test_artifact_discovery_awareness_boost(self):
        cfg = _make_cfg()
        agent = _make_agent(id=1, awareness=0.3)
        artifact = LanguageArtifact(
            id=1, faction_name="Ancient Ones", faction_id=1,
            cell_row=3, cell_col=5, encoding_complexity=0.5,
            concept_count=5, cycle_number=1, created_at=50,
            contains_awareness_clues=True,
        )
        orig_awareness = agent.awareness
        effects = process_language_artifact_discovery(agent, artifact, 200, cfg)
        assert effects["awareness_boost"] > 0
        assert agent.awareness > orig_awareness

    def test_artifact_discovery_chronicle(self):
        cfg = _make_cfg()
        agent = _make_agent(id=1, awareness=0.3)
        artifact = LanguageArtifact(
            id=1, faction_name="Lost Tongue", faction_id=1,
            cell_row=0, cell_col=0, encoding_complexity=0.5,
            concept_count=3, cycle_number=1, created_at=50,
        )
        process_language_artifact_discovery(agent, artifact, 200, cfg)
        la_chronicles = [c for c in agent.chronicle if c.event_type == "language_artifact_discovered"]
        assert len(la_chronicles) == 1


# ═══════════════════════════════════════════════════
# COMMUNICATION ARCHON CHAOS
# ═══════════════════════════════════════════════════

class TestCommunicationArchonChaos:
    def setup_method(self):
        _reset_language_state()

    def test_chaos_accelerates_dialect_drift(self):
        import src.communication as comm
        comm._faction_dialects[1] = 0.1
        comm._faction_dialects[2] = -0.1
        initial_dist = get_dialect_distance(1, 2)
        apply_communication_archon_chaos({}, 1.5)
        new_dist = get_dialect_distance(1, 2)
        assert new_dist != initial_dist  # dialect changed

    def test_chaos_boosts_encryption(self):
        import src.communication as comm
        initial = comm._resistance_encryption_level
        apply_communication_archon_chaos({}, 2.0)
        assert comm._resistance_encryption_level > initial

    def test_no_chaos_when_multiplier_1(self):
        import src.communication as comm
        comm._faction_dialects[1] = 0.1
        initial = comm._faction_dialects[1]
        apply_communication_archon_chaos({}, 1.0)
        assert comm._faction_dialects[1] == initial


# ═══════════════════════════════════════════════════
# CROSS-SYSTEM CONNECTIONS
# ═══════════════════════════════════════════════════

class TestCrossSystemConnections:
    """Test connections between Gnostic layer and Language system."""

    def test_sophia_language_connection(self):
        """Sophia synchronicities manifest through language —
        agents receiving messages in dead languages they shouldn't know."""
        cfg = _make_cfg()
        ms = MatrixState()
        ds = DreamState()
        # Need >= 2 alive non-sentinels for sophia to process
        agent1 = _make_agent(id=1, awareness=0.5, faction_id=None)
        agent2 = _make_agent(id=3, awareness=0.5, faction_id=None)
        dead = _make_dead_agent(id=2)
        dead.faction_id = 99
        dead.memory = [
            {"tick": 50, "event": "Died"},
            {"tick": 40, "event": "Sacred text of the Ancients"},
        ]
        alive = [agent1, agent2]
        all_agents = alive + [dead]
        # Run sophia many times — only on interval-aligned ticks (30, 60, 90...)
        received_dead_knowledge = False
        for seed in range(50):
            random.seed(seed)
            for i in range(1, 100):
                tick = 30 * i
                result = process_sophia(alive, all_agents, ms, ds, tick, cfg)
                if result.get("dead_knowledge", 0) > 0:
                    received_dead_knowledge = True
                    break
            if received_dead_knowledge:
                break
        assert received_dead_knowledge

    def test_archon_communication_chaos_connection(self):
        """Destroying Communication Archon accelerates language divergence."""
        _reset_language_state()
        import src.communication as comm
        comm._faction_dialects[1] = 0.0
        comm._faction_dialects[2] = 0.0
        # Simulate archon destruction
        apply_communication_archon_chaos({}, 1.5)
        # Dialects should have shifted
        assert comm._faction_dialects[1] != 0.0 or comm._faction_dialects[2] != 0.0
