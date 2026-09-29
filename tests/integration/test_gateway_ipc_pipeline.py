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

# File: tests/integration/test_gateway_ipc_pipeline.py
# Author: Gabriel Moraes
# Date: September 2026

import os

import pytest

from src.drivers.go_gateway_client import GoGatewayClient
from src.utils.paths import resource_path


@pytest.mark.integration
def test_go_gateway_ipc_lifecycle():
    binary_path = resource_path(os.path.join("bin", "carina-go"))
    assert os.path.exists(binary_path), f"Binary not found at {binary_path}"

    client = GoGatewayClient(binary_path=binary_path)

    try:
        # Start gateway subprocess and verify ping handshake
        started = client.start()
        assert started is True
        assert client.is_running() is True

        # Send ping
        ping_ok = client.ping(timeout=2.0)
        assert ping_ok is True

        # Query telemetry for unconfigured intersection
        telem = client.get_telemetry("tl_integration_test")
        assert telem is not None
        assert telem.get("status") == "offline"
        assert telem.get("intersection_id") == "tl_integration_test"

        # Emergency release
        rel = client.emergency_release_all()
        assert rel is True

    finally:
        client.stop()
        assert client.is_running() is False
