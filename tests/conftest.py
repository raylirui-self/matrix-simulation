"""Shared test fixtures for Cognitive Matrix tests."""
import random

import pytest

from src.config_loader import SimConfig
from src.engine import SimulationEngine, RunState


@pytest.fixture(autouse=True)
def fixed_seed():
    """Fix random seed for reproducible tests."""
    random.seed(42)
    yield


@pytest.fixture
def cfg():
    """Load default simulation config."""
    return SimConfig.load()


@pytest.fixture
def engine(cfg):
    """Create and initialize a simulation engine."""
    eng = SimulationEngine(cfg, state=RunState(run_id="test"))
    eng.initialize()
    return eng
