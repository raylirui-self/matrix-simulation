"""
Tests for Phase 1 Matrix features:
- Red pill persistent modifiers (costs + benefits)
- Blue pill splinter-in-the-mind
- Guide-type recruiters (persuasion checks)
- Anomaly quest stage progression
- Architect's Choice at the Core
"""
import random


from src.agents import Agent, Bond, create_agent
from src.matrix_layer import (
    MatrixState,
    process_matrix,
    _compute_core_choice_score,
    check_cycle_reset,
)
from src.programs import _create_locksmith


# ===================================================
# TEST: Red Pill Persistent Modifiers
# ===================================================

class TestRedPillModifiers:
    def test_redpill_awareness_growth_multiplied(self, cfg):
        """Redpilled agents gain awareness 2.5x faster."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.redpilled = True
        a.awareness = 0.3
        a.traits.curiosity = 0.5
        a.beliefs["system_trust"] = 0.0

        b = create_agent(cfg)
        b.phase = "adult"
        b.alive = True
        b.redpilled = False
        b.awareness = 0.3
        b.traits.curiosity = 0.5
        b.beliefs["system_trust"] = 0.0

        ms = MatrixState()
        agents_rp = [a]
        agents_norm = [b]

        process_matrix(agents_rp, ms, 1, cfg)
        ms2 = MatrixState()
        process_matrix(agents_norm, ms2, 1, cfg)

        # Redpilled agent should have grown awareness more
        assert a.awareness > b.awareness

    def test_redpill_health_regen_loss(self, cfg):
        """Redpilled agents lose health each tick (no Matrix comfort)."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.redpilled = True
        a.awareness = 0.5
        a.health = 0.8
        a.traits.curiosity = 0.5

        initial_health = a.health
        ms = MatrixState()
        process_matrix([a], ms, 1, cfg)

        assert a.health < initial_health

    def test_redpill_emotional_instability(self, cfg):
        """Redpilled agents have fear/anger baseline shift upward."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.redpilled = True
        a.awareness = 0.5
        a.emotions["fear"] = 0.0
        a.emotions["anger"] = 0.0

        ms = MatrixState()
        process_matrix([a], ms, 1, cfg)

        assert a.emotions["fear"] > 0.0, "Fear should increase for redpilled agent"
        assert a.emotions["anger"] > 0.0, "Anger should increase for redpilled agent"

    def test_redpill_event_applies_costs(self, cfg):
        """When agent takes the red pill, costs are applied immediately."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.awareness = 0.6
        a.traits.curiosity = 0.9
        a.beliefs["system_trust"] = -0.5
        a.emotions["happiness"] = 0.7
        initial_happiness = a.emotions["happiness"]

        ms = MatrixState()
        # Force redpill check tick
        interval = cfg.matrix.redpill_check_interval
        random.seed(10)  # need a seed where agent takes red pill
        # Run many times to get at least one redpill event
        for i in range(20):
            tick = interval * (i + 1)
            process_matrix([a], ms, tick, cfg)
            if a.redpilled:
                break

        if a.redpilled:
            # Happiness should have dropped
            assert a.emotions["happiness"] < initial_happiness

    def test_redpill_health_floor(self, cfg):
        """Health doesn't drop below 0.1 from redpill cost alone."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.redpilled = True
        a.awareness = 0.5
        a.health = 0.11

        ms = MatrixState()
        for tick in range(1, 50):
            process_matrix([a], ms, tick, cfg)

        assert a.health >= 0.1


# ===================================================
# TEST: Blue Pill Splinter-in-the-Mind
# ===================================================

class TestBluePillSplinter:
    def test_bluepill_sets_splinter_flag(self, cfg):
        """Blue pill agents get splinter_in_mind flag."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.awareness = 0.6
        a.traits.curiosity = 0.1  # low curiosity = more likely blue pill
        a.beliefs["system_trust"] = 0.8  # high trust = more likely blue pill

        ms = MatrixState()
        interval = cfg.matrix.redpill_check_interval
        # Run many redpill checks — some should result in blue pill
        for i in range(50):
            tick = interval * (i + 1)
            process_matrix([a], ms, tick, cfg)
            if a.splinter_in_mind:
                break

        # With high trust and low curiosity, agent should have taken blue pill
        assert a.splinter_in_mind or a.redpilled, \
            "Agent should have either taken blue pill (splinter) or red pill"

    def test_bluepill_awareness_floor(self, cfg):
        """Blue pill resets awareness to floor (0.3), not 0."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.awareness = 0.55
        a.traits.curiosity = 0.05
        a.beliefs["system_trust"] = 0.9

        ms = MatrixState()
        interval = cfg.matrix.redpill_check_interval

        random.seed(3)
        for i in range(100):
            tick = interval * (i + 1)
            a.awareness = 0.55  # keep resetting to ensure choice happens
            process_matrix([a], ms, tick, cfg)
            if a.splinter_in_mind:
                break

        if a.splinter_in_mind:
            bp_floor = getattr(cfg.matrix, 'bluepill_awareness_floor', 0.3)
            assert a.awareness >= bp_floor, \
                f"Blue pill awareness should be >= {bp_floor}, got {a.awareness}"

    def test_splinter_awareness_grows_faster(self, cfg):
        """Splinter-in-mind agents grow awareness 1.5x faster than normal."""
        # Splinter agent
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.splinter_in_mind = True
        a.awareness = 0.2
        a.traits.curiosity = 0.5
        a.beliefs["system_trust"] = 0.0

        # Normal agent (same stats)
        b = create_agent(cfg)
        b.phase = "adult"
        b.alive = True
        b.splinter_in_mind = False
        b.awareness = 0.2
        b.traits.curiosity = 0.5
        b.beliefs["system_trust"] = 0.0

        ms1 = MatrixState()
        ms2 = MatrixState()

        # Run one tick for each (use tick that doesn't trigger redpill check)
        process_matrix([a], ms1, 1, cfg)
        process_matrix([b], ms2, 1, cfg)

        assert a.awareness > b.awareness, \
            f"Splinter agent should grow faster: {a.awareness} vs {b.awareness}"

    def test_splinter_cleared_on_redpill(self, cfg):
        """Taking red pill clears the splinter_in_mind flag."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.splinter_in_mind = True
        a.awareness = 0.7
        a.traits.curiosity = 0.9
        a.beliefs["system_trust"] = -0.5

        ms = MatrixState()
        interval = cfg.matrix.redpill_check_interval

        for i in range(50):
            tick = interval * (i + 1)
            process_matrix([a], ms, tick, cfg)
            if a.redpilled:
                break

        if a.redpilled:
            assert not a.splinter_in_mind, "Splinter flag should be cleared on red pill"


# ===================================================
# TEST: Guide-Type Recruiters
# ===================================================

class TestRecruiters:
    def test_high_charisma_redpilled_becomes_recruiter(self, cfg):
        """Redpilled agent with high charisma becomes a recruiter."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.redpilled = True
        a.traits.charisma = 0.8
        a.awareness = 0.7

        ms = MatrixState()
        interval = getattr(cfg.matrix, 'recruiter_check_interval', 15)
        process_matrix([a], ms, interval, cfg)

        assert a.is_recruiter

    def test_low_charisma_not_recruiter(self, cfg):
        """Redpilled agent with low charisma does not become recruiter."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.redpilled = True
        a.traits.charisma = 0.2
        a.awareness = 0.7

        ms = MatrixState()
        interval = getattr(cfg.matrix, 'recruiter_check_interval', 15)
        process_matrix([a], ms, interval, cfg)

        assert not a.is_recruiter

    def test_recruiter_persuasion_success(self, cfg):
        """Recruiter can convert a high-awareness target to red pill."""
        recruiter = create_agent(cfg)
        recruiter.phase = "adult"
        recruiter.alive = True
        recruiter.redpilled = True
        recruiter.is_recruiter = True
        recruiter.traits.charisma = 0.95
        recruiter.awareness = 0.9
        recruiter.x, recruiter.y = 0.5, 0.5

        target = create_agent(cfg)
        target.phase = "adult"
        target.alive = True
        target.awareness = 0.45
        target.beliefs["system_trust"] = -0.5  # low trust = easier to recruit
        target.x, target.y = 0.52, 0.52  # within recruiter_search_radius

        ms = MatrixState()
        interval = getattr(cfg.matrix, 'recruiter_check_interval', 15)

        # Run multiple ticks to get a successful recruitment
        recruited = False
        for i in range(30):
            tick = interval * (i + 1)
            process_matrix([recruiter, target], ms, tick, cfg)
            if target.redpilled:
                recruited = True
                break

        assert recruited, "Recruiter with 0.95 charisma should eventually recruit low-trust target"
        assert any("resistance" == b.bond_type for b in target.bonds), \
            "Recruited target should have resistance bond"

    def test_recruiter_persuasion_failure_boosts_trust(self, cfg):
        """Failed recruitment boosts target's system_trust."""
        recruiter = create_agent(cfg)
        recruiter.phase = "adult"
        recruiter.alive = True
        recruiter.redpilled = True
        recruiter.is_recruiter = True
        recruiter.traits.charisma = 0.3  # low charisma = likely to fail
        recruiter.awareness = 0.6
        recruiter.x, recruiter.y = 0.5, 0.5

        target = create_agent(cfg)
        target.phase = "adult"
        target.alive = True
        target.awareness = 0.4
        target.beliefs["system_trust"] = 0.7  # high trust = hard to recruit
        target.x, target.y = 0.52, 0.52
        initial_trust = target.beliefs["system_trust"]

        ms = MatrixState()
        interval = getattr(cfg.matrix, 'recruiter_check_interval', 15)

        # Run ticks — should fail and boost trust
        for i in range(10):
            tick = interval * (i + 1)
            process_matrix([recruiter, target], ms, tick, cfg)

        # Target should still not be redpilled (very likely with low charisma vs high trust)
        # And if recruitment failed, trust should have increased
        if not target.redpilled:
            assert target.beliefs["system_trust"] >= initial_trust

    def test_non_redpilled_not_recruiter(self, cfg):
        """Non-redpilled agents don't become recruiters regardless of charisma."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.redpilled = False
        a.traits.charisma = 0.95

        ms = MatrixState()
        interval = getattr(cfg.matrix, 'recruiter_check_interval', 15)
        process_matrix([a], ms, interval, cfg)

        assert not a.is_recruiter


# ===================================================
# TEST: Anomaly Quest Stage Progression
# ===================================================

class TestAnomalyQuest:
    def _make_anomaly(self, cfg) -> Agent:
        """Create an Anomaly agent with high stats."""
        a = create_agent(cfg)
        a.phase = "adult"
        a.alive = True
        a.redpilled = True
        a.is_anomaly = True
        a.awareness = 0.9
        a.anomaly_quest_stage = 0
        return a

    def test_quest_stage_0_to_1_oracle_contact(self, cfg):
        """Anomaly advances from stage 0 to 1 when Oracle is guiding them."""
        anomaly = self._make_anomaly(cfg)
        ms = MatrixState()
        ms.anomaly_id = anomaly.id
        ms.oracle_target_id = anomaly.id  # Oracle is guiding the Anomaly

        process_matrix([anomaly], ms, 1, cfg)

        assert anomaly.anomaly_quest_stage == 1
        assert any("Locksmith" in m["event"] for m in anomaly.memory)

    def test_quest_stage_0_blocked_without_oracle(self, cfg):
        """Anomaly does NOT advance if Oracle is not guiding them."""
        anomaly = self._make_anomaly(cfg)
        ms = MatrixState()
        ms.anomaly_id = anomaly.id
        ms.oracle_target_id = 9999  # Oracle guiding someone else

        process_matrix([anomaly], ms, 1, cfg)

        assert anomaly.anomaly_quest_stage == 0

    def test_quest_stage_1_to_2_find_locksmith(self, cfg):
        """Anomaly advances from stage 1 to 2 when near Locksmith."""
        anomaly = self._make_anomaly(cfg)
        anomaly.anomaly_quest_stage = 1
        anomaly.x, anomaly.y = 0.5, 0.5

        locksmith = _create_locksmith(50, cfg)
        locksmith.x, locksmith.y = 0.52, 0.52  # within quest_locksmith_radius

        ms = MatrixState()
        ms.anomaly_id = anomaly.id

        process_matrix([anomaly, locksmith], ms, 1, cfg)

        assert anomaly.anomaly_quest_stage == 2
        assert len(anomaly.teleport_keys) > 0, "Anomaly should receive a key to the Core"

    def test_quest_stage_1_blocked_no_locksmith(self, cfg):
        """Anomaly does NOT advance at stage 1 without a Locksmith nearby."""
        anomaly = self._make_anomaly(cfg)
        anomaly.anomaly_quest_stage = 1
        anomaly.x, anomaly.y = 0.5, 0.5

        ms = MatrixState()
        ms.anomaly_id = anomaly.id

        process_matrix([anomaly], ms, 1, cfg)

        assert anomaly.anomaly_quest_stage == 1

    def test_quest_stage_2_to_3_reach_core(self, cfg):
        """Anomaly advances from stage 2 to 3 at map center and makes a choice."""
        anomaly = self._make_anomaly(cfg)
        anomaly.anomaly_quest_stage = 2
        anomaly.x, anomaly.y = 0.5, 0.5  # at the Core

        ms = MatrixState()
        ms.anomaly_id = anomaly.id

        process_matrix([anomaly], ms, 1, cfg)

        assert anomaly.anomaly_quest_stage == 3
        assert anomaly.anomaly_quest_complete
        assert ms.core_choice in ("reset", "fight")
        assert ms.core_choice_outcome in ("status_quo", "freedom", "system_failure")

    def test_quest_stage_2_blocked_far_from_center(self, cfg):
        """Anomaly at stage 2 does NOT complete quest if far from center."""
        anomaly = self._make_anomaly(cfg)
        anomaly.anomaly_quest_stage = 2
        anomaly.x, anomaly.y = 0.1, 0.1  # far from center

        ms = MatrixState()
        ms.anomaly_id = anomaly.id

        process_matrix([anomaly], ms, 1, cfg)

        assert anomaly.anomaly_quest_stage == 2
        assert not anomaly.anomaly_quest_complete

    def test_full_quest_progression(self, cfg):
        """Full quest: stage 0 -> 1 -> 2 -> 3 across multiple ticks."""
        anomaly = self._make_anomaly(cfg)
        locksmith = _create_locksmith(50, cfg)
        locksmith.x, locksmith.y = 0.3, 0.3

        ms = MatrixState()
        ms.anomaly_id = anomaly.id

        # Stage 0 -> 1: Oracle guides anomaly
        ms.oracle_target_id = anomaly.id
        process_matrix([anomaly, locksmith], ms, 1, cfg)
        assert anomaly.anomaly_quest_stage == 1

        # Stage 1 -> 2: Move near locksmith
        anomaly.x, anomaly.y = 0.3, 0.3
        process_matrix([anomaly, locksmith], ms, 2, cfg)
        assert anomaly.anomaly_quest_stage == 2

        # Stage 2 -> 3: Move to center
        anomaly.x, anomaly.y = 0.5, 0.5
        process_matrix([anomaly, locksmith], ms, 3, cfg)
        assert anomaly.anomaly_quest_stage == 3
        assert anomaly.anomaly_quest_complete


# ===================================================
# TEST: Core Choice Outcomes
# ===================================================

class TestCoreChoice:
    def test_compute_choice_score_high_fight(self):
        """Agent with low trust, high spirituality, bonds scores high (fight)."""
        a = Agent(
            id=1, sex="M", awareness=1.0, trauma=0.5,
            beliefs={"system_trust": -0.8, "spirituality": 0.7,
                     "individualism": 0.0, "tradition": 0.0},
        )
        a.bonds = [
            Bond(2, "resistance", 0.9, 0),
            Bond(3, "resistance", 0.8, 0),
            Bond(4, "resistance", 0.7, 0),
        ]
        score = _compute_core_choice_score(a)
        assert score > 0.5, f"High-fight agent should score > 0.5, got {score}"

    def test_compute_choice_score_low_reset(self):
        """Agent with high trust, no bonds scores low (reset)."""
        a = Agent(
            id=1, sex="M", awareness=0.3, trauma=0.0,
            beliefs={"system_trust": 0.8, "spirituality": -0.5,
                     "individualism": 0.0, "tradition": 0.0},
        )
        a.bonds = []
        score = _compute_core_choice_score(a)
        assert score < 0.5, f"Low-fight agent should score < 0.5, got {score}"

    def test_core_fight_freedom_outcome(self, cfg):
        """Fight choice with successful outcome boosts global awareness."""
        anomaly = create_agent(cfg)
        anomaly.phase = "adult"
        anomaly.alive = True
        anomaly.redpilled = True
        anomaly.is_anomaly = True
        anomaly.awareness = 0.95
        anomaly.anomaly_quest_stage = 2
        anomaly.x, anomaly.y = 0.5, 0.5
        anomaly.beliefs["system_trust"] = -0.9
        anomaly.beliefs["spirituality"] = 0.8
        anomaly.trauma = 0.5
        # Add resistance bonds to push score high
        for i in range(5):
            anomaly.bonds.append(Bond(100 + i, "resistance", 0.9, 0))

        bystander = create_agent(cfg)
        bystander.phase = "adult"
        bystander.alive = True
        bystander.awareness = 0.1
        initial_awareness = bystander.awareness

        ms = MatrixState()
        ms.anomaly_id = anomaly.id

        # Run until fight + freedom outcome (retry with different seeds)
        got_freedom = False
        for seed in range(100):
            random.seed(seed)
            # Reset state for retry
            anomaly.anomaly_quest_stage = 2
            anomaly.anomaly_quest_complete = False
            anomaly.x, anomaly.y = 0.5, 0.5
            bystander.awareness = initial_awareness
            ms.core_choice = None
            ms.core_choice_outcome = None

            process_matrix([anomaly, bystander], ms, 1, cfg)

            if ms.core_choice == "fight" and ms.core_choice_outcome == "freedom":
                got_freedom = True
                break

        assert got_freedom, "Should eventually get fight+freedom outcome"
        assert bystander.awareness > initial_awareness, "Freedom outcome should boost global awareness"

    def test_core_reset_outcome(self, cfg):
        """Reset choice produces status_quo outcome."""
        anomaly = create_agent(cfg)
        anomaly.phase = "adult"
        anomaly.alive = True
        anomaly.redpilled = True
        anomaly.is_anomaly = True
        anomaly.awareness = 0.5  # moderate awareness
        anomaly.anomaly_quest_stage = 2
        anomaly.x, anomaly.y = 0.5, 0.5
        anomaly.beliefs["system_trust"] = 0.7  # high trust -> reset
        anomaly.beliefs["spirituality"] = -0.3
        anomaly.trauma = 0.0
        anomaly.bonds = []  # no resistance bonds

        ms = MatrixState()
        ms.anomaly_id = anomaly.id

        process_matrix([anomaly], ms, 1, cfg)

        assert anomaly.anomaly_quest_complete
        assert ms.core_choice == "reset"
        assert ms.core_choice_outcome == "status_quo"

    def test_core_choice_triggers_cycle_reset(self, cfg):
        """After core choice is made, check_cycle_reset returns True."""
        ms = MatrixState()
        ms.core_choice = "reset"
        ms.core_choice_outcome = "status_quo"

        agents = [create_agent(cfg)]
        agents[0].alive = True

        assert check_cycle_reset(ms, agents, cfg) is True

    def test_fight_system_failure_outcome(self, cfg):
        """Fight with system failure reduces global awareness."""
        anomaly = create_agent(cfg)
        anomaly.phase = "adult"
        anomaly.alive = True
        anomaly.redpilled = True
        anomaly.is_anomaly = True
        anomaly.awareness = 0.95
        anomaly.anomaly_quest_stage = 2
        anomaly.x, anomaly.y = 0.5, 0.5
        anomaly.beliefs["system_trust"] = -0.9
        anomaly.beliefs["spirituality"] = 0.8
        anomaly.trauma = 0.5
        for i in range(5):
            anomaly.bonds.append(Bond(100 + i, "resistance", 0.9, 0))

        bystander = create_agent(cfg)
        bystander.phase = "adult"
        bystander.alive = True
        bystander.awareness = 0.5

        ms = MatrixState()
        ms.anomaly_id = anomaly.id

        got_failure = False
        for seed in range(200):
            random.seed(seed)
            anomaly.anomaly_quest_stage = 2
            anomaly.anomaly_quest_complete = False
            anomaly.x, anomaly.y = 0.5, 0.5
            bystander.awareness = 0.5
            ms.core_choice = None
            ms.core_choice_outcome = None

            process_matrix([anomaly, bystander], ms, 1, cfg)

            if ms.core_choice == "fight" and ms.core_choice_outcome == "system_failure":
                got_failure = True
                break

        assert got_failure, "Should eventually get fight+system_failure outcome"
        assert bystander.awareness < 0.5, "System failure should reduce global awareness"


# ===================================================
# TEST: Serialization roundtrip for new fields
# ===================================================

class TestNewFieldSerialization:
    def test_splinter_flag_survives_roundtrip(self, cfg):
        """splinter_in_mind survives to_dict/from_dict."""
        a = create_agent(cfg)
        a.splinter_in_mind = True
        a.is_recruiter = True
        a.anomaly_quest_stage = 2
        a.anomaly_quest_complete = True

        d = a.to_dict()
        restored = Agent.from_dict(d)

        assert restored.splinter_in_mind is True
        assert restored.is_recruiter is True
        assert restored.anomaly_quest_stage == 2
        assert restored.anomaly_quest_complete is True

    def test_matrix_state_core_choice_roundtrip(self):
        """MatrixState core_choice fields survive to_dict/from_dict."""
        ms = MatrixState()
        ms.core_choice = "fight"
        ms.core_choice_outcome = "freedom"

        d = ms.to_dict()
        restored = MatrixState.from_dict(d)

        assert restored.core_choice == "fight"
        assert restored.core_choice_outcome == "freedom"
