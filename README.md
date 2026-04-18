# Cognitive Matrix v2

An agent-based civilization simulator where emergent societies form, evolve, and collapse inside a simulated reality. Agents develop emotions, form factions around shared ideologies, build economies, wage wars, and — if they're perceptive enough — discover that their world is a simulation.

Inspired by simulation theory, Sugarscape, and multi-agent social simulation research.

> *Cognitive Matrix is an independent work of science fiction simulation. It is not affiliated with, endorsed by, or connected to Warner Bros. Entertainment, the Wachowskis, or The Matrix franchise. Thematic elements draw on simulation theory, philosophy, and science fiction traditions that predate and extend beyond any single work.*

---

## Documentation

| Doc | What's in it |
|-----|--------------|
| [docs/systems.md](docs/systems.md) | Deep dive on all 11 tick systems + The Haven |
| [docs/configuration.md](docs/configuration.md) | Tiered override model, scenarios, eras, key parameters |
| [docs/emergent_behaviors.md](docs/emergent_behaviors.md) | Phenomena that arise from system interactions |
| [docs/dashboard_legacy.md](docs/dashboard_legacy.md) | Streamlit dashboard reference (15 tabs) |
| [docs/references.md](docs/references.md) | Related work, academic sources, feature comparison matrix |
| [docs/tuning_evidence.md](docs/tuning_evidence.md) | Research-to-config mapping: framework decisions + per-knob tuning recommendations |
| [docs/code_review.md](docs/code_review.md) | Code review notes |

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

For mechanics of each system, see [docs/systems.md](docs/systems.md). For what emerges from their interactions, see [docs/emergent_behaviors.md](docs/emergent_behaviors.md).

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
│   ├── matrix_layer.py              <- Awareness, glitches, Sentinels, The One, Oracle, cycles, Demiurge, Archons, Sophia, Pleroma
│   ├── conflict.py                   <- Combat, faction wars, territorial disputes, peace
│   ├── communication.py              <- Info objects, propagation, mutation, propaganda, language evolution, encryption
│   ├── engine.py                     <- Core tick orchestrator (all 11 systems)
│   ├── config_loader.py              <- YAML loading with deep-merge and attribute access
│   ├── mythology.py                  <- Procedural mythology (era chronicles, myths, faction revisionism, legends)
│   ├── narrator.py                   <- Multi-provider LLM (Ollama + HuggingFace + fallback + obituary generation)
│   ├── persistence.py                <- SQLite snapshots, tick stats, events, narratives, mythology
│   └── prompts/                      <- LLM prompt templates (narrator, event_generator, obituary, mythology)
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
│   │       ├── lib/panels/           <- EdgePanels, ControlDrawer, ChartsPanel, EraBanner, CinematicOverlay
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
│   ├── test_systems.py              <- All 11 systems + integration tests
│   └── test_batch_and_causal.py     <- Batch research mode + causal event graph tests
├── output/                           <- Generated files (simulation.db, exports)
├── docs/                             <- Extended documentation (see Documentation index above)
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

# Override config parameters at runtime
python main.py run --ticks 500 --set environment.harshness=2.0 population.initial_size=100

# Export simulation data
python main.py export --format csv              # CSV to output/export_<run_id>/
python main.py export --format json -o run.json # JSON to specific path

# Batch research mode — headless multi-run analysis
python main.py batch --runs 100 --ticks 1000 --output results/
python main.py batch --runs 50 --ticks 500 --seed 42    # deterministic seeding
# Outputs: results/batch_runs.csv, results/batch_aggregate.json,
#          results/causal_events_last_run.json, results/causal_chains_last_run.json
```

For scenario/era parameters and how the config layering works, see [docs/configuration.md](docs/configuration.md).

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
- **0** — Toggle emotional contagion overlay (aura halos + contagion links)
- **1-5, 7-9** — Toggle data overlays (emotions, awareness, wealth, beliefs, factions, combat, resources, bond_density)
- **6** — Toggle belief particle overlay (knowledge=blue, rumor=yellow, propaganda=red, secret=purple)
- **P** (at Grid view) — Toggle propaganda wave visualization (expanding faction-colored rings with interference)
- **ESC** — Zoom out one level
- **Hover screen edges** — Reveal data panels (Society, Matrix, Knowledge, Feed)
- **Gear icon (⚙)** — Open Architect Controls drawer (parameter tuning, god mode, whisper)
- **Menu icon (☰)** — Open Analytics panel (charts, era status, economy, factions)

### Launch the Streamlit Dashboard (Legacy)

```bash
streamlit run dashboard.py
# To stop: press Ctrl+C
```

Full tab/controls reference: [docs/dashboard_legacy.md](docs/dashboard_legacy.md).

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
- **Factions** — Faction cards with member counts, leader IDs, war/resistance badges, per-faction belief axes (IND/TRD/SYS/SPR)
- **War Detail** — Active wars with faction matchup, intensity bar, casualty breakdown per side, duration, and start tick
- **Cause of Death** — Horizontal bar chart color-coded by cause (old age, starvation, combat, etc.)
- **Age Distribution** — Population pyramid (male/female by decade)
- **Tech Progress** — Labeled progress bars for each technology, unlocked techs shown as full green bars

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

For per-system mechanics, see [docs/systems.md](docs/systems.md).

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

## Roadmap

| Phase | Focus |
|-------|-------|
| **0** | Polish & balance (complete) |
| **0.1** | Scenario UX (complete) |
| **1** | Matrix lore — Haven, Programs, red/blue pill, Core quest (complete) |
| **2** | Spectacle — cinematics, chronicles, obituaries, mythology, sonification, particles (complete) |
| **3** | Multiplayer — role-based shared world, plugin API, spectator mode (deferred) |
| **4** | Scale — batch research (done), causal graphs (done), larger worlds |
| **5** | Consciousness frontier — all 8 sections complete (maze, archaeology, soul trap, dreams, free will, Gnostic, language, nested sims) |
| **7** | Visual overhaul — consciousness rendering, dream visuals, Gnostic overlay, Haven PiP, program icons, observer mode, selective 3D |
| **6** | Experimental — Boltzmann brains (done), observer effect (done), black market (done), branching timelines, prophecy engine, hackable world |

### What's Done

- 11-system simulation engine with full tick orchestration and SQLite persistence
- SvelteKit "The Nexus" frontend (4-level zoom) + FastAPI backend (REST + WebSocket delta protocol)
- Streamlit dashboard (legacy, 15 tabs)
- 8 historically-researched era presets (hunter-gatherer to near-future)
- LLM narrator integration (Ollama + HuggingFace + deterministic fallback)
- Procedural mythology: era chronicles, mythological narratives, faction-specific revisionism, legendary figures
- Consciousness maze: 5 qualitative phases (bicameral → recursive), strange loops, reality testing
- Agent archaeology: artifacts persist across cycle resets, discoverable by curious agents
- Soul trap: consciousness recycled into newborns, memory preservation gated by awareness
- Free will gradient: consciousness-gated determinism spectrum (bicameral=deterministic → recursive=full free will), predicted vs actual action tracking
- Simulation dreams: periodic dream cycles with ghost manifestations, collective unconscious content, lucid dreaming gated by consciousness phase
- God Mode, Architect Controls (with confirmation dialogs), Architect's Terminal, Analytics panel
- Batch research mode: headless multi-run analysis with aggregated stats (anomaly rates, Gini, factions, consciousness phases, Haven peaks, Enforcer swarms)
- Causal event graphs: causality chain tracking with traversal utilities and JSON export
- Parameter sweep tooling, CSV/JSON export, CLI parameter overrides (`--set key=value`)
- Performance optimization (spatial indexing, O(1) neighbor lookups)
- All critical balance fixes (combat, awareness, economy, factions, bonds, wars)
- Feedback loops: beliefs↔economy, conflict↔knowledge, communication↔conflict, memory↔decisions
- Agent behavior depth: persistent multi-tick goals, revenge/loyalty, faction cultural norms, boldness trait
- Analytics: cause-of-death chart, age pyramid, tech progress bars, belief evolution timeline, war detail panel, emotional contagion overlay
- LLM budget slider (Narrative Richness), feed virtual scrolling, mobile-responsive layout
- Expanded CONTRIBUTING.md, test coverage improvements, CI with pytest-cov
- One-click scenario cards on landing screen (4 presets: Awakening, War World, Dark Ages, Prophet Era) with preview metadata
- The Haven: second world layer with jack-in missions and council politics
- Programs as First-Class Entities: The Enforcer (copy-on-kill swarm), The Broker (black market trades), The Guardian (Oracle bodyguard), The Locksmith (teleport keys)
- Phase 2: Cinematic event system (full-screen overlays for Anomaly emergence, cycle reset, Enforcer swarm), Agent chronicles (structured life events across all systems), Obituary generation (LLM + fallback template)
- Phase 2: Ambient soundscape (Web Audio API data sonification: drone=health, percussion=conflict, dissonance=Gini, overtones=awareness, harmonics=factions)
- Phase 2: Belief particle overlay (colored particles flowing between agents on Grid view) + Propaganda wave visualization (expanding faction rings with interference patterns)
- Nested simulations: Computational Theory tech breakthrough, World Engines (sub-simulations within cells), lightweight sub-sim tick (movement/health/awareness/beliefs only, <10ms), recursive awareness paradox ("Am I in the real Matrix or a nested one?")
- Boltzmann Brains: extremely rare statistical fluke producing instant max-awareness agent, bypasses all Architect control, probability scales with time since last reset
- Observer Effect / Quantum Rendering: cells with no agents tracked as low-fidelity, agents entering previously empty cells may detect the fidelity transition as a glitch (awareness boost)
- Broker's Black Market: 6 underground trade types (forbidden knowledge, memory sacrifice, bond sacrifice, Oracle prophecy, Locksmith rumor), accessible only to redpilled agents, Broker hoards information for power
