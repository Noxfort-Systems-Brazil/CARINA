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

# File: tests/unit/test_connection_manager_orchestrator.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock

import pytest

from src.controller.connection_operation_handler import ConnectionOperationHandler
from src.controller.intersection_resolver import IntersectionResolver
from src.utils.network_address_parser import NetworkAddressParser


def test_network_address_parser():
    """Verify NetworkAddressParser RegEx extraction and IPv4 validation."""
    valid, ip, port, clean = NetworkAddressParser.parse_and_validate_ip("192.168.1.50:80161")
    assert valid is True
    assert ip == "192.168.1.50"
    assert port == 80161
    assert clean == "192.168.1.50:80161"

    # Default port fallback
    valid, ip, port, clean = NetworkAddressParser.parse_and_validate_ip("10.0.0.1")
    assert valid is True
    assert ip == "10.0.0.1"
    assert port == 161
    assert clean == "10.0.0.1"

    # Invalid IPv4 address
    valid, ip, port, clean = NetworkAddressParser.parse_and_validate_ip("999.999.999.999")
    assert valid is False


def test_intersection_resolver():
    """Verify IntersectionResolver IP mapping and status resolution."""
    active_conn = {}
    saved_ips = {"tl_1": "192.168.1.100"}

    mock_driver = MagicMock()
    mock_driver.is_connected = True
    mock_driver.ip_address = "192.168.1.50"
    mock_driver.hardware_driver.brand = "Noxfort"
    mock_driver.hardware_driver.model = "NTCIP-2026"
    active_conn["tl_2"] = mock_driver

    resolver = IntersectionResolver(active_conn, saved_ips)

    # Resolve IP of active driver
    assert resolver.find_intersection_by_ip("192.168.1.50") == "tl_2"
    # Resolve IP of saved IP
    assert resolver.find_intersection_by_ip("192.168.1.100") == "tl_1"
    # Connection state check
    assert resolver.is_intersection_connected("tl_2") is True
    assert resolver.is_intersection_connected("tl_1") is False

    # Hardware info check
    info = resolver.get_hardware_info("tl_2")
    assert info["is_connected"] is True
    assert info["brand"] == "Noxfort"
    assert info["model"] == "NTCIP-2026"


def test_connection_operation_handler_disconnect():
    """Verify that toggle_connection with action='disconnect' cleans active_connections, saved_ips, and database."""
    active_conn = {}
    saved_ips = {"tl_1": "192.168.1.100", "1": "192.168.1.100"}

    mock_driver = MagicMock()
    mock_driver.is_connected = True
    active_conn["tl_1"] = mock_driver

    handler = ConnectionOperationHandler(active_conn, saved_ips)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("src.controller.connection_config_repo.ConnectionConfigRepository.remove_connection_db", MagicMock())
        result = handler.toggle_connection("tl_1", action="disconnect")

    assert result is False
    assert "tl_1" not in active_conn
    assert "tl_1" not in saved_ips
    assert "1" not in saved_ips
    mock_driver.shutdown.assert_called_once()


def test_connection_operation_handler_shutdown_all():
    """Verify that shutdown_all_connections cleans all active_connections and saved_ips."""
    mock_driver1 = MagicMock()
    mock_driver2 = MagicMock()
    active_conn = {"tl_1": mock_driver1, "tl_2": mock_driver2}
    saved_ips = {"tl_1": "192.168.1.10", "tl_2": "192.168.1.20"}

    handler = ConnectionOperationHandler(active_conn, saved_ips)
    handler.shutdown_all_connections()

    assert len(active_conn) == 0
    assert len(saved_ips) == 0
    mock_driver1.shutdown.assert_called_once()
    mock_driver2.shutdown.assert_called_once()
