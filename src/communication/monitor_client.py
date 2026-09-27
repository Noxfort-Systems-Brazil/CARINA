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

# File: src/communication/monitor_client.py
# Author: Gabriel Moraes
# Date: 2026-03-03 (Refactored 2026-07-31 for SRP)

"""
MonitorClient acts as the Facade/Orchestrator integrating CARINA with the external
'Monitor' system via MQTT, delegating payload building to MonitorPayloadBuilder
and network transport to MonitorMqttTransport.
"""

import logging
import threading
import time
from typing import Optional

from communication.monitor_payload import MonitorPayloadBuilder
from utils.locale_manager_backend import LocaleManagerBackend
from utils.settings_manager import SettingsManager

try:
    from transports import BaseMonitorTransport, _log_monitor_healthcheck, create_monitor_transport
except ImportError:
    from src.transports import BaseMonitorTransport, _log_monitor_healthcheck, create_monitor_transport


class MonitorClient:
    """Facade for Monitor integration: orchestrates heartbeat scheduling and incident reporting."""

    _instance: Optional["MonitorClient"] = None

    @classmethod
    def get_instance(
        cls, settings_manager: SettingsManager = None, locale_manager: LocaleManagerBackend = None
    ) -> "MonitorClient":
        if cls._instance is None:
            if settings_manager is None:
                try:
                    from src.utils.settings_manager import SettingsManager

                    settings_manager = SettingsManager()
                except Exception:
                    from utils.settings_manager import SettingsManager

                    settings_manager = SettingsManager()
            cls(settings_manager=settings_manager, locale_manager=locale_manager)
        return cls._instance

    def __init__(self, settings_manager: SettingsManager, locale_manager: LocaleManagerBackend = None):
        MonitorClient._instance = self
        self.settings = settings_manager.load_settings()
        self.locale_manager = locale_manager if locale_manager else LocaleManagerBackend()
        self.enabled = str(self.settings.get("monitor_enabled", "False")).lower() == "true"

        host_str = self.settings.get("monitor_mqtt_host", "localhost")
        self.transport = create_monitor_transport(host_str, on_connect_cb=self.send_instant_heartbeat)
        self.transport.enabled = self.enabled

        self.topic_telemetry = "noxfort/telemetry/"
        self._running = False
        self._heartbeat_thread = None
        self._stop_event = threading.Event()
        self._heartbeat_interval = 30  # seconds
        self._reconnect_interval = 15  # seconds

        if self.enabled:
            self.transport.setup()
            self.start()

    @property
    def host(self) -> str:
        return self.transport.host

    @host.setter
    def host(self, value: str):
        self.transport.host = value

    @property
    def port(self) -> int:
        return self.transport.port

    @port.setter
    def port(self, value: int):
        self.transport.port = value

    @property
    def client(self):
        return getattr(self.transport, "client", None)

    @client.setter
    def client(self, value):
        if hasattr(self.transport, "client"):
            self.transport.client = value

    @property
    def is_connected(self) -> bool:
        return self.transport.is_connected

    def _ensure_connected(self) -> bool:
        return self.transport.ensure_connected()

    def start(self):
        """Starts the periodic heartbeat loop."""
        if not self.enabled:
            return

        self._running = True
        self._stop_event.clear()
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._heartbeat_thread.start()
            logging.info(f"[{self.__class__.__name__}] Heartbeat loop started (Interval: {self._heartbeat_interval}s)")
            _log_monitor_healthcheck("HEARTBEAT LOOP STARTED", self.is_connected, self.enabled, self.host, self.port)

    def stop(self, shutdown_message: str = None):
        """
        Stops the heartbeat loop and disconnects from MQTT/HTTP.

        Args:
            shutdown_message: Optional message to send as a final incident report before disconnecting.
        """
        self._running = False
        self._stop_event.set()

        if shutdown_message and self.enabled and self.is_connected:
            try:
                self.report_incident(category="SOFTWARE", level="CRITICAL", message=shutdown_message)
            except Exception as e:
                logging.error(f"[{self.__class__.__name__}] Failed to send shutdown message: {e}")

        self.enabled = False
        if self.transport:
            self.transport.disconnect()

        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)
            self._heartbeat_thread = None

        _log_monitor_healthcheck("MONITOR CLIENT STOPPED", False, False, self.host, self.port)

    def connect_manual(self, host_str: str):
        """Called by the UI to force a new live connection and persist state."""
        self.stop()

        self.enabled = True
        self.transport = create_monitor_transport(host_str, on_connect_cb=self.send_instant_heartbeat)
        self.transport.enabled = True

        # Persist monitor_enabled = True so CARINA stays constantly connected across restarts
        try:
            from src.utils.settings_manager import SettingsManager

            sm = SettingsManager()
            curr = sm.load_settings()
            curr["monitor_enabled"] = "True"
            curr["monitor_mqtt_host"] = host_str
            curr["monitor_mqtt_port"] = str(self.port)
            sm.save_settings(curr)
        except Exception as err:
            logging.error(f"[{self.__class__.__name__}] Failed to persist monitor_enabled setting: {err}")

        _log_monitor_healthcheck("MANUAL CONNECT REQUEST", self.is_connected, True, self.host, self.port)
        self.transport.setup()
        self.start()

    def disconnect_manual(self):
        """Called by the UI to explicitly disconnect immediately and persist state."""
        self.enabled = False
        if self.transport:
            self.transport.enabled = False

        # Persist monitor_enabled = False on explicit manual disconnect
        try:
            from src.utils.settings_manager import SettingsManager

            sm = SettingsManager()
            curr = sm.load_settings()
            curr["monitor_enabled"] = "False"
            sm.save_settings(curr)
        except Exception as err:
            logging.error(f"[{self.__class__.__name__}] Failed to persist monitor_enabled setting: {err}")

        _log_monitor_healthcheck("MANUAL DISCONNECT REQUEST", False, False, self.host, self.port)
        msg = self.locale_manager.get_string(
            "monitor.manual_disconnect", default="Operator explicitly disconnected CARINA from Monitor."
        )
        self.stop(shutdown_message=msg)

    def _heartbeat_loop(self):
        """Periodically checks connection health and publishes heartbeat."""
        counter = 0
        while self._running and not self._stop_event.is_set():
            if not self.enabled:
                break

            if counter % 10 == 0:
                _log_monitor_healthcheck(
                    f"PERIODIC HEALTHCHECK (Tick: {counter}s)", self.is_connected, self.enabled, self.host, self.port
                )

            if not self.is_connected and (counter % self._reconnect_interval == 0):
                logging.info(
                    f"[{self.__class__.__name__}] Healthcheck: Monitor connection inactive. Re-establishing connection..."
                )
                _log_monitor_healthcheck(
                    "HEALTHCHECK TRIGGERED AUTO-RECONNECT", False, self.enabled, self.host, self.port
                )
                try:
                    self.transport.ensure_connected()
                except Exception as err:
                    logging.error(f"[{self.__class__.__name__}] Healthcheck reconnect attempt error: {err}")

            if counter % self._heartbeat_interval == 0:
                self.send_instant_heartbeat()

            counter += 1
            if self._stop_event.wait(timeout=1.0):
                break

    def send_instant_heartbeat(self):
        """Sends the strict heartbeat JSON payload."""
        if not self.enabled or not self.is_connected:
            return
        try:
            payload = MonitorPayloadBuilder.create_payload(category="", level="INFO", message="heartbeat")
            if self.transport.publish(self.topic_telemetry, payload, qos=1, timeout=2.0):
                logging.debug(f"[{self.__class__.__name__}] Instant heartbeat published to Monitor.")
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Failed to send heartbeat: {e}")

    def report_incident(self, category: str, level: str, message: str) -> bool:
        """
        Immediately publishes an incident notification.

        Args:
            category (str): "HARDWARE" or "SOFTWARE"
            level (str): "WARNING" or "CRITICAL" (or "INFO")
            message (str): Descriptive text of the error.

        Returns:
            bool: True if successfully sent to MQTT, False otherwise.
        """
        if not self.enabled or not self._ensure_connected():
            return False

        try:
            payload = MonitorPayloadBuilder.create_payload(category, level, message)
            success = self.transport.publish(self.topic_telemetry, payload, qos=1, timeout=2.0)
            if success:
                logging.info(f"[{self.__class__.__name__}] Sent Incident ({level}): {message}")
            return success
        except Exception as e:
            logging.error(f"[{self.__class__.__name__}] Failed to send incident report: {e}")
            return False
