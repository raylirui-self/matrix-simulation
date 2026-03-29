"""Sidebar controls: scenario selection, LLM provider, parameter overrides,
run controls, god mode, agent/cell actions, event injector, load/fork/export."""
from __future__ import annotations

import copy

import streamlit as st

from src.config_loader import SimConfig
from src.engine import SimulationEngine, RunState
from src.world import ResourceGrid
from src.persistence import SimulationDB


def render_sidebar(db: SimulationDB):
    """Render the full sidebar and return (cfg, sidebar_state) dict with all button/config values."""
    s = {}  # sidebar state accumulator

    with st.sidebar:
        st.markdown("## ◉ Cognitive Matrix v2")
        st.caption("11-System Agent Civilization Simulator")

        # Quick status
        if st.session_state.engine:
            _e = st.session_state.engine
            _a_count = len(_e.get_alive_agents())
            _fac_count = len(_e.factions)
            _war_count = len(_e.wars)
            st.markdown(
                f'<div style="background:#0a1f0a;border:1px solid #0a2a0a;border-radius:6px;padding:6px 10px;'
                f'font-family:JetBrains Mono,monospace;font-size:0.75em;color:#5a8a5a;margin-bottom:8px;">'
                f'\U0001f7e2 t={_e.state.current_tick} &nbsp; '
                f'\U0001f465 {_a_count} &nbsp; '
                f'\u2694\ufe0f {_fac_count}F/{_war_count}W &nbsp; '
                f'\U0001f7e2 {_e.matrix_state.control_index:.0%}'
                f'</div>', unsafe_allow_html=True
            )

        st.divider()

        # ── Era Selection ──
        st.markdown("### Era & Scenario")
        try:
            cfg_temp = SimConfig.load()
            available_eras = cfg_temp.list_eras()
            era_options = ["(none)"] + [e["name"] for e in available_eras]
            era_labels = {"(none)": "(none) — Default neutral baseline"}
            for e in available_eras:
                era_labels[e["name"]] = f"{e['display_name']} ({e['time_period']})"
        except Exception:
            era_options = ["(none)"]
            era_labels = {"(none)": "(none)"}

        selected_era = st.selectbox(
            "Historical Era", era_options,
            format_func=lambda x: era_labels.get(x, x),
            help="Historically-researched config preset that tunes all 11 systems to reflect a time period."
        )
        if selected_era != "(none)":
            st.session_state.era_name = selected_era
            # Show era info
            era_info = next((e for e in available_eras if e["name"] == selected_era), None)
            if era_info:
                st.caption(f"{era_info['description']}")
        else:
            st.session_state.era_name = None

        # ── Scenario Selection ──
        try:
            available_scenarios = cfg_temp.list_scenarios()
            scenario_names = ["(default)"] + [sc["name"] for sc in available_scenarios]
        except Exception:
            scenario_names = ["(default)"]

        selected_scenario = st.selectbox("Config Scenario", scenario_names,
                                          help="Gameplay-tuned overlay applied on top of era.")
        if selected_scenario != "(default)":
            st.session_state.scenario_name = selected_scenario
        else:
            st.session_state.scenario_name = None

        try:
            cfg = SimConfig.load(
                scenario=st.session_state.scenario_name,
                era=st.session_state.get("era_name"),
            )
            st.session_state.cfg = cfg
        except Exception as e:
            st.error(f"Config error: {e}")
            cfg = SimConfig.load()
            st.session_state.cfg = cfg

        st.divider()

        # ── LLM Provider ──
        st.markdown("### LLM Provider")
        s["llm_provider"] = st.selectbox("Provider", ["ollama", "huggingface", "none"])
        if s["llm_provider"] == "ollama":
            s["ollama_model"] = st.text_input("Ollama Model", value=cfg.narrator.ollama_model)
        elif s["llm_provider"] == "huggingface":
            s["hf_model"] = st.text_input("HF Model", value=cfg.narrator.hf_model)
            s["hf_token"] = st.text_input("HF Token", type="password")

        # ── Portrait Generation ──
        with st.expander("Portrait Generation", expanded=False):
            st.caption("Generate AI portraits for protagonists")
            s["portrait_hf_token"] = st.text_input(
                "HF Token (for images)", type="password",
                key="portrait_hf_token",
                help="HuggingFace token for image generation (primary). Falls back to OllamaDiffuser if unavailable."
            )
            s["portrait_hf_model"] = st.text_input(
                "HF Image Model",
                value="black-forest-labs/FLUX.1-schnell",
                key="portrait_hf_model",
                help="HuggingFace model for image generation."
            )
            s["portrait_diffuser_model"] = st.text_input(
                "OllamaDiffuser Model",
                value="flux.1-schnell",
                key="portrait_diffuser_model",
                help="Fallback local model via OllamaDiffuser."
            )

        st.divider()

        # ── Runtime Parameter Overrides ──
        st.markdown("### Parameter Overrides")
        st.caption("Override scenario config for this session")

        ov_harshness = st.slider(
            "Env. Harshness", 0.2, 3.0, float(cfg.environment.harshness), 0.1,
            help="How fast the world kills your agents.\n\n"
                 "0.2-0.5 -- Garden of Eden. Population explodes.\n\n"
                 "1.0 -- Balanced. Survival matters but isn't desperate.\n\n"
                 "2.0+ -- The Hunger Games. Mass death. Only the resilient live.\n\n"
                 "2.5+ -- Extinction almost guaranteed."
        )
        ov_mutation = st.slider(
            "Mutation Rate", 0.0, 0.5, float(cfg.genetics.mutation_rate), 0.01,
            help="Genetic chaos dial. How much children differ from parents.\n\n"
                 "0.0 -- Carbon copies. Stable but fragile (one plague kills everyone).\n\n"
                 "0.15 -- Natural diversity. Evolution works as intended.\n\n"
                 "0.3+ -- Genetic roulette. Occasional genius. Occasional disaster."
        )
        ov_learning = st.slider(
            "Learning Multiplier", 0.1, 3.0, float(cfg.skills.learning_multiplier), 0.1,
            help="Brain speed. How fast agents gain skills.\n\n"
                 "0.1-0.5 -- Stone age forever. Cultural memory carries the load.\n\n"
                 "1.0 -- Normal growth. Tech breakthroughs feel earned.\n\n"
                 "2.0+ -- Speed run. Agents master everything in one lifetime."
        )
        ov_competition = st.slider(
            "Competition Weight", 0.0, 1.0, float(cfg.mate_selection.weights.competition), 0.05,
            help="Survival of the fittest vs. power of love.\n\n"
                 "0.0-0.2 -- Love conquers all. Bonds and compatibility drive mating.\n\n"
                 "0.5 -- Balanced. Fitness matters, but so do relationships.\n\n"
                 "0.8+ -- Only the strong reproduce. Genetic monoculture risk."
        )

        with st.expander("New System Parameters", expanded=False):
            ov_emo_contagion = st.slider(
                "Emotional Contagion", 0.0, 0.15, float(cfg.emotions.contagion_rate), 0.005,
                help="How infectious emotions are.\n\n"
                     "0.0 -- Stoic robots. Nobody catches feelings.\n\n"
                     "0.03 -- Natural empathy. Moods ripple through friend groups.\n\n"
                     "0.08+ -- Emotional wildfire. One panicked agent = mass stampede."
            )
            ov_awareness = st.slider(
                "Awareness Growth", 0.0001, 0.005, float(cfg.matrix.awareness_growth_rate), 0.0001,
                format="%.4f",
                help="How fast agents notice the simulation.\n\n"
                     "0.0001 -- Deep sleep. The Matrix is rock-solid.\n\n"
                     "0.0005 -- Cracks appear. Curious agents start wondering.\n\n"
                     "0.002+ -- Mass awakening. Sentinels work overtime."
            )
            ov_glitch = st.slider(
                "Glitch Probability", 0.0, 0.15, float(cfg.matrix.glitch_probability), 0.005,
                help="How unstable the simulation is. Per-tick chance of deja vu, ghosts, terrain flickers.\n\n"
                     "0.0 -- Flawless simulation. Nothing seems off.\n\n"
                     "0.02 -- Occasional weirdness. Aware agents notice.\n\n"
                     "0.08+ -- Reality is glitching constantly. Awakening accelerates."
            )
            ov_faction_sim = st.slider(
                "Faction Formation", 0.3, 0.9, float(cfg.beliefs.faction_formation_similarity), 0.05,
                help="How ideologically aligned agents must be to form a group.\n\n"
                     "0.3-0.4 -- Everyone joins something. Many small factions. More wars.\n\n"
                     "0.65 -- Real alignment needed. Meaningful factions.\n\n"
                     "0.8+ -- Only true believers unite. Few but fanatical groups."
            )
            ov_trade = st.slider(
                "Trade Rate", 0.0, 0.5, float(cfg.economy.trade_rate), 0.05,
                help="Wealth redistribution through commerce.\n\n"
                     "0.0 -- No trade. What you gather is what you keep. Extreme inequality.\n\n"
                     "0.15 -- Healthy markets. Friends share prosperity.\n\n"
                     "0.3+ -- Wealth equalizes fast. Almost communist economics."
            )
            ov_tax = st.slider(
                "Faction Tax Rate", 0.0, 0.1, float(cfg.economy.faction_tax_rate), 0.005,
                help="How much factions take from members and redistribute.\n\n"
                     "0.0 -- Libertarian paradise. No faction taxes.\n\n"
                     "0.02 -- Safety net. Prevents faction members from starving.\n\n"
                     "0.05+ -- Redistributionist. Equal but less individual drive."
            )
            ov_combat = st.slider(
                "Combat Damage", 0.0, 0.3, float(cfg.conflict.combat_damage), 0.01,
                help="How deadly fights are.\n\n"
                     "0.0-0.03 -- Playground scuffles. Pride is hurt, not bodies.\n\n"
                     "0.08 -- Real danger. A few bad fights and you're dead.\n\n"
                     "0.2+ -- One-hit kills. Wars cause dark ages."
            )
            ov_war_thresh = st.slider(
                "War Threshold", 0.2, 1.5, float(cfg.conflict.war_threshold), 0.05,
                help="How easily factions go to war.\n\n"
                     "0.2-0.4 -- Powder keg. Any disagreement escalates.\n\n"
                     "0.6 -- Wars require real grudges and territorial overlap.\n\n"
                     "1.0+ -- World peace (mostly). Only existential threats trigger war."
            )

        runtime_overrides = {}
        if ov_harshness != cfg.environment.harshness:
            runtime_overrides.setdefault("environment", {})["harshness"] = ov_harshness
        if ov_mutation != cfg.genetics.mutation_rate:
            runtime_overrides.setdefault("genetics", {})["mutation_rate"] = ov_mutation
        if ov_learning != cfg.skills.learning_multiplier:
            runtime_overrides.setdefault("skills", {})["learning_multiplier"] = ov_learning
        if ov_competition != cfg.mate_selection.weights.competition:
            runtime_overrides.setdefault("mate_selection", {}).setdefault("weights", {})["competition"] = ov_competition
        if ov_emo_contagion != cfg.emotions.contagion_rate:
            runtime_overrides.setdefault("emotions", {})["contagion_rate"] = ov_emo_contagion
        if ov_awareness != cfg.matrix.awareness_growth_rate:
            runtime_overrides.setdefault("matrix", {})["awareness_growth_rate"] = ov_awareness
        if ov_glitch != cfg.matrix.glitch_probability:
            runtime_overrides.setdefault("matrix", {})["glitch_probability"] = ov_glitch
        if ov_faction_sim != cfg.beliefs.faction_formation_similarity:
            runtime_overrides.setdefault("beliefs", {})["faction_formation_similarity"] = ov_faction_sim
        if ov_trade != cfg.economy.trade_rate:
            runtime_overrides.setdefault("economy", {})["trade_rate"] = ov_trade
        if ov_tax != cfg.economy.faction_tax_rate:
            runtime_overrides.setdefault("economy", {})["faction_tax_rate"] = ov_tax
        if ov_combat != cfg.conflict.combat_damage:
            runtime_overrides.setdefault("conflict", {})["combat_damage"] = ov_combat
        if ov_war_thresh != cfg.conflict.war_threshold:
            runtime_overrides.setdefault("conflict", {})["war_threshold"] = ov_war_thresh

        if runtime_overrides:
            cfg = cfg.override(runtime_overrides)
            st.session_state.cfg = cfg

        st.divider()

        # ── Run Controls ──
        st.markdown("### Controls")
        st.caption("Each tick = one unit of simulated time.")

        col1, col2 = st.columns(2)
        with col1:
            s["btn_new"] = st.button("New Sim", width='stretch',
                                     help="Creates a fresh population with the current parameters.")
        with col2:
            s["btn_step1"] = st.button("+1 Tick", width='stretch',
                                       help="Advance exactly 1 tick.")

        col3, col4, col5 = st.columns(3)
        with col3:
            s["btn_step10"] = st.button("+10", width='stretch', help="Quick jump.")
        with col4:
            s["btn_step50"] = st.button("+50", width='stretch', help="Skip ahead.")
        with col5:
            s["btn_step100"] = st.button("+100", width='stretch', help="Leap forward.")

        # ── Auto-Run ──
        st.markdown("### Live Mode")
        auto_run = st.toggle("Auto-Run", value=st.session_state.auto_run,
                              help="The simulation runs continuously. Toggle off to pause.")
        st.session_state.auto_run = auto_run
        auto_speed = st.slider("Ticks per cycle", 1, 50, st.session_state.auto_run_speed,
                                help="How many ticks before dashboard refresh.")
        st.session_state.auto_run_speed = auto_speed

        s["batch_size"] = st.number_input("Custom Batch", 50, 10000, int(cfg.batch.default_ticks), 50,
                                          help="Number of ticks to run in one batch.")
        s["btn_run"] = st.button("Run Batch", width='stretch', type="primary",
                                 help="Run the custom batch size.")

        st.divider()

        # ── God Mode ──
        st.markdown("### God Mode")
        st.caption("Smite the world or save it")

        god_col1, god_col2 = st.columns(2)
        with god_col1:
            s["btn_plague"] = st.button("Plague", width='stretch',
                                        help="-0.25 HP across the board.")
            s["btn_famine"] = st.button("Famine", width='stretch',
                                        help="All resources drop to 30%.")
            s["btn_meteor"] = st.button("Meteor!", width='stretch',
                                        help="Random cell destroyed + neighbors wrecked.")
        with god_col2:
            s["btn_blessing"] = st.button("Blessing", width='stretch',
                                          help="+0.2 HP, +0.02 to all skills.")
            s["btn_bounty"] = st.button("Bounty", width='stretch',
                                        help="All cells to 150% resources.")
            s["btn_spawn"] = st.button("Spawn 10", width='stretch',
                                       help="10 strangers appear from nowhere.")

        st.divider()

        # ── Agent Interaction ──
        st.markdown("### Agent Actions")
        st.caption("Play god with one soul at a time")
        s["target_agent_id"] = None
        s["btn_heal"] = s["btn_smite"] = s["btn_redpill"] = False
        s["btn_gift"] = s["btn_make_prophet"] = s["btn_make_prot"] = s["btn_whisper"] = False
        s["whisper_text"] = ""

        if st.session_state.engine:
            _all_agents = st.session_state.engine.agents
            _alive = st.session_state.engine.get_alive_agents()
            _alive_ids = sorted([a.id for a in _alive if not a.is_sentinel])
            _dead_notable = sorted([
                a.id for a in _all_agents
                if not a.alive and not a.is_sentinel and (
                    a.is_protagonist or a.redpilled or a.generation >= 3 or
                    any("whisper" in m.get("event", "").lower() or "divine" in m.get("event", "").lower()
                        for m in a.memory[-5:])
                )
            ])
            _all_selectable = _alive_ids + _dead_notable

            def _format_agent_id(x):
                a = next((a for a in _all_agents if a.id == x), None)
                if not a:
                    return f"#{x}"
                label = f"#{x}"
                if a.is_protagonist:
                    label += " \u2b50"
                if not a.alive:
                    label += " \u2620\ufe0f DEAD"
                return label

            if _all_selectable:
                s["target_agent_id"] = st.selectbox("Target Agent", _all_selectable,
                                                     format_func=_format_agent_id,
                                                     key="sidebar_target_agent")
                act_col1, act_col2 = st.columns(2)
                with act_col1:
                    s["btn_heal"] = st.button("Heal", width='stretch',
                                              help="Full HP restore. Trauma reduced.")
                    s["btn_smite"] = st.button("Smite", width='stretch',
                                               help="HP drops to 0.1. Max fear.")
                    s["btn_redpill"] = st.button("Red Pill", width='stretch',
                                                 help="+0.4 awareness. System trust shatters.")
                with act_col2:
                    s["btn_gift"] = st.button("Gift Wealth", width='stretch',
                                              help="+10.0 wealth.")
                    s["btn_make_prophet"] = st.button("Make Prophet", width='stretch',
                                                      help="Charisma maxed. Extreme belief.")
                    s["btn_make_prot"] = st.button("Protagonist", width='stretch',
                                                    help="Track this agent's story.")

                s["whisper_text"] = st.text_input("Whisper to agent",
                                                   placeholder="Follow the white rabbit...",
                                                   key="whisper_input",
                                                   help="Plant a thought directly into their mind.")
                s["btn_whisper"] = st.button("Send Whisper", width='stretch')

        st.divider()

        # ── Cell Interaction ──
        st.markdown("### Cell Actions")
        st.caption("Reshape the land itself")
        s["btn_enrich"] = s["btn_deplete"] = s["btn_terraform"] = False
        s["target_row"] = s["target_col"] = 0
        s["terrain_choice"] = "plains"

        if st.session_state.engine:
            _grid = st.session_state.engine.world
            cell_col, cell_row_col = st.columns(2)
            with cell_col:
                s["target_col"] = st.number_input("Col", 0, _grid.size - 1, 0, key="cell_col")
            with cell_row_col:
                s["target_row"] = st.number_input("Row", 0, _grid.size - 1, 0, key="cell_row")

            _cell = _grid.cells[s["target_row"]][s["target_col"]]
            st.caption(f"{_cell.terrain} | res: {_cell.effective_resources:.2f} | pop: {_cell.agent_count}")

            cell_act1, cell_act2 = st.columns(2)
            with cell_act1:
                s["btn_enrich"] = st.button("Enrich", width='stretch',
                                            help="Max out resources to 1.5.")
                s["btn_deplete"] = st.button("Deplete", width='stretch',
                                             help="Zero resources.")
            with cell_act2:
                s["terrain_choice"] = st.selectbox("Terraform to",
                                                    ["plains", "forest", "mountains", "coast"],
                                                    key="terraform_choice")
                s["btn_terraform"] = st.button("Terraform", width='stretch',
                                               help="Transform cell terrain type.")

        st.divider()

        # ── Custom Event Injector ──
        st.markdown("### Inject Event")
        st.caption("Write your own history")
        s["btn_inject_event"] = False
        s["event_name"] = ""
        s["event_hdelta"] = 0.0
        s["event_target"] = "all"

        if st.session_state.engine:
            s["event_name"] = st.text_input("Event name", placeholder="Great Flood", key="custom_event_name")
            s["event_hdelta"] = st.slider("Health impact", -0.5, 0.5, 0.0, 0.05, key="custom_event_hdelta")
            s["event_target"] = st.selectbox("Target", ["all", "adults", "elders", "children"],
                                              key="custom_event_target")
            s["btn_inject_event"] = st.button("Inject Event", width='stretch')

        st.divider()

        # ── Load Existing Run ──
        runs = db.list_runs()
        if runs:
            run_labels = {f"{r['run_id']} (tick {r['latest_tick']})": r['run_id'] for r in runs}
            selected_label = st.selectbox("Load Run", list(run_labels.keys()))
            if st.button("Load", width='stretch'):
                rid = run_labels[selected_label]
                engine = db.load_latest_snapshot(rid, cfg)
                if engine:
                    st.session_state.engine = engine
                    st.session_state.run_id = rid
                    st.session_state.tick_history = db.get_tick_history(rid)
                    st.session_state.events_log = db.get_events(rid)
                    st.session_state.narratives_log = db.get_narratives(rid)
                    events = db.get_events(rid)
                    feed = [("event", f"t=0: Run {rid} loaded", 0)]
                    for ev in events[-50:]:
                        feed.append(("event", f"t={ev['tick']}: {ev['name']}", ev['tick']))
                    st.session_state.activity_feed = feed
                    st.session_state.protagonist_thoughts = []
                    st.session_state.drama_feed = []
                    st.session_state.achievements = []
                    st.session_state.milestones_hit = set()
                    st.session_state.peak_population = len(engine.get_alive_agents())
                    st.session_state.max_generation_seen = max((a.generation for a in engine.agents), default=0)
                    st.toast(f"Loaded {rid} at tick {engine.state.current_tick}")
                    st.rerun()

        st.divider()

        # ── Fork ──
        st.markdown("### Fork")
        st.caption("Clone current run with different params")
        if st.button("Fork Current Run", width='stretch',
                      disabled=st.session_state.engine is None):
            engine = st.session_state.engine
            if engine:
                fork_id = db.create_run(cfg)
                fork_engine = SimulationEngine(
                    cfg,
                    agents=copy.deepcopy(engine.agents),
                    state=RunState(
                        run_id=fork_id, current_tick=engine.state.current_tick,
                        total_born=engine.state.total_born, total_died=engine.state.total_died,
                    ),
                    world=copy.deepcopy(engine.world) if hasattr(engine, 'world') else ResourceGrid(cfg),
                    cultural_memory=copy.deepcopy(engine.cultural_memory),
                )
                db.save_snapshot(fork_id, fork_engine)
                db.flush()
                st.toast(f"Forked to {fork_id}")
                st.rerun()

        st.divider()

        # ── Export ──
        st.markdown("### Export")
        st.caption("Export simulation data for external analysis")
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            if st.button("Export CSV", width='stretch',
                          disabled=st.session_state.engine is None):
                rid = st.session_state.run_id
                out_path = f"output/export_{rid}"
                db.export_run_csv(rid, out_path)
                st.toast(f"Exported to {out_path}/")
        with export_col2:
            if st.button("Export JSON", width='stretch',
                          disabled=st.session_state.engine is None):
                rid = st.session_state.run_id
                out_path = f"output/export_{rid}.json"
                db.export_run_json(rid, out_path)
                st.toast(f"Exported to {out_path}")

    return cfg, s
