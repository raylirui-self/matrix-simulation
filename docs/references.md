# Related Work & References

[← Back to README](../README.md)

Projects and research that inform this simulation's design.

---

## Closest Comparisons

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

## Classic Simulation & God Games

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

## Life Simulation & Artificial Life

| Project | Year | Relevance |
|---------|------|-----------|
| [**Creatures**](https://en.wikipedia.org/wiki/Creatures_(video_game_series)) (Cyberlife) | 1996 | Neural-network-brained creatures that learn, evolve genetically, and exhibit emergent behavior. Pioneered bottom-up emergent intelligence |
| [**The Sims**](https://www.ea.com/games/the-sims) (Maxis) | 2000+ | Maslow-based needs hierarchy, social bonds, emergent stories from autonomous behavior. Household-scale, not society-scale |
| **Conway's Game of Life** | 1970 | Zero-player cellular automaton — the foundational example of emergence from simple rules. No agents or social dynamics |
| [**Tierra**](https://en.wikipedia.org/wiki/Tierra_(computer_simulation)) (Thomas Ray) | 1991 | Self-replicating programs competing in a digital ecology; parasites and symbiotes emerge. No social/cognitive layer |
| [**Avida**](https://avida.devosoft.org/) (Michigan State) | 2003 | Digital evolution platform where programs evolve and compete on a lattice. Pure evolution research |
| [**Lenia**](https://chakazul.github.io/lenia.html) (Bert Chan) | 2015 | Continuous Game of Life generalization with 400+ emergent species. Mathematical/artistic, no cognition |
| [**The Bibites**](https://leocaussan.itch.io/the-bibites) | 2021 | Neural-network virtual creatures evolving via mutation and natural selection. Individual organism focus |

## Colony & Society Simulations

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

## Grand Strategy & Emergent History

| Project | Year | Relevance |
|---------|------|-----------|
| [**Crusader Kings 3**](https://www.crusaderkings.com/) | 2020 | Dynasty simulation with per-character traits, relationships, schemes, and emergent political narratives across generations. Player controls one dynasty |
| [**Victoria 3**](https://www.paradoxinteractive.com/games/victoria-3) | 2022 | Population groups (Pops) with political leanings, economic roles, and social movements. Macro-scale nation management |
| **Humankind** (Amplitude) | 2021 | 4X strategy combining 60 historical cultures across eras. Turn-based, not agent-based |
| **Mount & Blade II: Bannerlord** | 2022 | Dynamic factions, economy, NPC agency in a living political world. Action-RPG hybrid |

## Procedural History & Worldbuilding

| Project | Year | Relevance |
|---------|------|-----------|
| [**Caves of Qud**](https://www.cavesofqud.com/) | 2015+ | Procedural civilization generation with religions, art styles, languages, and mythic biographies. Player explores, doesn't simulate |
| [**Ultima Ratio Regum**](https://www.ultimaratioregum.co.uk/) | 2012+ | Procedural civilizations with religions, ideologies, art, and political systems. Academic art project |
| [**Galimulator**](https://snoddasmannen.itch.io/galimulator) | 2017 | Galactic empire rise/fall simulation with wars, dynasties, and revolutions. Abstracted agents at galactic scale |
| [**Screeps**](https://screeps.com/) | 2016 | MMO where players write JavaScript to control autonomous colony agents 24/7 in a persistent world. Player writes the AI |

## Multi-Agent LLM Frameworks

| Project | Year | Relevance |
|---------|------|-----------|
| [**AgentVerse**](https://github.com/OpenBMB/AgentVerse) (Tsinghua) | 2023 | Multi-agent framework for orchestrating LLM agents; supports task-solving and simulation |
| [**AutoGen**](https://github.com/microsoft/autogen) (Microsoft) | 2023 | Multi-agent conversation framework for complex problem-solving |
| [**MetaGPT**](https://github.com/geekan/MetaGPT) (DeepWisdom) | 2023 | Multi-agent framework assigning SOPs and roles to LLM agents |
| [**CrewAI**](https://github.com/crewAIInc/crewAI) | 2023 | Teams of LLM agents with roles handling workflows |
| [**Voyager**](https://voyager.minedojo.org/) (NVIDIA) | 2023 | First LLM-powered lifelong learning agent in Minecraft; continuous skill acquisition. Single agent |
| [**MineLand**](https://github.com/cocacola-lab/MineLand) | 2024 | Multi-agent Minecraft simulator supporting 48 agents with physical needs and limited senses |

## Emergent Behavior Research

| Project | Year | Relevance |
|---------|------|-----------|
| [**OpenAI Hide-and-Seek**](https://openai.com/index/emergent-tool-use/) | 2019 | Multi-agent RL agents discover 6 emergent strategies including tool use from simple competitive rules |
| [**Melting Pot**](https://github.com/google-deepmind/meltingpot) (DeepMind) | 2021 | Multi-agent RL environment for studying social dilemmas with up to 16 players |
| [**Facade**](https://www.interactivestory.net/) (Mateas & Stern) | 2005 | First interactive drama with believable AI characters using natural language. Two-character drama |

## ABM Frameworks

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

## Foundational Academic Models

| Reference | Year | Relevance |
|-----------|------|-----------|
| **Schelling's Segregation Model** | 1971 | Mild individual preferences create extreme macro-level segregation — foundational emergence demonstration |
| **Axelrod's Cooperation Tournament** | 1984 | Iterated Prisoner's Dilemma showing how cooperation emerges among self-interested agents |
| **El Farol Bar Problem** (W. Brian Arthur) | 1994 | Bounded rationality and emergent coordination without central control |
| **Santa Fe Artificial Stock Market** | 1994 | Agent-based stock market with evolutionary trading strategies — emergent economic dynamics |
| **Artificial Anasazi Model** (Axtell et al.) | 2002 | ABM reconstruction of Anasazi civilization collapse using archaeological data |
| **Cliodynamics** (Peter Turchin) | 2003+ | Mathematical models finding patterns in historical data to predict political instability — inspired by Asimov's psychohistory |
| [**JASSS**](https://www.jasss.org/) | 1998+ | *Journal of Artificial Societies and Social Simulation* — the primary academic journal for social simulation research |

## Opinion Dynamics & Belief Formation

Formal models of how beliefs drift, cluster into factions, and schism — theoretical backbone for System 7. Tuning-relevant findings mapped to config lines in [tuning_evidence.md](tuning_evidence.md).

| Reference | Year | Relevance |
|-----------|------|-----------|
| **Deffuant, Neau, Amblard, Weisbuch** (*Adv. Complex Syst.*) | 2000 | Bounded-confidence model (DW) — cluster count ≈ 1/(2ε) in 1-D; consensus for ε > 0.5 |
| **Hegselmann & Krause** (*JASSS* 5(3):2) | 2002 | HK bounded-confidence on complete graphs — consensus threshold ε_c ≈ 0.2 |
| **Castellano, Fortunato, Loreto** (*Rev. Mod. Phys.* 81:591) | 2009 | Canonical survey of statistical-physics approaches to social dynamics |
| **Lorenz** (*Int. J. Mod. Phys. C* 18:1819) | 2007 | BC survey; documents non-monotonic "consensus-strikes-back" windows |
| **Duggins** (*JASSS* 20(1):13) | 2017 | Empirical fit of extended DW to ANES 2012 — real-world ε ≈ 0.2–0.3 |
| **Axelrod** (*J. Confl. Resolut.* 41:203) | 1997 | Culture-dissemination model — F-q phase transition; discontinuous for F ≥ 3 |
| **Klemm et al.** (*Phys. Rev. E* 67:045101R) | 2003 | Noise-scaling law **r_c ~ 1/(N log N)** — critical design constraint for mutation |
| **Fernández-Gracia et al.** (*Phys. Rev. Lett.* 112:158701) | 2014 | Noisy voter fit to US elections 1980–2012 — σ_e ≈ 0.11, D = 0.03 |
| **Xie et al.** (*Phys. Rev. E* 84:011130) | 2011 | **10% committed-minority tipping** threshold (theoretical, binary-agreement) |
| **Centola, Becker, Brackbill, Baronchelli** (*Science* 360:1116) | 2018 | **25% experimental tipping** threshold (controlled online study) |
| **Baumann, Lorenz-Spreen, Sokolov, Starnini** (*Phys. Rev. X* 11:011012) | 2021 | Multidimensional activity-driven model — emergent ideological sorting across T topics |
| **Cinelli et al.** (*PNAS* 118:e2023301118) | 2021 | Echo-chamber empirics across 10⁸ items — platform topology dominates homophily |
| **Jager & Amblard** (*CMOT* 10:295) | 2005 | Repulsive BC — schism mechanism; pure attraction cannot polarize |
| **Flache & Macy** (*J. Math. Sociol.* 35:146) | 2011 | Signed-influence on small-worlds — long-range ties *accelerate* polarization |
| **Gleeson et al.** (*Phys. Rev. X* 6:021019) | 2016 | Twitter meme innovation rate 0.02–0.10; Zipf-like popularity near criticality |

## Language Emergence & Cultural Transmission of Communication

Theoretical backbone for System 11 (emergent language, dialect divergence, resistance encryption).

| Reference | Year | Relevance |
|-----------|------|-----------|
| **Kirby, Cornish & Smith** (*PNAS* 105:10681) | 2008 | Iterated learning with human chains — languages compress under transmission bottleneck |
| **Kirby, Tamariz, Cornish & Smith** (*Cognition* 141:87) | 2015 | Bayesian ILM — compositionality requires learnability + expressivity pressures jointly |
| **Brighton** (*Artificial Life* 8:25) | 2002 | Analytic proof: compositional stability requires bottleneck ratio b ≤ 0.1 |
| **Steels** (*Artificial Life* 2:319; *Talking Heads*) | 1995–2001 | Naming games — seminal agent-based language-emergence model |
| **Baronchelli et al.** (*J. Stat. Mech.* P06014) | 2006 | Naming-game scaling: **t_conv ∝ N^1.5**, peak memory ∝ √N on complete graphs |
| **Dall'Asta, Baronchelli, Barrat & Loreto** (*Phys. Rev. E* 74:036105) | 2006 | Network topology effects — community structure → multi-language metastability |
| **Raviv, Meyer & Lev-Ari** (*Proc. R. Soc. B* 286:20191262) | 2019 | Larger groups produce *more* systematic languages (input-variability mechanism) |
| **Pierrehumbert** (*Lang. & Speech* 46:115) | 2003 | Exemplar theory of phonetic change — frequency-based lenition |
| **Nettle** (*Linguistic Diversity*; *Lingua* 108:95) | 1999 | Social-impact sims — small communities diverge 2–3× faster than large ones |
| **Swadesh** (*Proc. Am. Phil. Soc.* 96:452); **Lees** (*Language* 29:113) | 1952, 1953 | Glottochronology — retention r ≈ 0.8048/ka, cognate half-life ~3200 yr |
| **Bergsland & Vogt** (*Curr. Anthropol.* 3:115) | 1962 | 5× rate variation in glottochronology (Icelandic vs Norwegian) |
| **Pagel, Atkinson & Meade** (*Nature* 449:717) | 2007 | ~100× word-replacement rate variation; frequency predicts 50% of rate variance |
| **Gray & Atkinson** (*Nature* 426:435); **Bouckaert et al.** (*Science* 337:957) | 2003, 2012 | Bayesian phylogenetics of Indo-European — relaxed-clock language dating |
| **Lazaridou, Peysakhovich & Baroni** (ICLR) | 2017 | Emergent-language deep-learning — codes opaque to humans but informative |
| **Skyrms** (*Signals*, OUP) | 2010 | Lewis signaling games — partial-pooling equilibria dominate for N ≥ 3 |
| **Dawkins & Krebs** (*Proc. R. Soc. B* 205:489) | 1979 | Predator–prey signaling arms races — life-dinner principle, partial-opacity stable |

## Cultural Evolution & Knowledge Transmission

Theoretical backbone for System 3 (knowledge transfer, cultural memory floors, dark ages).

| Reference | Year | Relevance |
|-----------|------|-----------|
| **Cavalli-Sforza & Feldman** (*Cultural Transmission and Evolution*, Princeton) | 1981 | Foundational formal theory of cultural inheritance |
| **Boyd & Richerson** (*Culture and the Evolutionary Process*, Chicago) | 1985 | Dual-inheritance theory — formal model of biased social learning (conformist, prestige, payoff) |
| **Tomasello** (*The Cultural Origins of Human Cognition*, Harvard) | 1999 | The "ratchet effect" — cumulative cultural evolution as human-distinctive |
| **Henrich** (*American Antiquity* 69:197) | 2004 | **Tasmanian model** — population below critical threshold loses cultural complexity |
| **Henrich** (*The Secret of Our Success*, Princeton) | 2015 | Collective-brain hypothesis — human adaptation is cultural, not individual |
| **Mesoudi** (*Cultural Evolution*, Chicago) | 2011 | Formal synthesis — Darwinian concepts for cultural transmission with empirical methods |
| **Kline & Boyd** (*Proc. R. Soc. B* 277:2559) | 2010 | Oceanic marine toolkits scale with population size + contact — empirical support for Henrich |
| **Powell, Shennan & Thomas** (*Science* 324:1298) | 2009 | Late Pleistocene cultural complexity tracks demographic thresholds |
| **Derex, Beugin, Godelle & Raymond** (*Nature* 503:389) | 2013 | Experimental: larger groups maintain higher cultural complexity |
| **Deffner, Kandler & Fogarty** (*Evol. Hum. Sci.* 4:e17) | 2022 | Critical: *effective* population matters more than census — depends on transmission mode + network |
| **Bentley, Hahn & Shennan** (*Proc. R. Soc. B* 271:1443) | 2004 | Neutral models — drift alone produces many observed cultural-frequency patterns |
| **Sperber** (*Explaining Culture*, Blackwell) | 1996 | Cultural attraction theory — stability from convergent transformation, not faithful copying |
| **Claidière, Scott-Phillips & Sperber** (*Phil. Trans. R. Soc. B* 369:20130368) | 2014 | Formal contrast: attraction-based vs selection-based accounts |
| **Acerbi, Charbonneau, Miton & Scott-Phillips** (*Evol. Hum. Sci.*) | 2023 | Cultural stability can emerge from convergent transformation alone (no copying required) |
| **Laland, Odling-Smee & Myles** (*Nat. Rev. Genet.* 11:137) | 2010 | 100+ cases of gene-culture coevolution (lactase, amylase, ADH) |
| **Heyes** (*Cognitive Gadgets*, Harvard) | 2018 | Even imitation and mind-reading are culturally acquired — culture builds the mind |
| **Henrich, Heine & Norenzayan** (*BBS* 33:61) | 2010 | The **WEIRD problem** — most psych data come from unrepresentative populations |
| **Bond & Smith** (*Psychological Bulletin* 119:111) | 1996 | Conformity varies across cultures — collectivist > individualist societies |
| **Aplin et al.** (*Nature* 518:538) | 2015 | Great tits show conformity-maintained foraging traditions — animal cultural evolution |
| **Brinkmann et al.** (*Nature Human Behaviour*) | 2023 | Machine culture — LLMs as cultural transmission participants at scale |

## Consciousness Theories for Agent Awareness

Theoretical backbone for System 9 (Matrix awareness, consciousness phases, free-will gradient). See [tuning_evidence.md](tuning_evidence.md) for phase-boundary analysis.

| Reference | Year | Relevance |
|-----------|------|-----------|
| **Baars** (*A Cognitive Theory of Consciousness*, CUP) | 1988 | **Global Workspace Theory** — consciousness as broadcast to specialist modules |
| **Dehaene & Naccache** (*Cognition* 79:1) | 2001 | Global Neuronal Workspace — biological implementation of broadcast |
| **Mashour, Roelfsema, Changeux & Dehaene** (*Neuron* 105:776) | 2020 | GNW canonical review — ignition, P3b, 200–300 ms threshold |
| **Goyal et al.** (ICLR; arXiv:2103.01197) | 2022 | Transformer-style ML analog of GWT — directly implementable reference design |
| **Oizumi, Albantakis & Tononi** (*PLoS CB* 10:e1003588) | 2014 | **IIT 3.0** — Φ as integrated information, formal cause-effect structure |
| **Albantakis et al.** (*PLoS CB* 19:e1011465) | 2023 | **IIT 4.0** — intrinsic-difference measure, non-negative system φ |
| **Mediano et al.** (arXiv:2109.13186 → *PNAS* 2025) | 2021 | **ΦID** synergy-redundancy decomposition — tractable proxy for Φ |
| **Barrett & Seth** (*PLoS CB* 7:e1001052) | 2011 | Φ_AR — Granger-based Φ proxy; what most neuroimaging papers actually compute |
| **Aaronson** (Shtetl-Optimized blog) | 2014 | Expander-graph objection — IIT assigns high Φ to intuitively unconscious structures |
| **Doerig, Schurger, Hess & Herzog** (*Conscious. Cogn.* 72:49) | 2019 | **Unfolding argument** — behavioral equivalents have different Φ; problem for IIT |
| **Rosenthal** (*Consciousness and Mind*, OUP) | 2005 | **Higher-Order Thought** theory — consciousness as meta-representation |
| **Lau & Rosenthal** (*TiCS* 15:365) | 2011 | Empirical HOT — PFC role, blindsight dissociation |
| **Maniscalco & Lau** (*Conscious. Cogn.* 21:422) | 2012 | **meta-d′ / M-ratio** — cleanest quantitative consciousness measure in the literature |
| **Brown, Lau & LeDoux** (*TiCS* 23:754) | 2019 | HOROR — phenomenality from higher-order representation itself |
| **Friston** (*Nat. Rev. Neurosci.* 11:127) | 2010 | **Free Energy Principle** — agents minimize variational free energy |
| **Parr, Pezzulo & Friston** (*Active Inference*, MIT) | 2022 | Active-inference textbook — unifies perception, action, learning via EFE |
| **Clark** (*BBS* 36:181; *Surfing Uncertainty*, OUP) | 2013, 2016 | Predictive processing — hierarchical generative models of the world |
| **Metzinger** (*Being No One*, MIT) | 2003 | Self-model theory — phenomenal self as transparent representational process |
| **Blanke & Metzinger** (*TiCS* 13:7) | 2009 | **Minimal Phenomenal Selfhood** — ownership + agency + 1PP as conjunctive criterion |
| **Hofstadter** (*Gödel, Escher, Bach*; *I Am a Strange Loop*) | 1979, 2007 | Strange loops — self-reference as core of the "I" |
| **Löb** (*J. Symbolic Logic* 20:115) | 1955 | **Löb's theorem** — agents cannot consistently prove own soundness (principled ceiling) |
| **Jaynes** (*Origin of Consciousness in the Breakdown of the Bicameral Mind*) | 1976 | Bicameral mind — historically wrong but source-monitoring intuition is salvageable |
| **Luhrmann** (*When God Talks Back*; *Top. Cogn. Sci.* 7:646) | 2012, 2015 | Modern rescue of Jaynes — source-monitoring and inner-speech attribution are culturally calibrated |
| **Fernyhough** (*The Voices Within*, Basic) | 2016 | Inner speech as internalized Vygotskian dialogue — mechanistic alternative to bicameralism |
| **Colombo & Wright** (*Synthese* 198:3463) | 2021 | FEP-is-not-falsifiable critique — active inference is a framework, not a theory |
| **Ramstead et al.** | 2023 | Friston concession: FEP is a mathematical framework, empirical bite requires specific models |
| **Bruineberg et al.** | 2022 | "The Emperor's New Markov Blankets" — Markov blankets are drawn by the modeler, not found |

## Philosophical Foundation

| Reference | Relevance |
|-----------|-----------|
| [**Bostrom's Simulation Argument**](https://www.simulation-argument.com/) (2003) | The theoretical basis for our Matrix meta-layer: what would it mean for simulated entities to discover their reality? |
| **"Growing Artificial Societies"** (Epstein & Axtell, 1996) | The book that established agent-based social simulation. Our project can be positioned as "Sugarscape extended with belief dynamics, LLM narration, and simulation-awareness mechanics" |

## Interactive Explorations

| Project | Relevance |
|---------|-----------|
| [**Parable of the Polygons**](https://ncase.me/polygons/) (Vi Hart & Nicky Case, 2014) | Interactive visualization of Schelling's segregation model — emergence from individual bias |
| [**The Evolution of Trust**](https://ncase.me/trust/) (Nicky Case, 2017) | Interactive game theory exploration of cooperation/defection dynamics |

## Academic References for Era Parameters

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

## Feature Comparison

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
