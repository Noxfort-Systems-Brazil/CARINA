# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/components/interactive_map.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Any, Callable, Optional

import flet as ft
import flet.canvas as cv

from ui.components.map_hit_detector import MapHitDetector
from ui.handlers.map_interaction_handler import MapInteractionHandler
from ui.loader.map_asset_loader import MapAssetLoader
from ui.renderers.planning_map_renderer import PlanningMapRenderer


class InteractiveMap(ft.Container):
    """
    Interactive Vector Map Orchestrator Component.
    Delegates file reading to MapAssetLoader, rendering to PlanningMapRenderer,
    and collision detection to MapHitDetector (SOLID SRP/DIP compliance).
    """

    def __init__(
        self,
        project_root: str,
        on_node_click: Optional[Callable[[str], None]] = None,
        on_edge_click: Optional[Callable[[str, dict], None]] = None,
        on_topology_loaded: Optional[Callable[[], None]] = None,
    ):
        super().__init__(expand=True)

        self.project_root = project_root
        self.on_node_click = on_node_click
        self.on_edge_click = on_edge_click
        self.on_topology_loaded = on_topology_loaded

        self.topology = None
        self.drawn_nodes_cache = []
        self.drawn_edges_cache = []
        self.recommendations = {}

        self.base_width = 1200
        self.base_height = 800

        self.asset_loader = MapAssetLoader()
        self.renderer = PlanningMapRenderer(self.base_width, self.base_height)
        self.interaction_handler = MapInteractionHandler(
            base_width=self.base_width, base_height=self.base_height, on_update_callback=self.update
        )

        self.selected_node_id = None
        self.selected_edge_id = None
        self.active_filter = "ALL"

        self.canvas_static = cv.Canvas(shapes=[], width=self.base_width, height=self.base_height)
        self.canvas_dynamic = cv.Canvas(shapes=[], width=self.base_width, height=self.base_height)

        self.last_mouse_x = self.base_width / 2
        self.last_mouse_y = self.base_height / 2

        self.map_stack = ft.Stack(
            controls=[self.canvas_static, self.canvas_dynamic],
            width=self.base_width,
            height=self.base_height,
            scale=self.interaction_handler.scale,
            offset=self.interaction_handler.offset,
        )

        def _on_hover(e: ft.HoverEvent):
            self.last_mouse_x = e.local_x
            self.last_mouse_y = e.local_y

        self.gesture_detector = ft.GestureDetector(
            content=self.map_stack,
            on_hover=_on_hover,
            on_pan_update=self.interaction_handler.handle_pan_update,
            on_scroll=lambda e: self.interaction_handler.handle_zoom(
                e, getattr(e, "local_x", self.last_mouse_x), getattr(e, "local_y", self.last_mouse_y)
            ),
            on_double_tap=lambda e: self.interaction_handler.center_and_reset_zoom(),
            on_tap_down=self._handle_tap,
        )

        self.content = self.gesture_detector
        self.bgcolor = "#F7F7F7"
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE
        self.border_radius = 10
        self.did_mount = self._on_mount

    def _on_mount(self) -> None:
        if self.page:
            original_on_resized = self.page.on_resized

            def _handle_resized(e):
                if original_on_resized and callable(original_on_resized):
                    original_on_resized(e)
                if self.topology and self.page:
                    pw, ph = self.page.width, self.page.height
                    if (pw is not None and pw < 300) or (ph is not None and ph < 200):
                        return
                    new_w = max(int(pw - 340), 400)
                    new_h = max(int(ph - 180), 300)
                    if new_w != self.base_width or new_h != self.base_height:
                        self.base_width = new_w
                        self.base_height = new_h
                        self.canvas_static.width = new_w
                        self.canvas_static.height = new_h
                        self.canvas_dynamic.width = new_w
                        self.canvas_dynamic.height = new_h
                        self.renderer.base_width = new_w
                        self.renderer.base_height = new_h
                        self.interaction_handler.base_width = new_w
                        self.interaction_handler.base_height = new_h
                        self.map_stack.width = new_w
                        self.map_stack.height = new_h
                        self.renderer.calculate_initial_fit(self.topology)
                        self._draw()
                        self.interaction_handler.center_and_reset_zoom()
                        self.update()

            self.page.on_resized = _handle_resized

    def load_map(self) -> None:
        """Orchestrates loading of topology JSON and delegates to the external Renderer."""
        map_data = self.asset_loader.load_map_data()
        if map_data:
            nodes, edges, bounds = map_data
            self.topology = {"nodes": nodes, "edges": edges, "bounds": bounds}

            if self.page:
                pw = self.page.width or 1280
                ph = self.page.height or 800
                new_w = max(int(pw - 340), 400)
                new_h = max(int(ph - 180), 300)
                self.base_width = new_w
                self.base_height = new_h
                self.canvas_static.width = new_w
                self.canvas_static.height = new_h
                self.canvas_dynamic.width = new_w
                self.canvas_dynamic.height = new_h
                self.renderer.base_width = new_w
                self.renderer.base_height = new_h
                self.interaction_handler.base_width = new_w
                self.interaction_handler.base_height = new_h
                self.map_stack.width = new_w
                self.map_stack.height = new_h

            self.renderer.calculate_initial_fit(self.topology)
            self._draw()
            self.interaction_handler.center_and_reset_zoom()
            self.update()
            if self.on_topology_loaded:
                try:
                    self.on_topology_loaded()
                except Exception as ex:
                    print(f"[InteractiveMap Orchestrator] Error calling on_topology_loaded: {ex}")

    def set_recommendations(self, recs: dict) -> None:
        self.recommendations = recs
        if self.topology:
            self._draw()
            self.update()

    def set_selected_node(self, node_id: Optional[str]) -> None:
        self.selected_node_id = node_id
        if node_id:
            self.selected_edge_id = None
        if self.topology:
            self._draw()
            if self.page:
                self.update()

    def set_selected_edge(self, edge_id: Optional[str]) -> None:
        self.selected_edge_id = edge_id
        if edge_id:
            self.selected_node_id = None
        if self.topology:
            self._draw()
            if self.page:
                self.update()

    def set_filter(self, filter_key: str) -> None:
        self.active_filter = filter_key
        if self.topology:
            self._draw()
            if self.page:
                self.update()

    def _draw(self) -> None:
        self.renderer.draw_topology(
            topology=self.topology,
            canvas_static=self.canvas_static,
            canvas_dynamic=self.canvas_dynamic,
            drawn_nodes_cache=self.drawn_nodes_cache,
            recommendations=self.recommendations,
            selected_node_id=self.selected_node_id,
            active_filter=self.active_filter,
            drawn_edges_cache=self.drawn_edges_cache,
            selected_edge_id=self.selected_edge_id,
        )

    def _handle_tap(self, e: ft.TapEvent) -> None:
        """Calculates 1:1 hit detection in map space via MapHitDetector."""
        scale = self.interaction_handler.scale.scale if self.interaction_handler.scale.scale > 0 else 1.0
        map_x, map_y = self.interaction_handler.get_map_coordinates(e.local_x, e.local_y)
        node_hit_radius = getattr(self.renderer, "hit_radius", 14.0)

        hit_type, element_id, raw_data = MapHitDetector.detect_hit(
            map_x=map_x,
            map_y=map_y,
            scale=scale,
            drawn_nodes_cache=self.drawn_nodes_cache,
            drawn_edges_cache=self.drawn_edges_cache,
            node_base_hit_radius=node_hit_radius,
        )

        if hit_type == "node":
            self.set_selected_node(element_id)
            if self.on_node_click:
                self.on_node_click(element_id)
        elif hit_type == "edge":
            self.set_selected_edge(element_id)
            if self.on_edge_click:
                self.on_edge_click(element_id, raw_data)
        else:
            self.set_selected_node(None)
            self.set_selected_edge(None)
