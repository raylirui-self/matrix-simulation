# Project: Cognitive Matrix v2 (human-matrix-sim)

## What this is
Agent-based civilization simulator with emergent societies, factions, and a Matrix-themed meta-layer (awareness, sentinels, nested sims). Python backend orchestrates 11 systems; SvelteKit frontend ("The Nexus") + legacy Streamlit dashboard.

## Tech stack
- Python >=3.11, FastAPI, Uvicorn, WebSockets
- PyYAML, pandas, plotly, Streamlit (legacy dashboard)
- Ollama / HuggingFace Hub for LLM narration
- SvelteKit + TypeScript + Canvas 2D (gui/frontend)
- pytest + pytest-cov, ruff

## Commands
- Install: `pip install -e ".[dev]"`
- Run: `python main.py new && python main.py run --ticks 500` (API: `make api`, Frontend: `make frontend`)
- Test: `python -m pytest`
- Lint: `ruff check src/ gui/ tests/`  (auto-fix: `ruff check --fix`; format: `ruff format`)
- Type check: n/a (no mypy configured)

## Code style
- Use ruff for formatting and linting — must be clean before commit (CI enforces)
- Dataclasses for data models; plain functions for systems (no god-classes)
- New systems: module in `src/`, function called from `src/engine.py` tick loop, signature roughly `(agents, world, config) -> events`
- Never hardcode tunables — add to `config/default.yaml`; config hierarchy: default < era < scenario < CLI < runtime sliders
- All LLM calls go through `src/narrator.py` (never call Ollama/HF directly from other modules)

## Architecture
- `src/engine.py` orchestrates 11 systems: agents, matrix_layer, beliefs, agency, narrator, world, haven, programs, dreams, nested_sim, causal_graph
- `gui/backend/api/routes/` — FastAPI routes; `gui/frontend/src/routes/+page.svelte` — Nexus entry
- `config/` — yaml hierarchy (default/eras/scenarios); `tests/` — pytest; `scripts/` — batch/sweep tools
- Before any work: read `TODO.md` (roadmap) and relevant `README.md` sections; update both after

## Testing
- Run single tests with: `pytest tests/test_file.py::test_name -v`
- Always write a failing test before fixing a bug
- Prefer pytest with descriptive test names; keep unit tests off the network/LLM path

## Git
- Use conventional commits (feat:, fix:, refactor:, docs:, test:) — reference TODO phase/item
- Keep commits atomic — one logical change per commit
- Run `ruff check` + `pytest` locally before committing

## When compacting context
- Preserve the full list of modified files
- Preserve any failing test output
- Preserve the current task description and remaining steps

## Key File Map
| Purpose | File(s) |
|---------|---------|
| Tick orchestrator | `src/engine.py` |
| Agent data model | `src/agents.py` |
| Matrix awareness/sentinels/anomaly/Gnostic | `src/matrix_layer.py` |
| Factions & beliefs | `src/beliefs.py` |
| Movement, agency, free will gradient | `src/agency.py` |
| LLM narrator/thoughts/obituary | `src/narrator.py` |
| World grid, resources, artifacts | `src/world.py` |
| Haven (real world) | `src/haven.py` |
| Programs (Enforcer/Broker/Guardian/Locksmith) | `src/programs.py` |
| Simulation dreams & lucid dreaming | `src/dreams.py` |
| Nested simulations & World Engines | `src/nested_sim.py` |
| Procedural mythology & legendary figures | `src/mythology.py` |
| Communication & emergent language | `src/communication.py` |
| Batch research mode | `src/batch.py` |
| Causal event graphs | `src/causal_graph.py` |
| Persistence (SQLite) | `src/persistence.py` |
| Master config | `config/default.yaml` |
| Era presets | `config/eras/*.yaml` |
| Scenario presets | `config/scenarios/*.yaml` |
| API routes | `gui/backend/api/routes/` |
| WebSocket route | `gui/backend/api/routes/websocket.py` |
| God mode API | `gui/backend/api/routes/god_mode.py` |
| Frontend entry | `gui/frontend/src/routes/+page.svelte` |
| World canvas rendering | `gui/frontend/src/lib/canvas/WorldMap.svelte` |
| Frontend state store | `gui/frontend/src/lib/stores/simulation.ts` |
