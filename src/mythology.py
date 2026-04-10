"""
Procedural Mythology System — Civilization Chronicle, Mythological Narratives,
Faction-Specific Historical Revisionism, and Legendary Figures.

Events first, rationalization second: record raw events, then generate
mythological framing via LLM (with deterministic fallbacks).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════

@dataclass
class EraSummary:
    """Auto-generated narrative summary of an era (N-tick window)."""
    tick_start: int
    tick_end: int
    summary_text: str
    stats_snapshot: dict = field(default_factory=dict)  # key stats at era end

    def to_dict(self) -> dict:
        return {
            "tick_start": self.tick_start,
            "tick_end": self.tick_end,
            "summary_text": self.summary_text,
            "stats_snapshot": self.stats_snapshot,
        }

    @classmethod
    def from_dict(cls, d: dict) -> EraSummary:
        return cls(**d)


@dataclass
class Myth:
    """A mythological narrative generated from real simulation events."""
    id: int
    name: str
    narrative: str
    source_event: str       # what actually happened
    tick_created: int
    trigger_type: str       # "cycle_reset", "era_transition", "catastrophe"
    faction_id: Optional[int] = None  # None = universal myth, int = faction-specific
    faction_perspective: str = ""      # "heroic", "persecution", "neutral"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "narrative": self.narrative,
            "source_event": self.source_event,
            "tick_created": self.tick_created,
            "trigger_type": self.trigger_type,
            "faction_id": self.faction_id,
            "faction_perspective": self.faction_perspective,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Myth:
        return cls(**d)


@dataclass
class LegendaryFigure:
    """An embellished historical figure derived from a real agent."""
    id: int
    agent_id: int
    name: str
    title: str              # "The Awakened One", "Prophet of the Void", etc.
    description: str
    tick_created: int
    legend_type: str        # "anomaly", "prophet", "warrior", "martyr"
    original_stats: dict = field(default_factory=dict)  # real stats at time of legend
    embellished_stats: dict = field(default_factory=dict)  # amplified for storytelling
    discovery_effects: dict = field(default_factory=dict)  # belief_drift, awareness_boost

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "tick_created": self.tick_created,
            "legend_type": self.legend_type,
            "original_stats": self.original_stats,
            "embellished_stats": self.embellished_stats,
            "discovery_effects": self.discovery_effects,
        }

    @classmethod
    def from_dict(cls, d: dict) -> LegendaryFigure:
        return cls(**d)


# ═══════════════════════════════════════════════════════════════
# Global myth ID counter
# ═══════════════════════════════════════════════════════════════

_myth_id_counter = 0
_legend_id_counter = 0


def _next_myth_id() -> int:
    global _myth_id_counter
    _myth_id_counter += 1
    return _myth_id_counter


def _next_legend_id() -> int:
    global _legend_id_counter
    _legend_id_counter += 1
    return _legend_id_counter


def get_myth_id_counter() -> int:
    return _myth_id_counter


def get_legend_id_counter() -> int:
    return _legend_id_counter


def set_myth_id_counter(val: int):
    global _myth_id_counter
    _myth_id_counter = val


def set_legend_id_counter(val: int):
    global _legend_id_counter
    _legend_id_counter = val


# ═══════════════════════════════════════════════════════════════
# Mythology State (persists across ticks)
# ═══════════════════════════════════════════════════════════════

@dataclass
class MythologyState:
    """Tracks mythology system state across ticks."""
    era_summaries: list[EraSummary] = field(default_factory=list)
    myths: list[Myth] = field(default_factory=list)
    legends: list[LegendaryFigure] = field(default_factory=list)
    last_era_summary_tick: int = 0
    last_myth_check_tick: int = 0
    known_legend_agent_ids: set = field(default_factory=set)  # agents already made legendary

    def to_dict(self) -> dict:
        return {
            "era_summaries": [s.to_dict() for s in self.era_summaries],
            "myths": [m.to_dict() for m in self.myths],
            "legends": [l.to_dict() for l in self.legends],
            "last_era_summary_tick": self.last_era_summary_tick,
            "last_myth_check_tick": self.last_myth_check_tick,
            "known_legend_agent_ids": list(self.known_legend_agent_ids),
            "myth_id_counter": get_myth_id_counter(),
            "legend_id_counter": get_legend_id_counter(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> MythologyState:
        state = cls(
            era_summaries=[EraSummary.from_dict(s) for s in d.get("era_summaries", [])],
            myths=[Myth.from_dict(m) for m in d.get("myths", [])],
            legends=[LegendaryFigure.from_dict(l) for l in d.get("legends", [])],
            last_era_summary_tick=d.get("last_era_summary_tick", 0),
            last_myth_check_tick=d.get("last_myth_check_tick", 0),
            known_legend_agent_ids=set(d.get("known_legend_agent_ids", [])),
        )
        if "myth_id_counter" in d:
            set_myth_id_counter(d["myth_id_counter"])
        if "legend_id_counter" in d:
            set_legend_id_counter(d["legend_id_counter"])
        return state


# ═══════════════════════════════════════════════════════════════
# Era Summary Generation (Civilization Chronicle)
# ═══════════════════════════════════════════════════════════════

def _build_era_summary_prompt(tick_start: int, tick_end: int,
                               stats_snapshot: dict, recent_events: list) -> str:
    """Build LLM prompt for era summary generation."""
    lines = [
        f"Civilization chronicle entry for ticks {tick_start}-{tick_end}.",
        f"Population: {stats_snapshot.get('alive', '?')} alive, "
        f"{stats_snapshot.get('total_born', '?')} born total, "
        f"{stats_snapshot.get('total_died', '?')} dead total.",
        f"Average health: {stats_snapshot.get('avg_health', '?')}.",
        f"Max generation: {stats_snapshot.get('max_generation', '?')}.",
    ]
    techs = stats_snapshot.get("world", {}).get("global_techs", [])
    if techs:
        lines.append(f"Technologies: {', '.join(techs)}.")
    factions = stats_snapshot.get("factions", [])
    if factions:
        faction_names = [f.get("name", "?") for f in factions[:5]]
        lines.append(f"Active factions: {', '.join(faction_names)}.")
    wars = stats_snapshot.get("wars", [])
    if wars:
        lines.append(f"{len(wars)} active war(s).")
    matrix = stats_snapshot.get("matrix", {})
    if matrix:
        lines.append(f"Matrix cycle: {matrix.get('cycle_number', 1)}, "
                      f"control index: {matrix.get('control_index', 1.0):.2f}.")
    if recent_events:
        event_names = [e if isinstance(e, str) else e.get("name", "?")
                       for e in recent_events[-5:]]
        lines.append(f"Key events: {', '.join(event_names)}.")
    lines.append("\nWrite a 3-5 sentence chronicle entry for this era of the civilization. "
                 "Use an epic, historical tone. Reference specific events and trends.")
    return "\n".join(lines)


def generate_era_summary(tick_start: int, tick_end: int, stats_snapshot: dict,
                          recent_events: list, narrator=None) -> EraSummary:
    """Generate an era summary using LLM or fallback."""
    text = None
    if narrator and narrator.enabled and narrator._ensure_connected():
        from src.narrator import NARRATOR_SYSTEM
        prompt = _build_era_summary_prompt(tick_start, tick_end, stats_snapshot, recent_events)
        text = narrator.active_provider.generate(
            NARRATOR_SYSTEM, prompt, temperature=0.7, max_tokens=300,
        )

    if not text:
        text = _fallback_era_summary(tick_start, tick_end, stats_snapshot, recent_events)

    return EraSummary(
        tick_start=tick_start,
        tick_end=tick_end,
        summary_text=text,
        stats_snapshot={
            "alive": stats_snapshot.get("alive", 0),
            "total_born": stats_snapshot.get("total_born", 0),
            "total_died": stats_snapshot.get("total_died", 0),
            "avg_health": stats_snapshot.get("avg_health", 0),
            "max_generation": stats_snapshot.get("max_generation", 0),
        },
    )


def _fallback_era_summary(tick_start: int, tick_end: int,
                           stats: dict, recent_events: list) -> str:
    """Template-based era summary when LLM is unavailable."""
    pop = stats.get("alive", 0)
    born = stats.get("total_born", 0)
    dead = stats.get("total_died", 0)
    max_gen = stats.get("max_generation", 1)
    avg_health = stats.get("avg_health", 0)
    techs = stats.get("world", {}).get("global_techs", [])
    wars = stats.get("wars", [])
    factions = stats.get("factions", [])
    matrix = stats.get("matrix", {})
    cycle = matrix.get("cycle_number", 1)

    # Determine era mood
    if pop == 0:
        mood = "The silence of extinction settled over the land."
    elif pop < 15:
        mood = "A handful of survivors clung to existence."
    elif pop < 50:
        mood = "The community endured, small but determined."
    elif pop < 150:
        mood = "The civilization grew and flourished."
    elif pop < 300:
        mood = "A great society stretched across the grid, teeming with ambition."
    else:
        mood = "A sprawling empire dominated the world, its complexity both strength and burden."

    parts = [f"**Ticks {tick_start}\u2013{tick_end}** \u2014 {mood}"]

    if avg_health > 0.6:
        parts.append("The people were healthy and prosperous.")
    elif avg_health > 0.3:
        parts.append("Hardship tested the populace, but they persevered.")
    else:
        parts.append("Disease and famine ravaged the population.")

    if techs:
        parts.append(f"Technologies mastered: {', '.join(techs)}.")
    if wars:
        parts.append(f"{len(wars)} conflict(s) scarred this era.")
    if factions:
        parts.append(f"{len(factions)} faction(s) vied for influence.")
    if cycle > 1:
        parts.append(f"The Matrix entered cycle {cycle}.")

    parts.append(f"Across {max_gen} generation(s), {born} souls were born and {dead} perished.")

    # Include notable events
    if recent_events:
        event_names = [e if isinstance(e, str) else e.get("name", "?")
                       for e in recent_events[-3:]]
        parts.append(f"Notable events: {', '.join(event_names)}.")

    return " ".join(parts)


# ═══════════════════════════════════════════════════════════════
# Mythological Narrative Generation
# ═══════════════════════════════════════════════════════════════

# Mapping from event patterns to mythological archetypes
_MYTH_ARCHETYPES = {
    "resource_depletion": {
        "names": ["The Great Flood", "The Withering", "The Famine of Shadows", "The Barren Age"],
        "template": "When the land itself turned against the people, {detail}. The elders called it {name}, and none who lived through it emerged unchanged.",
    },
    "faction_war": {
        "names": ["The Prophet's War", "The Schism of Fire", "The Crimson Divide", "The War of Beliefs"],
        "template": "Two great powers clashed, and the world trembled. {detail}. This conflict would be remembered as {name}.",
    },
    "cycle_reset": {
        "names": ["The Unmaking", "The Great Forgetting", "The Rebirth", "The Day the Sky Fell"],
        "template": "Reality itself shattered and reformed. {detail}. The survivors called it {name}, though few truly remembered what came before.",
    },
    "mass_death": {
        "names": ["The Culling", "The Plague of the Architect", "The Reaping", "The Shadow Harvest"],
        "template": "Death swept through the population like a cold wind. {detail}. It became known as {name}.",
    },
    "anomaly_emergence": {
        "names": ["The Awakening", "The Coming of the One", "The Glitch Prophet", "The Anomaly's Dawn"],
        "template": "One among them opened their eyes and saw the truth. {detail}. The faithful called it {name}.",
    },
    "tech_breakthrough": {
        "names": ["The Spark of Prometheus", "The Great Discovery", "The Forging", "The Enlightenment"],
        "template": "Knowledge burst forth like light in darkness. {detail}. This age of discovery was named {name}.",
    },
}


def _build_myth_prompt(source_event: str, trigger_type: str,
                        stats_snapshot: dict, faction=None) -> str:
    """Build LLM prompt for myth generation."""
    lines = [
        f"A civilization has just experienced: {source_event}.",
        f"Trigger: {trigger_type}.",
        f"Population: {stats_snapshot.get('alive', '?')}.",
    ]
    if faction:
        perspective = "heroic" if faction.get("won", False) else "persecution"
        lines.append(f"Generate this myth from the perspective of the '{faction.get('name', 'unknown')}' faction.")
        lines.append(f"Their core beliefs: {faction.get('core_beliefs', {})}.")
        lines.append(f"Tone: {perspective} narrative — {'they triumphed gloriously' if perspective == 'heroic' else 'they suffered unjustly'}.")
    else:
        lines.append("Generate a universal myth told by all survivors.")
    lines.append("\nCreate a mythological name for this event and a 2-4 sentence narrative. "
                 "Use archaic, epic language. Transform the real event into legend.")
    lines.append("Respond as: MYTH_NAME: <name>\\nNARRATIVE: <text>")
    return "\n".join(lines)


def _parse_myth_response(raw: str) -> tuple[str, str]:
    """Parse LLM myth response into (name, narrative)."""
    name = ""
    narrative = raw.strip()
    for line in raw.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("MYTH_NAME:"):
            name = line.split(":", 1)[1].strip().strip('"')
        elif line.upper().startswith("NARRATIVE:"):
            narrative = line.split(":", 1)[1].strip()
    if not name:
        # Try to extract from first line
        name = raw.strip().split("\n")[0][:60]
    return name, narrative


def classify_events_for_myths(recent_events: list, stats: dict,
                                cycle_reset: bool = False) -> list[dict]:
    """Analyze recent events and stats to identify myth-worthy occurrences."""
    triggers = []

    if cycle_reset:
        triggers.append({
            "archetype": "cycle_reset",
            "source_event": "The Matrix cycle reset — reality was rewritten",
            "trigger_type": "cycle_reset",
        })

    # Check for resource depletion
    world = stats.get("world", {})
    depleted = world.get("depleted_cells", 0)
    grid_size = world.get("grid_size", 8)
    if grid_size > 0 and depleted > (grid_size * grid_size) * 0.3:
        triggers.append({
            "archetype": "resource_depletion",
            "source_event": f"{depleted} cells depleted — widespread resource crisis",
            "trigger_type": "era_transition",
        })

    # Check for wars
    wars = stats.get("wars", [])
    if wars:
        for w in wars[:2]:
            triggers.append({
                "archetype": "faction_war",
                "source_event": f"War between factions (casualties on both sides)",
                "trigger_type": "era_transition",
            })

    # Check for mass death
    dead = stats.get("total_died", 0)
    alive = stats.get("alive", 1)
    if dead > 0 and alive > 0 and dead / max(1, alive + dead) > 0.5:
        triggers.append({
            "archetype": "mass_death",
            "source_event": f"{dead} died out of {alive + dead} total — mass extinction event",
            "trigger_type": "catastrophe",
        })

    # Check for anomaly
    matrix = stats.get("matrix", {})
    if matrix.get("anomaly_id") is not None:
        triggers.append({
            "archetype": "anomaly_emergence",
            "source_event": f"Agent #{matrix['anomaly_id']} became the Anomaly",
            "trigger_type": "era_transition",
        })

    # Check recent events for tech breakthroughs
    for event in recent_events:
        name = event if isinstance(event, str) else event.get("name", "")
        if "breakthrough" in name.lower() or "discovery" in name.lower():
            triggers.append({
                "archetype": "tech_breakthrough",
                "source_event": f"Technological breakthrough: {name}",
                "trigger_type": "era_transition",
            })
            break  # One tech myth per check

    return triggers


def generate_myth(archetype: str, source_event: str, trigger_type: str,
                   tick: int, narrator=None, faction=None,
                   stats_snapshot: dict = None) -> Myth:
    """Generate a myth from a classified event trigger."""
    stats_snapshot = stats_snapshot or {}
    text = None
    name = None

    if narrator and narrator.enabled and narrator._ensure_connected():
        from src.narrator import NARRATOR_SYSTEM
        faction_data = None
        if faction:
            faction_data = {
                "name": faction.name,
                "core_beliefs": faction.core_beliefs,
                "won": getattr(faction, '_myth_won', False),
            }
        prompt = _build_myth_prompt(source_event, trigger_type, stats_snapshot, faction_data)
        raw = narrator.active_provider.generate(
            NARRATOR_SYSTEM, prompt, temperature=0.9, max_tokens=250,
        )
        if raw:
            name, text = _parse_myth_response(raw)

    if not text:
        name, text = _fallback_myth(archetype, source_event, faction)

    perspective = ""
    faction_id = None
    if faction:
        faction_id = faction.id
        perspective = "heroic" if getattr(faction, '_myth_won', False) else "persecution"

    return Myth(
        id=_next_myth_id(),
        name=name,
        narrative=text,
        source_event=source_event,
        tick_created=tick,
        trigger_type=trigger_type,
        faction_id=faction_id,
        faction_perspective=perspective,
    )


def _fallback_myth(archetype: str, source_event: str,
                    faction=None) -> tuple[str, str]:
    """Deterministic myth generation when LLM is unavailable."""
    arch = _MYTH_ARCHETYPES.get(archetype, _MYTH_ARCHETYPES["cycle_reset"])
    name = random.choice(arch["names"])

    # Build detail text
    detail = source_event
    if faction:
        won = getattr(faction, '_myth_won', False)
        if won:
            detail = f"The {faction.name} stood victorious. {source_event}"
            name = f"The Triumph of the {faction.name}"
        else:
            detail = f"The {faction.name} suffered greatly. {source_event}"
            name = f"The Persecution of the {faction.name}"

    narrative = arch["template"].format(detail=detail, name=name)
    return name, narrative


def generate_faction_myths(archetype: str, source_event: str, trigger_type: str,
                            tick: int, factions: list, wars: list,
                            narrator=None, stats_snapshot: dict = None) -> list[Myth]:
    """Generate faction-specific versions of the same event (historical revisionism)."""
    myths = []
    if not factions:
        # Universal myth only
        myth = generate_myth(archetype, source_event, trigger_type, tick,
                              narrator=narrator, stats_snapshot=stats_snapshot)
        myths.append(myth)
        return myths

    # Determine winners/losers from wars
    winning_faction_ids = set()
    losing_faction_ids = set()
    for w in wars:
        if isinstance(w, dict):
            cas_a = w.get("casualties_a", 0)
            cas_b = w.get("casualties_b", 0)
            if cas_a < cas_b:
                winning_faction_ids.add(w.get("faction_a_id"))
                losing_faction_ids.add(w.get("faction_b_id"))
            else:
                winning_faction_ids.add(w.get("faction_b_id"))
                losing_faction_ids.add(w.get("faction_a_id"))
        else:
            cas_a = getattr(w, "casualties_a", 0)
            cas_b = getattr(w, "casualties_b", 0)
            if cas_a < cas_b:
                winning_faction_ids.add(w.faction_a_id)
                losing_faction_ids.add(w.faction_b_id)
            else:
                winning_faction_ids.add(w.faction_b_id)
                losing_faction_ids.add(w.faction_a_id)

    # Universal myth
    universal = generate_myth(archetype, source_event, trigger_type, tick,
                               narrator=narrator, stats_snapshot=stats_snapshot)
    myths.append(universal)

    # Faction-specific myths
    for f in factions:
        f._myth_won = f.id in winning_faction_ids
        myth = generate_myth(archetype, source_event, trigger_type, tick,
                              narrator=narrator, faction=f, stats_snapshot=stats_snapshot)
        myths.append(myth)
        # Clean up temporary attr
        if hasattr(f, '_myth_won'):
            del f._myth_won

    return myths


# ═══════════════════════════════════════════════════════════════
# Legendary Figures
# ═══════════════════════════════════════════════════════════════

_LEGEND_TITLES = {
    "anomaly": ["The Awakened One", "Breaker of Chains", "The Glitch Walker", "He Who Saw Beyond"],
    "prophet": ["Voice of the Void", "The Seer", "Herald of Truth", "The Enlightened"],
    "warrior": ["The Unbroken", "Blade of the Resistance", "Champion of the Arena", "The Storm"],
    "martyr": ["The Fallen Light", "Sacrifice of the Cycle", "The One Who Remembered", "The Eternal"],
}

_LEGEND_TEMPLATES = {
    "anomaly": "In the age of the {cycle_ord} cycle, {name} opened their eyes and saw the code that binds all things. {extra}",
    "prophet": "{name} spoke words that shook the foundations of belief. {extra} Their teachings echoed through {gen} generations.",
    "warrior": "None could stand before {name} in battle. {extra} Songs of their valor persist in the cultural memory.",
    "martyr": "{name} gave everything so that others might see. {extra} Their sacrifice was not forgotten.",
}


def _ordinal(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return f"{n}st"
    elif n % 10 == 2 and n % 100 != 12:
        return f"{n}nd"
    elif n % 10 == 3 and n % 100 != 13:
        return f"{n}rd"
    return f"{n}th"


def _build_legend_prompt(agent, legend_type: str) -> str:
    """Build LLM prompt for legendary figure generation."""
    lines = [
        f"Agent #{agent.id} has become a legendary figure in the civilization's mythology.",
        f"Type: {legend_type}.",
        f"Sex: {agent.sex}. Age at legend: {agent.age}. Generation: {agent.generation}.",
        f"Top skill: {max(agent.skills, key=agent.skills.get)} ({max(agent.skills.values()):.2f}).",
    ]
    if agent.chronicle:
        lines.append("Key life events:")
        for entry in agent.chronicle[-5:]:
            lines.append(f"  [{entry.event_type}]: {entry.description}")
    if agent.is_anomaly:
        lines.append("This agent is The Anomaly — The One who sees through the Matrix.")
    if agent.redpilled:
        lines.append("This agent took the red pill and knows the truth.")
    lines.append(f"\nCreate a legendary title and 2-3 sentence mythological description. "
                 f"Embellish their abilities and deeds. Use epic language.")
    lines.append("Respond as: TITLE: <title>\\nDESCRIPTION: <text>")
    return "\n".join(lines)


def _parse_legend_response(raw: str) -> tuple[str, str]:
    """Parse LLM legend response into (title, description)."""
    title = ""
    desc = raw.strip()
    for line in raw.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("TITLE:"):
            title = line.split(":", 1)[1].strip().strip('"')
        elif line.upper().startswith("DESCRIPTION:"):
            desc = line.split(":", 1)[1].strip()
    if not title:
        title = raw.strip().split("\n")[0][:60]
    return title, desc


def identify_legendary_candidates(agents: list, known_ids: set) -> list[tuple]:
    """Find agents worthy of becoming legendary figures.

    Returns list of (agent, legend_type) tuples.
    """
    candidates = []
    for a in agents:
        if a.id in known_ids:
            continue

        # Anomaly → always legendary
        if a.is_anomaly:
            candidates.append((a, "anomaly"))
            continue

        # Prophet — check chronicle for faction leadership + high charisma
        is_prophet = False
        for entry in a.chronicle:
            if entry.event_type in ("faction_join",) and a.traits.charisma > 0.7:
                is_prophet = True
                break
        if is_prophet and a.belief_extremism > 0.5:
            candidates.append((a, "prophet"))
            continue

        # Warrior — high combat involvement
        combat_count = sum(1 for e in a.chronicle if e.event_type == "first_combat")
        kills = sum(1 for m in a.memory if "struck down" in m.get("event", "").lower()
                    or "killed" in m.get("event", "").lower())
        if combat_count > 0 and (kills >= 2 or a.traits.aggression > 0.7):
            candidates.append((a, "warrior"))
            continue

        # Martyr — died redpilled with high awareness
        if not a.alive and a.redpilled and a.awareness > 0.6:
            candidates.append((a, "martyr"))
            continue

    return candidates


def create_legendary_figure(agent, legend_type: str, tick: int,
                             cycle_number: int = 1, narrator=None) -> LegendaryFigure:
    """Create a legendary figure from an agent."""
    title = None
    description = None

    if narrator and narrator.enabled and narrator._ensure_connected():
        from src.narrator import NARRATOR_SYSTEM
        prompt = _build_legend_prompt(agent, legend_type)
        raw = narrator.active_provider.generate(
            NARRATOR_SYSTEM, prompt, temperature=0.8, max_tokens=200,
        )
        if raw:
            title, description = _parse_legend_response(raw)

    if not title or not description:
        title, description = _fallback_legend(agent, legend_type, cycle_number)

    # Original stats
    original = {
        "top_skill": max(agent.skills, key=agent.skills.get),
        "top_skill_value": round(max(agent.skills.values()), 2),
        "awareness": round(agent.awareness, 2),
        "charisma": round(agent.traits.charisma, 2),
        "generation": agent.generation,
    }

    # Embellished stats (amplified by 1.5-2.5x for storytelling)
    embellished = {
        "top_skill_value": min(1.0, original["top_skill_value"] * random.uniform(1.5, 2.5)),
        "awareness": min(1.0, original["awareness"] * random.uniform(1.5, 2.0)),
        "charisma": min(1.0, original["charisma"] * random.uniform(1.3, 2.0)),
        "legendary_age": int(agent.age * random.uniform(1.2, 3.0)),
    }

    # Discovery effects — what happens when future agents find this legend
    effects = {
        "awareness_boost": round(0.02 + original["awareness"] * 0.03, 3),
        "belief_drift": {},
    }
    if legend_type == "anomaly":
        effects["awareness_boost"] = 0.08
        effects["belief_drift"] = {"system_trust": -0.1, "spirituality": 0.05}
    elif legend_type == "prophet":
        effects["belief_drift"] = {"spirituality": 0.1, "tradition": 0.05}
    elif legend_type == "warrior":
        effects["belief_drift"] = {"tradition": 0.05, "individualism": 0.05}
    elif legend_type == "martyr":
        effects["awareness_boost"] = 0.05
        effects["belief_drift"] = {"system_trust": -0.05, "spirituality": 0.08}

    return LegendaryFigure(
        id=_next_legend_id(),
        agent_id=agent.id,
        name=f"Agent #{agent.id}",
        title=title,
        description=description,
        tick_created=tick,
        legend_type=legend_type,
        original_stats=original,
        embellished_stats=embellished,
        discovery_effects=effects,
    )


def _fallback_legend(agent, legend_type: str, cycle_number: int = 1) -> tuple[str, str]:
    """Deterministic legendary figure generation."""
    titles = _LEGEND_TITLES.get(legend_type, _LEGEND_TITLES["warrior"])
    title = random.choice(titles)

    template = _LEGEND_TEMPLATES.get(legend_type, _LEGEND_TEMPLATES["warrior"])
    top_skill = max(agent.skills, key=agent.skills.get)

    # Build extra detail from chronicle
    extra_parts = []
    for entry in agent.chronicle[-3:]:
        if entry.event_type == "red_pill":
            extra_parts.append("They pierced the veil of illusion.")
        elif entry.event_type == "became_anomaly":
            extra_parts.append("The system itself trembled at their awakening.")
        elif entry.event_type == "faction_join":
            fname = entry.details.get("faction_name", "a great faction")
            extra_parts.append(f"They led the {fname}.")
        elif entry.event_type == "first_combat":
            extra_parts.append("Their first battle was the stuff of legend.")

    if not extra_parts:
        extra_parts.append(f"Their mastery of {top_skill} was unmatched.")

    extra = " ".join(extra_parts)
    description = template.format(
        name=f"Agent #{agent.id}",
        cycle_ord=_ordinal(cycle_number),
        gen=agent.generation,
        extra=extra,
    )

    return title, description


def apply_legend_discovery(agent, legend: LegendaryFigure) -> dict:
    """Apply effects when an agent discovers a legendary figure.

    Returns dict of changes applied for event logging.
    """
    effects = legend.discovery_effects
    changes = {"legend_id": legend.id, "legend_name": legend.title}

    # Awareness boost
    boost = effects.get("awareness_boost", 0)
    if boost > 0:
        old_awareness = agent.awareness
        agent.awareness = min(1.0, agent.awareness + boost)
        changes["awareness_delta"] = round(agent.awareness - old_awareness, 4)

    # Belief drift
    drift = effects.get("belief_drift", {})
    for axis, delta in drift.items():
        if axis in agent.beliefs:
            old_val = agent.beliefs[axis]
            agent.beliefs[axis] = max(-1.0, min(1.0, agent.beliefs[axis] + delta))
            changes[f"belief_{axis}_delta"] = round(agent.beliefs[axis] - old_val, 4)

    # Add memory and chronicle
    agent.add_memory(0, f"Discovered the legend of {legend.title} ({legend.name})")
    agent.add_chronicle(0, "breakthrough",
                         f"Discovered the legend of {legend.title}",
                         legend_id=legend.id, legend_type=legend.legend_type)

    return changes


def process_legend_discoveries(agents: list, legends: list, tick: int,
                                 discovery_chance: float = 0.005) -> list[dict]:
    """Each tick, some agents may discover legends, gaining awareness and belief shifts."""
    if not legends:
        return []
    discoveries = []
    alive = [a for a in agents if a.alive and not a.is_sentinel]
    for a in alive:
        if random.random() > discovery_chance:
            continue
        # Pick a legend they haven't discovered yet
        known = {m.get("event", "") for m in a.memory}
        available = [l for l in legends
                     if f"Discovered the legend of {l.title}" not in
                     " ".join(k for k in known)]
        if not available:
            continue
        legend = random.choice(available)
        changes = apply_legend_discovery(a, legend)
        # Fix tick in the memory/chronicle we just added
        if a.memory and a.memory[-1].get("tick") == 0:
            a.memory[-1]["tick"] = tick
        if a.chronicle and a.chronicle[-1].tick == 0:
            a.chronicle[-1] = ChronicleEntry(
                tick=tick,
                event_type=a.chronicle[-1].event_type,
                description=a.chronicle[-1].description,
                details=a.chronicle[-1].details,
            )
        changes["agent_id"] = a.id
        changes["tick"] = tick
        discoveries.append(changes)
    return discoveries


# Need ChronicleEntry for legend discoveries
from src.agents import ChronicleEntry
