# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Cross-process EVP state snapshot serialization and remote synchronization helper."""

import time
from typing import Any, Dict

from src.evp.evp_models import CorporationType, EmergencyVehicle


class EVPSnapshotSynchronizer:
    """Exports and applies active EVP vehicles and preemption states across processes."""

    @staticmethod
    def export_snapshot(
        vehicles: Dict[str, EmergencyVehicle],
        preemption_engine: Any,
    ) -> Dict[str, Any]:
        """Serializes active EVP vehicles and preemptions for cross-process AI synchronization."""
        serialized_vehicles = {
            vid: v.to_dict() for vid, v in vehicles.items() if v.is_online or v.is_evp_triggered or v.siren_active
        }
        active_preemptions = {tl_id: dict(info) for tl_id, info in preemption_engine._active_preemptions.items()}
        return {"vehicles": serialized_vehicles, "active_preemptions": active_preemptions}

    @staticmethod
    def _upsert_vehicle(
        vid: str,
        v_data: Dict[str, Any],
        vehicles: Dict[str, EmergencyVehicle],
        offline_timeout_seconds: float,
    ) -> None:
        corp = CorporationType.from_string(v_data.get("corporation", "SAMU"))
        veh = vehicles.get(vid)
        if veh is None:
            veh = EmergencyVehicle(
                vehicle_id=str(vid),
                corporation=corp,
                latitude=float(v_data.get("latitude", 0.0)),
                longitude=float(v_data.get("longitude", 0.0)),
                speed_kmh=float(v_data.get("speed_kmh", 0.0)),
                heading_deg=float(v_data.get("heading_deg", 0.0)),
                siren_active=bool(v_data.get("siren_active", False)),
                offline_timeout_seconds=offline_timeout_seconds,
            )
            vehicles[vid] = veh
        else:
            veh.latitude = float(v_data.get("latitude", veh.latitude))
            veh.longitude = float(v_data.get("longitude", veh.longitude))
            veh.speed_kmh = float(v_data.get("speed_kmh", veh.speed_kmh))
            veh.heading_deg = float(v_data.get("heading_deg", veh.heading_deg))
            veh.siren_active = bool(v_data.get("siren_active", veh.siren_active))

        veh.is_evp_triggered = bool(v_data.get("is_evp_triggered", False))
        veh.active_intersection_id = v_data.get("active_intersection_id")
        veh.last_update_time = float(v_data.get("last_update_time", time.time()))

    @classmethod
    def apply_snapshot(
        cls,
        snapshot: Any,
        vehicles: Dict[str, EmergencyVehicle],
        preemption_engine: Any,
        offline_timeout_seconds: float,
    ) -> None:
        """Synchronizes active EVP vehicles and preemptions received from CentralController."""
        if not isinstance(snapshot, dict):
            return

        raw_preemptions = snapshot.get("active_preemptions", {})
        if isinstance(raw_preemptions, dict):
            preemption_engine._active_preemptions.clear()
            for tl_id, info in raw_preemptions.items():
                if isinstance(info, dict):
                    preemption_engine._active_preemptions[str(tl_id)] = dict(info)

        raw_vehicles = snapshot.get("vehicles", {})
        if isinstance(raw_vehicles, dict):
            active_ids = set(raw_vehicles.keys())
            for stale_id in [k for k in list(vehicles.keys()) if k not in active_ids]:
                vehicles.pop(stale_id, None)

            for vid, v_data in raw_vehicles.items():
                if isinstance(v_data, dict):
                    cls._upsert_vehicle(vid, v_data, vehicles, offline_timeout_seconds)
