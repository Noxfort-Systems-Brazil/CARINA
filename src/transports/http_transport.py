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

# File: src/transports/http_transport.py
# Author: Gabriel Moraes
# Date: 2026-09-12 (SOLID Refactoring)

"""
MonitorHttpTransport handles resilient HTTP/HTTPS REST telemetry ingestion.
Adheres to:
- Single Responsibility Principle (SRP): Focuses exclusively on HTTP connection pooling,
  exponential backoff retries, and REST message dispatch.
- Liskov Substitution Principle (LSP): Fully implements BaseMonitorTransport.
"""

import logging
import threading
from typing import Callable, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from transports.base import BaseMonitorTransport, _log_monitor_healthcheck
from transports.endpoint_resolver import EndpointResolver


class MonitorHttpTransport(BaseMonitorTransport):
    """
    Manages resilient HTTP/HTTPS REST communication with connection pooling,
    exponential backoff retries, and telemetry publishing for Monitor integration.
    """

    def __init__(
        self, endpoint_url: str = "http://localhost:8080/api/telemetry", on_connect_cb: Optional[Callable] = None
    ):
        super().__init__(on_connect_cb=on_connect_cb)
        self.endpoint_url = EndpointResolver.normalize_http_url(endpoint_url)
        self._is_connected = False
        self.client = None  # Preserves backwards compatibility with code querying .client

        # Setup resilient requests Session with connection pooling and retry adapter
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=3, connect=3, read=2, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504], raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    @property
    def host(self) -> str:
        try:
            return urlparse(self.endpoint_url).hostname or self.endpoint_url
        except Exception:
            return self.endpoint_url

    @host.setter
    def host(self, value: str):
        self.configure_endpoint(value)

    @property
    def port(self) -> int:
        try:
            parsed = urlparse(self.endpoint_url)
            if parsed.port:
                return parsed.port
            return 443 if parsed.scheme == "https" else 80
        except Exception:
            return 80

    @property
    def endpoint_display(self) -> str:
        return self.endpoint_url

    @property
    def is_connected(self) -> bool:
        return self.enabled and self._is_connected

    def configure_endpoint(self, endpoint_str: str) -> None:
        """Updates and normalizes the target endpoint URL."""
        self.endpoint_url = EndpointResolver.normalize_http_url(endpoint_str)

    def setup(self) -> None:
        """Verifies connectivity to the HTTP Monitor endpoint and triggers on_connect callback."""
        if not self.enabled:
            return

        if self.session is None:
            self.session = self._create_session()

        logging.info(f"[{self.__class__.__name__}] Verifying connection to HTTP Monitor at {self.endpoint_url}")

        payload = '{"origin":"Carina","level":"INFO","message":"heartbeat"}'
        try:
            from communication.monitor_payload import MonitorPayloadBuilder

            payload = MonitorPayloadBuilder.create_payload(category="", level="INFO", message="heartbeat")
        except Exception:
            try:
                from src.communication.monitor_payload import MonitorPayloadBuilder

                payload = MonitorPayloadBuilder.create_payload(category="", level="INFO", message="heartbeat")
            except Exception:
                pass

        success = self.publish(topic="noxfort/telemetry/", payload=payload, timeout=3.0)
        if success:
            self._is_connected = True
            logging.info(f"[{self.__class__.__name__}] Connected successfully to HTTP Monitor at {self.endpoint_url}")
            _log_monitor_healthcheck("HTTP CONNECTED SUCCESS", True, self.enabled, self.host, self.port)
            if self._on_connect_user_cb:
                threading.Thread(target=self._on_connect_user_cb, daemon=True).start()
        else:
            self._is_connected = False
            logging.warning(f"[{self.__class__.__name__}] Could not verify HTTP Monitor at {self.endpoint_url}")
            _log_monitor_healthcheck("HTTP CONNECT FAILED", False, self.enabled, self.host, self.port)

    def ensure_connected(self) -> bool:
        """Verifies active connection or attempts revalidation."""
        if not self.enabled:
            return False
        if self._is_connected:
            return True

        logging.info(f"[{self.__class__.__name__}] Re-verifying HTTP Monitor connection at {self.endpoint_url}...")
        self.setup()
        return self._is_connected

    def publish(self, topic: str, payload: str, qos: int = 1, timeout: float = 5.0) -> bool:
        """Publishes a JSON payload via HTTP POST to /api/telemetry."""
        if not self.enabled:
            return False

        headers = {"Content-Type": "application/json", "User-Agent": "CARINA-Core/1.0", "Accept": "application/json"}

        try:
            t_connect = min(3.0, timeout)
            t_read = timeout
            resp = self.session.post(self.endpoint_url, data=payload, headers=headers, timeout=(t_connect, t_read))
            if resp.status_code in (200, 201, 202, 204):
                self._is_connected = True
                return True
            else:
                logging.error(
                    f"[{self.__class__.__name__}] HTTP POST failed with status {resp.status_code}: {resp.text[:200]}"
                )
                if resp.status_code >= 500:
                    self._is_connected = False
                return False
        except Exception as e:
            self._is_connected = False
            logging.error(f"[{self.__class__.__name__}] Connection error sending to {self.endpoint_url}: {e}")
            return False

    def disconnect(self) -> None:
        """Marks client as disconnected, disables transport and closes underlying session."""
        self.enabled = False
        self._is_connected = False
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass
            self.session = None
