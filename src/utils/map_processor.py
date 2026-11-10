# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
import time
from typing import Any, Dict

import sumolib  # type: ignore


class MapProcessor:
    """
    Responsible for parsing SUMO network files (.net.xml) and extracting
    topology data for the UI and system configuration.
    """

    @staticmethod
    def extract_topology_to_json(net_file: str, output_json: str, locale_manager=None) -> Dict[str, str]:
        """
        Reads .net.xml file and generates a JSON containing ALL junctions.
        Returns a dictionary mapping Traffic Light IDs to their initial maturity state (default 'CHILD').
        """

        def get_str(key: str, default: str = None, **kwargs) -> str:
            if locale_manager and hasattr(locale_manager, "get_string"):
                return locale_manager.get_string(key, default=default, **kwargs)
            return default.format(**kwargs) if default and kwargs else (default or key)

        logging.info(
            get_str("map_processor.extracting", default="[MAP_GEN] Extracting vector data to: {path}", path=output_json)
        )

        maturity_cache = {}

        try:
            net = sumolib.net.readNet(net_file, withInternal=False)

            bbox = net.getBBoxXY()
            bounds = {"min_x": bbox[0][0], "min_y": bbox[0][1], "max_x": bbox[1][0], "max_y": bbox[1][1]}

            edges_list = []
            for edge in net.getEdges():
                from_node = edge.getFromNode()
                to_node = edge.getToNode()
                raw_name = edge.getName() if hasattr(edge, "getName") else None
                edge_name = raw_name if raw_name else edge.getID()
                edges_list.append(
                    {
                        "id": edge.getID(),
                        "name": edge_name,
                        "from": from_node.getID() if from_node else None,
                        "to": to_node.getID() if to_node else None,
                        "shape": list(edge.getShape()),
                        "lanes": edge.getLaneNumber() if hasattr(edge, "getLaneNumber") else 1,
                        "speed": edge.getSpeed() if hasattr(edge, "getSpeed") else 13.89,
                        "length": edge.getLength() if hasattr(edge, "getLength") else 0.0,
                    }
                )

            from collections import defaultdict

            junction_neighbors = defaultdict(set)
            for edge in net.getEdges():
                from_node = edge.getFromNode()
                to_node = edge.getToNode()
                if from_node and to_node:
                    junction_neighbors[from_node.getID()].add(to_node.getID())
                    junction_neighbors[to_node.getID()].add(from_node.getID())

            nodes_list = []
            traffic_lights_count = 0
            junctions_count = 0

            ignored_types = {"dead_end", "internal", "rail_crossing", "rail_signal"}

            for node in net.getNodes():
                n_type = node.getType()
                node_id = node.getID()

                if n_type == "traffic_light":
                    traffic_lights_count += 1
                    # Initialize default maturity
                    maturity_cache[node_id] = "CHILD"
                elif len(junction_neighbors[node_id]) >= 3 and n_type not in ignored_types:
                    junctions_count += 1

                nx, ny = node.getCoord()
                node_data = {"id": node_id, "x": nx, "y": ny, "type": n_type}
                nodes_list.append(node_data)

            topology_data = {
                "bounds": bounds,
                "edges": edges_list,
                "nodes": nodes_list,
                "metadata": {
                    "generated_at": time.time(),
                    "total_tls": traffic_lights_count,
                    "total_junctions": junctions_count,
                },
            }

            # Ensure directory exists
            os.makedirs(os.path.dirname(output_json), exist_ok=True)

            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(topology_data, f)

            logging.info(
                get_str(
                    "map_processor.json_generated",
                    default="[MAP_GEN] JSON generated. TLS: {tls}, Junctions: {junctions}",
                    tls=traffic_lights_count,
                    junctions=junctions_count,
                )
            )

            return maturity_cache

        except Exception as e:
            logging.error(
                get_str(
                    "map_processor.critical_error", default="[MAP_GEN] Critical error parsing map: {error}", error=e
                ),
                exc_info=True,
            )
            raise e
