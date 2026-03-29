import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.agents import SKILL_NAMES


def render_agents_tab(engine, alive):
    st.caption("All agents in the simulation — alive and deceased. Filter, sort, and select any agent to inspect.")
    all_agents = [a for a in engine.agents if not a.is_sentinel]
    if not all_agents:
        st.error("No agents in simulation.")
        return

    # ── Scatter plot (alive only) ──
    if alive:
        agent_data = [{
            "id": a.id, "x": a.x, "y": a.y, "sex": a.sex,
            "phase": a.phase, "age": a.age,
            "health": round(a.health, 2), "intelligence": round(a.intelligence, 3),
            "generation": a.generation, "bonds": len(a.bonds),
            "is_protagonist": a.is_protagonist,
            "size": 6 + a.intelligence * 12 + (8 if a.is_protagonist else 0),
        } for a in alive]
        adf = pd.DataFrame(agent_data)

        phase_colors = {"infant": "#00ff88", "child": "#00ccff", "adolescent": "#ffaa00",
                        "adult": "#ff4466", "elder": "#aa66ff"}

        fig_scatter = px.scatter(
            adf, x="x", y="y", color="phase", size="size",
            hover_data=["id", "sex", "age", "health", "intelligence", "generation", "bonds"],
            color_discrete_map=phase_colors,
            symbol="is_protagonist",
            symbol_map={True: "star", False: "circle"},
        )
        fig_scatter.update_layout(
            template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
            height=400, margin=dict(t=30, b=30),
            font=dict(family="JetBrains Mono", color="#5a8a5a"),
            xaxis=dict(range=[0, 1], gridcolor="#0a2a0a", title=""),
            yaxis=dict(range=[0, 1], gridcolor="#0a2a0a", title=""),
            legend=dict(orientation="h", y=1.1),
        )
        fig_scatter.update_traces(marker=dict(opacity=0.8, line=dict(width=0)))
        st.plotly_chart(fig_scatter, width='stretch')

    # ── Build full dataframe ──
    table_data = []
    for a in all_agents:
        table_data.append({
            "ID": a.id,
            "Status": "ALIVE" if a.alive else "DECEASED",
            "Sex": a.sex,
            "Phase": a.phase,
            "Age": a.age,
            "Health": round(a.health, 2),
            "IQ": round(a.intelligence, 3),
            "Gen": a.generation,
            "Bonds": len(a.bonds),
            "Children": len(a.child_ids),
            "Wealth": round(a.wealth, 1),
            "Prot": "Y" if a.is_protagonist else "",
        })
    df = pd.DataFrame(table_data)

    # ── Counts ──
    alive_count = (df["Status"] == "ALIVE").sum()
    dead_count = (df["Status"] == "DECEASED").sum()
    st.markdown(f"**{len(df)} total agents** ({alive_count} alive, {dead_count} deceased)")

    # ── Filters ──
    f1, f2, f3, f4, f5 = st.columns(5)
    with f1:
        status_filter = st.multiselect(
            "Status", ["ALIVE", "DECEASED"], default=["ALIVE", "DECEASED"],
            key="agent_status_filter",
        )
    with f2:
        all_phases = sorted(df["Phase"].unique())
        phase_filter = st.multiselect(
            "Phase", all_phases, default=all_phases,
            key="agent_phase_filter",
        )
    with f3:
        sex_filter = st.multiselect(
            "Sex", ["M", "F"], default=["M", "F"],
            key="agent_sex_filter",
        )
    with f4:
        gen_min, gen_max = int(df["Gen"].min()), int(df["Gen"].max())
        if gen_min < gen_max:
            gen_range = st.slider(
                "Generation", gen_min, gen_max, (gen_min, gen_max),
                key="agent_gen_filter",
            )
        else:
            gen_range = (gen_min, gen_max)
    with f5:
        sort_by = st.selectbox(
            "Sort by", ["ID", "Age", "Health", "IQ", "Gen", "Bonds", "Children", "Wealth"],
            key="agent_sort",
        )

    # ── Apply filters ──
    mask = (
        df["Status"].isin(status_filter) &
        df["Phase"].isin(phase_filter) &
        df["Sex"].isin(sex_filter) &
        df["Gen"].between(*gen_range)
    )
    filtered = df[mask].sort_values(sort_by, ascending=False).reset_index(drop=True)

    st.caption(f"Showing {len(filtered)} / {len(df)} agents")

    # ── Searchable text filter ──
    search = st.text_input(
        "Search by ID", placeholder="e.g. 42",
        key="agent_search",
    )
    if search.strip():
        try:
            search_id = int(search.strip().lstrip("#"))
            filtered = filtered[filtered["ID"] == search_id]
        except ValueError:
            pass

    # ── Table ──
    st.dataframe(
        filtered, width='stretch', hide_index=True,
        height=400,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Sex": st.column_config.TextColumn("Sex", width="small"),
            "Phase": st.column_config.TextColumn("Phase", width="small"),
            "Age": st.column_config.NumberColumn("Age", width="small"),
            "Health": st.column_config.ProgressColumn("Health", min_value=0, max_value=1, width="small"),
            "IQ": st.column_config.ProgressColumn("IQ", min_value=0, max_value=1, width="small"),
            "Gen": st.column_config.NumberColumn("Gen", width="small"),
            "Bonds": st.column_config.NumberColumn("Bonds", width="small"),
            "Children": st.column_config.NumberColumn("Children", width="small"),
            "Wealth": st.column_config.NumberColumn("Wealth", width="small", format="%.1f"),
            "Prot": st.column_config.TextColumn("Prot", width="small"),
        },
    )

    # ── Agent Inspector ──
    st.markdown("---")
    st.markdown("#### Agent Inspector")

    _inspectable = sorted(all_agents, key=lambda a: (a.alive, -a.id), reverse=True)
    _inspectable_ids = [a.id for a in _inspectable]

    def _fmt_inspect(x):
        a = next((a for a in engine.agents if a.id == x), None)
        if not a:
            return f"#{x}"
        parts = [f"#{x}"]
        if a.is_protagonist:
            parts.append("\u2b50")
        if not a.alive:
            parts.append("\u2620\ufe0f DECEASED")
        else:
            parts.append(f"({a.phase}, age {a.age})")
        return " ".join(parts)

    col_sel, col_info = st.columns([1, 3])
    with col_sel:
        selected_id = st.selectbox("Inspect Agent", _inspectable_ids,
                                    format_func=_fmt_inspect)
    with col_info:
        agent = next((a for a in engine.agents if a.id == selected_id), None)
        if agent:
            if not agent.alive:
                death_mem = next((m for m in reversed(agent.memory) if m.get("event") == "Died"), None)
                death_tick = death_mem["tick"] if death_mem else "?"
                st.markdown(
                    f'<div style="background:rgba(255,68,102,0.1);border:1px solid #ff4466;'
                    f'border-radius:8px;padding:8px 12px;margin-bottom:8px;'
                    f'font-family:JetBrains Mono,monospace;color:#ff4466;font-size:0.85em;">'
                    f'\u2620\ufe0f DECEASED — Died at tick {death_tick} (age {agent.age})'
                    f'</div>', unsafe_allow_html=True
                )

            ic1, ic2, ic3, ic4 = st.columns(4)
            ic1.metric("Age", f"{agent.age} / {agent.traits.max_age}")
            ic2.metric("Phase", agent.phase.upper())
            ic3.metric("Sex", agent.sex)
            ic4.metric("Gen", agent.generation)

            ic5, ic6, ic7, ic8 = st.columns(4)
            ic5.metric("Health", f"{agent.health:.2f}")
            ic6.metric("IQ", f"{agent.intelligence:.3f}")
            ic7.metric("Bonds", len(agent.bonds))
            ic8.metric("Children", len(agent.child_ids))

            # Skills radar
            fig_sk = go.Figure()
            skill_vals = [agent.skills.get(s, 0) for s in SKILL_NAMES]
            fig_sk.add_trace(go.Scatterpolar(
                r=skill_vals + [skill_vals[0]],
                theta=SKILL_NAMES + [SKILL_NAMES[0]],
                fill="toself", fillcolor="rgba(255,170,0,0.15)",
                line=dict(color="#ffaa00", width=2), name="Skills",
            ))
            fig_sk.update_layout(
                template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                height=220, margin=dict(t=30, b=10, l=40, r=40),
                polar=dict(bgcolor="#040f04",
                           radialaxis=dict(visible=True, range=[0, 1], gridcolor="#0a2a0a"),
                           angularaxis=dict(gridcolor="#0a2a0a")),
                font=dict(family="JetBrains Mono", color="#5a8a5a"),
                showlegend=False,
            )
            st.plotly_chart(fig_sk, width='stretch')

            # Traits
            with st.expander("Inherited Traits"):
                for k, v in agent.traits.to_dict().items():
                    if k == "max_age":
                        st.text(f"max_age: {v}")
                    else:
                        st.progress(v, text=f"{k}: {v:.2f}")

            # Bonds
            if agent.bonds:
                with st.expander(f"Bonds ({len(agent.bonds)})"):
                    bond_data = [{"Type": b.bond_type, "Target": f"#{b.target_id}",
                                  "Strength": f"{b.strength:.2f}", "Formed": b.formed_at}
                                 for b in agent.bonds]
                    st.dataframe(pd.DataFrame(bond_data), width='stretch', hide_index=True)

            # Family Tree
            with st.expander("Family Tree"):
                all_agents_map = {a.id: a for a in engine.agents}

                st.markdown("**Lineage:**")

                if agent.parent_ids:
                    parent_strs = []
                    for pid in agent.parent_ids:
                        p = all_agents_map.get(pid)
                        if p:
                            status = "alive" if p.alive else f"died age {p.age}"
                            parent_strs.append(f"  #{pid} ({p.sex}, gen {p.generation}, {status})")
                        else:
                            parent_strs.append(f"  #{pid} (unknown)")
                    st.markdown("Parents:")
                    for ps in parent_strs:
                        st.text(ps)

                    gp_found = False
                    for pid in agent.parent_ids:
                        p = all_agents_map.get(pid)
                        if p and p.parent_ids:
                            if not gp_found:
                                st.markdown("Grandparents:")
                                gp_found = True
                            for gpid in p.parent_ids:
                                gp = all_agents_map.get(gpid)
                                if gp:
                                    st.text(f"    #{gpid} ({gp.sex}, gen {gp.generation})")
                else:
                    st.caption("First generation - no recorded parents")

                if agent.child_ids:
                    st.markdown(f"Children ({len(agent.child_ids)}):")
                    for cid in agent.child_ids:
                        child = all_agents_map.get(cid)
                        if child:
                            status = "alive" if child.alive else f"died age {child.age}"
                            st.text(f"  #{cid} ({child.sex}, gen {child.generation}, {status})")

                    gc_ids = []
                    for cid in agent.child_ids:
                        child = all_agents_map.get(cid)
                        if child:
                            gc_ids.extend(child.child_ids)
                    if gc_ids:
                        st.markdown(f"Grandchildren ({len(gc_ids)}):")
                        for gcid in gc_ids[:10]:
                            gc = all_agents_map.get(gcid)
                            if gc:
                                st.text(f"    #{gcid} ({gc.sex}, gen {gc.generation})")
                        if len(gc_ids) > 10:
                            st.caption(f"  ...and {len(gc_ids) - 10} more")

                def count_descendants(agent_id, depth=0):
                    if depth > 10:
                        return 0
                    a = all_agents_map.get(agent_id)
                    if not a:
                        return 0
                    count = len(a.child_ids)
                    for cid in a.child_ids:
                        count += count_descendants(cid, depth + 1)
                    return count

                total_desc = count_descendants(agent.id)
                if total_desc > 0:
                    st.markdown(f"**Dynasty size: {total_desc} total descendants**")

            # Memory
            if agent.memory:
                with st.expander(f"Memory ({len(agent.memory)})"):
                    for m in agent.memory[-15:]:
                        st.text(f"t={m['tick']:>5d}  {m['event']}")
