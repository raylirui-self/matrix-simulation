"""
Tests for Phase 2 Procedural Mythology features:
1. Civilization Chronicle — era summary generation
2. Mythological narrative generation — myth creation from events
3. Faction-specific historical revisionism — different perspectives
4. Legendary figures — creation, embellishment, and discovery
"""
import random

import pytest

from src.agents import Agent, Traits, Bond, ChronicleEntry, create_agent, SKILL_NAMES
from src.beliefs import Faction
from src.config_loader import SimConfig
from src.engine import SimulationEngine, RunState
from src.mythology import (
    EraSummary, Myth, LegendaryFigure, MythologyState,
    generate_era_summary, _fallback_era_summary,
    classify_events_for_myths, generate_myth, _fallback_myth,
    generate_faction_myths,
    identify_legendary_candidates, create_legendary_figure, _fallback_legend,
    apply_legend_discovery, process_legend_discoveries,
    _next_myth_id, _next_legend_id,
    set_myth_id_counter, set_legend_id_counter,
)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _make_agent(id=1, alive=True, **kwargs):
    """Create a test agent with sensible defaults."""
    a = Agent(
        id=id, sex="M", age=kwargs.get("age", 30), phase="adult",
        health=kwargs.get("health", 0.8),
        intelligence=0.5, generation=kwargs.get("generation", 2),
        alive=alive,
        traits=Traits(
            learning_rate=0.5, resilience=0.5, curiosity=0.5,
            sociability=0.5, charisma=kwargs.get("charisma", 0.5),
            aggression=kwargs.get("aggression", 0.3), boldness=0.5, max_age=80,
        ),
        skills={s: kwargs.get("skills", {}).get(s, 0.5) for s in SKILL_NAMES},
        awareness=kwargs.get("awareness", 0.0),
        redpilled=kwargs.get("redpilled", False),
        is_anomaly=kwargs.get("is_anomaly", False),
        faction_id=kwargs.get("faction_id", None),
    )
    if kwargs.get("chronicle"):
        a.chronicle = kwargs["chronicle"]
    return a


def _make_stats(**overrides):
    """Create a stats dict for testing."""
    base = {
        "alive": 50, "total_born": 80, "total_died": 30,
        "avg_health": 0.65, "max_generation": 3,
        "world": {"global_techs": ["agriculture"], "depleted_cells": 2, "grid_size": 8},
        "factions": [{"name": "Seekers", "core_beliefs": {"system_trust": -0.5}}],
        "wars": [],
        "matrix": {"cycle_number": 1, "control_index": 0.8, "anomaly_id": None},
        "recent_events": ["harsh_winter", "knowledge_bloom"],
    }
    base.update(overrides)
    return base


# ═══════════════════════════════════════════════════════════════
# TEST: Era Summary Generation (Civilization Chronicle)
# ═══════════════════════════════════════════════════════════════

class TestEraSummary:
    def test_era_summary_creation(self):
        """EraSummary can be created and serialized."""
        es = EraSummary(tick_start=0, tick_end=100, summary_text="An era of peace.",
                         stats_snapshot={"alive": 50})
        d = es.to_dict()
        assert d["tick_start"] == 0
        assert d["tick_end"] == 100
        restored = EraSummary.from_dict(d)
        assert restored.summary_text == "An era of peace."

    def test_fallback_era_summary_small_pop(self):
        """Fallback generates appropriate text for small populations."""
        stats = _make_stats(alive=10, avg_health=0.3)
        text = _fallback_era_summary(0, 100, stats, [])
        assert "Ticks 0" in text
        assert "100" in text
        assert "famine" in text.lower() or "disease" in text.lower() or "ravaged" in text.lower()

    def test_fallback_era_summary_large_pop(self):
        """Fallback generates appropriate text for large populations."""
        stats = _make_stats(alive=200, avg_health=0.8)
        text = _fallback_era_summary(0, 100, stats, ["knowledge_bloom"])
        assert "200" in text or "society" in text.lower() or "flourish" in text.lower()
        assert "knowledge_bloom" in text

    def test_fallback_era_summary_with_techs(self):
        """Fallback includes technology mentions."""
        stats = _make_stats()
        text = _fallback_era_summary(0, 100, stats, [])
        assert "agriculture" in text

    def test_fallback_era_summary_with_wars(self):
        """Fallback includes war mentions."""
        stats = _make_stats(wars=[{"faction_a_id": 1, "faction_b_id": 2}])
        text = _fallback_era_summary(0, 100, stats, [])
        assert "conflict" in text.lower()

    def test_fallback_era_summary_cycle(self):
        """Fallback mentions Matrix cycle when cycle > 1."""
        stats = _make_stats(matrix={"cycle_number": 3, "control_index": 0.5})
        text = _fallback_era_summary(0, 100, stats, [])
        assert "cycle 3" in text.lower()

    def test_generate_era_summary_no_narrator(self):
        """generate_era_summary uses fallback when no narrator provided."""
        stats = _make_stats()
        era = generate_era_summary(0, 100, stats, ["harsh_winter"])
        assert isinstance(era, EraSummary)
        assert era.tick_start == 0
        assert era.tick_end == 100
        assert len(era.summary_text) > 10

    def test_generate_era_summary_extinction(self):
        """Fallback handles extinction (pop=0)."""
        stats = _make_stats(alive=0)
        text = _fallback_era_summary(0, 100, stats, [])
        assert "extinction" in text.lower() or "silence" in text.lower()


# ═══════════════════════════════════════════════════════════════
# TEST: Mythological Narrative Generation
# ═══════════════════════════════════════════════════════════════

class TestMythGeneration:
    def test_myth_creation(self):
        """Myth can be created and serialized."""
        set_myth_id_counter(0)
        m = Myth(id=1, name="The Great Flood", narrative="Waters rose...",
                  source_event="resource depletion", tick_created=100,
                  trigger_type="era_transition")
        d = m.to_dict()
        assert d["name"] == "The Great Flood"
        restored = Myth.from_dict(d)
        assert restored.narrative == "Waters rose..."

    def test_classify_cycle_reset(self):
        """Cycle reset produces a cycle_reset trigger."""
        stats = _make_stats()
        triggers = classify_events_for_myths([], stats, cycle_reset=True)
        types = [t["archetype"] for t in triggers]
        assert "cycle_reset" in types

    def test_classify_resource_depletion(self):
        """High depletion produces a resource_depletion trigger."""
        stats = _make_stats(world={"depleted_cells": 25, "grid_size": 8, "global_techs": []})
        triggers = classify_events_for_myths([], stats)
        types = [t["archetype"] for t in triggers]
        assert "resource_depletion" in types

    def test_classify_wars(self):
        """Active wars produce faction_war triggers."""
        stats = _make_stats(wars=[{"faction_a_id": 1, "faction_b_id": 2}])
        triggers = classify_events_for_myths([], stats)
        types = [t["archetype"] for t in triggers]
        assert "faction_war" in types

    def test_classify_mass_death(self):
        """High death ratio produces mass_death trigger."""
        stats = _make_stats(alive=10, total_died=90)
        triggers = classify_events_for_myths([], stats)
        types = [t["archetype"] for t in triggers]
        assert "mass_death" in types

    def test_classify_anomaly(self):
        """Anomaly presence produces anomaly_emergence trigger."""
        stats = _make_stats(matrix={"cycle_number": 1, "control_index": 0.5, "anomaly_id": 42})
        triggers = classify_events_for_myths([], stats)
        types = [t["archetype"] for t in triggers]
        assert "anomaly_emergence" in types

    def test_classify_tech_breakthrough(self):
        """Tech breakthrough in events produces tech_breakthrough trigger."""
        stats = _make_stats()
        events = [{"name": "breakthrough: agriculture", "tick": 50}]
        triggers = classify_events_for_myths(events, stats)
        types = [t["archetype"] for t in triggers]
        assert "tech_breakthrough" in types

    def test_fallback_myth_cycle_reset(self):
        """Fallback myth for cycle_reset uses correct archetype."""
        set_myth_id_counter(0)
        name, text = _fallback_myth("cycle_reset", "Reality was rewritten")
        assert len(name) > 0
        assert "Reality was rewritten" in text

    def test_fallback_myth_resource_depletion(self):
        """Fallback myth for resource depletion."""
        name, text = _fallback_myth("resource_depletion", "20 cells depleted")
        assert len(name) > 0
        assert "20 cells depleted" in text

    def test_generate_myth_no_narrator(self):
        """generate_myth uses fallback when no narrator."""
        set_myth_id_counter(0)
        myth = generate_myth("cycle_reset", "The world reset", "cycle_reset", 100)
        assert isinstance(myth, Myth)
        assert myth.id == 1
        assert len(myth.name) > 0
        assert len(myth.narrative) > 10
        assert myth.trigger_type == "cycle_reset"


# ═══════════════════════════════════════════════════════════════
# TEST: Faction-Specific Historical Revisionism
# ═══════════════════════════════════════════════════════════════

class TestFactionMyths:
    def test_fallback_myth_with_winning_faction(self):
        """Winning faction gets heroic framing."""
        faction = Faction(id=1, name="Seekers", founder_id=1, formed_at=0)
        faction._myth_won = True
        name, text = _fallback_myth("faction_war", "War broke out", faction)
        assert "Triumph" in name or "Seekers" in name
        assert "victorious" in text.lower() or "triumph" in text.lower() or "Seekers" in text.lower()

    def test_fallback_myth_with_losing_faction(self):
        """Losing faction gets persecution framing."""
        faction = Faction(id=2, name="Guardians", founder_id=2, formed_at=0)
        faction._myth_won = False
        name, text = _fallback_myth("faction_war", "War broke out", faction)
        assert "Persecution" in name or "Guardians" in name
        assert "suffered" in text.lower() or "persecution" in text.lower() or "Guardians" in text.lower()

    def test_generate_faction_myths_produces_multiple(self):
        """generate_faction_myths creates universal + per-faction myths."""
        set_myth_id_counter(0)
        factions = [
            Faction(id=1, name="Seekers", founder_id=1, formed_at=0),
            Faction(id=2, name="Guardians", founder_id=2, formed_at=0),
        ]
        wars = [type('War', (), {"faction_a_id": 1, "faction_b_id": 2,
                                  "casualties_a": 5, "casualties_b": 10})()]
        myths = generate_faction_myths(
            "faction_war", "Two factions clashed", "era_transition", 100,
            factions=factions, wars=wars,
        )
        # Should have 1 universal + 2 faction-specific
        assert len(myths) == 3
        perspectives = {m.faction_perspective for m in myths}
        # Universal has empty perspective, plus heroic and persecution
        assert "" in perspectives
        assert "heroic" in perspectives or "persecution" in perspectives

    def test_faction_myths_different_narratives(self):
        """Different factions get different narrative text for same event."""
        set_myth_id_counter(0)
        factions = [
            Faction(id=1, name="Alpha", founder_id=1, formed_at=0),
            Faction(id=2, name="Beta", founder_id=2, formed_at=0),
        ]
        wars = [type('War', (), {"faction_a_id": 1, "faction_b_id": 2,
                                  "casualties_a": 3, "casualties_b": 8})()]
        myths = generate_faction_myths(
            "faction_war", "Great war", "era_transition", 100,
            factions=factions, wars=wars,
        )
        faction_myths = [m for m in myths if m.faction_id is not None]
        assert len(faction_myths) == 2
        # Different faction IDs
        assert faction_myths[0].faction_id != faction_myths[1].faction_id
        # Different perspectives
        assert faction_myths[0].faction_perspective != faction_myths[1].faction_perspective

    def test_generate_faction_myths_no_factions(self):
        """With no factions, only universal myth is generated."""
        set_myth_id_counter(0)
        myths = generate_faction_myths(
            "cycle_reset", "Reset happened", "cycle_reset", 50,
            factions=[], wars=[],
        )
        assert len(myths) == 1
        assert myths[0].faction_id is None


# ═══════════════════════════════════════════════════════════════
# TEST: Legendary Figures
# ═══════════════════════════════════════════════════════════════

class TestLegendaryFigures:
    def test_legendary_figure_creation(self):
        """LegendaryFigure can be created and serialized."""
        set_legend_id_counter(0)
        lf = LegendaryFigure(
            id=1, agent_id=42, name="Agent #42",
            title="The Awakened One", description="They saw the truth.",
            tick_created=100, legend_type="anomaly",
            original_stats={"awareness": 0.9},
            embellished_stats={"awareness": 1.0},
            discovery_effects={"awareness_boost": 0.05},
        )
        d = lf.to_dict()
        assert d["title"] == "The Awakened One"
        restored = LegendaryFigure.from_dict(d)
        assert restored.agent_id == 42

    def test_identify_anomaly_as_legendary(self):
        """Anomaly agents are identified as legendary candidates."""
        agent = _make_agent(id=1, is_anomaly=True, awareness=0.9)
        candidates = identify_legendary_candidates([agent], set())
        assert len(candidates) == 1
        assert candidates[0][1] == "anomaly"

    def test_identify_prophet_as_legendary(self):
        """High-charisma faction leaders with extreme beliefs become prophets."""
        agent = _make_agent(id=2, charisma=0.8, faction_id=1)
        agent.beliefs = {"individualism": 0.9, "tradition": 0.8,
                          "system_trust": -0.7, "spirituality": 0.9}
        agent.chronicle = [
            ChronicleEntry(tick=10, event_type="faction_join",
                            description="Joined Seekers", details={"faction_name": "Seekers"}),
        ]
        candidates = identify_legendary_candidates([agent], set())
        assert len(candidates) == 1
        assert candidates[0][1] == "prophet"

    def test_identify_warrior_as_legendary(self):
        """Agents with combat history become warrior legends."""
        agent = _make_agent(id=3, aggression=0.8)
        agent.chronicle = [
            ChronicleEntry(tick=5, event_type="first_combat",
                            description="Drew first blood", details={}),
        ]
        agent.memory = [
            {"tick": 10, "event": "Struck down Agent #5"},
            {"tick": 15, "event": "Killed Agent #6"},
        ]
        candidates = identify_legendary_candidates([agent], set())
        assert len(candidates) == 1
        assert candidates[0][1] == "warrior"

    def test_identify_martyr_as_legendary(self):
        """Dead redpilled agents with high awareness become martyrs."""
        agent = _make_agent(id=4, alive=False, redpilled=True, awareness=0.7)
        candidates = identify_legendary_candidates([agent], set())
        assert len(candidates) == 1
        assert candidates[0][1] == "martyr"

    def test_skip_known_legends(self):
        """Already-legendary agents are skipped."""
        agent = _make_agent(id=1, is_anomaly=True)
        candidates = identify_legendary_candidates([agent], {1})
        assert len(candidates) == 0

    def test_create_legendary_figure_fallback(self):
        """create_legendary_figure uses fallback when no narrator."""
        set_legend_id_counter(0)
        agent = _make_agent(id=42, is_anomaly=True, awareness=0.9)
        agent.chronicle = [
            ChronicleEntry(tick=10, event_type="became_anomaly",
                            description="Became The One", details={}),
        ]
        legend = create_legendary_figure(agent, "anomaly", tick=100, cycle_number=2)
        assert isinstance(legend, LegendaryFigure)
        assert legend.id == 1
        assert legend.agent_id == 42
        assert len(legend.title) > 0
        assert len(legend.description) > 10
        assert legend.legend_type == "anomaly"

    def test_legendary_figure_embellishment(self):
        """Embellished stats are amplified beyond original."""
        set_legend_id_counter(0)
        agent = _make_agent(id=5, awareness=0.5, charisma=0.6)
        legend = create_legendary_figure(agent, "prophet", tick=50)
        assert legend.embellished_stats["awareness"] >= legend.original_stats["awareness"]
        assert legend.embellished_stats["charisma"] >= legend.original_stats["charisma"]

    def test_legendary_figure_discovery_effects(self):
        """Discovery effects are set based on legend type."""
        set_legend_id_counter(0)
        agent = _make_agent(id=6, is_anomaly=True, awareness=0.9)
        legend = create_legendary_figure(agent, "anomaly", tick=100)
        assert legend.discovery_effects["awareness_boost"] == 0.08
        assert "system_trust" in legend.discovery_effects["belief_drift"]

    def test_apply_legend_discovery(self):
        """Discovering a legend boosts awareness and drifts beliefs."""
        agent = _make_agent(id=10, awareness=0.2)
        agent.beliefs = {"individualism": 0.0, "tradition": 0.0,
                          "system_trust": 0.5, "spirituality": 0.0}
        legend = LegendaryFigure(
            id=1, agent_id=42, name="Agent #42", title="The One",
            description="...", tick_created=50, legend_type="anomaly",
            discovery_effects={
                "awareness_boost": 0.08,
                "belief_drift": {"system_trust": -0.1, "spirituality": 0.05},
            },
        )
        changes = apply_legend_discovery(agent, legend)
        assert agent.awareness == pytest.approx(0.28, abs=0.01)
        assert agent.beliefs["system_trust"] == pytest.approx(0.4, abs=0.01)
        assert agent.beliefs["spirituality"] == pytest.approx(0.05, abs=0.01)
        assert changes["legend_id"] == 1
        # Memory and chronicle added
        assert any("legend" in m.get("event", "").lower() for m in agent.memory)

    def test_process_legend_discoveries(self):
        """process_legend_discoveries applies discoveries to agents."""
        random.seed(1)  # Ensure deterministic discovery
        agents = [_make_agent(id=i, awareness=0.1) for i in range(50)]
        for a in agents:
            a.beliefs = {"individualism": 0.0, "tradition": 0.0,
                          "system_trust": 0.5, "spirituality": 0.0}
        legend = LegendaryFigure(
            id=1, agent_id=99, name="Agent #99", title="The Prophet",
            description="...", tick_created=50, legend_type="prophet",
            discovery_effects={
                "awareness_boost": 0.03,
                "belief_drift": {"spirituality": 0.1},
            },
        )
        # High discovery chance to ensure at least one hit
        discoveries = process_legend_discoveries(agents, [legend], tick=100,
                                                   discovery_chance=0.5)
        assert len(discoveries) > 0
        # Check that at least one agent got boosted
        boosted = [a for a in agents if a.awareness > 0.1]
        assert len(boosted) > 0


# ═══════════════════════════════════════════════════════════════
# TEST: MythologyState Serialization
# ═══════════════════════════════════════════════════════════════

class TestMythologyState:
    def test_state_roundtrip(self):
        """MythologyState survives to_dict/from_dict roundtrip."""
        set_myth_id_counter(5)
        set_legend_id_counter(3)
        state = MythologyState(
            era_summaries=[EraSummary(0, 100, "Peace era.", {"alive": 50})],
            myths=[Myth(1, "The Flood", "Waters rose.", "depletion", 50, "era_transition")],
            legends=[LegendaryFigure(1, 42, "Agent #42", "The One", "...", 100, "anomaly")],
            last_era_summary_tick=100,
            last_myth_check_tick=50,
            known_legend_agent_ids={42},
        )
        d = state.to_dict()
        assert d["myth_id_counter"] == 5
        assert d["legend_id_counter"] == 3

        restored = MythologyState.from_dict(d)
        assert len(restored.era_summaries) == 1
        assert len(restored.myths) == 1
        assert len(restored.legends) == 1
        assert 42 in restored.known_legend_agent_ids
        assert restored.last_era_summary_tick == 100


# ═══════════════════════════════════════════════════════════════
# TEST: Engine Integration
# ═══════════════════════════════════════════════════════════════

class TestEngineIntegration:
    def test_engine_has_mythology_state(self, cfg):
        """Engine initializes with a MythologyState."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()
        assert isinstance(engine.mythology_state, MythologyState)

    def test_era_summary_generated_after_interval(self, cfg):
        """Era summary is generated after era_summary_interval ticks."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()
        # Run enough ticks to trigger era summary (default 100)
        for _ in range(100):
            result = engine.tick()
        assert len(engine.mythology_state.era_summaries) >= 1
        assert engine.mythology_state.era_summaries[0].tick_end == 100

    def test_mythology_stats_in_tick_result(self, cfg):
        """TickResult includes mythology_stats dict."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()
        result = engine.tick()
        assert hasattr(result, 'mythology_stats')
        assert isinstance(result.mythology_stats, dict)

    def test_myth_generation_on_interval(self, cfg):
        """Myths are generated at myth_check_interval."""
        engine = SimulationEngine(cfg, state=RunState(run_id="test"))
        engine.initialize()
        # Run 50 ticks (default myth check interval)
        for _ in range(50):
            result = engine.tick()
        # Should have generated some myths (depends on event classification)
        assert engine.mythology_state.last_myth_check_tick == 50


# ═══════════════════════════════════════════════════════════════
# TEST: Fallback Legend Templates
# ═══════════════════════════════════════════════════════════════

class TestFallbackLegend:
    def test_fallback_anomaly_legend(self):
        """Anomaly legend mentions awakening or code."""
        agent = _make_agent(id=1, is_anomaly=True)
        agent.chronicle = [
            ChronicleEntry(tick=10, event_type="became_anomaly",
                            description="Became The One", details={}),
        ]
        title, desc = _fallback_legend(agent, "anomaly", cycle_number=1)
        assert len(title) > 0
        assert "Agent #1" in desc

    def test_fallback_prophet_legend(self):
        """Prophet legend mentions teachings or generations."""
        agent = _make_agent(id=2)
        agent.chronicle = [
            ChronicleEntry(tick=5, event_type="faction_join",
                            description="Joined Seekers",
                            details={"faction_name": "Seekers"}),
        ]
        title, desc = _fallback_legend(agent, "prophet", cycle_number=1)
        assert len(title) > 0
        assert "generation" in desc.lower() or "teachings" in desc.lower() or "spoke" in desc.lower()

    def test_fallback_warrior_legend(self):
        """Warrior legend mentions battle or valor."""
        agent = _make_agent(id=3)
        agent.chronicle = [
            ChronicleEntry(tick=5, event_type="first_combat",
                            description="First blood", details={}),
        ]
        title, desc = _fallback_legend(agent, "warrior", cycle_number=1)
        assert len(title) > 0
        assert "battle" in desc.lower() or "legend" in desc.lower() or "stand" in desc.lower() or "Agent #3" in desc

    def test_fallback_martyr_legend(self):
        """Martyr legend mentions sacrifice."""
        agent = _make_agent(id=4, redpilled=True)
        agent.chronicle = [
            ChronicleEntry(tick=10, event_type="red_pill",
                            description="Took the red pill", details={}),
        ]
        title, desc = _fallback_legend(agent, "martyr", cycle_number=1)
        assert len(title) > 0
        assert "sacrifice" in desc.lower() or "gave" in desc.lower() or "pierced" in desc.lower() or "Agent #4" in desc
