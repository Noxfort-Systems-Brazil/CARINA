# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Domain Models and Entities for the EVP Module.
Implements CorporationType, TelemetryData, and EmergencyVehicle (Aggregate Root).
"""

from dataclasses import dataclass
from enum import Enum
import time
from typing import Any, Dict, Optional


class CorporationType(str, Enum):
    """
    Identifies the emergency vehicle corporation and its visual representation on the UI.
    """
    SAMU = "SAMU"
    BOMBEIRO = "BOMBEIRO"
    BOMBEIROS = "BOMBEIRO"
    POLICIA = "POLICIA"

    @property
    def shape(self) -> str:
        """Geometric shape rendered on the UI Canvas."""
        if self == CorporationType.SAMU:
            return "triangle"
        elif self == CorporationType.BOMBEIRO:
            return "square"
        return "circle"

    @property
    def base_color(self) -> str:
        """Nominal fixed color (patrol / siren off)."""
        if self == CorporationType.SAMU:
            return "#FFFFFF"
        elif self == CorporationType.BOMBEIRO:
            return "#FF8C00"
        return "#1E3A8A"

    @property
    def alert_color(self) -> str:
        """Flashing high-saturation color (siren on / alert mode)."""
        if self == CorporationType.SAMU:
            return "#E53935"
        elif self == CorporationType.BOMBEIRO:
            return "#FF3D00"
        return "#2563EB"

    @property
    def priority_level(self) -> int:
        """Priority level for resolving conflicts (1 = Max/Life-safety, 2 = Police)."""
        if self in (CorporationType.SAMU, CorporationType.BOMBEIRO):
            return 1
        return 2

    @classmethod
    def from_string(cls, value: str) -> "CorporationType":
        val_upper = str(value or "").strip().upper()
        if "SAMU" in val_upper or "AMBULANCIA" in val_upper or "AMB" in val_upper:
            return cls.SAMU
        if "BOMB" in val_upper or "FOGO" in val_upper or "RESCUE" in val_upper:
            return cls.BOMBEIRO
        return cls.POLICIA


@dataclass
class RegisteredVehicle:
    """
    Formal Municipal Emergency Fleet Registration Entity.
    Stores authorized vehicles and their hardware/network connection parameters.
    """
    vehicle_id: str
    corporation: CorporationType
    plate: str = ""
    description: str = ""
    device_id: str = ""
    ip_address: str = ""
    port: int = 8085
    protocol: str = "HTTP"
    auth_token: str = ""
    is_active: bool = True
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "corporation": self.corporation.value,
            "plate": self.plate,
            "description": self.description,
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "port": self.port,
            "protocol": self.protocol,
            "auth_token": self.auth_token,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegisteredVehicle":
        """Constructs a RegisteredVehicle entity from a sanitized dictionary."""
        v_id = str(data.get("vehicle_id", "")).strip().upper()
        corp = CorporationType.from_string(str(data.get("corporation", "SAMU")))
        plate = str(data.get("plate", "")).strip().upper()
        ip = str(data.get("ip_address", "")).strip() or "10.8.0.15"
        try:
            port = int(data.get("port", 8085))
        except (ValueError, TypeError):
            port = 8085
        proto = str(data.get("protocol", "HTTP")).strip().upper() or "HTTP"
        device_id = str(data.get("device_id", "")).strip()
        auth_token = str(data.get("auth_token", "")).strip()
        desc = str(data.get("description", "")).strip() or f"Viatura {v_id}"
        is_active = bool(data.get("is_active", True))
        created_at = float(data.get("created_at") or time.time())

        return cls(
            vehicle_id=v_id,
            corporation=corp,
            plate=plate,
            description=desc,
            device_id=device_id,
            ip_address=ip,
            port=port,
            protocol=proto,
            auth_token=auth_token,
            is_active=is_active,
            created_at=created_at,
        )


@dataclass(frozen=True)
class TelemetryData:
    """
    Unidirectional telemetry snapshot emitted by the vehicle GPS Antenna.
    """
    vehicle_id: str
    corporation: CorporationType
    latitude: float
    longitude: float
    speed_kmh: float = 0.0
    heading_deg: float = 0.0
    siren_active: bool = False
    timestamp: float = 0.0


class EmergencyVehicle:
    """
    Aggregate Root of Emergency Vehicle in the EVP Module.
    Encapsulates dynamic state, recent telemetry, active preemption cycle,
    and connectivity status (ONLINE / OFFLINE).
    """

    def __init__(
        self,
        vehicle_id: str,
        corporation: CorporationType,
        latitude: float,
        longitude: float,
        speed_kmh: float = 0.0,
        heading_deg: float = 0.0,
        siren_active: bool = False,
        offline_timeout_seconds: float = 30.0,
    ):
        self.vehicle_id = vehicle_id
        self.corporation = corporation
        self.latitude = latitude
        self.longitude = longitude
        self.speed_kmh = speed_kmh
        self.heading_deg = heading_deg
        self.siren_active = siren_active
        self.offline_timeout_seconds = offline_timeout_seconds

        self.is_evp_triggered: bool = False
        self.active_intersection_id: Optional[str] = None
        self.active_intersections: set[str] = set()
        self.active_block_id: Optional[str] = None
        self.dwell_start_time: float = 0.0
        self.last_update_time: float = time.time()

    @property
    def is_online(self) -> bool:
        """Determines whether the vehicle is broadcasting (online) or without signal/off."""
        return (time.time() - self.last_update_time) <= self.offline_timeout_seconds

    @property
    def status_label(self) -> str:
        """Human-readable label for telemetry and CCO."""
        return "ONLINE" if self.is_online else "OFFLINE"

    def update_telemetry(
        self,
        latitude: float,
        longitude: float,
        speed_kmh: float = 0.0,
        heading_deg: float = 0.0,
        siren_active: bool = False,
    ) -> None:
        """Updates dynamic GPS antenna position."""
        self.latitude = latitude
        self.longitude = longitude
        self.speed_kmh = speed_kmh
        self.heading_deg = heading_deg
        self.siren_active = siren_active
        self.last_update_time = time.time()

    def activate_evp(self, intersection_id: str, block_id: str) -> None:
        """Activates preemption state for this vehicle at a specific intersection."""
        self.is_evp_triggered = True
        self.active_intersections.add(intersection_id)
        self.active_intersection_id = intersection_id
        self.active_block_id = block_id
        self.dwell_start_time = time.time()

    def deactivate_evp(self, intersection_id: Optional[str] = None) -> None:
        """Deactivates preemption for this vehicle at a specific intersection or for all."""
        if intersection_id:
            self.active_intersections.discard(intersection_id)

        if not intersection_id or not self.active_intersections:
            self.active_intersections.clear()
            self.is_evp_triggered = False
            self.active_intersection_id = None
            self.active_block_id = None
            self.dwell_start_time = 0.0
        else:
            self.active_intersection_id = next(iter(self.active_intersections))

    def to_dict(self) -> Dict[str, Any]:
        """Serialization for UI and persistence."""
        return {
            "vehicle_id": self.vehicle_id,
            "corporation": self.corporation.value,
            "shape": self.corporation.shape,
            "base_color": self.corporation.base_color,
            "alert_color": self.corporation.alert_color,
            "priority": self.corporation.priority_level,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "speed_kmh": self.speed_kmh,
            "heading_deg": self.heading_deg,
            "siren_active": self.siren_active,
            "is_evp_triggered": self.is_evp_triggered,
            "active_intersection_id": self.active_intersection_id,
            "last_update_time": self.last_update_time,
            "is_online": self.is_online,
            "status": self.status_label,
            "last_seen_seconds": max(0.0, round(time.time() - self.last_update_time, 1)),
        }
