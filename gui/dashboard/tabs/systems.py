import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.agents import EMOTION_NAMES, SKILL_NAMES


def render_emotions_tab(alive):
    with st.expander("What is this?", expanded=False):
        st.markdown("""
**Emotions** drive agent behavior. Each agent has 5 emotions on a 0-1 scale:

- **Happiness** — Increases from good health, bonds, and wealth. Happy agents cooperate more and learn faster.
- **Fear** — Spikes from danger, death nearby, and low resources. Fearful agents flee and avoid risks.
- **Anger** — Rises from rivalry, injury, and injustice. Angry agents are more aggressive and competitive.
- **Grief** — Triggered by death of bonded agents. Slows learning and can lead to isolation.
- **Hope** — Grows from achievements, breakthroughs, and strong bonds. Hopeful agents explore and take risks.

Emotions are **contagious** — they spread between nearby agents through social bonds.
**Trauma** (0-1) accumulates from witnessing death, combat, and hardship. It permanently distorts emotions and decision-making.
""")
    if alive:
        st.markdown("#### Emotional Landscape")

        # Average emotions gauges
        avg_emo = {}
        non_sentinels = [a for a in alive if not a.is_sentinel]
        if non_sentinels:
            for emo in EMOTION_NAMES:
                avg_emo[emo] = sum(a.emotions.get(emo, 0) for a in non_sentinels) / len(non_sentinels)

            emo_colors = {"happiness": "#00ff88", "fear": "#ff4466", "anger": "#ff8844",
                          "grief": "#aa66ff", "hope": "#00ccff"}

            emo_help = {
                "happiness": "Average joy. High = peaceful society. Low = unrest.",
                "fear": "Average fear. High = population in danger or recently traumatized.",
                "anger": "Average anger. High = conflict and rivalry escalating.",
                "grief": "Average grief. High = many recent deaths among bonded agents.",
                "hope": "Average hope. High = breakthroughs and strong communities.",
            }
            emo_cols = st.columns(5)
            for i, emo in enumerate(EMOTION_NAMES):
                with emo_cols[i]:
                    st.metric(emo.capitalize(), f"{avg_emo[emo]:.2f}", help=emo_help.get(emo, ""))

            # Emotion radar for population
            fig_emo_radar = go.Figure()
            emo_vals = [avg_emo.get(e, 0) for e in EMOTION_NAMES]
            fig_emo_radar.add_trace(go.Scatterpolar(
                r=emo_vals + [emo_vals[0]],
                theta=[e.capitalize() for e in EMOTION_NAMES] + [EMOTION_NAMES[0].capitalize()],
                fill="toself", fillcolor="rgba(255,170,0,0.15)",
                line=dict(color="#ffaa00", width=2), name="Population Avg",
            ))
            fig_emo_radar.update_layout(
                template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                height=300, margin=dict(t=30, b=20, l=50, r=50),
                polar=dict(bgcolor="#040f04",
                           radialaxis=dict(visible=True, range=[0, 1], gridcolor="#0a2a0a"),
                           angularaxis=dict(gridcolor="#0a2a0a")),
                font=dict(family="JetBrains Mono", color="#5a8a5a"),
                showlegend=False,
            )
            st.plotly_chart(fig_emo_radar, width='stretch')

            # Dominant emotion distribution
            col_dom, col_trauma = st.columns(2)
            with col_dom:
                dom_counts = {}
                for a in non_sentinels:
                    dom = a.dominant_emotion
                    dom_counts[dom] = dom_counts.get(dom, 0) + 1
                fig_dom = go.Figure(go.Pie(
                    labels=list(dom_counts.keys()),
                    values=list(dom_counts.values()),
                    marker=dict(colors=[emo_colors.get(e, "#888") for e in dom_counts.keys()]),
                    hole=0.4, textinfo="label+percent",
                    textfont=dict(color="#b0d0b0"),
                ))
                fig_dom.update_layout(
                    template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                    height=250, margin=dict(t=30, b=10), title="Dominant Emotion",
                    font=dict(family="JetBrains Mono", color="#5a8a5a"), showlegend=False,
                )
                st.plotly_chart(fig_dom, width='stretch')

            with col_trauma:
                trauma_agents = [a for a in non_sentinels if a.trauma > 0.1]
                st.metric("Traumatized Agents", len(trauma_agents),
                          help="Agents with trauma > 0.1. Trauma makes agents learn slower, bond less, and make worse decisions.")
                st.metric("Avg Trauma", f"{sum(a.trauma for a in non_sentinels) / len(non_sentinels):.3f}",
                          help="Population-wide trauma level. High values indicate a civilization scarred by war, famine, or mass death.")
                st.metric("Emotional Intensity", f"{sum(a.emotional_intensity for a in non_sentinels) / len(non_sentinels):.3f}",
                          help="How strongly agents feel emotions on average. High intensity = volatile society (rapid mood swings, emotional contagion).")
                if trauma_agents:
                    st.caption("Most traumatized:")
                    for a in sorted(trauma_agents, key=lambda a: -a.trauma)[:5]:
                        st.text(f"  #{a.id}: trauma={a.trauma:.2f} (age {a.age}, {a.dominant_emotion})")
    else:
        st.info("No agents alive.")


def render_factions_tab(engine, alive):
    with st.expander("What is this?", expanded=False):
        st.markdown("""
**Factions** are ideological groups that emerge naturally when agents with similar beliefs cluster together.

- Agents have **4 belief axes**: individualism, tradition, system trust, and spirituality (each -1 to +1).
- When enough agents share similar beliefs, they form a faction with a **leader** and **core ideology**.
- Factions provide **learning bonuses** to members and create a sense of belonging.
- If beliefs diverge too much, a **schism** can split a faction in two.
- **Prophets** (agents with extreme charisma and beliefs) can found new factions.
- Factions with opposing beliefs and overlapping territory may declare **war**, causing combat casualties.

**Extremism** measures how far an agent's beliefs deviate from center (0 = moderate, 1 = radical).
""")
    if alive:
        non_sentinels = [a for a in alive if not a.is_sentinel]
        st.markdown("#### Factions & Ideology")

        factions = engine.factions
        wars = engine.wars

        # Faction overview metrics
        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("Active Factions", len(factions),
                   help="Ideological groups currently active. Form when agents with similar beliefs cluster together.")
        fc2.metric("Active Wars", len(wars),
                   help="Ongoing conflicts between factions. Wars cause combat damage, deaths, and emotional trauma to members.")
        affiliated = sum(1 for a in non_sentinels if a.faction_id is not None)
        fc3.metric("Affiliated Agents", f"{affiliated}/{len(non_sentinels)}",
                   help="How many agents belong to a faction vs total. Unaffiliated agents don't benefit from faction bonuses.")
        fc4.metric("Avg Extremism", f"{sum(a.belief_extremism for a in non_sentinels) / max(1, len(non_sentinels)):.2f}",
                   help="How radical beliefs are on average (0 = everyone moderate, 1 = everyone extreme). High extremism = more factions and wars.")

        # Faction cards
        if factions:
            for faction in factions:
                members = [a for a in non_sentinels if a.faction_id == faction.id]
                leader = next((a for a in members if a.id == faction.leader_id), None)
                at_war = any(
                    w.faction_a_id == faction.id or w.faction_b_id == faction.id
                    for w in wars
                )
                war_badge = ' [AT WAR]' if at_war else ''
                resistance_badge = ' [RESISTANCE]' if faction.is_resistance else ''

                with st.expander(f"{faction.name} ({len(members)} members){war_badge}{resistance_badge}", expanded=len(factions) <= 4):
                    fc_c1, fc_c2 = st.columns(2)
                    with fc_c1:
                        st.text(f"Founded: tick {faction.formed_at}")
                        st.text(f"Leader: #{faction.leader_id}" + (f" ({leader.protagonist_name})" if leader and leader.protagonist_name else ""))
                        st.text(f"Founder: #{faction.founder_id}")
                    with fc_c2:
                        # Core beliefs
                        for axis, val in faction.core_beliefs.items():
                            label = f"{axis}: {val:+.2f}"
                            normalized = (val + 1) / 2  # map -1..1 to 0..1
                            st.progress(normalized, text=label)

            # Wars section
            if wars:
                st.markdown("#### Active Wars")
                for war in wars:
                    fa = next((f for f in factions if f.id == war.faction_a_id), None)
                    fb = next((f for f in factions if f.id == war.faction_b_id), None)
                    fa_name = fa.name if fa else f"Faction #{war.faction_a_id}"
                    fb_name = fb.name if fb else f"Faction #{war.faction_b_id}"
                    st.markdown(f"**{fa_name} vs {fb_name}**")
                    st.caption(f"Started: tick {war.started_at} | Intensity: {war.intensity:.2f} | Casualties: {war.casualties_a} / {war.casualties_b}")
        else:
            st.info("No factions yet. Run more ticks for belief clusters to form.")

        # Population belief scatter
        if non_sentinels:
            st.markdown("#### Belief Landscape")
            belief_data = [{
                "id": a.id,
                "individualism": a.beliefs.get("individualism", 0),
                "tradition": a.beliefs.get("tradition", 0),
                "system_trust": a.beliefs.get("system_trust", 0),
                "spirituality": a.beliefs.get("spirituality", 0),
                "faction": str(a.faction_id) if a.faction_id else "None",
            } for a in non_sentinels]
            bdf = pd.DataFrame(belief_data)

            fig_bel = px.scatter(
                bdf, x="individualism", y="tradition", color="faction",
                hover_data=["id", "system_trust", "spirituality"],
                title="Belief Space (Individualism vs Tradition)",
            )
            fig_bel.update_layout(
                template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                height=350, margin=dict(t=40, b=30),
                font=dict(family="JetBrains Mono", color="#5a8a5a"),
                xaxis=dict(range=[-1.1, 1.1], gridcolor="#0a2a0a", title="Collectivist <-> Individualist"),
                yaxis=dict(range=[-1.1, 1.1], gridcolor="#0a2a0a", title="Progressive <-> Traditional"),
            )
            st.plotly_chart(fig_bel, width='stretch')
    else:
        st.info("No agents alive.")


def render_economy_tab(engine, alive):
    with st.expander("What is this?", expanded=False):
        st.markdown("""
**Economy** simulates wealth creation and distribution:

- Agents **gather resources** from the terrain each tick. Rich terrain = more wealth.
- **Trade** happens between friends — both benefit. Trade rate is configurable.
- **Theft** can occur between nearby strangers, especially aggressive agents.
- When an agent dies, their wealth is **inherited** by bonded agents (mates and children first).
- **Faction taxes** redistribute wealth among faction members.
- The **Gini Index** (0-1) measures inequality: 0 = everyone equal, 0.4 = healthy economy, 0.8+ = extreme oligarchy.
- Wealthy agents live longer (health bonus) and attract better mates.
""")
    if alive:
        non_sentinels = [a for a in alive if not a.is_sentinel]
        st.markdown("#### Economy & Wealth")

        if non_sentinels:
            wealth_values = sorted(a.wealth for a in non_sentinels)
            n = len(wealth_values)
            total_wealth = sum(wealth_values)
            avg_wealth = total_wealth / n if n else 0
            max_wealth = max(wealth_values) if wealth_values else 0

            ec1, ec2, ec3, ec4 = st.columns(4)
            ec1.metric("Total Wealth", f"{total_wealth:.1f}", help="Sum of all agent wealth. Grows as agents gather resources each tick.")
            ec2.metric("Avg Wealth", f"{avg_wealth:.2f}", help="Mean wealth per agent. Low = subsistence, High = prosperous civilization.")
            ec3.metric("Max Wealth", f"{max_wealth:.2f}", help="The richest agent. Compare with Avg to see inequality.")
            # Gini coefficient
            if n > 1 and total_wealth > 0:
                sum_diff = sum(abs(wealth_values[i] - wealth_values[j])
                               for i in range(min(n, 50)) for j in range(i + 1, min(n, 50)))
                sample_n = min(n, 50)
                gini = sum_diff / (sample_n * sample_n * (total_wealth / n)) if total_wealth > 0 else 0
                ec4.metric("Gini Index", f"{min(gini, 1.0):.3f}", help="Inequality measure. 0.0 = perfect equality, 0.4 = healthy capitalism, 0.6+ = oligarchy, 0.9+ = one agent owns everything.")
            else:
                ec4.metric("Gini Index", "N/A", help="Inequality measure. Requires 2+ agents with nonzero wealth.")

            # Wealth distribution histogram
            col_hist, col_top = st.columns(2)
            with col_hist:
                fig_wealth = go.Figure(go.Histogram(
                    x=[a.wealth for a in non_sentinels], nbinsx=20,
                    marker_color="#00ff88", opacity=0.7,
                ))
                fig_wealth.update_layout(
                    template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                    height=250, margin=dict(t=30, b=30), title="Wealth Distribution",
                    font=dict(family="JetBrains Mono", color="#5a8a5a"),
                    xaxis=dict(title="Wealth"), yaxis=dict(title="Count"),
                )
                st.plotly_chart(fig_wealth, width='stretch')

            with col_top:
                st.markdown("**Wealthiest Agents**")
                top_wealthy = sorted(non_sentinels, key=lambda a: -a.wealth)[:10]
                for rank, a in enumerate(top_wealthy, 1):
                    faction_str = f" [F#{a.faction_id}]" if a.faction_id else ""
                    st.text(f"  {rank}. #{a.id}: {a.wealth:.2f}{faction_str} (gen {a.generation})")

            # Wealth by faction
            if engine.factions:
                st.markdown("#### Wealth by Faction")
                faction_wealth = {}
                for faction in engine.factions:
                    members = [a for a in non_sentinels if a.faction_id == faction.id]
                    if members:
                        faction_wealth[faction.name] = sum(a.wealth for a in members) / len(members)
                unaffiliated = [a for a in non_sentinels if a.faction_id is None]
                if unaffiliated:
                    faction_wealth["Unaffiliated"] = sum(a.wealth for a in unaffiliated) / len(unaffiliated)

                if faction_wealth:
                    fig_fw = go.Figure(go.Bar(
                        x=list(faction_wealth.keys()),
                        y=list(faction_wealth.values()),
                        marker_color="#ffaa00", opacity=0.8,
                    ))
                    fig_fw.update_layout(
                        template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                        height=220, margin=dict(t=30, b=30), title="Avg Wealth per Faction",
                        font=dict(family="JetBrains Mono", color="#5a8a5a"),
                    )
                    st.plotly_chart(fig_fw, width='stretch')
    else:
        st.info("No agents alive.")


def render_matrix_tab(engine, alive):
    with st.expander("What is this?", expanded=False):
        st.markdown("""
**The Matrix** is a meta-layer inspired by the Matrix films. Your agents live in a simulation — and some may realize it.

- **Awareness** (0-1): How much an agent suspects their world isn't real. Grows slowly from curiosity, glitches, and contact with awakened agents.
- **Awakened / Redpilled**: Agents who have broken through. They see the code, resist the system, and spread awareness to others.
- **The Anomaly (The One)**: A single extraordinary agent who emerges when conditions are right. Reality bends around them.
- **Sentinels**: System-deployed agents that hunt awakened agents and inject "comfort" to suppress awareness.
- **Control Index** (0-1): How well the Matrix maintains stability. Below 0.5 = system is failing. Below 0.2 = cycle reset imminent.
- **Cycle Reset**: When total awareness exceeds the threshold, the Architect wipes everything and starts fresh. Agents lose awareness but keep other stats.
- **Glitches**: Random déjà vu moments that raise awareness in curious agents.
""")
    if alive:
        non_sentinels = [a for a in alive if not a.is_sentinel]
        ms = engine.matrix_state
        st.markdown("#### The Matrix")

        # System status
        mx1, mx2, mx3, mx4, mx5 = st.columns(5)
        mx1.metric("Cycle", ms.cycle_number, help="How many times the Matrix has been reset. Each reset wipes awareness but agents start fresh.")
        mx2.metric("Control Index", f"{ms.control_index:.2f}", help="System stability. 1.0 = total control. Below 0.5 = the system is losing grip. Below 0.2 = cycle reset imminent.")
        mx3.metric("Total Awareness", f"{ms.total_awareness:.2f}", help="Sum of all agents' awareness. When this exceeds the reset threshold, the Architect considers wiping the simulation.")
        sentinels = [a for a in alive if a.is_sentinel]
        mx4.metric("Sentinels", len(sentinels), help="Agents deployed by the system to suppress awareness. They hunt redpilled agents and inject comfort to lower awareness.")
        redpilled = [a for a in non_sentinels if a.redpilled]
        mx5.metric("Redpilled", len(redpilled), help="Agents who have seen through the simulation. They resist the system, spread awareness to others, and may become The One.")

        # Anomaly status
        if ms.anomaly_id:
            anomaly = next((a for a in alive if a.id == ms.anomaly_id), None)
            if anomaly:
                st.markdown(f"""
                <div class="era-banner" style="border-color: #ffd700;">
                    <div class="era-name" style="color: #ffd700;">THE ANOMALY DETECTED</div>
                    <div class="era-desc">Agent #{anomaly.id} {f'"{anomaly.protagonist_name}"' if anomaly.protagonist_name else ''} | Awareness: {anomaly.awareness:.2f} | HP: {anomaly.health:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

        # Awareness distribution
        col_aware, col_trust = st.columns(2)
        with col_aware:
            if non_sentinels:
                fig_aware = go.Figure(go.Histogram(
                    x=[a.awareness for a in non_sentinels], nbinsx=20,
                    marker_color="#aa66ff", opacity=0.7,
                ))
                fig_aware.update_layout(
                    template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                    height=250, margin=dict(t=30, b=30), title="Awareness Distribution",
                    font=dict(family="JetBrains Mono", color="#5a8a5a"),
                    xaxis=dict(range=[0, 1], title="Awareness"),
                )
                st.plotly_chart(fig_aware, width='stretch')

        with col_trust:
            if non_sentinels:
                fig_trust = go.Figure(go.Histogram(
                    x=[a.beliefs.get("system_trust", 0) for a in non_sentinels], nbinsx=20,
                    marker_color="#00ccff", opacity=0.7,
                ))
                fig_trust.update_layout(
                    template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                    height=250, margin=dict(t=30, b=30), title="System Trust Distribution",
                    font=dict(family="JetBrains Mono", color="#5a8a5a"),
                    xaxis=dict(range=[-1, 1], title="Skeptic <-> Trusting"),
                )
                st.plotly_chart(fig_trust, width='stretch')

        # Matrix world map: show awareness as color overlay
        if non_sentinels:
            st.markdown("#### Awareness Map")
            fig_mx_map = go.Figure()

            # Regular agents colored by awareness
            reg = [a for a in non_sentinels if not a.redpilled and not a.is_anomaly]
            if reg:
                fig_mx_map.add_trace(go.Scatter(
                    x=[a.x for a in reg], y=[a.y for a in reg],
                    mode="markers", name="Asleep",
                    marker=dict(
                        size=6, color=[a.awareness for a in reg],
                        colorscale=[[0, "#0a2a0a"], [0.5, "#aa66ff"], [1.0, "#ff4466"]],
                        cmin=0, cmax=1, showscale=True,
                        colorbar=dict(title="Awareness"),
                    ),
                    hovertext=[f"#{a.id} aw={a.awareness:.2f}" for a in reg],
                    hoverinfo="text",
                ))

            # Redpilled agents
            if redpilled:
                fig_mx_map.add_trace(go.Scatter(
                    x=[a.x for a in redpilled], y=[a.y for a in redpilled],
                    mode="markers", name="Redpilled",
                    marker=dict(size=10, color="#ff4466", symbol="diamond", line=dict(width=1, color="#ffd700")),
                    hovertext=[f"#{a.id} REDPILLED aw={a.awareness:.2f}" for a in redpilled],
                    hoverinfo="text",
                ))

            # Anomaly
            if ms.anomaly_id:
                anomaly = next((a for a in alive if a.id == ms.anomaly_id), None)
                if anomaly:
                    fig_mx_map.add_trace(go.Scatter(
                        x=[anomaly.x], y=[anomaly.y],
                        mode="markers+text", name="The One",
                        marker=dict(size=18, color="#ffd700", symbol="star", line=dict(width=2, color="#ff4466")),
                        text=["THE ONE"], textposition="top center",
                        textfont=dict(size=10, color="#ffd700"),
                    ))

            # Sentinels
            if sentinels:
                fig_mx_map.add_trace(go.Scatter(
                    x=[a.x for a in sentinels], y=[a.y for a in sentinels],
                    mode="markers", name="Sentinels",
                    marker=dict(size=12, color="#ff0000", symbol="x", line=dict(width=2, color="#ff4466")),
                    hovertext=[f"Sentinel #{a.id} HP={a.health:.2f}" for a in sentinels],
                    hoverinfo="text",
                ))

            fig_mx_map.update_layout(
                template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                height=400, margin=dict(t=10, b=10, l=10, r=10),
                font=dict(family="JetBrains Mono", color="#5a8a5a"),
                xaxis=dict(range=[0, 1], showticklabels=False, showgrid=False),
                yaxis=dict(range=[0, 1], showticklabels=False, showgrid=False, scaleanchor="x"),
                legend=dict(orientation="h", y=1.05),
            )
            st.plotly_chart(fig_mx_map, width='stretch')

        # Glitch log and oracle info
        gl_col, or_col = st.columns(2)
        with gl_col:
            st.markdown("**Matrix Stats**")
            st.text(f"Glitches this cycle: {ms.glitches_this_cycle}")
            st.text(f"Sentinels deployed (total): {ms.sentinels_deployed}")
            st.text(f"Ticks since reset: {ms.ticks_since_reset}")
            st.text(f"Reset threshold: {ms.reset_threshold}")
        with or_col:
            st.markdown("**The Oracle**")
            if ms.oracle_target_id:
                oracle_target = next((a for a in alive if a.id == ms.oracle_target_id), None)
                if oracle_target:
                    st.text(f"Guiding: #{oracle_target.id} (aw={oracle_target.awareness:.2f})")
                    st.text(f"Curiosity: {oracle_target.traits.curiosity:.2f}")
                    st.text(f"Intelligence: {oracle_target.intelligence:.3f}")
                else:
                    st.text("Target lost")
            else:
                st.text("No target selected yet")

            # Exiles
            exiles = [a for a in alive if a.is_exile]
            if exiles:
                st.markdown("**Exile Programs**")
                for ex in exiles:
                    st.text(f"  #{ex.id} (age {ex.age}, HP {ex.health:.2f})")
    else:
        st.info("No agents alive.")


def render_culture_tab(engine, summary, cfg):
    with st.expander("What is this?", expanded=False):
        st.markdown("""
**Cultural Memory** is how civilization preserves knowledge across generations.

- When agents die, their skills feed into a **knowledge pool** — the accumulated wisdom of the dead.
- The pool gradually raises the **cultural floor** — the minimum skill level that newborns start with.
- This means each generation starts smarter than the last (standing on the shoulders of giants).
- If population crashes (mass death, extinction), the floors **decay** — a dark age where knowledge is lost.
- The floor has a **cap** (red dotted line in the chart) that prevents newborns from starting too powerful.
- The radar chart compares the living population's actual skills vs the inherited floor.
""")
    cm = engine.cultural_memory

    st.markdown("#### Civilization Knowledge Floors")
    st.caption("The minimum skill level newborns inherit from accumulated cultural knowledge")

    floor_df = pd.DataFrame([
        {"Skill": k, "Floor": v, "Pool": cm.knowledge_pool.get(k, 0)}
        for k, v in cm.skill_floors.items()
    ])

    fig_floor = go.Figure()
    fig_floor.add_trace(go.Bar(
        x=floor_df["Skill"], y=floor_df["Floor"], name="Cultural Floor",
        marker_color="#00ff88", opacity=0.8,
    ))
    fig_floor.add_trace(go.Bar(
        x=floor_df["Skill"], y=floor_df["Pool"], name="Knowledge Pool",
        marker_color="#00ccff", opacity=0.5,
    ))
    fig_floor.add_hline(y=cfg.knowledge.cultural_memory.floor_cap,
                        line_dash="dot", line_color="#ff4466",
                        annotation_text=f"Cap: {cfg.knowledge.cultural_memory.floor_cap}")
    fig_floor.update_layout(
        template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
        height=300, margin=dict(t=30, b=30), barmode="group",
        font=dict(family="JetBrains Mono", color="#5a8a5a"),
        yaxis=dict(range=[0, max(0.6, cfg.knowledge.cultural_memory.floor_cap + 0.1)],
                   gridcolor="#0a2a0a"),
    )
    st.plotly_chart(fig_floor, width='stretch')

    # Skills radar comparing cultural floor vs population average
    if summary.get("avg_skills"):
        avg = summary["avg_skills"]
        floors = cm.skill_floors

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=[avg.get(s, 0) for s in SKILL_NAMES] + [avg.get(SKILL_NAMES[0], 0)],
            theta=SKILL_NAMES + [SKILL_NAMES[0]],
            fill="toself", fillcolor="rgba(255,170,0,0.15)",
            line=dict(color="#ffaa00", width=2), name="Population Avg",
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[floors.get(s, 0) for s in SKILL_NAMES] + [floors.get(SKILL_NAMES[0], 0)],
            theta=SKILL_NAMES + [SKILL_NAMES[0]],
            fill="toself", fillcolor="rgba(0,255,136,0.1)",
            line=dict(color="#00ff88", width=2, dash="dot"), name="Cultural Floor",
        ))
        fig_radar.update_layout(
            template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
            height=350, margin=dict(t=40, b=20, l=60, r=60),
            polar=dict(bgcolor="#040f04",
                       radialaxis=dict(visible=True, range=[0, 1], gridcolor="#0a2a0a"),
                       angularaxis=dict(gridcolor="#0a2a0a")),
            font=dict(family="JetBrains Mono", color="#5a8a5a"),
        )
        st.plotly_chart(fig_radar, width='stretch')
