# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for safety invariants:
1. Entropy certainty ceiling (min invariant).
2. Time duration floor (1-week minimum invariant).
3. ActionAuthorizer urban peak gating.
"""

from datetime import datetime
import pytest

from src.core.action_authorizer import ActionAuthorizer
from src.core.enums import Maturity
from src.promotion.maturity_pacing_calculator import MaturityPacingCalculator
from src.maturity.maturity_promotion_service import MaturityPromotionService
from src.core.dynamic_entropy_calculator import DynamicEntropyCalculator


class DummyEvaluator:
    def evaluate_agent(self, agent_id, current_phase, episodes_in_phase, recent_mfd_efficiency):
        return True, "test", 0.5, 10


class DummyReporter:
    def build_promotion_details(self, *args, **kwargs):
        return {}

    def report_promotion(self, *args, **kwargs):
        pass

    def build_rejection_details(self, *args, **kwargs):
        return {}

    def report_rejection(self, *args, **kwargs):
        pass


class DummyAgent:
    def __init__(self, phase=Maturity.CHILD):
        self.phase = phase
        self.episodes_in_phase = 1000

    def record_episode(self, r):
        pass

    def promote(self, new_phase):
        self.phase = new_phase


def test_entropy_safety_floor_prevents_relaxation():
    """Verifies that loose user entropy (e.g. 2.0) cannot override strict DA SILVA threshold."""
    entropy_calc = DynamicEntropyCalculator(n_actions=3, e_max=1.0, e_ideal=0.1)
    evaluator = DummyEvaluator()
    reporter = DummyReporter()
    service = MaturityPromotionService(entropy_calc, evaluator, reporter)

    agent = DummyAgent(phase=Maturity.CHILD)
    agents = {"tl_0": agent}

    # Agent has chaotic entropy of 0.85
    metrics = {"tl_0": {"entropy": 0.85, "reward": 10.0}}

    # User attempts to loosen threshold to 2.0 (chaos allowed)
    service.check_and_promote(
        agents=agents,
        agent_metrics=metrics,
        child_phase_duration=100,      # Dynamic threshold will be ~0.10
        teen_phase_min_duration=100,
        mfd_efficiency=0.9,
        manual_max_entropy=2.0,        # Attempted relaxation!
        is_automatic_mode=False,
    )

    # Invariant check: agent with entropy 0.85 MUST NOT be promoted when dynamic threshold is ~0.10
    assert agent.phase == Maturity.CHILD


def test_maturation_time_safety_floor_enforces_1_week():
    """Verifies that user settings cannot reduce child or teen phase below 1-week minimum."""
    from src.utils.episode_step_calculator import EpisodeStepCalculator

    # Mock settings where user attempts to set 2 episodes for child phase
    mock_settings = {
        "child_phase_episodes": "2",
        "teen_phase_min_episodes": "3",
        "telemetry_delta_ms": "250",
    }

    class TinyNet:
        def getTrafficLights(self):
            return ["tl_1"]

        def getEdges(self, withInternal=False):
            return []

        def getBBoxXY(self):
            return ((0.0, 0.0), (1000.0, 1000.0))

    net = TinyNet()
    pacing_res = EpisodeStepCalculator.calculate(net, telemetry_delta_ms=250.0)
    expected_min_1_week = pacing_res.child_episodes_1_week

    child_ep, teen_ep, child_steps, _ = MaturityPacingCalculator.calculate_pacing(
        net=net, tls_list=net.getTrafficLights(), settings=mock_settings
    )

    # Even though user requested 2 and 3 episodes, system must clamp to 1-week floor
    assert child_ep == expected_min_1_week
    assert teen_ep == expected_min_1_week
    assert child_ep >= 168  # At least 168 episodes (at 1 hour max)


def test_action_authorizer_urban_peak_gating():
    """Tests that TEEN is blocked during classical urban peak hours and active off-peak."""
    authorizer = ActionAuthorizer(settings={}, locale_manager=None)

    # Tuesday, October 20, 2026 at 07:30 (Morning Peak)
    ts_morning_peak = datetime(2026, 10, 20, 7, 30, 0).timestamp()
    auth_morning, _ = authorizer.is_action_authorized(
        agent_id="tl_1", maturity=Maturity.TEEN, sim_time=100.0, raw_timestamp=ts_morning_peak
    )
    assert auth_morning is False

    # Tuesday, October 20, 2026 at 18:30 (Evening Peak)
    ts_evening_peak = datetime(2026, 10, 20, 18, 30, 0).timestamp()
    auth_evening, _ = authorizer.is_action_authorized(
        agent_id="tl_1", maturity=Maturity.TEEN, sim_time=200.0, raw_timestamp=ts_evening_peak
    )
    assert auth_evening is False

    # Tuesday, October 20, 2026 at 12:00 (Weekday Midday Off-Peak)
    ts_midday = datetime(2026, 10, 20, 12, 0, 0).timestamp()
    auth_midday, _ = authorizer.is_action_authorized(
        agent_id="tl_1", maturity=Maturity.TEEN, sim_time=300.0, raw_timestamp=ts_midday
    )
    assert auth_midday is True

    # Saturday, October 24, 2026 at 14:00 (Weekend Off-Peak)
    ts_weekend = datetime(2026, 10, 24, 14, 0, 0).timestamp()
    auth_weekend, _ = authorizer.is_action_authorized(
        agent_id="tl_1", maturity=Maturity.TEEN, sim_time=400.0, raw_timestamp=ts_weekend
    )
    assert auth_weekend is True
