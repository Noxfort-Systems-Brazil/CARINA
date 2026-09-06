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

# File: ui/handlers/planning_map_renderer.py
# Author: Gabriel Moraes
# Date: April 16, 2026

import flet as ft
import flet.canvas as cv


class PlanningMapRenderer:
    """
    Exclusive specialist responsible for Geometry, Parsing, and Drawing
    of static/dynamic vector maps. Extracted from original God Class.
    """

    def __init__(self, base_width: int, base_height: int):
        self.base_width = base_width
        self.base_height = base_height

        self.fit_scale = 1.0
        self.fit_offset_x = 0
        self.fit_offset_y = 0

        # Domain Aesthetics
        self.street_color = ft.Colors.BLACK
        self.street_width = 4.5

        self.tl_box_color = ft.Colors.BLUE_800
        self.tl_light_colors = [ft.Colors.RED, ft.Colors.AMBER, ft.Colors.GREEN]
        self.hit_radius = 35.0

        self.junction_color = ft.Colors.ORANGE_600
        self.junction_radius = 6.0

    def calculate_initial_fit(self, topology: dict):
        if not topology:
            return
        try:
            bounds = topology.get("bounds")
            if not bounds:
                print("[PlanningMapRenderer] Warning: 'bounds' not found in JSON.")
                return

            min_x, min_y = bounds["min_x"], bounds["min_y"]
            max_x, max_y = bounds["max_x"], bounds["max_y"]

            map_w = max_x - min_x
            map_h = max_y - min_y
            if map_w == 0:
                map_w = 1
            if map_h == 0:
                map_h = 1

            scale_x = self.base_width / map_w
            scale_y = self.base_height / map_h
            self.fit_scale = min(scale_x, scale_y) * 0.95

            pixel_map_w = map_w * self.fit_scale
            pixel_map_h = map_h * self.fit_scale

            self.fit_offset_x = (self.base_width - pixel_map_w) / 2
            self.fit_offset_y = (self.base_height - pixel_map_h) / 2
        except Exception as e:
            print(f"[PlanningMapRenderer] Error calculating fit scale: {e}")

    def map_to_canvas(self, topology: dict, mx: float, my: float) -> tuple[float, float]:
        try:
            bounds = topology["bounds"]
            rel_x = mx - bounds["min_x"]
            rel_y_flipped = bounds["max_y"] - my
            cx = self.fit_offset_x + (rel_x * self.fit_scale)
            cy = self.fit_offset_y + (rel_y_flipped * self.fit_scale)
            return cx, cy
        except:
            return 0, 0

    def create_traffic_light_icon(self, sx: float, sy: float, rec_type: str = "existing"):
        shapes = []
        box_w, box_h = 16, 42
        light_radius = 5
        spacing = 11

        if rec_type == "add":
            box_color = ft.Colors.GREEN_700
        elif rec_type == "remove":
            box_color = ft.Colors.RED_700
        else:
            box_color = self.tl_box_color

        shapes.append(
            cv.Rect(
                x=sx - box_w / 2,
                y=sy - box_h / 2,
                width=box_w,
                height=box_h,
                border_radius=4,
                paint=ft.Paint(color=box_color, style=ft.PaintingStyle.FILL),
            )
        )

        y_offsets = [-spacing, 0, spacing]
        for i in range(3):
            shapes.append(
                cv.Circle(
                    x=sx,
                    y=sy + y_offsets[i],
                    radius=light_radius,
                    paint=ft.Paint(color=self.tl_light_colors[i], style=ft.PaintingStyle.FILL),
                )
            )
        return shapes

    def _is_edge_selected(self, edge_id: str, selected_edge_id: str | None) -> bool:
        if not selected_edge_id or not edge_id:
            return False
        e1 = str(edge_id).strip()
        e2 = str(selected_edge_id).strip()
        if e1 == e2:
            return True
        if e1.replace("edge_", "") == e2.replace("edge_", ""):
            return True
        return False

    def _is_node_selected(self, node_id: str, selected_node_id: str | None) -> bool:
        if not selected_node_id or not node_id:
            return False
        n1 = str(node_id).strip()
        n2 = str(selected_node_id).strip()
        if n1 == n2:
            return True
        if n1.replace("tl_", "").replace("node_", "") == n2.replace("tl_", "").replace("node_", ""):
            return True
        return False

    def draw_topology(
        self,
        topology: dict,
        canvas_static: cv.Canvas,
        canvas_dynamic: cv.Canvas,
        drawn_nodes_cache: list,
        recommendations: dict = None,
        selected_node_id: str = None,
        active_filter: str = "ALL",
        drawn_edges_cache: list = None,
        selected_edge_id: str = None,
    ):
        if not topology:
            return
        recommendations = recommendations or {}

        # Clears ONLY Nodes/Semaphores on loop (60 FPS isolation)
        canvas_dynamic.shapes.clear()
        drawn_nodes_cache.clear()
        if drawn_edges_cache is not None:
            drawn_edges_cache.clear()

        draw_streets = len(canvas_static.shapes) == 0

        # Paints Geographic Routes
        edges_data = topology.get("edges", [])
        if isinstance(edges_data, dict):
            edges_items = list(edges_data.items())
        elif isinstance(edges_data, list):
            edges_items = [
                (e.get("id", f"edge_{i}") if isinstance(e, dict) else f"edge_{i}", e) for i, e in enumerate(edges_data)
            ]
        else:
            edges_items = []

        # Nodes dictionary for coordinate and topology snapping
        nodes_data = topology.get("nodes", [])
        if isinstance(nodes_data, dict):
            nodes_iter = list(nodes_data.values())
        elif isinstance(nodes_data, list):
            nodes_iter = list(nodes_data)
        else:
            nodes_iter = []

        nodes_map = {n["id"]: n for n in nodes_iter if isinstance(n, dict) and "id" in n and "x" in n and "y" in n}

        # Count unique neighbor nodes to identify extremity/stub nodes
        node_neighbors = {}
        for edge_id, edge_item in edges_items:
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

        processed_topology = set()
        processed_bases = set()

        for edge_id, edge_item in edges_items:
            if not edge_item:
                continue
            try:
                shape_points = edge_item.get("shape") if isinstance(edge_item, dict) else edge_item
                if not shape_points or len(shape_points) < 2:
                    continue

                from_n = edge_item.get("from") if isinstance(edge_item, dict) else None
                to_n = edge_item.get("to") if isinstance(edge_item, dict) else None

                # Topological deduplication for base static drawing
                is_duplicate = False
                if from_n and to_n:
                    topo_key = tuple(sorted([from_n, to_n]))
                    if topo_key in processed_topology:
                        is_duplicate = True
                    else:
                        processed_topology.add(topo_key)
                else:
                    base_id = str(edge_id)[1:] if str(edge_id).startswith("-") else str(edge_id)
                    if base_id in processed_bases:
                        is_duplicate = True
                    else:
                        processed_bases.add(base_id)

                points = []
                canvas_pts = []

                # Snap to from_node center if available
                if from_n and from_n in nodes_map:
                    fn = nodes_map[from_n]
                    start_x, start_y = self.map_to_canvas(topology, fn["x"], fn["y"])
                    points.append(cv.Path.MoveTo(start_x, start_y))
                    canvas_pts.append((start_x, start_y))

                for i, coord in enumerate(shape_points):
                    cx, cy = self.map_to_canvas(topology, coord[0], coord[1])
                    if not points and i == 0:
                        points.append(cv.Path.MoveTo(cx, cy))
                    else:
                        points.append(cv.Path.LineTo(cx, cy))
                    canvas_pts.append((cx, cy))

                # Snap to to_node center if available
                if to_n and to_n in nodes_map:
                    tn = nodes_map[to_n]
                    end_x, end_y = self.map_to_canvas(topology, tn["x"], tn["y"])
                    points.append(cv.Path.LineTo(end_x, end_y))
                    canvas_pts.append((end_x, end_y))

                if drawn_edges_cache is not None:
                    edge_dict = edge_item if isinstance(edge_item, dict) else {}
                    drawn_edges_cache.append(
                        {
                            "id": str(edge_id),
                            "name": edge_dict.get("name", str(edge_id)),
                            "points": canvas_pts,
                            "raw": edge_dict,
                        }
                    )

                if draw_streets and not is_duplicate:
                    canvas_static.shapes.append(
                        cv.Path(
                            elements=points,
                            paint=ft.Paint(
                                color=self.street_color,
                                stroke_width=self.street_width,
                                stroke_cap=ft.StrokeCap.ROUND,
                                style=ft.PaintingStyle.STROKE,
                            ),
                        )
                    )

                # Draw elegant glowing casing overlay if this street edge is currently selected
                if self._is_edge_selected(edge_id, selected_edge_id):
                    # Layer 1: Dark outer casing border
                    canvas_dynamic.shapes.append(
                        cv.Path(
                            elements=points,
                            paint=ft.Paint(
                                color="#1E242B",
                                stroke_width=9.5,
                                stroke_cap=ft.StrokeCap.ROUND,
                                style=ft.PaintingStyle.STROKE,
                            ),
                        )
                    )
                    # Layer 2: Neon Cyan inner core line
                    canvas_dynamic.shapes.append(
                        cv.Path(
                            elements=points,
                            paint=ft.Paint(
                                color=ft.Colors.CYAN_ACCENT_400,
                                stroke_width=5.5,
                                stroke_cap=ft.StrokeCap.ROUND,
                                style=ft.PaintingStyle.STROKE,
                            ),
                        )
                    )
            except Exception as e:
                print(f"[PlanningMapRenderer] Error drawing specific edge: {e}")
                continue

        # Paints Traffic Lights and Junctions
        for node in nodes_iter:
            try:
                if "x" not in node or "y" not in node:
                    continue

                cx, cy = self.map_to_canvas(topology, node["x"], node["y"])
                node_type = node.get("type", "")
                node_id = node.get("id", "unknown")
                unique_neighbors = len(node_neighbors.get(node_id, set()))

                # Check recommendation first to see if we should upgrade this junction to show an icon
                rec_string = recommendations.get(node_id, {}).get("recommendation", "")
                rec_type = "existing"
                if "adicionar" in rec_string.lower() or "add" in rec_string.lower():
                    rec_type = "add"
                elif "remover" in rec_string.lower() or "remove" in rec_string.lower():
                    rec_type = "remove"

                # Apply visual filter if active
                if active_filter == "ADD" and rec_type != "add":
                    continue
                elif active_filter == "REMOVE" and rec_type != "remove":
                    continue
                elif active_filter == "KEEP" and rec_type != "existing":
                    continue

                is_traffic_light = False
                if node_type is None:
                    is_traffic_light = True
                elif "traffic_light" in str(node_type):
                    is_traffic_light = True

                # Check if this node is currently selected by the user
                if self._is_node_selected(node_id, selected_node_id):
                    canvas_dynamic.shapes.append(
                        cv.Circle(
                            x=cx,
                            y=cy,
                            radius=26,
                            paint=ft.Paint(color=ft.Colors.AMBER_400, stroke_width=3.5, style=ft.PaintingStyle.STROKE),
                        )
                    )

                is_junction = unique_neighbors >= 2 and node_type not in (
                    "dead_end",
                    "internal",
                    "rail_crossing",
                    "rail_signal",
                )
                has_semaphore = is_traffic_light or rec_type == "add"

                if has_semaphore or is_junction:
                    drawn_nodes_cache.append({"id": node_id, "cx": cx, "cy": cy})
                    # Always draw the orange junction node
                    canvas_dynamic.shapes.append(
                        cv.Circle(
                            x=cx,
                            y=cy,
                            radius=self.junction_radius,
                            paint=ft.Paint(color=self.junction_color, style=ft.PaintingStyle.FILL),
                        )
                    )
                    # If this junction has a traffic light (or recommended addition), also draw the traffic light icon centered on top of the node
                    if has_semaphore:
                        icon_shapes = self.create_traffic_light_icon(cx, cy, rec_type)
                        canvas_dynamic.shapes.extend(icon_shapes)
            except Exception as e:
                print(f"[PlanningMapRenderer] Error drawing specific node: {e}")
                continue
