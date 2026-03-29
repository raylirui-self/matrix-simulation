"""Matrix-themed CSS for the Streamlit dashboard."""

MATRIX_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;700&family=Space+Grotesk:wght@400;600;700&display=swap');
    .stApp { background-color: #030d03; }
    section[data-testid="stSidebar"] { background-color: #040f04; border-right: 1px solid #0a2a0a; }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; color: #00ff88 !important; }
    p, li, span, div { color: #b0d0b0; }
    [data-testid="stMetricValue"] { color: #00ff88 !important; font-family: 'JetBrains Mono', monospace !important; }
    [data-testid="stMetricLabel"] { color: #5a8a5a !important; }
    .stButton > button {
        background-color: #0a1f0a !important; border: 1px solid #00ff88 !important;
        color: #00ff88 !important; font-family: 'JetBrains Mono', monospace !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover { background-color: #0f3f0f !important; box-shadow: 0 0 15px rgba(0,255,136,0.3) !important; }
    .stTabs [data-baseweb="tab"] { color: #5a8a5a; }
    .stTabs [aria-selected="true"] { color: #00ff88 !important; }
    details { border: 1px solid #0a2a0a !important; background-color: #040f04 !important; }
    div[data-testid="stHeader"] { background-color: #030d03; }
    .block-container { padding-top: 1rem; }

    /* Activity feed ticker */
    .ticker-item {
        padding: 4px 8px; margin: 2px 0; border-radius: 4px;
        font-family: 'JetBrains Mono', monospace; font-size: 0.78em;
        border-left: 3px solid;
    }
    .ticker-birth { background: rgba(0,255,136,0.08); border-color: #00ff88; color: #00ff88; }
    .ticker-death { background: rgba(255,68,102,0.08); border-color: #ff4466; color: #ff4466; }
    .ticker-bond { background: rgba(0,204,255,0.08); border-color: #00ccff; color: #00ccff; }
    .ticker-tech { background: rgba(255,170,0,0.08); border-color: #ffaa00; color: #ffaa00; }
    .ticker-event { background: rgba(170,102,255,0.08); border-color: #aa66ff; color: #aa66ff; }
    .ticker-drama { background: rgba(255,136,68,0.08); border-color: #ff8844; color: #ff8844; }
    .ticker-god { background: rgba(255,215,0,0.1); border-color: #ffd700; color: #ffd700; }

    /* Era banner */
    .era-banner {
        text-align: center; padding: 28px 30px; margin: 8px 0 16px 0;
        border: 1px solid #00ff88; border-radius: 12px;
        background: linear-gradient(135deg, rgba(0,255,136,0.05), rgba(0,204,255,0.05));
        font-family: 'Space Grotesk', sans-serif;
        overflow: visible; white-space: normal;
        position: relative;
    }
    .era-banner-with-bg {
        text-align: center; padding: 50px 30px; margin: 8px 0 16px 0;
        border: 1px solid #00ff88; border-radius: 12px;
        font-family: 'Space Grotesk', sans-serif;
        overflow: visible; white-space: normal;
        position: relative;
        background-size: cover; background-position: center;
    }
    .era-banner-with-bg::before {
        content: ''; position: absolute; inset: 0; border-radius: 12px;
        background: rgba(3, 13, 3, 0.55);
    }
    .era-banner-with-bg > * { position: relative; z-index: 1; }
    .era-name {
        font-size: 2.2em; font-weight: 700; color: #00ff88;
        white-space: nowrap; letter-spacing: 0.03em;
        text-shadow: 0 0 20px rgba(0,255,136,0.4), 0 2px 4px rgba(0,0,0,0.8);
    }
    .era-desc {
        font-size: 1em; color: #b0d0b0; margin-top: 6px;
        text-shadow: 0 1px 3px rgba(0,0,0,0.8);
    }

    /* Achievement badge */
    .achievement {
        display: inline-block; padding: 4px 10px; margin: 3px;
        border-radius: 12px; font-size: 0.75em;
        font-family: 'JetBrains Mono', monospace;
        border: 1px solid;
    }
    .achievement-gold { background: rgba(255,215,0,0.1); border-color: #ffd700; color: #ffd700; }
    .achievement-silver { background: rgba(192,192,192,0.1); border-color: #c0c0c0; color: #c0c0c0; }
    .achievement-bronze { background: rgba(205,127,50,0.1); border-color: #cd7f32; color: #cd7f32; }
    .achievement-green { background: rgba(0,255,136,0.1); border-color: #00ff88; color: #00ff88; }

    /* God mode button styling */
    .god-btn > button {
        background: linear-gradient(135deg, #1a0a2a, #0a1a2a) !important;
        border-color: #ffd700 !important; color: #ffd700 !important;
    }
    .god-btn > button:hover { box-shadow: 0 0 20px rgba(255,215,0,0.4) !important; }

    /* Record card */
    .record-card {
        background: rgba(0,255,136,0.03); border: 1px solid #0a2a0a;
        border-radius: 8px; padding: 12px; margin: 4px 0;
        font-family: 'JetBrains Mono', monospace;
    }
    .record-title { color: #ffaa00; font-size: 0.85em; font-weight: bold; }
    .record-value { color: #00ff88; font-size: 1.4em; }
    .record-holder { color: #5a8a5a; font-size: 0.75em; }
</style>
"""
