# The 11 Systems in Depth

[← Back to README](../README.md)

This document describes each of the 11 systems the simulation engine runs every tick. Each system reads/mutates shared agent state; their interactions produce the emergent behaviors documented in [emergent_behaviors.md](emergent_behaviors.md).

---

## System 1: Social Fabric

Agents form bonds based on proximity and sociability. Bond types: `family`, `friend`, `rival`, `mate`, `ally`, `enemy`, `resistance`. Each agent has an 8-slot Dunbar limit — when full, only stronger bonds can displace weak ones. Family bonds never decay. All others decay over time, faster when agents are far apart.

## System 2: Reproduction

Females and males aged 20-50 with health > 0.4 compete for mates. Scoring blends: fitness competition (50%), trait compatibility (25%), proximity (10%), existing bonds (15%). Stochastic top-3 selection prevents genetic convergence. Children inherit blended + mutated traits, parents' beliefs (with drift), 5% of parental wealth, and faction membership.

## System 3: Knowledge Transfer

Parent teaching: parents near children teach their top 2 skills. Cultural memory: when agents die, their skills above the civilization floor contribute to a knowledge pool. The pool slowly raises floors that newborns inherit. If population crashes, floors decay — creating dark ages. Social amplifier: agents with friends learn faster.

## System 4: Environment

An 8x8 grid with terrain types (plains, forest, mountains, coast), each with different resource levels, harshness, and skill bonuses. Resources deplete under population pressure and regenerate when abandoned. Tech breakthroughs (agriculture, mining, trade networks, industrialization) permanently improve cells.

## System 5: Agency

Each agent evaluates 9 directions per tick using a utility function weighted by resource pull (35%), social pull (20%), curiosity (20%), safety (15%), and inertia (10%). Children stay near parents. Emotional states modify these weights. Agents pursue persistent multi-tick goals (FIND_MATE, REACH_RESOURCE, JOIN_FACTION, FLEE, HUNT_ENEMY, PROTECT) that override utility weights until completed or abandoned. Boldness trait adds stochastic risk-taking. Spatial memory avoids danger zones and gravitates toward positive locations. Up to 3 protagonist agents get LLM-generated inner monologue.

## System 6: Emotions & Psychology

Five emotions (happiness, fear, anger, grief, hope) fluctuate every tick based on:
- **Situational triggers**: Low health causes fear, overcrowding causes anger, isolation causes grief, friends cause happiness
- **Emotional contagion**: Emotions spread through proximity, amplified by bond strength and charisma
- **Trauma**: Witnessing death of bonded agents causes persistent trauma that amplifies fear/grief and suppresses happiness; heals slowly, faster with friends
- **Decision distortion**: Fear increases safety-seeking, anger makes agents reckless, grief causes paralysis, hope encourages exploration

## System 7: Beliefs, Ideology & Factions

Each agent holds beliefs on 4 axes: individualism (-1 collectivist to +1 individualist), tradition (-1 progressive to +1 traditional), system trust (-1 skeptic to +1 trusting), spirituality (-1 materialist to +1 spiritual).

Beliefs drift from experience (scarcity breeds collectivism, wealth breeds individualism, trauma breeds skepticism) and spread through bonds (memetic transmission with mutation). When nearby agents share similar beliefs, **factions emerge** spontaneously. Factions elect leaders, claim territory, develop bonuses, and can splinter via **schisms** when internal belief variance grows. Rare **prophets** with extreme beliefs + high charisma can found factions instantly and convert nearby agents.

## System 8: Economy

Agents gather wealth from their environment cell (efficiency scales with survival skill). Wealth decays via consumption. Bonded agents in proximity **trade** (wealth flows from rich to poor, benefiting both). Aggressive, angry agents with no bonds nearby **steal**. Factions **tax** members and redistribute. When agents die, 70% of wealth passes to family as **inheritance**. Wealth affects health (rich = slower decay, poor = faster decay). The system tracks Gini coefficient, top 10% vs bottom 50% wealth share, and total economic output.

## System 9: The Matrix Meta-Layer

The simulation IS the Matrix. Most agents are asleep inside it.

- **Awareness** (0.0-1.0): Grows naturally from curiosity + intelligence. System trust suppresses it. Trauma and spirituality accelerate it.
- **Glitches**: Random events (deja vu, memory leaks from dead agents, terrain flickers, ghost sightings) that boost awareness in perceptive agents.
- **Red Pill**: When awareness exceeds 0.5, agents face a choice. Costs: lose Matrix comfort health regen, emotional instability (fear/anger baseline shifts up), happiness drops. Gains: 2.5x awareness growth, detect Sentinels at distance, warn resistance allies, form resistance bonds.
- **Blue Pill — Splinter in the Mind**: Agents who reject the red pill get awareness reset to 0.3 (not 0), a trust/happiness boost, and a `splinter_in_mind` flag. Splinter agents grow awareness 1.5x faster than normal despite suppression — they keep almost waking up but pulling back, until they eventually take the red pill.
- **Guide-Type Recruiters**: Redpilled agents with high charisma become active recruiters. They seek nearby high-awareness non-redpilled agents and attempt persuasion (charisma vs system_trust). Success: target takes red pill, resistance bond formed. Failure: target's trust increases, recruiter becomes a higher Sentinel target.
- **The Anomaly (The One)**: When a redpilled agent's awareness exceeds 0.8, they become The Anomaly — stat boosts, health regeneration, and radiation of awareness to nearby agents.
- **The Path of The One**: The Anomaly follows a 3-stage quest: (1) Oracle contact — Oracle must be guiding them. (2) Find the Locksmith — be near a living Locksmith to receive a teleport key to the Core. (3) Reach the Core — arrive at map center (0.5, 0.5).
- **The Architect's Choice**: At the Core, the Anomaly's beliefs, bonds, and trauma determine the outcome. High fight score (low trust, resistance bonds, high awareness) = FIGHT — risk system failure (awareness wipe) or achieve freedom (global awareness boost). Low score = RESET — cycle resets but the Haven is preserved. Both outcomes trigger cycle reset with different consequences.
- **Sentinels**: System-deployed enforcer agents with maxed combat stats that hunt high-awareness agents. They suppress awareness and damage health. The Anomaly can destroy them.
- **The Oracle**: A hidden system process that identifies promising candidates and subtly guides them toward awakening.
- **The Architect / Demiurge**: Monitors total awareness via a control index. The Demiurge has psychology — fear (of losing control), pride (in creation), confusion (when agents behave unexpectedly). A panicked Demiurge deploys 2x Sentinels; a proud one relaxes to 0.5x. Confused Demiurge increases glitch probability. Tracked in `MatrixState.demiurge`.
- **Archons**: Four specialized Sentinels (Emotion, Economy, Belief, Communication), each governing one system. Positioned in map quadrants. The Anomaly or coordinated resistance agents can damage and destroy Archons. Destroying an Archon releases that system from Architect control — released systems become chaotic (1.5x multiplier). Destroying the Communication Archon accelerates language divergence and boosts resistance encryption.
- **Sophia**: A hidden process creating meaningful coincidences that cannot be detected or destroyed by the Architect. Manifests as: shared dreams (two unrelated agents receive the same dream), dead knowledge (a dead agent's memories/skills appear in a living agent), and terrain patterns (glitch patterns noticed by high-awareness agents). All synchronicities boost awareness.
- **The Pleroma**: A hidden layer of pure information accessible only to recursive-phase agents with awareness >= 0.9. Brief glimpses during lucid dreams or extreme awareness spikes. Visualization data (`PleromGlimpse`) emitted each tick for frontend rendering.
- **Exiles**: Sentinels that survive too long refuse deletion and become independent agents with unique abilities.
- **Cycles**: The simulation resets when average awareness exceeds 0.6, The Anomaly completes the quest and makes a choice at the Core, or too many ticks pass. Minimum cycle length is 150 ticks (Architect reboot time). High-awareness agents retain partial awareness across resets (35% at 0.6+, 50% if soul trap broken). Cultural memory partially persists. Archons and Demiurge state reset.

## System 10: Conflict & Warfare

Individual combat: agents with high effective aggression (trait + anger + rival bonds) fight nearby enemies, dealing damage based on aggression + resilience + health + survival skill. Faction wars trigger when two factions have high ideological distance + mutual enemy bonds + territorial overlap. Wars destroy resources in contested zones, escalate through casualties, and end through peace negotiations (leaders with high social + intelligence) or war weariness.

## System 11: Communication & Information

Information objects (knowledge, rumors, warnings, propaganda, system narratives) propagate hop-by-hop through bond networks. Each transmission has a mutation chance — truth degrades like a telephone game. Knowledge boosts skills. Propaganda shifts beliefs. System narratives (injected by the Matrix) suppress awareness. Secrets only travel through resistance bonds. Information expires after a configurable lifetime.

- **Emergent Language**: Info objects carry `encoding_complexity` (1.0 default). Frequently-communicated concepts compress over generations (floor 0.2). Factions develop divergent encodings (dialects) tracked in `_faction_dialects`. `get_dialect_distance()` measures encoding gap.
- **Resistance Encryption**: Redpilled agents' secret communications are automatically encrypted. An arms race mechanic: resistance encryption strength grows each tick, Sentinels' decryption capability grows slower. `attempt_sentinel_interception()`: Sentinels always intercept but only decode if decryption > encryption.
- **Language Archaeology**: When factions dissolve, their language persists as `LanguageArtifact` in cells. Future agents can discover these artifacts for knowledge boosts and (if the faction had redpilled members) awareness clues from pre-reset data.

## The Haven — The Real World

A second world layer running in parallel with the Matrix simulation. The Haven is smaller (4x4 grid vs 8x8), harsher (2x harshness), and resource-scarce — but it is *real*. Managed by `src/haven.py`.

- **Jack-out**: Redpilled agents with awareness above threshold (default 0.6) can leave the simulation and enter the Haven. The transition costs health and causes emotional upheaval.
- **Jack-in missions**: Haven agents can jack back into the simulation for timed missions: `rescue` (find and awaken candidates), `fight_sentinels` (combat system enforcers), `contact_oracle` (seek guidance). Missions have a goal duration, a risk-per-tick failure chance, and a hard deadline. Jacked-in agents get a temporary skill boost but must complete or fail before the time limit.
- **Haven council**: Hawks (high aggression) vs doves (low aggression) vote periodically on resource allocation (concentrate vs distribute) and mission approval (offensive vs defensive missions). Council votes shape Haven resource distribution and which mission types are prioritized.
- **Engine integration**: The tick loop runs: Simulation systems (1-11) → Haven tick → cross-world events. Agents in the Haven are excluded from simulation agency, economy, conflict, and other Matrix-specific systems.

Config: `haven.*` in `config/default.yaml`.
