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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: ui/renderers/map_visual_syncer.py
# Author: Gabriel Moraes
# Date: 2026-08-14

"""
Defines the MapVisualSyncer.

Synchronizes and applies cached visual telemetry (heatmaps, overrides, panel data)
directly to Canvas paths and interactive widgets during map initialization and rebuilding.
"""

from typing import Any, Dict, List, Optional

import flet as ft
import flet.canvas as cv

from ui.renderers.heatmap_color_resolver import HeatmapColorResolver


class MapVisualSyncer:
    """
    Applies initial and cached visual state to canvas elements and widgets.
    Adheres to SRP by handling visual state synchronization outside of the main UI widget.
    """

    def sync_cached_visuals(
        self,
        edge_paths: Dict[str, cv.Path],
        interactive_widgets_map: Dict[str, Any],
        topology_edges: List[Dict[str, Any]],
        congestion_data: Dict[str, Any],
        street_overrides: Dict[str, str],
        semaphore_overrides: Dict[str, str],
        panel_data: Dict[str, Any],
    ) -> None:
        """Immediately applies cached telemetry and colors to roads and widgets before the first render frame."""
        self._apply_street_visuals(edge_paths, topology_edges, congestion_data, street_overrides)
        self._apply_widget_telemetry(interactive_widgets_map, panel_data, semaphore_overrides)

    def _apply_street_visuals(
        self,
        edge_paths: Dict[str, cv.Path],
        topology_edges: List[Dict[str, Any]],
        congestion_data: Dict[str, Any],
        street_overrides: Dict[str, str],
    ) -> None:
        if not edge_paths or (not congestion_data and not street_overrides):
            return

        topology_groups: Dict[tuple, List[str]] = {}
        edge_group_map: Dict[str, List[str]] = {}

        for edge_data in topology_edges:
            from_n = edge_data.get("from")
            to_n = edge_data.get("to")
            if from_n and to_n:
                group_key = tuple(sorted([from_n, to_n]))
                if group_key not in topology_groups:
                    topology_groups[group_key] = []
                topology_groups[group_key].append(edge_data["id"])

        for group, ids in topology_groups.items():
            for eid in ids:
                edge_group_map[eid] = ids

        for edge_id, path_object in edge_paths.items():
            is_blocked = False
            siblings = edge_group_map.get(edge_id, [edge_id])
            max_congestion: Optional[float] = None

            for sibling in siblings:
                if street_overrides.get(sibling) == "BLOCKED":
                    is_blocked = True
                base_sibling = sibling[1:] if sibling.startswith("-") else sibling
                reverse_sibling = "-" + base_sibling if not sibling.startswith("-") else base_sibling
                val = None
                if sibling in congestion_data:
                    val = congestion_data[sibling]
                elif base_sibling in congestion_data:
                    val = congestion_data[base_sibling]
                elif reverse_sibling in congestion_data:
                    val = congestion_data[reverse_sibling]

                if val is not None:
                    if isinstance(val, dict):
                        val = val.get("congestion", 0.0)
                    if max_congestion is None or val > max_congestion:
                        max_congestion = val

            if is_blocked:
                new_color = "#000000"
            elif max_congestion is not None:
                new_color = HeatmapColorResolver.get_color_for_congestion(float(max_congestion))
            else:
                new_color = "#2ecc71"

            path_object.paint = ft.Paint(
                stroke_width=path_object.paint.stroke_width,
                color=new_color,
                style=path_object.paint.style,
                stroke_cap=path_object.paint.stroke_cap,
            )

    def _apply_widget_telemetry(
        self, interactive_widgets_map: Dict[str, Any], panel_data: Dict[str, Any], semaphore_overrides: Dict[str, str]
    ) -> None:
        if interactive_widgets_map and panel_data:
            for widget_id, widget in interactive_widgets_map.items():
                if hasattr(widget, "apply_telemetry"):
                    widget.apply_telemetry(panel_data, semaphore_overrides, blink_toggle=False)
