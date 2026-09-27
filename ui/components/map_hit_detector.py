# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/components/map_hit_detector.py
# Author: Gabriel Moraes
# Date: September 2026

import math
from typing import Any, Dict, List, Optional, Tuple


class MapHitDetector:
    """
    Performs 2D geometric collision and hit detection for vector map nodes and street polylines.
    Follows Single Responsibility Principle (SRP).
    """

    @staticmethod
    def _dist_sq(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2

    @classmethod
    def _dist_to_segment_sq(cls, p: Tuple[float, float], v: Tuple[float, float], w: Tuple[float, float]) -> float:
        l2 = cls._dist_sq(v, w)
        if l2 == 0:
            return cls._dist_sq(p, v)
        t = max(0.0, min(1.0, ((p[0] - v[0]) * (w[0] - v[0]) + (p[1] - v[1]) * (w[1] - v[1])) / l2))
        proj = (v[0] + t * (w[0] - v[0]), v[1] + t * (w[1] - v[1]))
        return cls._dist_sq(p, proj)

    @classmethod
    def detect_hit(
        cls,
        map_x: float,
        map_y: float,
        scale: float,
        drawn_nodes_cache: List[dict],
        drawn_edges_cache: List[dict],
        node_base_hit_radius: float = 14.0,
    ) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
        """
        Determines whether (map_x, map_y) collided with a node, street edge, or background.
        Returns: (hit_type, element_id, raw_data) where hit_type in ('node', 'edge', 'none').
        """
        effective_scale = scale if scale > 0 else 1.0

        # 1. Check Node Hits (Junctions / Semaphores)
        clicked_node_id = None
        min_node_dist = float("inf")
        node_hit_radius = node_base_hit_radius / effective_scale

        for node in drawn_nodes_cache:
            dx = map_x - node["cx"]
            dy = map_y - node["cy"]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < min_node_dist:
                min_node_dist = dist
                clicked_node_id = node["id"]

        node_hit = clicked_node_id is not None and min_node_dist <= node_hit_radius

        # 2. Check Street Segment Hits (Edges)
        clicked_edge_id = None
        clicked_edge_raw = None
        min_edge_dist_sq = float("inf")
        click_pt = (map_x, map_y)
        edge_hit_threshold_sq = (25.0 / effective_scale) ** 2

        for edge in drawn_edges_cache:
            pts = edge.get("points", [])
            for i in range(len(pts) - 1):
                d_sq = cls._dist_to_segment_sq(click_pt, pts[i], pts[i + 1])
                if d_sq < min_edge_dist_sq:
                    min_edge_dist_sq = d_sq
                    clicked_edge_id = edge["id"]
                    clicked_edge_raw = edge.get("raw", {})

        min_edge_dist = math.sqrt(min_edge_dist_sq)
        edge_hit = clicked_edge_id is not None and min_edge_dist_sq <= edge_hit_threshold_sq

        # 3. Disambiguate between Node and Edge hits
        if node_hit and edge_hit:
            if min_node_dist <= (8.0 / effective_scale) or min_node_dist < min_edge_dist:
                return "node", clicked_node_id, None
            else:
                return "edge", clicked_edge_id, clicked_edge_raw
        elif node_hit:
            return "node", clicked_node_id, None
        elif edge_hit:
            return "edge", clicked_edge_id, clicked_edge_raw
        else:
            return "none", None, None
