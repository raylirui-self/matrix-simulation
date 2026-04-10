# Contributing to Cognitive Matrix

Thanks for your interest in contributing! This guide will help you get started.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+ (for frontend)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/raylirui-self/matrix-simulation.git
   cd matrix-simulation
   ```

2. Install Python dependencies (with dev tools):
   ```bash
   make dev
   # or manually: pip install -e ".[dev]"
   ```

3. Install frontend dependencies:
   ```bash
   cd gui/frontend && npm install
   ```

4. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

### Running the Project

| Command | Description |
|---------|-------------|
| `make run` | Run simulation (500 ticks) |
| `make api` | Start FastAPI backend (port 8000) |
| `make frontend` | Start SvelteKit dev server (port 5173) |
| `make dashboard` | Start Streamlit dashboard |
| `make test` | Run Python tests |

## How to Contribute

### Reporting Bugs

Open an issue with:
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS

### Suggesting Features

Open an issue describing the feature, its motivation, and how it fits the project.

### Submitting Changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Add or update tests if applicable
4. Ensure all checks pass:
   ```bash
   make test
   ruff check src/ gui/ tests/
   ```
5. Submit a pull request

### Pull Request Guidelines

- Keep PRs focused on a single change
- Write a clear description of what and why
- Reference related issues if applicable
- Ensure CI passes before requesting review

## Code Style

- Python: follow existing patterns, lint with [ruff](https://docs.astral.sh/ruff/)
- Frontend: TypeScript, follow existing Svelte conventions
- Keep commits atomic and write clear commit messages

## Project Structure

- `src/` — Core simulation engine
- `gui/backend/` — FastAPI REST API
- `gui/frontend/` — SvelteKit web UI
- `gui/dashboard/` — Streamlit dashboard
- `config/` — YAML configuration and era presets
- `tests/` — pytest test suite
- `scripts/` — Utility scripts (parameter sweep)

## Adding a New System

All simulation systems follow the same pattern:

1. Create a function in `src/your_system.py` with signature: `process_your_system(agents, tick, cfg, ...) -> dict`
2. The function receives agents/world/config, mutates agent state, and returns a stats dict.
3. Wire it into the tick loop in `src/engine.py` (see existing systems for ordering).
4. Add any config parameters to `config/default.yaml` under a new section.
5. Add the stats dict to `TickResult` in `src/engine.py` if needed.
6. Add tests in `tests/test_systems.py`.

## Adding a Config Parameter

1. Add the parameter to `config/default.yaml` under the appropriate section (e.g., `population`, `environment`).
2. Access it in code via `cfg.section.param` (e.g., `cfg.population.min_floor`).
3. Never hardcode tunable values — always read from config.
4. Override hierarchy: `default.yaml` < era YAML < scenario YAML < `--set` CLI flag < runtime sliders.

## Creating a Scenario

1. Create a YAML file in `config/scenarios/` (e.g., `my_scenario.yaml`).
2. Add a `description:` key at the top for `python main.py scenarios` listing.
3. Override only the parameters you want to change — everything else inherits from `default.yaml`.
4. Run with: `python main.py --scenario my_scenario new && python main.py run`

## Adding a Dashboard Tab

1. Create a Svelte component in `gui/frontend/src/lib/panels/` (e.g., `MyPanel.svelte`).
2. Import and add it to the tab list in `gui/frontend/src/routes/+page.svelte`.
3. Fetch data from the FastAPI backend via the existing API client or add a new route in `gui/backend/api/routes/`.
4. Follow existing panel patterns for layout, reactivity, and WebSocket subscriptions.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
