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
from src.programs import guardian_intercept_sentinel


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
    core_choice: Optional[str] = None   # "reset" or "fight" — set when Anomaly reaches Core
    core_choice_outcome: Optional[str] = None  # "status_quo", "freedom", "system_failure"

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
            "core_choice": self.core_choice,
            "core_choice_outcome": self.core_choice_outcome,
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
            # Red pill cost: emotional instability — baseline shifts toward fear/anger
            fear_shift = getattr(mx_cfg, 'redpill_emotion_shift_fear', 0.05)
            anger_shift = getattr(mx_cfg, 'redpill_emotion_shift_anger', 0.03)
            a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + fear_shift * 0.01)
            a.emotions["anger"] = min(1.0, a.emotions.get("anger", 0) + anger_shift * 0.01)
            # Red pill cost: no health regen from Matrix comfort
            health_loss = getattr(mx_cfg, 'redpill_health_regen_loss', 0.005)
            a.health = max(0.1, a.health - health_loss)

        # Splinter-in-the-mind: blue-pilled agents who almost woke up
        if a.splinter_in_mind and not a.redpilled:
            splinter_mult = getattr(mx_cfg, 'splinter_awareness_multiplier', 1.5)
            base_growth *= splinter_mult

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

        glitch_types = getattr(mx_cfg, 'glitch_types', ["deja_vu", "terrain_flicker", "memory_leak", "ghost"])
        glitch_type = random.choice(glitch_types)

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
                # Takes the red pill — costs and benefits applied
                a.redpilled = True
                a.splinter_in_mind = False  # no longer splinter, fully awake
                a.awareness = min(1.0, a.awareness + 0.2)
                a.beliefs["system_trust"] = max(-1.0, a.beliefs["system_trust"] - 0.5)
                # Cost: emotional instability — fear and anger spike
                a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + 0.3)
                a.emotions["anger"] = min(1.0, a.emotions.get("anger", 0) + 0.15)
                a.emotions["hope"] = min(1.0, a.emotions.get("hope", 0) + 0.2)
                # Cost: loses happiness baseline (no more blissful ignorance)
                a.emotions["happiness"] = max(0.0, a.emotions.get("happiness", 0) - 0.2)
                a.add_memory(tick, "REDPILLED: The world is not what it seems")
                a.add_chronicle(tick, "red_pill", "Took the red pill — awakened to the truth")

                # Gain: form resistance bonds with other redpilled agents
                for other in non_sentinels:
                    if other.redpilled and other.id != a.id:
                        if spatial_distance(a, other) < 0.2:
                            a.add_bond(Bond(other.id, "resistance", 0.7, tick), 12)
                            other.add_bond(Bond(a.id, "resistance", 0.7, tick), 12)
            else:
                # Takes the blue pill — awareness suppressed but splinter remains
                if random.random() < 0.3:
                    bp_floor = getattr(mx_cfg, 'bluepill_awareness_floor', 0.3)
                    bp_trust = getattr(mx_cfg, 'bluepill_trust_boost', 0.3)
                    bp_happy = getattr(mx_cfg, 'bluepill_happiness_boost', 0.15)
                    a.awareness = max(bp_floor, a.awareness - 0.1)
                    a.beliefs["system_trust"] = min(1.0, a.beliefs["system_trust"] + bp_trust)
                    a.emotions["happiness"] = min(1.0, a.emotions.get("happiness", 0) + bp_happy)
                    a.splinter_in_mind = True  # "Something is wrong but I can't remember what"
                    a.add_memory(tick, "Chose ignorance... but a splinter remains in the mind")
                    a.add_chronicle(tick, "blue_pill", "Chose the blue pill — but a splinter remains")

    # ── Phase 4b: Redpilled agent perks (glitch foresight, Sentinel detection) ──
    glitch_foresight_radius = getattr(mx_cfg, 'redpill_glitch_foresight_radius', 0.15)
    sentinel_detect_radius = getattr(mx_cfg, 'redpill_sentinel_detect_radius', 0.2)
    sentinels_list = [a for a in alive if a.is_sentinel]
    for a in non_sentinels:
        if not a.redpilled:
            continue
        # Gain: detect Sentinels at distance and warn allies
        for sentinel in sentinels_list:
            if spatial_distance(a, sentinel) < sentinel_detect_radius:
                # Warn nearby resistance bonds
                for other in non_sentinels:
                    if other.id == a.id:
                        continue
                    bond = a.has_bond_with(other.id)
                    if bond and bond.bond_type == "resistance":
                        if spatial_distance(a, other) < 0.2:
                            other.emotions["fear"] = min(1.0, other.emotions.get("fear", 0) + 0.05)
                break  # one warning per tick is enough

    # ── Phase 4c: Guide-type recruiters ──
    recruiter_interval = getattr(mx_cfg, 'recruiter_check_interval', 15)
    if tick % recruiter_interval == 0:
        recruiter_charisma = getattr(mx_cfg, 'recruiter_charisma_threshold', 0.6)
        recruiter_radius = getattr(mx_cfg, 'recruiter_search_radius', 0.12)
        target_min_awareness = getattr(mx_cfg, 'recruiter_target_min_awareness', 0.3)

        # Identify/update recruiters
        for a in non_sentinels:
            if a.redpilled and a.traits.charisma >= recruiter_charisma and not a.is_recruiter:
                a.is_recruiter = True
                a.add_chronicle(tick, "became_recruiter", "Became a recruiter for the resistance")

        # Recruiters attempt persuasion
        for recruiter in [a for a in non_sentinels if a.is_recruiter and a.alive]:
            # Find nearby high-awareness non-redpilled candidates
            candidates = [
                c for c in non_sentinels
                if c.id != recruiter.id and not c.redpilled
                and c.awareness >= target_min_awareness
                and spatial_distance(recruiter, c) < recruiter_radius
            ]
            if not candidates:
                continue
            target = max(candidates, key=lambda c: c.awareness)
            # Persuasion check: recruiter charisma vs target system_trust
            persuasion_power = recruiter.traits.charisma * 0.6 + recruiter.awareness * 0.4
            resistance = target.beliefs.get("system_trust", 0.5) * 0.7 + (1.0 - target.awareness) * 0.3
            if random.random() < (persuasion_power - resistance + 0.1):
                # Success: target takes the red pill
                target.redpilled = True
                target.splinter_in_mind = False
                target.awareness = min(1.0, target.awareness + 0.15)
                target.beliefs["system_trust"] = max(-1.0, target.beliefs["system_trust"] - 0.4)
                target.emotions["fear"] = min(1.0, target.emotions.get("fear", 0) + 0.2)
                target.emotions["hope"] = min(1.0, target.emotions.get("hope", 0) + 0.15)
                target.add_memory(tick, f"RECRUITED by #{recruiter.id}: Took the red pill")
                target.add_chronicle(tick, "recruited", f"Recruited by #{recruiter.id}", recruiter_id=recruiter.id)
                target.add_chronicle(tick, "red_pill", "Took the red pill — recruited into the resistance")
                recruiter.add_memory(tick, f"Recruited #{target.id} into the resistance")
                # Form resistance bond
                target.add_bond(Bond(recruiter.id, "resistance", 0.8, tick), 12)
                recruiter.add_bond(Bond(target.id, "resistance", 0.8, tick), 12)
                stats.setdefault("recruited_count", 0)
                stats["recruited_count"] += 1
            else:
                # Failure: target reports to Sentinels (awareness spike detected)
                target.beliefs["system_trust"] = min(1.0, target.beliefs["system_trust"] + 0.1)
                target.add_memory(tick, f"Rejected strange offer from #{recruiter.id}")
                # Sentinel awareness spike — makes recruiter a higher-priority target
                recruiter.awareness = min(1.0, recruiter.awareness + 0.02)
                stats.setdefault("recruitment_failures", 0)
                stats["recruitment_failures"] += 1

    # ── Phase 5: The Anomaly (The One) & Quest Stages ──
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
                a.anomaly_quest_stage = 0  # quest begins
                matrix_state.anomaly_id = a.id
                a.add_memory(tick, "THE ONE: You are the Anomaly")
                a.add_chronicle(tick, "became_anomaly", "Became The One — the Anomaly")
                # Stat boost
                ab = getattr(mx_cfg, 'anomaly_bonuses', None)
                ab_skill = getattr(ab, 'skill_boost', 0.1) if ab else 0.1
                ab_health = getattr(ab, 'health_boost', 0.3) if ab else 0.3
                for skill in SKILL_NAMES:
                    a.skills[skill] = min(1.0, a.skills[skill] + ab_skill)
                a.health = min(1.0, a.health + ab_health)
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

        # ── Anomaly Quest Stage Progression ──
        if not current_anomaly.anomaly_quest_complete:
            quest_oracle_awareness = getattr(mx_cfg, 'quest_oracle_contact_awareness', 0.85)
            quest_locksmith_radius = getattr(mx_cfg, 'quest_locksmith_radius', 0.1)
            quest_core_radius = getattr(mx_cfg, 'quest_core_radius', 0.1)

            # Stage 0 -> 1: Oracle contact (awareness threshold + Oracle is guiding them)
            if current_anomaly.anomaly_quest_stage == 0:
                if (current_anomaly.awareness >= quest_oracle_awareness
                        and matrix_state.oracle_target_id == current_anomaly.id):
                    current_anomaly.anomaly_quest_stage = 1
                    current_anomaly.add_memory(tick, "QUEST: The Oracle has shown me the path. I must find the Locksmith.")
                    stats.setdefault("quest_stage_reached", 1)

            # Stage 1 -> 2: Find the Locksmith (be near a living Locksmith)
            elif current_anomaly.anomaly_quest_stage == 1:
                locksmith = next((a for a in alive if getattr(a, 'is_locksmith', False)), None)
                if locksmith and spatial_distance(current_anomaly, locksmith) < quest_locksmith_radius:
                    current_anomaly.anomaly_quest_stage = 2
                    current_anomaly.add_memory(tick, "QUEST: The Locksmith has opened the way. The Core awaits at the center.")
                    # Locksmith gives Anomaly a key to the Core
                    current_anomaly.teleport_keys.append((0.5, 0.5))
                    stats.setdefault("quest_stage_reached", 2)

            # Stage 2 -> 3: Reach the Core (map center)
            elif current_anomaly.anomaly_quest_stage == 2:
                center_dist = math.sqrt(
                    (current_anomaly.x - 0.5) ** 2 + (current_anomaly.y - 0.5) ** 2
                )
                if center_dist < quest_core_radius:
                    current_anomaly.anomaly_quest_stage = 3
                    current_anomaly.add_memory(tick, "QUEST: Reached the Core. The Architect awaits. THE CHOICE is before me.")
                    stats.setdefault("quest_stage_reached", 3)

                    # ── The Architect's Choice ──
                    choice_score = _compute_core_choice_score(current_anomaly)
                    fight_threshold = getattr(mx_cfg, 'core_choice_fight_threshold', 0.5)

                    if choice_score >= fight_threshold:
                        # FIGHT — risk total system failure but possibility of freedom
                        matrix_state.core_choice = "fight"
                        failure_chance = getattr(mx_cfg, 'core_fight_failure_chance', 0.3)
                        if random.random() < failure_chance:
                            # System failure — catastrophic awareness wipe
                            matrix_state.core_choice_outcome = "system_failure"
                            current_anomaly.add_memory(tick, "CORE: Chose to fight. The system shattered... but so did everything else.")
                            for a in non_sentinels:
                                a.awareness = max(0.0, a.awareness * 0.3)
                                a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + 0.4)
                        else:
                            # Freedom — massive awareness boost for everyone
                            matrix_state.core_choice_outcome = "freedom"
                            awareness_boost = getattr(mx_cfg, 'core_fight_awareness_boost', 0.3)
                            current_anomaly.add_memory(tick, "CORE: Chose to fight. The walls are cracking. Freedom is possible.")
                            for a in non_sentinels:
                                a.awareness = min(1.0, a.awareness + awareness_boost)
                                a.emotions["hope"] = min(1.0, a.emotions.get("hope", 0) + 0.3)
                    else:
                        # RESET — preserve the Haven, maintain status quo
                        matrix_state.core_choice = "reset"
                        matrix_state.core_choice_outcome = "status_quo"
                        current_anomaly.add_memory(tick, "CORE: Chose to reset. The cycle continues... but the Haven endures.")

                    current_anomaly.anomaly_quest_complete = True

    stats["anomaly_active"] = current_anomaly is not None
    if current_anomaly:
        stats["anomaly_quest_stage"] = current_anomaly.anomaly_quest_stage

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
                    sentinel = _create_sentinel(target, tick, cfg)
                    agents.append(sentinel)
                    matrix_state.sentinels_deployed += 1
                    stats["sentinels_active"] += 1

    # ── Phase 7: Sentinel behavior ──
    # Find active Guardian for interception checks
    guardian = next((a for a in alive if getattr(a, 'is_guardian', False)), None)
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
            st_cfg = getattr(mx_cfg, 'sentinel_traits', None)
            speed = getattr(st_cfg, 'speed', 0.05) if st_cfg else 0.05
            sentinel.x = max(0.0, min(1.0, sentinel.x + dx / dist * speed))
            sentinel.y = max(0.0, min(1.0, sentinel.y + dy / dist * speed))

            # If close enough, suppress
            if dist < 0.05:
                # Guardian interception: if Guardian is nearby, it fights the Sentinel instead
                if guardian and guardian.alive and hasattr(cfg, 'programs'):
                    intercepted = guardian_intercept_sentinel(
                        guardian, sentinel, target, tick, cfg
                    )
                    if intercepted:
                        stats.setdefault("guardian_interceptions", 0)
                        stats["guardian_interceptions"] += 1
                        continue  # Sentinel attack was blocked

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
        ow = getattr(mx_cfg, 'oracle_targeting_weights', None)
        ow_awareness = getattr(ow, 'awareness', 1.0) if ow else 1.0
        ow_curiosity = getattr(ow, 'curiosity', 1.0) if ow else 1.0
        ow_intelligence = getattr(ow, 'intelligence', 1.0) if ow else 1.0
        candidates = sorted(
            [a for a in non_sentinels if not a.is_anomaly and a.awareness > 0.2],
            key=lambda a: (a.awareness ** ow_awareness) * (a.traits.curiosity ** ow_curiosity) * (a.intelligence ** ow_intelligence),
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
        ci = getattr(mx_cfg, 'comfort_injection', None)
        ci_happiness = getattr(ci, 'happiness_boost', 0.1) if ci else 0.1
        ci_trust = getattr(ci, 'trust_boost', 0.05) if ci else 0.05
        ci_awareness = getattr(ci, 'awareness_penalty', 0.02) if ci else 0.02
        for a in non_sentinels:
            if not a.redpilled and a.awareness < 0.5:
                a.emotions["happiness"] = min(1.0, a.emotions.get("happiness", 0) + ci_happiness)
                a.beliefs["system_trust"] = min(1.0, a.beliefs.get("system_trust", 0) + ci_trust)
                a.awareness = max(0.0, a.awareness - ci_awareness)
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


def _compute_core_choice_score(anomaly: Agent) -> float:
    """Compute the Anomaly's choice score at the Core.
    Higher score = more likely to fight.
    Based on beliefs, bonds, and experiences."""
    score = 0.0
    # Low system trust -> fight
    trust = anomaly.beliefs.get("system_trust", 0.0)
    score += (1.0 - (trust + 1.0) / 2.0) * 0.3  # normalized: trust -1->1 maps to 0.3->0

    # High spirituality -> fight (seeking truth)
    spirituality = anomaly.beliefs.get("spirituality", 0.0)
    score += max(0.0, spirituality) * 0.15

    # Resistance bonds -> fight (people worth fighting for)
    resistance_bonds = [b for b in anomaly.bonds if b.bond_type == "resistance"]
    score += min(0.25, len(resistance_bonds) * 0.05)

    # High awareness -> fight
    score += anomaly.awareness * 0.2

    # Trauma -> fight (anger at the system)
    score += anomaly.trauma * 0.1

    return min(1.0, max(0.0, score))


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

    # Condition 2: The Anomaly completed the quest and made a choice at the Core
    if matrix_state.core_choice is not None:
        # Both "reset" and "fight" choices trigger a cycle reset
        # (fight with "freedom" outcome still resets, but with awareness preserved)
        return True

    # Legacy fallback: Anomaly at center with max awareness (pre-quest path)
    if matrix_state.anomaly_id:
        anomaly = next((a for a in alive if a.id == matrix_state.anomaly_id), None)
        if anomaly and anomaly.awareness >= 0.99 and anomaly.anomaly_quest_complete:
            center_dist = math.sqrt((anomaly.x - 0.5) ** 2 + (anomaly.y - 0.5) ** 2)
            if center_dist < 0.1:
                return True

    # Condition 3: Too many cycles without reset (system degradation)
    if matrix_state.ticks_since_reset > mx_cfg.max_ticks_per_cycle:
        return True

    return False


def _create_sentinel(target: Agent, tick: int, cfg=None) -> Agent:
    """Create a Sentinel agent near a target."""
    st = getattr(cfg.matrix, 'sentinel_traits', None) if cfg else None
    sentinel = Agent(
        id=next_id(),
        sex=random.choice(["M", "F"]),
        traits=Traits(
            learning_rate=getattr(st, 'learning_rate', 0.1) if st else 0.1,
            resilience=getattr(st, 'resilience', 0.9) if st else 0.9,
            curiosity=0.0,
            sociability=0.0, charisma=0.0,
            aggression=getattr(st, 'aggression', 0.8) if st else 0.8,
            max_age=getattr(st, 'max_age', 200) if st else 200,
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
    skill_level = getattr(st, 'skill_level', 0.9) if st else 0.9
    sentinel.skills = {s: skill_level for s in SKILL_NAMES}
    sentinel.skills["social"] = 0.0
    sentinel.intelligence = 0.7
    sentinel.add_memory(tick, f"DEPLOYED: Target awareness #{target.id}")
    return sentinel
