"""Tick runner and narrator integration for the dashboard."""
from __future__ import annotations

import math

import streamlit as st

from src.narrator import Narrator
from src.agency import generate_protagonist_thought

from gui.dashboard.state import check_achievements, generate_drama


def build_narrator(cfg, sidebar_state: dict) -> Narrator:
    """Build a narrator based on sidebar LLM provider selection."""
    llm_provider = sidebar_state.get("llm_provider", "none")
    if llm_provider == "ollama":
        return Narrator.from_config(cfg)
    elif llm_provider == "huggingface":
        from src.narrator import HuggingFaceProvider, OllamaProvider
        hf_model = sidebar_state.get("hf_model", cfg.narrator.hf_model)
        hf_token = sidebar_state.get("hf_token")
        providers = [
            HuggingFaceProvider(hf_model, hf_token if hf_token else None),
            OllamaProvider(cfg.narrator.ollama_model),
        ]
        return Narrator(providers=providers, enabled=True)
    return Narrator(enabled=False)


def run_ticks(num_ticks: int, cfg, db, sidebar_state: dict):
    """Run a number of ticks and update all state."""
    engine = st.session_state.engine
    if not engine:
        return
    engine.cfg = cfg
    run_id = st.session_state.run_id

    # Sync ID counters after Streamlit hot-reloads
    from src.agents import set_id_counter, get_id_counter
    from src.beliefs import set_faction_id_counter, get_faction_id_counter
    from src.communication import set_info_id_counter, get_info_id_counter
    max_agent_id = max((a.id for a in engine.agents), default=0)
    if get_id_counter() < max_agent_id:
        set_id_counter(max_agent_id)
    max_faction_id = max((f.id for f in engine.factions), default=0)
    if get_faction_id_counter() < max_faction_id:
        set_faction_id_counter(max_faction_id)
    max_info_id = max((i.id for i in engine.info_objects), default=0)
    if get_info_id_counter() < max_info_id:
        set_info_id_counter(max_info_id)

    narrator = build_narrator(cfg, sidebar_state)
    nc = cfg.narrator

    show_progress = num_ticks > 5
    progress = st.progress(0, text="Running...") if show_progress else None

    for i in range(num_ticks):
        prev_alive_ids = {a.id for a in engine.get_alive_agents()}

        result = engine.tick()
        db.save_tick_stats(run_id, result)

        # Accumulate tick history
        st.session_state.tick_history.append({
            "tick": result.tick,
            "alive_count": result.alive_count,
            "births": result.births, "deaths": result.deaths,
            "avg_intelligence": result.avg_intelligence,
            "avg_health": result.avg_health,
            "avg_generation": result.avg_generation,
            "bonds_formed": result.bonds_formed,
            "bonds_decayed": result.bonds_decayed,
            **result.phase_counts,
        })

        # Activity feed
        feed = st.session_state.activity_feed
        if result.births > 0:
            feed.append(("birth", f"t={result.tick}: {result.births} born (pop: {result.alive_count})", result.tick))
        if result.deaths > 0:
            feed.append(("death", f"t={result.tick}: {result.deaths} died (pop: {result.alive_count})", result.tick))
        if result.bonds_formed > 0:
            feed.append(("bond", f"t={result.tick}: {result.bonds_formed} new bonds formed", result.tick))
        for bt in result.breakthroughs:
            feed.append(("tech", f"t={result.tick}: BREAKTHROUGH - {bt}!", result.tick))
        # No cap — all feed entries accumulate until New Sim

        # Drama
        if result.tick % 5 == 0:
            drama = generate_drama(engine, result, prev_alive_ids)
            st.session_state.drama_feed.extend(drama)
            # No cap — all drama entries accumulate until New Sim

        # New system feed updates
        feed = st.session_state.activity_feed
        if result.belief_stats.get("factions_formed", 0) > 0:
            feed.append(("bond", f"t={result.tick}: New faction formed!", result.tick))
        if result.belief_stats.get("schisms", 0) > 0:
            feed.append(("drama", f"t={result.tick}: SCHISM - A faction has split!", result.tick))
        if result.belief_stats.get("prophets_emerged", 0) > 0:
            feed.append(("event", f"t={result.tick}: A PROPHET has emerged!", result.tick))
        if result.conflict_stats.get("wars_started", 0) > 0:
            feed.append(("death", f"t={result.tick}: WAR DECLARED between factions!", result.tick))
        if result.conflict_stats.get("wars_ended", 0) > 0:
            feed.append(("bond", f"t={result.tick}: PEACE - A war has ended", result.tick))
        if result.matrix_stats.get("glitches", 0) > 0:
            feed.append(("god", f"t={result.tick}: GLITCH detected in the Matrix...", result.tick))
        if result.matrix_stats.get("anomaly_active") and result.tick % 50 == 0:
            feed.append(("god", f"t={result.tick}: THE ANOMALY walks among us", result.tick))
        rp = result.matrix_stats.get("redpilled_count", 0)
        if rp > 0 and result.tick % 25 == 0:
            feed.append(("tech", f"t={result.tick}: {rp} agents have seen beyond the veil", result.tick))

        check_achievements(engine, result)

        # World events
        if result.tick % nc.event_interval == 0 and result.alive_count > 0:
            summary = engine.get_population_summary()
            event = narrator.generate_event(summary)
            if event:
                engine.queue_event(event)
                db.save_event(run_id, event)
                st.session_state.events_log.append(event.to_dict())
                st.session_state.activity_feed.append(
                    ("event", f"t={result.tick}: EVENT - {event.name}", result.tick)
                )

        # Narration
        if result.tick % nc.narration_interval == 0 and result.alive_count > 0:
            summary = engine.get_population_summary()
            text = narrator.narrate(summary)
            if text:
                db.save_narrative(run_id, result.tick, text)
                st.session_state.narratives_log.append({"tick": result.tick, "text": text})

        # Protagonist thoughts
        if result.tick % cfg.agency.protagonists.decision_interval == 0:
            for pid in engine.protagonist_ids:
                agent = next((a for a in engine.agents if a.id == pid and a.alive), None)
                if agent:
                    nearby = [
                        a for a in engine.get_alive_agents()
                        if a.id != pid and math.sqrt((a.x - agent.x)**2 + (a.y - agent.y)**2) < 0.15
                    ]
                    thought = generate_protagonist_thought(agent, engine.world, nearby, narrator, result.tick, use_llm=False)
                    if thought:
                        st.session_state.protagonist_thoughts.append(
                            {"agent_id": pid, "name": agent.protagonist_name, **thought}
                        )

        # Snapshot
        if result.tick % cfg.persistence.snapshot_interval == 0:
            db.save_snapshot(run_id, engine)
            db.flush()

        # Progress
        if progress and ((i + 1) % 10 == 0 or i == num_ticks - 1):
            progress.progress(
                (i + 1) / num_ticks,
                text=f"Tick {result.tick} | Pop: {result.alive_count} | Gen: {result.avg_generation:.1f}"
            )

        if result.alive_count == 0:
            st.warning(f"Extinction at tick {result.tick}!")
            ms = st.session_state.milestones_hit
            if isinstance(ms, list):
                ms = set(ms)
                st.session_state.milestones_hit = ms
            if "extinction" not in ms:
                ms.add("extinction")
                st.session_state.achievements.append(("gold", "The End", f"Civilization fell at tick {result.tick}"))
            break

    db.save_snapshot(run_id, engine)
    db.flush()
    if progress:
        progress.empty()

    st.toast(f"Tick {engine.state.current_tick} | Pop: {len(engine.get_alive_agents())}")
