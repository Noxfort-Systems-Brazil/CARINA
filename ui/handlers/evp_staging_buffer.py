# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
EVP Fleet In-Memory Transactional Buffer Manager (Staging).
Isolates modification tracking, snapshot comparison, and telemetry DTO
transformation logic from the Flet UI, ensuring compliance with SRP and Clean Architecture.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from src.evp.evp_models import RegisteredVehicle

logger = logging.getLogger(__name__)


class EVPStagingBuffer:
    """
    Maintains in-memory transactional state of added, modified, and removed vehicles.
    Detects diffs against database-persisted baseline.
    """

    def __init__(self):
        self._initial_saved_fleet: Dict[str, RegisteredVehicle] = {}
        self._staged_fleet: Dict[str, RegisteredVehicle] = {}
        self._staged_removals: Set[str] = set()

    @property
    def staged_fleet(self) -> Dict[str, RegisteredVehicle]:
        return self._staged_fleet

    @property
    def staged_removals(self) -> Set[str]:
        return self._staged_removals

    def capture_initial_state(self, loaded_fleet: Dict[str, Any]) -> None:
        """Sets the persisted baseline and initializes the in-memory working buffer."""
        self._initial_saved_fleet = {
            k: (v if isinstance(v, RegisteredVehicle) else RegisteredVehicle.from_dict(v.to_dict()))
            for k, v in loaded_fleet.items()
        }
        self._staged_fleet = dict(self._initial_saved_fleet)
        self._staged_removals.clear()

    def stage_vehicle(self, data: Any) -> Tuple[bool, str]:
        """Adds or updates vehicle in the in-memory transactional buffer."""
        if isinstance(data, RegisteredVehicle):
            data = data.to_dict()
        if not isinstance(data, dict):
            return False, "Dados inválidos para cadastro de viatura."
        v_id = str(data.get("vehicle_id", "")).strip().upper()
        if not v_id:
            return False, "Identificador da viatura é obrigatório."
        try:
            vehicle = RegisteredVehicle.from_dict(data)
            self._staged_fleet[v_id] = vehicle
            self._staged_removals.discard(v_id)
            return True, f"Viatura {v_id} cadastrada!"
        except Exception as e:
            logger.error(f"[EVPStagingBuffer] Erro ao cadastrar viatura {v_id}: {e}", exc_info=True)
            return False, f"Falha ao cadastrar viatura: {e}"

    def stage_removal(self, vehicle_id: str) -> bool:
        """Removes vehicle from staging buffer and adds to pending deletion set."""
        v_id = str(vehicle_id).strip().upper()
        found = False
        if v_id in self._staged_fleet:
            del self._staged_fleet[v_id]
            found = True
        self._staged_removals.add(v_id)
        return found

    def has_unsaved_changes(self) -> bool:
        """Compares RAM buffer with initial baseline to determine pending changes."""
        if self._staged_removals:
            return True
        if set(self._staged_fleet.keys()) != set(self._initial_saved_fleet.keys()):
            return True
        for v_id, v in self._staged_fleet.items():
            init_v = self._initial_saved_fleet.get(v_id)
            if not init_v:
                return True
            if (
                v.corporation != init_v.corporation
                or v.plate != init_v.plate
                or v.description != init_v.description
                or v.device_id != init_v.device_id
                or v.ip_address != init_v.ip_address
                or v.port != init_v.port
                or v.protocol != init_v.protocol
                or v.auth_token != init_v.auth_token
                or v.is_active != init_v.is_active
            ):
                return True
        return False

    def discard_changes(self) -> None:
        """Reverts RAM buffer state to saved baseline."""
        self._staged_fleet = {
            k: RegisteredVehicle.from_dict(v.to_dict()) for k, v in self._initial_saved_fleet.items()
        }
        self._staged_removals.clear()

    def commit_changes(self) -> None:
        """Promotes current staged state to baseline after database persistence."""
        self._initial_saved_fleet = {
            k: RegisteredVehicle.from_dict(v.to_dict()) for k, v in self._staged_fleet.items()
        }
        self._staged_removals.clear()

    def build_fleet_dtos(self, active_vehicles: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assembles DTO list for visual rendering merging active telemetry and offline vehicles."""
        fleet_dtos: List[Dict[str, Any]] = []
        seen = set()

        for v in active_vehicles.values():
            if v.vehicle_id in self._staged_removals or v.vehicle_id not in self._staged_fleet:
                continue
            d = v.to_dict()
            reg = self._staged_fleet.get(v.vehicle_id)
            if reg:
                d.update({
                    "plate": reg.plate,
                    "description": reg.description,
                    "ip_address": reg.ip_address,
                    "port": reg.port,
                    "protocol": reg.protocol,
                    "device_id": reg.device_id,
                    "auth_token": reg.auth_token,
                })
            fleet_dtos.append(d)
            seen.add(v.vehicle_id)

        for reg in self._staged_fleet.values():
            if reg.vehicle_id in seen or reg.vehicle_id in self._staged_removals:
                continue
            fleet_dtos.append({
                "vehicle_id": reg.vehicle_id,
                "corporation": reg.corporation.value,
                "shape": reg.corporation.shape,
                "base_color": reg.corporation.base_color,
                "alert_color": reg.corporation.alert_color,
                "priority": reg.corporation.priority_level,
                "latitude": 0.0,
                "longitude": 0.0,
                "speed_kmh": 0.0,
                "heading_deg": 0.0,
                "siren_active": False,
                "is_evp_triggered": False,
                "active_intersection_id": None,
                "last_update_time": 0.0,
                "is_online": False,
                "status": "OFFLINE",
                "last_seen_seconds": -1.0,
                "plate": reg.plate,
                "description": reg.description,
                "ip_address": reg.ip_address,
                "port": reg.port,
                "protocol": reg.protocol,
                "device_id": reg.device_id,
                "auth_token": reg.auth_token,
            })
        return fleet_dtos
