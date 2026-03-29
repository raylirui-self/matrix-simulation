import streamlit as st
import plotly.graph_objects as go

from src.agents import PHASES


def render_world_tab(engine, alive):
    st.caption("The 8x8 terrain grid with agents overlaid. Hover over cells for resources/pressure/tech. Bond lines connect nearby agents. Protagonists are starred.")
    grid = engine.world
    grid.update_agent_counts(engine.agents)
    size = grid.size

    st.markdown("#### World Map — Terrain + Agents")

    # Build combined terrain + agents map
    fig_world = go.Figure()

    # Terrain background as shapes
    terrain_fill = {
        "plains": "rgba(74,122,58,0.3)",
        "forest": "rgba(42,90,42,0.4)",
        "mountains": "rgba(106,90,74,0.3)",
        "coast": "rgba(58,106,138,0.3)",
    }
    terrain_border = {
        "plains": "rgba(74,122,58,0.5)",
        "forest": "rgba(42,90,42,0.6)",
        "mountains": "rgba(106,90,74,0.5)",
        "coast": "rgba(58,106,138,0.5)",
    }

    for r in range(size):
        for c in range(size):
            cell = grid.cells[r][c]
            x0, x1 = c / size, (c + 1) / size
            y0, y1 = r / size, (r + 1) / size
            fig_world.add_shape(
                type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                fillcolor=terrain_fill.get(cell.terrain, "rgba(50,50,50,0.2)"),
                line=dict(color=terrain_border.get(cell.terrain, "rgba(50,50,50,0.3)"), width=1),
                layer="below",
            )
            # Cell label
            techs = ",".join(t.name[:3] for t in cell.unlocked_techs) if cell.unlocked_techs else ""
            res_pct = int(cell.effective_resources * 100)
            label = f"{cell.terrain[:3].upper()}<br>r:{res_pct}% p:{cell.agent_count}"
            if techs:
                label += f"<br>{techs}"

    # Draw bond lines between alive agents (top 60 strongest)
    all_edges = []
    for a in alive:
        for b in a.bonds:
            if b.target_id > a.id:
                all_edges.append((a, b))
    all_edges.sort(key=lambda e: -e[1].strength)

    edge_colors = {"family": "rgba(0,255,136,0.15)", "friend": "rgba(0,204,255,0.2)",
                   "rival": "rgba(255,68,102,0.2)", "mate": "rgba(255,170,0,0.3)"}
    agent_map = {a.id: a for a in alive}

    for src_agent, bond in all_edges[:60]:
        tgt = agent_map.get(bond.target_id)
        if tgt:
            fig_world.add_trace(go.Scatter(
                x=[src_agent.x, tgt.x], y=[src_agent.y, tgt.y], mode="lines",
                line=dict(color=edge_colors.get(bond.bond_type, "rgba(100,100,100,0.1)"),
                          width=bond.strength * 1.5),
                showlegend=False, hoverinfo="skip",
            ))

    # Draw agents
    phase_colors = {"infant": "#00ff88", "child": "#00ccff", "adolescent": "#ffaa00",
                    "adult": "#ff4466", "elder": "#aa66ff"}

    for phase in PHASES:
        phase_agents = [a for a in alive if a.phase == phase]
        if not phase_agents:
            continue
        fig_world.add_trace(go.Scatter(
            x=[a.x for a in phase_agents],
            y=[a.y for a in phase_agents],
            mode="markers+text",
            marker=dict(
                size=[5 + a.intelligence * 10 + (6 if a.is_protagonist else 0) for a in phase_agents],
                color=phase_colors[phase],
                opacity=0.85,
                line=dict(width=[2 if a.is_protagonist else 0 for a in phase_agents],
                          color="#ffd700"),
                symbol=["star" if a.is_protagonist else "circle" for a in phase_agents],
            ),
            text=[a.protagonist_name if a.is_protagonist and a.protagonist_name else "" for a in phase_agents],
            textposition="top center",
            textfont=dict(size=8, color="#ffd700"),
            name=phase,
            hovertext=[
                f"#{a.id} ({a.sex})<br>Age: {a.age} | Phase: {a.phase}<br>"
                f"HP: {a.health:.2f} | IQ: {a.intelligence:.3f}<br>"
                f"Gen: {a.generation} | Bonds: {len(a.bonds)}"
                for a in phase_agents
            ],
            hoverinfo="text",
        ))

    # Cell info as invisible scatter for hover
    cell_x, cell_y, cell_text = [], [], []
    for r in range(size):
        for c in range(size):
            cell = grid.cells[r][c]
            cell_x.append((c + 0.5) / size)
            cell_y.append((r + 0.5) / size)
            techs = ", ".join(t.name for t in cell.unlocked_techs) if cell.unlocked_techs else "None"
            cell_text.append(
                f"<b>{cell.terrain.upper()}</b> [{r},{c}]<br>"
                f"Resources: {cell.effective_resources:.2f}<br>"
                f"Population: {cell.agent_count} / {cell.effective_capacity}<br>"
                f"Pressure: {cell.pressure:.1f}<br>"
                f"Techs: {techs}"
            )
    fig_world.add_trace(go.Scatter(
        x=cell_x, y=cell_y, mode="markers",
        marker=dict(size=20, opacity=0),
        hovertext=cell_text, hoverinfo="text",
        showlegend=False, name="cells",
    ))

    fig_world.update_layout(
        template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
        height=550, margin=dict(t=10, b=10, l=10, r=10),
        font=dict(family="JetBrains Mono", color="#5a8a5a"),
        xaxis=dict(range=[0, 1], showticklabels=False, showgrid=False),
        yaxis=dict(range=[0, 1], showticklabels=False, showgrid=False, scaleanchor="x"),
        legend=dict(orientation="h", y=1.05),
    )
    st.plotly_chart(fig_world, width='stretch')

    # World stats row
    ws = grid.summary()
    wc1, wc2, wc3, wc4 = st.columns(4)
    wc1.metric("Avg Resources", f"{ws['avg_resources']:.3f}")
    wc2.metric("Depleted Cells", ws["depleted_cells"])
    wc3.metric("Total Cells", ws["total_cells"])
    wc4.metric("Global Techs", ", ".join(ws["global_techs"]) if ws["global_techs"] else "None")

    # Resource heatmap
    with st.expander("Resource Heatmap"):
        res_grid = []
        res_text = []
        for r in range(size):
            row_vals = []
            row_text = []
            for c in range(size):
                cell = grid.cells[r][c]
                row_vals.append(cell.effective_resources)
                row_text.append(
                    f"res:{cell.effective_resources:.2f}<br>"
                    f"cap:{cell.effective_capacity}<br>"
                    f"pop:{cell.agent_count}<br>"
                    f"prs:{cell.pressure:.1f}"
                )
            res_grid.append(row_vals)
            res_text.append(row_text)

        fig_res = go.Figure(go.Heatmap(
            z=res_grid, text=res_text, texttemplate="%{text}",
            colorscale=[[0, "#1a0000"], [0.5, "#4a3a00"], [1.0, "#00ff88"]],
            zmin=0, zmax=1.5,
            colorbar=dict(title="Resources", tickfont=dict(color="#5a8a5a")),
        ))
        fig_res.update_layout(
            template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
            height=350, margin=dict(t=10, b=10, l=10, r=10),
            font=dict(family="JetBrains Mono", color="#5a8a5a", size=9),
            xaxis=dict(showticklabels=False), yaxis=dict(showticklabels=False, autorange="reversed"),
        )
        st.plotly_chart(fig_res, width='stretch')
