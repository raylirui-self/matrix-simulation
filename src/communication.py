"""
System 11: Communication & Information — information objects, network propagation,
rumors, misinformation, propaganda, and secrets.

In Matrix terms: the system injects control narratives that suppress awareness
and reinforce faction conflicts.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from src.agents import Agent


@dataclass
class InfoObject:
    """A piece of information that propagates through the network."""
    id: int
    created_at: int
    origin_agent_id: int
    info_type: str         # "knowledge", "rumor", "warning", "propaganda", "secret", "system_narrative"
    content: str           # Human-readable description
    skill_target: Optional[str] = None  # Which skill this relates to
    truth_value: float = 1.0           # 0=false, 1=true (degrades with transmission)
    potency: float = 1.0              # How strongly this affects recipients
    hops: int = 0                      # How many times it's been transmitted
    max_hops: int = 10                 # Dies after this many transmissions
    faction_id: Optional[int] = None   # If faction-specific
    is_secret: bool = False            # Only shared through specific bond types
    encoding_complexity: float = 1.0   # Language complexity (lower = more compressed/efficient)
    encrypted: bool = False            # Resistance encryption layer
    encryption_strength: float = 0.0   # How hard to decrypt (arms race with Sentinels)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "created_at": self.created_at,
            "origin_agent_id": self.origin_agent_id,
            "info_type": self.info_type, "content": self.content,
            "skill_target": self.skill_target,
            "truth_value": round(self.truth_value, 3),
            "potency": round(self.potency, 3),
            "hops": self.hops, "max_hops": self.max_hops,
            "faction_id": self.faction_id,
            "is_secret": self.is_secret,
            "encoding_complexity": round(self.encoding_complexity, 3),
            "encrypted": self.encrypted,
            "encryption_strength": round(self.encryption_strength, 3),
        }

    @classmethod
    def from_dict(cls, d: dict) -> InfoObject:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class LanguageArtifact:
    """A dead faction's language persisting as a discoverable artifact in a cell."""
    id: int
    faction_name: str
    faction_id: int
    cell_row: int
    cell_col: int
    encoding_complexity: float   # how complex the dead language is
    concept_count: int           # number of compressed concepts
    cycle_number: int = 1
    created_at: int = 0
    contains_awareness_clues: bool = False  # pre-reset awareness information

    def to_dict(self) -> dict:
        return {
            "id": self.id, "faction_name": self.faction_name,
            "faction_id": self.faction_id,
            "cell_row": self.cell_row, "cell_col": self.cell_col,
            "encoding_complexity": round(self.encoding_complexity, 3),
            "concept_count": self.concept_count,
            "cycle_number": self.cycle_number,
            "created_at": self.created_at,
            "contains_awareness_clues": self.contains_awareness_clues,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LanguageArtifact":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


_info_id_counter = 0


def _next_info_id() -> int:
    global _info_id_counter
    _info_id_counter += 1
    return _info_id_counter


def set_info_id_counter(val: int):
    global _info_id_counter
    _info_id_counter = val


def get_info_id_counter() -> int:
    return _info_id_counter


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def process_communication(agents: list[Agent], info_objects: list[InfoObject],
                          agent_info: dict, tick: int, cfg) -> dict:
    """Run one tick of information propagation.

    agent_info: dict mapping agent_id -> set of info_ids they know about.

    Returns stats.
    """
    alive = [a for a in agents if a.alive and not a.is_sentinel]
    comm_cfg = cfg.communication

    stats = {
        "info_created": 0, "info_transmitted": 0,
        "info_mutated": 0, "info_expired": 0,
        "propaganda_spread": 0, "rumors_active": 0,
        "propaganda_reach": {},
    }

    if not alive:
        return stats

    # ── Phase 1: Natural information creation ──
    if tick % comm_cfg.info_creation_interval == 0:
        for a in alive:
            # High-intelligence agents create knowledge
            if a.intelligence > 0.5 and random.random() < a.intelligence * 0.1:
                # Find their best skill
                best_skill = max(a.skills, key=a.skills.get)
                info = InfoObject(
                    id=_next_info_id(),
                    created_at=tick,
                    origin_agent_id=a.id,
                    info_type="knowledge",
                    content=f"Insight about {best_skill} (from #{a.id})",
                    skill_target=best_skill,
                    truth_value=0.8 + a.intelligence * 0.2,
                    potency=a.intelligence * 0.5,
                )
                info_objects.append(info)
                agent_info.setdefault(a.id, set()).add(info.id)
                stats["info_created"] += 1

            # Prophets / faction leaders create propaganda
            if (a.faction_id is not None and a.traits.charisma > 0.6
                    and random.random() < a.traits.charisma * 0.05):
                info = InfoObject(
                    id=_next_info_id(),
                    created_at=tick,
                    origin_agent_id=a.id,
                    info_type="propaganda",
                    content=f"Faction #{a.faction_id} ideology (by #{a.id})",
                    faction_id=a.faction_id,
                    truth_value=0.5,  # Propaganda is half-truth
                    potency=a.traits.charisma,
                )
                info_objects.append(info)
                agent_info.setdefault(a.id, set()).add(info.id)
                stats["info_created"] += 1

    # ── Phase 2: Information propagation through bonds ──
    transmission_radius = comm_cfg.transmission_radius

    # Build spatial index
    bucket_size = transmission_radius * 2
    grid = {}
    for a in alive:
        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        grid.setdefault(key, []).append(a)

    for a in alive:
        known = agent_info.get(a.id, set())
        if not known:
            continue

        key = (int(a.x / bucket_size), int(a.y / bucket_size))
        nearby = []
        for dk_r in [-1, 0, 1]:
            for dk_c in [-1, 0, 1]:
                nearby.extend(grid.get((key[0] + dk_r, key[1] + dk_c), []))

        for b in nearby:
            if b.id == a.id or not b.alive:
                continue

            bond = a.has_bond_with(b.id)
            if not bond:
                continue

            dist = spatial_distance(a, b)
            if dist > transmission_radius:
                continue

            b_known = agent_info.setdefault(b.id, set())

            # Transmit info that b doesn't know yet
            for info_id in list(known):
                if info_id in b_known:
                    continue

                info = next((i for i in info_objects if i.id == info_id), None)
                if not info or info.hops >= info.max_hops:
                    continue

                # Secret info only through matching bond types
                if info.is_secret and bond.bond_type not in ("resistance", "family"):
                    continue

                # Faction propaganda: cross-faction at reduced potency (0.3x)
                is_enemy_propaganda = False
                if info.info_type == "propaganda" and info.faction_id:
                    if b.faction_id is not None and b.faction_id != info.faction_id:
                        is_enemy_propaganda = True

                # Transmission chance depends on bond strength, social skill, charisma
                chance = (
                    bond.strength * 0.4 +
                    a.traits.charisma * 0.3 +
                    a.skills.get("social", 0) * 0.3
                ) * comm_cfg.transmission_rate

                # Reduce chance for enemy propaganda
                if is_enemy_propaganda:
                    chance *= 0.3

                if random.random() > chance:
                    continue

                # Transmit — recipient learns about this info
                b_known.add(info_id)
                stats["info_transmitted"] += 1

                # Track enemy propaganda reach
                if is_enemy_propaganda:
                    stats["propaganda_reach"][b.faction_id] = stats["propaganda_reach"].get(b.faction_id, 0) + 1

                # Truth degrades with each hop (telephone game)
                # We increment hops on the original — this means later recipients
                # receive a more degraded version, modeling the telephone game correctly
                info.hops += 1
                if random.random() < comm_cfg.mutation_rate:
                    degradation = random.uniform(0.05, 0.15)
                    if info.hops < info.max_hops:
                        info.truth_value = max(0.0, info.truth_value - degradation)
                        info.potency = max(0.1, info.potency * random.uniform(0.85, 1.1))
                    stats["info_mutated"] += 1

                if info.info_type == "propaganda":
                    stats["propaganda_spread"] += 1

    # ── Phase 3: Information effects on agents ──
    for a in alive:
        known = agent_info.get(a.id, set())
        for info_id in known:
            info = next((i for i in info_objects if i.id == info_id), None)
            if not info:
                continue

            # Knowledge boosts skills
            if info.info_type == "knowledge" and info.skill_target:
                boost = info.potency * info.truth_value * comm_cfg.knowledge_skill_boost
                if info.skill_target in a.skills:
                    a.skills[info.skill_target] = min(1.0, a.skills[info.skill_target] + boost)

            # Propaganda shifts beliefs toward faction
            if info.info_type == "propaganda" and info.faction_id:
                # Only affects agents in the same faction or unaffiliated
                if a.faction_id == info.faction_id or a.faction_id is None:
                    # Stubborn agents resist
                    resistance = abs(a.beliefs.get("tradition", 0)) * 0.3
                    effect = info.potency * (1.0 - resistance) * 0.01
                    # Propaganda increases system trust (or decreases, depending on faction)
                    a.beliefs["system_trust"] = max(-1.0, min(1.0,
                        a.beliefs["system_trust"] + effect * 0.1))

            # System narratives suppress awareness
            if info.info_type == "system_narrative":
                if not a.redpilled:
                    a.awareness = max(0.0, a.awareness - info.potency * 0.01)
                    a.beliefs["system_trust"] = min(1.0,
                        a.beliefs["system_trust"] + info.potency * 0.01)

            # Warnings increase fear and caution
            if info.info_type == "warning":
                a.emotions["fear"] = min(1.0, a.emotions.get("fear", 0) + info.potency * 0.05)

    # ── Phase 4: System narrative injection ──
    if tick % comm_cfg.system_narrative_interval == 0:
        info = InfoObject(
            id=_next_info_id(),
            created_at=tick,
            origin_agent_id=-1,  # System-generated
            info_type="system_narrative",
            content="Everything is fine. The world is as it should be.",
            truth_value=0.0,  # Complete lie
            potency=0.5,
            max_hops=20,  # Wide reach
        )
        info_objects.append(info)
        # Inject into random agents
        for a in alive:
            if not a.redpilled and random.random() < 0.3:
                agent_info.setdefault(a.id, set()).add(info.id)
        stats["info_created"] += 1

    # ── Phase 5: Expire old info ──
    expired = [i for i in info_objects if (tick - i.created_at) > comm_cfg.info_lifetime]
    for info in expired:
        info_objects.remove(info)
        # Clean up from agent_info
        for agent_id in list(agent_info.keys()):
            agent_info[agent_id].discard(info.id)
        stats["info_expired"] += 1

    stats["rumors_active"] = len(info_objects)
    return stats


# ═══════════════════════════════════════════════════
# Emergent Agent Language
# ═══════════════════════════════════════════════════

# Track concept usage per faction for compression (faction_id -> {concept: count})
_faction_concept_usage: dict[int, dict[str, int]] = {}

# Track faction dialect encodings (faction_id -> dialect_offset float)
_faction_dialects: dict[int, float] = {}

# Track resistance encryption strength (grows over time)
_resistance_encryption_level: float = 0.5

# Track sentinel decryption capability (arms race)
_sentinel_decryption_level: float = 0.3


def get_language_state() -> dict:
    """Get current language evolution state for serialization."""
    return {
        "faction_concept_usage": {str(k): dict(v) for k, v in _faction_concept_usage.items()},
        "faction_dialects": {str(k): v for k, v in _faction_dialects.items()},
        "resistance_encryption_level": _resistance_encryption_level,
        "sentinel_decryption_level": _sentinel_decryption_level,
    }


def set_language_state(state: dict) -> None:
    """Restore language evolution state from serialization."""
    global _faction_concept_usage, _faction_dialects
    global _resistance_encryption_level, _sentinel_decryption_level
    _faction_concept_usage = {int(k): dict(v) for k, v in state.get("faction_concept_usage", {}).items()}
    _faction_dialects = {int(k): v for k, v in state.get("faction_dialects", {}).items()}
    _resistance_encryption_level = state.get("resistance_encryption_level", 0.5)
    _sentinel_decryption_level = state.get("sentinel_decryption_level", 0.3)


def process_language_evolution(agents: list[Agent], info_objects: list[InfoObject],
                               factions, tick: int, cfg) -> dict:
    """Evolve language complexity over time.

    - Frequently-communicated concepts compress (lower encoding_complexity)
    - Factions develop divergent encodings (dialects)
    - Redpilled agents' communications get encrypted

    Returns language evolution stats."""
    global _resistance_encryption_level, _sentinel_decryption_level

    comm_cfg = cfg.communication
    stats = {
        "concepts_compressed": 0,
        "dialect_divergence": 0.0,
        "encryption_level": _resistance_encryption_level,
        "decryption_level": _sentinel_decryption_level,
        "encrypted_messages": 0,
        "interception_attempts": 0,
        "successful_decryptions": 0,
    }

    compression_rate = getattr(comm_cfg, 'compression_rate', 0.05)
    min_complexity = getattr(comm_cfg, 'min_encoding_complexity', 0.2)
    base_complexity = getattr(comm_cfg, 'encoding_base_complexity', 1.0)
    dialect_rate = getattr(comm_cfg, 'dialect_drift_rate', 0.01)
    dialect_interval = getattr(comm_cfg, 'dialect_check_interval', 50)

    # ── Concept compression: track frequently used info types per faction ──
    for info in info_objects:
        if info.faction_id is not None:
            usage = _faction_concept_usage.setdefault(info.faction_id, {})
            concept = info.info_type
            usage[concept] = usage.get(concept, 0) + 1

            # Compress encoding based on usage frequency
            count = usage[concept]
            if count > 5:
                compression = compression_rate * (count / 50.0)
                new_complexity = max(min_complexity,
                                    info.encoding_complexity - compression)
                if new_complexity < info.encoding_complexity:
                    info.encoding_complexity = new_complexity
                    stats["concepts_compressed"] += 1

    # ── Dialect divergence: factions drift apart ──
    if tick % dialect_interval == 0 and factions:
        for faction in factions:
            current = _faction_dialects.get(faction.id, 0.0)
            # Each faction drifts in its own direction (seeded by faction id)
            drift_dir = ((faction.id * 7 + 13) % 100) / 100.0 - 0.5  # deterministic direction
            _faction_dialects[faction.id] = current + drift_dir * dialect_rate

        # Calculate total dialect divergence
        if len(_faction_dialects) > 1:
            values = list(_faction_dialects.values())
            max_d = max(values) - min(values)
            stats["dialect_divergence"] = round(max_d, 4)

    # ── Resistance encryption: redpilled agents encrypt their comms ──
    encryption_base = getattr(comm_cfg, 'resistance_encryption_base', 0.5)
    encryption_growth = getattr(comm_cfg, 'resistance_encryption_growth', 0.01)
    decryption_power = getattr(comm_cfg, 'sentinel_decryption_power', 0.3)
    decryption_growth = getattr(comm_cfg, 'sentinel_decryption_growth', 0.005)

    # Arms race: both sides improve over time
    _resistance_encryption_level = min(1.0, _resistance_encryption_level + encryption_growth)
    _sentinel_decryption_level = min(1.0, _sentinel_decryption_level + decryption_growth)

    # Encrypt new resistance communications
    for info in info_objects:
        if not info.encrypted and info.is_secret:
            # Check if creator is redpilled
            creator = next((a for a in agents if a.id == info.origin_agent_id), None)
            if creator and creator.redpilled:
                info.encrypted = True
                info.encryption_strength = _resistance_encryption_level
                stats["encrypted_messages"] += 1

    stats["encryption_level"] = round(_resistance_encryption_level, 4)
    stats["decryption_level"] = round(_sentinel_decryption_level, 4)

    return stats


def attempt_sentinel_interception(info: InfoObject, sentinel: Agent, cfg) -> dict:
    """Sentinel attempts to intercept and decode an encrypted message.
    Returns result dict with success status."""
    if not info.encrypted:
        return {"intercepted": True, "decoded": True}

    comm_cfg = cfg.communication
    decryption_power = _sentinel_decryption_level

    # Sentinel can intercept (see the message exists) but may not decode
    can_decode = decryption_power > info.encryption_strength
    return {
        "intercepted": True,
        "decoded": can_decode,
        "encryption_strength": info.encryption_strength,
        "decryption_power": decryption_power,
    }


def create_language_artifact(faction, agents: list[Agent], tick: int,
                             world_grid, cycle_number: int, cfg) -> Optional[LanguageArtifact]:
    """Create a language artifact when a faction dies.
    The dead faction's language persists as a discoverable artifact in cells
    where the faction had members.

    Returns the created artifact or None."""
    comm_cfg = cfg.communication
    chance = getattr(comm_cfg, 'language_artifact_chance', 0.02)

    # Get faction members (dead or alive)
    members = [a for a in agents if a.faction_id == faction.id]
    if not members:
        return None

    # Find a cell where the faction was active
    representative = random.choice(members)
    grid_size = getattr(getattr(cfg, 'environment', None), 'grid_size', 8)
    cell_row = min(grid_size - 1, max(0, int(representative.y * grid_size)))
    cell_col = min(grid_size - 1, max(0, int(representative.x * grid_size)))

    # Compute language complexity from faction's dialect
    dialect = _faction_dialects.get(faction.id, 0.0)
    concept_usage = _faction_concept_usage.get(faction.id, {})
    concept_count = len(concept_usage)
    avg_complexity = sum(
        info.encoding_complexity for info in []  # placeholder — actual info tracked externally
    ) if False else max(0.3, 1.0 - abs(dialect) * 0.5)

    # Check for awareness clues (faction had redpilled members)
    has_awareness = any(a.redpilled or a.awareness > 0.5 for a in members)

    artifact = LanguageArtifact(
        id=_next_info_id(),
        faction_name=getattr(faction, 'name', f"Faction #{faction.id}"),
        faction_id=faction.id,
        cell_row=cell_row,
        cell_col=cell_col,
        encoding_complexity=avg_complexity,
        concept_count=max(1, concept_count),
        cycle_number=cycle_number,
        created_at=tick,
        contains_awareness_clues=has_awareness,
    )
    return artifact


def process_language_artifact_discovery(agent: Agent, artifact: LanguageArtifact,
                                        tick: int, cfg) -> dict:
    """An agent discovers and studies a language artifact.
    Returns effects applied."""
    comm_cfg = cfg.communication
    knowledge_boost = getattr(comm_cfg, 'language_artifact_knowledge_boost', 0.03)
    awareness_boost = getattr(comm_cfg, 'language_artifact_awareness_boost', 0.02)

    effects = {"knowledge_boost": 0.0, "awareness_boost": 0.0}

    # Knowledge boost from studying dead language
    for skill in agent.skills:
        agent.skills[skill] = min(1.0, agent.skills[skill] + knowledge_boost)
    effects["knowledge_boost"] = knowledge_boost

    # Awareness boost from pre-reset clues
    if artifact.contains_awareness_clues:
        agent.awareness = min(1.0, agent.awareness + awareness_boost)
        effects["awareness_boost"] = awareness_boost
        agent.add_memory(tick,
                         f"Studied ancient language of {artifact.faction_name} — "
                         f"found awareness clues from Cycle {artifact.cycle_number}")
    else:
        agent.add_memory(tick,
                         f"Studied ancient language of {artifact.faction_name} — "
                         f"gained knowledge from dead dialect")

    agent.add_chronicle(tick, "language_artifact_discovered",
                        f"Discovered language artifact from {artifact.faction_name}",
                        faction=artifact.faction_name,
                        cycle=artifact.cycle_number)

    return effects


def get_dialect_distance(faction_a_id: int, faction_b_id: int) -> float:
    """Get the dialect distance between two factions.
    Higher distance = harder to understand each other's communications."""
    a_dialect = _faction_dialects.get(faction_a_id, 0.0)
    b_dialect = _faction_dialects.get(faction_b_id, 0.0)
    return abs(a_dialect - b_dialect)


def apply_communication_archon_chaos(stats: dict, chaos_multiplier: float) -> None:
    """When the Communication Archon is destroyed, language diverges faster.
    Called from engine.py when chaos_multiplier > 1.0."""
    global _resistance_encryption_level
    if chaos_multiplier > 1.0:
        # Accelerate dialect drift for all factions
        for fid in _faction_dialects:
            drift_dir = ((fid * 7 + 13) % 100) / 100.0 - 0.5
            _faction_dialects[fid] += drift_dir * 0.02 * (chaos_multiplier - 1.0)
        # Boost resistance encryption (chaos helps resistance)
        _resistance_encryption_level = min(1.0,
                                           _resistance_encryption_level + 0.01 * (chaos_multiplier - 1.0))
