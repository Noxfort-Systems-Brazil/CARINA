# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Specialist Road Topology and Block Mapping Service (EVP).
Responsible for ingesting vector road networks, indexing traffic light nodes,
and computing the real physical length of approach blocks (SRP).
"""

import logging
import math
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from src.evp.evp_geo_projector import EVPEngineGeoProjector

logger = logging.getLogger(__name__)


class EVPTopologyService:
    """
    Thread-safe service for indexing traffic light nodes and road blocks.
    """

    def __init__(self):
        self._intersections_geo: Dict[str, Tuple[float, float]] = {}
        self._intersection_target_stages: Dict[str, int] = {}
        self._intersection_quadras: Dict[str, List[Dict[str, Any]]] = {}
        self._map_loaded: bool = False
        self._geo_bounds: Optional[Any] = None
        self._lock = threading.RLock()

    def _ensure_geo_bounds(self) -> Optional[Any]:
        """Retrieves or caches geodetic bounds (WGS84 and SUMO convBoundary) of active road network."""
        with self._lock:
            if self._geo_bounds is not None:
                return self._geo_bounds

            try:
                from src.utils.sumo_geo_bounds_reader import SumoGeoBoundsReader
                from ui.loader.map_asset_path_resolver import MapAssetPathResolver

                resolver = MapAssetPathResolver()
                scenario_dir = resolver.find_latest_scenario_dir()
                if scenario_dir:
                    maps_dir = os.path.join(scenario_dir, "maps")
                    target_dir = maps_dir if os.path.exists(maps_dir) else scenario_dir
                    if os.path.exists(target_dir):
                        candidates = [
                            os.path.join(target_dir, f)
                            for f in os.listdir(target_dir)
                            if f.endswith(".net.xml.gz") or f.endswith(".net.xml")
                        ]
                        if candidates:
                            self._geo_bounds = SumoGeoBoundsReader.read_bounds(candidates[0])
                            if self._geo_bounds:
                                logger.info(
                                    f"[EVPTopologyService] Metadados geodésicos carregados de {os.path.basename(candidates[0])}."
                                )
                                return self._geo_bounds
            except Exception as ex:
                logger.debug(f"[EVPTopologyService] Erro ao carregar metadados geodésicos da malha: {ex}")
            return None

    def set_geo_bounds(self, bounds: Any) -> None:
        """Allows explicit injection of geodetic bounds (useful for unit tests or preloading)."""
        with self._lock:
            self._geo_bounds = bounds

    def lat_lon_to_sumo(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        Converts WGS84 geographic coordinates (lat, lon) to local metric SUMO coordinates (x, y).
        """
        bounds = self._ensure_geo_bounds()
        return EVPEngineGeoProjector.lat_lon_to_sumo(lat, lon, bounds)

    def sumo_to_lat_lon(self, x: float, y: float) -> Tuple[float, float]:
        """
        Converts local metric SUMO coordinates (x, y) to WGS84 geographic coordinates (lat, lon).
        """
        bounds = self._ensure_geo_bounds()
        return EVPEngineGeoProjector.sumo_to_lat_lon(x, y, bounds)

    @property
    def intersections_geo(self) -> Dict[str, Tuple[float, float]]:
        with self._lock:
            return dict(self._intersections_geo)

    def register_intersection(
        self,
        intersection_id: str,
        lat: float,
        lon: float,
        target_stage: int = 1,
        quadra_length: Optional[float] = None,
    ) -> None:
        """Registers traffic light location, target stage, and optionally block length."""
        with self._lock:
            self._intersections_geo[intersection_id] = (lat, lon)
            self._intersection_target_stages[intersection_id] = target_stage
            if quadra_length is not None and quadra_length > 0:
                self._intersection_quadras[intersection_id] = [
                    {
                        "edge_id": f"edge_{intersection_id}",
                        "name": f"Aproximação {intersection_id}",
                        "from": None,
                        "to": intersection_id,
                        "length": float(quadra_length),
                        "shape": [],
                    }
                ]
            logger.info(
                f"[EVPTopologyService] Semáforo {intersection_id} em ({lat:.5f}, {lon:.5f}), alvo {target_stage}"
                f"{f', quadra {quadra_length:.0f}m' if quadra_length else ''}."
            )

    def get_quadra_length(self, intersection_id: str) -> Optional[float]:
        """Returns physical length of approach block in meters, if mapped."""
        with self._lock:
            quadras = self._intersection_quadras.get(intersection_id, [])
            if quadras:
                return max((q["length"] for q in quadras), default=None)
            return None

    def get_target_stage(self, intersection_id: str, default: int = 1) -> int:
        """Returns green corridor stage configured for approach."""
        with self._lock:
            return self._intersection_target_stages.get(intersection_id, default)

    def auto_load_map(self) -> bool:
        """Attempts to automatically load road map topology from disk."""
        try:
            from ui.loader.map_asset_loader import MapAssetLoader
            loader = MapAssetLoader()
            map_data = loader.load_map_data()
            if map_data:
                count = self.load_map_data(map_data)
                return count > 0
        except Exception as ex:
            logger.debug(f"[EVPTopologyService] Auto-carregamento omitido: {ex}")
        return False

    def load_map_data(self, map_data: Any) -> int:
        """
        Ingests vector topology of road network (nodes and edges).
        Maps traffic lights and calculates approach block lengths.
        """
        with self._lock:
            if not map_data:
                return 0

            nodes, edges = self._extract_nodes_and_edges(map_data)
            if not nodes:
                return 0

            tls_registered = self._register_nodes(nodes)
            self._map_incoming_edges(edges)
            self._map_loaded = True
            total_quadras = sum(len(q) for q in self._intersection_quadras.values())
            logger.info(f"[EVPTopologyService] Malha carregada: {tls_registered} semáforos, {total_quadras} quadras.")
            return tls_registered

    def _extract_nodes_and_edges(self, map_data: Any) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        nodes: Dict[str, Any] = {}
        edges: List[Dict[str, Any]] = []

        if isinstance(map_data, tuple) and len(map_data) >= 2:
            n_raw, e_raw = map_data[0], map_data[1]
            nodes = n_raw if isinstance(n_raw, dict) else {n["id"]: n for n in n_raw if isinstance(n, dict) and "id" in n}
            edges = e_raw if isinstance(e_raw, list) else []
        elif isinstance(map_data, dict):
            n_raw = map_data.get("nodes", {})
            nodes = n_raw if isinstance(n_raw, dict) else {n["id"]: n for n in n_raw if isinstance(n, dict) and "id" in n}
            edges = map_data.get("edges", [])
        return nodes, edges

    def _resolve_node_coords(self, x: float, y: float) -> Tuple[float, float]:
        """Resolves whether node coordinates are already geographic (lat, lon) or need conversion from SUMO metrics."""
        if abs(y) <= 90.0 and abs(x) <= 180.0 and (y != 0.0 or x != 0.0):
            bounds = self._ensure_geo_bounds()
            is_within_conv = False
            if bounds:
                is_within_conv = (bounds.min_x <= x <= bounds.max_x) and (bounds.min_y <= y <= bounds.max_y)
            if not is_within_conv or (x < 0 or y < 0):
                return float(y), float(x)
        return self.sumo_to_lat_lon(x, y)

    def _register_nodes(self, nodes: Dict[str, Any]) -> int:
        self._ensure_geo_bounds()
        registered = 0
        for n_id, n_info in nodes.items():
            if not isinstance(n_info, dict):
                continue
            n_type = str(n_info.get("type", "")).lower()
            is_tls = "traffic_light" in n_type or "tls" in n_type or n_id in self._intersections_geo
            x = float(n_info.get("x", n_info.get("lon", n_info.get("longitude", 0.0))))
            y = float(n_info.get("y", n_info.get("lat", n_info.get("latitude", 0.0))))

            if is_tls:
                lat, lon = self._resolve_node_coords(x, y)
                self._intersections_geo[n_id] = (lat, lon)
                self._intersection_target_stages.setdefault(n_id, 1)
                registered += 1

        if registered == 0:
            for n_id, n_info in nodes.items():
                if isinstance(n_info, dict):
                    x = float(n_info.get("x", n_info.get("lon", 0.0)))
                    y = float(n_info.get("y", n_info.get("lat", 0.0)))
                    lat, lon = self._resolve_node_coords(x, y)
                    self._intersections_geo[n_id] = (lat, lon)
                    self._intersection_target_stages.setdefault(n_id, 1)
                    registered += 1
        return registered

    def _map_incoming_edges(self, edges: List[Dict[str, Any]]) -> None:
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            to_node = edge.get("to")
            if not to_node or to_node not in self._intersections_geo:
                continue

            e_id = edge.get("id", f"quadra_{to_node}")
            e_len = float(edge.get("length", 0.0))
            shape = edge.get("shape", [])
            if e_len <= 0 and isinstance(shape, list) and len(shape) >= 2:
                e_len = sum(math.hypot(shape[i + 1][0] - shape[i][0], shape[i + 1][1] - shape[i][1]) for i in range(len(shape) - 1))

            self._intersection_quadras.setdefault(to_node, []).append({
                "edge_id": e_id,
                "name": edge.get("name", e_id),
                "from": edge.get("from"),
                "to": to_node,
                "length": e_len if e_len > 0 else 120.0,
                "shape": shape,
            })
