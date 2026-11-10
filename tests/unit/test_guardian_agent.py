# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
from unittest.mock import MagicMock, patch

import pytest
import torch

import src.agents.guardian_agent as ga
from src.agents.guardian_agent import GuardianAgent


@pytest.fixture
def base_aiconfig():
    conf = MagicMock()
    conf.getint.side_effect = lambda k, fallback=None: fallback if fallback else 100
    conf.getfloat.side_effect = lambda k, fallback=None: fallback if fallback else 0.5
    return conf


@pytest.fixture
def traffic_rules_config():
    conf = MagicMock()

    # Mock fallback params: min_green=15, yellow=4, red=2
    def get_float(k, fallback):
        vals = {"min_green_time_seconds": 15.0, "yellow_time_seconds": 4.0, "all_red_time_seconds": 2.0}
        return vals.get(k, fallback)

    conf.getfloat.side_effect = get_float
    return conf


@pytest.fixture
def mock_locale():
    mock = MagicMock()
    mock.get_string.side_effect = lambda key, default=None, **kwargs: default if default is not None else key
    return mock


@pytest.fixture
def guardian_agent(base_aiconfig, traffic_rules_config, mock_locale):
    with (
        patch.object(ga, "D3QN_TCN") as mock_tcn,
        patch.object(ga.optim, "AdamW") as mock_optim,
        patch.object(ga.torch.amp, "GradScaler") as mock_scaler,
        patch.object(ga.SafetyRules, "get_green", return_value=15.0),
        patch.object(ga.SafetyRules, "get_yellow", return_value=4.0),
        patch.object(ga.SafetyRules, "get_all_red", return_value=2.0),
        patch.object(ga.SafetyRules, "get_red", return_value=10.0),
    ):

        agent = GuardianAgent(
            aiconfig=base_aiconfig,
            traffic_rules_config=traffic_rules_config,
            locale_manager=mock_locale,
            shared_pae=None,
        )
        return agent


def test_guardian_initialization(guardian_agent):
    """Tests if Guardian rules were inferred from traffic configs."""
    assert guardian_agent.green_time == 15.0
    assert guardian_agent.yellow_time == 4.0
    assert guardian_agent.all_red_time == 2.0
    assert guardian_agent.ACTION_KEEP_STAGE == 0


def test_symbolic_barrier_min_green_violation(guardian_agent):
    """Tests if The Guardian VETOES changes if the minimum green is not met."""
    context = {
        "current_stage_duration": 10.0,  # Below the 15s minimum
        "current_stage_state": "G",
        "next_stage_has_flow": True,
        "tl_id": "TL_TEST",
    }

    # Independent of neural network, due to barriers, it must keep (0)
    decision, reason = guardian_agent.select_action([0, 0], context)
    assert decision == guardian_agent.ACTION_KEEP_STAGE
    assert "Minimum Green limits" in reason


def test_symbolic_barrier_ghost_green(guardian_agent):
    """Tests if The Guardian VETOES changes (saving ghost green) if no one requests green."""
    context = {
        "current_stage_duration": 50.0,  # Green can change
        "current_stage_state": "G",
        "next_stage_has_flow": False,  # But nobody needs it! (Avoidable Ghost Green)
        "tl_id": "TL_TEST",
    }

    # The guardian holds the phase
    decision, reason = guardian_agent.select_action([0, 0], context)
    assert decision == guardian_agent.ACTION_KEEP_STAGE
    assert "Ghost Green constraint" in reason


@patch.object(ga, "random")
def test_neural_inference_path(mock_random, guardian_agent):
    """Tests free path where symbolic barrier does not act and AI takes over."""
    context = {
        "current_stage_duration": 20.0,  # Ok
        "current_stage_state": "G",
        "next_stage_has_flow": True,  # Flow exists on crossing
        "tl_id": "TL_FREE",
    }

    # We force epsilon to go into network (not pure exploration)
    mock_random.random.return_value = 1.0  # Always > eps_threshold if warmed up
    guardian_agent.epsilon_end = -1.0  # Ensures greedy
    guardian_agent.epsilon_start = -1.0
    guardian_agent.steps_done = 999999

    # Mock of DQN forward pass
    mock_q_values = MagicMock()
    mock_max = MagicMock()
    mock_max.item.return_value = 1  # AI decides to change
    mock_q_values.max.return_value = [None, mock_max]

    guardian_agent.policy_net.return_value = mock_q_values

    with patch.object(ga.torch, "tensor"):
        decision, reason = guardian_agent.select_action([0, 0], context)

    assert decision == guardian_agent.ACTION_CHANGE_STAGE  # Neural action for change (1)


def test_temporal_sequence_padding(guardian_agent):
    """Tests if agent's Deque manages and does PADDING of state vector."""
    state1 = [1.0, 0.0]

    with patch.object(ga.torch, "from_numpy") as mock_from_numpy:
        mock_from_numpy.return_value = MagicMock()
        # Insert only 1 measurement. Must pad to TEMPORAL_SEQ_LEN
        seq_tensor = guardian_agent._get_temporal_sequence(state1, "TL_TEST")

        args = mock_from_numpy.call_args[0][0]
        assert args.shape == (guardian_agent.TEMPORAL_SEQ_LEN, len(state1))
        assert list(args[-1]) == state1


def test_symbolic_barrier_all_red_violation(guardian_agent):
    """Tests if The Guardian VETOES changes if the minimum All-Red is not met."""
    context = {
        "current_stage_duration": 1.0,  # Below the 2.0s minimum all-red
        "current_stage_state": "R",  # Red stage (no G or Y)
        "next_stage_has_flow": True,
        "is_clearance_red": True,
        "tl_id": "TL_TEST",
    }
    decision, reason = guardian_agent.select_action([0, 0], context)
    assert decision == guardian_agent.ACTION_KEEP_STAGE
    assert "Minimum All Red limits" in reason


def test_symbolic_barrier_red_violation(guardian_agent):
    """Tests if The Guardian VETOES changes if the minimum Red is not met."""
    context = {
        "current_stage_duration": 5.0,  # Below the 10.0s minimum red
        "current_stage_state": "R",  # Red stage (no G or Y)
        "next_stage_has_flow": True,
        "is_clearance_red": False,
        "tl_id": "TL_TEST",
    }
    decision, reason = guardian_agent.select_action([0, 0], context)
    assert decision == guardian_agent.ACTION_KEEP_STAGE
    assert "Minimum Red limits" in reason


def test_guardian_train_eval_toggle(guardian_agent):
    """GuardianAgent train() and eval() toggle network mode while keeping safety deterministic."""
    guardian_agent.train(True)
    assert guardian_agent.is_training is True
    guardian_agent.eval()
    assert guardian_agent.is_training is False


@patch.object(ga, "random")
def test_guardian_strictly_deterministic_neural_evaluation(mock_random, guardian_agent):
    """GuardianAgent must evaluate spillback risk 100% deterministically without random exploration."""
    mock_q_values = MagicMock()
    mock_max = MagicMock()
    mock_max.item.return_value = guardian_agent.ACTION_KEEP_STAGE  # Veto
    mock_q_values.max.return_value = [None, mock_max]
    guardian_agent.policy_net.return_value = mock_q_values

    # In traffic engineering safety, no random calls should ever be made
    risk = guardian_agent.evaluate_spillback_risk([0.8, 0.8], "TL_TEST")
    assert 0.0 <= risk <= 1.0
    assert risk >= guardian_agent.spillback_risk_threshold
    assert guardian_agent.is_exploratory_decision("TL_TEST") is False
    assert mock_random.random.called is False
    assert mock_random.randrange.called is False


def test_guardian_calibrated_continuous_risk_from_q_margin_and_kinematics(guardian_agent):
    """GuardianNeuralPredictor computes continuous calibrated risk from Q-margin, kinematics, and PAE forecast."""
    import math

    # Real Q-value tensor: Q(KEEP=0) = 1.5, Q(CHANGE=1) = 0.5 -> margin = +1.0 -> sigmoid(1.0) ~ 0.731
    guardian_agent.policy_net.return_value = torch.tensor([[1.5, 0.5]], dtype=torch.float32)

    # Feed growing congestion sequence: [occupancy, speed_norm, queue_norm, phase_0]
    guardian_agent.evaluate_spillback_breakdown([0.2, 0.8, 0.1, 1.0], "TL_CAL")
    breakdown = guardian_agent.evaluate_spillback_breakdown([0.9, 0.1, 0.85, 1.0], "TL_CAL")

    assert 0.0 < breakdown["neural_prob"] < 1.0
    assert breakdown["neural_prob"] == pytest.approx(1.0 / (1.0 + math.exp(-1.0)), rel=1e-3)
    assert breakdown["kinematic_risk"] > 0.6
    assert 0.0 < breakdown["risk"] < 1.0
    assert breakdown["q_margin"] == pytest.approx(1.0)

    # Low Q-margin and empty street should produce low continuous risk
    guardian_agent.policy_net.return_value = torch.tensor([[-2.0, 2.0]], dtype=torch.float32)
    low_breakdown = guardian_agent.evaluate_spillback_breakdown([0.05, 0.9, 0.0, 1.0], "TL_EMPTY")
    assert low_breakdown["risk"] < 0.2


def test_guardian_neural_veto_reports_neural_reason(guardian_agent):
    """When the neural network predicts spillback risk, select_action returns neural reason."""
    mock_q_values = MagicMock()
    mock_max = MagicMock()
    mock_max.item.return_value = guardian_agent.ACTION_KEEP_STAGE  # Neural network predicts spillback
    mock_q_values.max.return_value = [None, mock_max]
    guardian_agent.policy_net.return_value = mock_q_values

    context = {
        "current_stage_duration": 50.0,
        "current_stage_state": "G",
        "next_stage_has_flow": True,
        "tl_id": "TL_NEURAL",
    }

    action, reason = guardian_agent.select_action([0.9, 0.9], context)
    assert action == guardian_agent.ACTION_KEEP_STAGE
    assert "Neural" in reason or "neural" in reason.lower()


def test_guardian_max_green_ceiling_prevents_neural_starvation(guardian_agent):
    """When a green stage exceeds max_green_time, force-off is triggered regardless of neural spillback."""
    mock_q_values = MagicMock()
    mock_max = MagicMock()
    mock_max.item.return_value = guardian_agent.ACTION_KEEP_STAGE  # Neural network predicts spillback
    mock_q_values.max.return_value = [None, mock_max]
    guardian_agent.policy_net.return_value = mock_q_values

    context = {
        "current_stage_duration": 65.0,  # Exceeds 60.0s max green ceiling
        "current_stage_state": "G",
        "next_stage_has_flow": True,
        "tl_id": "TL_NEURAL",
        "max_green_time": 60.0,
    }

    action, reason = guardian_agent.select_action([0.9, 0.9], context)
    # Must allow changing stage to prevent starvation of conflicting approaches
    assert action == guardian_agent.ACTION_CHANGE_STAGE
    assert "Maximum green time" in reason or "force-off" in reason.lower()
