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

# File: tests/unit/test_connection_db_persistence.py
# Author: Gabriel Moraes
# Date: September 2026

import os
import sys

import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.controller.connection_config_repo import ConnectionConfigRepository


def test_db_connection_persistence():
    test_id = "test_intersection_99"
    test_ip = "192.168.1.99:1610"

    # Save to DB
    saved = ConnectionConfigRepository.save_connection_db(test_id, test_ip)
    assert saved is True

    # Load from DB
    loaded_configs = ConnectionConfigRepository.load_all_connections_db()
    assert test_id in loaded_configs
    assert loaded_configs[test_id] == test_ip

    # Remove/Deactivate auto-connect
    removed = ConnectionConfigRepository.remove_connection_db(test_id)
    assert removed is True

    # Verify no longer active
    reloaded_configs = ConnectionConfigRepository.load_all_connections_db()
    assert test_id not in reloaded_configs


def test_toggle_connection_explicit_disconnect(mocker=None):
    from unittest.mock import MagicMock, patch

    from src.controller.connection_manager import HardwareConnectionManager

    test_id = "test_intersection_disconnect"
    test_ip = "192.168.1.100"

    # Pre-save to DB as auto_connect=True
    ConnectionConfigRepository.save_connection_db(test_id, test_ip)
    assert test_id in ConnectionConfigRepository.load_all_connections_db()

    with patch("src.controller.connection_manager.HardwareConnectionManager._load_and_restore_saved_connections"):
        HardwareConnectionManager._active_instance = None
        mgr = HardwareConnectionManager.get_instance()

    with patch("src.controller.connection_manager.TrafficLightDriver") as mock_driver_cls:
        # Explicit disconnect on an intersection that is NOT currently in active_connections
        result = mgr.toggle_connection(test_id, ip_address=test_ip, action="disconnect")

        assert result is False
        # Assert TrafficLightDriver was NEVER instantiated (no SNMP probes/handshake)
        mock_driver_cls.assert_not_called()
        # Assert auto_connect was deactivated in DB
        assert test_id not in ConnectionConfigRepository.load_all_connections_db()
