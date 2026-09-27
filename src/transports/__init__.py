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

# File: src/transports/__init__.py
# Author: Gabriel Moraes
# Date: 2026-09-12 (SOLID Refactoring)

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
