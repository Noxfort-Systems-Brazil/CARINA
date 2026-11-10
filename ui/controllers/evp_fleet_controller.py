# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Emergency Vehicle Preemption (EVP) Fleet Controller.
Intermediates UI actions and the EVPService preemption service (DIP).
Supports an in-memory transactional buffer (staging) so changes made in the settings modal
remain in memory until explicitly applying 'Save Changes'.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from src.evp.evp_fleet_manager import EVPFleetManager
from src.evp.evp_models import RegisteredVehicle
from src.evp.evp_service import EVPService

logger = logging.getLogger(__name__)


class EVPFleetController:
    """Controller orchestrating the EVP fleet for the presentation layer with RAM staging support."""

    def __init__(self, evp_service: Optional[EVPService] = None, enable_staging: bool = True):
        self.evp_service = evp_service or EVPService.get_instance()
        self.enable_staging = enable_staging

        self._staged_fleet: Optional[Dict[str, RegisteredVehicle]] = None
        self._staged_removals: Set[str] = set()
        self._has_changes: bool = False

        if self.enable_staging:
            self.reset_staging()

    def reset_staging(self) -> None:
        """Initializes or reverts the in-memory staging buffer with the current persisted fleet state."""
        if hasattr(self.evp_service, "fleet_manager") and self.evp_service.fleet_manager:
            self.evp_service.fleet_manager.load_persisted_fleet()
        self._staged_fleet = {}
        for reg in self.evp_service._registered_fleet.values():
            if not self.evp_service.fleet_manager.is_vehicle_unregistered(reg.vehicle_id):
                self._staged_fleet[reg.vehicle_id] = RegisteredVehicle(
                    vehicle_id=reg.vehicle_id,
                    corporation=reg.corporation,
                    plate=reg.plate,
                    description=reg.description,
                    device_id=reg.device_id,
                    ip_address=reg.ip_address,
                    port=reg.port,
                    protocol=reg.protocol,
                    auth_token=reg.auth_token,
                    is_active=reg.is_active,
                    created_at=reg.created_at,
                )
        self._staged_removals.clear()
        self._has_changes = False

    def _ensure_staging(self) -> None:
        if self._staged_fleet is None:
            self.reset_staging()

    def has_unsaved_changes(self) -> bool:
        """Indicates whether there are pending unsaved changes in the RAM buffer."""
        return self._has_changes

    def save_changes(self) -> bool:
        """Persists all RAM-staged changes to disk/database."""
        if not self.enable_staging or not self._has_changes:
            return True

        self._ensure_staging()
        # 1. Execute deletions to disk/database (idempotent)
        for v_id in list(self._staged_removals):
            self.evp_service.unregister_fleet_vehicle(v_id)

        # 2. Execute insertions/updates to disk/database
        for v in list(self._staged_fleet.values()):
            if v.vehicle_id not in self._staged_removals:
                self.evp_service.register_fleet_vehicle(v)

        self._staged_removals.clear()
        self._has_changes = False
        logger.info("[EVPFleetController] Alterações da frota EVP salvas com sucesso em disco.")
        return True

    def discard_changes(self) -> None:
        """Discards any changes made in the RAM buffer and restores disk state."""
        if not self.enable_staging:
            return
        logger.info("[EVPFleetController] Alterações em RAM descartadas; restaurando estado gravado.")
        self.reset_staging()

    def get_fleet(self) -> List[Dict[str, Any]]:
        """Returns DTO list reflecting the current state (RAM-staged or persisted)."""
        if not self.enable_staging:
            return self.evp_service.get_all_vehicles()

        self._ensure_staging()
        result = []
        seen = set()
        active_vehicles = getattr(self.evp_service, "_vehicles", {})

        for v in active_vehicles.values():
            if (
                v.vehicle_id in self._staged_removals
                or v.vehicle_id not in self._staged_fleet
            ):
                continue
            d = v.to_dict()
            reg = self._staged_fleet.get(v.vehicle_id)
            if reg:
                d["plate"] = reg.plate
                d["description"] = reg.description
                d["ip_address"] = reg.ip_address
                d["port"] = reg.port
                d["protocol"] = reg.protocol
                d["device_id"] = reg.device_id
                d["auth_token"] = reg.auth_token
            result.append(d)
            seen.add(v.vehicle_id)

        for reg in self._staged_fleet.values():
            if (
                reg.vehicle_id not in seen
                and reg.vehicle_id not in self._staged_removals
            ):
                result.append({
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

        return result

    def register_vehicle(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Registers vehicle (in RAM buffer if staging enabled, or directly in service)."""
        v_id = str(data.get("vehicle_id", "")).strip().upper()
        if not v_id:
            return False, "Identificador da viatura é obrigatório."
        try:
            vehicle = RegisteredVehicle.from_dict(data)
            if self.enable_staging:
                self._ensure_staging()
                self._staged_fleet[v_id] = vehicle
                self._staged_removals.discard(v_id)
                if hasattr(self.evp_service, "fleet_manager") and self.evp_service.fleet_manager:
                    self.evp_service.fleet_manager._unregistered_vehicles.discard(v_id)
                self._has_changes = True
                return True, f"Viatura {v_id} cadastrada!"
            else:
                self.evp_service.register_fleet_vehicle(vehicle)
                return True, f"Viatura {v_id} cadastrada com sucesso!"
        except Exception as e:
            logger.error(f"[EVPFleetController] Erro ao cadastrar viatura {v_id}: {e}", exc_info=True)
            return False, f"Falha ao cadastrar viatura: {e}"

    def unregister_vehicle(self, vehicle_id: str) -> bool:
        """
        Permanently removes vehicle from authorized fleet, database, and telemetry service.
        Adds to denied/unauthorized list so concurrent simulator telemetry
        does not recreate or revive it upon discard.
        """
        v_id = str(vehicle_id).strip().upper()
        found = False
        if self._staged_fleet is not None and v_id in self._staged_fleet:
            del self._staged_fleet[v_id]
            found = True
        if v_id in self.evp_service._registered_fleet:
            found = True
        if v_id in getattr(self.evp_service, "_vehicles", {}):
            found = True

        removed_service = self.evp_service.unregister_fleet_vehicle(v_id)
        if removed_service:
            found = True

        if found:
            self._staged_removals.add(v_id)
            self._has_changes = True

        return found

    def import_csv(self, filepath: str) -> Tuple[int, int]:
        """Imports CSV sheet (into RAM buffer if staging enabled, or directly into service)."""
        if not self.enable_staging:
            return self.evp_service.import_fleet_connection_csv(filepath)

        self._ensure_staging()
        imported_vehicles, total_rows = EVPFleetManager.parse_csv_file(filepath)
        for v in imported_vehicles:
            self._staged_fleet[v.vehicle_id] = v
            self._staged_removals.discard(v.vehicle_id)
            if hasattr(self.evp_service, "fleet_manager") and self.evp_service.fleet_manager:
                self.evp_service.fleet_manager._unregistered_vehicles.discard(v.vehicle_id)

        if imported_vehicles:
            self._has_changes = True

        return (len(imported_vehicles), total_rows)

    def export_csv(self, filepath: str) -> bool:
        """Exports CSV template or current vehicle list."""
        return self.evp_service.export_fleet_csv_template(filepath)

