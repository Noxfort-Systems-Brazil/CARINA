# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any
import flet as ft


class MapGestureBuilder:
    """
    Builder responsible for creating and configuring the map GestureDetector
    with pan, zoom, hover, and tap interactions.
    Adheres to Single Responsibility Principle (SRP).
    """

    def __init__(self, interaction_handler: Any, event_router: Any, initial_x: float = 0.0, initial_y: float = 0.0):
        self.interaction_handler = interaction_handler
        self.event_router = event_router
        self.last_mouse_x = initial_x
        self.last_mouse_y = initial_y

    def build(self, content: ft.Control) -> ft.GestureDetector:
        """Constructs a GestureDetector configured with interaction callbacks."""
        return ft.GestureDetector(
            content=content,
            on_pan_update=self.interaction_handler.handle_pan_update,
            on_scroll=self.interaction_handler.handle_zoom,
            on_double_tap=lambda e: self.interaction_handler.center_and_reset_zoom(),
            on_tap_up=self.event_router.handle_map_tap,
        )

    @staticmethod
    def setup_resize_listener(page: ft.Page, viewport_manager: Any, on_rebuild: Any):
        """Attaches responsive resize listener filtering invalid dimensions."""
        if not page:
            return

        def _check_and_rebuild():
            pw = page.width
            ph = page.height
            if hasattr(page, "window") and page.window is not None:
                win_w = getattr(page.window, "width", None)
                win_h = getattr(page.window, "height", None)
                if isinstance(win_w, (int, float)) and win_w > 0:
                    pw = win_w
                if isinstance(win_h, (int, float)) and win_h > 0:
                    ph = win_h

            if (isinstance(pw, (int, float)) and pw < 300) or (isinstance(ph, (int, float)) and ph < 200):
                return
            old_w, old_h = viewport_manager.width, viewport_manager.height
            new_w, new_h = viewport_manager.calculate_dimensions(pw, ph)
            if new_w != old_w or new_h != old_h:
                on_rebuild()

        original_on_resized = page.on_resized

        def _handle_resized(e):
            if original_on_resized and callable(original_on_resized):
                original_on_resized(e)
            _check_and_rebuild()

        page.on_resized = _handle_resized

        # Also chain window events (maximize, unmaximize, resize, focus) for desktop
        if hasattr(page, "window") and page.window is not None:
            original_window_on_event = page.window.on_event

            def _handle_window_event(e):
                if original_window_on_event and callable(original_window_on_event):
                    original_window_on_event(e)
                _check_and_rebuild()

            page.window.on_event = _handle_window_event
