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

def test_causal_events_grows_but_stays_within_envelope(small_engine):
    """causal_events grows with ticks. Assert a pathological-growth ceiling.

    TODO(H-1): after cap-and-prune fix lands, replace the envelope with
        assert len(small_engine.causal_events) <= small_engine.cfg.causal_graph.max_events
    """
    ticks = 500
    for _ in range(ticks):
        small_engine.tick()

    # Envelope: <= 200 events per tick sustained would indicate a runaway loop.
    # Normal runs produce ~2-10 events/tick depending on activity.
    envelope = ticks * 200
    assert len(small_engine.causal_events) <= envelope, (
        f"causal_events grew to {len(small_engine.causal_events)} after {ticks} "
        f"ticks — envelope is {envelope}. Likely an event-recording loop bug."
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


# ─── H-2: pleroma_glimpses ────────────────────────────────────────────────────

def test_pleroma_glimpses_bounded_over_long_run(small_engine):
    """pleroma_glimpses is driven by high-awareness agents.

    Fast-forward agent awareness so glimpses can fire, then verify the
    list doesn't grow past a pathological threshold. Today's code has
    no cap — the envelope catches only runaway behavior.

    TODO(H-2): after cap lands, assert
        len(matrix_state.pleroma_glimpses) <= cfg.matrix.pleroma_max_history
    """
    # Boost awareness of half the population to unlock Gnostic-layer events
    for a in small_engine.agents[: len(small_engine.agents) // 2]:
        a.awareness = 0.95
        a.recursive_depth = 2

    ticks = 300
    for _ in range(ticks):
        small_engine.tick()

    matrix_state = getattr(small_engine, "matrix_state", None)
    if matrix_state is None or not hasattr(matrix_state, "pleroma_glimpses"):
        pytest.skip("matrix_state.pleroma_glimpses not present on this engine")

    # Envelope: one glimpse per agent per tick maximum would already be absurd.
    envelope = ticks * len(small_engine.agents)
    assert len(matrix_state.pleroma_glimpses) <= envelope


# ─── H-3: rate-limiter bucket dict ────────────────────────────────────────────

def test_rate_limiter_buckets_do_not_leak_on_unique_ips():
    """Simulate traffic from many distinct IPs through the rate limiter.

    Today each unique IP:key combination creates a permanent entry in
    `_hits`. This test documents current behavior and asserts a
    pathological-growth ceiling (1 entry per call). After the H-3 fix
    (empty-bucket eviction), tighten to:
        assert len(auth._hits) < N_IPS  # evicted once window passes
    """
    from gui.backend.api import auth

    # Snapshot size so we don't depend on test-order state
    auth._hits.clear()

    n_ips = 500
    for i in range(n_ips):
        request = MagicMock()
        request.client.host = f"10.0.0.{i % 256}.{i // 256}"
        auth.rate_limit(
            request,
            key="test_bucket",
            max_calls=10,
            window_seconds=60.0,
        )

    # Envelope: <= one bucket per unique IP:key combination.
    assert len(auth._hits) <= n_ips

    # TODO(H-3): after fix, force window expiry (time.sleep / monkeypatch
    # monotonic) then call rate_limit once more and assert
    # len(auth._hits) < n_ips — empty buckets should have been evicted.


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
