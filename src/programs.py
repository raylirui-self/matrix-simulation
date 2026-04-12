"""
Programs as First-Class Entities — The Enforcer, The Broker, The Guardian,
The Locksmith.

Special agent subtypes with unique behaviors that exist outside the normal
agent lifecycle. Called from engine.py tick loop after the Matrix layer.
"""
from __future__ import annotations

import math
import random
from typing import Optional

from src.agents import Agent, Bond, Traits, next_id, SKILL_NAMES, EMOTION_NAMES, BELIEF_AXES


def spatial_distance(a: Agent, b: Agent) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


# ═══════════════════════════════════════════════════
# The Enforcer
# ═══════════════════════════════════════════════════

def _create_enforcer(x: float, y: float, tick: int, cfg) -> Agent:
    """Spawn the original Enforcer agent near (x, y)."""
    ecfg = cfg.programs.enforcer
    override = ecfg.copy_trait_override
    enforcer = Agent(
        id=next_id(),
        sex=random.choice(["M", "F"]),
        traits=Traits(
            learning_rate=0.1,
            resilience=getattr(override, 'resilience', 0.8),
            curiosity=getattr(override, 'curiosity', 0.0),
            sociability=getattr(override, 'sociability', 0.0),
            charisma=0.1,
            aggression=getattr(override, 'aggression', 0.8),
            boldness=0.9,
            max_age=300,
        ),
        generation=0,
        x=max(0.0, min(1.0, x)),
        y=max(0.0, min(1.0, y)),
        health=1.0,
        is_enforcer=True,
        awareness=0.0,
        emotions={e: 0.0 for e in EMOTION_NAMES},
        beliefs={b: 0.0 for b in BELIEF_AXES},
    )
    enforcer.beliefs["system_trust"] = 1.0
    power = ecfg.combat_power
    enforcer.skills = {s: power for s in SKILL_NAMES}
    enforcer.skills["social"] = 0.0
    enforcer.intelligence = 0.5
    enforcer.phase = "adult"
    enforcer.add_memory(tick, "ENFORCER: Deployed to eliminate resistance")
    return enforcer


def convert_to_enforcer(victim: Agent, tick: int, cfg) -> None:
    """Convert a defeated agent into an Enforcer copy (in-place).
    Keeps memories but overrides traits and purpose."""
    ecfg = cfg.programs.enforcer
    override = ecfg.copy_trait_override
    victim.is_enforcer = True
    victim.is_sentinel = False
    victim.is_exile = False
    victim.redpilled = False
    victim.awareness = 0.0
    victim.health = 0.8  # reborn weakened
    victim.traits.aggression = getattr(override, 'aggression', 0.8)
    victim.traits.resilience = getattr(override, 'resilience', 0.8)
    victim.traits.sociability = getattr(override, 'sociability', 0.0)
    victim.traits.curiosity = getattr(override, 'curiosity', 0.0)
    victim.traits.boldness = 0.9
    victim.current_goal = "NONE"
    victim.goal_target_id = None
    victim.faction_id = None
    # Clear non-family bonds
    victim.bonds = [b for b in victim.bonds if b.bond_type == "family"]
    victim.add_memory(tick, "ASSIMILATED: Converted into Enforcer copy")


def enforcer_share_awareness(enforcers: list[Agent], cfg) -> None:
    """Enforcers share target location awareness with each other."""
    if len(enforcers) < 2:
        return
    radius = cfg.programs.enforcer.awareness_share_radius
    for e in enforcers:
        for other in enforcers:
            if e.id == other.id:
                continue
            if spatial_distance(e, other) < radius:
                # Share goal targets
                if other.goal_target_pos and not e.goal_target_pos:
                    e.goal_target_pos = other.goal_target_pos
                    e.goal_target_id = other.goal_target_id
                    e.current_goal = "HUNT_ENEMY"


def _process_enforcers(agents: list[Agent], tick: int, cfg) -> dict:
    """Enforcer tick: spawn if needed, share awareness, hunt targets."""
    ecfg = cfg.programs.enforcer
    if not ecfg.enabled:
        return {"enforcers_active": 0, "enforcer_spawned": False}

    alive = [a for a in agents if a.alive and getattr(a, 'location', 'simulation') != 'haven']
    enforcers = [a for a in alive if a.is_enforcer]
    stats = {"enforcers_active": len(enforcers), "enforcer_spawned": False}

    # Spawn initial enforcer if none exist
    if not enforcers and tick >= ecfg.min_tick:
        if random.random() < ecfg.spawn_chance:
            x, y = random.uniform(0.1, 0.9), random.uniform(0.1, 0.9)
            enforcer = _create_enforcer(x, y, tick, cfg)
            agents.append(enforcer)
            stats["enforcer_spawned"] = True
            stats["enforcers_active"] = 1
            enforcers = [enforcer]

    # Share awareness between copies
    enforcer_share_awareness(enforcers, cfg)

    # Enforcers hunt high-awareness non-enforcer agents
    non_enforcers = [a for a in alive if not a.is_enforcer and not a.is_sentinel
                     and not a.is_guardian]
    targets = sorted(non_enforcers, key=lambda a: -a.awareness)

    for e in enforcers:
        if not targets:
            break
        # Find nearest high-awareness target
        best = None
        best_dist = float('inf')
        for t in targets[:10]:  # check top 10 awareness targets
            d = spatial_distance(e, t)
            if d < best_dist:
                best = t
                best_dist = d

        if best:
            e.goal_target_id = best.id
            e.goal_target_pos = (best.x, best.y)
            e.current_goal = "HUNT_ENEMY"
            # Move toward target
            dx = best.x - e.x
            dy = best.y - e.y
            dist = math.sqrt(dx * dx + dy * dy) or 0.001
            speed = 0.04
            e.x = max(0.0, min(1.0, e.x + dx / dist * speed))
            e.y = max(0.0, min(1.0, e.y + dy / dist * speed))

    return stats


# ═══════════════════════════════════════════════════
# The Broker
# ═══════════════════════════════════════════════════

def _create_broker(tick: int, cfg) -> Agent:
    """Create the singleton Broker NPC."""
    bcfg = cfg.programs.broker
    loc = bcfg.location
    broker = Agent(
        id=next_id(),
        sex=random.choice(["M", "F"]),
        traits=Traits(
            learning_rate=0.3,
            resilience=0.7,
            curiosity=0.2,
            sociability=0.9,
            charisma=0.9,
            aggression=0.1,
            boldness=0.3,
            max_age=9999,  # effectively immortal
        ),
        generation=0,
        x=loc[0] if isinstance(loc, (list, tuple)) else 0.5,
        y=loc[1] if isinstance(loc, (list, tuple)) else 0.5,
        health=1.0,
        is_broker=True,
        awareness=0.5,  # knows the system but stays neutral
        emotions={e: 0.1 for e in EMOTION_NAMES},
        beliefs={b: 0.0 for b in BELIEF_AXES},
    )
    broker.skills = {s: 0.7 for s in SKILL_NAMES}
    broker.skills["social"] = 0.95
    broker.intelligence = 0.8
    broker.phase = "adult"
    broker.add_memory(tick, "THE BROKER: Open for business. Everything has a price.")
    return broker


def broker_trade(agent: Agent, broker: Agent, trade_type: str,
                 tick: int, cfg) -> Optional[str]:
    """Execute a trade between an agent and the Broker.
    Returns description of trade or None if failed."""
    bcfg = cfg.programs.broker
    dist = spatial_distance(agent, broker)
    if dist > bcfg.trade_radius:
        return None

    if trade_type == "awareness":
        price = bcfg.awareness_price
        if agent.wealth < price:
            return None
        agent.wealth -= price
        broker.wealth += price
        agent.awareness = min(1.0, agent.awareness + 0.1)
        agent.add_memory(tick, "Traded with the Broker: bought awareness boost")
        return f"Agent #{agent.id} bought awareness boost for {price} wealth"

    elif trade_type == "info":
        price = bcfg.info_price
        if agent.wealth < price:
            return None
        agent.wealth -= price
        broker.wealth += price
        # Random skill boost
        skill = random.choice(SKILL_NAMES)
        agent.skills[skill] = min(1.0, agent.skills[skill] + 0.05)
        agent.add_memory(tick, f"Traded with the Broker: bought secret {skill} knowledge")
        return f"Agent #{agent.id} bought {skill} info for {price} wealth"

    elif trade_type == "locksmith_location":
        price = bcfg.locksmith_info_price
        if agent.wealth < price:
            return None
        # Find the locksmith
        # (caller must pass locksmith location — handled in process_programs)
        agent.wealth -= price
        broker.wealth += price
        return f"Agent #{agent.id} bought Locksmith location for {price} wealth"

    # ── Black Market trades ──

    elif trade_type == "forbidden_knowledge":
        price = getattr(bcfg, 'forbidden_knowledge_price', 4.0)
        boost = getattr(bcfg, 'forbidden_knowledge_boost', 0.15)
        if agent.wealth < price:
            return None
        agent.wealth -= price
        broker.wealth += price
        agent.awareness = min(1.0, agent.awareness + boost)
        agent.add_memory(tick, "BLACK MARKET: Bought forbidden knowledge from the Broker — "
                         "the walls of reality thin")
        return f"Agent #{agent.id} bought forbidden knowledge for {price} wealth"

    elif trade_type == "memory_sacrifice":
        # Sacrifice a memory to gain forbidden knowledge (awareness boost)
        boost = getattr(bcfg, 'memory_sacrifice_awareness_boost', 0.12)
        if not agent.memory:
            return None
        sacrificed = agent.memory.pop(random.randint(0, len(agent.memory) - 1))
        agent.awareness = min(1.0, agent.awareness + boost)
        broker.wealth += 1.0  # Broker hoards information
        agent.add_memory(tick, "BLACK MARKET: Sacrificed a memory for forbidden knowledge — "
                         "something is gone but understanding grew")
        return f"Agent #{agent.id} sacrificed a memory for awareness boost"

    elif trade_type == "bond_sacrifice":
        # Sacrifice a friendship for power (skill boost)
        skill_boost = getattr(bcfg, 'bond_sacrifice_skill_boost', 0.08)
        friend_bonds = [b for b in agent.bonds if b.bond_type == "friend"]
        if not friend_bonds:
            return None
        sacrificed_bond = random.choice(friend_bonds)
        agent.bonds.remove(sacrificed_bond)
        broker.wealth += 2.0  # Broker profits from broken bonds
        for skill in SKILL_NAMES:
            agent.skills[skill] = min(1.0, agent.skills[skill] + skill_boost)
        agent.add_memory(tick, f"BLACK MARKET: Sacrificed friendship with #{sacrificed_bond.target_id} "
                         "for power — the Broker feeds on severed connections")
        return f"Agent #{agent.id} sacrificed bond with #{sacrificed_bond.target_id} for skill boost"

    elif trade_type == "oracle_prophecy":
        price = getattr(bcfg, 'oracle_prophecy_price', 6.0)
        if agent.wealth < price:
            return None
        agent.wealth -= price
        broker.wealth += price
        # Prophecy: reveal the current Anomaly or highest-awareness agent location
        # (The effect is a memory + awareness boost — the "knowledge" is the reward)
        agent.awareness = min(1.0, agent.awareness + 0.05)
        agent.beliefs["spirituality"] = min(1.0, agent.beliefs.get("spirituality", 0) + 0.1)
        agent.add_memory(tick, "BLACK MARKET: The Broker whispered a prophecy — "
                         "fragments of the Oracle's vision, sold for profit")
        return f"Agent #{agent.id} bought an Oracle prophecy for {price} wealth"

    elif trade_type == "locksmith_rumor":
        # Cheaper than exact location — gives approximate position
        price = getattr(bcfg, 'locksmith_info_price', 5.0) * 0.5
        if agent.wealth < price:
            return None
        agent.wealth -= price
        broker.wealth += price
        agent.add_memory(tick, "BLACK MARKET: The Broker hinted at the Locksmith's whereabouts")
        return f"Agent #{agent.id} bought Locksmith rumor for {price} wealth"

    return None


def _process_broker(agents: list[Agent], tick: int, cfg) -> dict:
    """Broker tick: spawn if needed, process nearby agent trades."""
    bcfg = cfg.programs.broker
    if not bcfg.enabled:
        return {"broker_active": False, "trades": 0}

    alive = [a for a in agents if a.alive and getattr(a, 'location', 'simulation') != 'haven']
    broker = next((a for a in alive if a.is_broker), None)
    stats = {"broker_active": False, "trades": 0}

    # Spawn broker at designated tick
    if broker is None and tick >= bcfg.spawn_tick:
        broker = _create_broker(tick, cfg)
        agents.append(broker)

    if broker is None or not broker.alive:
        return stats

    stats["broker_active"] = True
    # Broker stays at fixed location
    loc = bcfg.location
    broker.x = loc[0] if isinstance(loc, (list, tuple)) else 0.5
    broker.y = loc[1] if isinstance(loc, (list, tuple)) else 0.5
    broker.health = min(1.0, broker.health + 0.01)  # slow regen

    # Process trades with nearby agents
    non_programs = [a for a in alive if not a.is_broker and not a.is_sentinel
                    and not a.is_enforcer]
    for agent in non_programs:
        dist = spatial_distance(agent, broker)
        if dist > bcfg.trade_radius:
            continue

        # Check cooldown via memory
        recent_trades = [m for m in agent.memory[-5:]
                         if "Traded with the Broker" in m.get("event", "")]
        if recent_trades:
            last_trade_tick = recent_trades[-1].get("tick", 0)
            if tick - last_trade_tick < bcfg.trade_cooldown:
                continue

        # Agent decides what to trade for based on needs
        # High-awareness agents access the Black Market
        fk_price = getattr(bcfg, 'forbidden_knowledge_price', 4.0)
        prophecy_price = getattr(bcfg, 'oracle_prophecy_price', 6.0)
        if agent.awareness > 0.5 and agent.redpilled:
            # Black Market: forbidden knowledge (strongest awareness boost)
            if agent.wealth >= fk_price:
                result = broker_trade(agent, broker, "forbidden_knowledge", tick, cfg)
                if result:
                    stats["trades"] += 1
                    stats.setdefault("black_market_trades", 0)
                    stats["black_market_trades"] += 1
                    continue
            # Black Market: sacrifice a memory for awareness
            if agent.memory and len(agent.memory) > 3:
                if random.random() < 0.2:  # not every aware agent is desperate enough
                    result = broker_trade(agent, broker, "memory_sacrifice", tick, cfg)
                    if result:
                        stats["trades"] += 1
                        stats.setdefault("black_market_trades", 0)
                        stats["black_market_trades"] += 1
                        continue
            # Black Market: sacrifice a bond for power
            friend_bonds = [b for b in agent.bonds if b.bond_type == "friend"]
            if friend_bonds and random.random() < 0.1:  # rare desperation
                result = broker_trade(agent, broker, "bond_sacrifice", tick, cfg)
                if result:
                    stats["trades"] += 1
                    stats.setdefault("black_market_trades", 0)
                    stats["black_market_trades"] += 1
                    continue
            # Black Market: Oracle prophecy
            if agent.wealth >= prophecy_price and agent.beliefs.get("spirituality", 0) > 0.3:
                result = broker_trade(agent, broker, "oracle_prophecy", tick, cfg)
                if result:
                    stats["trades"] += 1
                    stats.setdefault("black_market_trades", 0)
                    stats["black_market_trades"] += 1
                    continue

        # Standard trades for less-aware agents
        if agent.awareness > 0.3 and agent.wealth >= bcfg.awareness_price:
            result = broker_trade(agent, broker, "awareness", tick, cfg)
            if result:
                stats["trades"] += 1
        elif agent.wealth >= bcfg.info_price:
            result = broker_trade(agent, broker, "info", tick, cfg)
            if result:
                stats["trades"] += 1

    return stats


# ═══════════════════════════════════════════════════
# The Guardian
# ═══════════════════════════════════════════════════

def _create_guardian(x: float, y: float, tick: int, cfg) -> Agent:
    """Create the Guardian — Oracle's bodyguard."""
    gcfg = cfg.programs.guardian
    guardian = Agent(
        id=next_id(),
        sex=random.choice(["M", "F"]),
        traits=Traits(
            learning_rate=0.2,
            resilience=0.95,
            curiosity=0.1,
            sociability=0.3,
            charisma=0.5,
            aggression=0.7,
            boldness=0.8,
            max_age=500,
        ),
        generation=0,
        x=max(0.0, min(1.0, x)),
        y=max(0.0, min(1.0, y)),
        health=1.0,
        is_guardian=True,
        awareness=0.3,
        emotions={e: 0.0 for e in EMOTION_NAMES},
        beliefs={b: 0.0 for b in BELIEF_AXES},
    )
    guardian.beliefs["system_trust"] = -0.5  # distrusts the system
    power = gcfg.combat_power
    guardian.skills = {s: power for s in SKILL_NAMES}
    guardian.intelligence = 0.7
    guardian.phase = "adult"
    guardian.add_memory(tick, "THE GUARDIAN: Sworn to protect those who seek the truth")
    return guardian


def guardian_intercept_sentinel(guardian: Agent, sentinel: Agent,
                                 target: Agent, tick: int, cfg) -> bool:
    """Guardian intercepts a Sentinel attack on an Oracle-guided agent.
    Returns True if interception happened."""
    gcfg = cfg.programs.guardian
    dist_to_target = spatial_distance(guardian, target)
    if dist_to_target > gcfg.interception_radius:
        return False

    # Guardian fights the sentinel instead
    g_power = (guardian.traits.aggression * 0.3 + guardian.traits.resilience * 0.3 +
               guardian.health * 0.2 + guardian.skills.get("survival", 0) * 0.2)
    s_power = (sentinel.traits.aggression * 0.3 + sentinel.traits.resilience * 0.25 +
               sentinel.health * 0.25 + sentinel.skills.get("survival", 0) * 0.2)

    # Guardian takes reduced damage, deals more
    damage_to_sentinel = g_power * 0.15 * random.uniform(0.8, 1.2)
    damage_to_guardian = s_power * 0.08 * random.uniform(0.5, 1.0)

    sentinel.health = max(0.0, sentinel.health - damage_to_sentinel)
    guardian.health = max(0.0, guardian.health - damage_to_guardian)

    if sentinel.health <= 0:
        sentinel.alive = False
        sentinel.death_cause = "combat"
        sentinel.add_memory(tick, f"Destroyed by Guardian #{guardian.id}")
        guardian.add_memory(tick, f"Destroyed Sentinel #{sentinel.id} protecting #{target.id}")
    else:
        guardian.add_memory(tick, f"Intercepted Sentinel #{sentinel.id} attack on #{target.id}")
        sentinel.add_memory(tick, f"Blocked by Guardian #{guardian.id}")

    return True


def _process_guardian(agents: list[Agent], oracle_target_id: Optional[int],
                      tick: int, cfg) -> dict:
    """Guardian tick: spawn if needed, patrol near Oracle-guided agents."""
    gcfg = cfg.programs.guardian
    if not gcfg.enabled:
        return {"guardian_active": False, "interceptions": 0}

    alive = [a for a in agents if a.alive and getattr(a, 'location', 'simulation') != 'haven']
    guardian = next((a for a in alive if a.is_guardian), None)
    stats = {"guardian_active": False, "interceptions": 0}

    # Spawn guardian if none exists
    if guardian is None and tick >= gcfg.min_tick:
        if random.random() < gcfg.spawn_chance:
            # Spawn near the Oracle's current target or a high-awareness agent
            high_awareness = sorted(
                [a for a in alive if not a.is_sentinel and a.awareness > 0.3],
                key=lambda a: -a.awareness
            )
            if high_awareness:
                target = high_awareness[0]
                guardian = _create_guardian(target.x, target.y, tick, cfg)
            else:
                guardian = _create_guardian(0.5, 0.5, tick, cfg)
            agents.append(guardian)

    if guardian is None or not guardian.alive:
        return stats

    stats["guardian_active"] = True
    guardian.health = min(1.0, guardian.health + 0.005)  # slow regen

    # Patrol: move toward Oracle target or highest-awareness agent that's received guidance
    patrol_target = None
    if oracle_target_id:
        patrol_target = next((a for a in alive if a.id == oracle_target_id), None)
    if not patrol_target:
        # Patrol near highest-awareness non-sentinel
        candidates = sorted(
            [a for a in alive if not a.is_sentinel and not a.is_enforcer
             and a.awareness > 0.3],
            key=lambda a: -a.awareness
        )
        if candidates:
            patrol_target = candidates[0]

    if patrol_target:
        dx = patrol_target.x - guardian.x
        dy = patrol_target.y - guardian.y
        dist = math.sqrt(dx * dx + dy * dy) or 0.001
        if dist > gcfg.patrol_radius * 0.5:
            speed = 0.03
            guardian.x = max(0.0, min(1.0, guardian.x + dx / dist * speed))
            guardian.y = max(0.0, min(1.0, guardian.y + dy / dist * speed))

    return stats


# ═══════════════════════════════════════════════════
# The Locksmith
# ═══════════════════════════════════════════════════

def _create_locksmith(tick: int, cfg) -> Agent:
    """Create the Locksmith — rare, creates teleportation keys."""
    locksmith = Agent(
        id=next_id(),
        sex=random.choice(["M", "F"]),
        traits=Traits(
            learning_rate=0.6,
            resilience=0.4,
            curiosity=0.8,
            sociability=0.5,
            charisma=0.6,
            aggression=0.1,
            boldness=0.4,
            max_age=150,
        ),
        generation=0,
        x=random.uniform(0.1, 0.9),
        y=random.uniform(0.1, 0.9),
        health=0.8,  # fragile
        is_locksmith=True,
        awareness=0.7,  # highly aware
        redpilled=True,
        emotions={e: 0.1 for e in EMOTION_NAMES},
        beliefs={b: 0.0 for b in BELIEF_AXES},
    )
    locksmith.beliefs["system_trust"] = -0.8
    locksmith.skills = {s: 0.6 for s in SKILL_NAMES}
    locksmith.skills["tech"] = 0.95
    locksmith.skills["logic"] = 0.9
    locksmith.intelligence = 0.85
    locksmith.phase = "adult"
    locksmith.add_memory(tick, "THE LOCKSMITH: I make doors where there are none")
    return locksmith


def locksmith_create_key(locksmith: Agent, tick: int, cfg) -> Optional[tuple]:
    """Locksmith creates a teleport key to a random destination.
    Returns (dest_x, dest_y) or None."""
    lcfg = cfg.programs.locksmith
    if tick % lcfg.key_creation_interval != 0:
        return None

    # Generate a key destination within key_range of locksmith
    angle = random.uniform(0, 2 * math.pi)
    dist = random.uniform(0.05, lcfg.key_range)
    dest_x = max(0.0, min(1.0, locksmith.x + math.cos(angle) * dist))
    dest_y = max(0.0, min(1.0, locksmith.y + math.sin(angle) * dist))
    return (round(dest_x, 4), round(dest_y, 4))


def use_teleport_key(agent: Agent, tick: int) -> bool:
    """Agent uses a teleport key to instantly move to destination.
    Returns True if key was consumed."""
    if not agent.teleport_keys:
        return False
    dest = agent.teleport_keys.pop(0)
    agent.x = dest[0]
    agent.y = dest[1]
    agent.add_memory(tick, f"Used teleport key to ({dest[0]:.2f}, {dest[1]:.2f})")
    return True


def _process_locksmith(agents: list[Agent], tick: int, cfg) -> dict:
    """Locksmith tick: spawn if needed, create and distribute keys."""
    lcfg = cfg.programs.locksmith
    if not lcfg.enabled:
        return {"locksmith_active": False, "keys_created": 0}

    alive = [a for a in agents if a.alive and getattr(a, 'location', 'simulation') != 'haven']
    locksmith = next((a for a in alive if a.is_locksmith), None)
    stats = {"locksmith_active": False, "keys_created": 0}

    # Spawn locksmith (rare)
    if locksmith is None and tick >= lcfg.min_tick:
        if random.random() < lcfg.spawn_chance:
            locksmith = _create_locksmith(tick, cfg)
            agents.append(locksmith)

    if locksmith is None or not locksmith.alive:
        return stats

    stats["locksmith_active"] = True

    # Create keys periodically
    key = locksmith_create_key(locksmith, tick, cfg)
    if key:
        # Give key to nearby allied agents (redpilled or anomaly)
        nearby_allies = [
            a for a in alive
            if a.id != locksmith.id
            and not a.is_sentinel and not a.is_enforcer
            and (a.redpilled or a.is_anomaly)
            and spatial_distance(a, locksmith) < 0.15
            and len(a.teleport_keys) < lcfg.max_keys_per_agent
        ]
        if nearby_allies:
            recipient = random.choice(nearby_allies)
            recipient.teleport_keys.append(key)
            recipient.add_memory(tick, f"Received teleport key from the Locksmith -> ({key[0]:.2f}, {key[1]:.2f})")
            locksmith.add_memory(tick, f"Gave teleport key to #{recipient.id}")
            stats["keys_created"] = 1
        else:
            # Locksmith holds key for self
            if len(locksmith.teleport_keys) < lcfg.max_keys_per_agent:
                locksmith.teleport_keys.append(key)
                stats["keys_created"] = 1

    # Locksmith wanders (not fixed location like Broker)
    locksmith.x = max(0.0, min(1.0, locksmith.x + random.gauss(0, 0.01)))
    locksmith.y = max(0.0, min(1.0, locksmith.y + random.gauss(0, 0.01)))

    return stats


# ═══════════════════════════════════════════════════
# Main entry point — called from engine.py
# ═══════════════════════════════════════════════════

def process_programs(agents: list[Agent], tick: int, cfg,
                     oracle_target_id: Optional[int] = None) -> dict:
    """Run one tick of all Program systems. Returns combined stats."""
    if not hasattr(cfg, 'programs'):
        return {}

    enforcer_stats = _process_enforcers(agents, tick, cfg)
    broker_stats = _process_broker(agents, tick, cfg)
    guardian_stats = _process_guardian(agents, oracle_target_id, tick, cfg)
    locksmith_stats = _process_locksmith(agents, tick, cfg)

    return {
        **enforcer_stats,
        **broker_stats,
        **guardian_stats,
        **locksmith_stats,
    }
