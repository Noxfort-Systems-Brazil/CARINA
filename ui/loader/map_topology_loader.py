# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
from typing import Any, Dict, Tuple

from src.utils.map_data_parser import parse_map_data


class MapTopologyLoader:
    """Specialized service for reading, parsing, and converting network map topology data."""

    @classmethod
    def load_topology(cls, scenario_dir: str) -> Tuple[Dict, Any, Dict] | None:
        """Attempts to load map topology from the scenario directory (JSON, SUMO net.xml, or legacy XML)."""
        try:
            maps_dir = os.path.join(scenario_dir, "maps")
            target_dir = maps_dir if os.path.exists(maps_dir) else scenario_dir

            # --- ATTEMPT 1: Load Topology JSON ---
            json_topology_path = os.path.join(target_dir, "map_topology.json")
            cached_fallback = None
            if os.path.exists(json_topology_path):
                try:
                    with open(json_topology_path, "r", encoding="utf-8") as f:
                        topology = json.load(f)
                    nodes_list = topology.get("nodes", [])
                    edges_list = topology.get("edges", [])
                    bounds = topology.get("bounds", {})

                    has_full_topology = edges_list and all(
                        "from" in e and "to" in e for e in edges_list[: min(10, len(edges_list))]
                    )
                    has_names = edges_list and any(
                        "name" in e and e["name"] for e in edges_list[: min(20, len(edges_list))]
                    )
                    if has_full_topology and has_names:
                        logging.info(f"[MapTopologyLoader] Carregando topologia vetorial: {json_topology_path}")
                        nodes_dict = {node["id"]: node for node in nodes_list}
                        cls.register_default_aliases(edges_list)
                        return nodes_dict, edges_list, bounds
                    elif has_full_topology:
                        nodes_dict = {node["id"]: node for node in nodes_list}
                        cached_fallback = (nodes_dict, edges_list, bounds)
                        logging.warning(
                            f"[MapTopologyLoader] Topologia sem 'name' em {json_topology_path}. Re-extraindo..."
                        )
                    else:
                        logging.warning(
                            f"[MapTopologyLoader] Topologia sem 'from'/'to' em {json_topology_path}. Re-extraindo..."
                        )
                except Exception as e:
                    logging.error(f"[MapTopologyLoader] Erro ao processar map_topology.json: {e}", exc_info=True)

            # --- ATTEMPT 2: Load SUMO Network Map (*.net.xml.gz / *.net.xml) ---
            net_file_path = None
            if os.path.exists(target_dir):
                gz_candidates = [
                    os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith(".net.xml.gz")
                ]
                xml_candidates = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith(".net.xml")]
                if gz_candidates:
                    net_file_path = gz_candidates[0]
                elif xml_candidates:
                    net_file_path = xml_candidates[0]

            if net_file_path:
                logging.info(
                    f"[MapTopologyLoader] Mapa SUMO ({os.path.basename(net_file_path)}): {net_file_path}. Extraindo JSON..."
                )
                from src.utils.map_processor import MapProcessor

                try:
                    MapProcessor.extract_topology_to_json(net_file_path, json_topology_path)

                    from src.rendering.cartodb_basemap_fetcher import CartoDBBasemapFetcher

                    if CartoDBBasemapFetcher.ENABLED:
                        maps_dir = os.path.join(scenario_dir, "maps") if os.path.exists(os.path.join(scenario_dir, "maps")) else target_dir
                        basemap_target = os.path.join(maps_dir, "basemap_positron.png")
                        if not os.path.exists(basemap_target):
                            from src.utils.sumo_geo_bounds_reader import SumoGeoBoundsReader

                            geo_bounds = SumoGeoBoundsReader.read_bounds(net_file_path)
                            if geo_bounds and geo_bounds.has_geo_coords:
                                CartoDBBasemapFetcher.fetch_basemap(geo_bounds, maps_dir)

                    if os.path.exists(json_topology_path):
                        with open(json_topology_path, "r", encoding="utf-8") as f:
                            topology = json.load(f)
                        nodes_list = topology.get("nodes", [])
                        edges_list = topology.get("edges", [])
                        bounds = topology.get("bounds", {})
                        nodes_dict = {node["id"]: node for node in nodes_list}
                        cls.register_default_aliases(edges_list)
                        return nodes_dict, edges_list, bounds
                except Exception as e:
                    logging.error(f"[MapTopologyLoader] Erro ao extrair topologia de {net_file_path}: {e}", exc_info=True)

            if cached_fallback:
                logging.info("[MapTopologyLoader] Usando topologia em cache como fallback.")
                cls.register_default_aliases(cached_fallback[1])
                return cached_fallback

            # --- ATTEMPT 3: Load Legacy Plain XML (.nod.xml) ---
            scenario_name = os.path.basename(scenario_dir)
            map_data_prefix = os.path.join(target_dir, f"{scenario_name}_map")
            if os.path.exists(map_data_prefix + ".nod.xml"):
                logging.info(f"[MapTopologyLoader] Carregando arquivos XML legado: {map_data_prefix}")
                parsed_data = parse_map_data(map_data_prefix)
                if parsed_data and len(parsed_data) == 3:
                    return parsed_data

        except Exception as e:
            logging.error(f"[MapTopologyLoader] Erro ao carregar mapa de {scenario_dir}: {e}", exc_info=True)

        return None

    @staticmethod
    def register_default_aliases(edges_list: list) -> None:
        """Registers road network street names as default aliases in AliasManager."""
        try:
            from ui.managers.alias_manager import AliasManager

            alias_mgr = AliasManager()
            mapping = {}
            for edge in edges_list:
                if isinstance(edge, dict):
                    eid = edge.get("id")
                    ename = edge.get("name")
                    if eid and ename and str(ename) != str(eid):
                        mapping[str(eid)] = str(ename)
            if mapping:
                alias_mgr.register_default_aliases(mapping)
        except Exception as ex:
            logging.debug(f"[MapTopologyLoader] Could not register default street aliases: {ex}")
