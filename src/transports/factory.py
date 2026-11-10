# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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
