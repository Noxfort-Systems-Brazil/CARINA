# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/rendering/static_map_painter.py
# Author: Gabriel Moraes
# Date: September 2026

import logging
from typing import Any, Callable, Dict, List, Optional

import matplotlib.patches as patches
from matplotlib.offsetbox import AnnotationBbox, DrawingArea


class StaticMapPainter:
    """
    Renders vector geometry (streets, intersections, traffic lights)
    onto a Matplotlib Axes instance matching the CARINA UI aesthetic.
    Follows Single Responsibility Principle (SRP).
    """

    @staticmethod
    def draw_streets(ax: Any, edges: List[Dict[str, Any]], map_to_canvas: Callable[[float, float], tuple]) -> None:
        """Paints black street lines (linewidth=4.5) on the given axis."""
        for edge in edges:
            shape = edge.get("shape")
            if not shape:
                continue
            try:
                projected_shape = [map_to_canvas(pt[0], pt[1]) for pt in shape]
                x_coords, y_coords = zip(*projected_shape)
                ax.plot(x_coords, y_coords, color="black", linewidth=4.5, zorder=1)
            except ValueError:
                logging.warning(f"[StaticMapPainter] Invalid shape for edge: {edge.get('id', 'N/A')}")

    @staticmethod
    def draw_nodes_and_traffic_lights(
        ax: Any,
        nodes: Dict[str, Any],
        icon_requests: Optional[Dict[str, str]],
        map_to_canvas: Callable[[float, float], tuple],
    ) -> None:
        """Paints junctions (orange circles) and vertical 3-light traffic light glyphs."""
        if not nodes:
            return

        for node_id, node in nodes.items():
            if "x" not in node or "y" not in node:
                continue
            cx, cy = map_to_canvas(node["x"], node["y"])

            clean_node_id = str(node_id).strip()
            rec_type = "existing"
            if icon_requests:
                if clean_node_id in icon_requests:
                    rec_type = icon_requests[clean_node_id]
                elif node_id in icon_requests:
                    rec_type = icon_requests[node_id]

            node_type = node.get("type")
            is_traffic_light = node_type is None or "traffic_light" in str(node_type)

            # Draw orange junction circle (radius 6)
            da_circle = DrawingArea(width=12, height=12, xdescent=0, ydescent=0)
            circle = patches.Circle((6, 6), 6, color="#FB8C00")
            da_circle.add_artist(circle)
            ab_circle = AnnotationBbox(da_circle, (cx, cy), box_alignment=(0.5, 0.5), frameon=False, pad=0.0, zorder=2)
            ax.add_artist(ab_circle)

            # Draw vertical 3-light traffic light if applicable
            if (is_traffic_light and rec_type != "no_signal") or rec_type == "add":
                da = DrawingArea(width=16, height=42, xdescent=0, ydescent=0)

                if rec_type == "add":
                    box_color = "#388E3C"  # Green_700
                elif rec_type == "remove":
                    box_color = "#D32F2F"  # Red_700
                else:
                    box_color = "#1565C0"  # Blue_800

                rect = patches.Rectangle((0, 0), 16, 42, facecolor=box_color, edgecolor="none")
                da.add_artist(rect)

                # Three bulbs: Red (top), Amber (mid), Green (bottom)
                c_red = patches.Circle((8, 33), 4, color="#FF0000")
                c_amber = patches.Circle((8, 21), 4, color="#FFC107")
                c_green = patches.Circle((8, 9), 4, color="#4CAF50")

                da.add_artist(c_red)
                da.add_artist(c_amber)
                da.add_artist(c_green)

                ab = AnnotationBbox(da, (cx, cy), box_alignment=(0.5, 0.5), frameon=False, pad=0.0, zorder=3)
                ax.add_artist(ab)
