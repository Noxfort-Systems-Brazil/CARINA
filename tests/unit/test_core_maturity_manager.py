# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from core.enums import Maturity
from maturity.maturity_manager import MaturityManager


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, fallback=None, **kwargs: fallback or key
    return lm


def test_maturity_manager_init(mock_locale):
    """MaturityManager initializes with dict settings and calculates targets."""
    settings = {
        "baseline_reward": -500.0,
        "performance_margin_percent": 10.0,
        "child_phase_episodes": 10,
        "teen_phase_min_episodes": 25,
        "performance_check_window": 5,
    }
    mgr = MaturityManager(settings=settings, locale_manager=mock_locale, baseline={"mean_reward": -500.0})
    assert mgr.child_phase_duration == 10
    assert mgr.teen_phase_min_duration == 25
    assert mgr.baseline_performance == -500.0
    assert mgr.baseline_target == pytest.approx(-550.0)

    mgr.set_performance_margin(32.0)
    assert mgr.baseline_target == pytest.approx(-660.0)


def test_maturity_manager_register_and_state(mock_locale, tmp_path):
    """MaturityManager registers agents and correctly serializes/deserializes state."""
    settings = {"performance_check_window": 5}
    mgr = MaturityManager(settings=settings, locale_manager=mock_locale)

    mgr.register_agents(["TL_1", "TL_2"])
    assert mgr.agent_maturity["TL_1"] == Maturity.CHILD
    assert mgr.agent_maturity["TL_2"] == Maturity.CHILD
    assert mgr.get_agent("TL_1").episodes_in_phase == 0

    state = mgr.get_state()
    assert state["agent_maturity"]["TL_1"] == "CHILD"
    assert "TL_2" in state["agent_episodes_in_phase"]

    save_path = str(tmp_path / "maturity_state.json")
    mgr.save_state(save_path)
    assert os.path.exists(save_path)

    # Load state in new manager
    new_mgr = MaturityManager(settings=settings, locale_manager=mock_locale)
    new_mgr.load_state(save_path)
    assert new_mgr.agent_maturity["TL_1"] == Maturity.CHILD


def test_maturity_manager_update_calibration_thresholds(mock_locale):
    """Legacy calibration threshold method runs cleanly."""
    mgr = MaturityManager(settings={}, locale_manager=mock_locale)
    with patch("logging.info") as mock_log:
        mgr.update_calibration_thresholds(1.0, 0.5)
        assert mock_log.called


def test_maturity_manager_check_and_promote_child(mock_locale):
    """MaturityManager processes child agent promotion evaluation."""
    settings = {
        "child_phase_episodes": 2,
        "teen_phase_min_episodes": 10,
        "performance_check_window": 5,
    }
    mgr = MaturityManager(settings=settings, locale_manager=mock_locale)
    mgr.register_agents(["TL_1"])

    with patch.object(mgr.promotion_evaluator, "evaluate_agent") as mock_eval:
        mock_eval.return_value = (True, "Target met", 0.05, 2)
        metrics = {"TL_1": {"reward": 100.0, "entropy": 0.02}}

        promoted = mgr.check_and_promote_agents(metrics, mfd_efficiency=0.9)
        assert promoted is True
        assert mgr.agent_maturity["TL_1"] == Maturity.TEEN
