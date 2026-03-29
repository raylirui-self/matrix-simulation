import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def render_social_tab(alive):
    with st.expander("What is this?", expanded=False):
        st.markdown("""
**Social bonds** are the relationships between agents. They form naturally through proximity and shared experiences.

- **Family** — parent-child bonds, formed at birth. Permanent.
- **Friend** — mutual bonds that form when agents spend time near each other. Boosts skill learning.
- **Mate** — romantic partners who can reproduce together. Strongest emotional bond.
- **Rival** — competitive/hostile bonds. Can escalate to conflict. Formed from resource competition or personality clashes.

Bond **strength** (0-1) decays over time if agents drift apart, and grows when they stay close.
The **network graph** below shows how agents are connected — clusters indicate communities.
""")
    if alive:
        # Bond type distribution
        bond_counts = {"family": 0, "friend": 0, "rival": 0, "mate": 0}
        for a in alive:
            for b in a.bonds:
                bond_counts[b.bond_type] = bond_counts.get(b.bond_type, 0) + 1

        bc1, bc2, bc3, bc4 = st.columns(4)
        bc1.metric("Family Bonds", bond_counts["family"],
                   help="Parent-child bonds. Formed at birth, last a lifetime.")
        bc2.metric("Friendships", bond_counts["friend"],
                   help="Mutual bonds from proximity. Friends learn skills faster together.")
        bc3.metric("Rivalries", bond_counts["rival"],
                   help="Hostile bonds. Rivals compete for resources and mates. Can trigger faction wars.")
        bc4.metric("Mate Bonds", bond_counts["mate"],
                   help="Romantic bonds. Mates can reproduce and share emotional support.")

        # Bond type pie + strength histogram side by side
        col_pie, col_hist = st.columns(2)

        with col_pie:
            fig_pie = go.Figure(go.Pie(
                labels=list(bond_counts.keys()),
                values=list(bond_counts.values()),
                marker=dict(colors=["#00ff88", "#00ccff", "#ff4466", "#ffaa00"]),
                hole=0.4,
                textinfo="label+percent",
                textfont=dict(color="#b0d0b0"),
            ))
            fig_pie.update_layout(
                template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                height=280, margin=dict(t=30, b=10), title="Bond Distribution",
                font=dict(family="JetBrains Mono", color="#5a8a5a"),
                showlegend=False,
            )
            st.plotly_chart(fig_pie, width='stretch')

        with col_hist:
            all_bonds = [(b.bond_type, b.strength) for a in alive for b in a.bonds]
            if all_bonds:
                bdf = pd.DataFrame(all_bonds, columns=["type", "strength"])
                fig_bdist = px.histogram(
                    bdf, x="strength", color="type", nbins=20, barmode="overlay",
                    color_discrete_map={"family": "#00ff88", "friend": "#00ccff",
                                         "rival": "#ff4466", "mate": "#ffaa00"},
                    opacity=0.6,
                )
                fig_bdist.update_layout(
                    template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                    height=280, margin=dict(t=30, b=30),
                    font=dict(family="JetBrains Mono", color="#5a8a5a"),
                    title="Bond Strength Distribution",
                )
                st.plotly_chart(fig_bdist, width='stretch')

        # Social network visualization
        st.markdown("#### Social Network")
        st.caption("Showing strongest 100 bonds | Node size = bond count | Color = generation")

        all_edges = []
        for a in alive:
            for b in a.bonds:
                if b.target_id > a.id:
                    all_edges.append((a.id, b.target_id, b.bond_type, b.strength, a.x, a.y))

        all_edges.sort(key=lambda e: -e[3])
        top_edges = all_edges[:100]

        if top_edges:
            agent_map = {a.id: a for a in alive}
            fig_net = go.Figure()

            edge_colors = {"family": "#00ff88", "friend": "#00ccff", "rival": "#ff4466", "mate": "#ffaa00"}
            for src_id, tgt_id, btype, strength, sx, sy in top_edges:
                tgt = agent_map.get(tgt_id)
                if tgt:
                    fig_net.add_trace(go.Scatter(
                        x=[sx, tgt.x], y=[sy, tgt.y], mode="lines",
                        line=dict(color=edge_colors.get(btype, "#444"), width=strength * 2),
                        opacity=0.4, showlegend=False,
                    ))

            node_x = [a.x for a in alive]
            node_y = [a.y for a in alive]
            node_color = [a.generation for a in alive]
            node_text = [f"#{a.id} ({a.phase}, gen {a.generation}, {len(a.bonds)} bonds)" for a in alive]

            fig_net.add_trace(go.Scatter(
                x=node_x, y=node_y, mode="markers", text=node_text,
                marker=dict(size=[4 + len(a.bonds) * 1.5 for a in alive],
                            color=node_color, colorscale="Viridis",
                            showscale=True, colorbar=dict(title="Gen")),
                showlegend=False,
            ))
            fig_net.update_layout(
                template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                height=400, margin=dict(t=10, b=10),
                font=dict(family="JetBrains Mono", color="#5a8a5a"),
                xaxis=dict(range=[0, 1], showticklabels=False),
                yaxis=dict(range=[0, 1], showticklabels=False),
            )
            st.plotly_chart(fig_net, width='stretch')
    else:
        st.info("No agents alive.")
