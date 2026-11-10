# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Routes asynchronous events received from the Go hardware gateway (Traps, Heartbeats).
Isolated responsibility according to the Single Responsibility Principle (SRP).
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class GoEventDispatcher:
    """
    Observer dispatcher for unsolicited push events arriving from physical hardware via Go.
    """

    _incident_executor: Optional[ThreadPoolExecutor] = None
    _executor_lock = threading.Lock()

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        with cls._executor_lock:
            if cls._incident_executor is None:
                cls._incident_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="GoIncidentWorker")
            return cls._incident_executor

    def __init__(self) -> None:
        self._ui_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def register_ui_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Registers a callback for UI updates upon receiving field traps/alarms."""
        if callback not in self._ui_callbacks:
            self._ui_callbacks.append(callback)

    def dispatch(self, event_data: Dict[str, Any]) -> None:
        """Routes asynchronous events received from Go gateway to CARINA systems."""
        event_type = event_data.get("event_type") or event_data.get("type")
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
                    logger.error(f"[GoEventDispatcher] Error in UI trap callback: {cb_err}", exc_info=True)

            # Notify IncidentFilter asynchronously for Monitor MQTT via bounded thread pool
            try:
                from src.drivers.incident_filter import IncidentFilter

                self.__class__._get_executor().submit(
                    IncidentFilter.process_and_report, intersection_id, level, event_data
                )
            except Exception as inc_err:
                logger.error(f"[GoEventDispatcher] Error reporting trap incident: {inc_err}", exc_info=True)

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
                logger.error(f"[GoEventDispatcher] Error reporting heartbeat lost: {e}", exc_info=True)

        # C. Heartbeat Restored
        elif event_type == "heartbeat_restored":
            logger.info(f"[GoEventDispatcher] ✅ Connection RESTORED to intersection {intersection_id}.")
            try:
                from src.drivers.incident_reporter import IncidentReporter

                IncidentReporter.report(
                    intersection_id, "INFO", f"CARINA restabeleceu conexão com o controlador: {intersection_id}."
                )
            except Exception as e:
                logger.error(f"[GoEventDispatcher] Error reporting heartbeat restored: {e}", exc_info=True)

        # D. EVP Vehicle GPS Telemetry push event from Go
        elif event_type == "evp_telemetry":
            payload = event_data.get("payload", {})
            try:
                from src.evp.evp_models import CorporationType, TelemetryData
                from src.evp.evp_service import EVPService

                v_id = str(payload.get("vehicle_id", "DESCONHECIDO"))
                corp_str = str(payload.get("corporation", "POLICIA"))
                lat = float(payload.get("latitude", 0.0))
                lon = float(payload.get("longitude", 0.0))
                speed = float(payload.get("speed_kmh", 0.0))
                heading = float(payload.get("heading_deg", 0.0))
                siren = bool(payload.get("siren_active", False))

                telemetry = TelemetryData(
                    vehicle_id=v_id,
                    corporation=CorporationType.from_string(corp_str),
                    latitude=lat,
                    longitude=lon,
                    speed_kmh=speed,
                    heading_deg=heading,
                    siren_active=siren,
                )
                EVPService.get_instance().process_telemetry(telemetry)
                logger.debug(f"[GoEventDispatcher] 🚑 EVP Telemetria recebida do Go para {v_id}")
            except Exception as evp_err:
                logger.error(f"[GoEventDispatcher] Erro ao processar telemetria EVP: {evp_err}", exc_info=True)
