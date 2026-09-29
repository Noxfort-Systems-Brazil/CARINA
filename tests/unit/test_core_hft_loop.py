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

# File: tests/unit/test_core_hft_loop.py
# Author: Gabriel Moraes
# Date: September 2026

# CARINA - Clean Architecture & SOLID Unit Test Suite
# Tests for HftEventLoop and HftSystemFacade (Synapse IPC & Failsafe Management)

from unittest.mock import MagicMock, patch

import pytest

from core.hft_event_loop import HftEventLoop
from core.hft_system_facade import HftSystemFacade


@pytest.fixture
def mock_hft_dependencies():
    ai_pipe = MagicMock()
    failsafe_mgr = MagicMock()
    request_proc = MagicMock()
    sds_queue = MagicMock()

    failsafe_mgr.failsafe_active = False
    failsafe_mgr.check_synapse_health.return_value = True

    return {
        "ai_pipe": ai_pipe,
        "failsafe_mgr": failsafe_mgr,
        "request_proc": request_proc,
        "sds_queue": sds_queue,
    }


def test_hft_event_loop_shutdown_via_pipe(mock_hft_dependencies):
    """Tests graceful loop shutdown upon receiving ('system', 'shutdown') command."""
    deps = mock_hft_dependencies
    ai_pipe = deps["ai_pipe"]

    # First poll True returns shutdown, subsequent returns False
    ai_pipe.poll.side_effect = [True, False]
    ai_pipe.recv.return_value = ("system", "shutdown")

    loop = HftEventLoop(
        ai_pipe_conn=ai_pipe,
        failsafe_manager=deps["failsafe_mgr"],
        request_processor=deps["request_proc"],
        sds_data_queue=deps["sds_queue"],
    )

    with patch("time.sleep", side_effect=lambda s: None):
        loop.run_loop()

    assert loop.is_running is False
    assert deps["request_proc"].process_queues.called


def test_hft_event_loop_synapse_unhealthy_triggers_failsafe(mock_hft_dependencies):
    """Tests failsafe activation when Synapse health check fails."""
    deps = mock_hft_dependencies
    deps["failsafe_mgr"].check_synapse_health.return_value = False
    deps["ai_pipe"].poll.return_value = False

    loop = HftEventLoop(
        ai_pipe_conn=deps["ai_pipe"],
        failsafe_manager=deps["failsafe_mgr"],
        request_processor=deps["request_proc"],
        sds_data_queue=deps["sds_queue"],
    )

    # Stop after one iteration
    def stop_loop(*args, **kwargs):
        loop.stop()

    deps["request_proc"].process_queues.side_effect = stop_loop

    with patch("time.sleep", side_effect=lambda s: None):
        loop.run_loop()

    deps["failsafe_mgr"].trigger_failsafe.assert_called_once()


def test_hft_event_loop_failsafe_active_ticks_and_enqueues(mock_hft_dependencies):
    """Tests failsafe ticking and sending phase updates to SDS queue when active."""
    deps = mock_hft_dependencies
    deps["failsafe_mgr"].failsafe_active = True
    deps["failsafe_mgr"].tick.return_value = {"C1": "rrrr"}
    deps["failsafe_mgr"].get_status.return_value = "DEGRADED_FAILSAFE"
    deps["ai_pipe"].poll.return_value = False

    loop = HftEventLoop(
        ai_pipe_conn=deps["ai_pipe"],
        failsafe_manager=deps["failsafe_mgr"],
        request_processor=deps["request_proc"],
        sds_data_queue=deps["sds_queue"],
    )

    def stop_loop(*args, **kwargs):
        loop.stop()

    deps["request_proc"].process_queues.side_effect = stop_loop

    with patch("time.sleep", side_effect=lambda s: None):
        loop.run_loop()

    assert deps["sds_queue"].put.called
    msg_type, payload = deps["sds_queue"].put.call_args[0][0]
    assert msg_type == "failsafe_phase_update"
    assert payload["changes"] == {"C1": "rrrr"}


def test_hft_system_facade_delegation():
    """Tests HftSystemFacade single responsibility and delegation to subsystems."""
    mock_topo_mgr = MagicMock()
    mock_recorder = MagicMock()
    mock_telemetry = MagicMock()
    mock_frame_proc = MagicMock()

    facade = HftSystemFacade(
        topology_manager=mock_topo_mgr,
        topology_recorder_bridge=mock_recorder,
        telemetry_aggregator=mock_telemetry,
        watchdog_queue=MagicMock(),
        ui_command_queue=MagicMock(),
        traffic_frame_processor=mock_frame_proc,
    )

    facade.handle_new_map("/maps/city.xml", "/output/dir")
    mock_topo_mgr.handle_new_map.assert_called_once_with("/maps/city.xml", "/output/dir", mock_telemetry)
    mock_recorder.update_recorder_topology.assert_called_once_with("/maps/city.xml")

    # Synapse traffic frame forwarding
    sample_frame = {"node_id": "J1", "status": "GREEN", "telemetry": {}}
    facade.process_traffic_frame(sample_frame)
    mock_frame_proc.process_traffic_frame.assert_called_once_with(sample_frame)

    facade.start_ai_session()
    facade.stop_ai_session()
