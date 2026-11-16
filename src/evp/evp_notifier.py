# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
EVP Event Notifier for Graphical User Interface (Flet Canvas).
Thread-safe Observer pattern for updating emergency vehicle positions and flashing markers.
"""

import logging
import threading
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EVPNotifier:
    """
    Asynchronous EVP event dispatcher for the user interface.
    """

    _instance = None
    _class_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "EVPNotifier":
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = threading.Lock()

    def register_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Registers a UI callback to receive emergency vehicle updates."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Removes a registered callback."""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def notify(self, vehicle_data: Dict[str, Any]) -> None:
        """Triggers notifications to all registered listeners."""
        with self._lock:
            listeners_copy = list(self._listeners)

        for listener in listeners_copy:
            try:
                listener(vehicle_data)
            except Exception as e:
                logger.error(f"[EVPNotifier] Erro ao notificar ouvinte da UI: {e}", exc_info=True)

        # Forward vehicle telemetry to Go Gateway (CCO Videowall SSE) only from the gateway owner process
        try:
            from src.drivers.go_gateway_client import GoGatewayClient

            if not GoGatewayClient.is_remote_gateway_role():
                gw_client = GoGatewayClient.get_instance()
                if gw_client.is_running():
                    gw_client.broadcast_cco({"type": "evp_telemetry", "vehicle": vehicle_data})
        except Exception as e:
            logger.debug(f"[EVPNotifier] Falha ao duplicar telemetria EVP para GoGateway: {e}")
