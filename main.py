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


def cmd_run(args, cfg: SimConfig, db: SimulationDB):
    # Find latest run or specific run
    run_id = args.run_id
    if not run_id:
        runs = db.list_runs()
        if not runs:
            print(color("No runs found. Create one with: python main.py new", "red"))
            return
        run_id = runs[0]["run_id"]

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


def cmd_eras(args, cfg: SimConfig, db: SimulationDB):
    eras = cfg.list_eras()
    print(color("═══ Available Eras ═══", "green"))
    for e in eras:
        print(f"  {e['name']:<20s} {e['time_period']:<15s} {e['display_name']}")
        print(f"  {'':20s} {e['description']}")
    if not eras:
        print("  No era files found in config/eras/")


def main():
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

    p_status = sub.add_parser("status", help="Show current state")
    p_status.add_argument("--run-id", "-r", default=None)

    sub.add_parser("list-runs", help="List all runs")
    sub.add_parser("scenarios", help="List available scenarios")
    sub.add_parser("eras", help="List available historical eras")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cfg = SimConfig.load(scenario=args.scenario, era=args.era)
    db = SimulationDB(args.db)

    commands = {
        "new": cmd_new, "run": cmd_run, "status": cmd_status,
        "list-runs": cmd_list, "scenarios": cmd_scenarios, "eras": cmd_eras,
    }
    commands[args.command](args, cfg, db)
    db.close()


if __name__ == "__main__":
    main()
