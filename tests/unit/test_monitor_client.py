# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import unittest
from unittest.mock import MagicMock, patch

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
