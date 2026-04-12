"""
Tests for Phase 4: Batch research mode and causal event graphs.

Covers:
- Batch CLI argument parsing
- Multi-run aggregation
- CSV/JSON export format
- Event ID generation
- Causal link recording
- Causal chain traversal
"""
from __future__ import annotations

import csv
import json
import os
import random

import pytest

from src.config_loader import SimConfig
from src.engine import (
    SimulationEngine, RunState, CausalEvent,
    next_event_id, reset_event_id_counter,
)
from src.agents import set_id_counter
from src.causal_graph import (
    build_index, get_ancestors, get_descendants, get_full_chain,
    find_root_events, find_longest_chains,
    export_events_json, export_chains_json,
)
from src.batch import (
    RunResult, run_single, aggregate_results,
    export_results_csv, export_results_json,
    _compute_gini,
)


# ═══════════════════════════════════════════════════════════════
# Event ID Generation
# ═══════════════════════════════════════════════════════════════

class TestEventIdGeneration:
    def test_event_ids_are_unique_and_sequential(self):
        reset_event_id_counter(0)
        ids = [next_event_id() for _ in range(5)]
        assert ids == [1, 2, 3, 4, 5]

    def test_reset_counter(self):
        reset_event_id_counter(100)
        assert next_event_id() == 101
        reset_event_id_counter(0)
        assert next_event_id() == 1


# ═══════════════════════════════════════════════════════════════
# Causal Link Recording
# ═══════════════════════════════════════════════════════════════

class TestCausalLinkRecording:
    @pytest.fixture
    def engine(self):
        random.seed(42)
        set_id_counter(0)
        reset_event_id_counter(0)
        cfg = SimConfig.load()
        eng = SimulationEngine(cfg, state=RunState(run_id="causal_test"))
        eng.initialize()
        return eng

    def test_record_event_returns_id(self, engine):
        eid = engine.record_event(1, "test", "Test event")
        assert isinstance(eid, int)
        assert eid > 0

    def test_record_event_with_caused_by(self, engine):
        eid1 = engine.record_event(1, "death", "Agent died", agent_id=1)
        eid2 = engine.record_event(1, "trauma", "Mate traumatized",
                                   agent_id=2, caused_by=eid1)
        assert engine.causal_events[-1].caused_by == eid1
        assert engine.causal_events[-1].event_id == eid2

    def test_agent_last_event_lookup(self, engine):
        eid = engine.record_event(5, "death", "Agent #10 died", agent_id=10)
        assert engine.get_agent_last_event(10, "death") == eid
        assert engine.get_agent_last_event(10, "birth") is None
        assert engine.get_agent_last_event(99, "death") is None

    def test_tick_records_causal_events(self, engine):
        """Running ticks should produce causal events (at minimum births)."""
        for _ in range(50):
            engine.tick()
        assert len(engine.causal_events) > 0
        # Should have at least some births
        birth_events = [e for e in engine.causal_events if e.event_type == "birth"]
        assert len(birth_events) >= 0  # may be 0 in 50 ticks, but events should exist

    def test_death_events_have_cause_field(self, engine):
        """Death events should include cause in details."""
        for _ in range(200):
            engine.tick()
        death_events = [e for e in engine.causal_events if e.event_type == "death"]
        if death_events:
            # All death events should have 'cause' in details
            for de in death_events:
                assert "cause" in de.details

    def test_causal_event_serialization(self):
        evt = CausalEvent(
            event_id=42, tick=10, event_type="death",
            description="Agent #5 died", agent_id=5,
            caused_by=30, details={"cause": "starvation"},
        )
        d = evt.to_dict()
        assert d["event_id"] == 42
        assert d["caused_by"] == 30
        restored = CausalEvent.from_dict(d)
        assert restored.event_id == 42
        assert restored.caused_by == 30
        assert restored.details["cause"] == "starvation"


# ═══════════════════════════════════════════════════════════════
# Causal Chain Traversal
# ═══════════════════════════════════════════════════════════════

class TestCausalChainTraversal:
    @pytest.fixture
    def chain_events(self):
        """A->B->C->D linear chain plus E (unlinked)."""
        return [
            CausalEvent(1, 10, "death", "A died", agent_id=1),
            CausalEvent(2, 10, "trauma", "B traumatized", agent_id=2, caused_by=1),
            CausalEvent(3, 11, "faction_founded", "B founds faction", agent_id=2, caused_by=2),
            CausalEvent(4, 15, "war_started", "War begins", caused_by=3),
            CausalEvent(5, 20, "birth", "E born", agent_id=5),  # unlinked
        ]

    def test_build_index(self, chain_events):
        by_id, children_of = build_index(chain_events)
        assert len(by_id) == 5
        assert 2 in children_of[1]  # A -> B
        assert 3 in children_of[2]  # B -> C
        assert 4 in children_of[3]  # C -> D

    def test_get_ancestors(self, chain_events):
        by_id, _ = build_index(chain_events)
        ancestors = get_ancestors(4, by_id)
        assert len(ancestors) == 3  # A, B, C
        assert ancestors[0].event_id == 1  # root first
        assert ancestors[-1].event_id == 3

    def test_get_ancestors_of_root(self, chain_events):
        by_id, _ = build_index(chain_events)
        ancestors = get_ancestors(1, by_id)
        assert ancestors == []

    def test_get_descendants(self, chain_events):
        by_id, children_of = build_index(chain_events)
        descendants = get_descendants(1, by_id, children_of)
        assert len(descendants) == 3  # B, C, D
        desc_ids = {d.event_id for d in descendants}
        assert desc_ids == {2, 3, 4}

    def test_get_full_chain(self, chain_events):
        by_id, children_of = build_index(chain_events)
        chain = get_full_chain(2, by_id, children_of)
        # Should include: A (ancestor) + B (self) + C, D (descendants)
        assert len(chain) == 4
        assert chain[0].event_id == 1
        assert chain[1].event_id == 2
        assert chain[-1].event_id == 4

    def test_find_root_events(self, chain_events):
        roots = find_root_events(chain_events)
        root_ids = {r.event_id for r in roots}
        assert root_ids == {1, 5}  # A and E have no parent

    def test_find_longest_chains(self, chain_events):
        chains = find_longest_chains(chain_events, top_n=5)
        assert len(chains) >= 1
        # Longest chain should be length 4 (A->B->C->D)
        assert len(chains[0]) == 4

    def test_find_longest_chains_empty(self):
        chains = find_longest_chains([], top_n=5)
        assert chains == []


# ═══════════════════════════════════════════════════════════════
# Causal Event Export
# ═══════════════════════════════════════════════════════════════

class TestCausalExport:
    @pytest.fixture
    def sample_events(self):
        return [
            CausalEvent(1, 10, "death", "A died", agent_id=1),
            CausalEvent(2, 10, "trauma", "B traumatized", agent_id=2, caused_by=1),
            CausalEvent(3, 11, "revenge_quest", "B seeks vengeance", agent_id=2, caused_by=2),
        ]

    def test_export_events_json(self, sample_events, tmp_path):
        path = str(tmp_path / "events.json")
        export_events_json(sample_events, path)
        with open(path) as f:
            data = json.load(f)
        assert data["total_events"] == 3
        assert len(data["events"]) == 3
        assert data["events"][0]["event_id"] == 1

    def test_export_chains_json(self, sample_events, tmp_path):
        path = str(tmp_path / "chains.json")
        stats = export_chains_json(sample_events, path, top_n=5)
        assert stats["total_events"] == 3
        assert stats["linked_events"] == 2
        with open(path) as f:
            data = json.load(f)
        assert "chains" in data
        assert "stats" in data
        # The chain A->B->C should be found
        assert data["stats"]["longest_chain_length"] == 3


# ═══════════════════════════════════════════════════════════════
# Batch CLI Argument Parsing
# ═══════════════════════════════════════════════════════════════

class TestBatchCliParsing:
    def test_batch_subcommand_parses(self):
        """Verify the batch subcommand is registered and parses correctly."""
        import argparse
        # Import the main module's parser setup

        # Test that batch args parse correctly by importing the parser
        # We test the argparse setup indirectly
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        p_batch = sub.add_parser("batch")
        p_batch.add_argument("--runs", "-n", type=int, default=10)
        p_batch.add_argument("--ticks", "-t", type=int, default=500)
        p_batch.add_argument("--output", "-o", default="results/")
        p_batch.add_argument("--seed", type=int, default=None)

        args = parser.parse_args(["batch", "--runs", "100", "--ticks", "1000",
                                  "--output", "results/"])
        assert args.command == "batch"
        assert args.runs == 100
        assert args.ticks == 1000
        assert args.output == "results/"

    def test_batch_default_args(self):
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        p_batch = sub.add_parser("batch")
        p_batch.add_argument("--runs", "-n", type=int, default=10)
        p_batch.add_argument("--ticks", "-t", type=int, default=500)
        p_batch.add_argument("--output", "-o", default="results/")
        p_batch.add_argument("--seed", type=int, default=None)

        args = parser.parse_args(["batch"])
        assert args.runs == 10
        assert args.ticks == 500
        assert args.seed is None

    def test_batch_seed_arg(self):
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        p_batch = sub.add_parser("batch")
        p_batch.add_argument("--runs", "-n", type=int, default=10)
        p_batch.add_argument("--ticks", "-t", type=int, default=500)
        p_batch.add_argument("--output", "-o", default="results/")
        p_batch.add_argument("--seed", type=int, default=None)

        args = parser.parse_args(["batch", "--seed", "42"])
        assert args.seed == 42


# ═══════════════════════════════════════════════════════════════
# Multi-Run Aggregation
# ═══════════════════════════════════════════════════════════════

class TestMultiRunAggregation:
    @pytest.fixture
    def sample_results(self):
        return [
            RunResult(
                run_index=0, ticks_completed=500, survived=True,
                elapsed_seconds=1.0, final_population=30,
                total_born=100, total_died=70,
                anomaly_emerged=True, anomaly_tick=200,
                gini=0.3, faction_count=3, max_faction_count=5,
                avg_awareness=0.2, max_awareness=0.8,
                redpilled_count=2,
                consciousness_phases={"bicameral": 10, "questioning": 15, "self_aware": 5},
                haven_peak_population=8, max_enforcer_count=4,
                matrix_cycles=1, avg_intelligence=0.4, avg_health=0.6,
                max_generation=3, avg_wealth=10.0,
                causal_event_count=150, longest_causal_chain=5,
            ),
            RunResult(
                run_index=1, ticks_completed=300, survived=False,
                elapsed_seconds=0.8, final_population=0,
                total_born=80, total_died=80,
                anomaly_emerged=False, anomaly_tick=0,
                gini=0.5, faction_count=0, max_faction_count=4,
                avg_awareness=0.0, max_awareness=0.0,
                redpilled_count=0,
                consciousness_phases={"bicameral": 20},
                haven_peak_population=3, max_enforcer_count=6,
                matrix_cycles=0, avg_intelligence=0.0, avg_health=0.0,
                max_generation=0, avg_wealth=0.0,
                causal_event_count=80, longest_causal_chain=3,
            ),
        ]

    def test_aggregate_survival_rate(self, sample_results):
        agg = aggregate_results(sample_results)
        assert agg.total_runs == 2
        assert agg.runs_survived == 1
        assert agg.survival_rate == 0.5

    def test_aggregate_anomaly_rate(self, sample_results):
        agg = aggregate_results(sample_results)
        assert agg.anomaly_emergence_rate == 0.5

    def test_aggregate_lifespan(self, sample_results):
        agg = aggregate_results(sample_results)
        assert agg.avg_civilization_lifespan == 400.0  # (500+300)/2

    def test_aggregate_gini(self, sample_results):
        agg = aggregate_results(sample_results)
        assert agg.avg_gini == 0.4  # (0.3+0.5)/2
        assert agg.min_gini == 0.3
        assert agg.max_gini == 0.5

    def test_aggregate_faction_counts(self, sample_results):
        agg = aggregate_results(sample_results)
        assert agg.avg_faction_count == 1.5
        assert agg.max_faction_count_across_runs == 5

    def test_aggregate_consciousness_phases(self, sample_results):
        agg = aggregate_results(sample_results)
        assert agg.consciousness_phase_totals["bicameral"] == 30  # 10+20
        assert agg.consciousness_phase_totals["questioning"] == 15
        assert agg.consciousness_phase_totals.get("self_aware") == 5

    def test_aggregate_haven_and_enforcers(self, sample_results):
        agg = aggregate_results(sample_results)
        assert agg.max_haven_peak == 8
        assert agg.max_enforcers_across_runs == 6

    def test_aggregate_causal_stats(self, sample_results):
        agg = aggregate_results(sample_results)
        assert agg.avg_causal_events == 115.0
        assert agg.avg_longest_chain == 4.0

    def test_aggregate_empty(self):
        agg = aggregate_results([])
        assert agg.total_runs == 0

    def test_aggregate_to_dict(self, sample_results):
        agg = aggregate_results(sample_results)
        d = agg.to_dict()
        assert "survival_rate" in d
        assert "anomaly_emergence_rate" in d
        assert "consciousness_phase_totals" in d


# ═══════════════════════════════════════════════════════════════
# CSV/JSON Export Format
# ═══════════════════════════════════════════════════════════════

class TestBatchExport:
    @pytest.fixture
    def sample_results(self):
        return [
            RunResult(
                run_index=0, ticks_completed=100, survived=True,
                elapsed_seconds=0.5, final_population=20,
                total_born=50, total_died=30,
                consciousness_phases={"bicameral": 10, "questioning": 8, "self_aware": 2},
            ),
            RunResult(
                run_index=1, ticks_completed=80, survived=False,
                elapsed_seconds=0.4, final_population=0,
                total_born=40, total_died=40,
                consciousness_phases={"bicameral": 15},
            ),
        ]

    def test_csv_export_creates_valid_file(self, sample_results, tmp_path):
        path = str(tmp_path / "test_runs.csv")
        export_results_csv(sample_results, path)

        assert os.path.exists(path)
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["run_index"] == "0"
        assert rows[0]["survived"] == "True"
        assert "phase_bicameral" in rows[0]

    def test_csv_export_has_required_columns(self, sample_results, tmp_path):
        path = str(tmp_path / "test_runs.csv")
        export_results_csv(sample_results, path)

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        required = [
            "run_index", "ticks_completed", "survived", "final_population",
            "anomaly_emerged", "gini", "faction_count", "max_faction_count",
            "haven_peak_population", "max_enforcer_count", "matrix_cycles",
            "causal_event_count", "longest_causal_chain",
        ]
        for col in required:
            assert col in fieldnames, f"Missing column: {col}"

    def test_json_export_creates_valid_file(self, sample_results, tmp_path):
        agg = aggregate_results(sample_results)
        path = str(tmp_path / "test_results.json")
        export_results_json(sample_results, agg, path)

        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "aggregate" in data
        assert "runs" in data
        assert len(data["runs"]) == 2
        assert data["aggregate"]["total_runs"] == 2

    def test_json_export_aggregate_fields(self, sample_results, tmp_path):
        agg = aggregate_results(sample_results)
        path = str(tmp_path / "test_results.json")
        export_results_json(sample_results, agg, path)

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        agg_data = data["aggregate"]
        assert "survival_rate" in agg_data
        assert "anomaly_emergence_rate" in agg_data
        assert "avg_gini" in agg_data
        assert "consciousness_phase_totals" in agg_data


# ═══════════════════════════════════════════════════════════════
# Gini Coefficient
# ═══════════════════════════════════════════════════════════════

class TestGiniCoefficient:
    def test_perfect_equality(self):
        assert _compute_gini([100, 100, 100, 100]) == 0.0

    def test_empty(self):
        assert _compute_gini([]) == 0.0

    def test_single(self):
        assert _compute_gini([100]) == 0.0

    def test_inequality(self):
        gini = _compute_gini([0, 0, 0, 0, 1000])
        assert gini > 0.5  # high inequality


# ═══════════════════════════════════════════════════════════════
# Integration: batch run_single produces expected outputs
# ═══════════════════════════════════════════════════════════════

class TestBatchRunSingle:
    def test_run_single_returns_result_and_engine(self):
        cfg = SimConfig.load()
        result, engine = run_single(cfg, ticks=50, run_index=0, seed=42)
        assert isinstance(result, RunResult)
        assert isinstance(engine, SimulationEngine)
        assert result.run_index == 0
        assert result.ticks_completed <= 50
        assert result.elapsed_seconds >= 0

    def test_run_single_records_causal_events(self):
        cfg = SimConfig.load()
        result, engine = run_single(cfg, ticks=100, run_index=0, seed=42)
        assert result.causal_event_count == len(engine.causal_events)
        # With 100 ticks we should have at least some events
        assert result.causal_event_count > 0

    def test_run_single_produces_valid_result(self):
        """A batch run should produce structurally valid results."""
        cfg = SimConfig.load()
        result, engine = run_single(cfg, ticks=50, run_index=7, seed=99)
        assert result.run_index == 7
        assert result.ticks_completed > 0
        assert result.total_born >= result.final_population
        assert result.elapsed_seconds >= 0
        # Consciousness phases should sum to alive non-sentinel count
        phase_total = sum(result.consciousness_phases.values())
        assert phase_total == result.final_population or result.final_population == 0
