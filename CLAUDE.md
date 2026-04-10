# Cognitive Matrix v2 — Claude Instructions

## Before Any Work
1. Read `TODO.md` to understand the roadmap and find which phase/item your task belongs to
2. Read relevant sections of `README.md` for architecture context and design decisions
3. Check `config/default.yaml` before hardcoding any values

## After Completing Work
1. Update `TODO.md`: check off completed items, add new items discovered during implementation
2. Update `README.md` if you changed: system behavior, config parameters, API endpoints, GUI features, project structure, or the roadmap
3. When committing, reference the TODO phase/item in the commit message (e.g., "Phase 0: fix population floor")

## Architecture Rules
- **11 systems are orchestrated by `src/engine.py`** — each system is a separate module in `src/`. New systems must follow the same pattern: a function called from `engine.py`'s tick loop that takes agents/world/config and returns events
- **Config hierarchy**: `config/default.yaml` < `config/eras/*.yaml` < `config/scenarios/*.yaml` < CLI flags < runtime sliders. Never hardcode tunable values — add them to `default.yaml`
- **LLM integration**: All LLM calls go through `src/narrator.py` which handles Ollama/HuggingFace/fallback. Never call LLM providers directly from other modules
- **Frontend (The Nexus)**: SvelteKit at `gui/frontend/src/`. Backend API at `gui/backend/api/`. Communication via REST + WebSocket
- **Legacy dashboard**: Streamlit at `gui/dashboard/`. Still maintained but secondary to The Nexus

## Code Style
- Python backend: follow existing patterns in `src/`. Use dataclasses for data, functions for systems
- Frontend: Svelte components, TypeScript, Canvas 2D rendering
- Tests: pytest in `tests/`. Run with `pytest` from project root
- Linting: ruff

## Key File Map
| Purpose | File(s) |
|---------|---------|
| Tick orchestrator | `src/engine.py` |
| Agent data model | `src/agents.py` |
| Matrix awareness/sentinels/anomaly | `src/matrix_layer.py` |
| Factions & beliefs | `src/beliefs.py` |
| Movement & spatial logic | `src/agency.py` |
| LLM narrator/thoughts | `src/narrator.py` |
| World grid & resources | `src/world.py` |
| Haven (real world) | `src/haven.py` |
| Programs (Enforcer/Broker/Guardian/Locksmith) | `src/programs.py` |
| Master config | `config/default.yaml` |
| Era presets | `config/eras/*.yaml` |
| API routes | `gui/backend/api/routes/` |
| Frontend entry | `gui/frontend/src/routes/+page.svelte` |
| God mode API | `gui/backend/api/routes/god_mode.py` |
| Persistence | `src/persistence.py` |

## What NOT to Do
- Don't add generic "improvements" beyond what was asked — this is a themed Matrix project, not a generic sim
- Don't create new files when editing existing ones would work
- Don't skip the TODO.md/README.md update step
- Don't add dependencies without checking if existing stack already covers the need
