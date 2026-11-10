# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MapTelemetryManager.

Centralizes thread-safe storage, caching, and querying of map telemetry data
(congestion data, panel data, and street data) for the LiveCanvasMapWidget subsystem.
"""

import threading
from typing import Any, Dict


class MapTelemetryManager:
    """
    Manages telemetry caching and ingestion for the live map.
    Adheres to SRP by handling only data storage and normalization.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._congestion_data: Dict[str, Any] = {}
        self._panel_data: Dict[str, Any] = {}
        self._street_data: Dict[str, Any] = {}

    def update_from_packet(self, data_packet: Dict[str, Any]) -> None:
        """Processes incoming data packets and updates cached state."""
        if not isinstance(data_packet, dict):
            return

        packet_type = data_packet.get("type", "unknown")

        with self._lock:
            if packet_type == "initial_map_geometry":
                congestion = data_packet.get("congestion_update", {})
                if isinstance(congestion, dict) and congestion:
                    self._congestion_data.update(congestion)
            elif packet_type in ["congestion_update", "update_dashboard_data"]:
                payload = data_packet.get("payload", {})
                if isinstance(payload, dict) and payload:
                    self._congestion_data.update(payload)

            if (
                "panel_data" in data_packet
                and isinstance(data_packet["panel_data"], dict)
                and data_packet["panel_data"]
            ):
                self._panel_data.update(data_packet["panel_data"])

            if (
                "street_data" in data_packet
                and isinstance(data_packet["street_data"], dict)
                and data_packet["street_data"]
            ):
                self._street_data.update(data_packet["street_data"])

    def merge_congestion_data(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict):
            with self._lock:
                self._congestion_data.update(data)

    def merge_panel_data(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict):
            with self._lock:
                self._panel_data.update(data)

    def merge_street_data(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict):
            with self._lock:
                self._street_data.update(data)

    def get_congestion_data(self) -> Dict[str, Any]:
        with self._lock:
            return self._congestion_data.copy()

    def get_panel_data(self) -> Dict[str, Any]:
        with self._lock:
            return self._panel_data.copy()

    def get_street_data(self) -> Dict[str, Any]:
        with self._lock:
            return self._street_data.copy()

    def clear(self) -> None:
        with self._lock:
            self._congestion_data.clear()
            self._panel_data.clear()
            self._street_data.clear()
