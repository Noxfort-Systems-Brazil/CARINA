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

# File: src/transports/mqtt_transport.py
# Author: Gabriel Moraes
# Date: 2026-09-12 (SOLID Refactoring)

"""
MonitorMqttTransport handles lower-level MQTT socket lifecycle, reconnection, and publishing.
Adheres to:
- Single Responsibility Principle (SRP): Focuses exclusively on MQTT broker connections,
  paho-mqtt event loops, QoS message delivery, and socket keepalive.
- Liskov Substitution Principle (LSP): Fully implements BaseMonitorTransport.
"""

import logging
import os
import threading
import time
from typing import Callable, Optional, Tuple

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

from transports.base import BaseMonitorTransport, _log_monitor_healthcheck
from transports.endpoint_resolver import EndpointResolver


class MonitorMqttTransport(BaseMonitorTransport):
    """Manages low-level MQTT connection, network loops, and publishing for Monitor integration."""

    def __init__(self, host: str = "localhost", port: int = 1883, on_connect_cb: Optional[Callable] = None):
        super().__init__(on_connect_cb=on_connect_cb)
        self._host, self._port = EndpointResolver.parse_mqtt_host_port(host, default_port=port)
        self.client: Optional[mqtt.Client] = None
        self._is_connected = False

    @staticmethod
    def parse_host_port(host_str: str, default_port: int = 1883) -> Tuple[str, int]:
        """Backward compatibility helper delegating to EndpointResolver."""
        return EndpointResolver.parse_mqtt_host_port(host_str, default_port=default_port)

    @property
    def host(self) -> str:
        return self._host

    @host.setter
    def host(self, value: str) -> None:
        self._host = value

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, value: int) -> None:
        self._port = int(value)

    @property
    def endpoint_display(self) -> str:
        return f"{self._host}:{self._port}"

    @property
    def is_connected(self) -> bool:
        """Returns True if MQTT client is active and connected."""
        if not self.enabled or not self.client:
            return False
        try:
            return bool(self.client.is_connected())
        except Exception:
            return False

    def configure_endpoint(self, host_str: str) -> None:
        """Updates host and port from a string representation."""
        self._host, self._port = EndpointResolver.parse_mqtt_host_port(host_str)

    def setup(self) -> None:
        """Initializes MQTT client and connects to the broker with a process-unique client ID."""
        self.setup_mqtt()

    def setup_mqtt(self) -> None:
        """Initializes MQTT client and connects to the broker with a process-unique client ID."""
        if not self.enabled:
            return
        if mqtt is None:
            logging.warning(f"[{self.__class__.__name__}] paho-mqtt is not installed; MQTT transport cannot connect.")
            self._is_connected = False
            return

        try:
            if self.client:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except Exception:
                    pass

            client_id = f"carina_monitor_client_{os.getpid()}"
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            logging.info(
                f"[{self.__class__.__name__}] Connecting to MQTT Broker at {self.host}:{self.port} (ID: {client_id})"
            )
            self.client.connect(self.host, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Connection attempt to MQTT Broker failed: {e}")
            self._is_connected = False

    def ensure_connected(self) -> bool:
        """Verifies active connection, waiting or re-establishing if necessary."""
        if not self.enabled:
            return False

        if self.is_connected:
            return True

        # Wait up to 1.5s for any background connection to complete
        for _ in range(15):
            if self.is_connected:
                return True
            time.sleep(0.1)

        logging.info(
            f"[{self.__class__.__name__}] MQTT client disconnected or uninitialized. Re-establishing connection..."
        )
        self.setup_mqtt()

        for _ in range(15):
            if self.is_connected:
                return True
            time.sleep(0.1)

        return self.is_connected

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self._is_connected = True
            logging.info(f"[{self.__class__.__name__}] Connected successfully to MQTT Broker.")
            _log_monitor_healthcheck("MQTT CONNECTED SUCCESS", True, self.enabled, self.host, self.port)
            if self._on_connect_user_cb:
                threading.Thread(target=self._on_connect_user_cb, daemon=True).start()
        else:
            self._is_connected = False
            logging.error(f"[{self.__class__.__name__}] Connection to MQTT failed with result code {reason_code}")
            _log_monitor_healthcheck(
                f"MQTT CONNECT FAILED (code: {reason_code})", False, self.enabled, self.host, self.port
            )

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        self._is_connected = False
        _log_monitor_healthcheck(f"MQTT DISCONNECTED (code: {reason_code})", False, self.enabled, self.host, self.port)
        if reason_code != 0 and self.enabled:
            logging.warning(
                f"[{self.__class__.__name__}] Unexpected disconnect from MQTT Broker (code: {reason_code}). Triggering auto-reconnect..."
            )
            threading.Thread(target=self.ensure_connected, daemon=True).start()

    def publish(self, topic: str, payload: str, qos: int = 1, timeout: float = 2.0) -> bool:
        """Publishes a payload to the given topic."""
        if not self.enabled or not self.client or not self.is_connected:
            return False
        try:
            info = self.client.publish(topic, payload, qos=qos)
            info.wait_for_publish(timeout=timeout)
            return True
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Failed to publish to topic {topic}: {e}")
            return False

    def disconnect(self) -> None:
        """Stops network loop, disables transport, and disconnects client."""
        self.enabled = False
        self._is_connected = False
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
            self.client = None
