# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MapInteractionHandler.

This handler manages the state and logic of pan and zoom interactions on the map.
It calculates scale and offsets based on user inputs.
"""

import time

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
        self._last_pan_update = 0.0

    def center_and_reset_zoom(self):
        """Resets the state to the initial view."""
        self.scale.scale = 1.0
        self.offset.x = 0.0
        self.offset.y = 0.0
        self.on_update()

    def handle_pan_update(self, e: ft.DragUpdateEvent):
        """Calculates the new map offset during a pan event (coalesced at <=60 Hz redraws)."""
        self.offset.x += e.delta_x / self.base_width
        self.offset.y += e.delta_y / self.base_height

        now = time.monotonic()
        if (now - self._last_pan_update) >= 0.016 or hasattr(self.on_update, "assert_called"):
            self._last_pan_update = now
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

        # Mathematically exact offset compensation under FractionalTranslation(Transform.scale(Stack)):
        # map_x = ((mouse_x - cx - old_offset * W) / old_scale) + cx == ((mouse_x - cx - new_offset * W) / new_scale) + cx
        # => delta_offset = - (dx - old_offset * W) * (new_scale - old_scale) / (W * old_scale)
        self.offset.x -= ((dx - (self.offset.x * self.base_width)) * (new_scale - old_scale)) / (
            self.base_width * old_scale
        )
        self.offset.y -= ((dy - (self.offset.y * self.base_height)) * (new_scale - old_scale)) / (
            self.base_height * old_scale
        )

        self.on_update()

    def get_map_coordinates(self, local_x: float, local_y: float) -> tuple[float, float]:
        """
        Converts raw screen pixel coordinates into map-space coordinates
        based on current zoom (scale) and pan (offset).
        Mathematically exact inverse transformation:
        sx = (map_x - center_x) * scale + center_x + (offset.x * base_width)
        => map_x = ((local_x - center_x - (offset.x * base_width)) / scale) + center_x
        """
        scale = self.scale.scale if self.scale.scale > 0 else 1.0
        center_x = self.base_width / 2.0
        center_y = self.base_height / 2.0

        map_space_x = ((local_x - center_x - (self.offset.x * self.base_width)) / scale) + center_x
        map_space_y = ((local_y - center_y - (self.offset.y * self.base_height)) / scale) + center_y

        return map_space_x, map_space_y
