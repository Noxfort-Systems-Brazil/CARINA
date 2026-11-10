# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Emergency Fleet DTO Builder (Clean Architecture / Presentation Adapter).
Transforms domain entities (EmergencyVehicle, RegisteredVehicle) into UI-ready representations.
"""

from typing import Any, Dict, List, Set

from src.evp.evp_models import RegisteredVehicle


class EVPFleetDtoBuilder:
    """Projects active vehicles and fleet records into UI-ready DTO dictionaries."""

    @staticmethod
    def build_vehicle_dtos(
        active_vehicles: Dict[str, Any],
        registered_fleet: Dict[str, RegisteredVehicle],
        unregistered_vehicles: Set[str],
    ) -> List[Dict[str, Any]]:
        """Generates a consolidated list of DTOs for display on map and UI cards."""
        result: List[Dict[str, Any]] = []
        seen: Set[str] = set()

        for v in active_vehicles.values():
            if v.vehicle_id in unregistered_vehicles:
                continue
            d = v.to_dict()
            reg = registered_fleet.get(v.vehicle_id)
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

        for reg in registered_fleet.values():
            if reg.vehicle_id not in seen and reg.vehicle_id not in unregistered_vehicles:
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
