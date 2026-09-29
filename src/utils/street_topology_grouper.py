# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/utils/street_topology_grouper.py
# Author: Gabriel Moraes
# Date: August 2026

import gzip
import logging
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple


class StreetTopologyGrouper:
    """
    Parses SUMO network files (.net.xml / .net.xml.gz), applies dual street grouping heuristics:
    1. Straight Streets: Paired by positive and negative edge IDs (e.g., '123' and '-123').
    2. Non-Straight / Curved Streets: Grouped by starting node ('from') and ending node ('to').
    Stores and updates custom user-configured names in PostgreSQL topology_dictionary.
    """

    def __init__(self, db_manager: Any = None, locale_manager: Any = None):
        self.db_manager = db_manager
        self.locale_manager = locale_manager

    def parse_and_store_topology(self, net_file_path: str) -> bool:
        """
        Parses .net.xml or .net.xml.gz file, identifies junctions (intersections)
        and edges (streets), applies dual grouping, and stores them in PostgreSQL.
        """
        if not os.path.exists(net_file_path):
            logging.warning(f"[StreetTopologyGrouper] Network file not found: {net_file_path}")
            return False

        try:
            if net_file_path.endswith(".gz"):
                with gzip.open(net_file_path, "rb") as f:
                    tree = ET.parse(f)
            else:
                tree = ET.parse(net_file_path)
            root = tree.getroot()
        except Exception as e:
            logging.error(f"[StreetTopologyGrouper] Error parsing network XML file {net_file_path}: {e}")
            return False

        intersections = []
        edges = []

        # 1. Parse Junctions (Intersections)
        for junction in root.findall("junction"):
            j_id = junction.get("id", "")
            j_type = junction.get("type", "")
            # Filter traffic light or priority junctions
            if j_id and not j_id.startswith(":") and j_type in ("traffic_light", "priority", "right_before_left"):
                num_id = self._extract_numeric_id(j_id)
                intersections.append(
                    {
                        "element_type": "INTERSECTION",
                        "raw_net_id": j_id,
                        "numeric_id": num_id,
                        "custom_name": f"Cruzamento ID {num_id}",
                        "from_node": None,
                        "to_node": None,
                        "is_bidirectional_pair": False,
                    }
                )

        # 2. Parse Edges (Streets) and apply dual grouping
        edge_raw_map: Dict[str, Dict[str, Any]] = {}
        for edge in root.findall("edge"):
            e_id = edge.get("id", "")
            if not e_id or e_id.startswith(":"):
                continue

            from_node = edge.get("from", "")
            to_node = edge.get("to", "")
            name = edge.get("name", "")
            num_id = self._extract_numeric_id(e_id)

            edge_raw_map[e_id] = {
                "raw_net_id": e_id,
                "numeric_id": num_id,
                "from_node": from_node,
                "to_node": to_node,
                "name": name,
            }

        # Apply Dual Grouping for Streets
        processed_edges = set()
        grouped_streets = []

        for e_id, info in edge_raw_map.items():
            if e_id in processed_edges:
                continue

            # Check straight street positive/negative pair (e.g., "123" and "-123" or "-abc" and "abc")
            opposite_id = f"-{e_id}" if not e_id.startswith("-") else e_id[1:]
            is_bidirectional = opposite_id in edge_raw_map

            if is_bidirectional:
                # Straight street pair
                processed_edges.add(e_id)
                processed_edges.add(opposite_id)

                custom_name = info["name"] or f"Via Principal (Arestas {e_id} / {opposite_id})"
                grouped_streets.append(
                    {
                        "element_type": "STREET",
                        "raw_net_id": f"{e_id};{opposite_id}",
                        "numeric_id": info["numeric_id"],
                        "custom_name": custom_name,
                        "from_node": info["from_node"],
                        "to_node": info["to_node"],
                        "is_bidirectional_pair": True,
                    }
                )
            else:
                # Non-straight / Curved street (grouped by from_node -> to_node)
                processed_edges.add(e_id)
                custom_name = info["name"] or f"Trecho Viário ({info['from_node']} -> {info['to_node']})"
                grouped_streets.append(
                    {
                        "element_type": "STREET",
                        "raw_net_id": e_id,
                        "numeric_id": info["numeric_id"],
                        "custom_name": custom_name,
                        "from_node": info["from_node"],
                        "to_node": info["to_node"],
                        "is_bidirectional_pair": False,
                    }
                )

        # 3. Store in PostgreSQL via db_manager
        all_elements = intersections + grouped_streets
        if self.db_manager and hasattr(self.db_manager, "step_decision_repo"):
            self.db_manager.step_decision_repo.bulk_save_topology_elements(all_elements)
            logging.info(
                f"[StreetTopologyGrouper] Successfully stored {len(all_elements)} topology elements ({len(intersections)} intersections, {len(grouped_streets)} street groups) in PostgreSQL."
            )

        return True

    def update_custom_name(self, element_type: str, raw_net_id: str, new_custom_name: str) -> bool:
        """
        Updates the user-configured custom name for a street or intersection in PostgreSQL.
        """
        if self.db_manager and hasattr(self.db_manager, "step_decision_repo"):
            return self.db_manager.step_decision_repo.update_topology_custom_name(
                element_type.upper(), raw_net_id, new_custom_name
            )
        return False

    @staticmethod
    def _extract_numeric_id(raw_id: str) -> int:
        """
        Extracts numeric digits from raw XML ID string into a BIGINT int.
        """
        digits = "".join([c for c in raw_id if c.isdigit()])
        if digits:
            return int(digits)
        # Fallback hash int if no digits present
        return abs(hash(raw_id)) % (10**10)
