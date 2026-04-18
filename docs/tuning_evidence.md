# Tuning Evidence & Design Decisions

[← Back to README](../README.md) | [References](references.md)

This document maps research findings from four deep-research reports (opinion dynamics, language emergence, cultural evolution, consciousness theories) to specific config values and code structures in Cognitive Matrix. It is a **decision document**: nothing here is automatically applied to the code. Every proposed change has a tradeoff that the maintainer reviews.

Each entry cites a reference (see [references.md](references.md) for full citations) and flags confidence: **Strong** = multiple independent empirical + theoretical lines agree; **Medium** = one well-supported result; **Weak** = derived from structural reasoning where literature is thin.

---

## Framework-level design decisions

These are architectural calls, not numeric tunings. They shape how the numeric knobs are interpreted.

### 1. Keep Californian, not Paris, for cultural transmission — but document the choice

The literature splits between the **Californian school** (Boyd, Richerson, Henrich — faithful imitation + selection among variants) and the **Paris school** (Sperber, Claidière — convergent transformation toward cognitive attractors, no faithful copying required). Acerbi et al. (2023) show stability can emerge from attraction alone, without copying.

[src/knowledge.py](../src/knowledge.py) currently models Californian-style teaching (parents teach top skills, cultural memory floors accumulate from faithful transmission). **Recommend keeping this** — it's more tractable for discrete skill values and matches the "ratchet effect" narrative this simulator aims for. But flag it explicitly in the docstring so future contributors understand it's a choice, not a default.

**Confidence:** Strong (two well-established frameworks; current code cleanly sits in one).

### 2. Preserve 5 phases but document the weak boundary

Consciousness research (prompt #4) argues the 5-phase ladder (bicameral → subjective → egoic → reflective → recursive) has one genuinely weak joint: **subjective → egoic**. MPS + transparent self-model (subjective) already implies implicit HOT-like structure (egoic), so the boundary is continuous, not discrete. The other three transitions (PSCA→subjective, egoic→reflective via HOT depth 2, reflective→recursive via fixed-point) are theoretically defensible.

**Recommend** keeping 5 phases for narrative coherence — but add a docstring in [src/matrix_layer.py](../src/matrix_layer.py) noting the subjective/egoic boundary is primarily aesthetic, not a joint in nature. Collapsing to 4 phases would be theoretically cleaner but narratively costly.

**Confidence:** Strong (research flagged this explicitly).

### 3. Keep awareness as a scalar at the API boundary; consider a hidden vector internally

Research argues collapsing GWT + IIT + HOT + active inference + strange loops into one `awareness ∈ [0,1]` scalar is philosophically suspect — these theories target different explananda. The recommended architecture: maintain a 7-channel vector internally, expose scalar via weighted geometric mean at the UI boundary.

**Recommend:** not doing this full refactor now. The existing scalar works for game mechanics; adding 7 channels is a large lift with no gameplay payoff until the frontend exposes diagnostics. **But** — when adding a new consciousness-phase criterion, prefer *structural tests* (meta-representation depth, fixed-point convergence) over raw awareness thresholds. Add them as *gates* on top of the scalar.

**Confidence:** Medium (architecturally correct but costly; defer unless frontend panels can exploit it).

### 4. Löb's theorem as principled ceiling on self-understanding

An agent that proves its own soundness is inconsistent (Löb 1955). This gives a mathematical basis for a game-design choice you probably already have: "fully understanding the Matrix" should be asymptotically unreachable, never fully attained. The Anomaly's journey should always have one more layer.

**Recommend:** add a comment in [src/matrix_layer.py](../src/matrix_layer.py) near the Pleroma-glimpse / recursive-phase code explaining that the awareness ceiling is Löbian, not arbitrary. Mechanically nothing changes; conceptually this upgrades the ceiling from game convention to principled constraint.

**Confidence:** Strong (formal theorem; interpretation to agents is structural analogy, so call it out as such).

### 5. Effective population, not census population, gates cultural-memory decay

Deffner, Kandler & Fogarty (2022) show that for cultural complexity, **effective population size** matters more than raw count. Transmission mode (one-to-many vs mesh), network structure, and connectedness determine effective N. A tribe of 100 with strict one-teacher-many-students transmission may have effective N much lower than a tribe of 50 with mesh.

Current [src/knowledge.py](../src/knowledge.py) cultural-memory decay keys off raw population. **This is empirically wrong** — but fixing it properly requires new infrastructure (measuring teaching-network degree distribution per tick). **Recommend:** add a TODO in the cultural-memory decay code pointing to this evidence, and introduce an `effective_population_multiplier` config knob defaulting to 1.0 that scenarios can override. Full measurement can come later.

**Confidence:** Strong theoretically; **Weak** on the specific correction factor (field hasn't calibrated it).

---

## Parameter tuning table

Each row: current value → recommended value → evidence → tradeoff.

### System 7 — Beliefs & Factions

| Config line | Current | Recommended | Evidence | Tradeoff |
|---|---|---|---|---|
| `beliefs.faction_formation_similarity` | **0.65** | **0.75–0.80** | Duggins 2017 (ANES) + Deffuant 2000 scaling. 4D belief space needs ~1.5–2.5× the 1-D threshold (ε_4D ≈ 0.30–0.40 distance → ~0.75–0.80 similarity). Current value treats 4D like 1-D. | **Gain:** fewer, larger, more ideologically coherent factions. **Lose:** early-game turbulence; scenarios expecting quick fragmentation (`prophet_era`, `dark_ages`) may need per-scenario overrides. **Confidence:** Strong |
| `beliefs.schism_variance_threshold` | **0.5** | **0.15–0.20** | Jager & Amblard 2005 + internal consistency: if per-axis σ ≈ ε_4D/2 ≈ 0.17, total 4D variance ≈ 0.12. Threshold slightly above (0.15–0.20) adds hysteresis. Current value is ~3× too high. | **Gain:** schisms actually fire during playtesting (likely rare now). **Lose:** possible schism storms if mutation rate isn't tuned in parallel. **Confidence:** Medium (literature on schism thresholds is thin) |
| `beliefs.mutation_rate` | **0.15** (per-hop info degradation) | Keep; add new `beliefs.per_tick_drift_sigma` | Not the same mechanism as Gleeson 2016's 0.02–0.10 meme innovation. Current knob is telephone-game mutation, which is fine. Separately, the Klemm r_c ~ 1/(N log N) law demands a per-tick per-axis belief drift, which is a *new* mechanism. | **Gain:** sustained diversity at scale (prevents monoculture collapse at N > 1000). **Lose:** new code path in `src/beliefs.py` to add Gaussian drift per tick; need to verify it doesn't destabilize existing tuning. **Confidence:** Strong |
| Prophet conversion radius | single spatial check | Dual radius: belief-space **1.5–2.0× ε_4D (0.50–0.70)** + spatial **2–3× normal neighborhood** | Xie 2011 (10%) + Centola 2018 (25%) tipping thresholds. Prophets must reach across the BC threshold (otherwise normal BC handles it), and must reach enough agents to cross Centola's local 25%. | **Gain:** prophets work as designed — flip local regions, rarely flip global civilization without reinforcement. **Lose:** new parameter to expose in config + dashboard. **Confidence:** Medium |

### System 11 — Communication / Language

| Config line | Current | Recommended | Evidence | Tradeoff |
|---|---|---|---|---|
| `communication.min_encoding_complexity` | **0.2** | Keep **0.2** for M<100; scale to 0.25 (M=100–1000) or 0.30 (M>1000) | Shannon source-coding theorem: ℓ_min = log₂ M / log₂ \|Σ\|. Kirby 2008 empirical compression ratio 0.15–0.22 validates 0.2 for their 27-meaning space. | **Gain:** floor tracks meaning-space size instead of being hard-coded. **Lose:** small code addition to compute effective M. **Confidence:** Strong |
| `communication.compression_rate` | **0.05** (flat) | **0.10 for frequent concepts, 0.02 for rare** (frequency-weighted) | Kirby 2008 (~50% error reduction over 10 generations → k ≈ 0.069); Raviv 2019 (k ≈ 0.09); Kirby-Tamariz 2015. Pagel 2007: word frequency predicts 50% of rate variance. | **Gain:** matches empirical Zipfian compression dynamics — frequent words compress faster, rare ones preserved longer. **Lose:** need per-concept usage counter; more memory per concept. **Confidence:** Strong |
| `communication.dialect_drift_rate` | **0.01/tick** (single exponential) | Two-phase: **N^1.5-scaled internal consensus** then **λ ≈ 0.005/generation lexical drift** | Baronchelli 2006 scaling law for Phase 1; Swadesh/Lees retention rate r ≈ 0.8 per millennium for Phase 2. Current single-exponential misses the fast→slow transition. | **Gain:** dialect formation has realistic fast-then-slow dynamics. **Lose:** two-phase state machine per faction pair is a structural change in `src/communication.py`. **Confidence:** Medium |

### System 3 — Knowledge & Cultural Memory

Cultural-evolution report (#3) is more qualitative than numeric. Most design calls are structural (see Framework Decision 5); few direct parameter changes derive.

| Config line | Current | Recommended | Evidence | Tradeoff |
|---|---|---|---|---|
| `knowledge.cultural_memory.decay_rate` | **0.001** | Keep; guard behind effective-population check (see Framework 5) | Henrich 2004 "Tasmanian" threshold is real in lab (Derex 2013) but contested in ethnography. Decay should only fire below effective-N threshold, not as a constant drip. | **Gain:** dark ages tied to genuine demographic collapse, not time. **Lose:** requires measuring effective-N per tick. **Confidence:** Medium |
| `knowledge.parent_teaching.transfer_rate` | **0.1** | Keep (no literature-derived challenge) | Boyd & Richerson's prestige/conformist/payoff biases are structural categories; literature hasn't calibrated a transfer rate for dyadic parent-child teaching. Current value is empirically ungrounded but not empirically contradicted. | **Gain:** none. **Lose:** none. **Confidence:** N/A (literature silent) |
| New: `knowledge.conformist_bias_strength` | absent | Add as new knob, default 0 (off) | Boyd & Richerson 1985: conformist bias is a core transmission mode. Currently not modeled. Bond & Smith 1996 shows it's culturally variable, so scenarios/eras could raise it for collectivist cultures. | **Gain:** richer cultural transmission model; era presets can differentiate collectivist vs individualist societies at the transmission level. **Lose:** new mechanism in `src/knowledge.py`; scope risk. **Confidence:** Strong theoretically; **defer** to avoid scope creep |

### System 9 — Matrix / Consciousness

| Area | Current | Recommended | Evidence | Tradeoff |
|---|---|---|---|---|
| Phase transitions | Awareness threshold crossings | Keep 5 phases, but add **docstring flagging subjective→egoic as weak boundary** | Consciousness report §8 mapping table — three boundaries strong, one (subj→egoic) is narrative | **Gain:** honesty in code; future contributors understand design tradeoff. **Lose:** none. **Confidence:** Strong |
| Recursive phase criterion | Awareness ≥ 0.9 | Add **fixed-point structural check** as secondary gate: agent's self-model converges under self-modeling operator | Hofstadter *I Am a Strange Loop*; Premakumar 2024 neural-quine result. Currently the recursive phase is a scalar cutoff; research wants structural criterion | **Gain:** recursive phase becomes structurally distinct, not just quantitatively further. **Lose:** need to define what "self-model convergence" means for agents that don't have explicit self-models yet. Significant new code. **Confidence:** Medium (theoretically clean; implementation-expensive) |
| Free-will gradient | Custom computation | Explicit formula: **φ_FW = α₁·log(γ) + α₂·log(T) − α₃·H[q(π̃)] + α₄·(−H[q(s_self)])** | Parr, Pezzulo & Friston 2022 active-inference; four components (decisiveness, counterfactual depth, non-randomness, self-model sharpness) | **Gain:** principled 4-term formula replaces heuristic. **Lose:** need γ (policy precision), T (counterfactual horizon), policy entropy, self-model entropy — not all currently computed per agent. Substantial refactor. **Confidence:** Strong for formula; **Weak** for feasibility of measuring all four in current code |
| Bicameral phase | Awareness below threshold + lore flavor (Jaynes) | **PSCA regime** — 6 computable conditions, transition when ≥4 reverse | Consciousness report §5.2 — source-monitoring + HOT depth < 2 + M-ratio at chance + low narrative coherence + command-channel dominance | **Gain:** bicameral phase becomes structurally grounded instead of narrative-only. **Lose:** 6 new per-agent scalars to compute. **Confidence:** High theoretically; **Medium** on feasibility — some conditions (M-ratio, narrative chain length) need infrastructure that doesn't exist |

---

## What the simulator can contribute back to the literature

Three places where Cognitive Matrix could generate citable research output, not just consume it:

1. **Schism thresholds in 4D belief space.** Research report #1 flagged this as a literature gap. Sweep `schism_variance_threshold` × population size × network topology, log faction lifecycle statistics, compare to Jager-Amblard predictions. Novel contribution because it combines BC + spatial + 4D, which the literature has not.

2. **Long-term cultural-memory dynamics on simulated 10⁴-tick civilizations.** Henrich's Tasmanian effect is lab-validated at short timescales. Cognitive Matrix runs civilization-scale time. Record dark-age depth × population-bottleneck size × cultural-reconnection rate. Potentially contributes to Deffner 2022 effective-N research.

3. **Consciousness-phase transition dynamics under system-wide perturbation.** Drop a Sentinel swarm (reduce policy horizon T), plague (kill high-HOT-depth agents), cycle reset (zero narrative coherence). Does the population regress through phases coherently or erratically? Testable predictions from the 7-channel vector framework.

Each of these is a *side effect* of normal simulation runs, not a dedicated research mode — meaning the infrastructure is already there, only analysis scripts are needed.

---

## Proposed execution order

If changes are accepted, suggested order (low-risk first):

1. **Documentation-only** (framework decisions 1, 2, 4): add docstrings flagging design choices. Zero gameplay impact. Days of work: 0.5.
2. **Parameter nudges** (System 7 rows 1–2, System 11 row 1): tighten faction similarity, lower schism threshold, document compression floor scaling. Gameplay impact: noticeable but low-risk. Days: 1–2 with playtesting.
3. **New parameters with default=off** (conformist bias, prophet dual-radius, per-tick belief drift): adds infrastructure, opt-in from scenarios. Days: 3–5.
4. **Structural changes** (two-phase dialect drift, effective-population gating for cultural memory, frequency-weighted compression): real refactoring. Days: 5–10.
5. **Deep consciousness refactor** (PSCA regime, fixed-point recursive criterion, 4-term free-will gradient): large scope. Weeks. Defer unless high priority.
