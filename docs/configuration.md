# Configuration

[← Back to README](../README.md)

Cognitive Matrix uses a layered YAML configuration system. Every tunable lives in [config/default.yaml](../config/default.yaml); eras, scenarios, CLI flags, and runtime sliders layer on top.

---

## Tiered Override System

1. `config/default.yaml` — Full defaults (every parameter)
2. `config/eras/*.yaml` — Historically-researched era presets
3. `config/scenarios/*.yaml` — Gameplay-tuned partial overrides
4. CLI flags — `--era`, `--scenario`, `--ticks`, `--set key=value`
5. Dashboard sliders — Runtime only

## Preset Scenarios

One-click scenario cards on the landing screen let you jump into curated experiences. Each scenario YAML includes `preview` text and `highlights` tags displayed on the card.

| Scenario | Theme | Key Tuning |
|----------|-------|------------|
| `awakening` | Mass red-pilling | 3x awareness growth, 4x glitch frequency, low redpill threshold |
| `warworld` | Endless conflict | Low combat threshold, scarce resources, fast faction formation |
| `dark_ages` | Knowledge collapse | 0.4x learning, 8x cultural memory decay, harsh environment |
| `prophet_era` | Ideological chaos | Frequent prophets, extreme beliefs, rapid faction churn |

## Creating a Custom Scenario

```yaml
# config/scenarios/my_experiment.yaml
description: "High awareness, fast factions"
preview: "Factions form by tick 100, wars by tick 200"
highlights:
  - "Fast factions"
  - "High awareness"
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

## Historical Eras

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

## Key Parameters

| Parameter | YAML Path | Effect |
|-----------|-----------|--------|
| Harshness | `environment.harshness` | Above 2.0 causes population collapse |
| Population floor | `population.min_floor` | Spawn immigrants when pop drops below this |
| Mutation rate | `genetics.mutation_rate` | High = genetic drift, low = convergence |
| Competition weight | `mate_selection.weights.competition` | High = premature convergence risk |
| Cultural floor cap | `knowledge.cultural_memory.floor_cap` | Higher = faster compound growth |
| Emotion baselines | `emotions.baselines.*` | Target emotions for natural decay |
| Emotional contagion | `emotions.contagion_rate` | Higher = mass panics, collective joy |
| Faction similarity | `beliefs.faction_formation_similarity` | Lower = more factions, more fragmented |
| Awareness growth | `matrix.awareness_growth_rate` | Higher = faster awakening, more system resistance (tuned to 0.008 so agents reach lucid within ~80-tick lifespan) |
| Glitch probability | `matrix.glitch_probability` | Higher = more Matrix instability |
| Sentinel traits | `matrix.sentinel_traits.*` | Customize Sentinel stats (resilience, aggression, speed) |
| Comfort injection | `matrix.comfort_injection.*` | System comfort values (happiness, trust, awareness) |
| Anomaly bonuses | `matrix.anomaly_bonuses.*` | The One's skill/health boosts |
| Red pill costs | `matrix.redpill_health_regen_loss`, `redpill_emotion_shift_*` | Health drain & emotional instability |
| Blue pill splinter | `matrix.bluepill_awareness_floor`, `splinter_awareness_multiplier` | Splinter-in-mind awareness growth |
| Recruiter settings | `matrix.recruiter_charisma_threshold`, `recruiter_check_interval` | Guide-type recruiter persuasion |
| Anomaly quest | `matrix.quest_oracle_contact_awareness`, `quest_locksmith_radius`, `quest_core_radius` | Path of The One stages |
| Core choice | `matrix.core_choice_fight_threshold`, `core_fight_failure_chance` | Architect's Choice outcomes |
| Combat damage | `conflict.combat_damage` | Higher = deadlier wars |
| War threshold | `conflict.war_threshold` | Lower = wars start more easily |
| Wartime innovation | `conflict.wartime_innovation_bonus` | Tech/survival skill bonus during wars |
| Trade rate | `economy.trade_rate` | Higher = faster wealth equalization |
| Faction tax | `economy.faction_tax_rate` | Higher = more redistributive factions |
| Narrative richness | `narrator.richness` | Off/Low/Medium/High LLM call frequency |
