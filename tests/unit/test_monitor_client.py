# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: tests/unit/test_monitor_client.py
# Author: Gabriel Moraes
# Date: September 2026

import json
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

try:
    from communication.monitor_client import MonitorClient
    from communication.monitor_payload import MonitorPayloadBuilder
    from communication.monitor_transport import MonitorHttpTransport
except ImportError:
    from src.communication.monitor_client import MonitorClient
    from src.communication.monitor_payload import MonitorPayloadBuilder
    from src.communication.monitor_transport import MonitorHttpTransport


class TestMonitorPayloadBuilder(unittest.TestCase):
    def test_create_payload_heartbeat(self):
        payload_str = MonitorPayloadBuilder.create_payload(category="", level="INFO", message="heartbeat")
        data = json.loads(payload_str)
        self.assertEqual(data["origin"], "Carina")
        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["message"], "heartbeat")
        self.assertIn("occurred_at", data)

    def test_create_payload_incident(self):
        payload_str = MonitorPayloadBuilder.create_payload(
            category="HARDWARE", level="CRITICAL", message="Sensor failure"
        )
        data = json.loads(payload_str)
        self.assertEqual(data["category"], "HARDWARE")
        self.assertEqual(data["level"], "CRITICAL")
        self.assertEqual(data["message"], "Sensor failure")


class TestMonitorClientFacade(unittest.TestCase):
    def setUp(self):
        MonitorClient._instance = None

    def tearDown(self):
        MonitorClient._instance = None

    @patch("communication.monitor_client.SettingsManager")
    @patch("communication.monitor_client.create_monitor_transport")
    def test_client_initialization_disabled(self, mock_create_transport, mock_settings_cls):
        mock_settings = MagicMock()
        mock_settings.load_settings.return_value = {"monitor_enabled": "False", "monitor_mqtt_host": "localhost"}
        mock_settings_cls.return_value = mock_settings

        mock_transport = MagicMock()
        mock_create_transport.return_value = mock_transport

        client = MonitorClient(settings_manager=mock_settings)
        self.assertFalse(client.enabled)
        self.assertEqual(MonitorClient.get_instance(), client)
        mock_create_transport.assert_called_once()

    @patch("communication.monitor_client.SettingsManager")
    @patch("transports.http_transport.requests.Session.post")
    def test_client_initialization_with_http_endpoint(self, mock_post, mock_settings_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        mock_settings = MagicMock()
        mock_settings.load_settings.return_value = {
            "monitor_enabled": "True",
            "monitor_mqtt_host": "https://monitor.noxfort.com/api/telemetry",
        }
        mock_settings_cls.return_value = mock_settings

        client = MonitorClient(settings_manager=mock_settings)
        self.assertTrue(client.enabled)
        self.assertIsInstance(client.transport, MonitorHttpTransport)
        self.assertTrue(client.is_connected)
        client.stop()

    @patch("communication.monitor_client.SettingsManager")
    @patch("communication.monitor_client.create_monitor_transport")
    def test_client_disconnect_manual_stops_and_preserves_instance(self, mock_create_transport, mock_settings_cls):
        mock_settings = MagicMock()
        mock_settings.load_settings.return_value = {"monitor_enabled": "True", "monitor_mqtt_host": "localhost"}
        mock_settings_cls.return_value = mock_settings

        mock_transport = MagicMock()
        mock_create_transport.return_value = mock_transport

        client = MonitorClient(settings_manager=mock_settings)
        self.assertTrue(client.enabled)

        client.disconnect_manual()
        self.assertFalse(client.enabled)
        self.assertFalse(client._running)
        mock_transport.disconnect.assert_called()
        self.assertIs(MonitorClient.get_instance(), client)


if __name__ == "__main__":
    unittest.main()
