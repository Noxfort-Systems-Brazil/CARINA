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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_transports_modular.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock, patch

import pytest

from transports.base import BaseMonitorTransport
from transports.endpoint_resolver import EndpointResolver, is_http_endpoint, normalize_http_url, parse_mqtt_host_port
from transports.factory import TransportFactory, create_monitor_transport
from transports.http_transport import MonitorHttpTransport
from transports.mqtt_transport import MonitorMqttTransport


@pytest.mark.unit
def test_endpoint_resolver_is_http():
    assert is_http_endpoint("http://example.com") is True
    assert is_http_endpoint("https://example.com/api") is True
    assert is_http_endpoint("tcp://broker.hivemq.com:1883") is False
    assert is_http_endpoint("mqtt://localhost:1883") is False
    assert is_http_endpoint("localhost:8080") is True
    assert is_http_endpoint("localhost:1883") is False
    assert is_http_endpoint("subdomain.ngrok-free.app") is True
    assert is_http_endpoint("monitor.noxfort.com") is True
    assert is_http_endpoint("") is False
    assert is_http_endpoint("192.168.1.1:1883") is False


@pytest.mark.unit
def test_endpoint_resolver_normalize_http_url():
    assert normalize_http_url("") == "http://localhost:8080/api/telemetry"
    assert normalize_http_url("localhost:8080") == "http://localhost:8080/api/telemetry"
    assert normalize_http_url("192.168.1.50:5000/api/telemetry") == "http://192.168.1.50:5000/api/telemetry"
    assert normalize_http_url("cloud.noxfort.com/status") == "https://cloud.noxfort.com/status/api/telemetry"


@pytest.mark.unit
def test_endpoint_resolver_parse_mqtt_host_port():
    h, p = parse_mqtt_host_port("tcp://broker.emqx.io:1883")
    assert h == "broker.emqx.io"
    assert p == 1883

    h2, p2 = parse_mqtt_host_port("mqtt://127.0.0.1:8883/path")
    assert h2 == "127.0.0.1"
    assert p2 == 8883

    h3, p3 = parse_mqtt_host_port("localhost:invalid_port")
    assert h3 == "localhost"
    assert p3 == 1883


@pytest.mark.unit
def test_http_transport_lifecycle_and_publish():
    transport = MonitorHttpTransport(endpoint_url="http://127.0.0.1:8080/api/telemetry")
    assert transport.host == "127.0.0.1"
    assert transport.port == 8080
    assert transport.endpoint_display == "http://127.0.0.1:8080/api/telemetry"
    assert transport.enabled is True

    # Test publish success
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch.object(transport.session, "post", return_value=mock_resp):
        res = transport.publish("test_topic", '{"data": 123}')
        assert res is True
        assert transport.is_connected is True

    # Test publish failure (status 500)
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    with patch.object(transport.session, "post", return_value=mock_resp):
        res = transport.publish("test_topic", '{"data": 123}')
        assert res is False
        assert transport.is_connected is False

    # Disconnect
    transport.disconnect()
    assert transport.enabled is False
    assert transport.is_connected is False
    assert transport.session is None


@pytest.mark.unit
def test_http_transport_setup_callback():
    cb_called = []

    def on_connect():
        cb_called.append(True)

    transport = MonitorHttpTransport(endpoint_url="http://127.0.0.1:8080/api/telemetry", on_connect_cb=on_connect)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch.object(transport.session, "post", return_value=mock_resp):
        transport.setup()
        assert transport.is_connected is True


@pytest.mark.unit
def test_mqtt_transport_lifecycle():
    transport = MonitorMqttTransport(host="broker.hivemq.com", port=1883)
    assert transport.host == "broker.hivemq.com"
    assert transport.port == 1883
    assert transport.endpoint_display == "broker.hivemq.com:1883"

    mock_client = MagicMock()
    mock_client.is_connected.return_value = True
    transport.client = mock_client
    transport._is_connected = True
    assert transport.is_connected is True

    # Publish
    mock_info = MagicMock()
    mock_client.publish.return_value = mock_info
    assert transport.publish("topic/carina", '{"msg": "hi"}') is True
    mock_info.wait_for_publish.assert_called_once()

    # Disconnect
    transport.disconnect()
    assert transport.enabled is False
    assert transport.is_connected is False
    assert transport.client is None


@pytest.mark.unit
def test_mqtt_transport_callbacks():
    cb = MagicMock()
    transport = MonitorMqttTransport(host="localhost", port=1883, on_connect_cb=cb)

    # Callback success
    transport._on_connect(None, None, None, 0)
    assert transport._is_connected is True

    # Callback failure
    transport._on_connect(None, None, None, 5)
    assert transport._is_connected is False

    # Disconnect callback
    transport._on_disconnect(None, None, None, 1)
    assert transport._is_connected is False


@pytest.mark.unit
def test_transport_factory_creation():
    # HTTP endpoint
    http_transport = create_monitor_transport("http://localhost:8080/api/telemetry")
    assert isinstance(http_transport, MonitorHttpTransport)

    # MQTT endpoint
    mqtt_transport = create_monitor_transport("localhost:1883")
    assert isinstance(mqtt_transport, MonitorMqttTransport)

    # Custom registration
    class DummyTransport(BaseMonitorTransport):
        @property
        def is_connected(self):
            return True

        @property
        def host(self):
            return "custom"

        @property
        def port(self):
            return 9999

        @property
        def endpoint_display(self):
            return "dummy"

        def setup(self):
            pass

        def ensure_connected(self):
            return True

        def publish(self, topic, payload, qos=1, timeout=5.0):
            return True

        def disconnect(self):
            pass

    TransportFactory.register_transport("custom", DummyTransport)
    assert TransportFactory._registry["custom"] is DummyTransport
