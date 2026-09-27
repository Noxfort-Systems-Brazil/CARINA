# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/renderers/planning_map_renderer.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Any, Dict, List, Optional

import flet as ft
import flet.canvas as cv

from ui.renderers.map_projection import MapProjection
from ui.renderers.node_drawer import NodeDrawer
from ui.renderers.street_drawer import StreetDrawer


class PlanningMapRenderer:
    """
    Exclusive specialist responsible for Geometry, Parsing, and Drawing
    of static/dynamic vector maps. Follows Clean Architecture Facade Pattern.
    """

    def __init__(self, base_width: int, base_height: int):
        self.projection = MapProjection(base_width, base_height)
        self.street_drawer = StreetDrawer(street_color=ft.Colors.BLACK, street_width=4.5)
        self.node_drawer = NodeDrawer(
            tl_box_color=ft.Colors.BLUE_800,
            junction_color=ft.Colors.ORANGE_600,
            junction_radius=6.0,
            hit_radius=14.0,
        )

    # Properties forwarded to projection/drawer for backwards compatibility
    @property
    def base_width(self) -> int:
        return self.projection.base_width

    @base_width.setter
    def base_width(self, val: int) -> None:
        self.projection.base_width = val

    @property
    def base_height(self) -> int:
        return self.projection.base_height

    @base_height.setter
    def base_height(self, val: int) -> None:
        self.projection.base_height = val

    @property
    def hit_radius(self) -> float:
        return self.node_drawer.hit_radius

    @property
    def junction_color(self):
        return self.node_drawer.junction_color

    def calculate_initial_fit(self, topology: dict) -> None:
        """Calculates scale and offset to fit topology bounds."""
        self.projection.calculate_initial_fit(topology)

    def map_to_canvas(self, topology: dict, mx: float, my: float) -> tuple[float, float]:
        """Maps geographic coordinate to canvas pixel space."""
        return self.projection.map_to_canvas(topology, mx, my)

    def create_traffic_light_icon(self, sx: float, sy: float, rec_type: str = "existing") -> List[Any]:
        """Creates traffic light icon shapes."""
        return self.node_drawer.create_traffic_light_icon(sx, sy, rec_type)

    def draw_topology(
        self,
        topology: dict,
        canvas_static: cv.Canvas,
        canvas_dynamic: cv.Canvas,
        drawn_nodes_cache: list,
        recommendations: Optional[dict] = None,
        selected_node_id: Optional[str] = None,
        active_filter: str = "ALL",
        drawn_edges_cache: Optional[list] = None,
        selected_edge_id: Optional[str] = None,
    ) -> None:
        """Coordinates clearing and drawing of streets and nodes on static/dynamic canvases."""
        if not topology:
            return

        canvas_static.shapes.clear()
        canvas_dynamic.shapes.clear()
        drawn_nodes_cache.clear()
        if drawn_edges_cache is not None:
            drawn_edges_cache.clear()

        # Build nodes map and node neighbors
        nodes_data = topology.get("nodes", [])
        if isinstance(nodes_data, dict):
            nodes_iter = list(nodes_data.values())
        elif isinstance(nodes_data, list):
            nodes_iter = list(nodes_data)
        else:
            nodes_iter = []

        nodes_map = {n["id"]: n for n in nodes_iter if isinstance(n, dict) and "id" in n and "x" in n and "y" in n}

        edges_data = topology.get("edges", [])
        if isinstance(edges_data, dict):
            edges_items = list(edges_data.items())
        elif isinstance(edges_data, list):
            edges_items = [
                (e.get("id", f"edge_{i}") if isinstance(e, dict) else f"edge_{i}", e) for i, e in enumerate(edges_data)
            ]
        else:
            edges_items = []

        node_neighbors: Dict[str, set] = {}
        for _, edge_item in edges_items:
            if isinstance(edge_item, dict):
                f = edge_item.get("from")
                t = edge_item.get("to")
                if f and t and f != t:
                    if f not in node_neighbors:
                        node_neighbors[f] = set()
                    if t not in node_neighbors:
                        node_neighbors[t] = set()
                    node_neighbors[f].add(t)
                    node_neighbors[t].add(f)

        # 1. Draw Streets
        self.street_drawer.draw_streets(
            topology=topology,
            canvas_static=canvas_static,
            canvas_dynamic=canvas_dynamic,
            map_to_canvas=self.projection.map_to_canvas,
            nodes_map=nodes_map,
            drawn_edges_cache=drawn_edges_cache,
            selected_edge_id=selected_edge_id,
        )

        # 2. Draw Nodes and Traffic Lights
        self.node_drawer.draw_nodes(
            topology=topology,
            canvas_dynamic=canvas_dynamic,
            map_to_canvas=self.projection.map_to_canvas,
            nodes_iter=nodes_iter,
            node_neighbors=node_neighbors,
            drawn_nodes_cache=drawn_nodes_cache,
            recommendations=recommendations,
            selected_node_id=selected_node_id,
            active_filter=active_filter,
        )
