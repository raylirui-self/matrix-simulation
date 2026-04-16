"""Causal event graph endpoints (Phase 7B — causal timeline panel).

Read-only queries over ``engine.causal_events``. The timeline panel on the
frontend polls ``/events`` for recent nodes and, on click, calls ``/chain``
for the ancestors+descendants of a specific event.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from gui.backend.api.state import manager
from src.causal_graph import build_index, get_ancestors, get_descendants

router = APIRouter(prefix="/api/sim/{run_id}/causal", tags=["causal"])


# Event types considered "major" enough to show on the timeline by default.
# Everything else is still queryable via ?types=... but this keeps the panel
# from drowning in low-signal per-tick noise.
DEFAULT_TIMELINE_TYPES = {
    "birth",
    "death",
    "breakthrough",
    "faction_founded",
    "faction_dissolved",
    "war_started",
    "war_ended",
    "anomaly_designated",
    "cycle_reset",
    "redpill",
    "jack_out",
    "jack_in",
    "archon_destroyed",
}


def _load_engine(run_id: str):
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return engine


@router.get("/events")
def list_causal_events(
    run_id: str,
    since_tick: int = 0,
    limit: int = 200,
    types: str | None = None,
):
    """Return recent causal events in ascending tick order.

    - ``since_tick``: return events with ``tick >= since_tick``.
    - ``limit``: hard cap on the number of events returned (most recent wins).
    - ``types``: optional comma-separated whitelist; defaults to a curated set
      of "major" event types for timeline display.
    """
    engine = _load_engine(run_id)
    if types:
        type_filter = {t.strip() for t in types.split(",") if t.strip()}
    else:
        type_filter = DEFAULT_TIMELINE_TYPES

    # Cap limit to avoid accidental full-history fetches blowing memory.
    limit = max(1, min(int(limit), 2000))

    # Walk events newest-first (engine.causal_events is append-only so the
    # tail is the freshest) and stop once we have `limit` matches.
    matching: list[dict] = []
    for evt in reversed(getattr(engine, 'causal_events', []) or []):
        if evt.tick < since_tick:
            break
        if evt.event_type not in type_filter:
            continue
        matching.append(evt.to_dict())
        if len(matching) >= limit:
            break

    # Reverse back to ascending order for the timeline (oldest → newest).
    matching.reverse()
    return {
        "events": matching,
        "total": len(matching),
        "current_tick": engine.state.current_tick,
    }


@router.get("/events/{event_id}/chain")
def get_causal_chain(run_id: str, event_id: int):
    """Return ancestors + self + descendants for a single event."""
    engine = _load_engine(run_id)
    events = getattr(engine, 'causal_events', []) or []
    by_id, children_of = build_index(events)
    self_evt = by_id.get(event_id)
    if self_evt is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

    ancestors = get_ancestors(event_id, by_id)
    descendants = get_descendants(event_id, by_id, children_of)
    return {
        "event": self_evt.to_dict(),
        "ancestors": [e.to_dict() for e in ancestors],
        "descendants": [e.to_dict() for e in descendants],
    }
