"""
Causal event graph — utilities for traversing and exporting causality chains.

Events are recorded by SimulationEngine.record_event() during ticks.
Each CausalEvent has an event_id and an optional caused_by (parent event_id).
This module provides traversal (ancestors/descendants) and JSON export.
"""
from __future__ import annotations

import json
from typing import Optional

from src.engine import CausalEvent


def build_index(events: list[CausalEvent]) -> tuple[dict[int, CausalEvent], dict[int, list[int]]]:
    """Build lookup dicts: id->event and parent_id->child_ids.

    Returns:
        (by_id, children_of) where children_of maps event_id -> list of child event_ids.
    """
    by_id: dict[int, CausalEvent] = {}
    children_of: dict[int, list[int]] = {}

    for evt in events:
        by_id[evt.event_id] = evt
        if evt.caused_by is not None:
            children_of.setdefault(evt.caused_by, []).append(evt.event_id)

    return by_id, children_of


def get_ancestors(event_id: int, by_id: dict[int, CausalEvent]) -> list[CausalEvent]:
    """Walk the caused_by chain upward to find all ancestors (root first)."""
    ancestors: list[CausalEvent] = []
    current = by_id.get(event_id)
    visited: set[int] = set()

    while current and current.caused_by is not None and current.caused_by not in visited:
        visited.add(current.event_id)
        parent = by_id.get(current.caused_by)
        if parent:
            ancestors.append(parent)
            current = parent
        else:
            break

    ancestors.reverse()  # root-first order
    return ancestors


def get_descendants(event_id: int, by_id: dict[int, CausalEvent],
                    children_of: dict[int, list[int]],
                    max_depth: int = 50) -> list[CausalEvent]:
    """BFS to find all downstream effects of an event."""
    result: list[CausalEvent] = []
    queue = [event_id]
    visited: set[int] = {event_id}
    depth = 0

    while queue and depth < max_depth:
        next_queue: list[int] = []
        for eid in queue:
            for child_id in children_of.get(eid, []):
                if child_id not in visited:
                    visited.add(child_id)
                    child = by_id.get(child_id)
                    if child:
                        result.append(child)
                        next_queue.append(child_id)
        queue = next_queue
        depth += 1

    return result


def get_full_chain(event_id: int, by_id: dict[int, CausalEvent],
                   children_of: dict[int, list[int]]) -> list[CausalEvent]:
    """Get the full causal chain: ancestors + self + descendants."""
    ancestors = get_ancestors(event_id, by_id)
    self_evt = by_id.get(event_id)
    descendants = get_descendants(event_id, by_id, children_of)

    chain = ancestors[:]
    if self_evt:
        chain.append(self_evt)
    chain.extend(descendants)
    return chain


def find_root_events(events: list[CausalEvent]) -> list[CausalEvent]:
    """Find events that have no parent (causal chain roots)."""
    return [e for e in events if e.caused_by is None]


def find_longest_chains(events: list[CausalEvent], top_n: int = 10) -> list[list[CausalEvent]]:
    """Find the N longest causal chains in the event graph."""
    by_id, children_of = build_index(events)

    # Find leaf events (no children)
    all_ids = {e.event_id for e in events}
    parent_ids = set()
    for clist in children_of.values():
        parent_ids.update(clist)
    # Events that are never a child of anything are roots
    # Events that are never a parent of anything are leaves
    leaf_ids = all_ids - set(children_of.keys())

    chains: list[list[CausalEvent]] = []
    for leaf_id in leaf_ids:
        leaf = by_id.get(leaf_id)
        if not leaf:
            continue
        ancestors = get_ancestors(leaf_id, by_id)
        chain = ancestors + [leaf]
        if len(chain) > 1:  # only interesting if multi-step
            chains.append(chain)

    chains.sort(key=len, reverse=True)
    return chains[:top_n]


def export_events_json(events: list[CausalEvent], path: str) -> None:
    """Export all causal events to a JSON file."""
    data = {
        "total_events": len(events),
        "events": [e.to_dict() for e in events],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_chains_json(events: list[CausalEvent], path: str,
                       top_n: int = 20) -> dict:
    """Export the longest causal chains to a JSON file.

    Returns summary stats about the chains.
    """
    chains = find_longest_chains(events, top_n=top_n)
    by_id, children_of = build_index(events)

    chain_data = []
    for i, chain in enumerate(chains):
        chain_data.append({
            "chain_id": i,
            "length": len(chain),
            "root_event": chain[0].to_dict() if chain else None,
            "leaf_event": chain[-1].to_dict() if chain else None,
            "events": [e.to_dict() for e in chain],
            "summary": " -> ".join(
                f"{e.event_type}(#{e.agent_id})" if e.agent_id else e.event_type
                for e in chain
            ),
        })

    # Event type distribution
    type_counts: dict[str, int] = {}
    for e in events:
        type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1

    # Count linked vs unlinked events
    linked = sum(1 for e in events if e.caused_by is not None)

    stats = {
        "total_events": len(events),
        "linked_events": linked,
        "unlinked_events": len(events) - linked,
        "event_type_counts": type_counts,
        "longest_chain_length": len(chains[0]) if chains else 0,
        "chains_found": len(chains),
    }

    output = {
        "stats": stats,
        "chains": chain_data,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return stats
