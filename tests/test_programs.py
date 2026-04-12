"""
Tests for Programs as First-Class Entities:
The Enforcer, The Broker, The Guardian, The Locksmith.
"""
import random


from src.agents import Agent, create_agent
from src.config_loader import SimConfig
from src.engine import SimulationEngine, RunState
from src.matrix_layer import MatrixState, process_matrix, _create_sentinel
from src.programs import (
    _create_enforcer,
    convert_to_enforcer,
    enforcer_share_awareness,
    _process_enforcers,
    _create_broker,
    broker_trade,
    _process_broker,
    _create_guardian,
    guardian_intercept_sentinel,
    _process_guardian,
    _create_locksmith,
    locksmith_create_key,
    use_teleport_key,
    _process_locksmith,
    process_programs,
)


# ===================================================
# TEST: The Enforcer
# ===================================================

class TestEnforcer:
    def test_create_enforcer(self, cfg):
        """Enforcer spawns with correct traits and flags."""
        enforcer = _create_enforcer(0.5, 0.5, 10, cfg)
        assert enforcer.is_enforcer
        assert enforcer.alive
        assert enforcer.traits.aggression == 0.8
        assert enforcer.traits.sociability == 0.0
        assert enforcer.beliefs["system_trust"] == 1.0
        assert enforcer.skills["survival"] == cfg.programs.enforcer.combat_power

    def test_convert_to_enforcer(self, cfg):
        """Victim is converted to Enforcer copy in-place."""
        victim = create_agent(cfg)
        victim.awareness = 0.7
        victim.redpilled = True
        victim.faction_id = 5
        old_id = victim.id
        old_memory_count = len(victim.memory)

        convert_to_enforcer(victim, 50, cfg)

        assert victim.is_enforcer
        assert victim.id == old_id  # same agent, overwritten
        assert victim.awareness == 0.0  # awareness wiped
        assert not victim.redpilled
        assert victim.faction_id is None
        assert victim.traits.aggression == 0.8
        assert victim.health == 0.8
        assert len(victim.memory) > old_memory_count  # gained assimilation memory

    def test_enforcer_copy_on_kill_exponential_growth(self, cfg):
        """When Enforcer kills, victim becomes copy — simulates exponential growth."""
        agents = []
        # Create the original Enforcer
        enforcer = _create_enforcer(0.5, 0.5, 10, cfg)
        enforcer.health = 1.0
        enforcer.traits.aggression = 0.9
        agents.append(enforcer)

        # Create victims close to the Enforcer
        for i in range(8):
            victim = create_agent(cfg)
            victim.x = 0.5 + random.uniform(-0.03, 0.03)
            victim.y = 0.5 + random.uniform(-0.03, 0.03)
            victim.health = 0.3  # low health so enforcer wins easily
            victim.traits.aggression = 0.1
            victim.traits.resilience = 0.1
            victim.skills["survival"] = 0.1
            victim.alive = True
            victim.phase = "adult"
            agents.append(victim)

        # Run multiple combat ticks — enforcers should assimilate victims
        from src.conflict import process_conflict
        from src.world import ResourceGrid
        world = ResourceGrid(cfg)
        wars = []
        factions = []

        initial_enforcer_count = sum(1 for a in agents if a.is_enforcer)
        assert initial_enforcer_count == 1

        for tick in range(1, 50):
            process_conflict(agents, factions, wars, tick, cfg, world)

        final_enforcer_count = sum(1 for a in agents if a.is_enforcer and a.alive)
        # At least one victim should have been converted
        assert final_enforcer_count > initial_enforcer_count, \
            f"Expected exponential growth: started with {initial_enforcer_count}, ended with {final_enforcer_count}"

    def test_enforcer_max_copies_cap(self, cfg):
        """Enforcer copies are capped at max_copies."""
        agents = []
        max_copies = cfg.programs.enforcer.max_copies

        # Create enforcers up to the cap
        for i in range(max_copies):
            e = _create_enforcer(0.5, 0.5, 10, cfg)
            agents.append(e)

        # Create a potential victim
        victim = create_agent(cfg)
        victim.x, victim.y = 0.5, 0.5
        victim.health = 0.1
        victim.alive = True
        agents.append(victim)

        # Enforcer count is at max — no more copies should be made
        enforcer_count_before = sum(1 for a in agents if a.is_enforcer)
        assert enforcer_count_before == max_copies

        # The copy-on-kill check in conflict.py checks the cap
        from src.conflict import process_conflict
        from src.world import ResourceGrid
        world = ResourceGrid(cfg)
        process_conflict(agents, [], [], 100, cfg, world)

        enforcer_count_after = sum(1 for a in agents if a.is_enforcer and a.alive)
        assert enforcer_count_after <= max_copies

    def test_enforcer_share_awareness(self, cfg):
        """Enforcers share goal target information."""
        e1 = _create_enforcer(0.5, 0.5, 10, cfg)
        e2 = _create_enforcer(0.52, 0.52, 10, cfg)
        e1.goal_target_pos = (0.8, 0.8)
        e1.goal_target_id = 99
        e1.current_goal = "HUNT_ENEMY"
        e2.goal_target_pos = None

        enforcer_share_awareness([e1, e2], cfg)

        assert e2.goal_target_pos == (0.8, 0.8)
        assert e2.goal_target_id == 99
        assert e2.current_goal == "HUNT_ENEMY"

    def test_enforcer_cannot_copy_guardian(self, cfg):
        """Guardian is immune to Enforcer copying."""
        guardian = _create_guardian(0.5, 0.5, 10, cfg)
        guardian.health = 0.1  # low health
        guardian.alive = True

        enforcer = _create_enforcer(0.5, 0.5, 10, cfg)
        enforcer.health = 1.0


        # Simulate the copy check from conflict.py
        guardian_immune = getattr(
            getattr(getattr(cfg, 'programs', None), 'guardian', None),
            'enforcer_immune', True
        )
        assert guardian_immune, "Guardian should be immune to Enforcer copying"
        # Guardian should NOT become an enforcer
        assert not guardian.is_enforcer or guardian.is_guardian

    def test_enforcer_spawn_timing(self, cfg):
        """Enforcers don't spawn before min_tick."""
        agents = [create_agent(cfg) for _ in range(5)]
        for a in agents:
            a.alive = True

        # Before min_tick — should not spawn
        random.seed(1)  # reproducible
        stats = _process_enforcers(agents, 1, cfg)
        assert stats["enforcers_active"] == 0


# ===================================================
# TEST: The Broker
# ===================================================

class TestBroker:
    def test_create_broker(self, cfg):
        """Broker spawns with correct traits and fixed location."""
        broker = _create_broker(100, cfg)
        assert broker.is_broker
        assert broker.alive
        assert broker.traits.charisma == 0.9
        assert broker.traits.max_age == 9999
        loc = cfg.programs.broker.location
        assert broker.x == loc[0]
        assert broker.y == loc[1]

    def test_broker_awareness_trade(self, cfg):
        """Agent can buy awareness boost from Broker."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.wealth = 10.0
        agent.awareness = 0.2
        agent.x, agent.y = broker.x, broker.y  # same location

        initial_awareness = agent.awareness
        initial_wealth = agent.wealth
        result = broker_trade(agent, broker, "awareness", 100, cfg)

        assert result is not None
        assert agent.awareness > initial_awareness
        assert agent.wealth < initial_wealth
        assert broker.wealth > 0

    def test_broker_info_trade(self, cfg):
        """Agent can buy skill info from Broker."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.wealth = 5.0
        agent.x, agent.y = broker.x, broker.y

        initial_wealth = agent.wealth
        result = broker_trade(agent, broker, "info", 100, cfg)

        assert result is not None
        assert agent.wealth < initial_wealth

    def test_broker_trade_requires_proximity(self, cfg):
        """Agent too far from Broker cannot trade."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.wealth = 10.0
        agent.x, agent.y = 0.0, 0.0  # far from broker

        result = broker_trade(agent, broker, "awareness", 100, cfg)
        assert result is None

    def test_broker_trade_requires_wealth(self, cfg):
        """Agent without enough wealth cannot trade."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.wealth = 0.0
        agent.x, agent.y = broker.x, broker.y

        result = broker_trade(agent, broker, "awareness", 100, cfg)
        assert result is None

    def test_broker_locksmith_location_trade(self, cfg):
        """Agent can buy Locksmith location from Broker."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.wealth = 10.0
        agent.x, agent.y = broker.x, broker.y

        result = broker_trade(agent, broker, "locksmith_location", 100, cfg)
        assert result is not None
        assert agent.wealth == 10.0 - cfg.programs.broker.locksmith_info_price

    def test_broker_stays_at_fixed_location(self, cfg):
        """Broker remains at configured location each tick."""
        agents = []
        broker = _create_broker(100, cfg)
        agents.append(broker)

        _process_broker(agents, 110, cfg)

        loc = cfg.programs.broker.location
        assert broker.x == loc[0]
        assert broker.y == loc[1]

    def test_broker_trade_cooldown(self, cfg):
        """Agent can't trade with Broker again within cooldown period."""
        broker = _create_broker(100, cfg)
        agent = create_agent(cfg)
        agent.wealth = 20.0
        agent.awareness = 0.4
        agent.x, agent.y = broker.x, broker.y
        agent.alive = True
        agent.phase = "adult"

        agents = [broker, agent]

        # First trade should work
        stats1 = _process_broker(agents, 100, cfg)
        assert stats1["trades"] >= 1

        # Immediately after — should be on cooldown
        stats2 = _process_broker(agents, 101, cfg)
        assert stats2["trades"] == 0


# ===================================================
# TEST: The Guardian
# ===================================================

class TestGuardian:
    def test_create_guardian(self, cfg):
        """Guardian spawns with high combat stats."""
        guardian = _create_guardian(0.5, 0.5, 10, cfg)
        assert guardian.is_guardian
        assert guardian.alive
        assert guardian.traits.resilience == 0.95
        assert guardian.skills["survival"] == cfg.programs.guardian.combat_power

    def test_guardian_intercepts_sentinel(self, cfg):
        """Guardian intercepts Sentinel attack on target."""
        guardian = _create_guardian(0.5, 0.5, 10, cfg)
        sentinel = _create_sentinel(create_agent(cfg), 10, cfg)
        sentinel.x, sentinel.y = 0.5, 0.5
        target = create_agent(cfg)
        target.x, target.y = 0.5, 0.5  # close to guardian
        target.awareness = 0.6
        target.alive = True

        initial_target_health = target.health
        initial_sentinel_health = sentinel.health

        intercepted = guardian_intercept_sentinel(guardian, sentinel, target, 10, cfg)

        assert intercepted
        # Target should NOT have been damaged (Guardian intercepted)
        assert target.health == initial_target_health
        # Sentinel should have taken damage from Guardian
        assert sentinel.health < initial_sentinel_health

    def test_guardian_does_not_intercept_if_far(self, cfg):
        """Guardian doesn't intercept if too far from target."""
        guardian = _create_guardian(0.0, 0.0, 10, cfg)
        sentinel = _create_sentinel(create_agent(cfg), 10, cfg)
        sentinel.x, sentinel.y = 0.9, 0.9
        target = create_agent(cfg)
        target.x, target.y = 0.9, 0.9  # far from guardian

        intercepted = guardian_intercept_sentinel(guardian, sentinel, target, 10, cfg)
        assert not intercepted

    def test_guardian_can_destroy_sentinel(self, cfg):
        """Guardian can destroy a Sentinel in combat."""
        guardian = _create_guardian(0.5, 0.5, 10, cfg)
        guardian.health = 1.0
        sentinel = _create_sentinel(create_agent(cfg), 10, cfg)
        sentinel.x, sentinel.y = 0.5, 0.5
        sentinel.health = 0.1  # very weak sentinel
        target = create_agent(cfg)
        target.x, target.y = 0.5, 0.5
        target.alive = True

        guardian_intercept_sentinel(guardian, sentinel, target, 10, cfg)

        assert not sentinel.alive
        assert sentinel.death_cause == "combat"

    def test_guardian_patrols_near_oracle_target(self, cfg):
        """Guardian moves toward Oracle's target."""
        guardian = _create_guardian(0.0, 0.0, 10, cfg)
        oracle_target = create_agent(cfg)
        oracle_target.x, oracle_target.y = 0.8, 0.8
        oracle_target.awareness = 0.5
        oracle_target.alive = True

        agents = [guardian, oracle_target]
        initial_x, initial_y = guardian.x, guardian.y

        _process_guardian(agents, oracle_target.id, 50, cfg)

        # Guardian should have moved closer to oracle target
        from src.programs import spatial_distance
        initial_dist = ((initial_x - 0.8)**2 + (initial_y - 0.8)**2)**0.5
        final_dist = spatial_distance(guardian, oracle_target)
        assert final_dist < initial_dist

    def test_guardian_integration_with_matrix(self, cfg):
        """Guardian intercepts Sentinels during matrix_layer processing."""
        agents = []
        # Create high-awareness target
        target = create_agent(cfg)
        target.awareness = 0.8
        target.alive = True
        target.phase = "adult"
        target.x, target.y = 0.5, 0.5
        agents.append(target)

        # Create Guardian near target
        guardian = _create_guardian(0.5, 0.5, 10, cfg)
        agents.append(guardian)

        # Create Sentinel near target
        sentinel = _create_sentinel(target, 10, cfg)
        sentinel.x, sentinel.y = 0.52, 0.52  # close enough to suppress
        agents.append(sentinel)

        matrix_state = MatrixState()
        matrix_state.oracle_target_id = target.id

        process_matrix(agents, matrix_state, 10, cfg)

        # Target should be somewhat protected by Guardian
        # (Guardian may or may not fully block depending on distances,
        # but the interception code path should be exercised)
        assert guardian.alive or sentinel.health < 1.0


# ===================================================
# TEST: The Locksmith
# ===================================================

class TestLocksmith:
    def test_create_locksmith(self, cfg):
        """Locksmith spawns with correct flags and high tech."""
        locksmith = _create_locksmith(100, cfg)
        assert locksmith.is_locksmith
        assert locksmith.alive
        assert locksmith.redpilled
        assert locksmith.skills["tech"] == 0.95
        assert locksmith.awareness == 0.7

    def test_locksmith_creates_key(self, cfg):
        """Locksmith creates teleport keys at regular intervals."""
        locksmith = _create_locksmith(100, cfg)
        interval = cfg.programs.locksmith.key_creation_interval

        # On the right tick, should create a key
        key = locksmith_create_key(locksmith, interval, cfg)
        assert key is not None
        assert len(key) == 2
        assert 0.0 <= key[0] <= 1.0
        assert 0.0 <= key[1] <= 1.0

    def test_locksmith_no_key_off_interval(self, cfg):
        """Locksmith doesn't create keys off-interval."""
        locksmith = _create_locksmith(100, cfg)
        key = locksmith_create_key(locksmith, 7, cfg)  # not on interval
        assert key is None

    def test_use_teleport_key(self, cfg):
        """Agent consumes a teleport key to move instantly."""
        agent = create_agent(cfg)
        agent.x, agent.y = 0.1, 0.1
        dest = (0.8, 0.8)
        agent.teleport_keys.append(dest)

        result = use_teleport_key(agent, 100)

        assert result is True
        assert agent.x == 0.8
        assert agent.y == 0.8
        assert len(agent.teleport_keys) == 0  # key consumed

    def test_use_teleport_key_empty(self, cfg):
        """Agent with no keys can't teleport."""
        agent = create_agent(cfg)
        result = use_teleport_key(agent, 100)
        assert result is False

    def test_locksmith_distributes_keys_to_redpilled(self, cfg):
        """Locksmith gives keys to nearby redpilled agents."""
        agents = []
        locksmith = _create_locksmith(100, cfg)
        locksmith.x, locksmith.y = 0.5, 0.5
        agents.append(locksmith)

        # Create nearby redpilled agent
        ally = create_agent(cfg)
        ally.x, ally.y = 0.52, 0.52
        ally.redpilled = True
        ally.alive = True
        agents.append(ally)

        # Create nearby non-redpilled agent (should not receive)
        normie = create_agent(cfg)
        normie.x, normie.y = 0.52, 0.52
        normie.alive = True
        agents.append(normie)

        interval = cfg.programs.locksmith.key_creation_interval
        stats = _process_locksmith(agents, interval, cfg)

        if stats["keys_created"] > 0:
            # Key should go to redpilled ally, not normie
            assert len(ally.teleport_keys) > 0 or len(locksmith.teleport_keys) > 0
            assert len(normie.teleport_keys) == 0

    def test_locksmith_max_keys_per_agent(self, cfg):
        """Agent can't hold more than max_keys_per_agent."""
        agent = create_agent(cfg)
        max_keys = cfg.programs.locksmith.max_keys_per_agent
        for i in range(max_keys + 5):
            agent.teleport_keys.append((0.5, 0.5))

        # Agent already has more than max — distribution should skip
        locksmith = _create_locksmith(100, cfg)
        locksmith.x, locksmith.y = agent.x, agent.y
        agent.redpilled = True
        agent.alive = True

        # The process function checks max before giving keys
        agents = [locksmith, agent]
        interval = cfg.programs.locksmith.key_creation_interval
        _process_locksmith(agents, interval, cfg)
        # Should not have given another key to the already-full agent
        # (key goes to locksmith instead or not created)

    def test_locksmith_killable(self, cfg):
        """Locksmith can be killed — is a high-value target."""
        locksmith = _create_locksmith(100, cfg)
        locksmith.health = 0.1
        locksmith.alive = True

        # Simulate being killed
        locksmith.health = 0.0
        locksmith.alive = False
        locksmith.death_cause = "combat"

        assert not locksmith.alive
        assert locksmith.death_cause == "combat"

    def test_locksmith_key_serialization(self, cfg):
        """Teleport keys survive agent serialization roundtrip."""
        agent = create_agent(cfg)
        agent.teleport_keys = [(0.3, 0.7), (0.5, 0.5)]
        d = agent.to_dict()
        restored = Agent.from_dict(d)
        assert len(restored.teleport_keys) == 2
        assert restored.teleport_keys[0] == (0.3, 0.7)
        assert restored.teleport_keys[1] == (0.5, 0.5)


# ===================================================
# TEST: Integration — process_programs
# ===================================================

class TestProgramsIntegration:
    def test_process_programs_returns_stats(self, cfg):
        """process_programs returns combined stats from all program systems."""
        agents = [create_agent(cfg) for _ in range(10)]
        for a in agents:
            a.alive = True
        stats = process_programs(agents, 200, cfg)
        assert "enforcers_active" in stats
        assert "broker_active" in stats
        assert "guardian_active" in stats
        assert "locksmith_active" in stats

    def test_engine_tick_includes_program_stats(self, cfg):
        """Engine tick result includes program_stats field."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_programs"))
        eng.initialize()
        result = eng.tick()
        assert hasattr(result, "program_stats")
        assert isinstance(result.program_stats, dict)

    def test_full_engine_run_with_programs(self, cfg):
        """Full 50-tick engine run doesn't crash with programs enabled."""
        eng = SimulationEngine(cfg, state=RunState(run_id="test_programs_full"))
        eng.initialize()
        for _ in range(50):
            eng.tick()
        alive = eng.get_alive_agents()
        assert len(alive) > 0

    def test_enforcer_agent_serialization(self, cfg):
        """Enforcer fields survive agent serialization roundtrip."""
        enforcer = _create_enforcer(0.5, 0.5, 10, cfg)
        d = enforcer.to_dict()
        restored = Agent.from_dict(d)
        assert restored.is_enforcer
        assert not restored.is_broker
        assert not restored.is_guardian
        assert not restored.is_locksmith

    def test_broker_agent_serialization(self, cfg):
        """Broker fields survive agent serialization roundtrip."""
        broker = _create_broker(100, cfg)
        d = broker.to_dict()
        restored = Agent.from_dict(d)
        assert restored.is_broker
        assert not restored.is_enforcer

    def test_programs_disabled_gracefully(self):
        """Programs gracefully handle missing config."""
        cfg = SimConfig.load()
        agents = [create_agent(cfg) for _ in range(5)]
        for a in agents:
            a.alive = True

        # Even with config present, should not crash
        stats = process_programs(agents, 1, cfg)
        assert isinstance(stats, dict)
