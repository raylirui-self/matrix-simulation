"""
System 6: Emotions & Psychology — emotional states, contagion, trauma, and decision distortion.

Emotions are the fuel of the Matrix. The machines harvest emotional intensity.
In human terms: emotions drive irrational behavior that shapes civilizations.
"""
from __future__ import annotations

import math

from src.agents import Agent, EMOTION_NAMES


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def process_emotions(agents: list[Agent], tick: int, cfg, world=None) -> dict:
    """Run one tick of emotional dynamics. Returns stats.
    If world is provided, uses real cell data for situational triggers."""
    alive = [a for a in agents if a.alive]
    emo_cfg = cfg.emotions

    stats = {
        "avg_happiness": 0.0, "avg_fear": 0.0, "avg_anger": 0.0,
        "avg_grief": 0.0, "avg_hope": 0.0,
        "emotional_intensity": 0.0, "trauma_count": 0,
    }
    if not alive:
        return stats

    # ── Phase 1: Natural emotional decay toward baseline ──
    decay_rate = emo_cfg.decay_rate  # how fast emotions return to baseline
    baselines_cfg = getattr(emo_cfg, 'baselines', None)
    baseline = {
        "happiness": getattr(baselines_cfg, 'happiness', 0.4) if baselines_cfg else 0.4,
        "fear": getattr(baselines_cfg, 'fear', 0.05) if baselines_cfg else 0.05,
        "anger": getattr(baselines_cfg, 'anger', 0.05) if baselines_cfg else 0.05,
        "grief": getattr(baselines_cfg, 'grief', 0.0) if baselines_cfg else 0.0,
        "hope": getattr(baselines_cfg, 'hope', 0.35) if baselines_cfg else 0.35,
    }

    for a in alive:
        if a.is_sentinel:
            # Sentinels have flat emotions — they're programs
            a.emotions = {e: 0.1 for e in EMOTION_NAMES}
            continue

        for emo in EMOTION_NAMES:
            current = a.emotions.get(emo, 0.0)
            target = baseline.get(emo, 0.2)
            # Resilient agents recover faster
            resilience_factor = 1.0 + a.traits.resilience * 0.5
            diff = target - current
            a.emotions[emo] = current + diff * decay_rate * resilience_factor

        # Trauma slowly heals (very slowly)
        if a.trauma > 0:
            # Friends help heal trauma
            friend_count = sum(1 for b in a.bonds if b.bond_type in ("friend", "mate"))
            heal_rate = emo_cfg.trauma_heal_rate * (1.0 + friend_count * 0.1)
            a.trauma = max(0.0, a.trauma - heal_rate)

        # Trauma amplifies fear and grief, suppresses happiness (reduced from 0.05 to 0.02)
        if a.trauma > 0.2:
            a.emotions["fear"] = min(1.0, a.emotions["fear"] + a.trauma * 0.02)
            a.emotions["grief"] = min(1.0, a.emotions["grief"] + a.trauma * 0.015)
            a.emotions["happiness"] = max(0.0, a.emotions["happiness"] - a.trauma * 0.015)

    # ── Phase 2: Situational emotional triggers ──
    for a in alive:
        if a.is_sentinel:
            continue

        # Health anxiety: low health → fear (only when very low)
        if a.health < 0.2:
            a.emotions["fear"] = min(1.0, a.emotions["fear"] + 0.03)
            a.emotions["hope"] = max(0.0, a.emotions["hope"] - 0.01)

        # High health + resources → happiness
        if world is not None:
            cell = world.get_cell(a.x, a.y)
            cell_resources = cell.effective_resources
            cell_pressure = cell.pressure
        else:
            cell_resources = 0.5
            cell_pressure = 0.5
        if a.health > 0.7 and cell_resources > 0.6:
            a.emotions["happiness"] = min(1.0, a.emotions["happiness"] + 0.02)

        # Overcrowding → anger (only severe overcrowding)
        if cell_pressure > 2.5:
            a.emotions["anger"] = min(1.0, a.emotions["anger"] + 0.015)
            a.emotions["fear"] = min(1.0, a.emotions["fear"] + 0.005)

        # Isolated (no bonds) → grief/fear
        if len(a.bonds) == 0 and a.phase in ("adult", "elder"):
            a.emotions["grief"] = min(1.0, a.emotions["grief"] + 0.02)
            a.emotions["happiness"] = max(0.0, a.emotions["happiness"] - 0.02)

        # Many friends → happiness/hope
        friend_count = sum(1 for b in a.bonds if b.bond_type in ("friend", "mate", "ally"))
        if friend_count >= 3:
            a.emotions["happiness"] = min(1.0, a.emotions["happiness"] + 0.01 * friend_count)
            a.emotions["hope"] = min(1.0, a.emotions["hope"] + 0.005 * friend_count)

        # Rivalries → anger
        rival_count = sum(1 for b in a.bonds if b.bond_type in ("rival", "enemy"))
        if rival_count > 0:
            a.emotions["anger"] = min(1.0, a.emotions["anger"] + 0.02 * rival_count)

        # Elder → acceptance (reduced extremes)
        if a.phase == "elder":
            for emo in EMOTION_NAMES:
                a.emotions[emo] *= 0.95

    # ── Phase 3: Emotional contagion (spread through proximity) ──
    contagion_radius = emo_cfg.contagion_radius
    contagion_rate = emo_cfg.contagion_rate

    # Build spatial index
    bucket_size = contagion_radius * 2
    grid = {}
    for a in alive:
        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        grid.setdefault(key, []).append(a)

    for a in alive:
        if a.is_sentinel:
            continue
        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        nearby = []
        for dk_r in [-1, 0, 1]:
            for dk_c in [-1, 0, 1]:
                nearby.extend(grid.get((key[0] + dk_r, key[1] + dk_c), []))

        for b in nearby:
            if b.id == a.id or not b.alive:
                continue
            dist = spatial_distance(a, b)
            if dist > contagion_radius:
                continue

            # Contagion strength: closer = stronger, bonded = stronger
            proximity_factor = 1.0 - (dist / contagion_radius)
            bond = a.has_bond_with(b.id)
            bond_factor = bond.strength * 1.5 if bond else 0.3

            transfer = contagion_rate * proximity_factor * bond_factor
            # Charismatic agents spread emotions more effectively
            transfer *= (1.0 + b.traits.charisma * 0.5)

            for emo in EMOTION_NAMES:
                if b.emotions.get(emo, 0) > a.emotions.get(emo, 0):
                    delta = (b.emotions[emo] - a.emotions[emo]) * transfer
                    a.emotions[emo] = min(1.0, a.emotions[emo] + delta)

    # ── Phase 4: Clamp and compute stats ──
    total_intensity = 0.0
    for a in alive:
        for emo in EMOTION_NAMES:
            a.emotions[emo] = max(0.0, min(1.0, a.emotions[emo]))
        total_intensity += a.emotional_intensity
        if a.trauma > 0.3:
            stats["trauma_count"] += 1

    n = len(alive)
    for emo in EMOTION_NAMES:
        stats[f"avg_{emo}"] = round(sum(a.emotions.get(emo, 0) for a in alive) / n, 4)
    stats["emotional_intensity"] = round(total_intensity / n, 4)

    return stats


def on_agent_death_emotions(dead_agent: Agent, agents: list[Agent], tick: int, cfg):
    """Trigger grief in bonded agents when someone dies."""
    emo_cfg = cfg.emotions
    for a in agents:
        if not a.alive or a.is_sentinel:
            continue
        bond = a.has_bond_with(dead_agent.id)
        if bond:
            grief_amount = bond.strength * emo_cfg.grief_on_bond_death
            a.emotions["grief"] = min(1.0, a.emotions["grief"] + grief_amount)
            a.emotions["happiness"] = max(0.0, a.emotions["happiness"] - grief_amount * 0.5)

            # Strong bonds cause trauma
            if bond.strength > 0.6 and bond.bond_type in ("family", "mate"):
                a.trauma = min(1.0, a.trauma + grief_amount * 0.5)
                a.add_memory(tick, f"Traumatized by death of #{dead_agent.id}")

            # Witnessing death increases fear for nearby agents
            if spatial_distance(a, dead_agent) < 0.1:
                a.emotions["fear"] = min(1.0, a.emotions["fear"] + 0.15)


def on_birth_emotions(parent_a: Agent, parent_b: Agent, child: Agent, tick: int):
    """Trigger happiness when a child is born."""
    for parent in (parent_a, parent_b):
        parent.emotions["happiness"] = min(1.0, parent.emotions["happiness"] + 0.2)
        parent.emotions["hope"] = min(1.0, parent.emotions["hope"] + 0.15)
        parent.emotions["grief"] = max(0.0, parent.emotions["grief"] - 0.1)


def on_breakthrough_emotions(agents: list[Agent], tick: int):
    """Tech breakthroughs inspire hope."""
    for a in agents:
        if a.alive and not a.is_sentinel:
            a.emotions["hope"] = min(1.0, a.emotions["hope"] + 0.1)
            a.emotions["happiness"] = min(1.0, a.emotions["happiness"] + 0.05)


def get_emotion_utility_modifiers(agent: Agent, cfg) -> dict:
    """Return utility weight modifiers based on emotional state.
    These modify the base utility weights in the agency system."""
    mods = {
        "resource_pull": 0.0,
        "social_pull": 0.0,
        "curiosity_pull": 0.0,
        "safety_penalty": 0.0,
        "inertia": 0.0,
    }

    emo = agent.emotions
    # Fear → increase safety, decrease curiosity (strong effect — panicked agents flee)
    if emo.get("fear", 0) > 0.3:
        fear_factor = emo["fear"] - 0.3
        mods["safety_penalty"] += fear_factor * 1.0
        mods["curiosity_pull"] -= fear_factor * 0.6
        mods["social_pull"] -= fear_factor * 0.3

    # Anger → reduce safety (reckless), increase resource competition, reduce inertia
    if emo.get("anger", 0) > 0.3:
        anger_factor = emo["anger"] - 0.3
        mods["safety_penalty"] -= anger_factor * 0.6
        mods["resource_pull"] += anger_factor * 0.4
        mods["inertia"] -= anger_factor * 0.3

    # Grief → near-paralysis at high levels, strong social/curiosity reduction
    if emo.get("grief", 0) > 0.2:
        grief_factor = emo["grief"] - 0.2
        mods["inertia"] += grief_factor * 0.8
        mods["social_pull"] -= grief_factor * 0.4
        mods["curiosity_pull"] -= grief_factor * 0.4
        mods["resource_pull"] -= grief_factor * 0.2

    # Hope → increase curiosity and social significantly
    if emo.get("hope", 0) > 0.4:
        hope_factor = emo["hope"] - 0.4
        mods["curiosity_pull"] += hope_factor * 0.5
        mods["social_pull"] += hope_factor * 0.4

    # Happiness → social boost and curiosity
    if emo.get("happiness", 0) > 0.5:
        happy_factor = emo["happiness"] - 0.5
        mods["social_pull"] += happy_factor * 0.4
        mods["curiosity_pull"] += happy_factor * 0.2

    return mods


# ── Private helpers ──
def _get_cell_resources(agent: Agent, cfg) -> float:
    """Approximate cell resources from position (avoids circular import)."""
    # This returns a default; the engine should pass actual values when available
    return 0.5


def _get_cell_pressure(agent: Agent, cfg) -> float:
    """Approximate cell pressure."""
    return 0.5
