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

# File: src/transports/endpoint_resolver.py
# Author: Gabriel Moraes
# Date: 2026-09-12 (SOLID Refactoring)

"""
Endpoint Resolver: Provides utilities for classifying, parsing, and normalizing network endpoints.
Adheres strictly to the Single Responsibility Principle (SRP):
Encapsulates all URI/URL/host parsing logic away from transport implementations.
"""

from typing import Tuple
from urllib.parse import urlparse, urlunparse


class EndpointResolver:
    """Encapsulates endpoint inspection, protocol inference, and URL normalization."""

    @staticmethod
    def is_http(endpoint: str) -> bool:
        """
        Determines if an endpoint string points to an HTTP/HTTPS REST endpoint
        (e.g., fixed site domain, cloud server, Ngrok tunnel, or IP:port) instead of an MQTT broker.
        """
        if not endpoint:
            return False
        ep = endpoint.strip().lower()

        # Explicit protocols
        if ep.startswith(("http://", "https://")):
            return True
        if ep.startswith(("tcp://", "mqtt://")):
            return False

        # REST endpoints or paths
        if "/api/" in ep or ep.endswith(("/api/telemetry", "/telemetry")):
            return True

        # Known web tunnels
        if any(dom in ep for dom in ["ngrok-free.app", "ngrok-free.dev", "ngrok.app", "ngrok.io"]) and "tcp" not in ep:
            return True

        # Check for known web ports (e.g. host:8080, host:80, host:443, host:8000, host:5000)
        if ":" in ep:
            parts = ep.split(":")
            port_str = parts[-1].split("/")[0]
            if port_str in ("80", "443", "8080", "8000", "5000"):
                return True
            if port_str in ("1883", "8883"):
                return False

        # Check if it has domain structure (e.g. monitor.noxfort.com, monitor.empresa.com.br)
        if "." in ep and not ep.replace(".", "").isdigit():
            return True

        return False

    @staticmethod
    def normalize_http_url(endpoint: str) -> str:
        """
        Normalizes an endpoint string into a complete, resilient HTTP/HTTPS URL targeting /api/telemetry.
        """
        url = endpoint.strip()
        if not url:
            return "http://localhost:8080/api/telemetry"

        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            lower = url.lower()
            if lower.startswith(
                ("localhost", "127.", "192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.3")
            ):
                url = f"http://{url}"
            else:
                url = f"https://{url}"

        parsed = urlparse(url)
        path = parsed.path.rstrip("/")

        # If path is empty or doesn't have an api path, route to /api/telemetry
        if not path or path == "":
            path = "/api/telemetry"
        elif not path.endswith("/api/telemetry") and "/api/" not in path:
            path = f"{path}/api/telemetry"

        normalized = urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))
        return normalized

    @staticmethod
    def parse_mqtt_host_port(host_str: str, default_port: int = 1883) -> Tuple[str, int]:
        """
        Parses host string in format '[scheme://]host[:port][/path]' or returns default port.
        Safely strips schemes (tcp://, mqtt://, http://, https://) and path fragments.
        """
        raw = host_str.strip()
        for prefix in ("tcp://", "mqtt://", "http://", "https://"):
            if raw.lower().startswith(prefix):
                raw = raw[len(prefix) :]
                break

        if "/" in raw:
            raw = raw.split("/", 1)[0]

        if ":" in raw:
            parts = raw.split(":", 1)
            try:
                return parts[0], int(parts[1])
            except ValueError:
                return parts[0], default_port
        return raw, default_port


# Top-level functional aliases for convenience
is_http_endpoint = EndpointResolver.is_http
normalize_http_url = EndpointResolver.normalize_http_url
parse_mqtt_host_port = EndpointResolver.parse_mqtt_host_port
