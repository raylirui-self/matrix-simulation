"""
The Haven — The Real World.

A second world layer running in parallel with the Matrix simulation.
The Haven is smaller, harsher, and resource-scarce — but it is *real*.
Redpilled agents who jack out live here. They can jack back in for
missions: rescue candidates, fight Sentinels, or contact the Oracle.

Public API
----------
HavenCell          — One cell in the Haven grid.
HavenGrid          — The Haven's resource grid (smaller, harsher).
Mission            — A jack-in mission with goal, duration, and risk.
CouncilVote        — A single council vote record.
HavenState         — Top-level Haven state (grid, missions, council).

init_haven(cfg)                         -> HavenState
    Create and return initial Haven state from config.

process_haven(agents, state, tick, cfg) -> dict
    Run one Haven tick: resource management, mission updates, council.
    Returns stats dict.

try_jack_out(agent, state, tick, cfg)   -> bool
    Attempt to move an agent from simulation to Haven.

try_jack_in(agent, state, tick, cfg, mission_type) -> Mission | None
    Launch a jack-in mission for a Haven agent back into the simulation.

complete_mission(agent, mission, tick, success) -> None
    Resolve a finished or failed mission.

run_council_vote(agents, state, tick, cfg) -> CouncilVote
    Hawks vs doves vote on resource allocation or mission approval.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from src.agents import Agent


# ─────────────────────────────────────────────
# Haven Grid
# ─────────────────────────────────────────────

@dataclass
class HavenCell:
    """A single zone in the Haven grid."""
    row: int
    col: int
    base_resources: float
    current_resources: float
    harshness: float
    carrying_capacity: int
    regeneration_rate: float
    agent_count: int = 0

    @property
    def effective_resources(self) -> float:
        return self.current_resources

    @property
    def pressure(self) -> float:
        return self.agent_count / self.carrying_capacity if self.carrying_capacity > 0 else 999.0

    def to_dict(self) -> dict:
        return {
            "row": self.row, "col": self.col,
            "base_resources": round(self.base_resources, 3),
            "current_resources": round(self.current_resources, 3),
            "harshness": self.harshness,
            "carrying_capacity": self.carrying_capacity,
            "agent_count": self.agent_count,
            "pressure": round(self.pressure, 2),
        }


class HavenGrid:
    """The Haven's resource grid — smaller and harsher than the simulation."""

    def __init__(self, cfg):
        hcfg = cfg.haven
        self.size: int = hcfg.grid_size
        self.cells: list[list[HavenCell]] = []
        self._generate(hcfg)

    def _generate(self, hcfg):
        base_res = hcfg.base_resources
        harshness = hcfg.harshness
        regen = hcfg.regeneration_rate
        cap = hcfg.base_carrying_capacity

        self.cells = []
        for r in range(self.size):
            row = []
            for c in range(self.size):
                res = base_res * random.uniform(0.6, 1.0)
                cell = HavenCell(
                    row=r, col=c,
                    base_resources=res,
                    current_resources=res,
                    harshness=harshness,
                    carrying_capacity=cap,
                    regeneration_rate=regen,
                )
                row.append(cell)
            self.cells.append(row)

    def get_cell(self, x: float, y: float) -> HavenCell:
        r = min(self.size - 1, max(0, int(y * self.size)))
        c = min(self.size - 1, max(0, int(x * self.size)))
        return self.cells[r][c]

    def update_agent_counts(self, agents: list[Agent]):
        for row in self.cells:
            for cell in row:
                cell.agent_count = 0
        for a in agents:
            if a.alive and a.location == "haven":
                cell = self.get_cell(a.x, a.y)
                cell.agent_count += 1

    def tick_resources(self):
        for row in self.cells:
            for cell in row:
                if cell.pressure > 1.0:
                    depletion = (cell.pressure - 1.0) * 0.03
                    cell.current_resources = max(0.0, cell.current_resources - depletion)
                else:
                    recovery = cell.regeneration_rate * (1.0 - cell.pressure)
                    cell.current_resources = min(cell.base_resources, cell.current_resources + recovery)

    def to_dict(self) -> dict:
        return {
            "size": self.size,
            "cells": [[c.to_dict() for c in row] for row in self.cells],
        }


# ─────────────────────────────────────────────
# Missions
# ─────────────────────────────────────────────

@dataclass
class Mission:
    """A jack-in mission: goal + duration + risk."""
    id: int
    agent_id: int
    mission_type: str       # "rescue", "fight_sentinels", "contact_oracle"
    target_tick: int        # tick when mission completes
    deadline_tick: int      # forced jack-out tick
    risk_per_tick: float    # failure probability per tick
    started_at: int
    completed: bool = False
    success: bool = False
    failed: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id, "agent_id": self.agent_id,
            "mission_type": self.mission_type,
            "target_tick": self.target_tick,
            "deadline_tick": self.deadline_tick,
            "risk_per_tick": round(self.risk_per_tick, 4),
            "started_at": self.started_at,
            "completed": self.completed,
            "success": self.success,
            "failed": self.failed,
        }


_mission_id_counter = 0


def _next_mission_id() -> int:
    global _mission_id_counter
    _mission_id_counter += 1
    return _mission_id_counter


def reset_mission_id_counter(val: int = 0):
    global _mission_id_counter
    _mission_id_counter = val


# ─────────────────────────────────────────────
# Council
# ─────────────────────────────────────────────

@dataclass
class CouncilVote:
    """Record of a Haven council vote."""
    tick: int
    topic: str              # "resource_allocation" or "mission_approval"
    hawks: int
    doves: int
    neutrals: int
    outcome: str            # "hawk_win", "dove_win", "tie"
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tick": self.tick, "topic": self.topic,
            "hawks": self.hawks, "doves": self.doves,
            "neutrals": self.neutrals, "outcome": self.outcome,
            "details": self.details,
        }


# ─────────────────────────────────────────────
# Haven State
# ─────────────────────────────────────────────

@dataclass
class HavenState:
    """Top-level state for the Haven world layer."""
    grid: HavenGrid
    missions: list[Mission] = field(default_factory=list)
    council_votes: list[CouncilVote] = field(default_factory=list)
    last_vote_tick: int = 0

    def to_dict(self) -> dict:
        return {
            "grid": self.grid.to_dict(),
            "missions": [m.to_dict() for m in self.missions],
            "council_votes": [v.to_dict() for v in self.council_votes[-10:]],
            "last_vote_tick": self.last_vote_tick,
        }


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def init_haven(cfg) -> HavenState:
    """Create and return initial Haven state from config."""
    grid = HavenGrid(cfg)
    return HavenState(grid=grid)


def try_jack_out(agent: Agent, haven_state: HavenState, tick: int, cfg) -> bool:
    """Attempt to move a simulation agent to the Haven.

    Requirements: agent must be redpilled (if configured) and above
    awareness threshold. Returns True if jack-out succeeds.
    """
    hcfg = cfg.haven
    if agent.location != "simulation":
        return False
    if not agent.alive:
        return False
    if hcfg.jackout_redpill_required and not agent.redpilled:
        return False
    if agent.awareness < hcfg.jackout_awareness_threshold:
        return False

    agent.location = "haven"
    # Place agent randomly in Haven grid
    agent.x = random.uniform(0.05, 0.95)
    agent.y = random.uniform(0.05, 0.95)
    agent.add_memory(tick, "Jacked out of the Matrix — entered the Haven")
    # Jacking out is traumatic: health dip, emotional upheaval
    agent.health = max(0.1, agent.health - 0.15)
    agent.emotions["fear"] = min(1.0, agent.emotions.get("fear", 0) + 0.3)
    agent.emotions["hope"] = min(1.0, agent.emotions.get("hope", 0) + 0.2)
    return True


def try_jack_in(agent: Agent, haven_state: HavenState, tick: int, cfg,
                mission_type: str) -> Optional[Mission]:
    """Launch a jack-in mission for a Haven agent back into the simulation.

    The agent appears in the simulation with boosted stats but a time limit.
    Returns the created Mission or None if invalid.
    """
    hcfg = cfg.haven
    if agent.location != "haven" or not agent.alive:
        return None

    valid_types = list(hcfg.jackin_mission_types)
    if mission_type not in valid_types:
        return None

    # Check no active mission already
    for m in haven_state.missions:
        if m.agent_id == agent.id and not m.completed and not m.failed:
            return None

    dur_range = list(hcfg.mission_duration_range)
    duration = random.randint(dur_range[0], dur_range[1])
    time_limit = hcfg.mission_time_limit

    mission = Mission(
        id=_next_mission_id(),
        agent_id=agent.id,
        mission_type=mission_type,
        target_tick=tick + duration,
        deadline_tick=tick + time_limit,
        risk_per_tick=hcfg.mission_risk_base,
        started_at=tick,
    )
    haven_state.missions.append(mission)

    # Move agent to simulation with boosted stats
    agent.location = "simulation"
    agent.x = random.uniform(0.05, 0.95)
    agent.y = random.uniform(0.05, 0.95)

    # Apply mission stat boost
    boost = hcfg.mission_stat_boost
    for skill in agent.skills:
        agent.skills[skill] = min(1.0, agent.skills[skill] + boost)

    agent.add_memory(tick, f"Jacked into the Matrix — mission: {mission_type}")
    return mission


def complete_mission(agent: Agent, mission: Mission, tick: int, success: bool) -> None:
    """Resolve a finished or failed mission. Agent returns to Haven."""
    mission.completed = True
    mission.success = success

    if success:
        agent.add_memory(tick, f"Mission '{mission.mission_type}' succeeded")
        agent.emotions["hope"] = min(1.0, agent.emotions.get("hope", 0) + 0.3)
        # Rescue missions: awareness boost to show rescued agents exist
        if mission.mission_type == "rescue":
            agent.awareness = min(1.0, agent.awareness + 0.05)
        elif mission.mission_type == "fight_sentinels":
            agent.emotions["anger"] = max(0.0, agent.emotions.get("anger", 0) - 0.1)
        elif mission.mission_type == "contact_oracle":
            agent.awareness = min(1.0, agent.awareness + 0.1)
    else:
        mission.failed = True
        agent.add_memory(tick, f"Mission '{mission.mission_type}' failed")
        agent.health = max(0.0, agent.health - 0.2)
        agent.emotions["fear"] = min(1.0, agent.emotions.get("fear", 0) + 0.2)

    # Return to Haven
    agent.location = "haven"
    agent.x = random.uniform(0.05, 0.95)
    agent.y = random.uniform(0.05, 0.95)


def run_council_vote(agents: list[Agent], haven_state: HavenState,
                     tick: int, cfg) -> CouncilVote:
    """Hawks vs doves vote on resource allocation or mission approval.

    Hawks (high aggression) want aggressive missions and concentrated resources.
    Doves (low aggression) want defense and even resource distribution.
    """
    hcfg = cfg.haven
    council_cfg = hcfg.council
    haven_agents = [a for a in agents if a.alive and a.location == "haven"]

    hawk_threshold = council_cfg.hawk_threshold
    dove_threshold = council_cfg.dove_threshold

    hawks = 0
    doves = 0
    neutrals = 0
    for a in haven_agents:
        if a.traits.aggression >= hawk_threshold:
            hawks += 1
        elif a.traits.aggression <= dove_threshold:
            doves += 1
        else:
            neutrals += 1

    # Determine outcome
    if hawks > doves:
        outcome = "hawk_win"
    elif doves > hawks:
        outcome = "dove_win"
    else:
        outcome = "tie"

    # Alternate between resource and mission topics
    topic = "resource_allocation" if tick % 2 == 0 else "mission_approval"

    details: dict = {}
    share_rate = council_cfg.resource_share_rate

    if topic == "resource_allocation":
        if outcome == "hawk_win":
            # Concentrate resources: top-resourced cells get more, others lose
            details = {"strategy": "concentrate", "share_rate": share_rate}
            _apply_hawk_resources(haven_state.grid, share_rate)
        else:
            # Distribute evenly
            details = {"strategy": "distribute", "share_rate": share_rate}
            _apply_dove_resources(haven_state.grid, share_rate)
    else:
        # Mission approval: hawks approve offensive missions, doves defensive
        if outcome == "hawk_win":
            details = {"approved_types": ["rescue", "fight_sentinels"]}
        else:
            details = {"approved_types": ["contact_oracle"]}

    vote = CouncilVote(
        tick=tick, topic=topic,
        hawks=hawks, doves=doves, neutrals=neutrals,
        outcome=outcome, details=details,
    )
    haven_state.council_votes.append(vote)
    haven_state.last_vote_tick = tick
    return vote


def _apply_hawk_resources(grid: HavenGrid, share_rate: float):
    """Hawks concentrate resources — strongest cells gain, weakest lose."""
    all_cells = [c for row in grid.cells for c in row]
    if not all_cells:
        return
    avg = sum(c.current_resources for c in all_cells) / len(all_cells)
    for c in all_cells:
        if c.current_resources >= avg:
            c.current_resources = min(c.base_resources * 1.5, c.current_resources + share_rate * 0.5)
        else:
            c.current_resources = max(0.0, c.current_resources - share_rate * 0.3)


def _apply_dove_resources(grid: HavenGrid, share_rate: float):
    """Doves redistribute — equalize resources across cells."""
    all_cells = [c for row in grid.cells for c in row]
    if not all_cells:
        return
    avg = sum(c.current_resources for c in all_cells) / len(all_cells)
    for c in all_cells:
        diff = avg - c.current_resources
        c.current_resources += diff * share_rate
        c.current_resources = max(0.0, c.current_resources)


def process_haven(agents: list[Agent], haven_state: HavenState,
                  tick: int, cfg) -> dict:
    """Run one Haven tick: resources, health decay, mission updates, council votes.

    Returns a stats dict.
    """
    hcfg = cfg.haven
    haven_agents = [a for a in agents if a.alive and a.location == "haven"]

    # ── Update agent counts on grid ──
    haven_state.grid.update_agent_counts(agents)

    # ── Resource tick ──
    haven_state.grid.tick_resources()

    # ── Health decay (harsher than simulation) ──
    for a in haven_agents:
        cell = haven_state.grid.get_cell(a.x, a.y)
        decay = 0.003 * cell.harshness
        resource_factor = 1.5 - cell.effective_resources
        decay *= max(0.5, resource_factor)
        a.health -= decay
        if a.health <= 0:
            a.alive = False
            a.health = 0
            a.death_cause = "haven_starvation"

    # ── Mission updates ──
    missions_completed = 0
    missions_failed = 0
    active_missions = [m for m in haven_state.missions if not m.completed and not m.failed]
    for mission in active_missions:
        agent = next((a for a in agents if a.id == mission.agent_id and a.alive), None)
        if agent is None:
            mission.failed = True
            mission.completed = True
            missions_failed += 1
            continue

        # Risk roll each tick
        if random.random() < mission.risk_per_tick:
            complete_mission(agent, mission, tick, success=False)
            missions_failed += 1
            continue

        # Mission completed on target tick
        if tick >= mission.target_tick:
            complete_mission(agent, mission, tick, success=True)
            missions_completed += 1
            continue

        # Forced jack-out on deadline
        if tick >= mission.deadline_tick:
            complete_mission(agent, mission, tick, success=False)
            missions_failed += 1
            continue

    # ── Council vote ──
    vote_result = None
    council_cfg = hcfg.council
    if haven_agents and tick - haven_state.last_vote_tick >= council_cfg.vote_interval:
        vote_result = run_council_vote(agents, haven_state, tick, cfg)

    # ── Auto jack-out: redpilled simulation agents above threshold ──
    jacked_out = 0
    for a in agents:
        if not a.alive or a.location != "simulation":
            continue
        if a.redpilled and a.awareness >= hcfg.jackout_awareness_threshold:
            # Small chance per tick to spontaneously jack out
            if random.random() < 0.02:
                if try_jack_out(a, haven_state, tick, cfg):
                    jacked_out += 1

    return {
        "haven_population": len(haven_agents),
        "missions_active": len([m for m in haven_state.missions if not m.completed and not m.failed]),
        "missions_completed": missions_completed,
        "missions_failed": missions_failed,
        "jacked_out": jacked_out,
        "council_vote": vote_result.to_dict() if vote_result else None,
    }
