"""
Agency — trait-driven utility function for movement + LLM protagonist decisions.
"""
from __future__ import annotations

import logging
import math
import random
from collections import defaultdict
from typing import Optional

from src.agents import Agent
from src.emotions import get_emotion_utility_modifiers
from src.world import ResourceGrid

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════
# FREE WILL GRADIENT
# ═══════════════════════════════════════════════════

def compute_free_will_index(agent: Agent) -> float:
    """Compute the free will index based on consciousness phase.

    Returns 0.0 (fully deterministic) to 1.0 (full free will).
    Maps directly to consciousness phases:
      bicameral=0.0, questioning=0.15, self_aware=0.4, lucid=0.7, recursive=1.0
    """
    phase_scores = {
        "bicameral": 0.0,
        "questioning": 0.15,
        "self_aware": 0.4,
        "lucid": 0.7,
        "recursive": 1.0,
    }
    base = phase_scores.get(agent.consciousness_phase, 0.0)
    # Recursive agents with high depth get even stronger free will signal
    if agent.consciousness_phase == "recursive" and agent.recursive_depth > 0:
        base = min(1.0, base + agent.recursive_depth * 0.02)
    agent.free_will_index = round(base, 4)
    return agent.free_will_index


def _apply_free_will(agent: Agent, directions: list, best_dx: float,
                     best_dy: float, best_util: float,
                     utilities: list[tuple[float, float, float]],
                     speed: float) -> tuple[float, float]:
    """Apply consciousness-gated free will overrides to the optimal move.

    Consciousness phases gate deviation:
    - bicameral: no deviation (fully deterministic, utility always picks optimal)
    - questioning: rare random deviations (small noise)
    - self_aware: can choose suboptimal for reasons (loyalty, emotion override)
    - lucid: can act against utility (self-sacrifice, deliberate suboptimal)
    - recursive: can rewrite utility weights (pick any action)

    Returns (dx, dy) after free will processing.
    """
    phase = agent.consciousness_phase

    if phase == "bicameral":
        # Fully deterministic — no deviation at all
        return best_dx, best_dy

    if phase == "questioning":
        # Rare random deviations — 10% chance of slight noise
        if random.random() < 0.10:
            alt_dirs = [(dx, dy, u) for dx, dy, u in utilities
                        if (dx, dy) != (best_dx, best_dy) and u > best_util * 0.5]
            if alt_dirs:
                pick = random.choice(alt_dirs)
                return pick[0], pick[1]
        return best_dx, best_dy

    if phase == "self_aware":
        # Can choose suboptimal for emotional/loyalty reasons
        # Higher emotional intensity = more likely to deviate
        emo_intensity = agent.emotional_intensity
        deviation_chance = 0.15 + emo_intensity * 0.25
        if random.random() < deviation_chance:
            # Pick a reasonably good alternative (top 3 actions)
            sorted_utils = sorted(utilities, key=lambda x: -x[2])
            candidates = sorted_utils[:3]
            pick = random.choice(candidates)
            return pick[0], pick[1]
        return best_dx, best_dy

    if phase == "lucid":
        # Can act against utility — self-sacrifice, reject optimal
        deviation_chance = 0.25 + agent.awareness * 0.15
        if random.random() < deviation_chance:
            # Can choose any action, including worst
            pick = random.choice(utilities)
            return pick[0], pick[1]
        return best_dx, best_dy

    if phase == "recursive":
        # Can rewrite own utility weights — effectively unconstrained
        # Always applies own judgment; 40% chance of deliberate override
        if random.random() < 0.40:
            # Weighted random: higher-utility actions still preferred but not dominant
            total = sum(max(0.01, u + 1.0) for _, _, u in utilities)
            r = random.uniform(0, total)
            cumulative = 0.0
            for dx, dy, u in utilities:
                cumulative += max(0.01, u + 1.0)
                if cumulative >= r:
                    return dx, dy
            return best_dx, best_dy
        return best_dx, best_dy

    return best_dx, best_dy


class SpatialIndex:
    """Grid-based spatial index for O(1) neighbor lookups instead of O(n).
    Divides [0,1] x [0,1] into cells and indexes agents by cell."""

    def __init__(self, cell_size: float = 0.1):
        self.cell_size = cell_size
        self.grid_dim = max(1, int(1.0 / cell_size))
        self.cells: dict[tuple[int, int], list[Agent]] = defaultdict(list)
        self._bond_ids: dict[int, set[int]] = {}

    def build(self, agents: list[Agent]):
        """Rebuild the index from a list of alive agents."""
        self.cells.clear()
        self._bond_ids.clear()
        for a in agents:
            if not a.alive:
                continue
            cx = min(self.grid_dim - 1, int(a.x / self.cell_size))
            cy = min(self.grid_dim - 1, int(a.y / self.cell_size))
            self.cells[(cx, cy)].append(a)
            self._bond_ids[a.id] = {b.target_id for b in a.bonds}

    def get_nearby(self, x: float, y: float, radius: float) -> list[Agent]:
        """Get all agents within radius of (x, y)."""
        cx = int(x / self.cell_size)
        cy = int(y / self.cell_size)
        cells_to_check = max(1, int(radius / self.cell_size) + 1)
        result = []
        r2 = radius * radius
        for dx in range(-cells_to_check, cells_to_check + 1):
            for dy in range(-cells_to_check, cells_to_check + 1):
                for agent in self.cells.get((cx + dx, cy + dy), []):
                    ddx = agent.x - x
                    ddy = agent.y - y
                    if ddx * ddx + ddy * ddy <= r2:
                        result.append(agent)
        return result


# Module-level spatial index, rebuilt once per tick batch
_spatial_index = SpatialIndex(cell_size=0.1)


def build_spatial_index(agents: list[Agent], cfg=None):
    """Rebuild the spatial index. Call once before processing all agent moves."""
    global _spatial_index
    cell_size = getattr(cfg.agency, 'spatial_cell_size', 0.1) if cfg else 0.1
    if _spatial_index.cell_size != cell_size:
        _spatial_index = SpatialIndex(cell_size=cell_size)
    _spatial_index.build(agents)


def _update_goal(agent: Agent, cfg):
    """Update agent's persistent goal based on current needs."""
    # Increment goal timer
    if agent.current_goal != "NONE":
        agent.goal_ticks += 1
        # Goals expire after 20 ticks
        if agent.goal_ticks > 20:
            agent.current_goal = "NONE"
            agent.goal_target_pos = None
            agent.goal_target_id = None
            agent.goal_ticks = 0
            return

    # Don't override active goals (except NONE)
    if agent.current_goal != "NONE":
        return

    # Priority: FLEE > FIND_MATE > REACH_RESOURCE > JOIN_FACTION
    if agent.health < 0.3:
        agent.current_goal = "FLEE"
        agent.goal_ticks = 0
    elif (agent.phase == "adult"
          and not any(b.bond_type == "mate" for b in agent.bonds)
          and agent.traits.sociability > 0.4):
        agent.current_goal = "FIND_MATE"
        agent.goal_ticks = 0
    elif agent.wealth < 0.2 and agent.skills.get("survival", 0) > 0.3:
        agent.current_goal = "REACH_RESOURCE"
        agent.goal_ticks = 0
    elif agent.faction_id is None and len(agent.bonds) > 2 and agent.phase == "adult":
        agent.current_goal = "JOIN_FACTION"
        agent.goal_ticks = 0


def compute_move(agent: Agent, grid: ResourceGrid, alive_agents: list[Agent],
                 cfg) -> tuple[float, float]:
    """Compute the best move for an agent using utility-weighted evaluation.

    Integrates:
    - Emotion modifiers (fear → safety seeking, grief → paralysis, etc.)
    - Protagonist LLM priority overrides (thoughts bias utility weights)
    - Spatial indexing for O(1) neighbor lookups
    """
    if not agent.alive:
        return agent.x, agent.y

    # ── Update persistent goal ──
    _update_goal(agent, cfg)

    weights = cfg.agency.utility_weights
    speed = cfg.agency.movement_speed

    # ── Emotion-modified weights ──
    emo_mods = get_emotion_utility_modifiers(agent, cfg)
    w_resource = weights.resource_pull + emo_mods.get("resource_pull", 0)
    w_social = weights.social_pull + emo_mods.get("social_pull", 0)
    w_curiosity = weights.curiosity_pull + emo_mods.get("curiosity_pull", 0)
    w_safety = weights.safety_penalty + emo_mods.get("safety_penalty", 0)
    w_inertia = weights.inertia + emo_mods.get("inertia", 0)

    # ── Protagonist LLM priority overrides ──
    if agent.is_protagonist and agent.inner_monologue:
        latest_priority = agent.inner_monologue[-1].get("priority", "survive")
        priority_boosts = {
            "survive": {"resource_pull": 0.15, "safety_penalty": 0.1},
            "explore": {"curiosity_pull": 0.25, "inertia": -0.1},
            "socialize": {"social_pull": 0.25, "curiosity_pull": -0.05},
            "reproduce": {"social_pull": 0.2, "resource_pull": 0.1},
            "teach": {"social_pull": 0.15, "inertia": 0.1},
        }
        boosts = priority_boosts.get(latest_priority, {})
        w_resource += boosts.get("resource_pull", 0)
        w_social += boosts.get("social_pull", 0)
        w_curiosity += boosts.get("curiosity_pull", 0)
        w_safety += boosts.get("safety_penalty", 0)
        w_inertia += boosts.get("inertia", 0)

    # Memory-based spatial preferences
    avoid_zones = []
    attract_zones = []
    for mem in agent.memory[-10:]:
        mx, my = mem.get("x"), mem.get("y")
        if mx is None or my is None:
            continue
        event = mem.get("event", "")
        if any(kw in event for kw in ("Fought", "Robbed", "Sentinel", "Died")):
            avoid_zones.append((mx, my))
        elif any(kw in event for kw in ("trade", "breakthrough", "friend")):
            attract_zones.append((mx, my))

    # ── Goal-based weight modifiers ──
    if agent.current_goal == "FLEE":
        w_safety += 0.5
    elif agent.current_goal == "FIND_MATE":
        w_social += 0.3
    elif agent.current_goal == "REACH_RESOURCE":
        w_resource += 0.3
    elif agent.current_goal == "JOIN_FACTION":
        w_social += 0.2

    # HUNT_ENEMY: find target for directional bias
    hunt_target = None
    if agent.current_goal == "HUNT_ENEMY" and agent.goal_target_id is not None:
        hunt_target = next(
            (a for a in alive_agents if a.id == agent.goal_target_id and a.alive),
            None,
        )
        if not hunt_target:
            # Target dead or gone, reset goal
            agent.current_goal = "NONE"
            agent.goal_target_id = None
            agent.goal_ticks = 0

    # PROTECT: check for bonded allies with low health nearby
    if agent.current_goal not in ("HUNT_ENEMY", "FLEE"):
        nearby_protect = _spatial_index.get_nearby(agent.x, agent.y, 0.15)
        for b in agent.bonds:
            if b.bond_type in ("mate", "friend") and b.strength > 0.7:
                ally = next((a for a in nearby_protect if a.id == b.target_id), None)
                if ally and ally.health < 0.4:
                    agent.current_goal = "PROTECT"
                    agent.goal_target_id = ally.id
                    agent.goal_ticks = 0
                    hunt_target = ally  # reuse for directional bias
                    break

    # Pre-compute bond target set for this agent
    bond_targets = _spatial_index._bond_ids.get(agent.id, set())

    # Pre-compute parent IDs if child
    parent_positions = {}
    if agent.phase in ("infant", "child"):
        for bond in agent.bonds:
            if bond.bond_type == "family" and bond.target_id in agent.parent_ids:
                parent_positions[bond.target_id] = bond.strength

    best_util = -999.0
    best_dx, best_dy = 0.0, 0.0
    all_utilities: list[tuple[float, float, float]] = []  # (dx, dy, utility)

    # Evaluate 8 directions + stay
    directions = [
        (0, 0), (speed, 0), (-speed, 0), (0, speed), (0, -speed),
        (speed, speed), (speed, -speed), (-speed, speed), (-speed, -speed),
    ]

    for dx, dy in directions:
        nx = max(0.0, min(1.0, agent.x + dx))
        ny = max(0.0, min(1.0, agent.y + dy))
        target_cell = grid.get_cell(nx, ny)
        utility = 0.0

        # Resource pull — prefer richer cells
        resource_pull = target_cell.effective_resources * agent.traits.resilience
        utility += resource_pull * w_resource

        # Social pull — use spatial index for O(1) lookup
        nearby = _spatial_index.get_nearby(nx, ny, 0.1)
        agents_near_target = 0
        friendly_near = 0
        for other in nearby:
            if other.id == agent.id:
                continue
            agents_near_target += 1
            if other.id in bond_targets:
                friendly_near += 1

        social_value = min(agents_near_target, 5) / 5.0 * agent.traits.sociability
        if friendly_near > 0:
            social_value += 0.2
        utility += social_value * w_social

        # Curiosity pull
        move_dist = math.sqrt(dx * dx + dy * dy)
        explore_value = move_dist / (speed * 1.42) * agent.traits.curiosity
        utility += explore_value * w_curiosity

        # Safety penalty — avoid overcrowded cells
        if target_cell.pressure > 1.0:
            overcrowd_penalty = (target_cell.pressure - 1.0) * 0.5
            utility -= overcrowd_penalty * w_safety

        # Inertia
        if dx == 0 and dy == 0:
            utility += w_inertia

        # Phase-specific: children stay near parents
        if parent_positions:
            for other in nearby:
                if other.id in parent_positions:
                    utility += 0.3 * parent_positions[other.id]

        # Memory spatial modifier
        if avoid_zones or attract_zones:
            mem_mod = 0.0
            for zx, zy in avoid_zones:
                d = math.sqrt((nx - zx)**2 + (ny - zy)**2)
                if d < 0.15:
                    mem_mod -= 0.1 * (1.0 - d / 0.15)
            for zx, zy in attract_zones:
                d = math.sqrt((nx - zx)**2 + (ny - zy)**2)
                if d < 0.15:
                    mem_mod += 0.05 * (1.0 - d / 0.15)
            utility += mem_mod

        # Directional bias toward HUNT_ENEMY / PROTECT target
        if hunt_target:
            curr_dist = math.sqrt((agent.x - hunt_target.x) ** 2 + (agent.y - hunt_target.y) ** 2)
            new_dist = math.sqrt((nx - hunt_target.x) ** 2 + (ny - hunt_target.y) ** 2)
            if new_dist < curr_dist:
                utility += 0.4  # strong bias toward target

        all_utilities.append((dx, dy, utility))

        if utility > best_util:
            best_util = utility
            best_dx, best_dy = dx, dy

    # ── Free Will Gradient: consciousness-gated deviation ──
    compute_free_will_index(agent)

    # Record the purely optimal (predicted) action before any overrides
    predicted_dx, predicted_dy = best_dx, best_dy

    # Apply free will override based on consciousness phase
    # This replaces the old boldness-only override for conscious agents
    if agent.consciousness_phase != "bicameral":
        best_dx, best_dy = _apply_free_will(
            agent, directions, best_dx, best_dy, best_util,
            all_utilities, speed,
        )
    else:
        # Bicameral: no boldness override, no noise — fully deterministic
        pass

    # Boldness: only applies to non-bicameral agents (bicameral are deterministic)
    if agent.consciousness_phase != "bicameral":
        if agent.traits.boldness > 0.6 and random.random() < (agent.traits.boldness - 0.5) * 0.3:
            alt_dirs = [(ddx, ddy) for ddx, ddy in directions if (ddx, ddy) != (best_dx, best_dy)]
            if alt_dirs:
                best_dx, best_dy = random.choice(alt_dirs)

    # Add slight random noise (suppressed for bicameral — they are deterministic)
    if agent.consciousness_phase == "bicameral":
        noise = 0.0
    else:
        noise = speed * 0.1
    new_x = max(0.0, min(1.0, agent.x + best_dx + (random.gauss(0, noise) if noise > 0 else 0)))
    new_y = max(0.0, min(1.0, agent.y + best_dy + (random.gauss(0, noise) if noise > 0 else 0)))

    # Record predicted vs actual for free will visualization
    predicted_x = max(0.0, min(1.0, agent.x + predicted_dx))
    predicted_y = max(0.0, min(1.0, agent.y + predicted_dy))
    agent._last_predicted_action = (round(predicted_x, 4), round(predicted_y, 4))
    agent._last_actual_action = (round(new_x, 4), round(new_y, 4))

    return new_x, new_y


def auto_select_protagonists(agents: list[Agent], cfg, current_protagonists: list[int]) -> list[int]:
    """Select up to max_count protagonists based on weighted criteria."""
    prot_cfg = cfg.agency.protagonists
    alive = [a for a in agents if a.alive and a.phase == "adult"]
    if not alive:
        return current_protagonists[:prot_cfg.max_count]

    # Keep existing valid protagonists
    valid_existing = [
        pid for pid in current_protagonists
        if any(a.id == pid and a.alive for a in agents)
    ]

    if len(valid_existing) >= prot_cfg.max_count:
        return valid_existing[:prot_cfg.max_count]

    # Score candidates
    weights = prot_cfg.auto_weights
    scored = []
    for a in alive:
        if a.id in valid_existing:
            continue
        score = (
            a.generation * weights.generation +
            len(a.bonds) / 8.0 * weights.bonds +
            a.intelligence * weights.intelligence +
            (1.0 - abs(a.age - 35) / 35.0) * weights.age  # prefer mid-life
        )
        scored.append((a.id, score))

    scored.sort(key=lambda x: -x[1])
    needed = prot_cfg.max_count - len(valid_existing)
    new_picks = [pid for pid, _ in scored[:needed]]

    # Mark agents
    all_prot = valid_existing + new_picks
    for a in agents:
        a.is_protagonist = a.id in all_prot

    return all_prot


def _fallback_thought(agent: Agent, grid: ResourceGrid,
                      nearby: list[Agent], tick: int) -> dict:
    """Generate a rich template-based inner monologue when no LLM is available."""
    import random
    # Seed with tick + agent id so each call produces unique output
    _rng = random.Random(tick * 1000 + agent.id + len(agent.inner_monologue))

    cell = grid.get_cell(agent.x, agent.y)
    bond_count = len(agent.bonds)
    mate_bonds = [b for b in agent.bonds if b.bond_type == "mate"]
    friend_bonds = [b for b in agent.bonds if b.bond_type == "friend"]
    rival_bonds = [b for b in agent.bonds if b.bond_type == "rival"]
    child_count = len(agent.child_ids)
    top_skill = max(agent.skills, key=agent.skills.get) if agent.skills else "survival"
    top_val = agent.skills.get(top_skill, 0)
    dom_emo = agent.dominant_emotion or "neutral"
    recent_mems = [m["event"] for m in agent.memory[-5:]]

    # Determine priority from agent state
    if agent.health < 0.3:
        priority = "survive"
    elif agent.phase in ("adolescent", "adult") and not mate_bonds and agent.traits.sociability > 0.4:
        priority = "reproduce"
    elif agent.traits.curiosity > 0.6 and cell.effective_resources > 0.5:
        priority = "explore"
    elif bond_count > 2 or agent.traits.sociability > 0.6:
        priority = "socialize"
    elif agent.phase == "elder" and child_count > 0:
        priority = "teach"
    else:
        priority = _rng.choice(["survive", "explore"])

    # ── Build a multi-layered thought ──
    paragraphs = []

    # === Opening: emotional state + situation awareness ===
    terrain_desc = {"plains": "open grasslands", "forest": "dense forest", "mountains": "rocky highlands", "coast": "the shoreline"}.get(cell.terrain, "this place")

    if agent.health < 0.2:
        paragraphs.append(_rng.choice([
            f"I'm dying. I can feel it in my bones — every breath costs me something I can't get back. The {terrain_desc} blurs around me. If this is the end, I wish someone would remember my name.",
            f"My hands are shaking. I can barely stand. The hunger is a living thing inside me now, gnawing, relentless. I've fought so hard to survive in these {terrain_desc}, but my body is betraying me.",
            f"Blood in my mouth. Stars in my vision. The {terrain_desc} stretches on forever and I don't know if I'll see another dawn. I think about everyone I've known and wonder if any of them are looking for me.",
        ]))
    elif agent.health < 0.4:
        paragraphs.append(_rng.choice([
            f"I'm hurting, but I refuse to stop. The {terrain_desc} doesn't care about my pain — it just keeps going, and so will I. I've survived worse. Haven't I?",
            f"Every muscle aches. I press my hand against my ribs and count my breaths. The {terrain_desc} is quiet today, as if waiting to see whether I'll make it through another cycle.",
        ]))
    elif dom_emo == "happiness" and agent.health > 0.6:
        paragraphs.append(_rng.choice([
            f"For once, things feel... right. Standing here in the {terrain_desc}, I feel something I haven't felt in a long time: hope. Maybe even peace. The world is harsh, but today it's beautiful.",
            f"I caught myself smiling. When did that start? The {terrain_desc} is alive with possibility, and for the first time in many cycles, I feel like I'm not just surviving — I'm living.",
        ]))
    elif dom_emo == "fear":
        paragraphs.append(_rng.choice([
            f"Something feels wrong. I can't explain it. The {terrain_desc} looks the same as yesterday, but there's a tension in the air, like the world is holding its breath before a storm.",
            f"I keep looking over my shoulder. The shadows in the {terrain_desc} seem deeper than they should be. I don't know what I'm afraid of, exactly. That might be the worst part.",
        ]))
    elif dom_emo == "anger":
        paragraphs.append(_rng.choice([
            f"The rage burns slow and constant, like embers that won't die. I look out across the {terrain_desc} and think about everything that's been taken from me. Everything I've had to endure.",
            f"I clench my fists until my knuckles go white. This world owes me nothing, I know that. But the unfairness of it — the sheer cruelty of how things work here in the {terrain_desc} — it makes my blood boil.",
        ]))
    elif dom_emo == "grief":
        paragraphs.append(_rng.choice([
            f"The grief comes in waves. I'll be fine for a while, moving through the {terrain_desc} like nothing happened, and then it hits — a memory, a scent, a familiar shape in the distance — and I'm drowning again.",
            f"I sit alone in the {terrain_desc} and let the sadness wash over me. They say time heals. I'm not sure I believe that. Some wounds just become part of you.",
        ]))
    else:
        paragraphs.append(_rng.choice([
            f"Another cycle in the {terrain_desc}. I watch the world turn and wonder where I fit in all of this. I'm generation {agent.generation} — how many came before me? How many will come after?",
            f"The {terrain_desc} stretches out before me. I've been alive for {agent.age} cycles now. Some days that feels like forever. Other days it feels like I just opened my eyes for the first time.",
        ]))

    # === Middle: relationships + social context ===
    if mate_bonds:
        partner = mate_bonds[0]
        if partner.strength > 0.7:
            paragraphs.append(_rng.choice([
                f"#{partner.target_id} is the reason I keep going. When everything else falls apart, that bond holds. I'd cross the entire map for them. I think they know that.",
                f"I think about #{partner.target_id} constantly. Our bond is the strongest thing in my world — stronger than hunger, stronger than fear. Whatever comes next, we face it together.",
            ]))
        else:
            paragraphs.append(_rng.choice([
                f"Things with #{partner.target_id} feel... uncertain lately. The bond is there, but it's fraying. I want to hold on, but maybe wanting isn't enough.",
                f"#{partner.target_id} and I — are we drifting? I can't tell anymore. Bonds are strange things. They form so fast and then time tests them in ways I never expected.",
            ]))
    elif bond_count == 0:
        paragraphs.append(_rng.choice([
            "I am completely, utterly alone. No bonds. No one to call friend or rival or lover. Just me and the endless terrain. Sometimes I speak out loud just to hear a voice — even if it's only my own.",
            "Isolation is a weight that grows heavier each cycle. I see others in the distance, clusters of agents with their bonds and alliances, and I wonder what's wrong with me. Why can't I connect?",
            "No bonds. The word echoes: *alone*. I've started talking to myself, narrating my actions like someone might be listening. Nobody is. But the habit keeps the silence from swallowing me whole.",
        ]))
    elif friend_bonds and not mate_bonds:
        f_id = friend_bonds[0].target_id
        paragraphs.append(_rng.choice([
            f"#{f_id} has become someone I trust. In a world where bonds break as easily as they form, friendship is a small miracle. I hope they feel the same.",
            f"I value what I have with #{f_id}. We watch each other's backs. It's not love, not rivalry — it's something quieter and maybe more durable. Companionship.",
        ]))

    if rival_bonds:
        r_id = rival_bonds[0].target_id
        paragraphs.append(_rng.choice([
            f"#{r_id}. Even thinking the number makes my jaw tighten. This rivalry isn't just competition — it's personal. One of us will outlast the other. I intend for it to be me.",
            f"I can't stop thinking about #{r_id}. Every achievement of theirs feels like a failure of mine. Is this rivalry making me stronger, or is it poisoning me from the inside?",
        ]))

    if nearby:
        strangers_near = [n for n in nearby if not agent.has_bond_with(n.id)]
        if strangers_near and len(strangers_near) > 3:
            paragraphs.append(f"This area is getting crowded. {len(strangers_near)} strangers within reach. Resources don't stretch forever — someone will have to move. I hope it's not me.")
        elif strangers_near and agent.traits.sociability > 0.5:
            paragraphs.append("New faces nearby. Part of me wants to reach out. A bond with the right agent could change everything. But trust is expensive, and betrayal costs more.")

    # === Children / legacy ===
    if child_count > 3:
        paragraphs.append(_rng.choice([
            f"I have {child_count} children in this world. {child_count} lives that carry pieces of me forward. Whatever happens to me, I've already changed the future. That thought is the closest thing I have to immortality.",
            f"{child_count} children. Some days the weight of that responsibility crushes me. Other days it lifts me up. They are my greatest achievement and my deepest vulnerability.",
        ]))
    elif child_count > 0 and agent.phase in ("adult", "elder"):
        paragraphs.append(f"My {'child' if child_count == 1 else f'{child_count} children'} — I wonder what kind of world I'm leaving them. Better than the one I inherited? I'm not sure. But I'm trying.")

    # === Skills / identity ===
    if top_val > 0.7:
        skill_musings = {
            "logic": "My mind is my sharpest tool. Where others see chaos, I see structure — patterns nested in patterns. Sometimes I wonder if the world itself follows rules that no one else has noticed yet.",
            "creativity": "The urge to create burns in me like a fever. I see the raw materials of this world and my mind reshapes them into something new. Art, invention, possibility — it all starts with imagining what doesn't exist yet.",
            "social": "I read people the way others read terrain. Every glance, every hesitation, every shift in posture tells a story. This gift — if that's what it is — makes me a bridge between souls. Or a manipulator. The line is thinner than I'd like.",
            "survival": "The land has taught me everything that matters. Where to find food when the ground looks barren. How to read the sky. When to run and when to stand. This knowledge is carved into my muscles and bones — no one can take it from me.",
            "tech": "I see mechanisms everywhere — in the way water flows, in how resources cluster, in the patterns of growth and decay. I can improve things. Make them work better. The world is a machine, and I'm slowly learning how to tune it.",
        }
        paragraphs.append(skill_musings.get(top_skill, f"I've mastered {top_skill} beyond what I thought possible. It defines me now — for better or worse."))

    # === Phase-specific reflection ===
    if agent.phase == "elder":
        paragraphs.append(_rng.choice([
            f"I feel the weight of {agent.age} cycles in every joint, every slow step. The young ones move so fast, so certain of themselves. I was like that once. Now I carry something they don't have yet: the memory of everything that went wrong, and the wisdom of having survived it.",
            "My time is running out — I can feel it the way you feel a storm approaching. Not with fear, exactly, but with a strange clarity. Everything matters more when you know it's ending. Every sunset. Every conversation. Every breath.",
        ]))
    elif agent.phase == "adolescent":
        paragraphs.append(_rng.choice([
            "The world is opening up and it's terrifying and exhilarating in equal measure. I'm not a child anymore, but I'm not sure what I am instead. Every day I discover something new about myself — not all of it good.",
            "I'm changing. I can feel it — not just my body, but my mind. Questions I never thought to ask are suddenly urgent. Who am I? What do I want? Why does any of this matter?",
        ]))
    elif agent.phase == "child":
        paragraphs.append(_rng.choice([
            "Everything is big and loud and confusing. The adults move with such purpose, like they know where they're going. I just try to keep up and not get left behind.",
            "I don't understand most of what happens around me, but I'm learning. Every cycle teaches me something new. The world is scary, but it's also full of wonders I haven't discovered yet.",
        ]))

    # === Closing: recent memory reaction ===
    if "Died" in str(recent_mems):
        paragraphs.append("I've seen death recently. It changes you. Makes the world feel thinner, like reality itself could tear if you pulled too hard.")
    elif any("breakthrough" in m.lower() for m in recent_mems):
        paragraphs.append("I witnessed something incredible — a breakthrough that changes everything. The air itself felt electric. We're not the same civilization we were before that moment.")
    elif any("whisper" in m.lower() for m in recent_mems):
        paragraphs.append("That whisper... I can't shake it. Words from nowhere, meant for me alone. Either I'm losing my mind, or something beyond this world is watching. Neither explanation brings me comfort.")
    elif agent.awareness > 0.5:
        paragraphs.append(_rng.choice([
            "There are moments — flickers, really — where the world seems... wrong. Like the texture of reality skips. I mentioned it to another agent once and they looked at me like I was insane. Maybe I am. But what if I'm not?",
            "I see through the cracks now. The patterns are too perfect, the rules too consistent. This world follows code, and I — I am part of that code. The question is whether knowing changes anything.",
        ]))

    # Pick a varied subset — always include first (emotional opener) + shuffle the rest
    if len(paragraphs) > 4:
        opener = paragraphs[0]
        rest = paragraphs[1:]
        _rng.shuffle(rest)
        paragraphs = [opener] + rest[:3]

    thought_text = " ".join(paragraphs[:4])
    thought = {"tick": tick, "thought": thought_text, "priority": priority}
    agent.inner_monologue.append(thought)
    return thought


def generate_protagonist_thought(agent: Agent, grid: ResourceGrid,
                                 nearby: list[Agent], narrator,
                                 tick: int, use_llm: bool = True) -> Optional[dict]:
    """Generate an inner monologue for a protagonist agent.

    Args:
        use_llm: If False, skip LLM and use fast templates (for batch runs).
                 If True, try LLM first then fall back to templates (for on-demand actions).
    """
    cell = grid.get_cell(agent.x, agent.y)
    bonds_desc = ", ".join(
        f"{b.bond_type}(#{b.target_id}, str={b.strength:.1f})"
        for b in agent.bonds[:5]
    )
    nearby_desc = ", ".join(
        f"#{n.id}({n.phase}, {'friend' if agent.has_bond_with(n.id) else 'stranger'})"
        for n in nearby[:5]
    )

    dom_emo = agent.dominant_emotion or "neutral"
    mate_bonds = [b for b in agent.bonds if b.bond_type == "mate"]
    rival_bonds = [b for b in agent.bonds if b.bond_type == "rival"]
    memory_context = agent.get_memory_context(recent_count=8)

    # Try LLM first (skipped during batch runs for performance)
    _used_llm = False
    if use_llm and narrator and narrator.enabled and narrator._ensure_connected():
        prompt = f"""You are {agent.protagonist_name or f'Agent #{agent.id}'}, a {agent.sex} {agent.phase} aged {agent.age} in a harsh civilization simulation. You are generation {agent.generation}.

PERSONALITY:
- Learning: {agent.traits.learning_rate:.2f} | Resilience: {agent.traits.resilience:.2f} | Curiosity: {agent.traits.curiosity:.2f}
- Sociability: {agent.traits.sociability:.2f} | Charisma: {agent.traits.charisma:.2f} | Aggression: {agent.traits.aggression:.2f}
- Dominant emotion right now: {dom_emo} | Trauma level: {agent.trauma:.2f}

SKILLS (best to worst): {sorted(agent.skills.items(), key=lambda x: -x[1])}
Health: {agent.health:.2f}/1.00 | Wealth: {agent.wealth:.1f} | Awareness: {agent.awareness:.2f}

LOCATION: {cell.terrain} terrain, resources {cell.effective_resources:.2f}, population pressure {cell.pressure:.1f}

RELATIONSHIPS:
- Bonds: {bonds_desc or 'none — completely alone'}
- Mate: {'#{}'.format(mate_bonds[0].target_id) + ' (str {:.1f})'.format(mate_bonds[0].strength) if mate_bonds else 'none'}
- Rivals: {', '.join(f'#{r.target_id}' for r in rival_bonds) if rival_bonds else 'none'}
- Children: {len(agent.child_ids)}
- Nearby right now: {nearby_desc or 'no one in sight'}

{memory_context}

{'MATRIX AWARENESS: You sense something is deeply wrong with reality. Glitches, patterns, déjà vu.' if agent.awareness > 0.3 else ''}
{'YOU HAVE BEEN REDPILLED: You know this world is a simulation. You see the code beneath the surface.' if agent.redpilled else ''}

Write a RICH inner monologue for this character. This is a journal entry / stream of consciousness.
- Reflect on your emotional state, your relationships, your fears and hopes
- Reference specific agents by their # number when thinking about bonds/rivals
- React to your recent memories
- Consider your mortality, your legacy, your place in the world
- Let your personality traits shape your voice (high aggression = fiercer, high curiosity = more questioning, etc.)
- Be literary and evocative, not clinical

Write 4-6 sentences of deeply personal inner thought. Then state your current priority.
Respond in JSON: {{"thought": "your inner monologue here", "priority": "survive|explore|socialize|reproduce|teach"}}"""

        system = "You are a literary AI writing deeply personal inner monologues for characters in a civilization simulation. Write with emotional depth, vivid imagery, and genuine introspection. Each character should feel like a real person wrestling with real concerns. Never be generic — anchor every thought in the character's specific circumstances, bonds, and memories."

        import json
        import re
        try:
            raw = narrator.active_provider.generate(system, prompt, temperature=0.9, max_tokens=400)
            if raw:
                text = raw.strip()

                # Clean thinking model artifacts
                # Remove "Thinking Process:", "Analyze the Request:", etc.
                thinking_patterns = [
                    r"^Thinking\s*Process:.*?\n\n",
                    r"^Analyze\s+the\s+Request:.*?\n\n",
                    r"^Let me\s+.*?\n\n",
                    r"^Okay,?\s+.*?\n\n",
                    r"^Alright,?\s+.*?\n\n",
                    r"^\*\*Analyze.*?\*\*.*?\n\n",
                ]
                for pattern in thinking_patterns:
                    text = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE).strip()

                # Try to parse as JSON
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    try:
                        data = json.loads(text[start:end])
                        thought_text = data.get("thought", "...")
                        priority = data.get("priority", "survive")
                        # Validate priority
                        if priority not in ("survive", "explore", "socialize", "reproduce", "teach"):
                            priority = "survive"
                        thought = {
                            "tick": tick,
                            "thought": thought_text,
                            "priority": priority,
                        }
                        agent.inner_monologue.append(thought)
                        _used_llm = True
                        return thought
                    except json.JSONDecodeError:
                        pass

                # No valid JSON — use cleaned text directly
                # Strip any remaining analysis/reasoning prefixes
                lines = text.split("\n")
                clean_lines = [line for line in lines if not any(
                    line.strip().startswith(p) for p in
                    ["*", "Analyze", "Role:", "Context:", "Personality:", "Emotional",
                     "Skills:", "Stats:", "Relationship", "Location:", "PERSONALITY",
                     "SKILLS", "LOCATION", "RELATIONSHIPS", "RECENT"]
                )]
                clean_text = "\n".join(clean_lines).strip()
                if not clean_text:
                    clean_text = text  # fallback to original if over-stripped

                thought = {
                    "tick": tick,
                    "thought": clean_text[:600],
                    "priority": "survive",
                }
                agent.inner_monologue.append(thought)
                _used_llm = True
                return thought
            else:
                logger.warning("LLM returned empty response for protagonist thought")
        except Exception as e:
            logger.warning(f"LLM protagonist thought failed: {e}")

    # Fallback: template-based thought
    return _fallback_thought(agent, grid, nearby, tick)