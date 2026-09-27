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

# File: src/drivers/go_event_dispatcher.py
# Author: Gabriel Moraes
# Date: 2026-09-25

"""
Routes asynchronous events received from the Go hardware gateway (Traps, Heartbeats).
Isolated responsibility according to the Single Responsibility Principle (SRP).
"""

import logging
import threading
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class GoEventDispatcher:
    """
    Observer dispatcher for unsolicited push events arriving from physical hardware via Go.
    """

    def __init__(self) -> None:
        self._ui_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def register_ui_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Registers a callback for UI updates upon receiving field traps/alarms."""
        if callback not in self._ui_callbacks:
            self._ui_callbacks.append(callback)

    def dispatch(self, event_data: Dict[str, Any]) -> None:
        """Routes asynchronous events received from Go gateway to CARINA systems."""
        event_type = event_data.get("event_type")
        intersection_id = event_data.get("intersection_id", "DESCONHECIDO")

        # A. SNMP Trap received on UDP 162
        if event_type == "trap":
            level = event_data.get("level", "WARNING")
            logger.warning(
                f"[GoEventDispatcher] 🚨 Trap received from {intersection_id}: [{level}] {event_data.get('details')}"
            )

            # Notify UI callbacks synchronously
            for cb in self._ui_callbacks:
                try:
                    cb(event_data)
                except Exception as cb_err:
                    logger.error(f"[GoEventDispatcher] Error in UI trap callback: {cb_err}")

            # Notify IncidentFilter asynchronously for Monitor MQTT
            try:
                from src.drivers.incident_filter import IncidentFilter

                threading.Thread(
                    target=IncidentFilter.process_and_report,
                    args=(intersection_id, level, event_data),
                    daemon=True,
                    name="IncidentFilterGoThread",
                ).start()
            except Exception as inc_err:
                logger.error(f"[GoEventDispatcher] Error reporting trap incident: {inc_err}")

        # B. Heartbeat Lost
        elif event_type == "heartbeat_lost":
            logger.critical(
                f"[GoEventDispatcher] ❌ Connection LOST to intersection {intersection_id} (Heartbeat failed)."
            )
            try:
                from src.drivers.incident_reporter import IncidentReporter

                IncidentReporter.report(
                    intersection_id, "CRITICAL", f"CARINA perdeu conexão com o controlador: {intersection_id}."
                )
            except Exception as e:
                logger.error(f"[GoEventDispatcher] Error reporting heartbeat lost: {e}")

        # C. Heartbeat Restored
        elif event_type == "heartbeat_restored":
            logger.info(f"[GoEventDispatcher] ✅ Connection RESTORED to intersection {intersection_id}.")
            try:
                from src.drivers.incident_reporter import IncidentReporter

                IncidentReporter.report(
                    intersection_id, "INFO", f"CARINA restabeleceu conexão com o controlador: {intersection_id}."
                )
            except Exception as e:
                logger.error(f"[GoEventDispatcher] Error reporting heartbeat restored: {e}")
