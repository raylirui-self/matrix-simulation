"""
Cognitive Matrix v2 — Streamlit Dashboard (Modular)
Main orchestrator that wires together sidebar, handlers, runner, and tabs.

Run: streamlit run dashboard.py
"""
from __future__ import annotations

import time

import streamlit as st

from src.agents import PHASES, SKILL_NAMES, EMOTION_NAMES, BELIEF_AXES

from dashboard.styles import MATRIX_CSS
from dashboard.state import init_state, get_db, get_era
from dashboard.controls import render_sidebar
from dashboard.runner import run_ticks
from dashboard.handlers import (
    handle_new_sim, handle_god_mode, handle_agent_actions,
    handle_cell_actions, handle_event_injection,
)
from dashboard.tabs.feed import render_feed_tab
from dashboard.tabs.charts import render_charts_tab
from dashboard.tabs.world import render_world_tab
from dashboard.tabs.agents import render_agents_tab
from dashboard.tabs.social import render_social_tab
from dashboard.tabs.systems import (
    render_emotions_tab, render_factions_tab, render_economy_tab,
    render_matrix_tab, render_culture_tab,
)
from dashboard.tabs.content import render_events_tab, render_narratives_tab, render_protagonists_tab
from dashboard.tabs.records import render_records_tab, render_compare_tab


def main():
    # ── Page Config ──
    st.set_page_config(
        page_title="Cognitive Matrix v2",
        page_icon="◉",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(MATRIX_CSS, unsafe_allow_html=True)

    # ── Init ──
    init_state()
    db = get_db()

    # ── Sidebar ──
    cfg, sidebar = render_sidebar(db)

    # ── Handle New ──
    if sidebar["btn_new"]:
        handle_new_sim(cfg, db)

    # ── Handle Run/Step ──
    step_amount = 0
    if sidebar["btn_step1"]:
        step_amount = 1
    elif sidebar["btn_step10"]:
        step_amount = 10
    elif sidebar["btn_step50"]:
        step_amount = 50
    elif sidebar["btn_step100"]:
        step_amount = 100
    elif sidebar["btn_run"]:
        step_amount = sidebar["batch_size"]

    if step_amount > 0 and st.session_state.engine:
        run_ticks(step_amount, cfg, db, sidebar)
        st.rerun()

    # ── Handle Interactions ──
    engine = st.session_state.engine

    if engine:
        handle_god_mode(engine, cfg, db, sidebar)
        handle_agent_actions(engine, db, sidebar)
        handle_cell_actions(engine, cfg, db, sidebar)
        handle_event_injection(engine, db, sidebar)

    # ── Auto-Run ──
    if st.session_state.auto_run and st.session_state.engine:
        if st.session_state.get("_skip_autorun", False):
            st.session_state._skip_autorun = False
        else:
            run_ticks(st.session_state.auto_run_speed, cfg, db, sidebar)
            time.sleep(0.1)
            st.rerun()

    # ── Landing Page ──
    if engine is None:
        st.markdown("# ◉ Cognitive Matrix v2")
        st.markdown("")
        st.markdown("""
        <div style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 4em; margin-bottom: 20px; filter: drop-shadow(0 0 20px rgba(0,255,136,0.5));">◉</div>
            <div style="font-family: 'Space Grotesk', sans-serif; font-size: 1.5em; color: #00ff88; margin-bottom: 10px;">
                Agent-Based Civilization Simulator
            </div>
            <div style="color: #5a8a5a; max-width: 600px; margin: 0 auto; line-height: 1.6;">
                Watch civilizations emerge from simple rules. Agents are born, learn,
                form bonds, compete, reproduce, and die. Knowledge accumulates across
                generations. Technologies unlock. Empires rise and fall.
            </div>
            <div style="margin-top: 30px; color: #3a6a3a;">
                Create a <span style="color: #00ff88;">New</span> simulation or
                <span style="color: #00ff88;">Load</span> a run from the sidebar.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # ── Active Simulation ──
    alive = engine.get_alive_agents()
    summary = engine.get_population_summary()

    # ── Era Banner ──
    world_info = summary.get("world", {})
    era_name, era_desc, era_color = get_era(
        engine.state.current_tick,
        len(alive),
        summary.get("avg_intelligence", 0),
        world_info.get("global_techs", [])
    )

    # Check for era landscape image
    import base64
    import os as _os
    from pathlib import Path
    era_img_dir = Path("output/era_landscapes")
    era_img_dir.mkdir(parents=True, exist_ok=True)
    era_safe_name = era_name.lower().replace(" ", "_")
    era_img_path = era_img_dir / f"{era_safe_name}.png"

    # Detect era change — generate landscape if missing
    prev_era = st.session_state.get("_current_era", None)
    era_changed = prev_era != era_name
    if era_changed:
        st.session_state._current_era = era_name

    # Show banner first (always visible immediately)
    era_banner_container = st.container()

    # Generate landscape if era changed and image missing
    if era_changed and not era_img_path.exists():
        hf_token = sidebar.get("portrait_hf_token") or _os.environ.get("HF_TOKEN")
        gen_status = st.empty()
        gen_status.info(f"Generating {era_name} landscape... This may take a moment.")
        try:
            from src.portrait import PortraitGenerator
            from dashboard.runner import build_narrator
            narrator = build_narrator(cfg, sidebar)
            gen = PortraitGenerator(
                hf_token=hf_token,
                hf_model=sidebar.get("portrait_hf_model", "black-forest-labs/FLUX.1-schnell"),
                diffuser_model=sidebar.get("portrait_diffuser_model", "flux.1-schnell"),
            )
            result = gen.generate_era_landscape(era_name, era_desc, narrator)
            if result:
                gen_status.success(f"{era_name} landscape generated!")
            else:
                gen_status.warning("Landscape generation failed — no image provider available. Set HF token in sidebar > Portrait Generation.")
        except Exception as e:
            gen_status.warning(f"Landscape generation failed: {e}")

    # Render the banner (with or without background image)
    with era_banner_container:
        if era_img_path.exists():
            img_data = base64.b64encode(era_img_path.read_bytes()).decode()
            st.markdown(f"""
            <div class="era-banner-with-bg" style="background-image: url('data:image/png;base64,{img_data}');">
                <div class="era-name" style="color: {era_color};">{era_name}</div>
                <div class="era-desc">{era_desc} | Tick {engine.state.current_tick}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="era-banner">
                <div class="era-name" style="color: {era_color};">{era_name}</div>
                <div class="era-desc">{era_desc} | Tick {engine.state.current_tick}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Header Metrics ──
    _hist = st.session_state.tick_history
    _prev_pop = _hist[-10]["alive_count"] if len(_hist) >= 10 else None
    _prev_hp = _hist[-10].get("avg_health") if len(_hist) >= 10 else None
    _prev_iq = _hist[-10].get("avg_intelligence") if len(_hist) >= 10 else None

    _pop = summary["alive"]
    _health = summary["avg_health"]
    _iq = summary["avg_intelligence"]
    _techs = world_info.get("global_techs", [])

    # Health interpretation
    if _health > 0.7:
        _hp_label = "Thriving"
        _hp_color = "normal"
    elif _health > 0.4:
        _hp_label = "Stressed"
        _hp_color = "normal"
    else:
        _hp_label = "Critical"
        _hp_color = "inverse"

    # IQ interpretation
    if _iq > 0.5:
        _iq_label = "Brilliant"
    elif _iq > 0.2:
        _iq_label = "Growing"
    else:
        _iq_label = "Primitive"

    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    m1.metric("Population", _pop,
              delta=f"{_pop - _prev_pop:+d}" if _prev_pop is not None else None,
              help="Living agents right now. Green arrow = growing, red = shrinking.")
    m2.metric("Total Born", summary["total_born"],
              help="Cumulative births since sim started. High numbers = healthy reproduction.")
    m3.metric("Total Deaths", summary["total_died"],
              help="Cumulative deaths. Compare with births — if deaths > births, civilization is declining.")
    m4.metric("Max Gen", summary["max_generation"],
              help="Highest generation alive. Gen 1 = original population. Higher = knowledge passed down through more generations.")
    m5.metric(f"Health ({_hp_label})", f"{_health:.0%}",
              delta=f"{_health - _prev_hp:+.0%}" if _prev_hp is not None else None,
              help="Average health of all agents (0-100%). Below 40% = survival crisis. Above 70% = thriving. Affected by resources, environment harshness, and age.")
    m6.metric(f"Intellect ({_iq_label})", f"{_iq:.0%}",
              delta=f"{_iq - _prev_iq:+.0%}" if _prev_iq is not None else None,
              help="Average intelligence across all agents (0-100%). This is the mean of all 5 skills. Higher = more capable civilization. Grows through learning and teaching across generations.")
    m7.metric(f"Tech ({len(_techs)})", ", ".join(_techs[-2:]) if _techs else "None",
              help="Technologies unlocked by the civilization. Each tech requires agents with high enough skills clustering together. Techs unlock new abilities and mark era transitions.")

    # ── Second Row — with descriptions ──
    _ns = [a for a in alive if not a.is_sentinel]
    if _ns:
        _avg_happy = sum(a.emotions.get("happiness", 0) for a in _ns) / len(_ns)
        _mood_icon = "\U0001f60a" if _avg_happy > 0.5 else "\U0001f610" if _avg_happy > 0.2 else "\U0001f61e"
        _factions = len(engine.factions)
        _wars = len(engine.wars)
        _wealth = summary.get("avg_wealth", 0)
        _control = engine.matrix_state.control_index
        _aware = summary.get("redpilled_count", 0)

        ns1, ns2, ns3, ns4, ns5, ns6 = st.columns(6)
        ns1.metric(f"{_mood_icon} Mood", f"{_avg_happy:.0%}",
                   help="Average happiness of the population. High mood = less conflict, more bonding. Low mood = unrest, aggression, and fear spread faster.")
        ns2.metric("\u2694\ufe0f Factions", _factions,
                   help=f"Ideological groups that agents form based on shared beliefs. Factions provide learning bonuses to members but can go to war with each other.")
        ns3.metric("\U0001f4b0 Avg Wealth", f"{_wealth:.1f}",
                   help="Average material wealth per agent. Wealth comes from resource gathering and trade. Rich agents live longer and attract better mates. Poor agents struggle to survive.")
        ns4.metric("\U0001f7e2 Stability", f"{_control:.0%}",
                   help="How stable the simulation is. High = the world runs smoothly. Low = glitches appear, agents start noticing anomalies, and the fabric of reality frays. (Think: how well the Matrix is holding together.)")
        ns5.metric("\U0001f441\ufe0f Awakened", _aware,
                   help="Agents who have 'seen through the simulation' — they've become aware that their world may not be real. Awakened agents behave unpredictably and can influence others. (Think: Neo in The Matrix.)")
        ns6.metric("\U0001f6e1\ufe0f Wars", _wars,
                   help=f"Active wars between factions. Wars cause combat damage, deaths, and emotional trauma. They end when one faction surrenders or is destroyed.")

    # ── Achievement Badges ──
    recent_achv = st.session_state.achievements[-5:] if st.session_state.achievements else []
    if recent_achv:
        badges_html = " ".join(
            f'<span class="achievement achievement-{a[0]}" title="{a[2]}">{a[1]}</span>'
            for a in reversed(recent_achv)
        )
        st.markdown(badges_html, unsafe_allow_html=True)

    # ── Tabs ──
    tab_feed, tab_charts, tab_world, tab_agents, tab_social, tab_emo, \
        tab_factions, tab_econ, tab_matrix, tab_culture, tab_events, \
        tab_narr, tab_prot, tab_records, tab_cmp = st.tabs([
        "\U0001f4e1 Live Feed",
        "\U0001f4c8 Charts",
        "\U0001f30d World",
        "\U0001f9ec Agents",
        "\U0001f91d Social",
        "\U0001f9e0 Emotions",
        "\u2694\ufe0f Factions",
        "\U0001f4b0 Economy",
        "\U0001f7e2 Matrix",
        "\U0001f4da Culture",
        "\u26a1 Events",
        "\U0001f4dc Narratives",
        "\u2b50 Protagonists",
        "\U0001f3c6 Records",
        "\U0001f504 Compare",
    ])

    with tab_feed:
        render_feed_tab()
    with tab_charts:
        render_charts_tab()
    with tab_world:
        render_world_tab(engine, alive)
    with tab_agents:
        render_agents_tab(engine, alive)
    with tab_social:
        render_social_tab(alive)
    with tab_emo:
        render_emotions_tab(alive)
    with tab_factions:
        render_factions_tab(engine, alive)
    with tab_econ:
        render_economy_tab(engine, alive)
    with tab_matrix:
        render_matrix_tab(engine, alive)
    with tab_culture:
        render_culture_tab(engine, summary, cfg)
    with tab_events:
        render_events_tab()
    with tab_narr:
        render_narratives_tab()
    with tab_prot:
        render_protagonists_tab(engine, alive, sidebar_state=sidebar)
    with tab_records:
        render_records_tab(engine, alive)
    with tab_cmp:
        render_compare_tab(db)
