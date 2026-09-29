# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/rendering/static_map_projector.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Any, Callable, Dict, List, Tuple


class StaticMapProjector:
    """
    Computes geographical bounding boxes and projects SUMO coordinates
    onto a normalized 1200x800 canvas coordinate space.
    Follows Single Responsibility Principle (SRP).
    """

    def __init__(self, base_width: float = 1200.0, base_height: float = 800.0):
        self.base_width = base_width
        self.base_height = base_height
        self.fit_scale = 1.0
        self.fit_offset_x = 0.0
        self.fit_offset_y = 0.0
        self.min_x = 0.0
        self.max_x = base_width
        self.min_y = 0.0
        self.max_y = base_height

    def compute_bounds_and_scale(self, nodes: Dict[str, Any], edges: List[Dict[str, Any]]) -> None:
        """Extracts geographical extents from nodes/edges and calculates aspect-preserving scale."""
        all_x = [n["x"] for n in nodes.values() if "x" in n] if nodes else []
        all_y = [n["y"] for n in nodes.values() if "y" in n] if nodes else []

        if edges:
            for edge in edges:
                shape = edge.get("shape")
                if shape:
                    for pt in shape:
                        all_x.append(pt[0])
                        all_y.append(pt[1])

        if all_x and all_y:
            self.min_x, self.max_x = min(all_x), max(all_x)
            self.min_y, self.max_y = min(all_y), max(all_y)

            map_w = self.max_x - self.min_x
            map_h = self.max_y - self.min_y
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
        else:
            self.min_x, self.max_x = 0.0, self.base_width
            self.min_y, self.max_y = 0.0, self.base_height
            self.fit_scale = 1.0
            self.fit_offset_x = 0.0
            self.fit_offset_y = 0.0

    def map_to_canvas(self, mx: float, my: float) -> Tuple[float, float]:
        """Translates and scales a simulation coordinate into a 2D canvas pixel coordinate."""
        rel_x = mx - self.min_x
        rel_y = my - self.min_y
        cx = self.fit_offset_x + (rel_x * self.fit_scale)
        cy = self.fit_offset_y + (rel_y * self.fit_scale)
        return cx, cy
