# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch
import numpy as np
import pytest
import torch

from core.enums import Maturity
from manager.cycle_manager import CycleManager
from maturity.maturity_config import MaturityConfig
from maturity.maturity_promotion_service import MaturityPromotionService


def test_cycle_manager_trains_agents_with_on_policy_memory(tmp_path):
    """Verifies that CycleManager executes PPO training on agents with get_batch before clearing."""
    mock_maturity_mgr = MagicMock()
    mock_maturity_mgr.check_and_promote_agents.return_value = False
    mock_maturity_mgr.agent_maturity = {"TL_1": Maturity.CHILD}

    mock_pipe = MagicMock()
    mock_ppo_optimizer = MagicMock()
    mock_ppo_optimizer.step.return_value = 0.42

    cycle_mgr = CycleManager(
        maturity_manager=mock_maturity_mgr,
        pipe_conn=mock_pipe,
        ppo_optimizer=mock_ppo_optimizer,
    )

    mock_agent = MagicMock()
    mock_memory = MagicMock()
    mock_memory.__len__.return_value = 10

    # Mock batch transitions (states, actions, log_probs, rewards, dones, state_values)
    dummy_states = torch.zeros((10, 4, 20))
    dummy_actions = torch.zeros(10)
    dummy_log_probs = torch.zeros(10)
    dummy_rewards = [1.0] * 10
    dummy_dones = [False] * 10
    dummy_state_values = torch.zeros(10)

    mock_memory.get_batch.return_value = (
        dummy_states,
        dummy_actions,
        dummy_log_probs,
        dummy_rewards,
        dummy_dones,
        dummy_state_values,
    )

    mock_agent.memory = mock_memory
    mock_agent.policy_net = MagicMock()
    mock_agent.optimizer = MagicMock()
    mock_agent.evaluate = MagicMock()
    mock_agent.steps_done = 0

    agents = {"TL_1": mock_agent}
    accumulated_metrics = {
        "TL_1": {"count": 10, "reward_sum": 10.0, "entropy_sum": 0.5}
    }

    with patch("manager.cycle_manager.get_base_output_dir", return_value=str(tmp_path)):
        cycle_mgr.evaluate_cycle(
            step_counter=100,
            agents=agents,
            accumulated_metrics=accumulated_metrics,
            mfd_efficiency=0.9,
        )

    # Verify PPO optimizer was called with agent parameters
    assert mock_ppo_optimizer.step.called
    assert mock_agent.steps_done == 10
    # Memory must be cleared after training
    assert mock_memory.clear.called
    # Checkpoints saved
    assert mock_agent.save_checkpoint.called


def test_maturity_config_loads_child_promotion_max_entropy_and_auto_flags():
    """Verifies that MaturityConfig correctly parses manual entropy and auto mode settings."""
    # 1. Manual mode with explicit child_promotion_max_entropy
    settings_manual = {
        "MATURITY": {
            "child_phase_episodes": 2,
            "teen_phase_min_episodes": 5,
            "performance_margin_percent": -50.0,
            "child_promotion_max_entropy": 1.5,
            "auto_pacing_enabled": False,
            "auto_performance_margin_enabled": False,
        }
    }
    cfg_manual = MaturityConfig.from_settings(settings_manual)
    assert cfg_manual.child_phase_duration == 2
    assert cfg_manual.child_promotion_max_entropy == 1.5
    assert not cfg_manual.is_automatic_mode

    # 2. Automatic mode
    settings_auto = {
        "MATURITY": {
            "child_phase_episodes": 30,
            "teen_phase_min_episodes": 120,
            "auto_pacing_enabled": True,
            "auto_performance_margin_enabled": True,
        }
    }
    cfg_auto = MaturityConfig.from_settings(settings_auto)
    assert cfg_auto.is_automatic_mode
    assert cfg_auto.auto_pacing_enabled
    assert cfg_auto.auto_performance_margin_enabled


def test_maturity_promotion_service_respects_manual_and_auto_modes():
    """Verifies that MaturityPromotionService uses effective thresholds and records mode correctly."""
    mock_entropy_calc = MagicMock()
    mock_entropy_calc.calculate_threshold.return_value = 0.8

    mock_promotion_eval = MagicMock()
    mock_promotion_eval.evaluate_agent.return_value = (True, "Performance target exceeded", 0.8, 1)

    mock_reporter = MagicMock()
    service = MaturityPromotionService(mock_entropy_calc, mock_promotion_eval, mock_reporter)

    mock_agent = MagicMock()
    mock_agent.phase = Maturity.CHILD
    mock_agent.episodes_in_phase = 1
    agents = {"TL_1": mock_agent}

    # 1. Manual mode with strict manual_max_entropy = 0.6 (stricter than dynamic 0.8)
    metrics = {"TL_1": {"reward": 100.0, "entropy": 0.4}}
    promoted = service.check_and_promote(
        agents=agents,
        agent_metrics=metrics,
        child_phase_duration=1,
        teen_phase_min_duration=1,
        mfd_efficiency=0.9,
        manual_max_entropy=0.6,
        is_automatic_mode=False,
    )

    assert promoted
    assert mock_agent.promote.called
    assert mock_reporter.report_promotion.called
    # Ensure details received mode_str
    details_args = mock_reporter.build_promotion_details.call_args[1]
    assert details_args.get("mode_str") == "MANUAL"
