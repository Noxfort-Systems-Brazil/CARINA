# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
WGS84 <-> SUMO Geodetic Projection Specialist (SRP / Clean Architecture).
Converts latitude/longitude coordinates to the metric Cartesian grid of the SUMO simulator.
"""

import logging
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


class EVPEngineGeoProjector:
    """Performs bidirectional conversions between WGS84 geographic coordinates and SUMO metric coordinates."""

    @staticmethod
    def lat_lon_to_sumo(lat: float, lon: float, bounds: Optional[Any]) -> Tuple[float, float]:
        """Converts WGS84 geographic coordinates (lat, lon) to SUMO local metric coordinates (x, y)."""
        if abs(lat) > 90.0 or abs(lon) > 180.0:
            return float(lon), float(lat)

        if bounds and bounds.has_geo_coords:
            if bounds.proj_parameter:
                try:
                    import pyproj

                    proj = pyproj.Proj(bounds.proj_parameter)
                    utm_x, utm_y = proj(lon, lat)
                    sumo_x = utm_x + bounds.net_offset[0]
                    sumo_y = utm_y + bounds.net_offset[1]
                    return float(sumo_x), float(sumo_y)
                except Exception as ex:
                    logger.debug(f"[EVPEngineGeoProjector] Projeção pyproj lat_lon_to_sumo: {ex}")

            d_lon = bounds.max_lon - bounds.min_lon
            d_lat = bounds.max_lat - bounds.min_lat
            if abs(d_lon) > 1e-9 and abs(d_lat) > 1e-9:
                ratio_x = (lon - bounds.min_lon) / d_lon
                ratio_y = (lat - bounds.min_lat) / d_lat
                sumo_x = bounds.min_x + ratio_x * (bounds.max_x - bounds.min_x)
                sumo_y = bounds.min_y + ratio_y * (bounds.max_y - bounds.min_y)
                return float(sumo_x), float(sumo_y)

        return float(lon), float(lat)

    @staticmethod
    def sumo_to_lat_lon(x: float, y: float, bounds: Optional[Any]) -> Tuple[float, float]:
        """Converts SUMO local metric coordinates (x, y) to WGS84 geographic coordinates (lat, lon)."""
        if bounds and bounds.has_geo_coords:
            if bounds.proj_parameter:
                try:
                    import pyproj

                    proj = pyproj.Proj(bounds.proj_parameter)
                    utm_x = x - bounds.net_offset[0]
                    utm_y = y - bounds.net_offset[1]
                    lon, lat = proj(utm_x, utm_y, inverse=True)
                    return float(lat), float(lon)
                except Exception as ex:
                    logger.debug(f"[EVPEngineGeoProjector] Projeção pyproj sumo_to_lat_lon: {ex}")

            d_x = bounds.max_x - bounds.min_x
            d_y = bounds.max_y - bounds.min_y
            if abs(d_x) > 1e-9 and abs(d_y) > 1e-9:
                ratio_x = (x - bounds.min_x) / d_x
                ratio_y = (y - bounds.min_y) / d_y
                lon = bounds.min_lon + ratio_x * (bounds.max_lon - bounds.min_lon)
                lat = bounds.min_lat + ratio_y * (bounds.max_lat - bounds.min_lat)
                return float(lat), float(lon)

        return float(y), float(x)
