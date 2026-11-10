# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Backwards-compatibility facade for the transports subsystem.
All concrete transports, interfaces, and utilities are housed in `src/transports/`.
"""

try:
    from transports import (
        BaseMonitorTransport,
        EndpointResolver,
        MonitorHttpTransport,
        MonitorMqttTransport,
        TransportFactory,
        _log_monitor_healthcheck,
        create_monitor_transport,
        is_http_endpoint,
        normalize_http_url,
        parse_mqtt_host_port,
    )
except ImportError:
    from transports import (
        BaseMonitorTransport,
        EndpointResolver,
        MonitorHttpTransport,
        MonitorMqttTransport,
        TransportFactory,
        _log_monitor_healthcheck,
        create_monitor_transport,
        is_http_endpoint,
        normalize_http_url,
        parse_mqtt_host_port,
    )

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
