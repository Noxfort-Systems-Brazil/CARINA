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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_engine_step_and_state.py
# Author: Gabriel Moraes
# Date: September 2026

# CARINA - Clean Architecture & SOLID Unit Test Suite
# Tests for StateExtractor and StepProcessor (Synapse Frame Processing & Orchestration)

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from engine.state_extractor import StateExtractor
from engine.step_processor import StepProcessor


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, **kwargs: f"[{key}]"
    return lm


def test_state_extractor_without_topology(mock_locale):
    """Verifies that state extraction returns empty array before topology is loaded."""
    extractor = StateExtractor(mock_locale)
    assert extractor.get_observation_space_size("TL1") == 0
    assert extractor.get_phase_lane_states("TL1", 0) == {}
    state = extractor.extract_state({"edges": {}}, "TL1", 0)
    assert state.size == 0


def test_state_extractor_with_mock_topology(mock_locale):
    """Tests loading topology via sumolib and extracting vectorized Synapse frames."""
    extractor = StateExtractor(mock_locale)

    mock_tls = MagicMock()
    mock_tls.getID.return_value = "TL1"

    # Mock connections
    mock_lane = MagicMock()
    mock_lane.getID.return_value = "edge1_0"
    mock_edge = MagicMock()
    mock_edge.getID.return_value = "edge1"
    mock_lane.getEdge.return_value = mock_edge
    mock_lane.getFromLane.return_value = mock_lane

    mock_tls.getConnections.return_value = [[mock_lane]]

    # Mock phase logic
    mock_phase_0 = MagicMock()
    mock_phase_0.state = "G"
    mock_phase_0.duration = 30.0
    mock_phase_1 = MagicMock()
    mock_phase_1.state = "r"
    mock_phase_1.duration = 10.0

    mock_logic = MagicMock()
    mock_logic.getPhases.return_value = [mock_phase_0, mock_phase_1]
    mock_tls.getPrograms.return_value = {"0": mock_logic}

    mock_net = MagicMock()
    mock_net.getTrafficLights.return_value = [mock_tls]

    with patch("sumolib.net.readNet", return_value=mock_net):
        extractor.load_topology("/fake/net.xml")

    assert extractor.topology_loaded is True
    assert extractor.tl_incoming_edges["TL1"] == ["edge1"]
    assert extractor.get_observation_space_size("TL1") > 0

    lane_states = extractor.get_phase_lane_states("TL1", 0)
    assert lane_states.get("edge1_0") == "G"

    # Extract state from Synapse real-time telemetry frame
    synapse_frame = {
        "edges": {"edge1": {"occupancy": 0.45, "mean_speed": 10.0, "queue_length": 3}},
        "tls_telemetry": {"TL1": {"active_ped_calls": 1}},
    }
    state_vector = extractor.extract_state(synapse_frame, "TL1", current_stage_idx=0)
    assert isinstance(state_vector, np.ndarray)
    assert state_vector.ndim == 1
    assert len(state_vector) > 0


def test_step_processor_orchestration(mock_locale):
    """Tests StepProcessor lifecycle, reset, and step execution with Synapse data."""
    mock_settings = MagicMock()
    mock_agent_mgr = MagicMock()
    mock_preprocessor = MagicMock()
    mock_extractor = MagicMock()
    mock_supervisor = MagicMock()
    mock_authorizer = MagicMock()
    mock_maturity_mgr = MagicMock()
    mock_reward_comp = MagicMock()
    mock_cycle_mgr = MagicMock()
    mock_pipe = MagicMock()

    processor = StepProcessor(
        settings=mock_settings,
        locale_manager=mock_locale,
        agent_manager=mock_agent_mgr,
        input_preprocessor=mock_preprocessor,
        state_extractor=mock_extractor,
        action_supervisor=mock_supervisor,
        action_authorizer=mock_authorizer,
        maturity_manager=mock_maturity_mgr,
        reward_computer=mock_reward_comp,
        cycle_manager=mock_cycle_mgr,
        pipe_conn=mock_pipe,
    )

    processor.set_current_phases({"TL1": 0})
    processor.set_guardians({"TL1": MagicMock()})
    assert processor.step_counter == 0

    # Mock agent_evaluator output
    processor.agent_evaluator.evaluate_agent = MagicMock(return_value=(1, "AUTONOMOUS", False, 12.5, 0.25, {}))

    synapse_traffic_data = {"timestamp": 100.0, "edges": {"edge1": {"occupancy": 0.2}}}
    mock_agent = MagicMock()

    # Process single step
    processor.process_hft_step(synapse_traffic_data, {"TL1": mock_agent})

    assert processor.step_counter == 1
    mock_supervisor.apply_actions.assert_called_once()

    # Test reset state
    processor.reset_state()
    assert processor.step_counter == 0
    assert len(processor.current_stages) == 0
