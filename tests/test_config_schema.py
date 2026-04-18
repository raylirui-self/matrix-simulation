"""
Config schema validation tests.

Pins finding M-7 in [docs/code_review.md](../docs/code_review.md):
era and scenario YAML overrides currently merge into default.yaml
without any check that the override keys exist. A typo produces
a silent no-op.

Each test walks every era + scenario file and asserts every key
path exists in default.yaml. Run this in CI so new scenarios
fail-fast on typos instead of drifting into the wild.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.config_loader import SimConfig

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _flatten_paths(data: dict, prefix: str = "") -> set[str]:
    """Return the set of dotted key paths in a nested dict.

    `{"a": {"b": 1, "c": {"d": 2}}}` → `{"a.b", "a.c.d"}`.
    Only leaves are included; intermediate dicts are not.
    """
    paths: set[str] = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and value:
            paths |= _flatten_paths(value, path)
        else:
            paths.add(path)
    return paths


def _strip_meta(data: dict) -> dict:
    """Drop metadata keys that aren't part of simulation config."""
    return {k: v for k, v in data.items() if k not in SimConfig._META_KEYS}


@pytest.fixture(scope="module")
def default_paths() -> set[str]:
    return _flatten_paths(_load_yaml(CONFIG_DIR / "default.yaml"))


def _override_files(subdir: str) -> list[Path]:
    return sorted((CONFIG_DIR / subdir).glob("*.yaml"))


@pytest.mark.parametrize(
    "override_path",
    _override_files("eras") + _override_files("scenarios"),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_override_keys_exist_in_default(override_path: Path, default_paths: set[str]):
    """Every leaf key in an era/scenario file must exist in default.yaml."""
    override = _strip_meta(_load_yaml(override_path))
    override_paths = _flatten_paths(override)

    unknown = override_paths - default_paths
    assert not unknown, (
        f"{override_path.relative_to(CONFIG_DIR.parent)} contains keys that do not "
        f"exist in default.yaml: {sorted(unknown)}. A typo here silently adds a new "
        f"key that no module reads."
    )


def test_default_yaml_is_valid_yaml():
    """Sanity: default.yaml parses and the loader accepts it."""
    cfg = SimConfig.load()
    assert cfg.population.initial_size > 0
    assert cfg.population.max_size >= cfg.population.min_floor


@pytest.mark.parametrize("era_name", [p.stem for p in _override_files("eras")])
def test_every_era_loads(era_name: str):
    """Every era file must load cleanly on top of default.yaml."""
    cfg = SimConfig.load(era=era_name)
    assert cfg is not None


@pytest.mark.parametrize("scenario_name", [p.stem for p in _override_files("scenarios")])
def test_every_scenario_loads(scenario_name: str):
    """Every scenario file must load cleanly on top of default.yaml."""
    cfg = SimConfig.load(scenario=scenario_name)
    assert cfg is not None
