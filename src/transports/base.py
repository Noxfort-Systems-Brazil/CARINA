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

# File: src/transports/base.py
# Author: Gabriel Moraes
# Date: 2026-09-12 (SOLID Refactoring)

"""
Defines the abstract base contract for all external Monitor communication transports.
Adheres to:
- Dependency Inversion Principle (DIP): High-level modules depend on BaseMonitorTransport.
- Liskov Substitution Principle (LSP): Any concrete transport is transparently interchangeable.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional


def _log_monitor_healthcheck(
    status_msg: str, is_connected: bool, enabled: bool, host: str = "127.0.0.1", port: int = 1883
):
    """Placeholder for monitor healthcheck audit logging."""
    pass


class BaseMonitorTransport(ABC):
    """
    Abstract base class representing a communication transport to the external Monitor system.
    Concrete implementations include HTTP REST (web/ngrok/cloud) and MQTT sockets.
    """

    def __init__(self, on_connect_cb: Optional[Callable] = None):
        self._enabled: bool = True
        self._on_connect_user_cb: Optional[Callable] = on_connect_cb

    @property
    def enabled(self) -> bool:
        """Returns whether this transport is administratively enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = bool(value)

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the transport is actively connected and capable of sending data."""
        pass

    @property
    @abstractmethod
    def host(self) -> str:
        """Returns the target hostname or domain string."""
        pass

    @property
    @abstractmethod
    def port(self) -> int:
        """Returns the target port number."""
        pass

    @property
    @abstractmethod
    def endpoint_display(self) -> str:
        """Returns a human-readable display string representing the target endpoint."""
        pass

    @abstractmethod
    def setup(self) -> None:
        """Initializes the connection and establishes the communication channel."""
        pass

    @abstractmethod
    def ensure_connected(self) -> bool:
        """Verifies active connectivity or triggers an automated reconnection attempt."""
        pass

    @abstractmethod
    def publish(self, topic: str, payload: str, qos: int = 1, timeout: float = 5.0) -> bool:
        """
        Publishes a JSON payload to the remote monitor.

        Args:
            topic: Destination topic or routing key (used by MQTT, ignored by direct HTTP).
            payload: Standardized JSON string.
            qos: Quality of Service level (0, 1, or 2).
            timeout: Maximum duration in seconds to wait for delivery acknowledgment.

        Returns:
            True if delivered successfully, False otherwise.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Closes any active sockets, background loops, or client sessions cleanly."""
        pass

    def setup_mqtt(self) -> None:
        """Backward compatibility alias for setup()."""
        self.setup()
