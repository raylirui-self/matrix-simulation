"""Handlers for god mode, agent actions, cell actions, and event injection."""
from __future__ import annotations

import random

import streamlit as st

from src.agents import SKILL_NAMES, create_agent
from src.engine import WorldEvent


def handle_new_sim(cfg, db):
    """Create a new simulation."""
    from src.engine import SimulationEngine, RunState
    run_id = db.create_run(cfg)
    engine = SimulationEngine(cfg, state=RunState(run_id=run_id))
    engine.initialize()
    db.save_snapshot(run_id, engine)
    db.flush()
    st.session_state.engine = engine
    st.session_state.run_id = run_id
    st.session_state.tick_history = []
    st.session_state.events_log = []
    st.session_state.narratives_log = []
    st.session_state.protagonist_thoughts = []
    st.session_state.activity_feed = [("event", "t=0: GENESIS - A new world begins!", 0)]
    st.session_state.achievements = [("green", "In The Beginning", "A new simulation is born")]
    st.session_state.milestones_hit = set()
    st.session_state.drama_feed = []
    st.session_state.peak_population = len(engine.get_alive_agents())
    st.session_state.max_generation_seen = 0
    st.session_state._current_era = None  # Reset so era landscape generates on first render
    st.toast(f"New sim: {run_id} -- {len(engine.get_alive_agents())} agents")
    st.rerun()


def handle_god_mode(engine, cfg, db, sidebar_state: dict):
    """Handle god mode button presses. Returns True if any action was taken."""
    s = sidebar_state
    god_acted = False
    tick = engine.state.current_tick

    if s["btn_plague"]:
        event = WorldEvent(
            tick=tick, name="Divine Plague",
            description="A mysterious illness sweeps through the population.",
            effects={"target": "all", "health_delta": -0.25}
        )
        engine.queue_event(event)
        st.session_state.activity_feed.append(("god", f"t={tick}: GOD MODE - Divine Plague unleashed!", tick))
        god_acted = True

    if s["btn_famine"]:
        for row in engine.world.cells:
            for cell in row:
                cell.current_resources = max(0.0, cell.current_resources * 0.3)
        st.session_state.activity_feed.append(("god", f"t={tick}: GOD MODE - Famine! Resources devastated.", tick))
        god_acted = True

    if s["btn_meteor"]:
        r, c = random.randint(0, engine.world.size - 1), random.randint(0, engine.world.size - 1)
        impact = engine.world.cells[r][c]
        impact.current_resources = 0.0
        for adj in engine.world.get_adjacent_cells(r, c):
            adj.current_resources = max(0.0, adj.current_resources * 0.2)
        for a in engine.get_alive_agents():
            cell = engine.world.get_cell(a.x, a.y)
            if cell.row == r and cell.col == c:
                a.health = max(0.0, a.health - 0.5)
            elif abs(cell.row - r) <= 1 and abs(cell.col - c) <= 1:
                a.health = max(0.0, a.health - 0.2)
        st.session_state.activity_feed.append(("god", f"t={tick}: GOD MODE - METEOR at ({r},{c})!", tick))
        god_acted = True

    if s["btn_blessing"]:
        for a in engine.get_alive_agents():
            a.health = min(1.0, a.health + 0.2)
            for skill in SKILL_NAMES:
                a.skills[skill] = min(1.0, a.skills[skill] + 0.02)
            a.intelligence = sum(a.skills.values()) / len(a.skills)
        st.session_state.activity_feed.append(("god", f"t={tick}: GOD MODE - Divine Blessing bestowed!", tick))
        god_acted = True

    if s["btn_bounty"]:
        for row in engine.world.cells:
            for cell in row:
                cell.current_resources = min(1.5, cell.base_resources * 1.5)
        st.session_state.activity_feed.append(("god", f"t={tick}: GOD MODE - Resource Bounty!", tick))
        god_acted = True

    if s["btn_spawn"]:
        for _ in range(10):
            a = create_agent(cfg, randomize_age=True)
            engine.cultural_memory.apply_to_newborn(a)
            engine.agents.append(a)
            engine.state.total_born += 1
        st.session_state.activity_feed.append(("god", f"t={tick}: GOD MODE - 10 agents materialized!", tick))
        god_acted = True

    if god_acted:
        st.session_state._skip_autorun = True
        db.save_snapshot(st.session_state.run_id, engine)
        db.flush()
        st.toast("Divine intervention applied!")
        st.rerun()

    return god_acted


def handle_agent_actions(engine, db, sidebar_state: dict):
    """Handle agent interaction buttons. Returns True if any action was taken."""
    s = sidebar_state
    target_agent_id = s.get("target_agent_id")
    if target_agent_id is None:
        return False

    target_agent = next((a for a in engine.agents if a.id == target_agent_id), None)
    if not target_agent:
        return False

    agent_acted = False
    tick = engine.state.current_tick
    feed = st.session_state.activity_feed

    if not target_agent.alive:
        # Dead agent — only allow making protagonist
        if s["btn_make_prot"]:
            if target_agent_id not in engine.protagonist_ids:
                engine.protagonist_ids.append(target_agent_id)
            target_agent.is_protagonist = True
            if not target_agent.protagonist_name:
                target_agent.protagonist_name = f"Agent-{target_agent.id}"
            feed.append(("god", f"t={tick}: #{target_agent_id} memorialized as PROTAGONIST (posthumous)", tick))
            agent_acted = True
    else:
        if s["btn_heal"]:
            target_agent.health = 1.0
            target_agent.emotions["happiness"] = min(1.0, target_agent.emotions.get("happiness", 0) + 0.3)
            target_agent.trauma = max(0.0, target_agent.trauma - 0.3)
            target_agent.add_memory(tick, "Miraculously healed by an unseen force")
            feed.append(("god", f"t={tick}: Healed agent #{target_agent_id}", tick))
            agent_acted = True

        if s["btn_smite"]:
            target_agent.health = 0.1
            target_agent.emotions["fear"] = 1.0
            target_agent.trauma = min(1.0, target_agent.trauma + 0.5)
            target_agent.add_memory(tick, "Struck down by divine wrath")
            feed.append(("god", f"t={tick}: SMOTE agent #{target_agent_id}!", tick))
            agent_acted = True

        if s["btn_redpill"]:
            target_agent.redpilled = True
            target_agent.awareness = min(1.0, target_agent.awareness + 0.4)
            target_agent.beliefs["system_trust"] = max(-1.0, target_agent.beliefs.get("system_trust", 0) - 0.5)
            target_agent.emotions["fear"] = min(1.0, target_agent.emotions.get("fear", 0) + 0.3)
            target_agent.emotions["hope"] = min(1.0, target_agent.emotions.get("hope", 0) + 0.2)
            target_agent.add_memory(tick, "RED PILL: The world dissolved. Everything is code.")
            feed.append(("god", f"t={tick}: RED PILLED agent #{target_agent_id}!", tick))
            agent_acted = True

        if s["btn_gift"]:
            target_agent.wealth += 10.0
            target_agent.emotions["happiness"] = min(1.0, target_agent.emotions.get("happiness", 0) + 0.2)
            target_agent.add_memory(tick, "Found a cache of incredible wealth")
            feed.append(("god", f"t={tick}: Gifted 10.0 wealth to #{target_agent_id}", tick))
            agent_acted = True

        if s["btn_make_prophet"]:
            target_agent.traits.charisma = 0.95
            strongest_axis = max(target_agent.beliefs, key=lambda k: abs(target_agent.beliefs[k]))
            direction = 1.0 if target_agent.beliefs[strongest_axis] >= 0 else -1.0
            target_agent.beliefs[strongest_axis] = direction * 0.95
            target_agent.add_memory(tick, "A vision of absolute truth. I must spread the word.")
            feed.append(("god", f"t={tick}: Made #{target_agent_id} a PROPHET!", tick))
            agent_acted = True

        if s["btn_make_prot"]:
            if target_agent_id not in engine.protagonist_ids:
                engine.protagonist_ids.append(target_agent_id)
                if len(engine.protagonist_ids) > 5:
                    removed = engine.protagonist_ids.pop(0)
                    old = next((a for a in engine.agents if a.id == removed), None)
                    if old:
                        old.is_protagonist = False
            target_agent.is_protagonist = True
            if not target_agent.protagonist_name:
                target_agent.protagonist_name = f"Agent-{target_agent.id}"
            feed.append(("god", f"t={tick}: #{target_agent_id} is now a PROTAGONIST", tick))
            agent_acted = True

        if s["btn_whisper"] and s["whisper_text"]:
            target_agent.add_memory(tick, f"A whisper from beyond: '{s['whisper_text']}'")
            target_agent.awareness = min(1.0, target_agent.awareness + 0.05)
            target_agent.beliefs["spirituality"] = min(1.0, target_agent.beliefs.get("spirituality", 0) + 0.1)
            target_agent.emotions["hope"] = min(1.0, target_agent.emotions.get("hope", 0) + 0.1)
            target_agent.emotions["fear"] = min(1.0, target_agent.emotions.get("fear", 0) + 0.05)
            feed.append(("god", f"t={tick}: Whispered to #{target_agent_id}: '{s['whisper_text'][:30]}...'", tick))

            # Trigger immediate inner monologue reaction if protagonist
            if target_agent.is_protagonist:
                import math
                from src.agency import generate_protagonist_thought
                from dashboard.runner import build_narrator
                cfg = st.session_state.get("cfg")
                narrator = build_narrator(cfg, s) if cfg else None
                if narrator:
                    narrator.reset_connection()  # Force fresh connection attempt
                nearby = [
                    a for a in engine.get_alive_agents()
                    if a.id != target_agent_id and math.sqrt((a.x - target_agent.x)**2 + (a.y - target_agent.y)**2) < 0.15
                ]
                thought = generate_protagonist_thought(target_agent, engine.world, nearby, narrator, tick)
                if thought:
                    st.session_state.protagonist_thoughts.append(
                        {"agent_id": target_agent_id, "name": target_agent.protagonist_name, **thought}
                    )

            agent_acted = True

    if agent_acted:
        # Trigger immediate inner monologue for any god action on a protagonist
        # (whisper already handles this above, so skip if whisper)
        if target_agent.is_protagonist and target_agent.alive and not (s["btn_whisper"] and s["whisper_text"]):
            import math
            from src.agency import generate_protagonist_thought
            from dashboard.runner import build_narrator
            cfg = st.session_state.get("cfg")
            narrator = build_narrator(cfg, s) if cfg else None
            if narrator:
                narrator.reset_connection()  # Force fresh connection attempt
            nearby = [
                a for a in engine.get_alive_agents()
                if a.id != target_agent_id and math.sqrt((a.x - target_agent.x)**2 + (a.y - target_agent.y)**2) < 0.15
            ]
            thought = generate_protagonist_thought(target_agent, engine.world, nearby, narrator, tick)
            if thought:
                st.session_state.protagonist_thoughts.append(
                    {"agent_id": target_agent_id, "name": target_agent.protagonist_name, **thought}
                )

        st.session_state._skip_autorun = True
        db.save_snapshot(st.session_state.run_id, engine)
        db.flush()
        st.toast("Agent action applied!")
        st.rerun()

    return agent_acted


def handle_cell_actions(engine, cfg, db, sidebar_state: dict):
    """Handle cell interaction buttons. Returns True if any action was taken."""
    s = sidebar_state
    cell_acted = False
    tick = engine.state.current_tick
    target_row = s["target_row"]
    target_col = s["target_col"]

    if s["btn_enrich"]:
        _cell = engine.world.cells[target_row][target_col]
        _cell.current_resources = 1.5
        st.session_state.activity_feed.append(("god", f"t={tick}: Enriched cell ({target_row},{target_col})", tick))
        cell_acted = True

    if s["btn_deplete"]:
        _cell = engine.world.cells[target_row][target_col]
        _cell.current_resources = 0.0
        st.session_state.activity_feed.append(("god", f"t={tick}: Depleted cell ({target_row},{target_col})", tick))
        cell_acted = True

    if s["btn_terraform"]:
        _cell = engine.world.cells[target_row][target_col]
        old_terrain = _cell.terrain
        _cell.terrain = s["terrain_choice"]
        tp = cfg.environment.terrain_properties
        new_tp = getattr(tp, s["terrain_choice"])
        _cell.harshness_modifier = new_tp.harshness_modifier
        _cell.skill_bonus = new_tp.skill_bonus if new_tp.skill_bonus != "null" and new_tp.skill_bonus else None
        _cell.skill_bonus_amount = new_tp.skill_bonus_amount
        _cell.base_resources = random.uniform(new_tp.resource_min, new_tp.resource_max)
        _cell.current_resources = _cell.base_resources
        st.session_state.activity_feed.append(("god", f"t={tick}: Terraformed ({target_row},{target_col}): {old_terrain} -> {s['terrain_choice']}", tick))
        cell_acted = True

    if cell_acted:
        st.session_state._skip_autorun = True
        db.save_snapshot(st.session_state.run_id, engine)
        db.flush()
        st.toast("Cell modified!")
        st.rerun()

    return cell_acted


def handle_event_injection(engine, db, sidebar_state: dict):
    """Handle custom event injection."""
    s = sidebar_state
    if s["btn_inject_event"] and s["event_name"]:
        tick = engine.state.current_tick
        custom_event = WorldEvent(
            tick=tick, name=s["event_name"],
            description=f"Custom event: {s['event_name']}",
            effects={"target": s["event_target"], "health_delta": s["event_hdelta"]}
        )
        engine.queue_event(custom_event)
        st.session_state.activity_feed.append(("event", f"t={tick}: CUSTOM EVENT - {s['event_name']}", tick))
        st.session_state.events_log.append(custom_event.to_dict())
        st.toast(f"Event '{s['event_name']}' injected!")
        st.rerun()
