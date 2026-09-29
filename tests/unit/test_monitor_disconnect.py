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

# File: tests/unit/test_monitor_disconnect.py
# Author: Gabriel Moraes
# Date: September 2026

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.drivers.incident_reporter import IncidentReporter
from src.handlers.ui_command_handler import UICommandHandler


class TestMonitorDisconnect(unittest.TestCase):
    @patch("src.utils.settings_manager.SettingsManager")
    @patch("src.communication.monitor_client.MonitorClient")
    def test_incident_reporter_report_noop_when_disabled(self, mock_mon_cls, mock_settings_cls):
        mock_settings = MagicMock()
        mock_settings.load_settings.return_value = {"monitor_enabled": "False"}
        mock_settings_cls.return_value = mock_settings

        mock_mon = MagicMock()
        mock_mon.enabled = False
        mock_mon_cls.get_instance.return_value = mock_mon

        with patch("requests.post") as mock_http_post:
            IncidentReporter.report("TL_TEST_01", "CRITICAL", "Hardware fault")
            mock_mon.report_incident.assert_not_called()
            mock_mon._ensure_connected.assert_not_called()
            mock_http_post.assert_not_called()

    @patch("src.utils.settings_manager.SettingsManager")
    @patch("src.communication.monitor_client.MonitorClient")
    def test_incident_reporter_report_trap_noop_when_disabled(self, mock_mon_cls, mock_settings_cls):
        mock_settings = MagicMock()
        mock_settings.load_settings.return_value = {"monitor_enabled": "False"}
        mock_settings_cls.return_value = mock_settings

        mock_mon = MagicMock()
        mock_mon.enabled = False
        mock_mon_cls.get_instance.return_value = mock_mon

        with patch("requests.post") as mock_http_post:
            IncidentReporter.report_trap("TL_TEST_01", "CRITICAL", {"message": "Lamp failure"})
            mock_mon.report_incident.assert_not_called()
            mock_mon._ensure_connected.assert_not_called()
            mock_http_post.assert_not_called()

    @patch("src.handlers.ui_command_handler.SettingsManager")
    def test_ui_command_handler_save_settings_disconnects_monitor(self, mock_settings_cls):
        mock_settings_inst = MagicMock()
        mock_settings_cls.return_value = mock_settings_inst

        mock_failsafe = MagicMock()
        mock_monitor_client = MagicMock()
        mock_failsafe.monitor_client = mock_monitor_client

        handler = UICommandHandler(
            locale_manager=MagicMock(),
            override_manager=MagicMock(),
            failsafe_manager=mock_failsafe,
            security_manager=MagicMock(),
            sds_data_queue=MagicMock(),
        )

        cmd = {
            "type": "save_settings",
            "payload": {
                "EXTERNAL_MONITOR": {"monitor_enabled": "False", "monitor_mqtt_host": "http://mycarina.duckdns.org"}
            },
        }

        handler.process(cmd, sumo_conn=None, override_commands_buffer=[])
        mock_monitor_client.disconnect_manual.assert_called_once()
        mock_monitor_client.connect_manual.assert_not_called()

    @patch("src.handlers.ui_command_handler.SettingsManager")
    def test_ui_command_handler_set_monitor_connection_disconnect(self, mock_settings_cls):
        mock_settings_inst = MagicMock()
        mock_settings_cls.return_value = mock_settings_inst
        mock_settings_inst.load_settings.return_value = {}

        mock_failsafe = MagicMock()
        mock_monitor_client = MagicMock()
        mock_failsafe.monitor_client = mock_monitor_client

        handler = UICommandHandler(
            locale_manager=MagicMock(),
            override_manager=MagicMock(),
            failsafe_manager=mock_failsafe,
            security_manager=MagicMock(),
            sds_data_queue=MagicMock(),
        )

        cmd = {"type": "set_monitor_connection", "payload": {"enabled": False, "host": "http://mycarina.duckdns.org"}}

        handler.process(cmd, sumo_conn=None, override_commands_buffer=[])
        mock_monitor_client.disconnect_manual.assert_called_once()
        mock_settings_inst.save_settings.assert_called_once()
        saved_dict = mock_settings_inst.save_settings.call_args[0][0]
        self.assertEqual(saved_dict["monitor_enabled"], "False")


if __name__ == "__main__":
    unittest.main()
