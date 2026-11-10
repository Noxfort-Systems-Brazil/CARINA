# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the abstract base contract for all external Monitor communication transports.
Adheres to:
- Dependency Inversion Principle (DIP): High-level modules depend on BaseMonitorTransport.
- Liskov Substitution Principle (LSP): Any concrete transport is transparently interchangeable.
"""

from abc import ABC, abstractmethod
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def _log_monitor_healthcheck(
    status_msg: str, is_connected: bool, enabled: bool, host: str = "127.0.0.1", port: int = 1883
):
    """Logs monitor transport healthcheck state transitions at debug level."""
    logger.debug(
        "[MonitorHealthcheck] status=%s | connected=%s | enabled=%s | endpoint=%s:%s",
        status_msg,
        is_connected,
        enabled,
        host,
        port,
    )


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
