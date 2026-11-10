# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MapEventRouter.

This router handles all incoming user events (clicks, taps, overrides) and
delegates them to the appropriate managers (StateManager, Animator),
resolving the SRP violation in the main widget.
"""

from typing import Callable, Optional

import flet as ft


class MapEventRouter:
    """
    Handles event routing for the map widget.
    It takes raw user interactions and routes them to the appropriate managers
    or external callbacks.
    """

    def __init__(
        self,
        interaction_handler,
        street_interaction_handler,
        safe_update_callback: Callable[[], None],
        on_semaphore_click: Callable[[Optional[str]], None] = None,
        on_street_click: Callable[[Optional[str]], None] = None,
    ):
        self.interaction_handler = interaction_handler
        self.street_interaction_handler = street_interaction_handler
        self.safe_update_callback = safe_update_callback
        self.on_semaphore_click = on_semaphore_click
        self.on_street_click = on_street_click

        self.state_manager = None
        self.animator = None

    def attach_managers(self, state_manager, animator):
        """Attaches the dynamically built managers to the router."""
        self.state_manager = state_manager
        self.animator = animator

    def handle_map_tap(self, e: ft.TapEvent):
        """Converts tap coordinates and routes the click to elements with smart disambiguation."""
        if getattr(e, "local_x", None) is None or getattr(e, "local_y", None) is None:
            return

        map_x, map_y = self.interaction_handler.get_map_coordinates(e.local_x, e.local_y)
        scale = self.interaction_handler.scale.scale if self.interaction_handler.scale.scale > 0 else 1.0

        # 0. Check Emergency Vehicle Hit (highest priority interactive element)
        if getattr(self, "evp_overlay_manager", None) and self.evp_overlay_manager.vehicle_markers:
            for v_id, marker in self.evp_overlay_manager.vehicle_markers.items():
                if not getattr(marker, "visible", True):
                    continue
                m_cx = (getattr(marker, "left", 0.0) or 0.0) + (marker.width / 2.0)
                m_cy = (getattr(marker, "top", 0.0) or 0.0) + (marker.height / 2.0)
                dist_v = ((map_x - m_cx) ** 2 + (map_y - m_cy) ** 2) ** 0.5
                if dist_v <= (24.0 / scale):
                    if self.evp_overlay_manager.on_vehicle_click:
                        v_data = {
                            "vehicle_id": marker.vehicle_id,
                            "corporation": marker.corporation,
                            "latitude": marker.latitude,
                            "longitude": marker.longitude,
                            "speed_kmh": marker.speed_kmh,
                            "heading_deg": marker.heading_deg,
                            "siren_active": marker.siren_active,
                            "is_evp_triggered": marker.is_evp_triggered,
                        }
                        self.evp_overlay_manager.on_vehicle_click(v_data)
                    return

        # 1. Check Traffic Light / Interactive Widget Hit
        hit_tl_id = None
        dist_tl = float("inf")
        box_hit_id = None
        if self.state_manager:
            box_hit_id = self.state_manager.check_widget_hit(map_x, map_y, padding=4.0)
            closest_tl_id, dist_tl_val = self.state_manager.get_closest_widget_distance(map_x, map_y)
            if box_hit_id:
                hit_tl_id = box_hit_id
                dist_tl = 0.0
            elif closest_tl_id and dist_tl_val <= (18.0 / scale):
                hit_tl_id = closest_tl_id
                dist_tl = dist_tl_val

        # 2. Check Street Segment Hit
        closest_edge_id = None
        dist_street = float("inf")
        hit_street = False
        if self.street_interaction_handler:
            closest_edge_id, dist_street = self.street_interaction_handler.find_closest_edge(map_x, map_y)
            dynamic_threshold = self.street_interaction_handler.base_hit_threshold / scale
            hit_street = closest_edge_id is not None and dist_street <= dynamic_threshold

        # 3. Disambiguate when both or either element is hit
        if hit_tl_id and hit_street:
            # If the user clicked inside/on the traffic light box (or padding),
            # the traffic light is the foreground element and takes precedence over streets underneath.
            # Otherwise, whichever element is closer to the tap wins.
            if box_hit_id or dist_tl < dist_street:
                self.handle_interactive_click(hit_tl_id)
            else:
                self.street_interaction_handler.select_edge(closest_edge_id)
        elif hit_tl_id:
            self.handle_interactive_click(hit_tl_id)
        elif hit_street:
            self.street_interaction_handler.select_edge(closest_edge_id)
        else:
            # Tap on empty background clears selections
            if self.state_manager:
                self.state_manager.set_selection(item_type=None, item_id=None)
                self.safe_update_callback()
            if self.on_semaphore_click:
                self.on_semaphore_click(None)
            if self.on_street_click:
                self.on_street_click(None)

    def handle_interactive_click(self, widget_id: str):
        if not self.state_manager:
            return
        current_selection = self.state_manager.selected_interactive_id
        new_selection_id = widget_id if current_selection != widget_id else None

        self.state_manager.set_selection(item_type="interactive", item_id=new_selection_id)
        self.safe_update_callback()

        if self.on_semaphore_click:
            self.on_semaphore_click(new_selection_id)

    def handle_street_click(self, edge_id: Optional[str]):
        if self.state_manager:
            self.state_manager.set_selection(item_type="street", item_id=edge_id)
            self.safe_update_callback()
        if self.on_street_click:
            self.on_street_click(edge_id)

    def set_semaphore_override_state(self, semaphore_id: str, state: str):
        if self.state_manager and self.animator:
            widget = self.state_manager.interactive_widgets.get(semaphore_id)
            if widget:
                command = {"type": "semaphore", "id": semaphore_id, "state": state}
                self.animator.command_queue.put(command)

    def set_street_override_state(self, street_id: str, state: str):
        if self.animator:
            command = {"type": "street", "id": street_id, "state": state}
            self.animator.command_queue.put(command)
