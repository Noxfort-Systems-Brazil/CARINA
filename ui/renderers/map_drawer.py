# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MapDrawer class.

This specialist is responsible for parsing raw map geometry and transforming
it into drawable Flet Canvas shapes.
"""

from typing import Any, Dict, List, Optional

import flet as ft
import flet.canvas as cv

from ui.renderers.heatmap_color_resolver import HeatmapColorResolver


class MapDrawer:
    """
    An expert in transforming map geometry data into drawable shapes
    on the Flet Canvas.
    """

    def __init__(self, nodes: Dict, edges: List):
        """
        Initializes the Drawer with raw map data.

        Args:
            nodes (Dict): Dictionary with nodes (intersections) and their coordinates.
            edges (List): List of edges (streets) and their shapes.
        """
        self.nodes = nodes
        self.edges = edges

        # Attributes that will be calculated by the transformation
        self.scale = 1.0
        self.canvas_center_x = 0
        self.canvas_center_y = 0
        self.sumo_center_x = 0
        self.sumo_center_y = 0

    def calculate_transformations(self, view_width: int, view_height: int, fit_factor: float = 0.95):
        """
        Calculates all required values (scale, centers) for coordinate transformation.
        This method must be called before drawing.
        """
        all_x = [n["x"] for n in self.nodes.values()] + [p[0] for e in self.edges for p in e["shape"]]
        all_y = [n["y"] for n in self.nodes.values()] + [p[1] for e in self.edges for p in e["shape"]]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        map_width = max_x - min_x
        map_height = max_y - min_y

        base_scale = min(view_width / map_width, view_height / map_height) if map_width > 0 and map_height > 0 else 1
        self.scale = base_scale * fit_factor

        self.canvas_center_x = view_width / 2
        self.canvas_center_y = view_height / 2
        self.sumo_center_x = min_x + (map_width / 2)
        self.sumo_center_y = min_y + (map_height / 2)

    def transform_point(self, sumo_x: float, sumo_y: float) -> tuple[float, float]:
        """
        Applies the "Render from Center" transformation to a single point.
        """
        relative_x = sumo_x - self.sumo_center_x
        relative_y = sumo_y - self.sumo_center_y

        canvas_x = self.canvas_center_x + (relative_x * self.scale)
        canvas_y = self.canvas_center_y - (relative_y * self.scale)

        return canvas_x, canvas_y

    def _is_intersection_node(
        self,
        node_id: Optional[str],
        node_neighbors: Dict[str, set],
        incoming_edges: Dict[str, list],
        outgoing_edges: Dict[str, list],
        is_origin: bool = False,
        is_destination: bool = False,
    ) -> bool:
        """
        Determines whether a node is an actual intersection where
        connecting streets should converge to the center point.
        Dead ends (extremities, single-neighbor nodes, and dead_end types) are excluded.
        """
        if not node_id or node_id not in self.nodes:
            return False
        node_data = self.nodes[node_id]
        n_type = node_data.get("type")
        if n_type in ("dead_end", "internal", "rail_crossing", "rail_signal"):
            return False
        unique_neighbors = len(node_neighbors.get(node_id, set()))
        if unique_neighbors <= 1:
            return False
        if is_origin and len(incoming_edges.get(node_id, [])) == 0:
            return False
        if is_destination and len(outgoing_edges.get(node_id, [])) == 0:
            return False
        return True

    def draw_initial_map(
        self, canvas: cv.Canvas, stroke_width: float = 5.0, initial_congestion: Optional[Dict[str, Any]] = None
    ) -> Dict[str, cv.Path]:
        """
        Draws the base map shapes (streets and nodes) onto the provided Canvas object.

        Args:
            canvas (cv.Canvas): The Flet Canvas object where the map will be drawn.
            stroke_width (float): The thickness of the streets to be drawn.
            initial_congestion (Dict[str, Any], optional): Cached congestion values to color streets immediately.

        Returns:
            Dict[str, cv.Path]: A dictionary mapping street ID to the created Path object.
        """
        edge_paths = {}
        processed_bases = {}
        processed_topology = {}

        # Count unique neighbor nodes and incoming/outgoing edges to identify dead ends and intersections
        node_neighbors: Dict[str, set] = {}
        incoming_edges: Dict[str, list] = {}
        outgoing_edges: Dict[str, list] = {}
        for edge in self.edges:
            f = edge.get("from")
            t = edge.get("to")
            if f and t and f != t:
                if f not in node_neighbors:
                    node_neighbors[f] = set()
                if t not in node_neighbors:
                    node_neighbors[t] = set()
                node_neighbors[f].add(t)
                node_neighbors[t].add(f)
                outgoing_edges.setdefault(f, []).append(edge)
                incoming_edges.setdefault(t, []).append(edge)

        # First, draw the streets
        for edge in self.edges:
            edge_id = edge.get("id")
            if not edge_id:
                continue

            from_n = edge.get("from")
            to_n = edge.get("to")

            # Topological deduplication: if two edges connect the same nodes, draw only one shape
            if from_n and to_n:
                topo_key = tuple(sorted([from_n, to_n]))
                if topo_key in processed_topology:
                    edge_paths[edge_id] = processed_topology[topo_key]
                    continue
            else:
                # Fallback to string-based base_id deduplication if topology is missing
                base_id = edge_id[1:] if edge_id.startswith("-") else edge_id
                if base_id in processed_bases:
                    edge_paths[edge_id] = processed_bases[base_id]
                    continue

            path_points = []

            # Extend to from_node center ONLY if it is an intersection (not a dead end / extremity)
            if self._is_intersection_node(from_n, node_neighbors, incoming_edges, outgoing_edges, is_origin=True):
                fn = self.nodes[from_n]
                tx, ty = self.transform_point(fn["x"], fn["y"])
                path_points.append(cv.Path.MoveTo(tx, ty))

            for i, point in enumerate(edge["shape"]):
                tx, ty = self.transform_point(point[0], point[1])
                if not path_points and i == 0:
                    path_points.append(cv.Path.MoveTo(tx, ty))
                else:
                    path_points.append(cv.Path.LineTo(tx, ty))

            # Extend to to_node center ONLY if it is an intersection (not a dead end / extremity)
            if self._is_intersection_node(to_n, node_neighbors, incoming_edges, outgoing_edges, is_destination=True):
                tn = self.nodes[to_n]
                tx, ty = self.transform_point(tn["x"], tn["y"])
                path_points.append(cv.Path.LineTo(tx, ty))

            # Draw an elegant outline/underlay path to create a road-casing effect
            outline_path = cv.Path(
                path_points,
                paint=ft.Paint(
                    stroke_width=stroke_width + 4.0,
                    color="#CC1E1E24",  # Elegant dark charcoal grey with opacity
                    style=ft.PaintingStyle.STROKE,
                    stroke_cap=ft.StrokeCap.ROUND,
                ),
            )
            canvas.shapes.append(outline_path)

            initial_color = "#2ecc71"  # Default Emerald Green
            if initial_congestion:
                val = None
                base_id = edge_id[1:] if edge_id.startswith("-") else edge_id
                rev_id = "-" + base_id if not edge_id.startswith("-") else base_id
                if edge_id in initial_congestion:
                    val = initial_congestion[edge_id]
                elif base_id in initial_congestion:
                    val = initial_congestion[base_id]
                elif rev_id in initial_congestion:
                    val = initial_congestion[rev_id]

                if val is not None:
                    if isinstance(val, dict):
                        val = val.get("congestion", 0.0)
                    try:
                        initial_color = HeatmapColorResolver.get_color_for_congestion(float(val))
                    except Exception:
                        initial_color = "#2ecc71"

            path_object = cv.Path(
                path_points,
                paint=ft.Paint(
                    stroke_width=stroke_width,
                    color=initial_color,
                    style=ft.PaintingStyle.STROKE,
                    stroke_cap=ft.StrokeCap.ROUND,
                ),
            )
            canvas.shapes.append(path_object)

            # Store references
            if from_n and to_n:
                topo_key = tuple(sorted([from_n, to_n]))
                processed_topology[topo_key] = path_object
            else:
                base_id = edge_id[1:] if edge_id.startswith("-") else edge_id
                processed_bases[base_id] = path_object

            edge_paths[edge_id] = path_object

        # Draw the nodes (intersections) above the streets - only for genuine priority intersections
        for node_id, node_data in self.nodes.items():
            n_type = node_data.get("type")
            if (
                n_type != "traffic_light"
                and self._is_intersection_node(node_id, node_neighbors, incoming_edges, outgoing_edges)
                and len(incoming_edges.get(node_id, [])) > 0
                and len(outgoing_edges.get(node_id, [])) > 0
            ):
                tx, ty = self.transform_point(node_data["x"], node_data["y"])

                # Outer circle for a clean white border
                node_border = cv.Circle(x=tx, y=ty, radius=6.5, paint=ft.Paint(color="#FFFFFF"))
                canvas.shapes.append(node_border)

                # Inner circle for the node core
                node_circle = cv.Circle(
                    x=tx, y=ty, radius=4.5, paint=ft.Paint(color="#2C3E50")  # Premium Slate/Charcoal color
                )
                canvas.shapes.append(node_circle)

        return edge_paths
