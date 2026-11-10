# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import math
from typing import Tuple

from src.utils.sumo_geo_bounds_reader import SumoGeoBounds


class BasemapGeoMath:
    """Provides pure mathematical and geodetic coordinate transformations for map tiles and bounds."""

    DEFAULT_PADDING_RATIO = 0.25

    @classmethod
    def compute_padded_bounds(
        cls, bounds: SumoGeoBounds, padding_ratio: float = DEFAULT_PADDING_RATIO
    ) -> Tuple[float, float, float, float, float, float, float, float]:
        """Calculates padded boundaries in both SUMO metric (x, y) and WGS84 (lon, lat)."""
        net_w = abs(bounds.max_x - bounds.min_x)
        net_h = abs(bounds.max_y - bounds.min_y)

        if net_w <= 1e-3 or net_h <= 1e-3:
            net_w = 1000.0
            net_h = 1000.0

        pad_x = net_w * padding_ratio
        pad_y = net_h * padding_ratio

        p_min_x = bounds.min_x - pad_x
        p_max_x = bounds.max_x + pad_x
        p_min_y = bounds.min_y - pad_y
        p_max_y = bounds.max_y + pad_y

        p_min_lon, p_max_lon = bounds.min_lon, bounds.max_lon
        p_min_lat, p_max_lat = bounds.min_lat, bounds.max_lat

        projected = False
        if bounds.proj_parameter:
            try:
                import pyproj

                proj = pyproj.Proj(bounds.proj_parameter)
                ox, oy = bounds.net_offset
                lon_sw, lat_sw = proj(p_min_x - ox, p_min_y - oy, inverse=True)
                lon_ne, lat_ne = proj(p_max_x - ox, p_max_y - oy, inverse=True)

                p_min_lon = min(lon_sw, lon_ne)
                p_max_lon = max(lon_sw, lon_ne)
                p_min_lat = min(lat_sw, lat_ne)
                p_max_lat = max(lat_sw, lat_ne)
                projected = True
            except Exception as proj_err:
                logging.debug(f"[BasemapGeoMath] Projeção pyproj ignorada: {proj_err}")

        if not projected:
            lon_span = abs(bounds.max_lon - bounds.min_lon)
            lat_span = abs(bounds.max_lat - bounds.min_lat)
            pad_lon = lon_span * padding_ratio
            pad_lat = lat_span * padding_ratio
            p_min_lon = bounds.min_lon - pad_lon
            p_max_lon = bounds.max_lon + pad_lon
            p_min_lat = bounds.min_lat - pad_lat
            p_max_lat = bounds.max_lat + pad_lat

        return p_min_x, p_max_x, p_min_y, p_max_y, p_min_lon, p_max_lon, p_min_lat, p_max_lat

    @staticmethod
    def lon_lat_to_tile(lon: float, lat: float, zoom: int) -> Tuple[int, int]:
        """Converts lon/lat in degrees to slippy map tile coordinates (x, y)."""
        n = 2.0**zoom
        x_tile = int((lon + 180.0) / 360.0 * n)
        lat_clamped = max(-85.0511, min(85.0511, lat))
        lat_rad = math.radians(lat_clamped)
        y_tile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x_tile, y_tile

    @staticmethod
    def lon_lat_to_pixel(
        lon: float, lat: float, zoom: int, x_min_tile: int, y_min_tile: int
    ) -> Tuple[float, float]:
        """Converts lon/lat to pixel coordinates relative to the top-left tile in the stitched grid."""
        n = 2.0**zoom
        x_pixel = ((lon + 180.0) / 360.0 * n - x_min_tile) * 256.0
        lat_clamped = max(-85.0511, min(85.0511, lat))
        lat_rad = math.radians(lat_clamped)
        y_pixel = ((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n - y_min_tile) * 256.0
        return x_pixel, y_pixel

    @staticmethod
    def compute_best_zoom(min_lon: float, max_lon: float, target_pixels: int = 1600) -> int:
        """Computes the optimal zoom level to achieve approximately target_pixels width."""
        lon_span = abs(max_lon - min_lon)
        if lon_span <= 1e-6:
            return 16

        raw_zoom = math.log2(target_pixels / ((lon_span / 360.0) * 256.0))
        zoom = round(raw_zoom)
        return max(13, min(17, zoom))
