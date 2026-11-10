# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock

import numpy as np
import pytest
import torch

from engine.input_preprocessor import InputPreprocessor
from engine.metrics_tracker import MetricsTracker
from engine.reward_calculator import RewardCalculator
from manager.episode_override_manager import EpisodeOverrideManager


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, fallback=None, **kwargs: fallback or key
    return lm


def test_reward_calculator(mock_locale):
    """RewardCalculator calculates waiting time penalty and vehicle clearance bonus."""
    mock_settings = MagicMock()
    mock_section = MagicMock()
    mock_section.getfloat.side_effect = lambda k: -1.5 if "waiting" in k else 2.0
    mock_settings.__getitem__.return_value = mock_section

    calc = RewardCalculator(mock_settings, mock_locale)
    assert calc.reward_weights["waiting_time"] == -1.5
    assert calc.reward_weights["flow"] == 2.0

    current_batch = {
        "tls_controlled_lanes": {"TL_1": ["lane_1", "lane_2"]},
        "lane_waiting_time": {"lane_1": 10.0, "lane_2": 5.0},
        "lane_vehicle_ids": {"lane_1": ["veh_3"], "lane_2": []},
    }
    last_batch = {
        "lane_vehicle_ids": {"lane_1": ["veh_1", "veh_2", "veh_3"], "lane_2": ["veh_4"]},
    }

    rewards = calc.calculate_rewards_from_batch(["TL_1"], current_batch, last_batch)
    # waiting_time = 15.0 * -1.5 = -22.5
    # flow_bonus = (3-1) + (1-0) = 3 cleared * 2.0 = 6.0
    # total = -22.5 + 6.0 = -16.5
    assert rewards["TL_1"] == pytest.approx(-16.5)


def test_metrics_tracker_record_and_finalize():
    """MetricsTracker accumulates step metrics and computes means on episode end."""
    tracker = MetricsTracker()
    tracker.record_step(
        rewards={"TL_1": 10.0, "TL_2": -5.0},
        entropies={"TL_1": 0.5, "TL_2": 0.8},
    )
    tracker.record_step(
        rewards={"TL_1": 20.0, "TL_2": 5.0},
        entropies={"TL_1": 0.3, "TL_2": 0.6},
    )

    summary = tracker.finalize_episode()
    assert summary["TL_1"]["reward"] == 30.0
    assert summary["TL_1"]["entropy"] == pytest.approx(0.4)
    assert summary["TL_2"]["reward"] == 0.0
    assert summary["TL_2"]["entropy"] == pytest.approx(0.7)
    tracker.close()


def test_input_preprocessor_stacking():
    """InputPreprocessor manages deque history and outputs stacked tensors."""
    device = torch.device("cpu")
    preprocessor = InputPreprocessor(sequence_length=4, device=device)

    v1 = np.array([1.0, 2.0], dtype=np.float32)
    t1, np1 = preprocessor.prepare_tensor("TL_1", v1)
    # First time seeing TL_1, padded with zeros
    assert t1.shape == (1, 4, 2)
    assert np1.shape == (4, 2)

    v2 = np.array([3.0, 4.0], dtype=np.float32)
    t2, np2 = preprocessor.prepare_tensor("TL_1", v2)
    assert t2.shape == (1, 4, 2)

    preprocessor.reset()
    assert len(preprocessor.state_history) == 0


def test_episode_override_manager():
    """EpisodeOverrideManager parses UI manual overrides and updates coordinators."""
    mock_decision_coord = MagicMock()
    mock_decision_coord.override_states = {}
    mock_action_supervisor = MagicMock()

    next_states = {
        "operation_mode": "MANUAL",
        "override_commands": [
            {"semaphore_id": "TL_1", "state": "ALERT"},
            {"semaphore_id": "TL_2", "state": "OFF"},
        ],
        "active_overrides": {"TL_3": "ALERT"},
    }

    mode = EpisodeOverrideManager.process_overrides(
        next_states,
        mock_decision_coord,
        mock_action_supervisor,
        current_operation_mode="AUTO",
    )

    assert mode == "MANUAL"
    assert mock_action_supervisor.apply_hardware_override.call_count == 2
    assert mock_decision_coord.override_states == {"TL_3": "ALERT"}


def test_reward_computer():
    """RewardComputer computes queue length, occupancy, and non-linear spillback/safety penalties from edge data."""
    from engine.reward_computer import RewardComputer

    mock_settings = MagicMock()
    weights_map = {
        "weight_waiting_time": -2.0,
        "weight_occupancy": -0.5,
        "weight_spillback": -25.0,
        "weight_emergency_brake": -50.0,
        "weight_teleport": -300.0,
    }
    mock_settings.getfloat.side_effect = lambda sec, key, fallback=None: weights_map.get(key, fallback)

    mock_extractor = MagicMock()
    mock_extractor.tl_lanes = {"TL_1": ["edge1_0", "edge1_1"]}

    computer = RewardComputer(mock_settings, mock_extractor)
    edges_data = {"edge1": {"queue_length": 5, "occupancy": 0.4}}

    reward = computer.calculate("TL_1", edges_data)
    # queue: 5 * -2.0 = -10.0, occupancy: 0.4 * -0.5 = -0.2, spillback: 0.0 => total = -10.2
    assert reward == pytest.approx(-10.2)

    # With severe spillback (occupancy = 0.90 -> excess = (0.90-0.80)/0.20 = 0.5 -> severity = 0.25) and 1 emergency brake
    edges_data_spill = {"edge1": {"queue_length": 5, "occupancy": 0.90, "emergency_brakes": 1}}
    reward_spill = computer.calculate("TL_1", edges_data_spill)
    # queue: -10.0, occupancy: -0.45, spillback: 0.25 * -25.0 = -6.25, brake: -50.0 => -66.7
    assert reward_spill == pytest.approx(-66.7)


def test_reward_calculator_multi_objective_terms(mock_locale):
    """RewardCalculator incorporates Max-Pressure, non-linear spillback, phase switch, emergency brakes, and teleports."""
    import configparser

    cfg = configparser.ConfigParser()
    cfg["REWARD_WEIGHTS"] = {
        "weight_waiting_time": "-1.0",
        "weight_flow": "2.0",
        "weight_queue_pressure": "-0.5",
        "weight_spillback": "-20.0",
        "weight_phase_switch": "-3.0",
        "weight_emergency_brake": "-50.0",
        "weight_teleport": "-300.0",
    }

    calc = RewardCalculator(cfg, mock_locale)
    current_batch = {
        "tls_controlled_lanes": {"TL_1": ["lane_1"]},
        "lane_waiting_time": {"lane_1": 10.0},
        "lane_vehicle_ids": {"lane_1": ["v2"]},
        "lane_queue_length": {"lane_1": 8.0},
        "downstream_queue_length": {"lane_1": 2.0},
        "lane_occupancy": {"lane_1": 0.90},
        "lane_emergency_brakes": {"lane_1": 1},
        "tls_teleports": {"TL_1": 1},
        "tls_phases": {"TL_1": 2},
    }
    last_batch = {
        "lane_vehicle_ids": {"lane_1": ["v1", "v2"]},
        "tls_phases": {"TL_1": 0},
    }

    rewards = calc.calculate_rewards_from_batch(["TL_1"], current_batch, last_batch)
    breakdown = calc.get_last_reward_breakdown("TL_1")

    assert breakdown["waiting_time"] == pytest.approx(-10.0)
    assert breakdown["flow"] == pytest.approx(2.0)
    assert breakdown["queue_pressure"] == pytest.approx(-3.0)  # (8 - 2) * -0.5
    assert breakdown["spillback"] == pytest.approx(-5.0)  # ((0.90-0.80)/0.20)^2 * -20 = 0.25 * -20
    assert breakdown["phase_switch"] == pytest.approx(-3.0)
    assert breakdown["emergency_brake"] == pytest.approx(-50.0)
    assert breakdown["teleport"] == pytest.approx(-300.0)
    assert rewards["TL_1"] == pytest.approx(-369.0)
