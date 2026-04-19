"""
Memory-bounds regression tests.

Pins the behavior targeted by findings H-1, H-2, H-3 in
[docs/code_review.md](../docs/code_review.md) — three collections
that grow without a cap in the current implementation:

- SimulationEngine.causal_events            (H-1)
- matrix_state.pleroma_glimpses             (H-2)
- gui.backend.api.auth._hits (rate buckets) (H-3)

Each test uses a loose upper bound today so the current code
still passes. When the cap-and-prune fix lands, tighten each
bound to `cfg.<area>.max_<thing>` and remove the TODO marker.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from src.config_loader import SimConfig
from src.engine import RunState, SimulationEngine


@pytest.fixture
def small_engine():
    """A small, fast engine tuned for long-ish tick counts in tests."""
    cfg = SimConfig.load().override({
        "population": {"initial_size": 20, "max_size": 80, "min_floor": 5},
        "narrator": {"provider": "none"},
    })
    eng = SimulationEngine(cfg, state=RunState(run_id="memory_bounds"))
    eng.initialize()
    return eng


# ─── H-1: causal_events ───────────────────────────────────────────────────────

def test_causal_events_respects_configured_cap(small_engine):
    """causal_events must never exceed cfg.causal_graph.max_events.

    Uses a deliberately small cap so the FIFO prune branch is exercised
    inside 500 ticks. With the default 50000 cap, the prune is rarely hit
    in short test runs.
    """
    max_events = 500
    small_engine.cfg = small_engine.cfg.override({"causal_graph": {"max_events": max_events}})

    for _ in range(500):
        small_engine.tick()

    assert len(small_engine.causal_events) <= max_events, (
        f"causal_events={len(small_engine.causal_events)} exceeded cap={max_events}"
    )


def test_causal_events_prunes_fifo_not_lifo(small_engine):
    """When pruning, the oldest events must be dropped — not the newest —
    so that recent causality chains remain intact."""
    small_engine.cfg = small_engine.cfg.override({"causal_graph": {"max_events": 50}})

    for _ in range(200):
        small_engine.tick()

    # Surviving events should all be from the later ticks (high tick numbers).
    # If we pruned LIFO instead, the survivors would be the first few ticks.
    ticks_in_survivors = [e.tick for e in small_engine.causal_events]
    assert min(ticks_in_survivors) > 10, (
        "oldest surviving event should be recent (FIFO prune); "
        f"got min tick {min(ticks_in_survivors)}"
    )


def test_causal_events_monotonic_within_tick(small_engine):
    """Within a single tick, causal_events only grows — never shrinks.

    This pins the invariant that record_event is append-only today,
    so a future "prune on read" implementation won't accidentally
    mutate during a tick.
    """
    before = len(small_engine.causal_events)
    small_engine.tick()
    after = len(small_engine.causal_events)
    assert after >= before


# ─── H-2: pleroma_glimpses (verified NOT a bug on 2026-04-17) ───────────────
#
# The 2026-04-17 review flagged `matrix_state.pleroma_glimpses.append(...)` at
# matrix_layer.py:1187 as unbounded. Re-verification showed the list is
# cleared at the TOP of every tick inside `process_pleroma_glimpses` (line
# 1148) and again on cycle reset (engine.py:349). So the list is by-design
# bounded to "this tick's glimpses only" — a transient frame payload for the
# frontend, not a log. The test below pins that invariant so a refactor that
# removes the per-tick clear would fail loudly.

def test_pleroma_glimpses_list_is_transient_per_tick(small_engine):
    """matrix_state.pleroma_glimpses is cleared each tick by design."""
    for a in small_engine.agents[: len(small_engine.agents) // 2]:
        a.awareness = 0.95
        a.recursive_depth = 2

    ticks = 200
    for _ in range(ticks):
        small_engine.tick()

    matrix_state = getattr(small_engine, "matrix_state", None)
    if matrix_state is None or not hasattr(matrix_state, "pleroma_glimpses"):
        pytest.skip("matrix_state.pleroma_glimpses not present on this engine")

    # Per-tick-clear invariant: after many ticks the size reflects only
    # the most recent tick, never the accumulated history.
    assert len(matrix_state.pleroma_glimpses) <= len(small_engine.agents), (
        "pleroma_glimpses should reflect a single tick's events, not history"
    )


# ─── H-3: rate-limiter bucket dict ────────────────────────────────────────────

def test_rate_limiter_buckets_do_not_leak_on_unique_ips(monkeypatch):
    """After the window expires, stale buckets are evicted by `_evict_empty_buckets`.

    Pins H-3: simulate many distinct IPs, advance monotonic time past the
    window, trigger another call, and assert the dict shrinks.
    """
    from gui.backend.api import auth

    auth._hits.clear()
    fake_now = [1_000.0]

    def fake_monotonic() -> float:
        return fake_now[0]

    monkeypatch.setattr(auth.time, "monotonic", fake_monotonic)

    n_ips = 500
    for i in range(n_ips):
        request = MagicMock()
        request.client.host = f"10.0.{i // 256}.{i % 256}"
        auth.rate_limit(request, key="test_bucket",
                        max_calls=10, window_seconds=60.0)

    # All buckets present before eviction.
    assert len(auth._hits) == n_ips

    # Advance time past the window and force an eviction sweep.
    fake_now[0] += 120.0
    auth._evict_empty_buckets(fake_now[0], window_seconds=60.0)

    assert len(auth._hits) == 0, (
        f"expected all {n_ips} buckets evicted after window expiry, "
        f"got {len(auth._hits)} still present"
    )


def test_rate_limiter_eviction_keeps_live_buckets(monkeypatch):
    """Active buckets (calls within window) must NOT be evicted."""
    from gui.backend.api import auth

    auth._hits.clear()
    fake_now = [1_000.0]
    monkeypatch.setattr(auth.time, "monotonic", lambda: fake_now[0])

    live = MagicMock()
    live.client.host = "10.0.0.1"
    stale = MagicMock()
    stale.client.host = "10.0.0.2"

    auth.rate_limit(live, key="k", max_calls=10, window_seconds=60.0)
    auth.rate_limit(stale, key="k", max_calls=10, window_seconds=60.0)

    # Age the stale bucket only — live gets a fresh call.
    fake_now[0] += 70.0
    auth.rate_limit(live, key="k", max_calls=10, window_seconds=60.0)

    auth._evict_empty_buckets(fake_now[0], window_seconds=60.0)

    assert "k:10.0.0.1" in auth._hits
    assert "k:10.0.0.2" not in auth._hits


def test_rate_limiter_rejects_over_limit():
    """Sanity check: the limiter actually enforces its cap today.

    Not a bounds test — a positive test to prove the limiter is wired
    up before we later assert it also cleans up.
    """
    from fastapi import HTTPException

    from gui.backend.api import auth

    auth._hits.clear()
    request = MagicMock()
    request.client.host = "10.0.0.1"

    for _ in range(5):
        auth.rate_limit(request, key="cap_test", max_calls=5, window_seconds=60.0)

    with pytest.raises(HTTPException) as exc:
        auth.rate_limit(request, key="cap_test", max_calls=5, window_seconds=60.0)
    assert exc.value.status_code == 429


# ─── Performance guard: ticks shouldn't asymptotically slow ───────────────────

def test_tick_time_does_not_degrade_with_event_history(small_engine):
    """If causal_events serialization or lookup were O(n), tick time
    would grow with accumulated history. This test catches that
    regression — it is *not* a strict bound, just a 10x guard.
    """
    # Warm-up to amortize any first-tick cost
    for _ in range(20):
        small_engine.tick()

    def time_n_ticks(n: int) -> float:
        start = time.perf_counter()
        for _ in range(n):
            small_engine.tick()
        return time.perf_counter() - start

    early = time_n_ticks(50)
    # Burn in history
    for _ in range(300):
        small_engine.tick()
    late = time_n_ticks(50)

    assert late < early * 10, (
        f"Tick time degraded {late / early:.1f}x after event history built up — "
        "likely O(n) cost somewhere in the tick loop."
    )
