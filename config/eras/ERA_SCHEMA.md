# Era Configuration Schema

Eras are historically-researched configuration presets that tune all 11 simulation
subsystems to reflect a specific time period in human history. Like the Matrix in
the movie chose the late 20th century as its setting, users can choose any era to
shape how agents interact, think, grow, and organize.

## How Eras Work

An era file is a YAML override (same as scenarios) that deep-merges onto
`default.yaml`. The difference from gameplay scenarios:

- **Scenarios** (`config/scenarios/`) are gameplay-tuned (harsh_world, peaceful)
- **Eras** (`config/eras/`) are historically-grounded, with citations and rationale

Eras and scenarios can be combined: e.g., `--era medieval --scenario harsh_world`
applies the era first, then the scenario tweaks on top.

## Era File Structure

```yaml
# ── Metadata ──
name: "Short display name"
description: "One-line summary"
time_period: "~1200 CE"           # approximate date or range
region: "Western Europe"           # geographic focus
historical_context: |
  Multi-line description of the era's defining characteristics,
  what life was like, and why the parameter choices reflect reality.

# ── Simulation Overrides ──
# Only include parameters that DIFFER from default.yaml.
# Each section includes inline comments explaining the historical rationale.

population:
  initial_size: 30  # rationale here

# ... all 11 subsystems as needed ...

# ── Pre-Unlocked Technologies ──
# Which tech_breakthroughs are already discovered at tick 0.
# (Handled by engine: skips threshold check, grants bonuses immediately)
pre_unlocked_tech: []              # e.g., [agriculture, mining]

# ── Starting Belief Distribution ──
# Override the random initialization of agent beliefs.
# Each axis: mean and std for normal distribution.
starting_beliefs:
  individualism: { mean: 0.0, std: 0.2 }
  tradition:     { mean: 0.0, std: 0.2 }
  system_trust:  { mean: 0.0, std: 0.2 }
  spirituality:  { mean: 0.0, std: 0.2 }

# ── Era-Specific Flavor ──
# Optional: narrative hints for the LLM narrator
narrator_hints:
  setting: "Brief setting description for LLM context"
  vocabulary: []   # period-appropriate terms the narrator should use
  themes: []       # narrative themes to emphasize
```

## Design Principles

1. **Historical grounding over gameplay balance** — parameters should reflect
   reality even if it makes the simulation harder or easier.

2. **Cite your reasoning** — inline comments explain WHY a value was chosen,
   not just WHAT it is.

3. **Minimal overrides** — only override parameters that genuinely differ from
   the default. The default config represents a "neutral" baseline.

4. **Composable** — eras should work with scenario overlays. Don't hardcode
   assumptions that break when combined with harsh_world or peaceful.

5. **Narrator integration** — the `narrator_hints` section lets the LLM
   generate era-appropriate prose without changing the narrator code.
