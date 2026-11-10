# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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
    mock_settings.getint.return_value = 100
    mock_timer = MagicMock()
    mock_evaluator = MagicMock()
    mock_transition_mgr = MagicMock()
    mock_supervisor = MagicMock()
    mock_pae_trainer = MagicMock()
    mock_mfd_processor = MagicMock()
    mock_actuator = MagicMock()
    mock_telemetry_pub = MagicMock()
    mock_cycle_mgr = MagicMock()
    mock_episode_reporter = MagicMock()

    processor = StepProcessor(
        settings=mock_settings,
        locale_manager=mock_locale,
        step_timer=mock_timer,
        agent_evaluator=mock_evaluator,
        stage_transition_manager=mock_transition_mgr,
        action_supervisor=mock_supervisor,
        online_pae_trainer=mock_pae_trainer,
        mfd_processor=mock_mfd_processor,
        hardware_actuator=mock_actuator,
        telemetry_publisher=mock_telemetry_pub,
        cycle_manager=mock_cycle_mgr,
        episode_reporter=mock_episode_reporter,
    )

    processor.set_current_phases({"TL1": 0})
    processor.set_guardians({"TL1": MagicMock()})
    assert processor.step_counter == 0

    from engine.agent_evaluator import FleetDecisions

    # Mock agent_evaluator output via FleetDecisions
    mock_evaluator.evaluate_fleet.return_value = FleetDecisions(
        actions={"TL1": 1},
        lanes_state={"TL1": {}},
        maturity_info={"TL1": "AUTONOMOUS"},
        step_reward_sum=12.5,
        guardian_vetoed_any=False,
        metrics_delta={"TL1": (12.5, 0.25)},
    )

    synapse_traffic_data = {"timestamp": 100.0, "edges": {"edge1": {"occupancy": 0.2}}}
    mock_agent = MagicMock()

    # Process single step
    processor.process_hft_step(synapse_traffic_data, {"TL1": mock_agent})

    assert processor.step_counter == 1
    mock_supervisor.apply_actions.assert_called_once()
    mock_transition_mgr.apply_software_transitions.assert_called_once()
    mock_pae_trainer.train_step.assert_called_once()
    mock_telemetry_pub.publish.assert_called_once()

    # Test reset state
    processor.reset_state()
    assert processor.step_counter == 0
    assert len(processor.current_stages) == 0
    mock_pae_trainer.reset.assert_called_once()

