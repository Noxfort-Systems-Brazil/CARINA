# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Specialist Traffic Light Preemption Decision Engine and State Machine (EVP).
Manages traffic light stage switching, regulatory CONTRAN watchdog timers,
and fail-safe disconnects for offline vehicles (SOLID / SRP).
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

from src.evp.evp_models import EmergencyVehicle

logger = logging.getLogger(__name__)

ACTION_ADVANCE = 0
ACTION_HOLD = 1


class EVPPreemptionEngine:
    """
    Specialist engine for traffic light preemption calculation, timing, and transitions.
    """

    ACTION_ADVANCE = ACTION_ADVANCE
    ACTION_HOLD = ACTION_HOLD

    def __init__(
        self,
        max_dwell_timeout_seconds: float = 45.0,
        on_action_dispatch: Optional[Callable[[str, int, str], None]] = None,
    ):
        self.max_dwell_timeout_seconds = max_dwell_timeout_seconds
        self.on_action_dispatch = on_action_dispatch
        self._active_preemptions: Dict[str, Dict] = {}
        self._lock = threading.RLock()

    def is_preemption_active(self, intersection_id: str) -> bool:
        with self._lock:
            return intersection_id in self._active_preemptions

    def activate_preemption(self, intersection_id: str, vehicle: EmergencyVehicle, target_stage: int = 1) -> None:
        with self._lock:
            vehicle.activate_evp(intersection_id, block_id=f"BLOCK_{intersection_id}")
            self._active_preemptions[intersection_id] = {
                "vehicle_id": vehicle.vehicle_id,
                "corporation": vehicle.corporation,
                "target_stage": target_stage,
                "start_time": time.time(),
            }
            if self.on_action_dispatch:
                self.on_action_dispatch(intersection_id, target_stage, "ACTIVATE_PREEMPT")

    def release_preemption(
        self,
        intersection_id: str,
        vehicle_id: Optional[str] = None,
        vehicle: Optional[EmergencyVehicle] = None,
    ) -> None:
        with self._lock:
            if vehicle:
                vehicle.deactivate_evp(intersection_id)
            self._active_preemptions.pop(intersection_id, None)
            if self.on_action_dispatch:
                self.on_action_dispatch(intersection_id, 0, "RELEASE_PREEMPT")

    def get_preemption_action(
        self,
        intersection_id: str,
        current_stage: int,
        stage_duration: float = 0.0,
        stage_duration_seconds: Optional[float] = None,
        vehicles: Optional[Dict[str, EmergencyVehicle]] = None,
    ) -> Tuple[int, str]:
        if stage_duration_seconds is not None:
            stage_duration = stage_duration_seconds
        with self._lock:
            preempt = self._active_preemptions.get(intersection_id)
            if not preempt:
                return self.ACTION_HOLD, "NOMINAL"

            target_stage = preempt.get("target_stage", 1)
            elapsed = time.time() - preempt.get("start_time", time.time())
            v_id = preempt.get("vehicle_id", "")
            vehicle = vehicles.get(v_id) if vehicles else None

            if vehicle and not vehicle.is_online:
                logger.warning(f"[EVPPreemptionEngine] 📴 {v_id} OFFLINE em {intersection_id}. Desarmando preempção.")
                self.release_preemption(intersection_id, vehicle_id=v_id, vehicle=vehicle)
                return self.ACTION_ADVANCE, "EVP_VEHICLE_OFFLINE_FAILSAFE"

            if vehicle and not vehicle.siren_active:
                logger.info(f"[EVPPreemptionEngine] 🔕 {v_id} sem sirene (Modo Alerta desligado) em {intersection_id}. Desarmando preempção.")
                self.release_preemption(intersection_id, vehicle_id=v_id, vehicle=vehicle)
                return self.ACTION_ADVANCE, "EVP_SIREN_INACTIVE_RELEASE"

            # Unconditional CONTRAN Watchdog fail-safe (maximum preemption dwell exceeded)
            if elapsed >= self.max_dwell_timeout_seconds:
                logger.warning(f"[EVPPreemptionEngine] Watchdog estourado ({elapsed:.1f}s) em {intersection_id}. Liberando.")
                self.release_preemption(intersection_id, vehicle_id=v_id, vehicle=vehicle)
                return self.ACTION_ADVANCE, "EVP_WATCHDOG_TIMEOUT_EXCEEDED"

            if current_stage == target_stage:
                return self.ACTION_HOLD, "EVP_CORREDOR_VERDE_HOLD"

            return self.ACTION_ADVANCE, "EVP_TRANSICAO_PARA_ALVO"

    def evaluate_vehicle_lifecycle(
        self,
        vehicle: EmergencyVehicle,
        topology_service: Any,
        kinematics: Any,
    ) -> bool:
        """Spatially evaluates vehicle and triggers/releases preemption upon block entrance or checkout."""
        with self._lock:
            if not vehicle.siren_active:
                intersections_to_release = [
                    int_id for int_id, p_info in self._active_preemptions.items()
                    if p_info.get("vehicle_id") == vehicle.vehicle_id
                ]
                for int_id in intersections_to_release:
                    logger.info(f"[EVPPreemptionEngine] 🔕 Sirene desligada por {vehicle.vehicle_id} em {int_id}. Desarmando.")
                    self.release_preemption(int_id, vehicle_id=vehicle.vehicle_id, vehicle=vehicle)
                vehicle.deactivate_evp()
                return False

            intersections = topology_service.intersections_geo
            if not intersections:
                topology_service.auto_load_map()
                intersections = topology_service.intersections_geo

            nearest = kinematics.find_nearest_intersection(vehicle.latitude, vehicle.longitude, intersections)
            if not nearest:
                return False

            int_id, _ = nearest
            i_lat, i_lon = intersections[int_id]

            active_intersections = getattr(vehicle, "active_intersections", set())
            if vehicle.is_evp_triggered and (int_id in active_intersections or vehicle.active_intersection_id == int_id):
                if kinematics.has_checked_out(vehicle.latitude, vehicle.longitude, i_lat, i_lon):
                    logger.info(f"[EVPPreemptionEngine] 🏁 Veículo {vehicle.vehicle_id} transpôs {int_id}. Checkout.")
                    self.release_preemption(int_id, vehicle_id=vehicle.vehicle_id, vehicle=vehicle)
                    return vehicle.is_evp_triggered
                return True

            quadra_length = topology_service.get_quadra_length(int_id)
            if kinematics.is_at_block_entrance(vehicle.latitude, vehicle.longitude, i_lat, i_lon, quadra_length=quadra_length):
                if int_id not in self._active_preemptions:
                    target_stage = topology_service.get_target_stage(int_id, default=1)
                    q_desc = f" ({quadra_length:.0f}m)" if quadra_length else ""
                    logger.info(f"[EVPPreemptionEngine] 🚨 {vehicle.vehicle_id} entrou na quadra de {int_id}{q_desc}!")
                    self.activate_preemption(int_id, vehicle, target_stage=target_stage)
                    return True

            return vehicle.is_evp_triggered
