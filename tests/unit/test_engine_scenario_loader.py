# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock
import pytest

from engine.scenario_loader import ScenarioLoader


def test_scenario_loader_execution():
    """Verifies that ScenarioLoader coordinates step reset, agent setup, MFD, and cycle eval."""
    mock_step_proc = MagicMock()
    mock_step_proc.accumulated_metrics = {"TL1": {"reward_sum": 0.0}}
    mock_agent_mgr = MagicMock()
    mock_topo_mgr = MagicMock()
    mock_extractor = MagicMock()
    mock_maturity_mgr = MagicMock()
    mock_mfd = MagicMock()
    mock_cycle_mgr = MagicMock()
    mock_mfd_proc = MagicMock()
    mock_mfd_proc.get_latest_efficiency.return_value = 0.85

    mock_agent = MagicMock()
    mock_agent_mgr.setup_environment.return_value = (
        {"TL1": mock_agent},  # agents
        {"TL1": 0},          # current_stages
        "mock_strategist",   # strategist
        {"TL1": MagicMock()} # guardians
    )

    loader = ScenarioLoader(
        step_processor=mock_step_proc,
        agent_manager=mock_agent_mgr,
        topology_manager=mock_topo_mgr,
        state_extractor=mock_extractor,
        maturity_manager=mock_maturity_mgr,
        mfd=mock_mfd,
        cycle_manager=mock_cycle_mgr,
        mfd_processor=mock_mfd_proc,
    )

    loader.load_scenario("/fake/city.net.xml")

    # 1. Step processor reset
    mock_step_proc.reset_state.assert_called_once()

    # 2. Agent Manager environment setup
    mock_agent_mgr.setup_environment.assert_called_once_with(
        map_path="/fake/city.net.xml",
        topology_manager=mock_topo_mgr,
        state_extractor=mock_extractor,
        maturity_manager=mock_maturity_mgr,
    )

    # 3. Synchronize phases & guardians
    mock_step_proc.set_current_phases.assert_called_once_with({"TL1": 0})
    mock_step_proc.set_guardians.assert_called_once()

    # 4. MFD topology
    mock_mfd.load_topology.assert_called_once_with("/fake/city.net.xml")

    # 5. Cycle 0 evaluation
    mock_cycle_mgr.evaluate_cycle.assert_called_once_with(
        0, {"TL1": mock_agent}, mock_step_proc.accumulated_metrics, 0.85
    )

    assert loader.current_map_path == "/fake/city.net.xml"
    assert "TL1" in loader.agents


def test_scenario_loader_exception_propagation():
    """Verifies that errors in environment setup are logged and re-raised."""
    mock_step_proc = MagicMock()
    mock_agent_mgr = MagicMock()
    mock_agent_mgr.setup_environment.side_effect = RuntimeError("Invalid net file")

    loader = ScenarioLoader(
        step_processor=mock_step_proc,
        agent_manager=mock_agent_mgr,
        topology_manager=MagicMock(),
        state_extractor=MagicMock(),
        maturity_manager=MagicMock(),
        mfd=MagicMock(),
        cycle_manager=MagicMock(),
    )

    with pytest.raises(RuntimeError, match="Invalid net file"):
        loader.load_scenario("/bad/path.net.xml")
