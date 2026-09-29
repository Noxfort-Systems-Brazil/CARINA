# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: ui/handlers/map_interaction_handler.py
# Author: Gabriel Moraes
# Date: September 24, 2025

"""
Defines the MapInteractionHandler.

This handler manages the state and logic of pan and zoom interactions on the map.
It calculates scale and offsets based on user inputs.
"""

import flet as ft


class MapInteractionHandler:
    """Manages the state and logic of map pan and zoom interactions."""

    def __init__(self, base_width: float, base_height: float, on_update_callback):
        """
        Initializes the interaction handler.
        """
        self.base_width = base_width
        self.base_height = base_height

        # Classes are called directly from 'ft'
        self.offset = ft.Offset(0, 0)
        self.scale = ft.Scale(scale=1.0, alignment=ft.alignment.center)

        # --- Behavior Settings ---
        self.max_zoom = 3.0
        self.min_zoom = 0.5

        self.on_update = on_update_callback

    def center_and_reset_zoom(self):
        """Resets the state to the initial view."""
        self.scale.scale = 1.0
        self.offset.x = 0.0
        self.offset.y = 0.0
        self.on_update()

    def handle_pan_update(self, e: ft.DragUpdateEvent):
        """Calculates the new map offset during a pan event."""
        effective_scale = self.scale.scale if self.scale.scale > 0 else 1.0

        # Exact vector anchoring maintaining absolute mouse grip under any zoom (1:1 Tracking)
        self.offset.x += e.delta_x / (self.base_width * effective_scale)
        self.offset.y += e.delta_y / (self.base_height * effective_scale)

        self.on_update()

    def handle_zoom(self, e: ft.ScrollEvent, mouse_x: float = None, mouse_y: float = None):
        """Calculates the new map scale and aligns the Vector Offset (Zoom to Pointer)."""
        old_scale = self.scale.scale

        if getattr(e, "local_x", None) is not None:
            mouse_x = e.local_x
        elif mouse_x is None:
            mouse_x = self.base_width / 2.0

        if getattr(e, "local_y", None) is not None:
            mouse_y = e.local_y
        elif mouse_y is None:
            mouse_y = self.base_height / 2.0

        if e.scroll_delta_y < 0:
            new_scale = min(self.max_zoom, old_scale * 1.1)
        else:
            new_scale = max(self.min_zoom, old_scale * 0.9)

        if new_scale == old_scale:
            return

        self.scale.scale = new_scale

        # True Zoom Math (Pointer Anchoring)
        # Exact vector anchoring: preserving the exact map point under the mouse cursor across zoom levels (0 drift)
        center_x = self.base_width / 2.0
        center_y = self.base_height / 2.0

        dx = mouse_x - center_x
        dy = mouse_y - center_y

        # Mathematically exact offset compensation:
        # mx = (mouse_x - cx) / old_scale + cx - old_offset * W == (mouse_x - cx) / new_scale + cx - new_offset * W
        # => delta_offset = - dx * (new_scale - old_scale) / (W * old_scale * new_scale)
        self.offset.x -= (dx * (new_scale - old_scale)) / (self.base_width * old_scale * new_scale)
        self.offset.y -= (dy * (new_scale - old_scale)) / (self.base_height * old_scale * new_scale)

        self.on_update()

    def get_map_coordinates(self, local_x: float, local_y: float) -> tuple[float, float]:
        """
        Converts raw screen pixel coordinates into map-space coordinates
        based on current zoom (scale) and pan (offset).
        Mathematically exact inverse transformation:
        sx = (map_x - center_x) * scale + center_x + (offset.x * base_width * scale)
        => map_x = (local_x - center_x) / scale + center_x - (offset.x * base_width)
        """
        scale = self.scale.scale if self.scale.scale > 0 else 1.0
        center_x = self.base_width / 2.0
        center_y = self.base_height / 2.0

        map_space_x = ((local_x - center_x) / scale) + center_x - (self.offset.x * self.base_width)
        map_space_y = ((local_y - center_y) / scale) + center_y - (self.offset.y * self.base_height)

        return map_space_x, map_space_y
