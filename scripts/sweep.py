"""
Parameter sweep tool — run multiple simulations with different parameters
and compare outcomes. Outputs CSV for analysis.

Usage:
    python sweep.py --param environment.harshness --values 0.5,1.0,1.5,2.0 --ticks 200
    python sweep.py --param genetics.mutation_rate --range 0.05,0.3,0.05 --ticks 300
    python sweep.py --sweep-file sweep_config.json --ticks 500

Output: output/sweep_results.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time

from src.config_loader import SimConfig
from src.engine import SimulationEngine, RunState
from src.agents import set_id_counter


def set_nested(d: dict, path: str, value):
    """Set a nested dict value by dotted path."""
    keys = path.split(".")
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def run_single(cfg: SimConfig, ticks: int, label: str) -> dict:
    """Run a single simulation and return summary stats."""
    set_id_counter(0)
    engine = SimulationEngine(cfg, state=RunState(run_id=label))
    engine.initialize()

    start = time.time()
    for _ in range(ticks):
        result = engine.tick()
        if result.alive_count == 0:
            break

    elapsed = time.time() - start
    alive = engine.get_alive_agents()
    non_sentinels = [a for a in alive if not a.is_sentinel]
    n = len(non_sentinels)

    stats = {
        "label": label,
        "ticks_completed": engine.state.current_tick,
        "final_population": n,
        "total_born": engine.state.total_born,
        "total_died": engine.state.total_died,
        "survived": n > 0,
        "elapsed_seconds": round(elapsed, 2),
    }

    if n > 0:
        stats["avg_intelligence"] = round(sum(a.intelligence for a in non_sentinels) / n, 4)
        stats["avg_health"] = round(sum(a.health for a in non_sentinels) / n, 4)
        stats["max_generation"] = max(a.generation for a in non_sentinels)
        stats["avg_wealth"] = round(sum(a.wealth for a in non_sentinels) / n, 3)
        stats["avg_awareness"] = round(sum(a.awareness for a in non_sentinels) / n, 4)
        stats["redpilled_count"] = sum(1 for a in non_sentinels if a.redpilled)
        stats["factions"] = len(engine.factions)
        stats["wars"] = len(engine.wars)
        stats["matrix_cycle"] = engine.matrix_state.cycle_number
        stats["control_index"] = round(engine.matrix_state.control_index, 4)
        # Gini coefficient
        wealth_vals = sorted(a.wealth for a in non_sentinels)
        total_w = sum(wealth_vals)
        if total_w > 0 and n > 1:
            sum_diff = sum(abs(wealth_vals[i] - wealth_vals[j])
                           for i in range(min(n, 50))
                           for j in range(i + 1, min(n, 50)))
            sample_n = min(n, 50)
            stats["gini"] = round(min(1.0, sum_diff / (sample_n ** 2 * (total_w / n))), 4)
        else:
            stats["gini"] = 0.0
        # Cultural floors
        stats["avg_cultural_floor"] = round(
            sum(engine.cultural_memory.skill_floors.values()) / 5, 4
        )
    else:
        stats.update({
            "avg_intelligence": 0, "avg_health": 0, "max_generation": 0,
            "avg_wealth": 0, "avg_awareness": 0, "redpilled_count": 0,
            "factions": 0, "wars": 0, "matrix_cycle": engine.matrix_state.cycle_number,
            "control_index": 1.0, "gini": 0.0, "avg_cultural_floor": 0.0,
        })

    return stats


def main():
    parser = argparse.ArgumentParser(description="Parameter Sweep Tool")
    parser.add_argument("--param", help="Dotted parameter path (e.g., environment.harshness)")
    parser.add_argument("--values", help="Comma-separated values to sweep")
    parser.add_argument("--range", help="start,stop,step for numeric range")
    parser.add_argument("--sweep-file", help="JSON file with sweep config")
    parser.add_argument("--ticks", type=int, default=200, help="Ticks per run")
    parser.add_argument("--repeats", type=int, default=1, help="Repeats per configuration")
    parser.add_argument("--scenario", default=None, help="Base scenario name")
    parser.add_argument("--output", default="output/sweep_results.csv", help="Output CSV path")

    args = parser.parse_args()

    base_cfg = SimConfig.load(scenario=args.scenario)

    # Build sweep configurations
    sweep_configs = []

    if args.sweep_file:
        with open(args.sweep_file, "r") as f:
            sweep_data = json.load(f)
        for entry in sweep_data:
            overrides = entry.get("overrides", {})
            label = entry.get("label", str(overrides))
            sweep_configs.append((label, overrides))

    elif args.param:
        values = []
        if args.values:
            for v in args.values.split(","):
                try:
                    values.append(float(v))
                except ValueError:
                    values.append(v)
        elif args.range:
            parts = [float(x) for x in args.range.split(",")]
            start, stop, step = parts[0], parts[1], parts[2]
            v = start
            while v <= stop + step * 0.01:
                values.append(round(v, 6))
                v += step

        for val in values:
            overrides = {}
            set_nested(overrides, args.param, val)
            sweep_configs.append((f"{args.param}={val}", overrides))

    else:
        parser.error("Provide --param with --values/--range, or --sweep-file")

    # Run sweep
    all_results = []
    total = len(sweep_configs) * args.repeats
    print(f"Running {total} simulations ({len(sweep_configs)} configs x {args.repeats} repeats)")
    print(f"  Ticks per run: {args.ticks}")
    print(f"  Output: {args.output}")
    print()

    for i, (label, overrides) in enumerate(sweep_configs):
        cfg = base_cfg.override(overrides) if overrides else base_cfg
        for rep in range(args.repeats):
            run_label = f"{label}_r{rep}" if args.repeats > 1 else label
            print(f"  [{i * args.repeats + rep + 1}/{total}] {run_label}...", end=" ", flush=True)
            stats = run_single(cfg, args.ticks, run_label)
            stats["param_value"] = label
            stats["repeat"] = rep
            all_results.append(stats)
            print(f"pop={stats['final_population']}, "
                  f"gen={stats['max_generation']}, "
                  f"iq={stats['avg_intelligence']:.3f}, "
                  f"t={stats['elapsed_seconds']}s")

    # Write CSV
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    if all_results:
        fieldnames = list(all_results[0].keys())
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
        print(f"\nResults written to {args.output}")
    else:
        print("No results generated.")


if __name__ == "__main__":
    main()
