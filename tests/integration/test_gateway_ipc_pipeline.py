# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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


@pytest.mark.integration
def test_go_gateway_pure_pipe_concurrency():
    binary_path = resource_path(os.path.join("bin", "carina-go"))
    sock_path = "/tmp/carina_gateway.sock"

    # Ensure no lingering socket exists before starting
    if os.path.exists(sock_path):
        os.remove(sock_path)

    client = GoGatewayClient(binary_path=binary_path)

    try:
        assert client.start() is True
        assert client.is_running() is True
        assert client.ping(timeout=2.0) is True

        # Verify that pure pipe mode DOES NOT create any Unix domain socket
        assert not os.path.exists(sock_path), f"Unix domain socket unexpectedly created at {sock_path}"

        # Test concurrent / sequential queries over the anonymous pipe
        res_a = client.send_command("gateway_get_status")
        res_b = client.send_command("gateway_get_status")
        assert res_a.get("success") is True
        assert res_b.get("success") is True

    finally:
        client.stop()
        assert client.is_running() is False
        assert not os.path.exists(sock_path)

