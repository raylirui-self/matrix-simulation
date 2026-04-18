# Streamlit Dashboard (Legacy)

[← Back to README](../README.md)

The Streamlit dashboard is the legacy frontend, retained for analytics-heavy workflows while The Nexus is the recommended primary interface. It provides 15 tabs for monitoring and interacting with the simulation.

Launch with:

```bash
streamlit run dashboard.py
# To stop: press Ctrl+C
```

**Controls:**
- Quick step buttons (+1, +10, +50, +100 ticks) with descriptive tooltips
- **Live Mode** — Auto-run with configurable speed (1-50 ticks/cycle), intervene while running
- Custom batch runner for long simulations
- **God Mode**: Plague, Famine, Meteor, Blessing, Bounty, Spawn — with immediate DB persistence
- **Agent Actions**: Select any agent and Heal, Smite, Red Pill, Gift Wealth, Make Prophet, Make Protagonist, or Whisper (inject memories)
- **Cell Actions**: Enrich, Deplete, or Terraform any grid cell in real time
- **Event Injector**: Create custom world events with configurable targets and health impact
- Scenario selection, 12 parameter sliders (all with detailed help text), fork & compare
- Compact status bar showing tick/population/factions/wars/control at a glance

**Visualization Tabs (15 tabs with emoji icons):**
- **Live Feed** — Real-time activity ticker + drama feed (births, deaths, romances, wars, glitches)
- **Charts** — Population, intelligence, health, phase distribution, births/deaths, bonds, generations
- **World** — Agents overlaid on terrain grid with bond lines and cell hover info
- **Agents** — Scatter plot, inspector with skill radar, trait bars, bonds, family tree (3 generations), dynasty size
- **Social** — Bond distribution pie chart, strength histogram, network graph colored by generation
- **Emotions** — Population emotion radar, dominant emotion pie, trauma tracking with most-traumatized list
- **Factions** — Faction cards with core beliefs, leadership, wars, belief-space scatter plot
- **Economy** — Wealth distribution, Gini index, leaderboard, wealth-by-faction breakdown
- **Matrix** — Control index, awareness distribution, system trust, awareness heatmap, Anomaly banner, Sentinel tracking
- **Culture** — Cultural memory floors, knowledge pool, population vs floor radar
- **Events** — LLM-generated world events with health/skill effects
- **Narratives** — LLM-generated civilization narratives
- **Protagonists** — Visual character cards with HP bars, emotion bars, trait bars, status tags, skill radars, inner monologue, portrait prompts
- **Records** — Hall of records, all-time records, skill leaderboards, tiered achievement system, civilization summary
- **Compare** — Overlay population/intelligence trajectories from multiple runs with config diff

**Header Metrics:**
Two rows of at-a-glance metrics with trend deltas: Population (with +/- change), Born, Deaths, Max Gen, Avg Health, Avg IQ, Techs, plus Mood, Factions, Avg Wealth, Matrix Control, Redpilled, Active Wars.

**Civilization Era System:**
The dashboard tracks the current era based on progress: Genesis, Dawn of Tribes, Tribal Expansion, Age of Awakening, Agricultural Age, Bronze Age, Trade Era, Industrial Age.
