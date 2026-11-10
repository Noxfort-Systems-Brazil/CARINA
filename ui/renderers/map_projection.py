# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Tuple


class MapProjection:
    """
    Handles coordinate normalization, aspect ratio calculations,
    and translation from geographic coordinates to 2D canvas pixels.
    Follows Single Responsibility Principle (SRP).
    """

    def __init__(self, base_width: int, base_height: int):
        self.base_width = base_width
        self.base_height = base_height
        self.fit_scale = 1.0
        self.fit_offset_x = 0.0
        self.fit_offset_y = 0.0

    def calculate_initial_fit(self, topology: dict) -> None:
        """Calculates scale and offsets to center and fit topology bounds into canvas."""
        if not topology:
            return
        try:
            bounds = topology.get("bounds")
            if not bounds:
                return

            min_x, min_y = bounds["min_x"], bounds["min_y"]
            max_x, max_y = bounds["max_x"], bounds["max_y"]

            map_w = max_x - min_x
            map_h = max_y - min_y
            if map_w == 0:
                map_w = 1.0
            if map_h == 0:
                map_h = 1.0

            scale_x = self.base_width / map_w
            scale_y = self.base_height / map_h
            self.fit_scale = min(scale_x, scale_y) * 0.95

            pixel_map_w = map_w * self.fit_scale
            pixel_map_h = map_h * self.fit_scale

            self.fit_offset_x = (self.base_width - pixel_map_w) / 2.0
            self.fit_offset_y = (self.base_height - pixel_map_h) / 2.0
        except Exception as e:
            print(f"[MapProjection] Error calculating fit scale: {e}")

    def map_to_canvas(self, topology: dict, mx: float, my: float) -> Tuple[float, float]:
        """Maps geographic coordinate (mx, my) to canvas pixel coordinates (cx, cy)."""
        try:
            bounds = topology["bounds"]
            rel_x = mx - bounds["min_x"]
            rel_y_flipped = bounds["max_y"] - my
            cx = self.fit_offset_x + (rel_x * self.fit_scale)
            cy = self.fit_offset_y + (rel_y_flipped * self.fit_scale)
            return cx, cy
        except Exception:
            return 0.0, 0.0
