# Cognitive Matrix v2

An agent-based civilization simulator where emergent societies form, evolve, and collapse inside a simulated reality. Agents develop emotions, form factions around shared ideologies, build economies, wage wars, and — if they're perceptive enough — discover that their world is a simulation.

Inspired by the Matrix trilogy, Sugarscape, and multi-agent social simulation research.

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
human-matrix-sim/
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
│   ├── backend/                      <- FastAPI backend (The Construct API)
│   │   └── api/
│   │       ├── main.py               <- FastAPI app, CORS, route mounting
│   │       ├── state.py              <- In-memory engine manager singleton
│   │       └── routes/               <- REST + WebSocket endpoints
│   ├── frontend/                     <- SvelteKit web frontend
│   │   ├── src/lib/canvas/           <- WebGL world map, code rain, agent views
│   │   ├── src/lib/panels/           <- Edge panels, terminal
│   │   ├── src/lib/stores/           <- Svelte stores (simulation, UI state)
│   │   └── src/lib/api/              <- REST + WebSocket client
│   └── dashboard/                    <- Streamlit dashboard (15 tabs)
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
├── scripts/                          <- Utility scripts
│   └── sweep.py                      <- Parameter sweep tool (outputs CSV)
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
git clone https://github.com/YOUR_USERNAME/human-matrix-sim.git
cd human-matrix-sim

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

### Launch the Dashboard

```bash
streamlit run dashboard.py
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

## The Dashboard

The Streamlit dashboard provides 15 tabs for monitoring and interacting with the simulation:

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
- **Cycles**: The Matrix resets when total awareness exceeds critical mass, The Anomaly reaches The Source, or too many ticks pass. Cultural memory partially persists across cycles.

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

### Games & Simulations

| Project | Relevance |
|---------|-----------|
| [**Dwarf Fortress**](https://www.bay12games.com/dwarves/) | Per-dwarf personality, emotions, social bonds, faction warfare, resource economy. Their thought/emotion system parallels our System 6 |
| [**WorldBox**](https://www.superworldbox.com/) | God-sim with emergent civilizations, wars, and tech progression. The "watch and intervene" model parallels our God Mode |

### Frameworks

| Framework | Relevance |
|-----------|-----------|
| [**Mesa**](https://github.com/projectmesa/mesa) (Python) | Standard Python ABM framework. Our engine builds equivalent functionality with domain-specific extensions |
| [**MASON**](https://github.com/eclab/mason) (Java) | High-performance ABM toolkit. Relevant for spatial indexing if scaling beyond 8x8 |

### Philosophical Foundation

| Reference | Relevance |
|-----------|-----------|
| [**Bostrom's Simulation Argument**](https://www.simulation-argument.com/) (2003) | The theoretical basis for our Matrix meta-layer: what would it mean for simulated entities to discover their reality? |
| **"Growing Artificial Societies"** (Epstein & Axtell, 1996) | The book that established agent-based social simulation. Our project can be positioned as "Sugarscape extended with belief dynamics, LLM narration, and simulation-awareness mechanics" |

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

| Feature | Cognitive Matrix | Generative Agents | Sugarscape | Dwarf Fortress | Project Sid |
|---------|-----------------|-------------------|------------|----------------|-------------|
| Agent count | ~50-500 | 25 | 100s | 100s | 1000+ |
| LLM integration | Hybrid (protagonists) | Full (all agents) | None | None | Full (all agents) |
| Social bonds | 8-slot Dunbar | Relationships | No | Detailed | Emergent |
| Belief/ideology | 4-axis + factions | No | Binary tags | Values system | Emergent |
| Economy | Trade + Gini | No | Sugar/spice | Detailed | Emergent |
| Generational | Reproduction + cultural memory | No | Yes | Yes | No |
| Emotions | 5 emotions + trauma + contagion | No | No | Yes (detailed) | No |
| Conflict/warfare | Faction wars | No | Basic | Detailed | Minimal |
| **Matrix meta-layer** | **Yes (unique)** | No | No | No | No |

**Our differentiator**: The Matrix meta-layer — where agents can discover they're simulated and the system actively fights to maintain control — is genuinely novel across this landscape.

---

## Roadmap

### Completed

- [x] Full system state persistence (factions, wars, matrix state, protagonists, info objects survive save/load)
- [x] Live Mode with auto-run and mid-simulation interventions
- [x] Agent interaction panel (Heal, Smite, Red Pill, Gift, Prophet, Protagonist, Whisper)
- [x] Visual character cards for protagonists with HP/emotion/trait bars
- [x] Header metrics with trend deltas and new systems row
- [x] Comprehensive tooltips for all parameters, controls, metrics, and achievements
- [x] Full world state restoration from snapshots (terrain, resources, techs all preserved)
- [x] Protagonist LLM decision overrides (inner monologue priority biases utility weights)
- [x] Emotion-modified agency (`get_emotion_utility_modifiers` integrated into `compute_move` — fear → safety seeking, grief → paralysis, hope → exploration)
- [x] Faction-specific cultural memory (each faction maintains independent knowledge pools with 1.5x contribution/absorption rates and 0.5x decay)
- [x] Matrix cycle reset (awareness wipe, sentinel removal, partial cultural memory preservation at 70%, resource regeneration, war dissolution)
- [x] Parameter sweep tooling (`scripts/sweep.py` — sweep any parameter with `--param`/`--values`/`--range`, outputs CSV with full stats)
- [x] Export simulation history to CSV/JSON (dashboard buttons + `db.export_run_csv()`/`db.export_run_json()`)
- [x] Performance optimization (spatial indexing with `SpatialIndex` for O(1) neighbor lookups, dict-based bond decay — 447 agents at ~106ms/tick)

### Phase 0: Polish & Improve Current Systems

> **Empirical findings**: We ran 6+ simulations across default, harsh, peaceful, high-awareness (10x), conflict-tuned (low threshold + high wealth), and god-mode scenarios, totaling 12,000+ agents. Results: zero combat, zero wars, zero redpilled agents, converging faction beliefs, and near-zero wealth under default parameters. Even with 10x awareness growth, agents die (~age 70-94) long before reaching the 0.5 redpill threshold. Even with low war thresholds and agents within combat range holding rival bonds, fear suppresses all effective aggression to negative values. God mode actions (red pill, gift wealth, whisper) have no lasting effect — modified agents die and replacements start from scratch.

#### Critical Balance Fixes (Systems Are Too Quiet)

- [x] **Conflict system is dead — fear suppresses all combat**: Fear no longer fully cancels aggression (capped at 50% penalty). Rival bonds now form naturally through social proximity between aggressive agents. Agents with rival/enemy bonds get a 30% chance to fight even below the aggression threshold. Combat threshold lowered from 0.5 to 0.35, combat radius increased.
- [x] **Awareness is mathematically unreachable**: Growth rate increased 10x (0.0005→0.005) with additive passive baseline so all agents accumulate. Awareness now partially inherits from parents (15%, 30% if redpilled). Elders gain awareness 1.5x faster. System trust suppression capped at 70%. Agents now routinely reach the 0.5 redpill threshold.
- [x] **God mode actions are ephemeral**: Awareness and redpilled status now inheritable. Redpilled parents pass 30% awareness and low system trust to children. Wealth inherits via the existing inheritance system. Whispered memories persist through the memory system.
- [x] **Faction beliefs converge**: Added faction core belief anchoring (members drift toward core beliefs). Cross-faction memetic transmission reduced to 30%, same-faction amplified 1.5x (echo chamber). Added environmental belief pressures: bond count affects individualism, combat experience shifts tradition, poverty breeds collectivism.
- [x] **Economy produces near-zero wealth**: Default gather_rate tripled from 0.05 to 0.15. Theft threshold lowered from 0.5 to 0.35. Economy now produces meaningful wealth, trades, and thefts that cascade into rival bonds and combat.
- [x] **Bonds never decay**: Removed proximity reinforcement (was canceling decay). Far-apart bonds now decay at 2x rate. Base decay rates increased for all non-family bond types. Bonds now properly churn.
- [x] **"Harsh world" grows 9x larger than default**: Scenario now includes hard population cap (120), lower carrying capacity (12), faster health decay (2x), harder reproduction (min health 0.6, half reproduction chance), scarcer resources, and higher maintenance costs.
- [x] **Tune faction warfare threshold**: Lowered from 0.6 to 0.4. War check interval reduced from 30 to 25 ticks. Rival bonds now actually form (see conflict fix), enabling the rivalry component of war score.
- [x] **Duplicate faction names**: Added uniqueness check with fallback to numbered names if all 380 prefix-suffix combinations are exhausted.

#### Additional Balance & Bug Fixes

- [x] **Fix Sentinel suppression scaling**: Max sentinels now scales with population (1 per 20 agents, minimum from config). System can deploy proportionally to population size.
- [ ] **Add population floor / soft reset**: When population drops below a critical threshold, trigger immigration or divine intervention instead of running empty.
- [x] **Fix communication mutation bug**: Hop count now increments before mutation check. Later recipients receive more degraded info (correct telephone-game behavior) while earlier recipients retain their version's truth level.
- [ ] **Move hardcoded values to config**: Baseline emotions, breakthrough population threshold, spatial index cell size, system narrative text, Sentinel trait templates, protagonist priority thresholds.
- [ ] **CLI Unicode crash on Windows**: `main.py` outputs Unicode characters (checkmarks, arrows) that crash on Windows cp1252 terminals without `PYTHONIOENCODING=utf-8`.

#### Missing Feedback Loops

- [x] **Economy ↔ Beliefs**: Wealth now drives individualism (wealth > 1.0 → individualist drift), poverty drives collectivism (wealth < 0.2 → collectivist drift). Rich agents with many bonds trend collectivist; isolated wealthy agents trend individualist.
- [ ] **Beliefs ↔ Economy**: Collectivist vs. individualist factions should have different trade/taxation behaviors instead of identical economic rules.
- [ ] **Conflict ↔ Knowledge**: Wars should produce innovation (wartime breakthroughs) and tactical knowledge, not just destruction.
- [ ] **Communication ↔ Conflict**: Propaganda info objects should influence war initiation and faction loyalty, not just belief drift.
- [ ] **Memory ↔ Decisions**: Agents keep 50 memories but never reference them. Traumatic memories should trigger avoidance; positive memories should create place attachment.
- [x] **Leadership ↔ Faction behavior**: Leader traits now affect faction bonuses — charismatic leaders boost recruitment, aggressive leaders lower war threshold, intelligent leaders improve cohesion, low-intelligence leaders cause faster member drift.

#### Agent Behavior Depth

- [ ] **Persistent goals**: Agents recalculate decisions from scratch every tick. Add multi-tick goals (find mate, reach resource, join faction) that create consistent character arcs.
- [x] **Emotional intensity scaling**: Emotion utility modifiers doubled/tripled. Fear now has 1.0x safety multiplier (was 0.5x). Grief causes near-paralysis at high levels (0.8x inertia). Anger overrides safety (0.6x reduction). Emotion baselines retuned: fear 0.05 (was 0.1), anger 0.05 (was 0.1), hope 0.35 (was 0.3).
- [ ] **Revenge and loyalty**: Agents who are robbed or whose mates are killed should actively hunt enemies. Agents should prioritize protecting bonded allies.
- [ ] **Faction cultural norms**: Factions should develop localized customs — trade-only-with-members, mandatory tithes, warrior culture bonuses, pacifist combat penalties.
- [ ] **Risk-taking**: Add a boldness trait or state so agents occasionally take suboptimal actions for ideological, emotional, or relational reasons — sacrifice for love, gamble on unlikely ventures.

#### Dashboard & UX

- [ ] **LLM budget slider**: "Narrative Richness" control — Off / Low / Medium / High — controlling how many LLM calls per tick cycle.
- [ ] **Confirmation dialogs for God Mode**: Plague, Meteor, and Famine trigger instantly with no undo. Add confirmation with consequence preview.
- [ ] **Cause-of-death breakdown**: Chart showing starvation vs. old age vs. combat vs. sentinel kills. Critical for diagnosing systemic problems.
- [ ] **Age distribution pyramid**: Standard demographic visualization — immediately reveals aging populations or baby booms.
- [ ] **Tech progress indicators**: Show proximity to next breakthrough, not just unlocked techs.
- [ ] **War detail panel**: Territory control visualization, casualty breakdown by faction, war progress (who's winning), and combat history timeline.
- [ ] **Belief evolution timeline**: Track how a faction's core beliefs shifted over time — "How did this faction radicalize?"
- [ ] **Emotional contagion visualization**: Trace how panic or hope spreads through the population. Identify emotional epicenters.
- [ ] **Feed pagination**: With 10,000+ entries, the live feed renders all items into the DOM. Add pagination or virtual scrolling.
- [ ] **Mobile-responsive layout**: Metric rows (7 columns) and 15 tabs break on small screens. Use adaptive columns and icon-only tabs on mobile.

#### Developer Experience & Community Readiness

- [ ] **CONTRIBUTING.md**: How to add a new system, a new config parameter, a new scenario, and a new dashboard tab. Essential before open-sourcing.
- [ ] **More scenarios**: Only 2 scenarios for 11 systems. Add: `matrix_aware` (high awareness growth), `tribal` (small bonds, fast rumor decay), `tech_race` (high mutation, fast breakthroughs), `knowledge_paradise` (strong cultural memory), `isolated_cells` (high terrain variation, low trade radius). *(Partially fulfilled: 8 historically-researched era presets now provide rich initial conditions; gameplay-focused scenarios still needed.)*
- [x] **Fix harsh_world scenario**: Added hard population cap (120), lower carrying capacity (12 per cell), 2x health decay, 3.5x elder decay, halved reproduction chance, higher health threshold to reproduce (0.6), scarcer resources (gather_rate 0.08), and higher maintenance costs.
- [ ] **CLI export command**: `persistence.py` has `export_run_csv()` and `export_run_json()` but no CLI interface. Add `python main.py export --format csv`.
- [ ] **CLI parameter overrides**: Allow `python main.py run --set environment.harshness=2.0` for quick experiments without creating scenario files.
- [ ] **Test coverage gaps**: Add tests for extinction recovery, bond capacity overflow, extreme parameter ranges, info object expiration, war triggering thresholds, and Matrix cycle reset with scaling populations.
- [ ] **CI improvements**: Add coverage reporting (pytest-cov), linting (ruff/black), sweep.py validation, and scenario YAML schema checks.

### Phase 0.1: Quick-Start & Scenario UX

- [ ] **One-click scenario cards**: Replace the scenario dropdown with visual cards showing scenario name, description, and key parameter highlights. Click to start a new sim with that config instantly.
- [x] **Choosable initial conditions**: ~~Let users pick starting population size, world size, initial era (e.g., "start in Bronze Age" with pre-leveled skills and techs), and seed agent archetypes (warriors, scholars, prophets) before launching.~~ Fulfilled by the Historical Era system (`--era` flag) — 8 researched presets from hunter-gatherer bands to near-future dystopia, each with calibrated demographics, economy, beliefs, and pre-unlocked tech.
- [ ] **Scenario preview**: Before starting, show a brief summary of what to expect — "This scenario typically produces wars by tick 200 and Matrix awakening by tick 500" — based on pre-run statistics.
- [ ] **Preset "interesting" scenarios**: Bundle scenarios that are known to produce drama — e.g., `awakening` (high awareness + low trust), `warworld` (high aggression + low war threshold + high gather rate), `dark_ages` (high harshness + low regen), `prophet_era` (high charisma variance + low faction threshold).

### Phase 1: Deepen the Matrix Lore

- [ ] **Zion — The Real World**: A second, harsher world layer where redpilled agents "jack out" to. Zion agents can jack back in on missions (rescue candidates, fight Sentinels, contact the Oracle). Zion has its own council politics, resource scarcity, and internal tensions — mirroring the films' Morpheus-vs-pragmatist divide. Both worlds run in parallel each tick, connected by jack-in/jack-out events.
- [ ] **Programs as first-class entities**: The Matrix is populated by programs with their own agendas beyond the Architect's control:
  - **Agent Smith** — a replicating agent. When Smith defeats an agent, that agent becomes another Smith copy. A runaway Smith swarm is an existential threat that forces cycle resets.
  - **The Merovingian** — an exile who hoards information and trades in secrets. Runs a black market for awareness, wealth, and forbidden knowledge.
  - **Seraph** — Oracle's protector. Intercepts Sentinel attacks on Oracle-guided agents.
  - **The Keymaker** — rare NPC who creates shortcuts (teleportation between grid cells) for resistance agents.
- [ ] **The Choice — Deeper Red Pill / Blue Pill**: Agents who take the red pill lose Matrix comforts (health regen, system trust buffs) but gain abilities (see through glitches, detect Sentinels, form resistance bonds). Blue pill agents forget their awareness spike and get a happiness/trust boost — but a lingering "splinter in the mind" that can resurface. Morpheus-type agents actively recruit high-awareness candidates with persuasion checks.
- [ ] **The Source & The Path of The One**: The Anomaly's journey follows the films — visit the Oracle (gain prophecy), find the Keymaker, reach the Source (map center). At the Source, the Architect presents the choice: reset the cycle (preserving Zion) or fight (risking total extinction). Each cycle's One can make a different choice, creating branching history.

### Phase 2: Make It Fun to Watch & Share

- [ ] **LLM budget slider**: A "Narrative Richness" control in the dashboard — Off (deterministic fallback), Low (narrator summaries every N ticks), Medium (narrator + protagonist inner monologue), High (narrator + monologue + agent dialogue during key events + Oracle prophecies).
- [ ] **Cinematic event system**: Key Matrix moments get special dashboard treatment — The One emerging (full-screen banner with narrative), cycle resets (dramatic countdown with age summary), Smith swarm (escalating warnings), Zion's last stand (Sentinel breach sequence).
- [ ] **Agent stories & chronicle**: Each agent accumulates structured life events (born, taught by, joined faction, witnessed war, took red pill). "Obituary" button generates an LLM summary of any agent's life. A Civilization Chronicle tab auto-generates narrative history organized by era.

### Phase 3: Multiplayer & Community

- [ ] **Role-based shared world**: One player hosts a simulation, others connect via browser. Each player picks a role with different powers:
  - **Architect** — god mode, system controls, deploy Sentinels
  - **Oracle** — whisper to agents, influence awareness, guide candidates
  - **Morpheus** — red-pill agents, recruit for Zion, lead resistance
  - **Merovingian** — manipulate economy, trade information, hoard secrets
- [ ] **System plugin API**: A clean interface (`class System: def tick(self, agents, world, config) -> events`) so contributors can add new systems without touching the engine core.
- [ ] **Scenario & event pack sharing**: A community folder for user-submitted YAML scenarios and LLM prompt packs (noir, comedy, documentary narrative styles).
- [ ] **Spectator mode**: A lightweight read-only web view with auto-narrated LLM commentary and optional chat overlay where spectators vote on god-mode interventions.

### Phase 4: Scale & Research

- [ ] **Larger worlds**: 16x16 or 32x32 grids with chunked spatial indexing. Natural geography (rivers as borders, ocean crossings, mountain passes as chokepoints). Isolated civilizations that eventually make "first contact."
- [ ] **Batch research mode**: Headless runs with no dashboard overhead. Run 100+ simulations, aggregate stats (Anomaly emergence rate, average civilization lifespan, Gini distributions), export research datasets.
- [ ] **Causal event graphs**: Track causality chains ("Agent X died → Agent Y traumatized → Y became prophet → Founded faction Z → War with faction A"). Visualize as interactive graphs in the dashboard.
