"""
Unit tests for [src/portrait.py](../src/portrait.py).

Closes the coverage gap called out in L-7 (prior L-1) — portrait.py
was previously at 0% coverage because every code path reached out
to HuggingFace or OllamaDiffuser, and the integration tests
(correctly) skipped all of it.

Strategy: mock the narrator, image providers, and filesystem so
the orchestration logic itself is exercised without any network
or disk writes outside `tmp_path`.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agents import Agent, Bond, Traits
from src.portrait import (
    HuggingFaceImageProvider,
    OllamaDiffuserProvider,
    PortraitGenerator,
    generate_portrait_prompt_llm,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def protagonist():
    """A richly-populated agent so the prompt builder has data to chew on."""
    traits = Traits(resilience=0.8, curiosity=0.9, charisma=0.7,
                    aggression=0.2, sociability=0.6)
    a = Agent(
        id=42, sex="F", age=35, phase="adult", health=0.85,
        traits=traits, generation=4, wealth=12.5,
        is_anomaly=True, redpilled=True, awareness=0.7,
        protagonist_name="Tria",
    )
    a.skills = {"logic": 0.8, "creativity": 0.5, "social": 0.6,
                "survival": 0.3, "tech": 0.2}
    a.bonds = [Bond(target_id=7, bond_type="mate", strength=0.8, formed_at=10)]
    a.child_ids = [101, 102]
    a.memory = [
        {"tick": 30, "event": "Witnessed the sentinel purge"},
        {"tick": 31, "event": "Joined the resistance"},
    ]
    a.emotions = {"happiness": 0.3, "fear": 0.6, "anger": 0.2, "grief": 0.1, "hope": 0.4}
    a.trauma = 0.4
    return a


@pytest.fixture
def connected_narrator():
    """Narrator that pretends to be a live LLM producing a canned prompt."""
    n = MagicMock()
    n.enabled = True
    n._ensure_connected.return_value = True
    n.active_provider.generate.return_value = "  A haunted portrait, green rain.  "
    return n


@pytest.fixture(autouse=True)
def isolate_portrait_dir(tmp_path, monkeypatch):
    """Point PORTRAITS_DIR at tmp_path so tests never touch output/portraits/."""
    from src import portrait
    monkeypatch.setattr(portrait, "PORTRAITS_DIR", tmp_path / "portraits")


# ─── generate_portrait_prompt_llm ────────────────────────────────────────────

def test_prompt_llm_returns_none_when_narrator_disabled(protagonist):
    narrator = MagicMock()
    narrator.enabled = False
    assert generate_portrait_prompt_llm(protagonist, narrator) is None


def test_prompt_llm_returns_none_when_narrator_absent(protagonist):
    assert generate_portrait_prompt_llm(protagonist, None) is None


def test_prompt_llm_returns_none_when_not_connected(protagonist):
    narrator = MagicMock()
    narrator.enabled = True
    narrator._ensure_connected.return_value = False
    assert generate_portrait_prompt_llm(protagonist, narrator) is None


def test_prompt_llm_strips_whitespace_on_success(protagonist, connected_narrator):
    result = generate_portrait_prompt_llm(protagonist, connected_narrator)
    assert result == "A haunted portrait, green rain."


def test_prompt_llm_passes_agent_context_to_provider(protagonist, connected_narrator):
    generate_portrait_prompt_llm(protagonist, connected_narrator)
    # The user-prompt arg (position 1) should mention THE ANOMALY badge
    args, kwargs = connected_narrator.active_provider.generate.call_args
    _system, user = args[0], args[1]
    assert "THE ANOMALY" in user
    assert "REDPILLED" in user
    assert protagonist.protagonist_name in user


def test_prompt_llm_swallows_provider_exceptions(protagonist, connected_narrator):
    connected_narrator.active_provider.generate.side_effect = RuntimeError("boom")
    # Should return None rather than bubble the exception
    assert generate_portrait_prompt_llm(protagonist, connected_narrator) is None


# ─── PortraitGenerator orchestrator ──────────────────────────────────────────

def _fake_provider(*, connects: bool = True, generates: bool = True, name: str = "fake"):
    p = MagicMock()
    p.connect.return_value = connects
    p.generate.return_value = generates
    p.name = name
    return p


def test_portrait_generator_no_providers_connect_returns_none(protagonist, connected_narrator):
    gen = PortraitGenerator()
    gen.providers = [
        _fake_provider(connects=False),
        _fake_provider(connects=False),
    ]
    result = gen.generate_portrait(protagonist, connected_narrator, run_id="r1", tick=5)
    assert result is None


def test_portrait_generator_first_provider_success_path(
    protagonist, connected_narrator, tmp_path
):
    gen = PortraitGenerator()
    first = _fake_provider(connects=True, generates=True, name="first")
    second = _fake_provider(connects=True, generates=True, name="second")
    gen.providers = [first, second]

    result = gen.generate_portrait(protagonist, connected_narrator, run_id="r1", tick=5)

    assert result is not None
    assert "agent_42_t5.png" in result
    # First provider did the work; second was not called for generate
    first.generate.assert_called_once()
    second.generate.assert_not_called()


def test_portrait_generator_falls_back_when_first_provider_generate_fails(
    protagonist, connected_narrator
):
    gen = PortraitGenerator()
    first = _fake_provider(connects=True, generates=False, name="first")
    second = _fake_provider(connects=True, generates=True, name="second")
    gen.providers = [first, second]

    result = gen.generate_portrait(protagonist, connected_narrator, run_id="r1", tick=5)

    assert result is not None
    first.generate.assert_called_once()
    second.generate.assert_called_once()


def test_portrait_generator_provider_name_reports_none_until_connected():
    gen = PortraitGenerator()
    assert gen.provider_name == "none"


def test_portrait_generator_ensure_connected_caches_active_provider():
    gen = PortraitGenerator()
    p = _fake_provider(connects=True, name="pick-me")
    gen.providers = [p]
    assert gen._ensure_connected() is True
    assert gen.active_provider is p
    # Second call should short-circuit — no additional connect() call
    connect_calls_before = p.connect.call_count
    gen._ensure_connected()
    assert p.connect.call_count == connect_calls_before


# ─── Era landscape ───────────────────────────────────────────────────────────

def test_generate_era_landscape_uses_template_fallback_without_narrator(monkeypatch, tmp_path):
    # Redirect landscape output path into tmp (generate_era_landscape
    # uses a relative Path that resolves against the cwd).
    monkeypatch.chdir(tmp_path)

    gen = PortraitGenerator()
    provider = _fake_provider(connects=True, generates=True)
    gen.providers = [provider]

    result = gen.generate_era_landscape("genesis", "The first stirrings", narrator=None)

    assert result is not None
    # The template prompt must have been used — verify via the call arg
    call_args = provider.generate.call_args
    prompt_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("prompt")
    assert "void" in prompt_arg.lower() or "green" in prompt_arg.lower()


def test_generate_era_landscape_reuses_existing_file(monkeypatch, tmp_path):
    """If a landscape file already exists for the era, skip regeneration."""
    monkeypatch.chdir(tmp_path)
    era_dir = tmp_path / "output" / "era_landscapes"
    era_dir.mkdir(parents=True)
    existing = era_dir / "genesis.png"
    existing.write_bytes(b"fake png")

    gen = PortraitGenerator()
    provider = _fake_provider()
    gen.providers = [provider]

    result = gen.generate_era_landscape("genesis", "The first stirrings", narrator=None)

    assert result is not None
    # No generate call because the file was cached
    provider.generate.assert_not_called()


# ─── HuggingFaceImageProvider ────────────────────────────────────────────────

def test_hf_provider_connect_without_token_fails(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    p = HuggingFaceImageProvider(token=None)
    assert p.connect() is False


def test_hf_provider_name_format():
    p = HuggingFaceImageProvider(model="black-forest-labs/FLUX.1-schnell")
    assert p.name == "hf/FLUX.1-schnell"


# ─── OllamaDiffuserProvider ──────────────────────────────────────────────────

def test_ollama_diffuser_name_format():
    p = OllamaDiffuserProvider(model="flux.1-schnell")
    assert p.name == "ollamadiffuser/flux.1-schnell"


def test_ollama_diffuser_connect_handles_missing_import(monkeypatch):
    """If ollamadiffuser is not installed, connect() must return False cleanly."""
    import sys

    # Block the import path
    monkeypatch.setitem(sys.modules, "ollamadiffuser", None)
    p = OllamaDiffuserProvider()
    assert p.connect() is False
