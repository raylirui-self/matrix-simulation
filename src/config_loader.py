"""
YAML config loader with deep-merge and Pydantic-style validation.
Supports: default.yaml < scenario overrides < runtime overrides.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Optional

import yaml


def deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge overrides into base. Mutates base."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def find_config_dir() -> Path:
    """Locate config/ directory relative to project root."""
    # Try relative to this file first, then cwd
    candidates = [
        Path(__file__).resolve().parent.parent / "config",
        Path.cwd() / "config",
    ]
    for c in candidates:
        if (c / "default.yaml").exists():
            return c
    raise FileNotFoundError(
        "Cannot find config/default.yaml. Run from project root or set CONFIG_DIR env var."
    )


class SimConfig:
    """
    Simulation configuration loaded from YAML with attribute-style access.
    Supports nested access: cfg.environment.harshness, cfg.mate_selection.weights.competition
    """

    # Era-specific metadata (not part of simulation config, stored separately)
    era_metadata: dict = {}

    def __init__(self, data: dict):
        self._data = data
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, SimConfig(value))
            else:
                setattr(self, key, value)

    def __getitem__(self, key: str):
        return self._data[key]

    def __contains__(self, key: str):
        return key in self._data

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def to_dict(self) -> dict:
        """Recursively convert back to plain dict."""
        result = {}
        for key, value in self._data.items():
            if isinstance(value, dict):
                result[key] = SimConfig(value).to_dict()
            else:
                result[key] = value
        return result

    def override(self, overrides: dict) -> SimConfig:
        """Return a new SimConfig with overrides applied."""
        merged = deep_merge(copy.deepcopy(self._data), overrides)
        return SimConfig(merged)

    # Keys in era/scenario files that are metadata, not simulation config overrides
    _META_KEYS = {
        "name", "description", "time_period", "region", "historical_context",
        "pre_unlocked_tech", "starting_beliefs", "narrator_hints",
        "preview", "highlights",
    }

    @classmethod
    def load(cls, scenario: Optional[str] = None,
             era: Optional[str] = None,
             config_dir: Optional[Path] = None) -> SimConfig:
        """Load default config, optionally merging an era and/or scenario file.

        Priority: default.yaml < era.yaml < scenario.yaml < runtime overrides.
        """
        config_dir = config_dir or (
            Path(os.environ["CONFIG_DIR"]) if "CONFIG_DIR" in os.environ
            else find_config_dir()
        )

        with open(config_dir / "default.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        era_metadata = {}

        # Era overrides (applied first — historical baseline)
        if era:
            era_path = config_dir / "eras" / f"{era}.yaml"
            if not era_path.exists():
                available = [p.stem for p in (config_dir / "eras").glob("*.yaml")]
                raise FileNotFoundError(
                    f"Era '{era}' not found. Available: {available}"
                )
            with open(era_path, "r", encoding="utf-8") as f:
                era_data = yaml.safe_load(f) or {}
            # Extract era metadata before merging config overrides
            for key in cls._META_KEYS:
                if key in era_data:
                    era_metadata[key] = era_data.pop(key)
            deep_merge(data, era_data)

        # Scenario overrides (applied on top of era)
        if scenario:
            scenario_path = config_dir / "scenarios" / f"{scenario}.yaml"
            if not scenario_path.exists():
                available = [p.stem for p in (config_dir / "scenarios").glob("*.yaml")]
                raise FileNotFoundError(
                    f"Scenario '{scenario}' not found. Available: {available}"
                )
            with open(scenario_path, "r", encoding="utf-8") as f:
                overrides = yaml.safe_load(f) or {}
            # Remove non-config metadata keys before merging
            for mk in cls._META_KEYS:
                overrides.pop(mk, None)
            deep_merge(data, overrides)

        cfg = cls(data)
        cfg.era_metadata = era_metadata
        return cfg

    def list_scenarios(self, config_dir: Optional[Path] = None) -> list[dict]:
        """List available scenario files with descriptions and preview metadata."""
        config_dir = config_dir or find_config_dir()
        scenarios = []
        scenario_dir = config_dir / "scenarios"
        if scenario_dir.exists():
            for p in sorted(scenario_dir.glob("*.yaml")):
                with open(p, encoding="utf-8") as f:
                    content = yaml.safe_load(f) or {}
                scenarios.append({
                    "name": p.stem,
                    "description": content.get("description", "No description"),
                    "preview": content.get("preview", ""),
                    "highlights": content.get("highlights", []),
                })
        return scenarios

    def list_eras(self, config_dir: Optional[Path] = None) -> list[dict]:
        """List available era files with descriptions and metadata."""
        config_dir = config_dir or find_config_dir()
        eras = []
        era_dir = config_dir / "eras"
        if era_dir.exists():
            for p in sorted(era_dir.glob("*.yaml")):
                with open(p, encoding="utf-8") as f:
                    content = yaml.safe_load(f) or {}
                eras.append({
                    "name": p.stem,
                    "display_name": content.get("name", p.stem),
                    "description": content.get("description", "No description"),
                    "time_period": content.get("time_period", "Unknown"),
                    "region": content.get("region", "Unknown"),
                })
        return eras