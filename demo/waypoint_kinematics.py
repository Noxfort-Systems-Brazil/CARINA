# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Waypoint Kinematics Engine replicating EVP_SIMULATOR vehicle movement.
Snaps emergency fleet vehicles strictly to road network polyline waypoints,
calculates continuous bearings, and synchronizes SUMO metric and WGS84 GPS coordinates.
"""

import math
from typing import Dict, List, Optional, Tuple

DEFAULT_GEO_BOUNDS = {
    "min_lon": -51.240163,
    "min_lat": -23.515986,
    "max_lon": -51.233151,
    "max_lat": -23.507576,
}

DEFAULT_METRIC_BOUNDS = {
    "min_x": 0.0,
    "min_y": 0.0,
    "max_x": 715.96,
    "max_y": 930.36,
}


def sumo_to_geo(x: float, y: float) -> Tuple[float, float]:
    """Converts SUMO local metric (x, y) to WGS84 (latitude, longitude) of Rolândia network."""
    dx = DEFAULT_METRIC_BOUNDS["max_x"] - DEFAULT_METRIC_BOUNDS["min_x"]
    dy = DEFAULT_METRIC_BOUNDS["max_y"] - DEFAULT_METRIC_BOUNDS["min_y"]
    if abs(dx) < 1e-9 or abs(dy) < 1e-9:
        return (DEFAULT_GEO_BOUNDS["min_lat"], DEFAULT_GEO_BOUNDS["min_lon"])

    ratio_x = (x - DEFAULT_METRIC_BOUNDS["min_x"]) / dx
    ratio_y = (y - DEFAULT_METRIC_BOUNDS["min_y"]) / dy

    lon = DEFAULT_GEO_BOUNDS["min_lon"] + ratio_x * (DEFAULT_GEO_BOUNDS["max_lon"] - DEFAULT_GEO_BOUNDS["min_lon"])
    lat = DEFAULT_GEO_BOUNDS["min_lat"] + ratio_y * (DEFAULT_GEO_BOUNDS["max_lat"] - DEFAULT_GEO_BOUNDS["min_lat"])
    return lat, lon


def geo_to_sumo(lat: float, lon: float) -> Tuple[float, float]:
    """Converts WGS84 (latitude, longitude) to SUMO local metric (x, y)."""
    d_lon = DEFAULT_GEO_BOUNDS["max_lon"] - DEFAULT_GEO_BOUNDS["min_lon"]
    d_lat = DEFAULT_GEO_BOUNDS["max_lat"] - DEFAULT_GEO_BOUNDS["min_lat"]
    if abs(d_lon) < 1e-9 or abs(d_lat) < 1e-9:
        return (DEFAULT_METRIC_BOUNDS["min_x"], DEFAULT_METRIC_BOUNDS["min_y"])

    ratio_x = (lon - DEFAULT_GEO_BOUNDS["min_lon"]) / d_lon
    ratio_y = (lat - DEFAULT_GEO_BOUNDS["min_lat"]) / d_lat

    x = DEFAULT_METRIC_BOUNDS["min_x"] + ratio_x * (DEFAULT_METRIC_BOUNDS["max_x"] - DEFAULT_METRIC_BOUNDS["min_x"])
    y = DEFAULT_METRIC_BOUNDS["min_y"] + ratio_y * (DEFAULT_METRIC_BOUNDS["max_y"] - DEFAULT_METRIC_BOUNDS["min_y"])
    return x, y


# Official street polyline waypoints from map_topology.json
SAMU_WAYPOINTS: List[List[float]] = [
    [408.67, 394.07],
    [386.46, 503.3],
    [383.56, 517.4],
    [364.46, 609.53],
    [361.53, 623.63],
    [338.26, 735.81],
    [335.34, 749.91],
    [315.67, 844.69],
    [307.49, 858.58],
    [147.28, 931.82],
]

BOMBEIRO_WAYPOINTS: List[List[float]] = [
    [368.81, 616.17],
    [443.49, 631.87],
    [457.68, 634.86],
    [529.74, 650.06],
    [543.92, 653.04],
    [575.38, 659.6],
]

POLICIA_WAYPOINTS: List[List[float]] = [
    [529.94, 290.36],
    [504.89, 401.01],
    [501.67, 415.22],
    [477.4, 522.33],
    [474.2, 536.48],
    [453.42, 628.21],
    [450.22, 642.35],
    [424.78, 754.71],
]


class WaypointVehicle:
    """
    Simulates a vehicle moving along polyline waypoints matching EVP_SIMULATOR logic.
    """

    def __init__(
        self,
        vehicle_id: str,
        corporation: str,
        waypoints: List[List[float]],
        speed_kmh: float = 60.0,
        is_loop: bool = True,
        siren_active: bool = False,
        target_intersection_id: Optional[str] = None,
        target_intersection_xy: Optional[Tuple[float, float]] = None,
    ):
        self.vehicle_id = vehicle_id
        self.corporation = corporation
        self.waypoints = [list(w) for w in waypoints]
        self.speed_kmh = speed_kmh
        self.is_loop = is_loop
        self.siren_active = siren_active
        self.target_intersection_id = target_intersection_id
        self.target_intersection_xy = target_intersection_xy

        self.seg_idx = 0
        self.direction = 1  # 1 = forward, -1 = reverse (for bouncing routes)
        self.progress_on_seg = 0.0

        if self.waypoints:
            self.x = self.waypoints[0][0]
            self.y = self.waypoints[0][1]
        else:
            self.x, self.y = 0.0, 0.0

        self.heading_deg = 0.0
        self.is_evp_triggered = False
        self.dist_to_intersection = 999.0

        self._update_heading()

    def _update_heading(self):
        if not self.waypoints or len(self.waypoints) < 2:
            return
        next_idx = self.seg_idx + self.direction
        if 0 <= next_idx < len(self.waypoints):
            p1 = self.waypoints[self.seg_idx]
            p2 = self.waypoints[next_idx]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            rad = math.atan2(dx, dy)
            self.heading_deg = round((math.degrees(rad) + 360.0) % 360.0, 1)

    def update(self, dt: float) -> None:
        """Advances vehicle position along the waypoints by traveled distance (speed * dt)."""
        if len(self.waypoints) < 2:
            return

        dist_traveled = (self.speed_kmh / 3.6) * dt
        remaining = dist_traveled

        while remaining > 0:
            next_idx = self.seg_idx + self.direction
            if not (0 <= next_idx < len(self.waypoints)):
                # Boundary reached
                if self.is_loop:
                    self.seg_idx = 0
                    self.direction = 1
                    self.progress_on_seg = 0.0
                    self.x = self.waypoints[0][0]
                    self.y = self.waypoints[0][1]
                    self._update_heading()
                else:
                    self.direction = -self.direction
                    self.progress_on_seg = 0.0
                    self._update_heading()
                break

            p_curr = self.waypoints[self.seg_idx]
            p_next = self.waypoints[next_idx]
            seg_len = math.hypot(p_next[0] - p_curr[0], p_next[1] - p_curr[1])

            if seg_len < 1e-3:
                self.seg_idx = next_idx
                continue

            dist_left_on_seg = seg_len - self.progress_on_seg

            if remaining < dist_left_on_seg:
                self.progress_on_seg += remaining
                frac = self.progress_on_seg / seg_len
                self.x = p_curr[0] + frac * (p_next[0] - p_curr[0])
                self.y = p_curr[1] + frac * (p_next[1] - p_curr[1])
                self._update_heading()
                remaining = 0.0
            else:
                remaining -= dist_left_on_seg
                self.seg_idx = next_idx
                self.progress_on_seg = 0.0
                self.x = p_next[0]
                self.y = p_next[1]
                self._update_heading()

        # Check preemption approach towards target intersection
        if self.target_intersection_xy:
            tx, ty = self.target_intersection_xy
            self.dist_to_intersection = math.hypot(self.x - tx, self.y - ty)
            # Preemption zone between 60m and 160m on approach (prior to crossing)
            is_approaching = (self.y < ty + 10.0) if self.direction > 0 else True
            self.is_evp_triggered = self.siren_active and (self.dist_to_intersection <= 160.0) and is_approaching

    def to_payload(self) -> Dict:
        """Returns standard EVP telemetry dictionary."""
        lat, lon = sumo_to_geo(self.x, self.y)
        return {
            "vehicle_id": self.vehicle_id,
            "corporation": self.corporation,
            "latitude": lat,
            "longitude": lon,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "speed_kmh": round(self.speed_kmh, 1),
            "heading_deg": round(self.heading_deg, 1),
            "siren_active": self.siren_active,
            "is_evp_triggered": self.is_evp_triggered,
            "active_intersection_id": self.target_intersection_id if self.is_evp_triggered else None,
            "distance_to_intersection": round(self.dist_to_intersection, 1) if self.target_intersection_xy else 0.0,
            "is_online": True,
        }
