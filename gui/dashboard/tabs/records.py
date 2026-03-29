import json

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from src.agents import SKILL_NAMES


def render_records_tab(engine, alive):
    st.caption("Records, leaderboards, and achievements. Who lived longest? Who has the most children? Which skill is most mastered? Achievements unlock as your civilization hits milestones.")
    st.markdown("#### Hall of Records")

    if alive:
        # Current records
        oldest = max(alive, key=lambda a: a.age)
        smartest = max(alive, key=lambda a: a.intelligence)
        healthiest = max(alive, key=lambda a: a.health)
        most_social = max(alive, key=lambda a: len(a.bonds))
        most_children = max(engine.agents, key=lambda a: len(a.child_ids))
        highest_gen = max(alive, key=lambda a: a.generation)

        # All-time records (include dead agents)
        all_agents = engine.agents
        most_children_ever = max(all_agents, key=lambda a: len(a.child_ids))
        oldest_ever = max(all_agents, key=lambda a: a.age)

        rec_col1, rec_col2, rec_col3 = st.columns(3)

        with rec_col1:
            st.markdown(f"""
            <div class="record-card">
                <div class="record-title">ELDEST LIVING</div>
                <div class="record-value">Age {oldest.age}</div>
                <div class="record-holder">#{oldest.id} ({oldest.sex}, Gen {oldest.generation})</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="record-card">
                <div class="record-title">BRIGHTEST MIND</div>
                <div class="record-value">IQ {smartest.intelligence:.3f}</div>
                <div class="record-holder">#{smartest.id} (Age {smartest.age}, Gen {smartest.generation})</div>
            </div>
            """, unsafe_allow_html=True)

        with rec_col2:
            st.markdown(f"""
            <div class="record-card">
                <div class="record-title">MOST CONNECTED</div>
                <div class="record-value">{len(most_social.bonds)} bonds</div>
                <div class="record-holder">#{most_social.id} (Age {most_social.age})</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="record-card">
                <div class="record-title">MOST PROLIFIC (LIVING)</div>
                <div class="record-value">{len(most_children.child_ids)} children</div>
                <div class="record-holder">#{most_children.id} ({most_children.sex}, Gen {most_children.generation})</div>
            </div>
            """, unsafe_allow_html=True)

        with rec_col3:
            st.markdown(f"""
            <div class="record-card">
                <div class="record-title">PEAK HEALTH</div>
                <div class="record-value">HP {healthiest.health:.2f}</div>
                <div class="record-holder">#{healthiest.id} (Age {healthiest.age})</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="record-card">
                <div class="record-title">HIGHEST GENERATION</div>
                <div class="record-value">Gen {highest_gen.generation}</div>
                <div class="record-holder">#{highest_gen.id} (Age {highest_gen.age})</div>
            </div>
            """, unsafe_allow_html=True)

        # All-time section
        st.markdown("#### All-Time Records")
        at_col1, at_col2, at_col3 = st.columns(3)
        with at_col1:
            st.markdown(f"""
            <div class="record-card">
                <div class="record-title">OLDEST EVER</div>
                <div class="record-value">Age {oldest_ever.age}</div>
                <div class="record-holder">#{oldest_ever.id} ({'alive' if oldest_ever.alive else 'deceased'})</div>
            </div>
            """, unsafe_allow_html=True)
        with at_col2:
            st.markdown(f"""
            <div class="record-card">
                <div class="record-title">MOST CHILDREN EVER</div>
                <div class="record-value">{len(most_children_ever.child_ids)} children</div>
                <div class="record-holder">#{most_children_ever.id} ({'alive' if most_children_ever.alive else 'deceased'})</div>
            </div>
            """, unsafe_allow_html=True)
        with at_col3:
            st.markdown(f"""
            <div class="record-card">
                <div class="record-title">PEAK POPULATION</div>
                <div class="record-value">{st.session_state.peak_population}</div>
                <div class="record-holder">Highest population recorded</div>
            </div>
            """, unsafe_allow_html=True)

        # Skill leaderboards
        st.markdown("#### Skill Leaderboards")
        lb_cols = st.columns(5)
        for i, skill in enumerate(SKILL_NAMES):
            with lb_cols[i]:
                st.markdown(f"**{skill.upper()}**")
                top_5 = sorted(alive, key=lambda a: a.skills.get(skill, 0), reverse=True)[:5]
                for rank, a in enumerate(top_5, 1):
                    medal = ["1st", "2nd", "3rd", "4th", "5th"][rank - 1]
                    st.caption(f"{medal}: #{a.id} ({a.skills.get(skill, 0):.3f})")

    # ── Graveyard: Notable Dead Agents ──
    dead_agents = [a for a in engine.agents if not a.alive and not a.is_sentinel]
    if dead_agents:
        with st.expander(f"\u2620\ufe0f Graveyard ({len(dead_agents)} deceased)", expanded=False):
            st.caption("Notable deceased agents. Sorted by age at death. Click 'Include dead agents' in the Agents tab to inspect their full profiles.")
            # Sort by most interesting: protagonists first, then by age
            notable_dead = sorted(dead_agents,
                                   key=lambda a: (a.is_protagonist, a.generation, a.age, len(a.child_ids)),
                                   reverse=True)[:30]
            grave_data = []
            for a in notable_dead:
                tags = []
                if a.is_protagonist:
                    tags.append("\u2b50")
                if a.redpilled:
                    tags.append("\U0001f534")
                if a.is_anomaly:
                    tags.append("\U0001f7e1")
                if len(a.child_ids) > 3:
                    tags.append(f"\U0001f476x{len(a.child_ids)}")
                # Find death tick from memory
                death_tick = "?"
                for m in reversed(a.memory):
                    if m.get("event") == "Died":
                        death_tick = m.get("tick", "?")
                        break
                grave_data.append({
                    "ID": f"#{a.id}",
                    "Tags": " ".join(tags),
                    "Age": a.age,
                    "Gen": a.generation,
                    "IQ": f"{a.intelligence:.3f}",
                    "Children": len(a.child_ids),
                    "Died at": f"t={death_tick}",
                    "Last Memory": a.memory[-1]["event"][:50] if a.memory else "\u2014",
                })
            st.dataframe(pd.DataFrame(grave_data), width='stretch', hide_index=True)

    # Achievements
    st.markdown("#### Achievements Unlocked")
    st.caption("Gold = population/survival milestones | Silver = generational endurance | Bronze = tech breakthroughs | Green = intelligence thresholds. Hover for details.")
    achievements = st.session_state.achievements
    if achievements:
        achv_html = ""
        for tier, name, desc in achievements:
            achv_html += f'<span class="achievement achievement-{tier}" title="{desc}">{name}</span>'
        st.markdown(achv_html, unsafe_allow_html=True)
        st.caption(f"{len(achievements)} achievements unlocked")
    else:
        st.info("Run the simulation to unlock achievements!")

    # Civilization stats summary
    st.markdown("#### Civilization Summary")
    cs1, cs2, cs3, cs4 = st.columns(4)
    cs1.metric("Total Born", engine.state.total_born)
    cs2.metric("Total Died", engine.state.total_died)
    cs3.metric("Survival Rate", f"{(len(alive) / max(1, engine.state.total_born) * 100):.1f}%")
    cs4.metric("Avg Lifespan", f"{sum(a.age for a in engine.agents if not a.alive) / max(1, engine.state.total_died):.1f}" if engine.state.total_died > 0 else "N/A")


def render_compare_tab(db):
    st.caption("Compare multiple simulation runs side-by-side. Fork a run with different parameters, then overlay their population and intelligence curves to see how changes affect outcomes.")
    st.markdown("### Scenario Comparison")

    runs = db.list_runs()
    if len(runs) >= 2:
        run_labels = [f"{r['run_id']} (tick {r['latest_tick']})" for r in runs]
        selected = st.multiselect("Select Runs", run_labels, default=run_labels[:2])

        if len(selected) >= 2:
            fig_cmp = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                     subplot_titles=["Population", "Avg Intelligence"])
            palette = px.colors.qualitative.Set2

            for idx, label in enumerate(selected):
                rid = label.split(" ")[0]
                hist = db.get_tick_history(rid)
                if not hist:
                    continue
                cdf = pd.DataFrame(hist)
                color = palette[idx % len(palette)]

                fig_cmp.add_trace(
                    go.Scatter(x=cdf["tick"], y=cdf["alive_count"],
                               name=f"{rid} pop", line=dict(color=color, width=2)),
                    row=1, col=1,
                )
                if "avg_intelligence" in cdf.columns:
                    fig_cmp.add_trace(
                        go.Scatter(x=cdf["tick"], y=cdf["avg_intelligence"],
                                   name=f"{rid} iq", line=dict(color=color, width=2, dash="dot"),
                                   showlegend=False),
                        row=2, col=1,
                    )

            fig_cmp.update_layout(
                template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                height=500, margin=dict(t=40, b=30),
                font=dict(family="JetBrains Mono", color="#5a8a5a"),
                legend=dict(orientation="h", y=1.08),
            )
            fig_cmp.update_xaxes(gridcolor="#0a2a0a")
            fig_cmp.update_yaxes(gridcolor="#0a2a0a")
            st.plotly_chart(fig_cmp, width='stretch')

            # Config diff
            st.markdown("#### Config Differences")
            configs = {}
            for label in selected:
                rid = label.split(" ")[0]
                row = db.conn.execute(
                    "SELECT config_json FROM runs WHERE run_id = ?", (rid,)
                ).fetchone()
                if row:
                    configs[rid] = json.loads(row["config_json"])

            if len(configs) >= 2:
                def flatten(d, prefix=""):
                    items = {}
                    for k, v in d.items():
                        key = f"{prefix}.{k}" if prefix else k
                        if isinstance(v, dict):
                            items.update(flatten(v, key))
                        else:
                            items[key] = v
                    return items

                flat = {rid: flatten(c) for rid, c in configs.items()}
                all_keys = set()
                for f in flat.values():
                    all_keys.update(f.keys())

                diffs = []
                for key in sorted(all_keys):
                    vals = [flat[rid].get(key, "--") for rid in flat]
                    if len(set(str(v) for v in vals)) > 1:
                        row = {"Parameter": key}
                        for rid, val in zip(flat.keys(), vals):
                            row[rid] = val
                        diffs.append(row)

                if diffs:
                    st.dataframe(pd.DataFrame(diffs), width='stretch', hide_index=True)
                else:
                    st.caption("All configs identical. Fork with different params to compare.")
    else:
        st.info("Need 2+ runs. Use Fork in the sidebar.")
