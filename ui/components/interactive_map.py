# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: ui/components/interactive_map.py
# Author: Gabriel Moraes
# Date: December 16, 2025

import math

import flet as ft
import flet.canvas as cv

from ui.handlers.map_interaction_handler import MapInteractionHandler
from ui.loader.map_asset_loader import MapAssetLoader
from ui.renderers.planning_map_renderer import PlanningMapRenderer


class InteractiveMap(ft.Container):
    """
    Interactive Vector Map Orchestrator Component.
    Delegates geographic file reading to MapAssetLoader and maps
    matrix rendering to PlanningMapRenderer. (SOLID SRP/DIP compliance).
    """

    def __init__(self, project_root: str, on_node_click=None, on_edge_click=None, on_topology_loaded=None):
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

        # Specialized Core Modules (Composition)
        self.asset_loader = MapAssetLoader()
        self.renderer = PlanningMapRenderer(self.base_width, self.base_height)
        self.interaction_handler = MapInteractionHandler(
            base_width=self.base_width, base_height=self.base_height, on_update_callback=self.update
        )

        self.selected_node_id = None
        self.selected_edge_id = None
        self.active_filter = "ALL"

        self.canvas_static = cv.Canvas(shapes=[], expand=True)
        self.canvas_dynamic = cv.Canvas(shapes=[], expand=True)

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
            on_scroll=lambda e: self.interaction_handler.handle_zoom(e, self.last_mouse_x, self.last_mouse_y),
            on_double_tap=lambda e: self.interaction_handler.center_and_reset_zoom(),
            on_tap_down=self._handle_tap,
        )

        self.content = self.gesture_detector
        self.bgcolor = "#F7F7F7"
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE
        self.border_radius = 10

    def load_map(self):
        """Orchestrates loading of topology JSON and delegates to the external Renderer."""
        map_data = self.asset_loader.load_map_data()

        if map_data:
            nodes, edges, bounds = map_data
            self.topology = {"nodes": nodes, "edges": edges, "bounds": bounds}

            print(f"[InteractiveMap Orchestrator] Topology loaded into memory. Initiating delegation...")
            self.renderer.calculate_initial_fit(self.topology)
            self._draw()

            self.interaction_handler.center_and_reset_zoom()
            self.update()
            if self.on_topology_loaded:
                try:
                    self.on_topology_loaded()
                except Exception as ex:
                    print(f"[InteractiveMap Orchestrator] Error calling on_topology_loaded: {ex}")
        else:
            print(f"[InteractiveMap Orchestrator] Map Asset Loader failed to find topology.")

    def set_recommendations(self, recs: dict):
        """Atualiza as recomendações e re-renderiza o mapa com as novas cores."""
        self.recommendations = recs
        if self.topology:
            self._draw()
            self.update()

    def set_selected_node(self, node_id: str | None):
        """Define o nó selecionado no mapa para desenhar o anel de destaque."""
        self.selected_node_id = node_id
        if node_id:
            self.selected_edge_id = None
        if self.topology:
            self._draw()
            if self.page:
                self.update()

    def set_selected_edge(self, edge_id: str | None):
        """Define a via/rua selecionada no mapa para desenhar o traço luminoso."""
        self.selected_edge_id = edge_id
        if edge_id:
            self.selected_node_id = None
        if self.topology:
            self._draw()
            if self.page:
                self.update()

    def set_filter(self, filter_key: str):
        """Define o filtro ativo para desenhar apenas nós específicos."""
        self.active_filter = filter_key
        if self.topology:
            self._draw()
            if self.page:
                self.update()

    def _draw(self):
        """Requests PlanningMapRenderer to flush pixels onto the Stack Canvas."""
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

    def _handle_tap(self, e: ft.TapEvent):
        """Calculates 1:1 hit detection in map space using get_map_coordinates (identical to Dashboard)."""
        scale = self.interaction_handler.scale.scale if self.interaction_handler.scale.scale > 0 else 1.0

        # 1. Convert screen pixel tap (e.local_x, e.local_y) into true map-space coordinates
        map_x, map_y = self.interaction_handler.get_map_coordinates(e.local_x, e.local_y)

        # 2. Check Node Hits (Junctions / Semaphores) in map coordinates
        clicked_node_id = None
        min_node_dist = float("inf")

        # Hit radius in map space scales inversely with zoom for consistent pixel target size
        node_hit_radius = (self.renderer.hit_radius if hasattr(self.renderer, "hit_radius") else 15.0) / scale

        for node in self.drawn_nodes_cache:
            dx = map_x - node["cx"]
            dy = map_y - node["cy"]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= node_hit_radius and dist < min_node_dist:
                min_node_dist = dist
                clicked_node_id = node["id"]

        if clicked_node_id:
            print(f"[InteractiveMap Orchestrator] Intersection Node Hit detected: {clicked_node_id}")
            self.set_selected_node(clicked_node_id)
            if self.on_node_click:
                self.on_node_click(clicked_node_id)
            return

        # 3. Check Street Segment Hits (Edges) in map coordinates
        def _dist_sq(p1, p2):
            return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2

        def _dist_to_segment_sq(p, v, w):
            l2 = _dist_sq(v, w)
            if l2 == 0:
                return _dist_sq(p, v)
            t = max(0.0, min(1.0, ((p[0] - v[0]) * (w[0] - v[0]) + (p[1] - v[1]) * (w[1] - v[1])) / l2))
            proj = (v[0] + t * (w[0] - v[0]), v[1] + t * (w[1] - v[1]))
            return _dist_sq(p, proj)

        clicked_edge_id = None
        clicked_edge_raw = None
        min_edge_dist_sq = float("inf")
        click_pt = (map_x, map_y)

        # Hit threshold in map space scales inversely with zoom for consistent pixel target size (matching Dashboard)
        edge_hit_threshold_sq = (20.0 / scale) ** 2

        for edge in self.drawn_edges_cache:
            pts = edge.get("points", [])
            for i in range(len(pts) - 1):
                d_sq = _dist_to_segment_sq(click_pt, pts[i], pts[i + 1])
                if d_sq < min_edge_dist_sq:
                    min_edge_dist_sq = d_sq
                    clicked_edge_id = edge["id"]
                    clicked_edge_raw = edge.get("raw", {})

        if clicked_edge_id and min_edge_dist_sq <= edge_hit_threshold_sq:
            print(f"[InteractiveMap Orchestrator] Street Edge Hit detected: {clicked_edge_id}")
            self.set_selected_edge(clicked_edge_id)
            if self.on_edge_click:
                self.on_edge_click(clicked_edge_id, clicked_edge_raw)
            return

        # Tap on empty background clears selections
        self.set_selected_node(None)
        self.set_selected_edge(None)
