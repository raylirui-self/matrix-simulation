"""End-to-end API + WebSocket smoke test.

Exercises every button-equivalent endpoint the Nexus frontend talks to:

    Create sim   → POST /api/sim
    Inspect      → GET  /api/sim/{id}
    Advance      → POST /api/sim/{id}/tick
    State dump   → GET  /api/sim/{id}/state
    History      → GET  /api/sim/{id}/history
    Config slide → PUT  /api/sim/{id}/config (whitelisted + rejected)
    World grid   → GET  /api/sim/{id}/world
    God mode     → POST /api/sim/{id}/god (gated behind env flag + auth)
    Media        → POST /api/sim/{id}/media/narrate (rate-limited)
    WebSocket    → /ws/sim/{id} (tick, auto/stop, state, malformed JSON)
    Health       → GET  /api/health

Uses starlette.testclient so no uvicorn process is required. Each test is
self-contained and does not assume prior state.
"""
from __future__ import annotations

import importlib
import json

import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def app_with_god_mode(tmp_path, monkeypatch):
    """Build a fresh FastAPI app with god-mode enabled and an admin token.

    Rebuilds gui.backend.api.main so the GOD_MODE_ENABLED env flag is read
    at import time. Uses a per-test SQLite DB to avoid cross-test pollution.
    """
    monkeypatch.setenv("GOD_MODE_ENABLED", "1")
    monkeypatch.setenv("ADMIN_TOKEN", "test-token")
    monkeypatch.setenv("MEDIA_AUTH_REQUIRED", "0")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

    # Reinit the existing manager in place — re-binding state.manager would
    # orphan route modules that imported `from gui.backend.api.state import manager`
    # at load time.
    import gui.backend.api.state as state_module
    state_module.manager.__init__(db_path=str(tmp_path / "sim.db"))

    # Re-import the main module so the god-mode router is mounted with env=1.
    import gui.backend.api.main as main_module
    importlib.reload(main_module)

    client = TestClient(main_module.app)
    yield client


@pytest.fixture()
def app_no_god_mode(tmp_path, monkeypatch):
    """Build an app WITHOUT god mode enabled — verifies the gate works."""
    monkeypatch.delenv("GOD_MODE_ENABLED", raising=False)
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)

    import gui.backend.api.state as state_module
    state_module.manager.__init__(db_path=str(tmp_path / "sim.db"))

    import gui.backend.api.main as main_module
    importlib.reload(main_module)

    return TestClient(main_module.app)


# ──────────────────────────────────────────────────────────────────────────
# Health + create flow
# ──────────────────────────────────────────────────────────────────────────

def test_health_endpoint(app_with_god_mode):
    r = app_with_god_mode.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_fetch_simulation(app_with_god_mode):
    r = app_with_god_mode.post("/api/sim", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "run_id" in body
    assert body["tick"] == 0
    assert body["alive_count"] > 0

    run_id = body["run_id"]
    r2 = app_with_god_mode.get(f"/api/sim/{run_id}")
    assert r2.status_code == 200
    assert r2.json()["run_id"] == run_id


# ──────────────────────────────────────────────────────────────────────────
# Tick advancement (the primary "play" button)
# ──────────────────────────────────────────────────────────────────────────

def test_advance_ticks_and_history(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]

    r = app_with_god_mode.post(f"/api/sim/{run_id}/tick", json={"count": 10})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ticks_run"] == 10
    assert body["tick"] == 10

    # History endpoint should now have entries
    r = app_with_god_mode.get(f"/api/sim/{run_id}/history")
    assert r.status_code == 200
    hist = r.json()
    assert hist["total"] >= 10
    assert len(hist["history"]) >= 10


def test_state_endpoint_returns_full_snapshot(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    app_with_god_mode.post(f"/api/sim/{run_id}/tick", json={"count": 5})

    r = app_with_god_mode.get(f"/api/sim/{run_id}/state")
    assert r.status_code == 200
    body = r.json()
    for key in ("tick", "agents", "world", "factions", "wars", "matrix", "summary"):
        assert key in body
    # Agent summary must include fields used by the frontend panels
    if body["agents"]:
        sample = body["agents"][0]
        for key in ("id", "health", "emotion", "awareness", "faction_id", "trauma"):
            assert key in sample


# ──────────────────────────────────────────────────────────────────────────
# Config sliders — whitelist enforcement (M-2)
# ──────────────────────────────────────────────────────────────────────────

def test_config_slider_allowed_sections(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]

    # narrator + emotions are in the whitelist
    r = app_with_god_mode.put(
        f"/api/sim/{run_id}/config",
        json={"narrator": {"narration_interval": 50}, "emotions": {"decay_rate": 0.2}},
    )
    assert r.status_code == 200, r.text
    assert "narrator" in r.json()["updated_sections"]


def test_config_slider_rejects_non_whitelisted(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]

    # population is intentionally NOT in the whitelist — would desync engine state
    r = app_with_god_mode.put(
        f"/api/sim/{run_id}/config",
        json={"population": {"max_size": 999}},
    )
    assert r.status_code == 400
    assert "population" in r.json()["detail"]


# ──────────────────────────────────────────────────────────────────────────
# God mode gating (C-1) and spawn cap (M-3)
# ──────────────────────────────────────────────────────────────────────────

def test_god_mode_disabled_by_default(app_no_god_mode):
    # With GOD_MODE_ENABLED unset, the router is not mounted at all.
    run_id = app_no_god_mode.post("/api/sim", json={}).json()["run_id"]
    r = app_no_god_mode.post(f"/api/sim/{run_id}/god", json={"action": "spawn"})
    # FastAPI returns 404 Not Found for an unmounted route
    assert r.status_code == 404


def test_god_mode_requires_admin_token(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    # Missing token
    r = app_with_god_mode.post(f"/api/sim/{run_id}/god", json={"action": "spawn"})
    assert r.status_code == 401


def test_god_mode_spawn_with_valid_token(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    r = app_with_god_mode.post(
        f"/api/sim/{run_id}/god",
        json={"action": "spawn"},
        headers={"X-Admin-Token": "test-token"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"
    assert "agent_id" in r.json()


def test_god_mode_spawn_n_clamped_below_cap(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    r = app_with_god_mode.post(
        f"/api/sim/{run_id}/god",
        json={"action": "spawn_n", "params": {"count": 500}},  # clamp to 50
        headers={"X-Admin-Token": "test-token"},
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["agent_ids"]) <= 50


def test_god_mode_meteor_and_event(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    app_with_god_mode.post(f"/api/sim/{run_id}/tick", json={"count": 2})

    for action in ("meteor", "blessing", "bounty", "famine", "plague"):
        r = app_with_god_mode.post(
            f"/api/sim/{run_id}/god",
            json={"action": action, "params": {"amount": 0.2, "severity": 0.2, "resource_factor": 0.5}},
            headers={"X-Admin-Token": "test-token"},
        )
        assert r.status_code == 200, f"{action}: {r.text}"


# ──────────────────────────────────────────────────────────────────────────
# World route exposes artifact flag (existing uncommitted change)
# ──────────────────────────────────────────────────────────────────────────

def test_world_route_has_artifact_fields(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    r = app_with_god_mode.get(f"/api/sim/{run_id}/world")
    assert r.status_code == 200
    cells = r.json()["cells"]
    assert all("has_artifact" in c and "artifact_count" in c for c in cells)


# ──────────────────────────────────────────────────────────────────────────
# WebSocket — tick, malformed JSON (C-3), state sync, stop
# ──────────────────────────────────────────────────────────────────────────

def test_websocket_tick_flow(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]

    with app_with_god_mode.websocket_connect(f"/ws/sim/{run_id}") as ws:
        ws.send_text(json.dumps({"command": "tick", "count": 3}))
        seen = 0
        for _ in range(3):
            msg = ws.receive_json()
            assert msg["type"] == "tick"
            seen += 1
        assert seen == 3


def test_websocket_malformed_json_returns_error_frame(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]

    with app_with_god_mode.websocket_connect(f"/ws/sim/{run_id}") as ws:
        # Malformed JSON — must NOT drop the connection
        ws.send_text("this-is-not-json")
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "invalid_json"

        # Connection still usable afterwards
        ws.send_text(json.dumps({"command": "tick", "count": 1}))
        msg = ws.receive_json()
        assert msg["type"] == "tick"


def test_websocket_state_sync(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    with app_with_god_mode.websocket_connect(f"/ws/sim/{run_id}") as ws:
        ws.send_text(json.dumps({"command": "state"}))
        msg = ws.receive_json()
        assert msg["type"] == "state_sync"
        assert "agents" in msg
        assert "matrix" in msg


def test_websocket_unknown_command_returns_error(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    with app_with_god_mode.websocket_connect(f"/ws/sim/{run_id}") as ws:
        ws.send_text(json.dumps({"command": "invalid_command"}))
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "unknown_command"


# ──────────────────────────────────────────────────────────────────────────
# Media endpoint (H-2) — the narrate path is safe to exercise without a real
# LLM because narrator.Narrator falls back to deterministic stub text.
# ──────────────────────────────────────────────────────────────────────────

def test_media_narrate_rate_limit(app_with_god_mode, monkeypatch):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    # Disable the real LLM path so the endpoint returns quickly
    monkeypatch.setenv("OLLAMA_DISABLE", "1")

    ok_calls = 0
    rate_limited = False
    for _ in range(15):
        r = app_with_god_mode.post(f"/api/sim/{run_id}/media/narrate")
        if r.status_code == 200:
            ok_calls += 1
        elif r.status_code == 429:
            rate_limited = True
            break
    assert ok_calls >= 1
    assert rate_limited, "media narrate should rate-limit after 10 calls"


# ──────────────────────────────────────────────────────────────────────────
# Causal event timeline endpoints (Phase 7B)
# ──────────────────────────────────────────────────────────────────────────


def test_causal_events_endpoint_returns_recent_events(app_with_god_mode):
    """The /causal/events endpoint powers the Phase 7B timeline panel.
    Running a few ticks generates at least a few birth/death events from
    the engine's `record_event` calls."""
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    app_with_god_mode.post(f"/api/sim/{run_id}/tick", json={"count": 20})

    r = app_with_god_mode.get(f"/api/sim/{run_id}/causal/events?limit=50")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "events" in body
    assert "current_tick" in body
    assert isinstance(body["events"], list)
    # Each event must expose the fields the frontend panel renders/walks
    for evt in body["events"]:
        for key in ("event_id", "tick", "event_type", "description"):
            assert key in evt, f"causal event missing {key}: {evt}"


def test_causal_events_filter_by_type(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    app_with_god_mode.post(f"/api/sim/{run_id}/tick", json={"count": 10})

    r = app_with_god_mode.get(
        f"/api/sim/{run_id}/causal/events?types=birth&limit=500"
    )
    assert r.status_code == 200
    for evt in r.json()["events"]:
        assert evt["event_type"] == "birth"


def test_causal_chain_endpoint_returns_ancestors_and_descendants(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    app_with_god_mode.post(f"/api/sim/{run_id}/tick", json={"count": 15})

    # Grab any existing event
    r = app_with_god_mode.get(f"/api/sim/{run_id}/causal/events?limit=50")
    events = r.json()["events"]
    assert events, "expected at least one causal event after 15 ticks"
    event_id = events[0]["event_id"]

    r2 = app_with_god_mode.get(
        f"/api/sim/{run_id}/causal/events/{event_id}/chain"
    )
    assert r2.status_code == 200, r2.text
    chain = r2.json()
    assert chain["event"]["event_id"] == event_id
    assert isinstance(chain["ancestors"], list)
    assert isinstance(chain["descendants"], list)


def test_causal_chain_missing_event_returns_404(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    r = app_with_god_mode.get(f"/api/sim/{run_id}/causal/events/999999/chain")
    assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
# Population summary guard (M-5) — still produces a summary after extinction
# ──────────────────────────────────────────────────────────────────────────

def test_extinction_population_summary(app_with_god_mode):
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    # Kill every agent via god mode
    state_r = app_with_god_mode.get(f"/api/sim/{run_id}/state").json()
    for agent in state_r["agents"]:
        app_with_god_mode.post(
            f"/api/sim/{run_id}/god",
            json={"action": "kill", "target_id": agent["id"]},
            headers={"X-Admin-Token": "test-token"},
        )
    # Summary should still succeed (returns an empty-phase dict)
    r = app_with_god_mode.get(f"/api/sim/{run_id}/state")
    assert r.status_code == 200
    assert r.json()["summary"]["alive"] == 0


# ──────────────────────────────────────────────────────────────────────────
# CSV export guard (H-1) — extinction run must export without crashing
# ──────────────────────────────────────────────────────────────────────────

def test_csv_export_handles_extinction(tmp_path, app_with_god_mode):
    """CSV export used to IndexError on flat_agents[0] when population was
    zero. H-1 introduced an empty-list guard with a canonical header."""
    run_id = app_with_god_mode.post("/api/sim", json={}).json()["run_id"]
    # Force an empty agents snapshot by saving with zero alive agents.
    import gui.backend.api.state as state_module
    engine = state_module.manager.get_engine(run_id)
    for a in engine.agents:
        a.alive = False
    state_module.manager.db.save_snapshot(run_id, engine)
    state_module.manager.db.flush()

    out = tmp_path / "export"
    state_module.manager.db.export_run_csv(run_id, str(out))
    csv_file = out / "agents.csv"
    assert csv_file.exists()
    # Header present, zero data rows
    lines = csv_file.read_text(encoding="utf-8").splitlines()
    assert lines, "CSV should at least contain a header"
    assert "id" in lines[0]
