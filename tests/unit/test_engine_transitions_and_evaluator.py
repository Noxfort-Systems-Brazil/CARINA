# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: tests/unit/test_engine_transitions_and_evaluator.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock

import pytest

from engine.evaluator import ValidationEvaluator
from engine.stage_transition_manager import StageTransitionManager


def test_stage_transition_manager_yellow_advance():
    """StageTransitionManager automatically advances yellow stage when duration exceeds yellow_time."""
    mock_extractor = MagicMock()
    mock_extractor.tl_green_stages = {"TL_1": [0]}  # 0 is green, 1 is yellow
    mock_extractor.tl_stage_codes = {"TL_1": {0: "G", 1: "y", 2: "r"}}

    mock_supervisor = MagicMock()
    mock_supervisor._last_stage_change_time = {"TL_1": 10.0}

    manager = StageTransitionManager(mock_extractor, mock_supervisor)
    current_stages = {"TL_1": 1}  # Currently in yellow (1)

    # Simulation time is 10.0 + yellow_time + 1.0 -> should advance to red (2)
    manager.auto_advance_transitions(sim_time=10.0 + manager.yellow_time + 1.0, current_stages=current_stages)
    assert current_stages["TL_1"] == 2
    assert mock_supervisor._last_stage_change_time["TL_1"] > 10.0


def test_stage_transition_manager_update_estimated_stage():
    """StageTransitionManager updates estimated stage index on demand."""
    mock_extractor = MagicMock()
    mock_extractor.tl_stage_codes = {"TL_1": {0: "G", 1: "y", 2: "r"}}
    mock_supervisor = MagicMock()
    mock_supervisor._last_stage_change_time = {}

    manager = StageTransitionManager(mock_extractor, mock_supervisor)
    current_stages = {"TL_1": 0}

    manager.update_estimated_stage("TL_1", current_stage_idx=0, sim_time=25.0, current_stages=current_stages)
    assert current_stages["TL_1"] == 1
    assert mock_supervisor._last_stage_change_time["TL_1"] == 25.0


def test_validation_evaluator_execution():
    """ValidationEvaluator runs evaluation episodes without learning."""
    mock_settings = MagicMock()
    mock_settings.getint.side_effect = lambda sec, key, fallback=None: 4 if "seq" in key else 10

    evaluator = ValidationEvaluator(mock_settings)

    mock_agent = MagicMock()
    mock_agent.device = "cpu"
    mock_action = MagicMock()
    mock_action.item.return_value = 0
    mock_agent.choose_action.return_value = (mock_action, None, None, None)

    agents = {"TL_1": mock_agent}

    mock_env = MagicMock()
    mock_env.get_global_state.return_value = {"TL_1": [0.1, 0.2]}
    # Step returns next_states, rewards, done
    mock_env.step.return_value = ({"TL_1": [0.1, 0.2]}, {"TL_1": 5.0}, True)

    avg_reward = evaluator.evaluate(agents, mock_env, num_episodes=1)
    assert avg_reward == 5.0
    assert mock_agent.policy_net.eval.called
    assert mock_agent.policy_net.train.called
