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

# File: tests/unit/test_live_data_provider_ipc.py
# Author: Gabriel Moraes
# Date: 2026

import queue
import time
from unittest.mock import MagicMock

import pytest

from sds.dashboard_orchestrator import Orchestrator
from ui.providers.live_data_provider import LiveDataProvider


@pytest.fixture(autouse=True)
def reset_live_data_provider_state():
    LiveDataProvider.GLOBAL_SHUTDOWN_EVENT = None
    LiveDataProvider.CACHED_INITIAL_GEOMETRY = None
    yield
    LiveDataProvider.GLOBAL_SHUTDOWN_EVENT = None
    LiveDataProvider.CACHED_INITIAL_GEOMETRY = None


def test_live_data_provider_command_dispatch():
    mock_telem_q = queue.Queue()
    mock_cmd_q = queue.Queue()
    callback = MagicMock()

    provider = LiveDataProvider(on_data_received=callback, ui_telemetry_queue=mock_telem_q, ui_command_queue=mock_cmd_q)

    test_command = {"type": "set_global_mode", "payload": {"mode": "MANUAL"}}
    provider.send_command_to_backend(test_command)

    assert not mock_cmd_q.empty()
    received_cmd = mock_cmd_q.get_nowait()
    assert received_cmd == test_command


def test_live_data_provider_receives_telemetry():
    mock_telem_q = queue.Queue()
    mock_cmd_q = queue.Queue()
    callback = MagicMock()

    provider = LiveDataProvider(on_data_received=callback, ui_telemetry_queue=mock_telem_q, ui_command_queue=mock_cmd_q)

    provider.start()
    try:
        # Upon start, it should send check_lockdown to cmd_q
        time.sleep(0.05)
        assert not mock_cmd_q.empty()
        lockdown_check = mock_cmd_q.get_nowait()
        assert lockdown_check.get("type") == "check_lockdown"

        # Send a telemetry packet into the queue
        telemetry_packet = {"type": "congestion_update", "payload": {"edge_1": 0.85}}
        mock_telem_q.put(telemetry_packet)

        # Allow worker thread to process
        for _ in range(20):
            if callback.called:
                break
            time.sleep(0.05)

        callback.assert_called_with(telemetry_packet)
    finally:
        provider.stop()
        assert provider.is_stopped


def test_live_data_provider_caches_and_redispatches_initial_geometry():
    mock_telem_q = queue.Queue()
    mock_cmd_q = queue.Queue()
    callback1 = MagicMock()

    LiveDataProvider.CACHED_INITIAL_GEOMETRY = None

    provider1 = LiveDataProvider(
        on_data_received=callback1, ui_telemetry_queue=mock_telem_q, ui_command_queue=mock_cmd_q
    )
    provider1.start()
    try:
        geometry_packet = {"type": "initial_map_geometry", "geometry": {"nodes": {}, "edges": {}}}
        mock_telem_q.put(geometry_packet)
        for _ in range(20):
            if callback1.called:
                break
            time.sleep(0.05)

        callback1.assert_called_with(geometry_packet)
        assert LiveDataProvider.CACHED_INITIAL_GEOMETRY == geometry_packet
    finally:
        provider1.stop()

    # Now simulate a second UI launch/restore from tray
    callback2 = MagicMock()
    mock_telem_q2 = queue.Queue()
    mock_cmd_q2 = queue.Queue()

    provider2 = LiveDataProvider(
        on_data_received=callback2, ui_telemetry_queue=mock_telem_q2, ui_command_queue=mock_cmd_q2
    )
    provider2.start()
    try:
        # It should immediately have invoked callback2 with cached geometry
        callback2.assert_called_with(geometry_packet)
    finally:
        provider2.stop()


def test_orchestrator_ipc_mode_disables_websocket_server():
    mock_sds_q = queue.Queue()
    mock_cmd_q = queue.Queue()
    mock_telem_q = queue.Queue()
    mock_settings = MagicMock()
    mock_lm = MagicMock()
    mock_lm.get_string.return_value = "Test Log"

    orchestrator = Orchestrator(
        sds_data_queue=mock_sds_q,
        settings=mock_settings,
        ui_command_queue=mock_cmd_q,
        locale_manager=mock_lm,
        ui_telemetry_queue=mock_telem_q,
    )

    # When ui_telemetry_queue is provided, WebSocketServer is not instantiated
    assert orchestrator.ui_telemetry_queue is not None
    assert orchestrator.ws_server is None
