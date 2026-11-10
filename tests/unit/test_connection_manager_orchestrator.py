# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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


def test_connection_operation_handler_get_string():
    lm = MagicMock()
    lm.get_string.return_value = "localized_msg"
    handler = ConnectionOperationHandler({}, {}, locale_manager=lm)
    assert handler._get_string("key") == "localized_msg"

    # Fallback without locale_manager
    handler_no_lm = ConnectionOperationHandler({}, {}, locale_manager=None)
    assert handler_no_lm._get_string("key", default="Default {param}", param="value") == "Default value"
    assert handler_no_lm._get_string("key", default=None) == "key"


def test_connection_operation_handler_restore_saved_async():
    active_conn = {}
    saved_ips = {}
    known_intersections = []
    toggle_func = MagicMock()

    handler = ConnectionOperationHandler(active_conn, saved_ips)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "src.controller.connection_config_repo.ConnectionConfigRepository.load_all_connections_db",
            MagicMock(return_value={"tl_1": "10.0.0.1:161"}),
        )
        # Run restore
        handler.restore_saved_connections_async(known_intersections, toggle_func)

        # Allow background thread to execute
        import time
        time.sleep(0.1)

    assert "tl_1" in saved_ips
    assert "tl_1" in known_intersections


def test_connection_operation_handler_connect_success_and_failure():
    from unittest.mock import patch
    active_conn = {}
    saved_ips = {}

    handler = ConnectionOperationHandler(active_conn, saved_ips)

    # 1. No IP provided
    with patch("src.controller.connection_config_repo.ConnectionConfigRepository.remove_connection_db") as mock_remove:
        res = handler.toggle_connection("tl_1", ip_address=None, action="connect")
        assert res is False
        assert mock_remove.called

    # 2. Invalid IP format
    with patch("src.controller.connection_config_repo.ConnectionConfigRepository.remove_connection_db") as mock_remove:
        res = handler.toggle_connection("tl_1", ip_address="invalid_ip", action="connect")
        assert res is False
        assert mock_remove.called

    # 3. Valid IP connect success
    mock_driver = MagicMock()
    mock_driver.is_connected = True
    with patch("src.controller.connection_operation_handler.TrafficLightDriver", return_value=mock_driver), \
         patch("src.controller.connection_config_repo.ConnectionConfigRepository.save_connection_db") as mock_save:
        res = handler.toggle_connection("tl_1", ip_address="192.168.1.10:161", action="connect")
        assert res is True
        assert "tl_1" in active_conn
        assert mock_save.called

    # 4. Valid IP connect failure (not connected)
    mock_driver_fail = MagicMock()
    mock_driver_fail.is_connected = False
    with patch("src.controller.connection_operation_handler.TrafficLightDriver", return_value=mock_driver_fail):
        res = handler.toggle_connection("tl_2", ip_address="192.168.1.20:161", action="connect")
        assert res is False
        assert "tl_2" not in active_conn


def test_connection_operation_handler_local_simulator_autodetection():
    from unittest.mock import patch
    active_conn = {}
    saved_ips = {}

    handler = ConnectionOperationHandler(active_conn, saved_ips)

    # Initial driver fails on standard port, but driver on candidate port 1610 succeeds
    first_driver = MagicMock()
    first_driver.is_connected = False

    detected_driver = MagicMock()
    detected_driver.is_connected = True

    def driver_side_effect(**kwargs):
        if kwargs.get("port") == 1610:
            return detected_driver
        return first_driver

    with patch("src.controller.connection_operation_handler.TrafficLightDriver", side_effect=driver_side_effect), \
         patch("src.controller.connection_config_repo.ConnectionConfigRepository.save_connection_db"):
        res = handler.toggle_connection("tl_1", ip_address="127.0.0.1", action="connect")
        assert res is True
        assert saved_ips["tl_1"] == "127.0.0.1:1610"
        assert active_conn["tl_1"] is detected_driver


def test_connection_operation_handler_import_csv_and_bulk_connect():
    from unittest.mock import patch
    active_conn = {"tl_1": MagicMock()}
    saved_ips = {}
    known_intersections = []

    handler = ConnectionOperationHandler(active_conn, saved_ips)

    mock_toggle = MagicMock(side_effect=[True, False])
    with patch(
        "src.controller.connection_config_repo.ConnectionConfigRepository.import_csv_config",
        return_value={"tl_1": "192.168.1.10", "tl_2": "192.168.1.20"},
    ):
        success, total = handler.import_csv_and_bulk_connect(
            filepath="connections.csv",
            known_intersections=known_intersections,
            toggle_func=mock_toggle,
        )

    assert total == 2
    assert success == 1
    assert "tl_1" in known_intersections
    assert "tl_2" in known_intersections

