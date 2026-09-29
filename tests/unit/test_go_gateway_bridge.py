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

# File: tests/unit/test_go_gateway_bridge.py
# Author: Gabriel Moraes
# Date: September 2026

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from src.drivers.go_driver_proxy import GoTrafficDriverProxy
from src.drivers.go_gateway_client import GoGatewayClient
from src.utils.paths import resource_path


@pytest.mark.unit
def test_go_gateway_binary_exists():
    binary_path = resource_path(os.path.join("bin", "carina-go"))
    assert os.path.exists(binary_path), f"Binário Go não encontrado em {binary_path}"
    assert os.access(binary_path, os.X_OK), f"Binário Go em {binary_path} não é executável"


@pytest.mark.unit
def test_go_gateway_client_lifecycle():
    client = GoGatewayClient()
    try:
        # 1. Start gateway
        assert client.start() is True
        assert client.is_running() is True

        # 2. Ping
        assert client.ping(timeout=2.0) is True

        # 3. Connect intersection (NTCIP)
        res = client.connect_intersection(
            intersection_id="J_UNIT_1",
            ip="127.0.0.1",
            port=16199,
            protocol="ntcip",
            green_stages=[0, 1, 2, 3],
        )
        assert res.get("success") is True
        data = res.get("data", {})
        assert data.get("protocol") == "NTCIP 1202"
        assert data.get("is_connected") is True

        # 4. Telemetry query (offline because 16199 is not a live controller)
        telemetry = client.get_telemetry("J_UNIT_1")
        assert telemetry.get("intersection_id") == "J_UNIT_1"
        assert telemetry.get("status") == "offline"

        # 5. Disconnect
        assert client.disconnect_intersection("J_UNIT_1") is True

        # 6. Emergency release
        assert client.emergency_release_all() is True

    finally:
        client.stop()
        assert client.is_running() is False


@pytest.mark.unit
def test_go_traffic_driver_proxy():
    client = GoGatewayClient()
    try:
        assert client.start() is True
        res = client.connect_intersection(
            intersection_id="J_PROXY_TEST",
            ip="127.0.0.1",
            port=16198,
            protocol="ntcip",
            green_stages=[0, 1],
        )
        assert res.get("success") is True

        proxy = GoTrafficDriverProxy(
            ip_address="127.0.0.1",
            port=16198,
            intersection_id="J_PROXY_TEST",
            protocol_name="NTCIP 1202",
            brand="Siemens",
            model="ST950",
            client=client,
        )

        assert proxy.get_protocol_name() == "NTCIP 1202"
        assert proxy.brand == "Siemens"
        assert proxy.model == "ST950"

        # Telemetry
        status = proxy.get_telemetry()
        assert status.get("intersection_id") == "J_PROXY_TEST"
        assert status.get("brand") == "Siemens"

        # Release control
        proxy.release_control()

        # Shutdown
        proxy.shutdown()

    finally:
        client.stop()


@pytest.mark.unit
def test_go_driver_proxy_stop_heartbeat_calls_shutdown():
    mock_client = MagicMock()
    proxy = GoTrafficDriverProxy(
        ip_address="127.0.0.1",
        port=16198,
        intersection_id="J_PROXY_HB",
        client=mock_client,
    )
    proxy.stop_heartbeat()
    mock_client.disconnect_intersection.assert_called_once_with("J_PROXY_HB")


@pytest.mark.unit
def test_go_gateway_client_disconnect_alternate_id_fallback():
    client = GoGatewayClient()
    with patch.object(client, "send_command") as mock_send:
        # First attempt fails, second attempt succeeds
        mock_send.side_effect = [{"success": False}, {"success": True}]
        result = client.disconnect_intersection("tl_123")
        assert result is True
        assert mock_send.call_count == 2
        mock_send.assert_any_call("disconnect", timeout=3.0, intersection_id="tl_123")
        mock_send.assert_any_call("disconnect", timeout=3.0, intersection_id="123")
