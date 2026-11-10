# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Package transports: Modular, SOLID-compliant communication transports for external Monitor systems.
"""

from transports.base import BaseMonitorTransport, _log_monitor_healthcheck
from transports.endpoint_resolver import EndpointResolver, is_http_endpoint, normalize_http_url, parse_mqtt_host_port
from transports.factory import TransportFactory, create_monitor_transport
from transports.http_transport import MonitorHttpTransport
from transports.mqtt_transport import MonitorMqttTransport

__all__ = [
    "BaseMonitorTransport",
    "MonitorHttpTransport",
    "MonitorMqttTransport",
    "EndpointResolver",
    "TransportFactory",
    "create_monitor_transport",
    "is_http_endpoint",
    "normalize_http_url",
    "parse_mqtt_host_port",
    "_log_monitor_healthcheck",
]
