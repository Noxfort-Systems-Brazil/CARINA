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

# File: src/transports/factory.py
# Author: Gabriel Moraes
# Date: 2026-09-12 (SOLID Refactoring)

"""
TransportFactory: Factory Method for creating concrete Monitor transports.
Adheres to:
- Open/Closed Principle (OCP): New transports (e.g., WebSocket, gRPC) can be registered
  dynamically via register_transport without modifying the factory creation core.
- Dependency Inversion Principle (DIP): Returns the BaseMonitorTransport abstraction.
"""

from typing import Callable, Dict, Optional, Type

from transports.base import BaseMonitorTransport
from transports.endpoint_resolver import EndpointResolver
from transports.http_transport import MonitorHttpTransport
from transports.mqtt_transport import MonitorMqttTransport


class TransportFactory:
    """Factory registry producing BaseMonitorTransport implementations based on endpoint strings."""

    _registry: Dict[str, Type[BaseMonitorTransport]] = {
        "http": MonitorHttpTransport,
        "mqtt": MonitorMqttTransport,
    }

    @classmethod
    def register_transport(cls, scheme: str, transport_cls: Type[BaseMonitorTransport]) -> None:
        """
        Registers a new transport implementation under a scheme name (OCP compliance).
        """
        cls._registry[scheme.lower()] = transport_cls

    @classmethod
    def create_transport(cls, endpoint_str: str, on_connect_cb: Optional[Callable] = None) -> BaseMonitorTransport:
        """
        Instantiates and returns the appropriate BaseMonitorTransport based on endpoint analysis.
        """
        if EndpointResolver.is_http(endpoint_str):
            http_cls = cls._registry.get("http", MonitorHttpTransport)
            return http_cls(endpoint_url=endpoint_str, on_connect_cb=on_connect_cb)

        mqtt_cls = cls._registry.get("mqtt", MonitorMqttTransport)
        return mqtt_cls(host=endpoint_str, on_connect_cb=on_connect_cb)


def create_monitor_transport(endpoint_str: str, on_connect_cb: Optional[Callable] = None) -> BaseMonitorTransport:
    """Convenience top-level factory function."""
    return TransportFactory.create_transport(endpoint_str, on_connect_cb=on_connect_cb)
