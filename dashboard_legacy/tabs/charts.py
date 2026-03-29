import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.agents import PHASES


def render_charts_tab():
    st.caption("Population trends, demographics, births vs deaths, bond activity, and generational progress over time.")
    history = st.session_state.tick_history
    if history:
        df = pd.DataFrame(history)

        # Population & Intelligence
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(
            go.Scatter(x=df["tick"], y=df["alive_count"], name="Population",
                       line=dict(color="#00ff88", width=2), fill="tozeroy",
                       fillcolor="rgba(0,255,136,0.05)"),
            secondary_y=False,
        )
        fig1.add_trace(
            go.Scatter(x=df["tick"], y=df["avg_intelligence"], name="Avg Intelligence",
                       line=dict(color="#00ccff", width=2, dash="dot")),
            secondary_y=True,
        )
        fig1.add_trace(
            go.Scatter(x=df["tick"], y=df["avg_health"], name="Avg Health",
                       line=dict(color="#ffaa00", width=1, dash="dash")),
            secondary_y=True,
        )
        fig1.update_layout(
            template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
            height=320, margin=dict(t=30, b=30),
            legend=dict(orientation="h", y=1.12),
            font=dict(family="JetBrains Mono", color="#5a8a5a"),
        )
        fig1.update_xaxes(gridcolor="#0a2a0a")
        fig1.update_yaxes(gridcolor="#0a2a0a", secondary_y=False, title="Pop")
        fig1.update_yaxes(gridcolor="#0a2a0a", secondary_y=True, title="IQ / Health")
        st.plotly_chart(fig1, width='stretch')

        # Phase stacked area + births/deaths side by side
        col_phase, col_bd = st.columns(2)

        with col_phase:
            phase_cols = [p for p in PHASES if p in df.columns]
            if phase_cols:
                fig2 = go.Figure()
                colors = {"infant": "#00ff88", "child": "#00ccff", "adolescent": "#ffaa00",
                          "adult": "#ff4466", "elder": "#aa66ff"}
                for phase in phase_cols:
                    fig2.add_trace(go.Scatter(
                        x=df["tick"], y=df[phase], name=phase,
                        stackgroup="one", line=dict(width=0.5),
                        fillcolor=colors.get(phase, "#888"),
                    ))
                fig2.update_layout(
                    template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                    height=250, margin=dict(t=30, b=30), title="Population by Phase",
                    legend=dict(orientation="h", y=1.12),
                    font=dict(family="JetBrains Mono", color="#5a8a5a"),
                )
                st.plotly_chart(fig2, width='stretch')

        with col_bd:
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(x=df["tick"], y=df["births"], name="Births",
                                   marker_color="#00ff88", opacity=0.7))
            fig3.add_trace(go.Bar(x=df["tick"], y=df["deaths"], name="Deaths",
                                   marker_color="#ff4466", opacity=0.7))
            fig3.update_layout(
                template="plotly_dark", barmode="overlay",
                paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                height=250, margin=dict(t=30, b=30), title="Births vs Deaths",
                legend=dict(orientation="h", y=1.12),
                font=dict(family="JetBrains Mono", color="#5a8a5a"),
            )
            st.plotly_chart(fig3, width='stretch')

        # Bond activity + generation trend
        col_bonds, col_gen = st.columns(2)
        with col_bonds:
            if "bonds_formed" in df.columns:
                fig_bonds = go.Figure()
                fig_bonds.add_trace(go.Scatter(
                    x=df["tick"], y=df["bonds_formed"], name="Formed",
                    line=dict(color="#00ccff", width=2),
                ))
                fig_bonds.add_trace(go.Scatter(
                    x=df["tick"], y=df["bonds_decayed"], name="Decayed",
                    line=dict(color="#ff8844", width=2, dash="dot"),
                ))
                fig_bonds.update_layout(
                    template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                    height=220, margin=dict(t=30, b=30), title="Bond Activity",
                    legend=dict(orientation="h", y=1.12),
                    font=dict(family="JetBrains Mono", color="#5a8a5a"),
                )
                st.plotly_chart(fig_bonds, width='stretch')

        with col_gen:
            if "avg_generation" in df.columns:
                fig_gen = go.Figure()
                fig_gen.add_trace(go.Scatter(
                    x=df["tick"], y=df["avg_generation"], name="Avg Generation",
                    line=dict(color="#aa66ff", width=2), fill="tozeroy",
                    fillcolor="rgba(170,102,255,0.05)",
                ))
                fig_gen.update_layout(
                    template="plotly_dark", paper_bgcolor="#030d03", plot_bgcolor="#040f04",
                    height=220, margin=dict(t=30, b=30), title="Generational Progress",
                    legend=dict(orientation="h", y=1.12),
                    font=dict(family="JetBrains Mono", color="#5a8a5a"),
                )
                st.plotly_chart(fig_gen, width='stretch')
    else:
        st.info("Run a batch to see charts.")
