"""
System: Simulation Dreams — periodic altered states for the entire simulation.

Every N ticks the simulation enters a dream state lasting K ticks.
During dreams:
  - Movement range is increased, terrain effects are reduced
  - Dead agents temporarily manifest as ghosts
  - Collective unconscious: dream content drawn from recent sim history
  - Lucid dreaming: high-awareness agents gain special abilities and permanent awareness boosts

Research basis: Jungian collective unconscious + lucid dreaming literature.
Consciousness phases gate lucid dreaming ability — recursive agents have maximum dream lucidity.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field

from src.agents import Agent

logger = logging.getLogger(__name__)


@dataclass
class GhostManifestation:
    """A temporarily manifested dead agent during a dream cycle."""
    source_agent_id: int
    x: float
    y: float
    name: str  # description of the ghost
    memories: list[str]  # key memories the ghost carries
    tick_manifested: int

    def to_dict(self) -> dict:
        return {
            "source_agent_id": self.source_agent_id,
            "x": round(self.x, 4), "y": round(self.y, 4),
            "name": self.name,
            "memories": self.memories,
            "tick_manifested": self.tick_manifested,
        }


@dataclass
class DreamState:
    """Tracks the simulation-wide dream state."""
    is_dreaming: bool = False
    dream_start_tick: int = 0
    dream_end_tick: int = 0
    last_dream_end_tick: int = 0         # when the last dream ended (for interval calc)
    total_dream_cycles: int = 0
    ghosts: list[GhostManifestation] = field(default_factory=list)
    lucid_agent_ids: list[int] = field(default_factory=list)
    dream_content: list[str] = field(default_factory=list)  # collective unconscious narrative

    def to_dict(self) -> dict:
        return {
            "is_dreaming": self.is_dreaming,
            "dream_start_tick": self.dream_start_tick,
            "dream_end_tick": self.dream_end_tick,
            "last_dream_end_tick": self.last_dream_end_tick,
            "total_dream_cycles": self.total_dream_cycles,
            "ghosts": [g.to_dict() for g in self.ghosts],
            "lucid_agent_ids": list(self.lucid_agent_ids),
            "dream_content": list(self.dream_content),
        }

    @classmethod
    def from_dict(cls, d: dict) -> DreamState:
        state = cls(
            is_dreaming=d.get("is_dreaming", False),
            dream_start_tick=d.get("dream_start_tick", 0),
            dream_end_tick=d.get("dream_end_tick", 0),
            last_dream_end_tick=d.get("last_dream_end_tick", 0),
            total_dream_cycles=d.get("total_dream_cycles", 0),
            lucid_agent_ids=d.get("lucid_agent_ids", []),
            dream_content=d.get("dream_content", []),
        )
        for g in d.get("ghosts", []):
            state.ghosts.append(GhostManifestation(
                source_agent_id=g["source_agent_id"],
                x=g["x"], y=g["y"],
                name=g["name"],
                memories=g.get("memories", []),
                tick_manifested=g.get("tick_manifested", 0),
            ))
        return state


def _should_start_dream(dream_state: DreamState, tick: int, cfg) -> bool:
    """Check if a new dream cycle should begin."""
    if dream_state.is_dreaming:
        return False
    dream_cfg = getattr(cfg, 'dreams', None)
    interval = getattr(dream_cfg, 'cycle_interval', 50) if dream_cfg else 50
    ticks_since_last = tick - dream_state.last_dream_end_tick
    return ticks_since_last >= interval


def _start_dream(dream_state: DreamState, tick: int, cfg) -> None:
    """Activate dream state."""
    dream_cfg = getattr(cfg, 'dreams', None)
    duration = getattr(dream_cfg, 'duration', 5) if dream_cfg else 5
    dream_state.is_dreaming = True
    dream_state.dream_start_tick = tick
    dream_state.dream_end_tick = tick + duration
    dream_state.total_dream_cycles += 1
    dream_state.ghosts.clear()
    dream_state.lucid_agent_ids.clear()
    dream_state.dream_content.clear()


def _end_dream(dream_state: DreamState, tick: int) -> None:
    """Deactivate dream state."""
    dream_state.is_dreaming = False
    dream_state.last_dream_end_tick = tick
    dream_state.ghosts.clear()
    dream_state.lucid_agent_ids.clear()


def _generate_collective_unconscious(recent_events: list[dict], cfg) -> list[str]:
    """Generate dream content from recent simulation history.

    Wars replay as surreal combat, deaths as ghost encounters,
    suppressed awareness surfaces as bizarre glitches.
    """
    dream_cfg = getattr(cfg, 'dreams', None)
    max_events = getattr(dream_cfg, 'collective_unconscious_events', 5) if dream_cfg else 5

    dream_narratives = []
    sampled = recent_events[-max_events:] if recent_events else []

    for event in sampled:
        name = event.get("name", "").lower() if isinstance(event, dict) else str(event).lower()
        desc = event.get("description", "") if isinstance(event, dict) else str(event)

        if any(kw in name for kw in ("war", "battle", "combat", "conflict")):
            dream_narratives.append(
                f"Surreal combat vision: shadows of armies clash in impossible geometries. {desc}"
            )
        elif any(kw in name for kw in ("death", "died", "killed")):
            dream_narratives.append(
                f"Ghost encounter: a translucent figure whispers forgotten truths. {desc}"
            )
        elif any(kw in name for kw in ("awareness", "glitch", "anomaly", "red pill")):
            dream_narratives.append(
                f"Architecture dream: the walls of reality shimmer and reveal code beneath. {desc}"
            )
        elif any(kw in name for kw in ("breakthrough", "tech", "discovery")):
            dream_narratives.append(
                f"Prophetic vision: knowledge flows like water through impossible channels. {desc}"
            )
        else:
            dream_narratives.append(
                f"Abstract dream: fragments of memory swirl in a collective unconscious. {desc}"
            )

    return dream_narratives


def _manifest_ghosts(dead_agents: list[Agent], dream_state: DreamState,
                     tick: int, cfg) -> list[GhostManifestation]:
    """Manifest recently dead agents as ghosts during dream state."""
    dream_cfg = getattr(cfg, 'dreams', None)
    ghost_max_age = getattr(dream_cfg, 'ghost_max_age', 20) if dream_cfg else 20
    manifest_chance = getattr(dream_cfg, 'ghost_manifest_chance', 0.3) if dream_cfg else 0.3
    max_ghosts = getattr(dream_cfg, 'max_ghosts', 10) if dream_cfg else 10

    new_ghosts = []
    existing_source_ids = {g.source_agent_id for g in dream_state.ghosts}

    for dead in dead_agents:
        if len(dream_state.ghosts) + len(new_ghosts) >= max_ghosts:
            break
        if dead.source_agent_id if hasattr(dead, 'source_agent_id') else dead.id in existing_source_ids:
            continue
        # Check how recently they died (approximate from last memory tick)
        death_tick = 0
        for mem in reversed(dead.memory):
            if "Died" in mem.get("event", ""):
                death_tick = mem.get("tick", 0)
                break
        if death_tick == 0 or (tick - death_tick) > ghost_max_age:
            continue
        if random.random() > manifest_chance:
            continue

        # Manifest ghost at death location
        ghost_memories = [m.get("event", "") for m in dead.memory[-3:]]
        ghost = GhostManifestation(
            source_agent_id=dead.id,
            x=dead.x, y=dead.y,
            name=f"Ghost of #{dead.id} (gen {dead.generation})",
            memories=ghost_memories,
            tick_manifested=tick,
        )
        new_ghosts.append(ghost)
        dream_state.ghosts.append(ghost)

    return new_ghosts


def _process_lucid_dreaming(agents: list[Agent], dream_state: DreamState,
                            tick: int, cfg) -> list[int]:
    """Process lucid dreaming for aware agents.

    Consciousness phases gate lucidity:
    - bicameral/questioning: cannot become lucid
    - self_aware: low chance
    - lucid: moderate chance
    - recursive: high chance (maximum dream lucidity)

    Lucid agents can communicate across entire map, access hidden memories,
    and perceive simulation architecture. Lucidity permanently boosts awareness.
    """
    dream_cfg = getattr(cfg, 'dreams', None)
    awareness_threshold = getattr(dream_cfg, 'lucid_awareness_threshold', 0.5) if dream_cfg else 0.5
    base_chance = getattr(dream_cfg, 'lucid_base_chance', 0.3) if dream_cfg else 0.3
    awareness_boost = getattr(dream_cfg, 'lucid_awareness_boost', 0.02) if dream_cfg else 0.02
    memory_unlock_count = getattr(dream_cfg, 'lucid_memory_unlock_count', 3) if dream_cfg else 3

    # Phase-specific lucidity multipliers
    phase_multipliers = {
        "bicameral": 0.0,       # cannot become lucid
        "questioning": 0.0,     # cannot become lucid
        "self_aware": 0.3,      # low chance
        "lucid": 0.7,           # moderate chance (name is apt)
        "recursive": 1.0,       # maximum dream lucidity
    }

    newly_lucid = []
    for agent in agents:
        if not agent.alive or agent.is_sentinel:
            continue
        if agent.awareness < awareness_threshold:
            continue
        phase_mult = phase_multipliers.get(agent.consciousness_phase, 0.0)
        if phase_mult <= 0.0:
            continue

        # Lucidity chance: base * phase_mult * awareness * curiosity * reality_testing
        chance = (base_chance * phase_mult * agent.awareness
                  * agent.traits.curiosity * agent.reality_testing)
        if random.random() > chance:
            continue

        # Agent becomes lucid!
        newly_lucid.append(agent.id)
        if agent.id not in dream_state.lucid_agent_ids:
            dream_state.lucid_agent_ids.append(agent.id)

        # Permanent awareness boost from lucid dreaming
        agent.awareness = min(1.0, agent.awareness + awareness_boost)

        # Access hidden memories: unlock compressed memories
        if agent.memory_summary and memory_unlock_count > 0:
            agent.add_memory(tick,
                             "LUCID DREAM: Recovered lost memories from the collective unconscious")

        # Perceive simulation architecture
        if agent.consciousness_phase in ("lucid", "recursive"):
            agent.add_memory(tick,
                             "LUCID DREAM: Saw the architecture of the simulation — "
                             "grids within grids, tick counters, utility functions guiding every step")

        # Chronicle entry
        agent.add_chronicle(tick, "phase_transition",
                            f"Became lucid during dream cycle #{dream_state.total_dream_cycles}",
                            dream_cycle=dream_state.total_dream_cycles)

    return newly_lucid


def process_dreams(agents: list[Agent], all_agents: list[Agent],
                   dream_state: DreamState, tick: int, cfg,
                   recent_events: list[dict] = None) -> dict:
    """Main dream system entry point. Called from engine.py tick loop.

    Args:
        agents: alive agents in the simulation
        all_agents: all agents (including dead) for ghost manifestation
        dream_state: persistent dream state
        tick: current simulation tick
        cfg: simulation config
        recent_events: recent event log for collective unconscious

    Returns:
        dict of dream stats for the tick
    """
    stats = {
        "is_dreaming": dream_state.is_dreaming,
        "dream_cycle": dream_state.total_dream_cycles,
        "ghosts_active": len(dream_state.ghosts),
        "lucid_agents": len(dream_state.lucid_agent_ids),
        "dream_started": False,
        "dream_ended": False,
    }

    # Check if dream should start
    if not dream_state.is_dreaming and _should_start_dream(dream_state, tick, cfg):
        _start_dream(dream_state, tick, cfg)
        stats["dream_started"] = True

        # Generate collective unconscious content
        dream_state.dream_content = _generate_collective_unconscious(
            recent_events or [], cfg
        )
        stats["dream_content"] = dream_state.dream_content

    # Process active dream
    if dream_state.is_dreaming:
        # Check if dream should end
        if tick >= dream_state.dream_end_tick:
            _end_dream(dream_state, tick)
            stats["dream_ended"] = True
            stats["is_dreaming"] = False
            return stats

        # Manifest ghosts from recently dead agents
        dead_agents = [a for a in all_agents if not a.alive]
        new_ghosts = _manifest_ghosts(dead_agents, dream_state, tick, cfg)
        stats["new_ghosts"] = len(new_ghosts)
        stats["ghosts_active"] = len(dream_state.ghosts)

        # Process lucid dreaming
        newly_lucid = _process_lucid_dreaming(agents, dream_state, tick, cfg)
        stats["newly_lucid"] = len(newly_lucid)
        stats["lucid_agents"] = len(dream_state.lucid_agent_ids)

    return stats


def get_dream_movement_multiplier(dream_state: DreamState, cfg) -> float:
    """Get the movement speed multiplier during dreams.
    Called from engine.py when computing agent moves."""
    if not dream_state.is_dreaming:
        return 1.0
    dream_cfg = getattr(cfg, 'dreams', None)
    return getattr(dream_cfg, 'movement_range_multiplier', 2.0) if dream_cfg else 2.0


def get_dream_terrain_reduction(dream_state: DreamState, cfg) -> float:
    """Get the terrain harshness reduction factor during dreams.
    Returns a multiplier (0.5 means terrain effects halved)."""
    if not dream_state.is_dreaming:
        return 1.0
    dream_cfg = getattr(cfg, 'dreams', None)
    return getattr(dream_cfg, 'terrain_effect_reduction', 0.5) if dream_cfg else 0.5
