"""
Resource grid — terrain types, depletion, regeneration, tech breakthroughs.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from src.config_loader import SimConfig


@dataclass
class TechBreakthrough:
    """A technology that has been unlocked in a specific cell."""
    name: str
    unlocked_at: int  # tick
    resource_bonus: float
    capacity_bonus: int


@dataclass
class ResourceCell:
    """A single zone in the resource grid."""
    row: int
    col: int
    terrain: str
    base_resources: float
    current_resources: float
    harshness_modifier: float
    skill_bonus: Optional[str]
    skill_bonus_amount: float
    carrying_capacity: int
    regeneration_rate: float
    unlocked_techs: list[TechBreakthrough] = field(default_factory=list)
    agent_count: int = 0

    resource_cap: float = 1.5

    @property
    def effective_resources(self) -> float:
        """Resources including tech bonuses."""
        bonus = sum(t.resource_bonus for t in self.unlocked_techs)
        return min(self.resource_cap, self.current_resources + bonus)

    @property
    def effective_capacity(self) -> int:
        bonus = sum(t.capacity_bonus for t in self.unlocked_techs)
        return self.carrying_capacity + bonus

    @property
    def pressure(self) -> float:
        cap = self.effective_capacity
        return self.agent_count / cap if cap > 0 else 999.0

    def to_dict(self) -> dict:
        return {
            "row": self.row, "col": self.col, "terrain": self.terrain,
            "base_resources": round(self.base_resources, 3),
            "current_resources": round(self.current_resources, 3),
            "effective_resources": round(self.effective_resources, 3),
            "harshness_modifier": self.harshness_modifier,
            "skill_bonus": self.skill_bonus,
            "carrying_capacity": self.effective_capacity,
            "agent_count": self.agent_count,
            "pressure": round(self.pressure, 2),
            "techs": [t.name for t in self.unlocked_techs],
        }


class ResourceGrid:
    """The world — an NxN grid of resource cells with terrain."""

    def __init__(self, cfg: SimConfig):
        self.size = cfg.environment.grid_size
        self.cfg = cfg
        self.cells: list[list[ResourceCell]] = []
        self.global_techs: set[str] = set()  # for tracking across cells
        self._generate()

    def _generate(self):
        """Create the terrain map using weighted random assignment with smoothing."""
        env = self.cfg.environment

        # Build terrain weights
        weights = env.terrain_weights.to_dict() if hasattr(env.terrain_weights, 'to_dict') else dict(env.terrain_weights._data)
        terrains = list(weights.keys())
        probs = list(weights.values())

        # Normalize
        total = sum(probs)
        probs = [p / total for p in probs]

        # Generate base terrain
        raw = []
        for r in range(self.size):
            row = []
            for c in range(self.size):
                terrain = random.choices(terrains, weights=probs, k=1)[0]
                row.append(terrain)
            raw.append(row)

        # Light smoothing — each cell has a chance to match its neighbors
        for _ in range(2):
            for r in range(self.size):
                for c in range(self.size):
                    neighbors = []
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.size and 0 <= nc < self.size:
                            neighbors.append(raw[nr][nc])
                    if neighbors and random.random() < 0.4:
                        raw[r][c] = max(set(neighbors), key=neighbors.count)

        # Build cells
        props = env.terrain_properties
        regen = env.regeneration_rate
        base_cap = env.base_carrying_capacity

        self.cells = []
        for r in range(self.size):
            row = []
            for c in range(self.size):
                terrain = raw[r][c]
                tp = getattr(props, terrain)
                res_min = tp.resource_min
                res_max = tp.resource_max
                base_res = random.uniform(res_min, res_max)

                cell = ResourceCell(
                    row=r, col=c, terrain=terrain,
                    base_resources=base_res,
                    current_resources=base_res,
                    harshness_modifier=tp.harshness_modifier,
                    skill_bonus=tp.skill_bonus if tp.skill_bonus != "null" and tp.skill_bonus else None,
                    skill_bonus_amount=tp.skill_bonus_amount,
                    carrying_capacity=base_cap,
                    regeneration_rate=regen,
                    resource_cap=getattr(env, 'resource_cap', 1.5),
                )
                row.append(cell)
            self.cells.append(row)

    def get_cell(self, x: float, y: float) -> ResourceCell:
        """Map continuous (x,y) in [0,1] to grid cell."""
        r = min(self.size - 1, max(0, int(y * self.size)))
        c = min(self.size - 1, max(0, int(x * self.size)))
        return self.cells[r][c]

    def get_cell_rc(self, row: int, col: int) -> Optional[ResourceCell]:
        if 0 <= row < self.size and 0 <= col < self.size:
            return self.cells[row][col]
        return None

    def get_adjacent_cells(self, row: int, col: int) -> list[ResourceCell]:
        """Return all valid adjacent cells (including diagonals)."""
        adj = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                cell = self.get_cell_rc(row + dr, col + dc)
                if cell:
                    adj.append(cell)
        return adj

    def update_agent_counts(self, agents: list):
        """Recount agents per cell. Call once per tick."""
        for row in self.cells:
            for cell in row:
                cell.agent_count = 0
        for a in agents:
            if a.alive:
                cell = self.get_cell(a.x, a.y)
                cell.agent_count += 1

    def tick_resources(self):
        """Deplete and regenerate resources based on population pressure."""
        depletion_rate = getattr(self.cfg.environment, 'depletion_rate', 0.02)
        for row in self.cells:
            for cell in row:
                pressure = cell.pressure
                if pressure > 1.0:
                    depletion = (pressure - 1.0) * depletion_rate
                    cell.current_resources = max(0.0, cell.current_resources - depletion)
                else:
                    recovery = cell.regeneration_rate * (1.0 - pressure)
                    cell.current_resources = min(
                        cell.base_resources, cell.current_resources + recovery
                    )

    def check_breakthroughs(self, cell: ResourceCell,
                                avg_tech: float, avg_social: float,
                                tick: int) -> Optional[TechBreakthrough]:
            """Check if a cell qualifies for a new tech breakthrough."""
            bt_cfg = self.cfg.environment.tech_breakthroughs
            if not bt_cfg.enabled:
                return None

            existing_names = {t.name for t in cell.unlocked_techs}

            for threshold in bt_cfg.thresholds:
                name = threshold["name"]
                if name in existing_names:
                    continue
                # Terrain restriction
                if threshold.get("terrain") and threshold["terrain"] != cell.terrain:
                    continue
                # Tech level check
                if avg_tech < threshold["tech_level"]:
                    continue
                # Social requirement
                if threshold.get("requires_social") and avg_social < threshold["requires_social"]:
                    continue

                bt = TechBreakthrough(
                    name=name,
                    unlocked_at=tick,
                    resource_bonus=threshold["resource_bonus"],
                    capacity_bonus=threshold.get("capacity_bonus", 0),
                )
                cell.unlocked_techs.append(bt)
                self.global_techs.add(name)
                return bt

            return None

    def to_dict(self) -> dict:
        """Serialize full grid state including per-cell resources, techs, terrain."""
        cells_data = []
        for row in self.cells:
            row_data = []
            for cell in row:
                cell_data = {
                    "row": cell.row, "col": cell.col, "terrain": cell.terrain,
                    "base_resources": cell.base_resources,
                    "current_resources": cell.current_resources,
                    "harshness_modifier": cell.harshness_modifier,
                    "skill_bonus": cell.skill_bonus,
                    "skill_bonus_amount": cell.skill_bonus_amount,
                    "carrying_capacity": cell.carrying_capacity,
                    "regeneration_rate": cell.regeneration_rate,
                    "techs": [{"name": t.name, "unlocked_at": t.unlocked_at,
                               "resource_bonus": t.resource_bonus,
                               "capacity_bonus": t.capacity_bonus}
                              for t in cell.unlocked_techs],
                }
                row_data.append(cell_data)
            cells_data.append(row_data)
        return {
            "size": self.size,
            "cells": cells_data,
            "global_techs": list(self.global_techs),
        }

    @classmethod
    def from_dict(cls, data: dict, cfg: SimConfig) -> ResourceGrid:
        """Restore a grid from serialized state with full fidelity."""
        grid = cls.__new__(cls)
        grid.size = data.get("size", cfg.environment.grid_size)
        grid.cfg = cfg
        grid.global_techs = set(data.get("global_techs", []))
        grid.cells = []

        for row_data in data.get("cells", []):
            row = []
            for cd in row_data:
                techs = []
                for td in cd.get("techs", []):
                    if isinstance(td, str):
                        # Legacy format: just tech name string
                        techs.append(TechBreakthrough(name=td, unlocked_at=0,
                                                       resource_bonus=0.05, capacity_bonus=2))
                    else:
                        techs.append(TechBreakthrough(
                            name=td["name"], unlocked_at=td.get("unlocked_at", 0),
                            resource_bonus=td.get("resource_bonus", 0.05),
                            capacity_bonus=td.get("capacity_bonus", 2),
                        ))
                cell = ResourceCell(
                    row=cd["row"], col=cd["col"], terrain=cd["terrain"],
                    base_resources=cd["base_resources"],
                    current_resources=cd["current_resources"],
                    harshness_modifier=cd["harshness_modifier"],
                    skill_bonus=cd.get("skill_bonus"),
                    skill_bonus_amount=cd.get("skill_bonus_amount", 0.0),
                    carrying_capacity=cd.get("carrying_capacity", cfg.environment.base_carrying_capacity),
                    regeneration_rate=cd.get("regeneration_rate", cfg.environment.regeneration_rate),
                    unlocked_techs=techs,
                )
                row.append(cell)
            grid.cells.append(row)

        return grid

    def summary(self) -> dict:
        """Aggregate grid statistics."""
        total_res = 0
        total_agents = 0
        terrain_counts = {}
        depleted = 0
        for row in self.cells:
            for cell in row:
                total_res += cell.effective_resources
                total_agents += cell.agent_count
                terrain_counts[cell.terrain] = terrain_counts.get(cell.terrain, 0) + 1
                if cell.current_resources < 0.1:
                    depleted += 1
        n = self.size * self.size
        return {
            "avg_resources": round(total_res / n, 3),
            "depleted_cells": depleted,
            "total_cells": n,
            "terrain_distribution": terrain_counts,
            "global_techs": list(self.global_techs),
        }