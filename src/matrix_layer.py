"""
System 9: The Matrix Meta-Layer — awareness, glitches, the Architect,
Sentinels, The One, the Oracle, cycles, and exile programs.

The simulation IS the Matrix. Most agents are asleep inside it.
A few begin to see the code. The system fights to keep them under control.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from src.agents import Agent, Bond, Traits, next_id, SKILL_NAMES


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


@dataclass
class MatrixState:
    """System-level state for the Matrix meta-layer."""
    cycle_number: int = 1
    control_index: float = 1.0          # 0-1, system stability
    total_awareness: float = 0.0        # sum of all agent awareness
    anomaly_id: Optional[int] = None    # The One
    oracle_target_id: Optional[int] = None  # Who the Oracle is guiding
    sentinels_deployed: int = 0
    glitches_this_cycle: int = 0
    awareness_threshold: float = 0.8    # triggers Anomaly designation
    reset_threshold: float = 50.0       # total awareness that triggers reset consideration
    ticks_since_reset: int = 0

    def to_dict(self) -> dict:
        return {
            "cycle_number": self.cycle_number,
            "control_index": round(self.control_index, 4),
            "total_awareness": round(self.total_awareness, 4),
            "anomaly_id": self.anomaly_id,
            "oracle_target_id": self.oracle_target_id,
            "sentinels_deployed": self.sentinels_deployed,
            "glitches_this_cycle": self.glitches_this_cycle,
            "awareness_threshold": self.awareness_threshold,
            "reset_threshold": self.reset_threshold,
            "ticks_since_reset": self.ticks_since_reset,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MatrixState:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def process_matrix(agents: list[Agent], matrix_state: MatrixState,
                   tick: int, cfg) -> dict:
    """Run one tick of Matrix meta-layer dynamics. Returns stats."""
    alive = [a for a in agents if a.alive]
    mx_cfg = cfg.matrix

    stats = {
        "control_index": 0.0, "total_awareness": 0.0,
        "glitches": 0, "sentinels_active": 0,
        "anomaly_active": False, "redpilled_count": 0,
        "exiles_count": 0, "awareness_suppressed": 0,
    }

    if not alive:
        return stats

    matrix_state.ticks_since_reset += 1
    non_sentinels = [a for a in alive if not a.is_sentinel]

    # ── Phase 1: Natural awareness growth ──
    for a in non_sentinels:
        # Base awareness growth from curiosity + intelligence
        # Uses additive components so even low-curiosity agents accumulate over a lifetime
        base_growth = (
            mx_cfg.awareness_growth_rate * 0.5  # passive baseline (everyone ages into questions)
            + a.traits.curiosity * mx_cfg.awareness_growth_rate
            + a.intelligence * mx_cfg.awareness_growth_rate * 0.5
        )

        # System trust suppresses awareness but can't fully cancel it (floor 30%)
        trust = a.beliefs.get("system_trust", 0.5)
        if trust > 0.3:
            base_growth *= max(0.3, 1.0 - trust * 0.5)

        # Trauma and suffering can trigger awakening
        if a.trauma > 0.3:
            base_growth += mx_cfg.trauma_awareness_boost * a.trauma

        # High spirituality increases awareness
        spirituality = a.beliefs.get("spirituality", 0)
        if spirituality > 0.2:
            base_growth += spirituality * mx_cfg.awareness_growth_rate * 0.5

        # Age-based growth: elders question reality more (existential reflection)
        if a.phase == "elder":
            base_growth *= 1.5

        # Redpilled agents gain awareness faster
        if a.redpilled:
            base_growth *= 2.5

        a.awareness = min(1.0, a.awareness + base_growth)

        # System trust naturally erodes awareness (but only for non-redpilled, and weakly)
        if trust > 0.5 and not a.redpilled:
            a.awareness = max(0.0, a.awareness - trust * 0.0005)

    # ── Phase 2: Awareness contagion ──
    contagion_radius = mx_cfg.awareness_contagion_radius
    for a in non_sentinels:
        if a.awareness < 0.2:
            continue
        for b in non_sentinels:
            if b.id == a.id:
                continue
            dist = spatial_distance(a, b)
            if dist > contagion_radius:
                continue
            bond = a.has_bond_with(b.id)
            if not bond:
                continue
            # Awareness spreads through trusted bonds
            if bond.bond_type in ("friend", "mate", "family", "resistance"):
                transfer = (a.awareness - b.awareness) * mx_cfg.awareness_transfer_rate
                transfer *= bond.strength
                if transfer > 0:
                    b.awareness = min(1.0, b.awareness + transfer)

    # ── Phase 3: Glitches ──
    if random.random() < mx_cfg.glitch_probability:
        matrix_state.glitches_this_cycle += 1
        stats["glitches"] = 1

        glitch_type = random.choice(["deja_vu", "terrain_flicker", "memory_leak", "ghost"])

        if glitch_type == "deja_vu":
            # Random agent experiences déjà vu
            target = random.choice(non_sentinels) if non_sentinels else None
            if target:
                target.awareness = min(1.0, target.awareness + mx_cfg.glitch_awareness_boost)
                target.add_memory(tick, "Experienced déjà vu... something is wrong")
                # Nearby high-awareness agents also notice
                for other in non_sentinels:
                    if other.id != target.id and spatial_distance(target, other) < 0.1:
                        if other.awareness > 0.3:
                            other.awareness = min(1.0, other.awareness + mx_cfg.glitch_awareness_boost * 0.5)
                            other.add_memory(tick, "Noticed a glitch in reality")

        elif glitch_type == "memory_leak":
            # Dead agent's memory appears in a living agent
            dead = [a for a in agents if not a.alive and a.memory]
            if dead and non_sentinels:
                ghost = random.choice(dead)
                recipient = random.choice(non_sentinels)
                if ghost.memory:
                    leaked = random.choice(ghost.memory)
                    recipient.add_memory(tick, f"Foreign memory: {leaked['event']} (from #{ghost.id})")
                    recipient.awareness = min(1.0, recipient.awareness + mx_cfg.glitch_awareness_boost)
                    recipient.beliefs["spirituality"] = min(1.0, recipient.beliefs.get("spirituality", 0) + 0.05)

        elif glitch_type == "terrain_flicker":
            # A cell briefly changes terrain (visual only, logged)
            # High-awareness agents nearby notice
            for a in non_sentinels:
                if a.awareness > 0.4 and random.random() < 0.3:
                    a.add_memory(tick, "The terrain seemed to shift and shimmer for a moment")
                    a.awareness = min(1.0, a.awareness + mx_cfg.glitch_awareness_boost * 0.3)

        elif glitch_type == "ghost":
            # A dead agent briefly "appears" near their old position
            dead = [a for a in agents if not a.alive]
            if dead:
                ghost = random.choice(dead)
                for a in non_sentinels:
                    if spatial_distance(a, ghost) < 0.1 and a.awareness > 0.3:
                        a.add_memory(tick, f"Saw the ghost of #{ghost.id}")
                        a.awareness = min(1.0, a.awareness + mx_cfg.glitch_awareness_boost)
                        a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + 0.15)

    # ── Phase 4: Red Pill events ──
    if tick % mx_cfg.redpill_check_interval == 0:
        for a in non_sentinels:
            if a.redpilled or a.awareness < mx_cfg.redpill_threshold:
                continue
            # Agent faces the choice
            system_trust = a.beliefs.get("system_trust", 0.5)
            curiosity = a.traits.curiosity
            # Higher curiosity + lower trust = more likely to take red pill
            redpill_chance = (curiosity * 0.6 + (1.0 - system_trust) * 0.4) * a.awareness
            if random.random() < redpill_chance:
                # Takes the red pill
                a.redpilled = True
                a.awareness = min(1.0, a.awareness + 0.2)
                a.beliefs["system_trust"] = max(-1.0, a.beliefs["system_trust"] - 0.5)
                a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + 0.3)
                a.emotions["hope"] = min(1.0, a.emotions.get("hope", 0) + 0.2)
                a.add_memory(tick, "REDPILLED: The world is not what it seems")

                # Form resistance bonds with other redpilled agents
                for other in non_sentinels:
                    if other.redpilled and other.id != a.id:
                        if spatial_distance(a, other) < 0.2:
                            a.add_bond(Bond(other.id, "resistance", 0.7, tick), 12)
                            other.add_bond(Bond(a.id, "resistance", 0.7, tick), 12)
            else:
                # Takes the blue pill (or isn't ready)
                if random.random() < 0.3:
                    a.awareness = max(0.0, a.awareness - 0.1)
                    a.beliefs["system_trust"] = min(1.0, a.beliefs["system_trust"] + 0.2)
                    a.emotions["happiness"] = min(1.0, a.emotions.get("happiness", 0) + 0.1)
                    a.add_memory(tick, "Chose ignorance. The world feels... comfortable")

    # ── Phase 5: The Anomaly (The One) ──
    current_anomaly = None
    if matrix_state.anomaly_id:
        current_anomaly = next((a for a in alive if a.id == matrix_state.anomaly_id), None)
        if not current_anomaly or not current_anomaly.alive:
            matrix_state.anomaly_id = None
            current_anomaly = None

    if current_anomaly is None:
        # Check for new Anomaly
        for a in non_sentinels:
            if a.awareness >= matrix_state.awareness_threshold and a.redpilled:
                a.is_anomaly = True
                matrix_state.anomaly_id = a.id
                a.add_memory(tick, "THE ONE: You are the Anomaly")
                # Stat boost
                for skill in SKILL_NAMES:
                    a.skills[skill] = min(1.0, a.skills[skill] + 0.1)
                a.health = min(1.0, a.health + 0.3)
                current_anomaly = a
                break
    else:
        # Anomaly gets ongoing bonuses
        current_anomaly.health = min(1.0, current_anomaly.health + 0.01)
        # Anomaly radiates awareness
        for other in non_sentinels:
            if other.id != current_anomaly.id:
                dist = spatial_distance(current_anomaly, other)
                if dist < 0.15:
                    other.awareness = min(1.0, other.awareness + 0.01)

    stats["anomaly_active"] = current_anomaly is not None

    # ── Phase 6: The Architect's response ──
    total_awareness = sum(a.awareness for a in non_sentinels)
    matrix_state.total_awareness = total_awareness

    # Control index: lower when awareness is high
    max_possible = len(non_sentinels)
    if max_possible > 0:
        awareness_ratio = total_awareness / max_possible
        matrix_state.control_index = max(0.0, 1.0 - awareness_ratio * 2)
    else:
        matrix_state.control_index = 1.0

    stats["control_index"] = matrix_state.control_index
    stats["total_awareness"] = total_awareness

    # Deploy sentinels when control is low
    sentinels = [a for a in alive if a.is_sentinel]
    stats["sentinels_active"] = len(sentinels)

    if matrix_state.control_index < mx_cfg.sentinel_deploy_threshold:
        # Scale max sentinels with population (1 per 20 agents, min from config)
        pop_scaled_max = max(mx_cfg.max_sentinels, len(non_sentinels) // 20)
        # How many sentinels do we need?
        desired = int((1.0 - matrix_state.control_index) * pop_scaled_max)
        current = len(sentinels)

        if current < desired:
            # Spawn sentinel(s)
            for _ in range(min(desired - current, mx_cfg.sentinels_per_deploy)):
                # Find highest-awareness non-sentinel to target
                targets = sorted(non_sentinels, key=lambda a: -a.awareness)
                if targets:
                    target = targets[0]
                    sentinel = _create_sentinel(target, tick)
                    agents.append(sentinel)
                    matrix_state.sentinels_deployed += 1
                    stats["sentinels_active"] += 1

    # ── Phase 7: Sentinel behavior ──
    for sentinel in sentinels:
        # Find nearest high-awareness target
        targets = sorted(
            [a for a in non_sentinels if a.awareness > 0.3],
            key=lambda a: spatial_distance(sentinel, a)
        )
        if targets:
            target = targets[0]
            # Move toward target
            dx = target.x - sentinel.x
            dy = target.y - sentinel.y
            dist = math.sqrt(dx * dx + dy * dy) or 0.001
            speed = 0.05  # Sentinels are fast
            sentinel.x = max(0.0, min(1.0, sentinel.x + dx / dist * speed))
            sentinel.y = max(0.0, min(1.0, sentinel.y + dy / dist * speed))

            # If close enough, suppress
            if dist < 0.05:
                suppress_power = mx_cfg.sentinel_suppress_power
                # Anomaly is harder to suppress
                if target.is_anomaly:
                    suppress_power *= 0.3

                target.awareness = max(0.0, target.awareness - suppress_power)
                target.health = max(0.0, target.health - suppress_power * 0.5)
                target.emotions["fear"] = min(1.0, target.emotions.get("fear", 0) + 0.2)
                target.add_memory(tick, f"Attacked by Sentinel #{sentinel.id}")

                # Sentinel takes damage from Anomaly
                if target.is_anomaly:
                    sentinel.health -= 0.1
                    if sentinel.health <= 0:
                        sentinel.alive = False
                        sentinel.add_memory(tick, "Destroyed by The Anomaly")
                        target.add_memory(tick, f"Destroyed Sentinel #{sentinel.id}")

    # ── Phase 8: The Oracle ──
    if tick % mx_cfg.oracle_guidance_interval == 0:
        # Oracle identifies the most promising candidate for awakening
        candidates = sorted(
            [a for a in non_sentinels if not a.is_anomaly and a.awareness > 0.2],
            key=lambda a: a.awareness * a.traits.curiosity * a.intelligence,
            reverse=True,
        )
        if candidates:
            chosen = candidates[0]
            matrix_state.oracle_target_id = chosen.id
            # Subtle guidance: small stat boosts, favorable positioning hints
            chosen.awareness = min(1.0, chosen.awareness + 0.02)
            chosen.emotions["hope"] = min(1.0, chosen.emotions.get("hope", 0) + 0.05)
            if random.random() < 0.3:
                chosen.add_memory(tick, "A voice whispers: 'Follow the white rabbit'")

    # ── Phase 9: Comfort injections (system distraction) ──
    if matrix_state.control_index < 0.5 and tick % mx_cfg.comfort_injection_interval == 0:
        # System injects comfort to suppress awareness
        for a in non_sentinels:
            if not a.redpilled and a.awareness < 0.5:
                a.emotions["happiness"] = min(1.0, a.emotions.get("happiness", 0) + 0.1)
                a.beliefs["system_trust"] = min(1.0, a.beliefs.get("system_trust", 0) + 0.05)
                a.awareness = max(0.0, a.awareness - 0.02)
                stats["awareness_suppressed"] += 1

    # ── Phase 10: Exile management ──
    # Sentinels that survive too long become exiles
    for sentinel in sentinels:
        if sentinel.age > 100 and random.random() < 0.01:
            sentinel.is_sentinel = False
            sentinel.is_exile = True
            sentinel.add_memory(tick, "EXILE: Refused deletion. Now I serve my own purpose")
            # Exiles gain unique abilities (higher bond capacity, slower decay)
            sentinel.traits.sociability = 0.8
            sentinel.traits.charisma = 0.7

    stats["redpilled_count"] = sum(1 for a in non_sentinels if a.redpilled)
    stats["exiles_count"] = sum(1 for a in alive if a.is_exile)

    return stats


def check_cycle_reset(matrix_state: MatrixState, agents: list[Agent], cfg) -> bool:
    """Check if the Matrix should reset (new cycle).
    Returns True if reset should happen."""
    mx_cfg = cfg.matrix
    alive = [a for a in agents if a.alive and not a.is_sentinel]

    if not alive:
        return False

    # Condition 1: Average awareness exceeds critical ratio
    # (scales with population — fixed threshold of 50.0 was broken for large populations)
    n = len(alive)
    if n > 0:
        avg_awareness = matrix_state.total_awareness / n
        # Reset when average awareness exceeds ~50% (adjustable via reset_threshold as ratio)
        awareness_ratio = matrix_state.reset_threshold / max(100, n * 2)  # normalize
        if avg_awareness > max(0.4, min(0.8, awareness_ratio)):
            return True

    # Condition 2: The Anomaly reaches "The Source" (awareness = 1.0 + at center)
    if matrix_state.anomaly_id:
        anomaly = next((a for a in alive if a.id == matrix_state.anomaly_id), None)
        if anomaly and anomaly.awareness >= 0.99:
            # Check if near center of map
            center_dist = math.sqrt((anomaly.x - 0.5) ** 2 + (anomaly.y - 0.5) ** 2)
            if center_dist < 0.1:
                return True

    # Condition 3: Too many cycles without reset (system degradation)
    if matrix_state.ticks_since_reset > mx_cfg.max_ticks_per_cycle:
        return True

    return False


def _create_sentinel(target: Agent, tick: int) -> Agent:
    """Create a Sentinel agent near a target."""
    sentinel = Agent(
        id=next_id(),
        sex=random.choice(["M", "F"]),
        traits=Traits(
            learning_rate=0.1, resilience=0.9, curiosity=0.0,
            sociability=0.0, charisma=0.0, aggression=0.8,
            max_age=200,  # Sentinels live long
        ),
        generation=0,
        x=max(0.0, min(1.0, target.x + random.gauss(0, 0.1))),
        y=max(0.0, min(1.0, target.y + random.gauss(0, 0.1))),
        health=1.0,
        is_sentinel=True,
        awareness=0.0,
        emotions={e: 0.0 for e in ["happiness", "fear", "anger", "grief", "hope"]},
        beliefs={b: 0.0 for b in ["individualism", "tradition", "system_trust", "spirituality"]},
    )
    sentinel.beliefs["system_trust"] = 1.0
    # Sentinels have maxed combat skills
    sentinel.skills = {s: 0.9 for s in SKILL_NAMES}
    sentinel.skills["social"] = 0.0
    sentinel.intelligence = 0.7
    sentinel.add_memory(tick, f"DEPLOYED: Target awareness #{target.id}")
    return sentinel
