# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
EVP Telemetry Processor (Application Layer / SOLID: SRP).
Encapsulates real-time telemetry digestion, vehicle state tracking, and lifecycle triggers.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional

from src.evp.evp_models import EmergencyVehicle, RegisteredVehicle, TelemetryData

logger = logging.getLogger(__name__)


class EVPTelemetryProcessor:
    """
    Application Service responsible for processing GPS telemetry packets,
    verifying authorization, maintaining in-memory vehicle entities,
    and delegating preemption evaluations.
    """

    def __init__(
        self,
        offline_timeout_seconds: float = 30.0,
        auto_register_fleet: bool = False,
    ):
        self.offline_timeout_seconds = offline_timeout_seconds
        self.auto_register_fleet = auto_register_fleet

    def ingest_telemetry(
        self,
        telemetry: TelemetryData,
        vehicles: Dict[str, EmergencyVehicle],
        fleet_manager: Any,
    ) -> Optional[EmergencyVehicle]:
        """Validates authorization and updates in-memory vehicle telemetry state."""
        v_id = telemetry.vehicle_id

        if fleet_manager.is_vehicle_unregistered(v_id):
            logger.debug(f"[EVPTelemetryProcessor] Telemetria de {v_id} ignorada (viatura desautorizada/removida).")
            return None

        if v_id not in fleet_manager._fleet:
            if self.auto_register_fleet:
                fleet_manager.register_vehicle(
                    RegisteredVehicle(vehicle_id=v_id, corporation=telemetry.corporation, created_at=time.time())
                )
            else:
                logger.debug(
                    f"[EVPTelemetryProcessor] Telemetria de {v_id} ignorada (viatura não cadastrada na frota)."
                )
                return None

        vehicle = vehicles.get(v_id)
        if vehicle is None:
            vehicle = EmergencyVehicle(
                vehicle_id=v_id,
                corporation=telemetry.corporation,
                latitude=telemetry.latitude,
                longitude=telemetry.longitude,
                speed_kmh=telemetry.speed_kmh,
                heading_deg=telemetry.heading_deg,
                siren_active=telemetry.siren_active,
                offline_timeout_seconds=self.offline_timeout_seconds,
            )
            vehicles[v_id] = vehicle
        else:
            vehicle.update_telemetry(
                telemetry.latitude,
                telemetry.longitude,
                telemetry.speed_kmh,
                telemetry.heading_deg,
                telemetry.siren_active,
            )
        return vehicle

    def process(
        self,
        telemetry: TelemetryData,
        vehicles: Dict[str, EmergencyVehicle],
        fleet_manager: Any,
        topology_service: Any,
        kinematics: Any,
        preemption_engine: Any,
        on_notify_ui: Optional[Callable[[Any], None]] = None,
        on_persist_telemetry: Optional[Callable[[EmergencyVehicle, bool], None]] = None,
    ) -> Optional[EmergencyVehicle]:
        """
        Processes an incoming telemetry frame for an emergency vehicle.
        Returns the updated/created EmergencyVehicle entity or None if ignored.
        """
        vehicle = self.ingest_telemetry(telemetry=telemetry, vehicles=vehicles, fleet_manager=fleet_manager)
        if vehicle is None:
            return None

        evp_triggered = preemption_engine.evaluate_vehicle_lifecycle(
            vehicle=vehicle,
            topology_service=topology_service,
            kinematics=kinematics,
        )

        if on_notify_ui:
            on_notify_ui(vehicle)

        if on_persist_telemetry:
            try:
                on_persist_telemetry(vehicle, evp_triggered)
            except Exception as ex:
                logger.error(f"[EVPTelemetryProcessor] Erro na persistência: {ex}", exc_info=True)

        return vehicle
