# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_engine_metrics_and_rewards.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock

import numpy as np
import pytest
import torch

from engine.episode_override_manager import EpisodeOverrideManager
from engine.input_preprocessor import InputPreprocessor
from engine.metrics_tracker import MetricsTracker
from engine.reward_calculator import RewardCalculator


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
    """RewardComputer computes queue length and occupancy penalties from edge data."""
    from engine.reward_computer import RewardComputer

    mock_settings = MagicMock()
    mock_settings.getfloat.side_effect = lambda sec, key, fallback=None: -2.0 if "waiting" in key else -0.5

    mock_extractor = MagicMock()
    mock_extractor.tl_lanes = {"TL_1": ["edge1_0", "edge1_1"]}

    computer = RewardComputer(mock_settings, mock_extractor)
    edges_data = {"edge1": {"queue_length": 5, "occupancy": 0.4}}

    reward = computer.calculate("TL_1", edges_data)
    # queue: 5 * -2.0 = -10.0, occupancy: 0.4 * -0.5 = -0.2 => total = -10.2
    assert reward == pytest.approx(-10.2)
