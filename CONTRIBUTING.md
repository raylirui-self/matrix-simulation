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

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
