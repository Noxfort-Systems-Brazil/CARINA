# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/renderers/street_drawer.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Any, Callable, Dict, List, Optional

import flet as ft
import flet.canvas as cv


class StreetDrawer:
    """
    Renders vector street networks, handles topological deduplication,
    and draws dynamic neon selection halos on Flet canvases.
    Follows Single Responsibility Principle (SRP).
    """

    def __init__(self, street_color: str = ft.Colors.BLACK, street_width: float = 4.5):
        self.street_color = street_color
        self.street_width = street_width

    @staticmethod
    def is_edge_selected(edge_id: str, selected_edge_id: Optional[str]) -> bool:
        """Determines if a street edge is currently selected."""
        if not selected_edge_id or not edge_id:
            return False
        e1 = str(edge_id).strip()
        e2 = str(selected_edge_id).strip()
        if e1 == e2:
            return True
        if e1.replace("edge_", "") == e2.replace("edge_", ""):
            return True
        return False

    def draw_streets(
        self,
        topology: dict,
        canvas_static: cv.Canvas,
        canvas_dynamic: cv.Canvas,
        map_to_canvas: Callable[[dict, float, float], tuple],
        nodes_map: Dict[str, dict],
        drawn_edges_cache: Optional[list] = None,
        selected_edge_id: Optional[str] = None,
    ) -> None:
        """Draws all network streets, populating caches and drawing selection halos."""
        edges_data = topology.get("edges", [])
        if isinstance(edges_data, dict):
            edges_items = list(edges_data.items())
        elif isinstance(edges_data, list):
            edges_items = [
                (e.get("id", f"edge_{i}") if isinstance(e, dict) else f"edge_{i}", e) for i, e in enumerate(edges_data)
            ]
        else:
            edges_items = []

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

                # Topological deduplication
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

                if from_n and from_n in nodes_map:
                    fn = nodes_map[from_n]
                    start_x, start_y = map_to_canvas(topology, fn["x"], fn["y"])
                    points.append(cv.Path.MoveTo(start_x, start_y))
                    canvas_pts.append((start_x, start_y))

                for i, coord in enumerate(shape_points):
                    cx, cy = map_to_canvas(topology, coord[0], coord[1])
                    if not points and i == 0:
                        points.append(cv.Path.MoveTo(cx, cy))
                    else:
                        points.append(cv.Path.LineTo(cx, cy))
                    canvas_pts.append((cx, cy))

                if to_n and to_n in nodes_map:
                    tn = nodes_map[to_n]
                    end_x, end_y = map_to_canvas(topology, tn["x"], tn["y"])
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

                if not is_duplicate:
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

                # Glowing neon casing if selected
                if self.is_edge_selected(edge_id, selected_edge_id):
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
                print(f"[StreetDrawer] Error drawing specific edge: {e}")
                continue
