#!/usr/bin/env python3
"""
Cognitive Matrix v2 — CLI Entry Point
"""
from __future__ import annotations

import argparse
import json
import sys
import signal

from src.config_loader import SimConfig
from src.engine import SimulationEngine, RunState
from src.narrator import Narrator
from src.persistence import SimulationDB
from src.agents import set_id_counter
from src.batch import (
    run_single as batch_run_single,
    aggregate_results, export_results_csv, export_results_json,
)
from src.causal_graph import export_events_json, export_chains_json


def color(text: str, code: str) -> str:
    codes = {"green": "32", "red": "31", "yellow": "33", "cyan": "36", "dim": "90", "bold": "1"}
    return f"\033[{codes.get(code, '0')}m{text}\033[0m"


def cmd_new(args, cfg: SimConfig, db: SimulationDB):
    run_id = db.create_run(cfg)
    engine = SimulationEngine(cfg, state=RunState(run_id=run_id))
    engine.initialize()
    db.save_snapshot(run_id, engine)
    db.flush()
    alive = engine.get_alive_agents()
    print(color(f"✓ New simulation: {run_id}", "green"))
    print(f"  Population: {len(alive)} agents on {cfg.environment.grid_size}x{cfg.environment.grid_size} grid")
    era_str = f"era={args.era}" if args.era else ""
    scn_str = f"scenario={args.scenario}" if args.scenario else ""
    cfg_str = ", ".join(filter(None, [era_str, scn_str])) or "default"
    print(f"  Config: {cfg_str}")
    if cfg.era_metadata:
        meta = cfg.era_metadata
        print(f"  Era: {meta.get('name', '?')} ({meta.get('time_period', '?')}) — {meta.get('region', '?')}")
        pre_tech = meta.get('pre_unlocked_tech', [])
        if pre_tech:
            print(f"  Pre-unlocked tech: {', '.join(pre_tech)}")


def parse_overrides(pairs: list[str]) -> dict:
    """Parse key=value pairs into nested dict for config override."""
    import yaml
    result = {}
    for pair in pairs:
        if "=" not in pair:
            print(f"Warning: ignoring invalid override '{pair}' (expected key=value)")
            continue
        path, value = pair.split("=", 1)
        keys = path.split(".")
        d = result
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        # Auto-type the value
        d[keys[-1]] = yaml.safe_load(value)
    return result


def cmd_export(args, cfg: SimConfig, db: SimulationDB):
    """Export simulation data to CSV or JSON."""
    run_id = args.run_id
    if not run_id:
        runs = db.list_runs()
        if not runs:
            print(color("No runs found.", "red"))
            return
        run_id = runs[0]["run_id"]

    fmt = args.format
    output = args.output

    if fmt == "csv":
        output = output or f"output/export_{run_id}"
        db.export_run_csv(run_id, output)
        print(color(f"Exported CSV to {output}/", "green"))
    else:
        output = output or f"output/export_{run_id}.json"
        db.export_run_json(run_id, output)
        print(color(f"Exported JSON to {output}", "green"))


def cmd_run(args, cfg: SimConfig, db: SimulationDB):
    # Find latest run or specific run
    run_id = args.run_id
    if not run_id:
        runs = db.list_runs()
        if not runs:
            print(color("No runs found. Create one with: python main.py new", "red"))
            return
        run_id = runs[0]["run_id"]

    # Apply CLI overrides
    if args.overrides:
        override_dict = parse_overrides(args.overrides)
        cfg = cfg.override(override_dict)

    engine = db.load_latest_snapshot(run_id, cfg)
    if not engine:
        print(color(f"Cannot load run {run_id}", "red"))
        return

    narrator = Narrator.from_config(cfg)
    ticks = args.ticks or cfg.batch.default_ticks
    nc = cfg.narrator

    print(color(f"▶ Running {ticks} ticks on {run_id} (from tick {engine.state.current_tick})", "cyan"))
    print(f"  Narrator: {narrator.provider_name}")

    # Graceful stop on Ctrl+C
    stopped = False
    def handle_sigint(sig, frame):
        nonlocal stopped
        stopped = True
        print(color("\n⏹ Stopping gracefully...", "yellow"))
    signal.signal(signal.SIGINT, handle_sigint)

    for i in range(ticks):
        if stopped:
            break

        result = engine.tick()
        db.save_tick_stats(run_id, result)

        # World events
        if result.tick % nc.event_interval == 0 and result.alive_count > 0:
            summary = engine.get_population_summary()
            event = narrator.generate_event(summary)
            if event:
                engine.queue_event(event)
                db.save_event(run_id, event)

        # Narration
        if result.tick % nc.narration_interval == 0 and result.alive_count > 0:
            summary = engine.get_population_summary()
            text = narrator.narrate(summary)
            if text:
                db.save_narrative(run_id, result.tick, text)

        # Snapshot
        if result.tick % cfg.persistence.snapshot_interval == 0:
            db.save_snapshot(run_id, engine)
            db.flush()

        # Progress
        if (i + 1) % cfg.batch.progress_interval == 0:
            bt_str = f" 🔬 {','.join(result.breakthroughs)}" if result.breakthroughs else ""
            print(f"  t={result.tick:>5d}  pop={result.alive_count:<4d}  "
                  f"hp={result.avg_health:.2f}  iq={result.avg_intelligence:.3f}  "
                  f"gen={result.avg_generation:.1f}  +{result.births}/-{result.deaths}  "
                  f"bonds+{result.bonds_formed}/-{result.bonds_decayed}{bt_str}")

        if result.alive_count == 0:
            print(color(f"  ☠ Extinction at tick {result.tick}", "red"))
            break

    db.save_snapshot(run_id, engine)
    db.flush()
    print(color(f"✓ Saved at tick {engine.state.current_tick}", "green"))


def cmd_status(args, cfg: SimConfig, db: SimulationDB):
    run_id = args.run_id
    if not run_id:
        runs = db.list_runs()
        if not runs:
            print("No runs.")
            return
        run_id = runs[0]["run_id"]

    engine = db.load_latest_snapshot(run_id, cfg)
    if not engine:
        print(f"Cannot load {run_id}")
        return

    s = engine.get_population_summary()
    print(color(f"═══ Run {run_id} — Tick {s['tick']} ═══", "green"))
    print(f"  Population: {s['alive']} alive ({s['total_born']} born, {s['total_died']} dead)")
    print(f"  Phases: {json.dumps(s['phases'])}")
    print(f"  Avg Health: {s['avg_health']:.3f}  Avg Intelligence: {s['avg_intelligence']:.3f}")
    print(f"  Max Generation: {s['max_generation']}")
    print(f"  Cultural Floors: {json.dumps(s['cultural_floors'])}")
    w = s.get("world", {})
    print(f"  World: {w.get('avg_resources', '?')} avg res, {w.get('depleted_cells', 0)} depleted")
    print(f"  Technologies: {w.get('global_techs', [])}")
    if s.get("protagonist_ids"):
        print(f"  Protagonists: {s['protagonist_ids']}")


def cmd_list(args, cfg: SimConfig, db: SimulationDB):
    runs = db.list_runs()
    if not runs:
        print("No runs.")
        return
    print(color("═══ Simulation Runs ═══", "green"))
    for r in runs:
        print(f"  {r['run_id']}  tick={r['latest_tick']:<5d}  created={r['created_at']}")


def cmd_scenarios(args, cfg: SimConfig, db: SimulationDB):
    scenarios = cfg.list_scenarios()
    print(color("═══ Available Scenarios ═══", "green"))
    for s in scenarios:
        print(f"  {s['name']:<20s} {s['description']}")
    if not scenarios:
        print("  No scenario files found in config/scenarios/")


def cmd_batch(args, cfg: SimConfig, db: SimulationDB):
    """Run multiple headless simulations for research analysis."""
    import os

    runs = args.runs
    ticks = args.ticks
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    # Force LLM off for speed
    cfg = cfg.override({"narrator": {"enabled": False}})

    print(color(f"▶ Batch research mode: {runs} runs x {ticks} ticks", "cyan"))
    print(f"  Output: {output_dir}/")
    print(f"  LLM: disabled (headless)")
    print()

    results = []
    last_engine = None
    for i in range(runs):
        seed = args.seed + i if args.seed is not None else None
        print(f"  [{i + 1}/{runs}] ", end="", flush=True)
        run_result, engine = batch_run_single(cfg, ticks, i, seed=seed)
        results.append(run_result)
        last_engine = engine
        status = "survived" if run_result.survived else f"extinct@t{run_result.ticks_completed}"
        print(f"{status}  pop={run_result.final_population}  "
              f"factions={run_result.faction_count}  "
              f"gini={run_result.gini:.3f}  "
              f"events={run_result.causal_event_count}  "
              f"t={run_result.elapsed_seconds}s")

    # Aggregate
    agg = aggregate_results(results)

    # Export per-run CSV
    csv_path = os.path.join(output_dir, "batch_runs.csv")
    export_results_csv(results, csv_path)
    print(color(f"\n✓ Per-run CSV: {csv_path}", "green"))

    # Export aggregate JSON
    json_path = os.path.join(output_dir, "batch_aggregate.json")
    export_results_json(results, agg, json_path)
    print(color(f"✓ Aggregate JSON: {json_path}", "green"))

    # Export causal events from last run as example
    if last_engine and last_engine.causal_events:
        events_path = os.path.join(output_dir, "causal_events_last_run.json")
        export_events_json(last_engine.causal_events, events_path)
        chains_path = os.path.join(output_dir, "causal_chains_last_run.json")
        chain_stats = export_chains_json(last_engine.causal_events, chains_path)
        print(color(f"✓ Causal events: {events_path}", "green"))
        print(color(f"✓ Causal chains: {chains_path} ({chain_stats['chains_found']} chains, longest={chain_stats['longest_chain_length']})", "green"))

    # Print summary
    print(color(f"\n═══ Aggregate Results ({runs} runs) ═══", "cyan"))
    print(f"  Survival rate:         {agg.survival_rate:.1%}")
    print(f"  Anomaly emergence:     {agg.anomaly_emergence_rate:.1%}")
    print(f"  Avg lifespan:          {agg.avg_civilization_lifespan:.0f} ticks")
    print(f"  Avg Gini:              {agg.avg_gini:.3f} (range {agg.min_gini:.3f}-{agg.max_gini:.3f})")
    print(f"  Avg factions:          {agg.avg_faction_count:.1f} (max {agg.max_faction_count_across_runs})")
    print(f"  Avg Haven peak:        {agg.avg_haven_peak:.1f} (max {agg.max_haven_peak})")
    print(f"  Avg max Enforcers:     {agg.avg_max_enforcers:.1f} (max {agg.max_enforcers_across_runs})")
    print(f"  Avg matrix cycles:     {agg.avg_matrix_cycles:.1f}")
    print(f"  Consciousness phases:  {agg.consciousness_phase_totals}")
    print(f"  Avg causal events:     {agg.avg_causal_events:.0f}")
    print(f"  Avg longest chain:     {agg.avg_longest_chain:.1f}")


def cmd_eras(args, cfg: SimConfig, db: SimulationDB):
    eras = cfg.list_eras()
    print(color("═══ Available Eras ═══", "green"))
    for e in eras:
        print(f"  {e['name']:<20s} {e['time_period']:<15s} {e['display_name']}")
        print(f"  {'':20s} {e['description']}")
    if not eras:
        print("  No era files found in config/eras/")


def main():
    # Fix Unicode output on Windows terminals using cp1252 encoding
    import io
    if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description="Cognitive Matrix v2")
    parser.add_argument("--scenario", "-s", default=None, help="Scenario name (without .yaml)")
    parser.add_argument("--era", "-e", default=None,
                        help="Era name (without .yaml) — historically-grounded config preset")
    parser.add_argument("--db", default="output/simulation.db", help="Database path")

    sub = parser.add_subparsers(dest="command")

    p_new = sub.add_parser("new", help="Create new simulation")

    p_run = sub.add_parser("run", help="Run batch of ticks")
    p_run.add_argument("--ticks", "-t", type=int, default=None)
    p_run.add_argument("--run-id", "-r", default=None)
    p_run.add_argument("--set", nargs="*", default=[], dest="overrides",
                        help="Override config: --set key=value ...")

    p_status = sub.add_parser("status", help="Show current state")
    p_status.add_argument("--run-id", "-r", default=None)

    sub.add_parser("list-runs", help="List all runs")
    sub.add_parser("scenarios", help="List available scenarios")
    sub.add_parser("eras", help="List available historical eras")

    p_batch = sub.add_parser("batch", help="Run headless batch simulations for research")
    p_batch.add_argument("--runs", "-n", type=int, default=10, help="Number of simulation runs")
    p_batch.add_argument("--ticks", "-t", type=int, default=500, help="Ticks per run")
    p_batch.add_argument("--output", "-o", default="results/", help="Output directory")
    p_batch.add_argument("--seed", type=int, default=None,
                         help="Base random seed (run i uses seed+i)")

    p_export = sub.add_parser("export", help="Export simulation data")
    p_export.add_argument("--format", "-f", choices=["csv", "json"], default="csv",
                          help="Export format")
    p_export.add_argument("--run-id", "-r", default=None,
                          help="Run ID (uses latest if omitted)")
    p_export.add_argument("--output", "-o", default=None, help="Output path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cfg = SimConfig.load(scenario=args.scenario, era=args.era)
    db = SimulationDB(args.db)

    commands = {
        "new": cmd_new, "run": cmd_run, "status": cmd_status,
        "list-runs": cmd_list, "scenarios": cmd_scenarios, "eras": cmd_eras,
        "export": cmd_export, "batch": cmd_batch,
    }
    commands[args.command](args, cfg, db)
    db.close()


if __name__ == "__main__":
    main()
