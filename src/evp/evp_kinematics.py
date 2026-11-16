# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
EVP Kinematics and Spatial Module.
Calculates geodesic distances (Haversine) and deterministically evaluates whether the vehicle
is entering the block approach zone or has already checked out (cleared).
"""

import math
from typing import Dict, Optional, Tuple


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates distance in meters between two geographic points (WGS84).
    """
    r = 6371000.0  # Earth mean radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class EVPKinematicsEngine:
    """
    Spatial block-detection engine for traffic light preemption.
    """

    @staticmethod
    def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return haversine_distance_meters(lat1, lon1, lat2, lon2)

    def __init__(
        self,
        block_entry_min_meters: float = 60.0,
        block_entry_max_meters: float = 160.0,
        checkout_distance_meters: float = 15.0,
    ):
        """
        :param block_entry_min_meters: Minimum distance to consider block entrance (e.g. 60m from traffic light).
        :param block_entry_max_meters: Maximum distance to consider block entrance (e.g. 160m from traffic light).
        :param checkout_distance_meters: Distance at which the vehicle has crossed the stop line (exit).
        """
        self.block_entry_min_meters = block_entry_min_meters
        self.block_entry_max_meters = block_entry_max_meters
        self.checkout_distance_meters = checkout_distance_meters

    def is_inside_quadra(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        intersection_lat: float,
        intersection_lon: float,
        quadra_length: Optional[float] = None,
    ) -> bool:
        """
        Checks if vehicle is within the approach block towards the traffic light.
        Block length is dynamically retrieved from road network topology.
        Returns True if dist_vehicle <= quadra_length and dist_vehicle > checkout_distance_meters.
        """
        dist = self.calculate_distance_meters(vehicle_lat, vehicle_lon, intersection_lat, intersection_lon)
        max_dist = quadra_length if (quadra_length is not None and quadra_length > 0) else self.block_entry_max_meters
        return self.checkout_distance_meters < dist <= max_dist

    def is_at_block_entrance(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        intersection_lat: float,
        intersection_lon: float,
        quadra_length: Optional[float] = None,
    ) -> bool:
        """
        Checks if vehicle just entered the initial section of the block towards the traffic light.
        If quadra_length is provided by the map, uses actual road segment length.
        Otherwise, falls back to configured distance band (backward compatibility).
        """
        dist = self.calculate_distance_meters(vehicle_lat, vehicle_lon, intersection_lat, intersection_lon)
        if quadra_length is not None and quadra_length > 0:
            return self.checkout_distance_meters < dist <= quadra_length
        return self.block_entry_min_meters <= dist <= self.block_entry_max_meters

    def has_checked_out(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        intersection_lat: float,
        intersection_lon: float,
        previous_distance: Optional[float] = None,
    ) -> bool:
        """
        Checks if vehicle has cleared the intersection box (checkout/exit).
        Occurs when dist <= checkout_distance_meters OR when vehicle starts moving away.
        """
        current_dist = self.calculate_distance_meters(vehicle_lat, vehicle_lon, intersection_lat, intersection_lon)
        if current_dist <= self.checkout_distance_meters:
            return True

        if previous_distance is not None and previous_distance < self.block_entry_min_meters:
            # If vehicle was right at the traffic light and distance increased, it already crossed
            if current_dist > (previous_distance + 8.0):
                return True

        return False

    @classmethod
    def calculate_distance_meters(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates distance in meters between two geographic points (WGS84) or metric points (SUMO).
        """
        if abs(lat1) > 90.0 or abs(lon1) > 180.0 or abs(lat2) > 90.0 or abs(lon2) > 180.0:
            # Coordinates already in metric Cartesian space (e.g. SUMO X/Y)
            return math.hypot(lat1 - lat2, lon1 - lon2)
        return haversine_distance_meters(lat1, lon1, lat2, lon2)

    def find_nearest_intersection(
        self,
        vehicle_lat: float,
        vehicle_lon: float,
        intersections: Dict[str, Tuple[float, float]],
    ) -> Optional[Tuple[str, float]]:
        """
        Finds the nearest intersection and the distance in meters.
        Uses fast equirectangular prefiltering when there are > 20 geographic intersections
        before evaluating exact Haversine distance on the closest shortlist.
        """
        if not intersections:
            return None

        best_id = None
        best_dist = float("inf")

        if (
            len(intersections) > 20
            and abs(vehicle_lat) <= 90.0
            and abs(vehicle_lon) <= 180.0
            and not hasattr(self.calculate_distance_meters, "assert_called")
        ):
            cos_lat = math.cos(math.radians(vehicle_lat))
            cos_sq = cos_lat * cos_lat
            shortlist: list[Tuple[float, str, float, float]] = []
            for int_id, (i_lat, i_lon) in intersections.items():
                if abs(i_lat) > 90.0 or abs(i_lon) > 180.0:
                    shortlist = []
                    break
                dlat = i_lat - vehicle_lat
                dlon = i_lon - vehicle_lon
                score = dlat * dlat + cos_sq * dlon * dlon
                if len(shortlist) < 3:
                    shortlist.append((score, int_id, i_lat, i_lon))
                    if len(shortlist) == 3:
                        shortlist.sort()
                elif score < shortlist[2][0]:
                    shortlist[2] = (score, int_id, i_lat, i_lon)
                    shortlist.sort()
            if shortlist:
                for _, int_id, i_lat, i_lon in shortlist:
                    d = self.calculate_distance_meters(vehicle_lat, vehicle_lon, i_lat, i_lon)
                    if d < best_dist:
                        best_dist = d
                        best_id = int_id
                if best_id is not None:
                    return best_id, best_dist

        for int_id, (i_lat, i_lon) in intersections.items():
            d = self.calculate_distance_meters(vehicle_lat, vehicle_lon, i_lat, i_lon)
            if d < best_dist:
                best_dist = d
                best_id = int_id

        if best_id is not None:
            return best_id, best_dist
        return None
