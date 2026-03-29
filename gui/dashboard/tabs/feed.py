import streamlit as st
import pandas as pd

# Color map matching the original ticker CSS
TYPE_COLORS = {
    "birth": "#00ff88",
    "death": "#ff4466",
    "bond": "#00ccff",
    "tech": "#ffaa00",
    "event": "#aa66ff",
    "drama": "#ff8844",
    "god": "#ffd700",
}

TYPE_ICONS = {
    "birth": "🟢",
    "death": "💀",
    "bond": "🤝",
    "tech": "⚡",
    "event": "🔮",
    "drama": "🎭",
    "god": "👁",
}


def _styled_feed_table(data: list[tuple], key_prefix: str):
    """Render a filterable, color-coded feed table."""
    if not data:
        st.info("No entries yet. Run some ticks!")
        return

    df = pd.DataFrame(data, columns=["Type", "Message", "Tick"])
    all_types = sorted(df["Type"].unique())

    # Filters
    f1, f2 = st.columns(2)
    with f1:
        sel_types = st.multiselect(
            "Filter by type", all_types, default=all_types,
            format_func=lambda t: f"{TYPE_ICONS.get(t, '•')} {t}",
            key=f"{key_prefix}_type_filter",
        )
    with f2:
        tick_min, tick_max = int(df["Tick"].min()), int(df["Tick"].max())
        if tick_min < tick_max:
            tick_range = st.slider(
                "Tick range", tick_min, tick_max, (tick_min, tick_max),
                key=f"{key_prefix}_tick_filter",
            )
        else:
            tick_range = (tick_min, tick_max)

    # Apply filters
    mask = df["Type"].isin(sel_types) & df["Tick"].between(*tick_range)
    filtered = df[mask].sort_values("Tick", ascending=False).reset_index(drop=True)

    st.caption(f"{len(filtered)} / {len(df)} entries")

    # Render as color-coded HTML (preserves the visual feel)
    if filtered.empty:
        st.info("No matching entries.")
        return

    # Build scrollable color-coded list
    html_parts = ['<div style="max-height:500px;overflow-y:auto;padding-right:4px;">']
    for _, row in filtered.iterrows():
        color = TYPE_COLORS.get(row["Type"], "#5a8a5a")
        bg = color.replace("#", "")
        # Convert hex to rgba for background
        r, g, b = int(bg[:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
        icon = TYPE_ICONS.get(row["Type"], "•")
        html_parts.append(
            f'<div style="padding:5px 10px;margin:2px 0;border-radius:4px;'
            f'border-left:3px solid {color};background:rgba({r},{g},{b},0.08);'
            f'font-family:JetBrains Mono,monospace;font-size:0.78em;color:{color};'
            f'display:flex;align-items:center;gap:8px;">'
            f'<span style="opacity:0.7;min-width:45px;text-align:right;color:#5a8a5a;">t={int(row["Tick"])}</span>'
            f'<span style="min-width:20px;">{icon}</span>'
            f'<span style="flex:1;">{row["Message"]}</span>'
            f'</div>'
        )
    html_parts.append('</div>')
    st.markdown("\n".join(html_parts), unsafe_allow_html=True)


def render_feed_tab():
    st.caption("Scrolling log of everything happening in the simulation — births, deaths, romances, wars, glitches, and divine interventions.")
    feed_col, drama_col = st.columns([1, 1])

    with feed_col:
        st.markdown("#### Activity Feed")
        st.caption("Real-time events from the simulation")
        _styled_feed_table(st.session_state.activity_feed, "feed")

    with drama_col:
        st.markdown("#### Drama & Stories")
        st.caption("Love, loss, rivalry, and triumph")
        _styled_feed_table(st.session_state.drama_feed, "drama")
