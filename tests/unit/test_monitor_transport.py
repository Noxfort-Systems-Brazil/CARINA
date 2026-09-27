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

# File: tests/unit/test_monitor_transport.py
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

try:
    from communication.monitor_transport import (
        BaseMonitorTransport,
        MonitorHttpTransport,
        MonitorMqttTransport,
        create_monitor_transport,
        is_http_endpoint,
        normalize_http_url,
    )
except ImportError:
    from src.communication.monitor_transport import (
        BaseMonitorTransport,
        MonitorHttpTransport,
        MonitorMqttTransport,
        create_monitor_transport,
        is_http_endpoint,
        normalize_http_url,
    )


class TestEndpointDetectionAndNormalization(unittest.TestCase):
    def test_is_http_endpoint(self):
        # HTTP / HTTPS explicit
        self.assertTrue(is_http_endpoint("https://medicochirurgical-stenophagous-london.ngrok-free.dev/api/telemetry"))
        self.assertTrue(is_http_endpoint("http://localhost:8080/api/telemetry"))
        self.assertTrue(is_http_endpoint("https://monitor.noxfort.com"))
        self.assertTrue(is_http_endpoint("http://192.168.1.50:8080"))

        # Domain names
        self.assertTrue(is_http_endpoint("monitor.noxfort.com"))
        self.assertTrue(is_http_endpoint("monitor.noxfort.com/api/telemetry"))
        self.assertTrue(is_http_endpoint("subdomain.ngrok-free.dev"))

        # MQTT / TCP explicit
        self.assertFalse(is_http_endpoint("tcp://0.tcp.sa.ngrok.io:12345"))
        self.assertFalse(is_http_endpoint("mqtt://192.168.1.10:1883"))
        self.assertFalse(is_http_endpoint("127.0.0.1:1883"))
        self.assertFalse(is_http_endpoint("localhost"))
        self.assertFalse(is_http_endpoint(""))

    def test_normalize_http_url(self):
        # Full URL with api path
        url1 = normalize_http_url("https://test.ngrok-free.dev/api/telemetry")
        self.assertEqual(url1, "https://test.ngrok-free.dev/api/telemetry")

        # Full URL without api path
        url2 = normalize_http_url("https://test.ngrok-free.dev")
        self.assertEqual(url2, "https://test.ngrok-free.dev/api/telemetry")

        # Domain without scheme
        url3 = normalize_http_url("monitor.noxfort.com")
        self.assertEqual(url3, "https://monitor.noxfort.com/api/telemetry")

        # Local IP without scheme
        url4 = normalize_http_url("192.168.1.100:8080")
        self.assertEqual(url4, "http://192.168.1.100:8080/api/telemetry")

        # Localhost without scheme
        url5 = normalize_http_url("localhost:8080")
        self.assertEqual(url5, "http://localhost:8080/api/telemetry")


class TestMonitorHttpTransport(unittest.TestCase):
    @patch("transports.http_transport.requests.Session.post")
    def test_publish_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        transport = MonitorHttpTransport(endpoint_url="https://monitor.noxfort.com/api/telemetry")
        res = transport.publish("noxfort/telemetry/", '{"origin":"Carina","message":"heartbeat"}')

        self.assertTrue(res)
        self.assertTrue(transport.is_connected)
        self.assertEqual(transport.host, "monitor.noxfort.com")
        self.assertEqual(transport.port, 443)
        mock_post.assert_called_once()

    @patch("transports.http_transport.requests.Session.post")
    def test_publish_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 502
        mock_resp.text = "Bad Gateway"
        mock_post.return_value = mock_resp

        transport = MonitorHttpTransport(endpoint_url="https://monitor.noxfort.com/api/telemetry")
        res = transport.publish("noxfort/telemetry/", '{"origin":"Carina","message":"heartbeat"}')

        self.assertFalse(res)
        self.assertFalse(transport.is_connected)

    @patch("transports.http_transport.requests.Session.post")
    def test_setup_and_ensure_connected(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        transport = MonitorHttpTransport(endpoint_url="https://monitor.noxfort.com/api/telemetry")
        self.assertFalse(transport.is_connected)

        transport.setup()
        self.assertTrue(transport.is_connected)
        self.assertTrue(transport.ensure_connected())

    def test_disconnect_disables_http_transport(self):
        transport = MonitorHttpTransport(endpoint_url="https://monitor.noxfort.com/api/telemetry")
        transport._is_connected = True
        self.assertTrue(transport.enabled)
        self.assertTrue(transport.is_connected)

        transport.disconnect()
        self.assertFalse(transport.enabled)
        self.assertFalse(transport.is_connected)
        self.assertIsNone(transport.session)

        # After disconnect, ensure_connected must return False without attempting any network connection
        with patch("transports.http_transport.requests.Session.post") as mock_post:
            self.assertFalse(transport.ensure_connected())
            mock_post.assert_not_called()


class TestMonitorMqttTransport(unittest.TestCase):
    def test_parse_host_port(self):
        host, port = MonitorMqttTransport.parse_host_port("192.168.1.10:1883")
        self.assertEqual(host, "192.168.1.10")
        self.assertEqual(port, 1883)

        host_def, port_def = MonitorMqttTransport.parse_host_port("localhost")
        self.assertEqual(host_def, "localhost")
        self.assertEqual(port_def, 1883)

        # TCP scheme
        host_tcp, port_tcp = MonitorMqttTransport.parse_host_port("tcp://0.tcp.sa.ngrok.io:12345")
        self.assertEqual(host_tcp, "0.tcp.sa.ngrok.io")
        self.assertEqual(port_tcp, 12345)

        # HTTPS prefix safety
        host_https, port_https = MonitorMqttTransport.parse_host_port("https://monitor.noxfort.com/api/telemetry")
        self.assertEqual(host_https, "monitor.noxfort.com")
        self.assertEqual(port_https, 1883)

    @patch("transports.mqtt_transport.mqtt")
    def test_publish_success(self, mock_mqtt):
        mock_client = MagicMock()
        mock_mqtt.Client.return_value = mock_client
        mock_info = MagicMock()
        mock_client.publish.return_value = mock_info

        transport = MonitorMqttTransport(host="localhost", port=1883)
        transport.setup_mqtt()
        transport._is_connected = True

        res = transport.publish("test/topic", '{"msg": "hi"}')
        self.assertTrue(res)
        mock_client.publish.assert_called_once_with("test/topic", '{"msg": "hi"}', qos=1)

    @patch("transports.mqtt_transport.mqtt")
    def test_disconnect_disables_mqtt_transport(self, mock_mqtt):
        mock_client = MagicMock()
        mock_mqtt.Client.return_value = mock_client
        transport = MonitorMqttTransport(host="localhost", port=1883)
        transport.setup_mqtt()
        transport._is_connected = True

        transport.disconnect()
        self.assertFalse(transport.enabled)
        self.assertFalse(transport.is_connected)
        mock_client.loop_stop.assert_called_once()
        mock_client.disconnect.assert_called_once()


class TestTransportFactory(unittest.TestCase):
    def test_create_monitor_transport_http(self):
        transport = create_monitor_transport(
            "https://medicochirurgical-stenophagous-london.ngrok-free.dev/api/telemetry"
        )
        self.assertIsInstance(transport, MonitorHttpTransport)
        self.assertIsInstance(transport, BaseMonitorTransport)

    def test_create_monitor_transport_mqtt(self):
        transport = create_monitor_transport("127.0.0.1:1883")
        self.assertIsInstance(transport, MonitorMqttTransport)
        self.assertIsInstance(transport, BaseMonitorTransport)

    def test_liskov_substitution(self):
        # Both transports satisfy the BaseMonitorTransport contract
        http_t = create_monitor_transport("https://domain.com")
        mqtt_t = create_monitor_transport("127.0.0.1:1883")

        self.assertTrue(issubclass(MonitorHttpTransport, BaseMonitorTransport))
        self.assertTrue(issubclass(MonitorMqttTransport, BaseMonitorTransport))
        self.assertTrue(hasattr(http_t, "setup"))
        self.assertTrue(hasattr(mqtt_t, "setup"))
        self.assertTrue(hasattr(http_t, "ensure_connected"))
        self.assertTrue(hasattr(mqtt_t, "ensure_connected"))
        self.assertTrue(hasattr(http_t, "publish"))
        self.assertTrue(hasattr(mqtt_t, "publish"))
        self.assertTrue(hasattr(http_t, "disconnect"))
        self.assertTrue(hasattr(mqtt_t, "disconnect"))


if __name__ == "__main__":
    unittest.main()
