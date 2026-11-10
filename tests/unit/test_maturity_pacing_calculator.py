# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock
import pytest

from core.enums import Maturity
from maturity.maturity_manager import MaturityManager
from promotion.maturity_pacing_calculator import MaturityPacingCalculator
from promotion.promotion_evaluator import PromotionEvaluator


def test_calculate_pacing_default_settings():
    net = MagicMock()
    net.getEdges.return_value = [MagicMock() for _ in range(20)]
    tls_list = [MagicMock() for _ in range(5)]

    settings = {
        "update_timestep": 1024,
        "episode_max_steps": 100,
    }

    child_ep, teen_ep, child_steps, teen_steps = MaturityPacingCalculator.calculate_pacing(
        net=net, tls_list=tls_list, settings=settings
    )

    assert child_ep > 0
    assert teen_ep > 0
    computed_steps = child_steps // child_ep
    assert computed_steps % 100 == 0
    assert child_steps == child_ep * computed_steps
    assert teen_steps == teen_ep * computed_steps
    # Enforces 1-week safety floor: episodes * steps * 0.25s >= 604800s
    assert child_steps * 0.25 >= 604800
    assert teen_steps * 0.25 >= 604800


def test_apply_if_enabled_respects_flag():
    mgr = MagicMock()
    net = MagicMock()
    tls_list = [MagicMock()]

    # When disabled
    settings_disabled = {"auto_pacing_enabled": False}
    applied = MaturityPacingCalculator.apply_if_enabled(mgr, net, tls_list, settings_disabled)
    assert applied is False
    mgr.set_phase_durations.assert_not_called()

    # When enabled
    settings_enabled = {"auto_pacing_enabled": True, "episode_max_steps": 100, "update_timestep": 1000}
    applied = MaturityPacingCalculator.apply_if_enabled(mgr, net, tls_list, settings_enabled)
    assert applied is True
    mgr.set_phase_durations.assert_called_once()


def test_promotion_evaluator_set_phase_durations():
    evaluator = PromotionEvaluator(settings=None)
    evaluator.set_phase_durations(child_episodes=42, teen_episodes=150)

    assert evaluator.configs["CHILD"].t_min == 42
    assert evaluator.configs["TEEN"].t_min == 150

    # Evaluate agent with fewer episodes than required
    promoted, reason, thresh, req = evaluator.evaluate_agent(
        agent_id="TL_1",
        current_phase=Maturity.CHILD,
        episodes_in_phase=10,
        recent_mfd_efficiency=0.99,
    )
    assert promoted is False
    assert req == 42


def test_maturity_manager_set_phase_durations_integration():
    mock_locale = MagicMock()
    mock_locale.get_string.side_effect = lambda k, **kw: k

    mgr = MaturityManager(settings={"performance_check_window": 5}, locale_manager=mock_locale)
    mgr.set_phase_durations(child_episodes=35, teen_episodes=120)

    assert mgr.child_phase_duration == 35
    assert mgr.teen_phase_min_duration == 120
    assert mgr.promotion_evaluator.configs["CHILD"].t_min == 35
    assert mgr.promotion_evaluator.configs["TEEN"].t_min == 120
