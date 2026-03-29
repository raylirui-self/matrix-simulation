"""Session state management and helper functions for the dashboard."""
from __future__ import annotations

import streamlit as st

from src.config_loader import SimConfig
from src.persistence import SimulationDB


def init_state():
    """Initialize all session state defaults."""
    defaults = {
        "db": None, "run_id": None, "engine": None,
        "narrator": None, "tick_history": [], "events_log": [],
        "narratives_log": [], "protagonist_thoughts": [],
        "scenario_name": None, "era_name": None, "cfg": None,
        "activity_feed": [],
        "achievements": [],
        "milestones_hit": [],
        "drama_feed": [],
        "peak_population": 0,
        "total_techs_unlocked": 0,
        "max_generation_seen": 0,
        "auto_run": False,
        "auto_run_speed": 5,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_db() -> SimulationDB:
    if st.session_state.db is None:
        cfg = get_cfg()
        st.session_state.db = SimulationDB(cfg.persistence.db_path)
    return st.session_state.db


def get_cfg() -> SimConfig:
    if st.session_state.cfg is None:
        try:
            st.session_state.cfg = SimConfig.load(scenario=st.session_state.scenario_name)
        except Exception:
            st.session_state.cfg = SimConfig.load()
    return st.session_state.cfg


def get_era(tick, pop, avg_intel, techs):
    """Determine the current civilization era based on progress."""
    tech_names = set(techs) if techs else set()
    if "industrialization" in tech_names:
        return ("Industrial Age", "Machines reshape the world", "#ffd700")
    if "trade_networks" in tech_names:
        return ("Trade Era", "Commerce connects communities", "#00ccff")
    if "mining" in tech_names:
        return ("Bronze Age", "Metal tools forge a new world", "#cd7f32")
    if "agriculture" in tech_names:
        return ("Agricultural Age", "Settled life begins", "#4a7a3a")
    if avg_intel > 0.3:
        return ("Age of Awakening", "Knowledge grows rapidly", "#aa66ff")
    if pop > 80:
        return ("Tribal Expansion", "Clans spread across the land", "#ff8844")
    if pop > 20:
        return ("Dawn of Tribes", "Small groups form bonds", "#00ff88")
    if pop > 0:
        return ("Genesis", "Life stirs in the void", "#5a8a5a")
    return ("The Void", "Nothing remains...", "#ff4466")


def generate_portrait_prompt(agent) -> str:
    """Generate an image generation prompt describing how this agent looks."""
    age_desc = {
        "infant": "a newborn baby",
        "child": "a young child",
        "adolescent": "a teenage youth",
        "adult": f"a {'man' if agent.sex == 'M' else 'woman'} in their prime",
        "elder": f"an aged {'man' if agent.sex == 'M' else 'woman'} with weathered features",
    }.get(agent.phase, "a person")

    descriptors = []
    if agent.traits.resilience > 0.7:
        descriptors.append("strong and battle-scarred")
    elif agent.traits.resilience < 0.3:
        descriptors.append("frail and delicate")
    if agent.traits.curiosity > 0.7:
        descriptors.append("with bright inquisitive eyes")
    elif agent.traits.curiosity < 0.3:
        descriptors.append("with a guarded cautious gaze")
    if agent.traits.charisma > 0.7:
        descriptors.append("radiating commanding presence")
    elif agent.traits.charisma < 0.3:
        descriptors.append("quiet and unassuming")
    if agent.traits.sociability > 0.7:
        descriptors.append("warm and approachable expression")
    elif agent.traits.sociability < 0.3:
        descriptors.append("distant and solitary")
    if agent.traits.aggression > 0.6:
        descriptors.append("fierce and intimidating")

    dom_emo = agent.dominant_emotion
    emo_desc = {
        "happiness": "a gentle smile",
        "fear": "wide fearful eyes and tense posture",
        "anger": "a furrowed brow and clenched jaw",
        "grief": "tear-streaked cheeks and hollow eyes",
        "hope": "an upward gaze full of determination",
    }.get(dom_emo, "a neutral expression")

    awareness_desc = ""
    if agent.is_anomaly:
        awareness_desc = "Eyes glowing with otherworldly green light, reality bending around them. "
    elif agent.redpilled:
        awareness_desc = "Eyes that see through the veil of reality, faint digital code reflected in their pupils. "
    elif agent.awareness > 0.5:
        awareness_desc = "A haunted look, as if they can see something others cannot. "
    elif agent.is_sentinel:
        awareness_desc = "Unnaturally perfect features, cold emotionless expression, wearing a dark suit. "
    elif agent.is_exile:
        awareness_desc = "Ancient and mysterious, with an aura of hidden power. "

    if agent.wealth > 5.0:
        clothing = "wearing ornate robes and jewelry"
    elif agent.wealth > 2.0:
        clothing = "in well-made practical clothing"
    elif agent.wealth > 0.5:
        clothing = "in simple hand-sewn garments"
    else:
        clothing = "in tattered rags"

    top_skill = max(agent.skills, key=agent.skills.get) if agent.skills else "survival"
    skill_prop = {
        "logic": "surrounded by geometric patterns and symbols",
        "creativity": "with colorful paint on their hands",
        "social": "standing among a circle of people",
        "survival": "holding a weathered tool",
        "tech": "near crude machines and inventions",
    }.get(top_skill, "")

    faction_desc = ""
    if agent.faction_id is not None:
        faction_desc = "bearing a faction symbol on their chest, "

    desc_str = ", ".join(descriptors[:3]) if descriptors else "ordinary features"
    prompt = (
        f"Portrait of {age_desc}, {desc_str}, {emo_desc}. "
        f"{awareness_desc}"
        f"{faction_desc}{clothing}, {skill_prop}. "
        f"Dark cinematic lighting, digital rain in background, Matrix-inspired color palette of black and green. "
        f"Highly detailed, concept art style."
    )
    return prompt.strip()


def check_achievements(engine, result):
    """Check and award milestones/achievements."""
    new_achievements = []
    ms = st.session_state.milestones_hit
    if isinstance(ms, set):
        ms = list(ms)
        st.session_state.milestones_hit = ms

    pop = result.alive_count
    tick = result.tick

    def _award(key, tier, name, desc):
        if key not in ms:
            ms.append(key)
            new_achievements.append((tier, name, desc))

    for threshold in [50, 100, 200, 300, 500]:
        if pop >= threshold:
            _award(f"pop_{threshold}", "gold", f"Population {threshold}!", f"Reached {threshold} souls at tick {tick}")

    if pop > st.session_state.peak_population:
        st.session_state.peak_population = pop

    if result.avg_generation > st.session_state.max_generation_seen:
        st.session_state.max_generation_seen = result.avg_generation
    for gen in [3, 5, 10, 15, 20]:
        if result.avg_generation >= gen:
            _award(f"gen_{gen}", "silver", f"Generation {gen}", f"Civilization endures {gen} generations")

    for bt in result.breakthroughs:
        _award(f"tech_{bt}", "bronze", f"Discovery: {bt}", f"Unlocked {bt} technology")

    for iq_level, label in [(0.2, "Curious Minds"), (0.4, "Enlightenment"), (0.6, "Brilliance"), (0.8, "Transcendence")]:
        if result.avg_intelligence >= iq_level:
            _award(f"iq_{iq_level}", "green", label, f"Average IQ reached {iq_level:.1f}")

    if pop > 20 and st.session_state.peak_population > 50:
        history = st.session_state.tick_history
        if len(history) > 10:
            recent_min = min(h.get("alive_count", 999) for h in history[-50:]) if len(history) >= 50 else pop
            if recent_min < 10:
                _award("phoenix", "gold", "Phoenix Rising!", "Recovered from near-extinction")

    for a in new_achievements:
        st.session_state.achievements.append(a)
    return new_achievements


def generate_drama(engine, result, prev_agents_snapshot):
    """Generate dramatic narrative from simulation events."""
    drama = []
    alive = engine.get_alive_agents()
    agent_map = {a.id: a for a in engine.agents}

    if result.births > 0:
        newborns = [a for a in alive if a.age == 0]
        for baby in newborns[:3]:
            parents = [agent_map.get(pid) for pid in baby.parent_ids]
            parent_names = []
            for p in parents:
                if p and p.is_protagonist and p.protagonist_name:
                    parent_names.append(p.protagonist_name)
                elif p:
                    parent_names.append(f"Agent #{p.id}")
            if len(parent_names) == 2:
                drama.append(("birth", f"A {'boy' if baby.sex == 'M' else 'girl'} is born to {parent_names[0]} & {parent_names[1]} (Gen {baby.generation})", result.tick))

    recently_dead = [a for a in engine.agents if not a.alive and any(
        m.get("tick") == result.tick and m.get("event") == "Died" for m in a.memory
    )]
    for dead in recently_dead[:2]:
        title = ""
        if dead.is_protagonist:
            title = f"Protagonist {dead.protagonist_name or ''} "
        elif dead.generation >= 3:
            title = f"Elder of Gen {dead.generation} "
        elif len(dead.child_ids) >= 3:
            title = f"Prolific parent "
        if title or dead.age > 60:
            drama.append(("death", f"{title}#{dead.id} has perished at age {dead.age} (IQ: {dead.intelligence:.2f}, {len(dead.child_ids)} children)", result.tick))

    for a in alive:
        for bond in a.bonds:
            if bond.bond_type == "mate" and bond.formed_at == result.tick and bond.target_id > a.id:
                target = agent_map.get(bond.target_id)
                if target:
                    drama.append(("bond", f"#{a.id} and #{target.id} have formed a mate bond (compatibility sparks fly!)", result.tick))

    for a in alive:
        for bond in a.bonds:
            if bond.bond_type == "rival" and bond.formed_at == result.tick and bond.target_id > a.id:
                target = agent_map.get(bond.target_id)
                if target:
                    drama.append(("drama", f"Rivalry erupts between #{a.id} and #{target.id}!", result.tick))

    for bt in result.breakthroughs:
        drama.append(("tech", f"BREAKTHROUGH: {bt} has been discovered! A new era dawns.", result.tick))

    return drama
