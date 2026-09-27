# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/renderers/node_drawer.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Any, Callable, Dict, List, Optional

import flet as ft
import flet.canvas as cv


class NodeDrawer:
    """
    Renders junctions, traffic light glyphs with color-coded recommendations,
    and amber selection rings on Flet canvases.
    Follows Single Responsibility Principle (SRP).
    """

    def __init__(
        self,
        tl_box_color: str = ft.Colors.BLUE_800,
        junction_color: str = ft.Colors.ORANGE_600,
        junction_radius: float = 6.0,
        hit_radius: float = 14.0,
    ):
        self.tl_box_color = tl_box_color
        self.junction_color = junction_color
        self.junction_radius = junction_radius
        self.hit_radius = hit_radius
        self.tl_light_colors = [ft.Colors.RED, ft.Colors.AMBER, ft.Colors.GREEN]

    @staticmethod
    def is_node_selected(node_id: str, selected_node_id: Optional[str]) -> bool:
        """Determines if a node or semaphore is currently selected."""
        if not selected_node_id or not node_id:
            return False
        n1 = str(node_id).strip()
        n2 = str(selected_node_id).strip()
        if n1 == n2:
            return True
        if n1.replace("tl_", "").replace("node_", "") == n2.replace("tl_", "").replace("node_", ""):
            return True
        return False

    def create_traffic_light_icon(self, sx: float, sy: float, rec_type: str = "existing") -> List[Any]:
        """Creates canvas shapes for a vertical 3-light traffic light glyph."""
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

    def draw_nodes(
        self,
        topology: dict,
        canvas_dynamic: cv.Canvas,
        map_to_canvas: Callable[[dict, float, float], tuple],
        nodes_iter: List[dict],
        node_neighbors: Dict[str, set],
        drawn_nodes_cache: list,
        recommendations: Optional[dict] = None,
        selected_node_id: Optional[str] = None,
        active_filter: str = "ALL",
    ) -> None:
        """Draws all junctions and traffic lights with recommendation filters."""
        recs = recommendations or {}

        for node in nodes_iter:
            try:
                if "x" not in node or "y" not in node:
                    continue

                cx, cy = map_to_canvas(topology, node["x"], node["y"])
                node_type = node.get("type", "")
                node_id = node.get("id", "unknown")
                unique_neighbors = len(node_neighbors.get(node_id, set()))

                rec_string = recs.get(node_id, {}).get("recommendation", "")
                rec_type = "existing"
                if "adicionar" in rec_string.lower() or "add" in rec_string.lower():
                    rec_type = "add"
                elif "remover" in rec_string.lower() or "remove" in rec_string.lower():
                    rec_type = "remove"

                if active_filter == "ADD" and rec_type != "add":
                    continue
                elif active_filter == "REMOVE" and rec_type != "remove":
                    continue
                elif active_filter == "KEEP" and rec_type != "existing":
                    continue

                is_traffic_light = node_type is None or "traffic_light" in str(node_type)

                if self.is_node_selected(node_id, selected_node_id):
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
                    canvas_dynamic.shapes.append(
                        cv.Circle(
                            x=cx,
                            y=cy,
                            radius=self.junction_radius,
                            paint=ft.Paint(color=self.junction_color, style=ft.PaintingStyle.FILL),
                        )
                    )
                    if has_semaphore:
                        icon_shapes = self.create_traffic_light_icon(cx, cy, rec_type)
                        canvas_dynamic.shapes.extend(icon_shapes)
            except Exception as e:
                print(f"[NodeDrawer] Error drawing specific node: {e}")
                continue
