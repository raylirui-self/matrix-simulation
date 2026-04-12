"""
Batch research mode — run many headless simulations and aggregate stats.

Usage (via main.py):
    python main.py batch --runs 100 --ticks 1000 --output results/

Aggregated metrics:
    - Anomaly emergence rate
    - Avg civilization lifespan (ticks until extinction, or full run)
    - Gini coefficient distributions
    - Faction count distributions
    - Consciousness phase distributions
    - Haven population peaks
    - Enforcer swarm sizes
    - Causal event chain statistics
"""
from __future__ import annotations

import csv
import json
import os
import random
import time
from dataclasses import dataclass, field

from src.config_loader import SimConfig
from src.engine import SimulationEngine, RunState, reset_event_id_counter
from src.agents import set_id_counter
from src.causal_graph import export_chains_json, export_events_json


@dataclass
class RunResult:
    """Stats from a single headless run."""
    run_index: int
    ticks_completed: int
    survived: bool
    elapsed_seconds: float
    final_population: int
    total_born: int
    total_died: int
    # Aggregatable stats
    anomaly_emerged: bool = False
    anomaly_tick: int = 0
    gini: float = 0.0
    faction_count: int = 0
    max_faction_count: int = 0
    avg_awareness: float = 0.0
    max_awareness: float = 0.0
    redpilled_count: int = 0
    consciousness_phases: dict = field(default_factory=dict)
    haven_peak_population: int = 0
    max_enforcer_count: int = 0
    matrix_cycles: int = 0
    avg_intelligence: float = 0.0
    avg_health: float = 0.0
    max_generation: int = 0
    avg_wealth: float = 0.0
    causal_event_count: int = 0
    longest_causal_chain: int = 0

    def to_dict(self) -> dict:
        d = {
            "run_index": self.run_index,
            "ticks_completed": self.ticks_completed,
            "survived": self.survived,
            "elapsed_seconds": self.elapsed_seconds,
            "final_population": self.final_population,
            "total_born": self.total_born,
            "total_died": self.total_died,
            "anomaly_emerged": self.anomaly_emerged,
            "anomaly_tick": self.anomaly_tick,
            "gini": self.gini,
            "faction_count": self.faction_count,
            "max_faction_count": self.max_faction_count,
            "avg_awareness": self.avg_awareness,
            "max_awareness": self.max_awareness,
            "redpilled_count": self.redpilled_count,
            "haven_peak_population": self.haven_peak_population,
            "max_enforcer_count": self.max_enforcer_count,
            "matrix_cycles": self.matrix_cycles,
            "avg_intelligence": self.avg_intelligence,
            "avg_health": self.avg_health,
            "max_generation": self.max_generation,
            "avg_wealth": self.avg_wealth,
            "causal_event_count": self.causal_event_count,
            "longest_causal_chain": self.longest_causal_chain,
        }
        # Flatten consciousness phases
        for phase, count in self.consciousness_phases.items():
            d[f"phase_{phase}"] = count
        return d


def _compute_gini(wealth_values: list[float]) -> float:
    """Compute Gini coefficient from a list of wealth values."""
    n = len(wealth_values)
    if n < 2:
        return 0.0
    vals = sorted(wealth_values)
    total = sum(vals)
    if total <= 0:
        return 0.0
    # Use sample for performance (same approach as sweep.py)
    sample = vals[:50] if n > 50 else vals
    sn = len(sample)
    sum_diff = sum(
        abs(sample[i] - sample[j])
        for i in range(sn) for j in range(i + 1, sn)
    )
    return min(1.0, sum_diff / (sn ** 2 * (total / n)))


def run_single(cfg: SimConfig, ticks: int, run_index: int,
               seed: int | None = None) -> tuple[RunResult, SimulationEngine]:
    """Run a single headless simulation.

    Returns (RunResult, engine) — engine is kept for causal event export.
    """
    if seed is not None:
        random.seed(seed)
    set_id_counter(0)
    reset_event_id_counter(0)

    engine = SimulationEngine(cfg, state=RunState(run_id=f"batch_{run_index}"))
    engine.initialize()

    start = time.time()
    max_factions = 0
    haven_peak = 0
    max_enforcers = 0
    anomaly_tick = 0
    anomaly_emerged = False

    for _ in range(ticks):
        result = engine.tick()

        # Track peaks during simulation
        faction_count = len(engine.factions)
        max_factions = max(max_factions, faction_count)

        enforcer_count = sum(1 for a in engine.get_alive_agents() if a.is_enforcer)
        max_enforcers = max(max_enforcers, enforcer_count)

        if engine.haven_state:
            haven_pop = len([a for a in engine.agents if a.alive and a.location == "haven"])
            haven_peak = max(haven_peak, haven_pop)

        if engine.matrix_state.anomaly_id and not anomaly_emerged:
            anomaly_emerged = True
            anomaly_tick = result.tick

        if result.alive_count == 0:
            break

    elapsed = time.time() - start
    alive = engine.get_alive_agents()
    non_sentinels = [a for a in alive if not a.is_sentinel]
    n = len(non_sentinels)

    # Consciousness phase distribution
    phases: dict[str, int] = {}
    for a in non_sentinels:
        phases[a.consciousness_phase] = phases.get(a.consciousness_phase, 0) + 1

    # Causal chain stats
    from src.causal_graph import find_longest_chains
    longest_chains = find_longest_chains(engine.causal_events, top_n=1)
    longest_chain_len = len(longest_chains[0]) if longest_chains else 0

    run_result = RunResult(
        run_index=run_index,
        ticks_completed=engine.state.current_tick,
        survived=n > 0,
        elapsed_seconds=round(elapsed, 2),
        final_population=n,
        total_born=engine.state.total_born,
        total_died=engine.state.total_died,
        anomaly_emerged=anomaly_emerged,
        anomaly_tick=anomaly_tick,
        gini=round(_compute_gini([a.wealth for a in non_sentinels]), 4) if n > 1 else 0.0,
        faction_count=len(engine.factions),
        max_faction_count=max_factions,
        avg_awareness=round(sum(a.awareness for a in non_sentinels) / n, 4) if n else 0.0,
        max_awareness=round(max((a.awareness for a in non_sentinels), default=0.0), 4),
        redpilled_count=sum(1 for a in non_sentinels if a.redpilled),
        consciousness_phases=phases,
        haven_peak_population=haven_peak,
        max_enforcer_count=max_enforcers,
        matrix_cycles=engine.matrix_state.cycle_number,
        avg_intelligence=round(sum(a.intelligence for a in non_sentinels) / n, 4) if n else 0.0,
        avg_health=round(sum(a.health for a in non_sentinels) / n, 4) if n else 0.0,
        max_generation=max((a.generation for a in non_sentinels), default=0),
        avg_wealth=round(sum(a.wealth for a in non_sentinels) / n, 3) if n else 0.0,
        causal_event_count=len(engine.causal_events),
        longest_causal_chain=longest_chain_len,
    )

    return run_result, engine


@dataclass
class AggregateStats:
    """Aggregated stats across multiple batch runs."""
    total_runs: int = 0
    runs_survived: int = 0
    survival_rate: float = 0.0
    anomaly_emergence_rate: float = 0.0
    avg_civilization_lifespan: float = 0.0
    avg_gini: float = 0.0
    min_gini: float = 0.0
    max_gini: float = 0.0
    avg_faction_count: float = 0.0
    max_faction_count_across_runs: int = 0
    avg_haven_peak: float = 0.0
    max_haven_peak: int = 0
    avg_max_enforcers: float = 0.0
    max_enforcers_across_runs: int = 0
    avg_matrix_cycles: float = 0.0
    consciousness_phase_totals: dict = field(default_factory=dict)
    avg_causal_events: float = 0.0
    avg_longest_chain: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "runs_survived": self.runs_survived,
            "survival_rate": round(self.survival_rate, 4),
            "anomaly_emergence_rate": round(self.anomaly_emergence_rate, 4),
            "avg_civilization_lifespan": round(self.avg_civilization_lifespan, 2),
            "avg_gini": round(self.avg_gini, 4),
            "min_gini": round(self.min_gini, 4),
            "max_gini": round(self.max_gini, 4),
            "avg_faction_count": round(self.avg_faction_count, 2),
            "max_faction_count_across_runs": self.max_faction_count_across_runs,
            "avg_haven_peak": round(self.avg_haven_peak, 2),
            "max_haven_peak": self.max_haven_peak,
            "avg_max_enforcers": round(self.avg_max_enforcers, 2),
            "max_enforcers_across_runs": self.max_enforcers_across_runs,
            "avg_matrix_cycles": round(self.avg_matrix_cycles, 2),
            "consciousness_phase_totals": self.consciousness_phase_totals,
            "avg_causal_events": round(self.avg_causal_events, 2),
            "avg_longest_chain": round(self.avg_longest_chain, 2),
        }


def aggregate_results(results: list[RunResult]) -> AggregateStats:
    """Compute aggregate statistics across multiple run results."""
    n = len(results)
    if n == 0:
        return AggregateStats()

    survived = sum(1 for r in results if r.survived)
    anomalies = sum(1 for r in results if r.anomaly_emerged)
    ginis = [r.gini for r in results]

    phase_totals: dict[str, int] = {}
    for r in results:
        for phase, count in r.consciousness_phases.items():
            phase_totals[phase] = phase_totals.get(phase, 0) + count

    return AggregateStats(
        total_runs=n,
        runs_survived=survived,
        survival_rate=survived / n,
        anomaly_emergence_rate=anomalies / n,
        avg_civilization_lifespan=sum(r.ticks_completed for r in results) / n,
        avg_gini=sum(ginis) / n,
        min_gini=min(ginis),
        max_gini=max(ginis),
        avg_faction_count=sum(r.faction_count for r in results) / n,
        max_faction_count_across_runs=max(r.max_faction_count for r in results),
        avg_haven_peak=sum(r.haven_peak_population for r in results) / n,
        max_haven_peak=max(r.haven_peak_population for r in results),
        avg_max_enforcers=sum(r.max_enforcer_count for r in results) / n,
        max_enforcers_across_runs=max(r.max_enforcer_count for r in results),
        avg_matrix_cycles=sum(r.matrix_cycles for r in results) / n,
        consciousness_phase_totals=phase_totals,
        avg_causal_events=sum(r.causal_event_count for r in results) / n,
        avg_longest_chain=sum(r.longest_causal_chain for r in results) / n,
    )


def export_results_csv(results: list[RunResult], path: str) -> None:
    """Export per-run results to CSV."""
    if not results:
        return
    rows = [r.to_dict() for r in results]
    fieldnames = list(rows[0].keys())
    # Gather all phase columns across runs
    all_keys: set[str] = set()
    for row in rows:
        all_keys.update(row.keys())
    for key in sorted(all_keys):
        if key not in fieldnames:
            fieldnames.append(key)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_results_json(results: list[RunResult], aggregate: AggregateStats,
                        path: str) -> None:
    """Export full results + aggregate to JSON."""
    data = {
        "aggregate": aggregate.to_dict(),
        "runs": [r.to_dict() for r in results],
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
