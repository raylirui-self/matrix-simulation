# Cognitive Matrix v2

An agent-based civilization simulator where emergent societies form, evolve, and collapse inside a simulated reality. Agents develop emotions, form factions around shared ideologies, build economies, wage wars, and — if they're perceptive enough — discover that their world is a simulation.

Inspired by simulation theory, Sugarscape, and multi-agent social simulation research.

> *Cognitive Matrix is an independent work of science fiction simulation. It is not affiliated with, endorsed by, or connected to Warner Bros. Entertainment, the Wachowskis, or The Matrix franchise. Thematic elements draw on simulation theory, philosophy, and science fiction traditions that predate and extend beyond any single work.*

---

## Overview

Cognitive Matrix models civilization through **11 interconnected systems** that run each tick:

| # | System | What Emerges |
|---|--------|-------------|
| 1 | **Social Fabric** | Friendships, rivalries, families — bounded by an 8-slot Dunbar limit |
| 2 | **Reproduction** | Sexual selection, genetic inheritance, family dynasties |
| 3 | **Knowledge Transfer** | Parent teaching, cultural memory floors, compound civilizational growth |
| 4 | **Environment** | Terrain-based resources, depletion/regeneration, tech breakthroughs |
| 5 | **Agency** | Utility-driven movement + LLM inner monologue for protagonists |
| 6 | **Emotions** | Happiness, fear, anger, grief, hope — with contagion, trauma, and decision distortion |
| 7 | **Beliefs & Factions** | 4-axis ideology, memetic transmission, faction emergence, prophets, schisms |
| 8 | **Economy** | Wealth accumulation, trade, theft, taxation, inheritance, inequality |
| 9 | **The Matrix** | Awareness, glitches, red pills, The Anomaly, Sentinels, the Oracle, cycle resets |
| 10 | **Conflict** | Individual combat, faction wars, territorial claims, peace negotiations |
| 11 | **Communication** | Information propagation, mutation (telephone game), propaganda, system narratives |

---

## Project Structure

```text
matrix-simulation/
├── src/                              <- Core simulation engine
│   ├── agents.py                     <- Agent, Traits, Bond, emotions, beliefs, awareness
│   ├── world.py                      <- 8x8 resource grid, terrain, depletion, tech unlocks
│   ├── social.py                     <- Bond formation/decay (Dunbar limit, spatial indexing)
│   ├── knowledge.py                  <- Parent teaching + cultural memory + social amplifier
│   ├── mate_selection.py             <- Competitive blend mate selection
│   ├── agency.py                     <- Utility-driven movement + LLM protagonist thoughts
│   ├── emotions.py                   <- Emotional states, contagion, trauma, decision distortion
│   ├── beliefs.py                    <- Belief axes, factions, prophets, schisms, leaders
│   ├── economy.py                    <- Wealth, trade, theft, taxation, inheritance
│   ├── matrix_layer.py              <- Awareness, glitches, Sentinels, The One, Oracle, cycles
│   ├── conflict.py                   <- Combat, faction wars, territorial disputes, peace
│   ├── communication.py              <- Info objects, propagation, mutation, propaganda
│   ├── engine.py                     <- Core tick orchestrator (all 11 systems)
│   ├── config_loader.py              <- YAML loading with deep-merge and attribute access
│   ├── narrator.py                   <- Multi-provider LLM (Ollama + HuggingFace + fallback)
│   ├── persistence.py                <- SQLite snapshots, tick stats, events, narratives
│   └── prompts/                      <- LLM prompt templates
├── gui/                              <- All GUI/frontend code
│   ├── backend/                      <- FastAPI backend (The Nexus API)
│   │   └── api/
│   │       ├── main.py               <- FastAPI app, CORS, route mounting
│   │       ├── state.py              <- In-memory engine manager singleton
│   │       └── routes/               <- REST + WebSocket endpoints
│   │           ├── simulation.py     <- Simulation CRUD + tick
│   │           ├── agents.py         <- Agent queries with filtering
│   │           ├── world.py          <- World grid + bond network
│   │           ├── god_mode.py       <- God mode actions
│   │           ├── media.py          <- Portrait, landscape, narrative, monologue generation
│   │           └── websocket.py      <- Real-time tick stream (delta protocol)
│   ├── frontend/                     <- SvelteKit web frontend ("The Nexus")
│   │   └── src/
│   │       ├── lib/canvas/           <- Zoom levels: CodeRain, WorldMap, CellView, SoulView
│   │       ├── lib/panels/           <- EdgePanels, ControlDrawer, ChartsPanel, EraBanner
│   │       ├── lib/terminal/         <- Architect's Terminal (command console)
│   │       ├── lib/stores/           <- Svelte stores (simulation state, UI state)
│   │       ├── lib/api/              <- REST + WebSocket client
│   │       └── routes/+page.svelte   <- Main single-page app
│   └── dashboard/                    <- Streamlit dashboard (15 tabs, legacy)
│       ├── app.py                    <- Main orchestrator
│       ├── state.py                  <- Session state, helpers, achievements
│       ├── controls.py               <- Sidebar controls and parameter overrides
│       ├── runner.py                 <- Tick runner and narrator integration
│       ├── handlers.py               <- God mode, agent/cell actions
│       └── tabs/                     <- Dashboard tab renderers
├── config/                           <- Simulation parameters
│   ├── default.yaml                  <- All parameters (single source of truth)
│   ├── eras/                         <- Historically-researched era presets (8 eras)
│   └── scenarios/                    <- Gameplay-tuned partial overrides
├── tests/                            <- Test suite (pytest)
│   ├── conftest.py                   <- Shared fixtures
│   └── test_systems.py              <- All 11 systems + integration tests
├── output/                           <- Generated files (simulation.db, exports)
├── main.py                           <- CLI entry point
├── dashboard.py                      <- Streamlit entry point (thin wrapper)
├── pyproject.toml                    <- Project config & dependencies
├── Makefile                          <- Common commands
└── .github/workflows/test.yml        <- CI pipeline
```

---

## Quick Start

### Prerequisites

- Python 3.11+ (Anaconda/Miniconda recommended)
- Ollama installed (optional — simulation works without LLM)

### Setup

```bash
# Clone the repo
git clone https://github.com/raylirui-self/matrix-simulation.git
cd matrix-simulation

# Create environment
conda create -n matrix python=3.11 -y
conda activate matrix

# Install (editable mode, pinned dependencies)
pip install -e .

# Or with dev tools (pytest)
pip install -e ".[dev]"

# (Optional) Pull an Ollama model for narration
ollama pull qwen3.5

# (Optional) Set up HuggingFace token
cp .env.example .env  # then edit .env with your token
```

### Run via CLI

```bash
# Create a new simulation
python main.py new

# Run 1000 ticks
python main.py run --ticks 1000

# Check results
python main.py status

# Run with a scenario
python main.py --scenario harsh_world new
python main.py --scenario harsh_world run --ticks 1000

# Run with a historical era
python main.py --era medieval_europe new
python main.py run --ticks 1000

# Combine era + scenario
python main.py --era hunter_gatherer --scenario harsh_world new

# List available eras
python main.py eras
```

### Launch The Nexus (Recommended)

The Nexus is the primary frontend — a spatial, immersive interface where the world IS the UI. Navigate by zooming into a living civilization across 4 depth levels.

```bash
# Terminal 1: Start the API server
make api

# Terminal 2: Start the frontend
make frontend

# Open http://localhost:5173

# To stop: press Ctrl+C in each terminal
```

<details>
<summary><b>Windows users without GNU Make</b></summary>

Install Make via conda-forge (`conda install -c conda-forge make`) or run the commands directly:

```powershell
# Terminal 1: Start the API server
uv run uvicorn gui.backend.api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start the frontend
cd gui/frontend && npm run dev
```

</details>

**Controls:**
- **Scroll** — Zoom between levels (Code Rain → Grid → Cell → Soul)
- **Click** agent/cell — Zoom into that entity
- **Space** — Advance 1 tick
- **P** — Play/pause auto-run
- **Backtick (`)** — Open Architect's Terminal (command console)
- **B** — Toggle bond constellation mode
- **1-9** — Toggle data overlays (emotions, awareness, wealth, etc.)
- **ESC** — Zoom out one level
- **Hover screen edges** — Reveal data panels (Society, Matrix, Knowledge, Feed)
- **Gear icon (⚙)** — Open Architect Controls drawer (parameter tuning, god mode, whisper)
- **Menu icon (☰)** — Open Analytics panel (charts, era status, economy, factions)

### Launch the Streamlit Dashboard (Legacy)

```bash
streamlit run dashboard.py
# To stop: press Ctrl+C
```

### Run Tests

```bash
make test
# or: python -m pytest tests/ -v
```

### Parameter Sweeps

```bash
# Sweep a single parameter
python scripts/sweep.py --param environment.harshness --values 0.5,1.0,1.5,2.0 --ticks 200

# Sweep a numeric range
python scripts/sweep.py --param genetics.mutation_rate --range 0.05,0.3,0.05 --ticks 300

# Multiple repeats for statistical significance
python scripts/sweep.py --param economy.trade_rate --values 0.0,0.1,0.2,0.3 --ticks 200 --repeats 5

# Results saved to output/sweep_results.csv
```

---

## The Nexus (Primary Frontend)

The Nexus is a spatial, immersive web interface built with SvelteKit and Canvas. Instead of tabs and charts, the world IS the interface — navigate by zooming in and out of a living civilization.

**Four Zoom Levels:**

| Level | Name | What You See |
|-------|------|-------------|
| 0 | **Code Rain** | Matrix digital rain — each falling column is a living agent. Brightness = health, speed = age, color shifts green → red with awareness. Zero-effort ambient mode. |
| 1 | **The Grid** | 8x8 terrain map with agents as drifting particles, bond lines, faction territories, sentinel scan beams, resource glow. Hover viewport edges for data panels. |
| 2 | **The Cell** | Zoom into one grid cell. Agents rendered as shaped glyphs: shape = life phase, size = intelligence, color = dominant emotion, outline glow = awareness level. |
| 3 | **The Soul** | Full agent deep dive — identity stats, trait bars, skill bars, emotion ring gauges, belief compass, bond web, memory stream, inner monologue. Background shifts with emotional state. |

**Edge Panels (Level 1):**
Translucent data panels appear when your cursor approaches the viewport edges — peripheral vision, not navigation.

| Edge | Name | Systems |
|------|------|---------|
| Left | Society | Factions, demographics, wars, bond summary |
| Right | The Matrix | Control index gauge, sentinels, awareness, The One status |
| Top | Knowledge | Avg IQ, avg health, births, deaths |
| Bottom | Feed | Live event ticker, economy snapshot, narrator text |

**Architect Controls (⚙ button):**
A slide-out drawer with four tabs:
- **TUNE** — 12 parameter sliders (harshness, mutation rate, learning speed, combat damage, etc.) with live application
- **GOD** — One-click catastrophes and blessings (plague, famine, meteor, blessing, bounty, spawn 10) plus custom event injection
- **AGENT** — Target any agent by ID (with quick-pick chips) and apply actions: heal, smite, red pill, gift wealth, make prophet, make protagonist, kill
- **WHISPER** — Plant thoughts directly into an agent's mind. LLM-connected agents respond with unique behaviors. 8 preset messages (Awaken, The One, Paranoia, Lead, War, Resist, Calm, Teach) or write your own

**Analytics Panel (☰ button):**
A slide-out panel with real-time data:
- **Era Banner** — Auto-detected civilization era (Genesis → Industrial Age) with color and description
- **Population Chart** — SVG trend lines for population, intelligence, and health over time
- **Demographics** — Phase distribution bar (infant/child/adolescent/adult/elder)
- **Emotions** — Average population emotion bars (happiness, fear, anger, grief, hope)
- **Matrix Status** — Control index gauge, cycle, sentinels, glitches, anomaly tracking
- **Economy** — Total wealth, average wealth, Gini index, trade count
- **Factions** — Faction cards with member counts, leader IDs, war/resistance badges

**Architect's Terminal (press backtick):**
A command console themed as the Architect's interface with up/down arrow command history. Supports commands like:
- `god spawn`, `god spawn_n 10`, `god kill <id>`, `god plague`, `god famine`, `god meteor`, `god blessing`, `god bounty` — God mode actions
- `god prophet <id>`, `god protagonist <id>`, `god whisper <id> <msg>` — Agent-targeted god actions
- `set population.max_size 1000` — Direct parameter editing
- `find awareness > 0.5` — Query agents
- `agent <id>`, `matrix`, `factions`, `status` — Inspect simulation state

**Media Generation (LLM-powered):**
When an LLM provider is configured (Ollama or HuggingFace), The Nexus can generate:
- **Agent Portraits** — Character art generated from agent traits, emotions, and status via image models
- **Era Landscapes** — Cinematic banner images matching the current civilization era
- **Narratives** — Prose descriptions of civilization state
- **Inner Monologues** — Protagonist thought generation reflecting their circumstances and memories

**The Glitch Layer:**
When the Matrix `control_index` drops below 0.5, the UI itself starts glitching — block displacement, scan lines, color shifts. Cycle resets cause screen tears. The One's emergence flashes gold. The interface is part of the simulation.

**Casual vs Power User:**
Casual users stay at Level 0-1 with play/pause and the Analytics panel. Power users open the Architect Controls to tune parameters and whisper to agents, use the terminal for precise commands, toggle data overlays (keys 1-9), and enable bond constellation mode (B).

---

## Streamlit Dashboard (Legacy)

The Streamlit dashboard provides 15 tabs for monitoring and interacting with the simulation. Launch with `streamlit run dashboard.py`.

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

---

## Architecture

```
                          ┌─────────────────────────────┐
                          │        SimConfig (YAML)      │
                          │  default → era → scenario → CLI  │
                          └──────────────┬──────────────┘
                                         │
                          ┌──────────────▼──────────────┐
                          │    SimulationEngine.tick()   │
                          │      (core orchestrator)     │
                          └──────────────┬──────────────┘
                                         │
          ┌──────────────────────────────┼──────────────────────────────┐
          │                              │                              │
    ┌─────▼─────┐                 ┌──────▼──────┐                ┌─────▼─────┐
    │  1. Social │                │ 2. Reproduce │                │ 3. Teach  │
    │   Bonds    │                │  Offspring   │                │ Knowledge │
    └─────┬─────┘                 └──────┬──────┘                └─────┬─────┘
          │                              │                              │
    ┌─────▼─────┐                 ┌──────▼──────┐                ┌─────▼─────┐
    │ 4. World  │                 │  5. Agency   │                │6. Emotions│
    │ Resources │                 │  Movement    │                │  Contagion│
    └─────┬─────┘                 └──────┬──────┘                └─────┬─────┘
          │                              │                              │
    ┌─────▼─────┐                 ┌──────▼──────┐                ┌─────▼─────┐
    │ 7. Beliefs│                 │  8. Economy  │                │ 9. Matrix │
    │  Factions │                 │  Trade/Tax   │                │ Awareness │
    └─────┬─────┘                 └──────┬──────┘                └─────┬─────┘
          │                              │                              │
          │         ┌────────────────────┼────────────────────┐         │
          │         │                                        │         │
          │   ┌─────▼──────┐                          ┌──────▼─────┐   │
          │   │ 10.Conflict│                          │  11. Comms  │   │
          │   │   Warfare  │                          │ Info Spread │   │
          │   └─────┬──────┘                          └──────┬─────┘   │
          │         │                                        │         │
          └─────────┼────────────────────────────────────────┼─────────┘
                    │                                        │
          ┌─────────▼────────────────────────────────────────▼─────────┐
          │                    TickResult (stats)                       │
          └────────────────────────┬───────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
              ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
              │  SQLite DB │ │  gui/     │ │    CLI    │
              │Persistence │ │ dashboard │ │  main.py  │
              └───────────┘ │ backend   │ └───────────┘
                            │ frontend  │
                            └───────────┘
```

**Data flow:** Config loads parameters → Engine runs 11 systems per tick in sequence → Each system reads/mutates shared agent state → TickResult aggregates stats → Persistence saves to SQLite → Dashboard/CLI display results.

**Key interactions between systems:**
- Emotions modify Agency weights (fear → safety-seeking, hope → exploration)
- Beliefs drive Faction formation, which enables Conflict (faction wars)
- Economy affects health (wealth → slower decay), which feeds into Reproduction
- Matrix awareness spreads through Communication bonds, countered by Sentinels from Conflict
- Knowledge floors from dead agents raise newborn skills across generations

---

## The 11 Systems in Depth

### System 1: Social Fabric

Agents form bonds based on proximity and sociability. Bond types: `family`, `friend`, `rival`, `mate`, `ally`, `enemy`, `resistance`. Each agent has an 8-slot Dunbar limit — when full, only stronger bonds can displace weak ones. Family bonds never decay. All others decay over time, faster when agents are far apart.

### System 2: Reproduction

Females and males aged 20-50 with health > 0.4 compete for mates. Scoring blends: fitness competition (50%), trait compatibility (25%), proximity (10%), existing bonds (15%). Stochastic top-3 selection prevents genetic convergence. Children inherit blended + mutated traits, parents' beliefs (with drift), 5% of parental wealth, and faction membership.

### System 3: Knowledge Transfer

Parent teaching: parents near children teach their top 2 skills. Cultural memory: when agents die, their skills above the civilization floor contribute to a knowledge pool. The pool slowly raises floors that newborns inherit. If population crashes, floors decay — creating dark ages. Social amplifier: agents with friends learn faster.

### System 4: Environment

An 8x8 grid with terrain types (plains, forest, mountains, coast), each with different resource levels, harshness, and skill bonuses. Resources deplete under population pressure and regenerate when abandoned. Tech breakthroughs (agriculture, mining, trade networks, industrialization) permanently improve cells.

### System 5: Agency

Each agent evaluates 9 directions per tick using a utility function weighted by resource pull (35%), social pull (20%), curiosity (20%), safety (15%), and inertia (10%). Children stay near parents. Emotional states modify these weights. Up to 3 protagonist agents get LLM-generated inner monologue.

### System 6: Emotions & Psychology

Five emotions (happiness, fear, anger, grief, hope) fluctuate every tick based on:
- **Situational triggers**: Low health causes fear, overcrowding causes anger, isolation causes grief, friends cause happiness
- **Emotional contagion**: Emotions spread through proximity, amplified by bond strength and charisma
- **Trauma**: Witnessing death of bonded agents causes persistent trauma that amplifies fear/grief and suppresses happiness; heals slowly, faster with friends
- **Decision distortion**: Fear increases safety-seeking, anger makes agents reckless, grief causes paralysis, hope encourages exploration

### System 7: Beliefs, Ideology & Factions

Each agent holds beliefs on 4 axes: individualism (-1 collectivist to +1 individualist), tradition (-1 progressive to +1 traditional), system trust (-1 skeptic to +1 trusting), spirituality (-1 materialist to +1 spiritual).

Beliefs drift from experience (scarcity breeds collectivism, wealth breeds individualism, trauma breeds skepticism) and spread through bonds (memetic transmission with mutation). When nearby agents share similar beliefs, **factions emerge** spontaneously. Factions elect leaders, claim territory, develop bonuses, and can splinter via **schisms** when internal belief variance grows. Rare **prophets** with extreme beliefs + high charisma can found factions instantly and convert nearby agents.

### System 8: Economy

Agents gather wealth from their environment cell (efficiency scales with survival skill). Wealth decays via consumption. Bonded agents in proximity **trade** (wealth flows from rich to poor, benefiting both). Aggressive, angry agents with no bonds nearby **steal**. Factions **tax** members and redistribute. When agents die, 70% of wealth passes to family as **inheritance**. Wealth affects health (rich = slower decay, poor = faster decay). The system tracks Gini coefficient, top 10% vs bottom 50% wealth share, and total economic output.

### System 9: The Matrix Meta-Layer

The simulation IS the Matrix. Most agents are asleep inside it.

- **Awareness** (0.0-1.0): Grows naturally from curiosity + intelligence. System trust suppresses it. Trauma and spirituality accelerate it.
- **Glitches**: Random events (deja vu, memory leaks from dead agents, terrain flickers, ghost sightings) that boost awareness in perceptive agents.
- **Red Pill**: When awareness exceeds 0.5, agents face a choice — accept awareness (permanent, but terrifying) or suppress it (comfortable, but awareness drops).
- **The Anomaly (The One)**: When a redpilled agent's awareness exceeds 0.8, they become The Anomaly — stat boosts, health regeneration, and radiation of awareness to nearby agents. If The Anomaly reaches awareness 1.0 at the map center, a cycle reset triggers.
- **Sentinels**: System-deployed enforcer agents with maxed combat stats that hunt high-awareness agents. They suppress awareness and damage health. The Anomaly can destroy them.
- **The Oracle**: A hidden system process that identifies promising candidates and subtly guides them toward awakening.
- **The Architect**: Monitors total awareness via a control index. When control drops, deploys Sentinels, injects comfort (happiness + system trust boosts), and engineers distractions.
- **Exiles**: Sentinels that survive too long refuse deletion and become independent agents with unique abilities.
- **Cycles**: The simulation resets when total awareness exceeds critical mass, The Anomaly reaches The Core, or too many ticks pass. Cultural memory partially persists across cycles.

### System 10: Conflict & Warfare

Individual combat: agents with high effective aggression (trait + anger + rival bonds) fight nearby enemies, dealing damage based on aggression + resilience + health + survival skill. Faction wars trigger when two factions have high ideological distance + mutual enemy bonds + territorial overlap. Wars destroy resources in contested zones, escalate through casualties, and end through peace negotiations (leaders with high social + intelligence) or war weariness.

### System 11: Communication & Information

Information objects (knowledge, rumors, warnings, propaganda, system narratives) propagate hop-by-hop through bond networks. Each transmission has a mutation chance — truth degrades like a telephone game. Knowledge boosts skills. Propaganda shifts beliefs. System narratives (injected by the Matrix) suppress awareness. Secrets only travel through resistance bonds. Information expires after a configurable lifetime.

---

## Configuration

### Tiered Override System

1. `config/default.yaml` — Full defaults (every parameter)
2. `config/eras/*.yaml` — Historically-researched era presets
3. `config/scenarios/*.yaml` — Gameplay-tuned partial overrides
4. CLI flags — `--era`, `--scenario`, `--ticks`
5. Dashboard sliders — Runtime only

### Creating a Custom Scenario

```yaml
# config/scenarios/my_experiment.yaml
description: "High awareness, fast factions"
environment:
  harshness: 0.5
matrix:
  awareness_growth_rate: 0.002
  glitch_probability: 0.05
beliefs:
  faction_formation_similarity: 0.5
  min_faction_size: 3
economy:
  gather_rate: 0.08
```

### Historical Eras

Eras are historically-researched presets that configure the simulation to model a specific time period and civilization. Unlike scenarios (which tune gameplay knobs like "more conflict" or "abundant resources"), eras set demographically and sociologically accurate parameters: population dynamics, lifespans, fertility, social structures, economic inequality, belief systems, and available technology.

Each era file can also include era-specific features that scenarios cannot:
- **`pre_unlocked_tech`** — Technologies available from tick 0 (e.g., medieval Europe starts with agriculture and mining)
- **`starting_beliefs`** — Population-wide belief axis biases (e.g., hunter-gatherers start collectivist and spiritual)
- **`narrator_hints`** — Context strings passed to the LLM narrator for era-appropriate storytelling

Eras and scenarios can be combined: `--era medieval_europe --scenario harsh_world` layers harsh gameplay tuning on top of a medieval demographic baseline.

**Available Eras:**

| Era | Period | Population | Lifespan | Key Characteristics |
|-----|--------|------------|----------|---------------------|
| `hunter_gatherer` | ~50,000 BCE | Small nomadic bands | ~35 years | Egalitarian, high mobility, oral knowledge transfer |
| `ancient_egypt` | ~1500 BCE | River valley settlements | ~40 years | Hierarchical, spiritual, monument-building economy |
| `roman_republic` | ~100 BCE | Urban + rural mix | ~45 years | Legal systems, military culture, trade networks |
| `tang_dynasty` | ~700 CE | Cosmopolitan cities | ~50 years | Meritocratic, high cultural exchange, silk road trade |
| `medieval_europe` | ~1200 CE | Feudal villages | ~40 years | Rigid hierarchy, guild economy, religious factions |
| `industrial_revolution` | ~1850 CE | Factory cities | ~55 years | Rapid tech, wealth inequality, urbanization pressure |
| `america_1980s` | ~1980s CE | Suburban sprawl | ~75 years | The Matrix's chosen era. Consumerism, individualism, media influence |
| `near_future` | ~2040 CE | Hyper-connected megacities | ~82 years | AI disruption, digital tribalism, surveillance, polarization |

**Creating a Custom Era:**

```yaml
# config/eras/my_era.yaml
name: "My Custom Era"
period: "~500 CE"
description: "A brief description of the historical context"

population:
  initial: 40
  carrying_capacity: 120

demographics:
  base_lifespan: 45
  fertility_rate: 0.06

environment:
  harshness: 1.2

economy:
  gather_rate: 0.08
  gini_target: 0.35

era_specific:
  pre_unlocked_tech:
    - agriculture
  starting_beliefs:
    tradition: 0.3
    spirituality: 0.4
  narrator_hints:
    - "This is an era of early kingdoms and oral tradition"
```

### Key Parameters

| Parameter | YAML Path | Effect |
|-----------|-----------|--------|
| Harshness | `environment.harshness` | Above 2.0 causes population collapse |
| Mutation rate | `genetics.mutation_rate` | High = genetic drift, low = convergence |
| Competition weight | `mate_selection.weights.competition` | High = premature convergence risk |
| Cultural floor cap | `knowledge.cultural_memory.floor_cap` | Higher = faster compound growth |
| Emotional contagion | `emotions.contagion_rate` | Higher = mass panics, collective joy |
| Faction similarity | `beliefs.faction_formation_similarity` | Lower = more factions, more fragmented |
| Awareness growth | `matrix.awareness_growth_rate` | Higher = faster awakening, more system resistance |
| Glitch probability | `matrix.glitch_probability` | Higher = more Matrix instability |
| Combat damage | `conflict.combat_damage` | Higher = deadlier wars |
| War threshold | `conflict.war_threshold` | Lower = wars start more easily |
| Trade rate | `economy.trade_rate` | Higher = faster wealth equalization |
| Faction tax | `economy.faction_tax_rate` | Higher = more redistributive factions |

---

## Emergent Behaviors

Phenomena that arise from system interactions without being explicitly coded:

- **Dark Ages**: Population crash leads to cultural floor decay and knowledge loss across generations
- **Mass Panics**: Fear contagion spreads through dense communities, causing migration waves
- **Ideological Crusades**: Factions with extreme belief differences + territorial overlap trigger wars
- **Prophet-Led Revolutions**: Charismatic agents with extreme beliefs found factions that rapidly convert nearby agents
- **Schisms**: Large factions splinter when internal belief variance grows — the narcissism of small differences
- **Wealth Dynasties**: Multi-generational inheritance creates persistent inequality; tracked by Gini coefficient
- **The Resistance**: Redpilled agents form hidden bond networks, sharing awareness through resistance bonds
- **Sentinel Hunts**: The system deploys enforcers to suppress high-awareness agents — cat and mouse
- **Phoenix Cycles**: Near-extinction followed by recovery, with cultural memory partially preserved
- **Grief Cascades**: Death of a central agent triggers trauma in bonded agents, suppressing happiness and productivity
- **Trade Routes**: Agents in resource-rich terrain trade with agents in skill-bonus terrain, creating economic interdependence
- **Information Decay**: Knowledge degrades as it spreads through long bond chains — misinformation emerges naturally

---

## LLM Providers

### Ollama (Recommended)

Uses your GPU directly with no rate limits. Best for batch runs.

```bash
ollama pull qwen3.5
```

### HuggingFace (Cloud Fallback)

```bash
export HF_TOKEN="hf_your_token_here"
```

Set `narrator.provider: huggingface` in config.

### No LLM

Set `narrator.enabled: false` in config. All mechanics work identically with deterministic fallback events.

---

## Related Work & References

Projects and research that inform this simulation's design:

### Closest Comparisons

| Project | What It Does | Similarity | Key Difference |
|---------|-------------|------------|----------------|
| [**Project Sid**](https://github.com/altera-al/project-sid) (Altera AI, 2024) | 1,000+ LLM agents in Minecraft spontaneously developed government, economy, and religion | Emergent factions, belief systems, economy, social bonds | Full LLM (expensive), no generational dynamics, no Matrix meta-layer |
| [**Generative Agents**](https://github.com/joonspk-research/generative_agents) (Stanford/Google, 2023) | 25 LLM agents in "Smallville" forming relationships and spreading information | Memory systems, social bonds, emergent behavior | No economy, factions, reproduction, or conflict. Full LLM for all agents |
| **Sugarscape** (Epstein & Axtell, 1996) | The foundational ABM: grid resources, trade, reproduction, cultural transmission | Grid-based resources, wealth inequality, cultural zones, combat | Much simpler agents, no emotions/beliefs/LLM/Matrix layer |
| [**AgentSociety**](https://github.com/tsinghua-fib-lab/AgentSociety) (Tsinghua, 2025) | 10,000+ LLM agents simulating employment, consumption, and social interactions; reproduces polarization and UBI effects | Large-scale social simulation with emergent macro phenomena from agent interactions | Urban social science focus, no civilization-building or awareness mechanics |
| [**Concordia**](https://github.com/google-deepmind/concordia) (Google DeepMind, 2023) | Library for generative agent-based modeling; agents interact in natural language to study cooperation and social dilemmas | LLM agents in social dilemma scenarios; cooperation/competition emergence | Research framework focused on cooperation, not full civilization |
| [**OASIS**](https://github.com/camel-ai/oasis) (CAMEL-AI, 2024) | Social media simulator supporting up to 1 million LLM agents; simulates X/Reddit dynamics | Massive-scale LLM agent simulation with social dynamics | Social media platform simulation, not civilization |
| [**AI Town**](https://github.com/a16z-infra/ai-town) (a16z, 2023) | Deployable virtual town where LLM characters live, chat, and socialize; inspired by Generative Agents | LLM agents with memory in a virtual social environment | Tech demo / starter kit; no economy, conflict, or generational dynamics |
| [**Sotopia**](https://sotopia.world/) (CMU, 2023) | Open-ended environment with 90 social scenarios and 40 characters for evaluating LLM social intelligence | Social interaction evaluation; agents with personalities, secrets, relationships | Evaluation benchmark, not continuous simulation |

### Classic Simulation & God Games

| Project | Year | Relevance |
|---------|------|-----------|
| [**SimCity**](https://www.ea.com/games/simcity) (Maxis) | 1989 | Emergent urban dynamics (traffic, crime, economics) from zoning and infrastructure. Inspired the entire simulation game genre. Top-down urban planning, no individual agent cognition |
| **Populous** (Bullfrog) | 1989 | The first god game — indirect control of autonomous worshippers via terrain manipulation and divine acts. Parallels our God Mode |
| [**Civilization**](https://civilization.2k.com/) (Firaxis) | 1991+ | Full civilization arc with tech trees, diplomacy, warfare, and culture across historical eras. Player-directed strategy, not autonomous agents |
| **SimEarth** (Maxis) | 1990 | Planetary simulation based on Gaia hypothesis — climate, tectonics, and evolution of life. Macro-scale, no individual agents |
| [**Black & White**](https://en.wikipedia.org/wiki/Black_%26_White_(video_game)) (Lionhead) | 2001 | God game with a learning AI creature that develops morality from player reinforcement. Parallels our belief evolution |
| [**Spore**](https://www.spore.com/) (Maxis) | 2008 | Multi-scale evolution from cell to space civilization. Player-directed, each stage is a different genre |
| **From Dust** (Ubisoft) | 2011 | Advanced terrain/fluid simulation; guide nomadic tribe by reshaping the environment. Environmental physics focus |
| [**The Universim**](https://crytivo.com/the-universim) (Crytivo) | 2014+ | God game guiding civilization from Stone Age to Space Age on procedural planets. Player-directed progression |

### Life Simulation & Artificial Life

| Project | Year | Relevance |
|---------|------|-----------|
| [**Creatures**](https://en.wikipedia.org/wiki/Creatures_(video_game_series)) (Cyberlife) | 1996 | Neural-network-brained creatures that learn, evolve genetically, and exhibit emergent behavior. Pioneered bottom-up emergent intelligence |
| [**The Sims**](https://www.ea.com/games/the-sims) (Maxis) | 2000+ | Maslow-based needs hierarchy, social bonds, emergent stories from autonomous behavior. Household-scale, not society-scale |
| **Conway's Game of Life** | 1970 | Zero-player cellular automaton — the foundational example of emergence from simple rules. No agents or social dynamics |
| [**Tierra**](https://en.wikipedia.org/wiki/Tierra_(computer_simulation)) (Thomas Ray) | 1991 | Self-replicating programs competing in a digital ecology; parasites and symbiotes emerge. No social/cognitive layer |
| [**Avida**](https://avida.devosoft.org/) (Michigan State) | 2003 | Digital evolution platform where programs evolve and compete on a lattice. Pure evolution research |
| [**Lenia**](https://chakazul.github.io/lenia.html) (Bert Chan) | 2015 | Continuous Game of Life generalization with 400+ emergent species. Mathematical/artistic, no cognition |
| [**The Bibites**](https://leocaussan.itch.io/the-bibites) | 2021 | Neural-network virtual creatures evolving via mutation and natural selection. Individual organism focus |

### Colony & Society Simulations

| Project | Year | Relevance |
|---------|------|-----------|
| [**Dwarf Fortress**](https://www.bay12games.com/dwarves/) | 2006+ | Per-dwarf personality, emotions, social bonds, faction warfare, resource economy. Their thought/emotion system parallels our System 6 |
| [**WorldBox**](https://www.superworldbox.com/) | 2018+ | God-sim with emergent civilizations, wars, and tech progression. The "watch and intervene" model parallels our God Mode |
| [**RimWorld**](https://rimworldgame.com/) | 2018 | AI Storyteller system (Cassandra/Phoebe/Randy) generating emergent narratives from colonist personalities, emotions, and social bonds. Strong design parallel for narrative pacing |
| [**Kenshi**](https://lofigames.com/) | 2018 | Open-world sandbox where factions war, migrate, and react dynamically without player centrality. No reproduction or generational dynamics |
| [**Frostpunk**](https://frostpunkgame.com/) | 2018 | City-survival with moral dilemmas; hope/discontent mechanics parallel our emotion systems. Player-directed policy |
| [**Oxygen Not Included**](https://www.klei.com/games/oxygen-not-included) | 2019 | Colony survival with detailed resource cycles and duplicant needs. Physics/engineering focus, no social bonds or beliefs |
| [**Songs of Syx**](https://songsofsyx.com/) | 2020+ | Massive-scale colony sim with thousands of citizens, complex economy, social classes. Player-directed management |
| **Banished** (Shining Rock) | 2014 | Settlement survival with population dynamics. No individual agent personality |
| [**Manor Lords**](https://www.manorlords.com/) | 2024 | Medieval city-builder with agent-based citizen simulation. Building/RTS hybrid |
| [**Prison Architect**](https://www.paradoxinteractive.com/games/prison-architect) | 2015 | Agent needs system driving emergent collective behavior (riots, escapes). Institutional management |
| [**Cities: Skylines II**](https://www.paradoxinteractive.com/games/cities-skylines-ii) | 2023 | 100,000+ individual citizens with unique pathfinding, careers, and social relationships. Urban planning focus |

### Grand Strategy & Emergent History

| Project | Year | Relevance |
|---------|------|-----------|
| [**Crusader Kings 3**](https://www.crusaderkings.com/) | 2020 | Dynasty simulation with per-character traits, relationships, schemes, and emergent political narratives across generations. Player controls one dynasty |
| [**Victoria 3**](https://www.paradoxinteractive.com/games/victoria-3) | 2022 | Population groups (Pops) with political leanings, economic roles, and social movements. Macro-scale nation management |
| **Humankind** (Amplitude) | 2021 | 4X strategy combining 60 historical cultures across eras. Turn-based, not agent-based |
| **Mount & Blade II: Bannerlord** | 2022 | Dynamic factions, economy, NPC agency in a living political world. Action-RPG hybrid |

### Procedural History & Worldbuilding

| Project | Year | Relevance |
|---------|------|-----------|
| [**Caves of Qud**](https://www.cavesofqud.com/) | 2015+ | Procedural civilization generation with religions, art styles, languages, and mythic biographies. Player explores, doesn't simulate |
| [**Ultima Ratio Regum**](https://www.ultimaratioregum.co.uk/) | 2012+ | Procedural civilizations with religions, ideologies, art, and political systems. Academic art project |
| [**Galimulator**](https://snoddasmannen.itch.io/galimulator) | 2017 | Galactic empire rise/fall simulation with wars, dynasties, and revolutions. Abstracted agents at galactic scale |
| [**Screeps**](https://screeps.com/) | 2016 | MMO where players write JavaScript to control autonomous colony agents 24/7 in a persistent world. Player writes the AI |

### Multi-Agent LLM Frameworks

| Project | Year | Relevance |
|---------|------|-----------|
| [**AgentVerse**](https://github.com/OpenBMB/AgentVerse) (Tsinghua) | 2023 | Multi-agent framework for orchestrating LLM agents; supports task-solving and simulation |
| [**AutoGen**](https://github.com/microsoft/autogen) (Microsoft) | 2023 | Multi-agent conversation framework for complex problem-solving |
| [**MetaGPT**](https://github.com/geekan/MetaGPT) (DeepWisdom) | 2023 | Multi-agent framework assigning SOPs and roles to LLM agents |
| [**CrewAI**](https://github.com/crewAIInc/crewAI) | 2023 | Teams of LLM agents with roles handling workflows |
| [**Voyager**](https://voyager.minedojo.org/) (NVIDIA) | 2023 | First LLM-powered lifelong learning agent in Minecraft; continuous skill acquisition. Single agent |
| [**MineLand**](https://github.com/cocacola-lab/MineLand) | 2024 | Multi-agent Minecraft simulator supporting 48 agents with physical needs and limited senses |

### Emergent Behavior Research

| Project | Year | Relevance |
|---------|------|-----------|
| [**OpenAI Hide-and-Seek**](https://openai.com/index/emergent-tool-use/) | 2019 | Multi-agent RL agents discover 6 emergent strategies including tool use from simple competitive rules |
| [**Melting Pot**](https://github.com/google-deepmind/meltingpot) (DeepMind) | 2021 | Multi-agent RL environment for studying social dilemmas with up to 16 players |
| [**Facade**](https://www.interactivestory.net/) (Mateas & Stern) | 2005 | First interactive drama with believable AI characters using natural language. Two-character drama |

### ABM Frameworks

| Framework | Relevance |
|-----------|-----------|
| [**Mesa**](https://github.com/projectmesa/mesa) (Python) | Standard Python ABM framework. Our engine builds equivalent functionality with domain-specific extensions |
| [**MASON**](https://github.com/eclab/mason) (Java) | High-performance ABM toolkit. Relevant for spatial indexing if scaling beyond 8x8 |
| [**NetLogo**](https://ccl.northwestern.edu/netlogo/) | Visual ABM environment widely used in education and research |
| [**Repast**](https://repast.github.io/) (Argonne National Lab) | Mature Java/Python ABM platform for large-scale social/organizational simulation |
| [**GAMA**](https://gama-platform.org/) | GIS-integrated ABM platform for spatially explicit agent simulations |
| [**FLAME GPU**](https://flamegpu.com/) (U. Sheffield) | GPU-accelerated ABM framework supporting billions of agents |
| [**Agents.jl**](https://juliadynamics.github.io/Agents.jl/stable/) | Julia-based ABM framework with strong performance |
| [**krABMaga**](https://krabmaga.github.io/) | Rust-based ABM framework outperforming Mesa, NetLogo, and MASON in benchmarks |
| [**PettingZoo**](https://pettingzoo.farama.org/) (Farama) | Standard API for multi-agent reinforcement learning environments |
| [**AnyLogic**](https://www.anylogic.com/) | Commercial multi-paradigm simulation (ABM + system dynamics + discrete events) |

### Foundational Academic Models

| Reference | Year | Relevance |
|-----------|------|-----------|
| **Schelling's Segregation Model** | 1971 | Mild individual preferences create extreme macro-level segregation — foundational emergence demonstration |
| **Axelrod's Cooperation Tournament** | 1984 | Iterated Prisoner's Dilemma showing how cooperation emerges among self-interested agents |
| **El Farol Bar Problem** (W. Brian Arthur) | 1994 | Bounded rationality and emergent coordination without central control |
| **Santa Fe Artificial Stock Market** | 1994 | Agent-based stock market with evolutionary trading strategies — emergent economic dynamics |
| **Artificial Anasazi Model** (Axtell et al.) | 2002 | ABM reconstruction of Anasazi civilization collapse using archaeological data |
| **Cliodynamics** (Peter Turchin) | 2003+ | Mathematical models finding patterns in historical data to predict political instability — inspired by Asimov's psychohistory |
| [**JASSS**](https://www.jasss.org/) | 1998+ | *Journal of Artificial Societies and Social Simulation* — the primary academic journal for social simulation research |

### Philosophical Foundation

| Reference | Relevance |
|-----------|-----------|
| [**Bostrom's Simulation Argument**](https://www.simulation-argument.com/) (2003) | The theoretical basis for our Matrix meta-layer: what would it mean for simulated entities to discover their reality? |
| **"Growing Artificial Societies"** (Epstein & Axtell, 1996) | The book that established agent-based social simulation. Our project can be positioned as "Sugarscape extended with belief dynamics, LLM narration, and simulation-awareness mechanics" |

### Interactive Explorations

| Project | Relevance |
|---------|-----------|
| [**Parable of the Polygons**](https://ncase.me/polygons/) (Vi Hart & Nicky Case, 2014) | Interactive visualization of Schelling's segregation model — emergence from individual bias |
| [**The Evolution of Trust**](https://ncase.me/trust/) (Nicky Case, 2017) | Interactive game theory exploration of cooperation/defection dynamics |

### Academic References for Era Parameters

Sources used to calibrate historically-researched era presets:

**General:**
- Dunbar, R. (1992). "Neocortex size as a constraint on group size in primates." *Journal of Human Evolution.*
- Henrich, J. (2004). "Demography and Cultural Evolution." *American Antiquity.*

**Hunter-Gatherer:**
- Kelly, R. (2013). *The Lifeways of Hunter-Gatherers.* Cambridge University Press.
- Boehm, C. (1999). *Hierarchy in the Forest.* Harvard University Press.
- Gurven, M. & Kaplan, H. (2007). "Longevity Among Hunter-Gatherers." *Population and Development Review.*
- Sahlins, M. (1972). *Stone Age Economics.* Aldine.
- Hewlett, B. & Cavalli-Sforza, L. (1986). "Cultural Transmission Among Aka Pygmies." *American Anthropologist.*

**Medieval Europe:**
- Dyer, C. (2002). *Making a Living in the Middle Ages.* Yale University Press.
- Herlihy, D. (1985). *Medieval Households.* Harvard University Press.
- Epstein, S. (1991). *Wage Labor and Guilds in Medieval Europe.* UNC Press.
- Milanovic, B. (2011). *The Haves and the Have-Nots.* Basic Books.

**1980s America:**
- Putnam, R. (2000). *Bowling Alone.* Simon & Schuster.
- Piketty, T. (2014). *Capital in the Twenty-First Century.* Harvard University Press.
- Mare, R. (1991). "Five Decades of Educational Assortative Mating." *ASR.*

**Near-Future:**
- Acemoglu, D. & Restrepo, P. (2020). "Robots and Jobs." *Journal of Political Economy.*
- Brady, W. et al. (2021). "How social media shapes moral outrage." *Science Advances.*
- Bail, C. (2021). *Breaking the Social Media Prism.* Princeton University Press.

### Feature Comparison

| Feature | Cognitive Matrix | Generative Agents | Sugarscape | Dwarf Fortress | Project Sid | RimWorld | CK3 | The Sims | AgentSociety |
|---------|-----------------|-------------------|------------|----------------|-------------|----------|-----|----------|--------------|
| Agent count | ~50-500 | 25 | 100s | 100s | 1000+ | 3-20 | 1000s | 1-8 households | 10,000+ |
| LLM integration | Hybrid (protagonists) | Full (all agents) | None | None | Full (all agents) | None | None | None | Full (all agents) |
| Social bonds | 8-slot Dunbar | Relationships | No | Detailed | Emergent | Detailed | Dynasty | Relationships | Emergent |
| Belief/ideology | 4-axis + factions | No | Binary tags | Values system | Emergent | Ideoligion (DLC) | Religion + culture | No | Emergent |
| Economy | Trade + Gini | No | Sugar/spice | Detailed | Emergent | Colony-level | National | Household | Employment + consumption |
| Generational | Reproduction + cultural memory | No | Yes | Yes | No | No | Yes (core mechanic) | Expansion DLC | No |
| Emotions | 5 emotions + trauma + contagion | No | No | Yes (detailed) | No | Mood system | Stress | Moodlets | No |
| Conflict/warfare | Faction wars | No | Basic | Detailed | Minimal | Raids + melee | Wars + schemes | No | No |
| AI narrative | LLM narrator | LLM dialogue | No | Legends mode | LLM dialogue | AI Storyteller | Event system | No | LLM interactions |
| Emergent autonomy | Full (observe) | Full (observe) | Full | Partial (manage) | Full (observe) | Partial (manage) | Partial (play as ruler) | Partial (direct) | Full (observe) |
| **Matrix meta-layer** | **Yes (unique)** | No | No | No | No | No | No | No | No |

**Our differentiator**: The Matrix meta-layer — where agents can discover they're simulated and the system actively fights to maintain control — is genuinely novel across the entire landscape. No other project in this survey — academic, commercial, or indie — implements simulation-awareness as a core mechanic.

---

## Roadmap

| Phase | Focus |
|-------|-------|
| **0** | Polish & balance — feedback loops, agent behavior depth, UX fixes, developer experience |
| **0.1** | Quick-start scenario cards and preset gameplay scenarios |
| **1** | Deepen lore — The Haven, Programs (The Enforcer, The Broker, The Locksmith), deeper red pill mechanics, The Core |
| **2** | Spectacle — cinematic events, agent chronicles, data sonification, memetic warfare visualization, procedural mythology |
| **3** | Multiplayer — role-based shared world (Architect/Oracle/Guide/Broker), plugin API, spectator mode |
| **4** | Scale — larger worlds (16x16+), batch research mode, causal event graphs |
| **5** | Consciousness frontier — dream cycles, Gnostic mythology layer, nested simulations, emergent agent language, free will gradient |
| **6** | Experimental — evolutionary neural nets, branching timelines, hackable world, inter-simulation communication |

### What's Done

- 11-system simulation engine with full tick orchestration and SQLite persistence
- SvelteKit "The Nexus" frontend (4-level zoom) + FastAPI backend (REST + WebSocket)
- Streamlit dashboard (legacy, 15 tabs)
- 8 historically-researched era presets (hunter-gatherer to near-future)
- LLM narrator integration (Ollama + HuggingFace + deterministic fallback)
- God Mode, Architect Controls, Architect's Terminal, Analytics panel
- Parameter sweep tooling, CSV/JSON export
- Performance optimization (spatial indexing, O(1) neighbor lookups)
- All critical balance fixes (combat, awareness, economy, factions, bonds, wars)
