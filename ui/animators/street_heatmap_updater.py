# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Applies congestion heatmap color updates and topological sibling edge resolution
to canvas paths. Decouples street rendering from MapAnimator to respect SRP and Clean Architecture.
"""

from typing import Any, Dict, List
import flet as ft
import flet.canvas as cv
from ui.renderers.heatmap_color_resolver import HeatmapColorResolver


class StreetHeatmapUpdater:
    """
    Computes and applies color changes to street path elements based on
    real-time congestion telemetry and manual street overrides.
    """

    @staticmethod
    def build_edge_group_map(topology_edges: List[Dict]) -> Dict[str, List[str]]:
        """Maps edge IDs to sibling edge IDs sharing the same intersection endpoints."""
        edge_group_map: Dict[str, List[str]] = {}
        topology_groups: Dict[tuple, List[str]] = {}
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
        return edge_group_map

    @classmethod
    def update_edge_paths(
        cls,
        edge_paths: Dict[str, cv.Path],
        edge_group_map: Dict[str, List[str]],
        congestion_data: Dict[str, Any],
        street_overrides: Dict[str, str],
    ) -> None:
        """Evaluates congestion values and overrides, then updates Paint color on paths."""
        for edge_id, path_object in edge_paths.items():
            is_blocked = False
            siblings = edge_group_map.get(edge_id, [edge_id])
            max_congestion = None

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
                new_color = HeatmapColorResolver.get_color_for_congestion(max_congestion)
            else:
                new_color = "#2ecc71"

            if path_object.paint.color != new_color:
                path_object.paint = ft.Paint(
                    stroke_width=path_object.paint.stroke_width,
                    color=new_color,
                    style=path_object.paint.style,
                    stroke_cap=path_object.paint.stroke_cap,
                )
