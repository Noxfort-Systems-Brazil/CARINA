# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import gzip
import logging
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from typing import TYPE_CHECKING

# --- CHANGE 1: Add import ---
if TYPE_CHECKING:
    from .locale_manager_backend import LocaleManagerBackend


# --- CHANGE 2: Modify function signature ---
def build_lane_to_edge_map(net_file_path: str, lm: "LocaleManagerBackend") -> dict:
    """
    Reads a .net.xml file and builds a dictionary mapping each lane ID
    to its corresponding street (edge) ID.
    """
    logging.info(lm.get_string("network_parser.lane_to_edge.start", path=net_file_path))
    lane_to_edge_map = {}
    try:
        opener = gzip.open if net_file_path.endswith(".gz") else open
        with opener(net_file_path, "rb") as f:
            tree = ET.parse(f)

        root = tree.getroot()
        for edge in root.findall("edge"):
            edge_id = edge.get("id")
            if not edge_id or edge_id.startswith(":"):
                continue

            for lane in edge.findall("lane"):
                lane_id = lane.get("id")
                if lane_id:
                    lane_to_edge_map[lane_id] = edge_id

        logging.info(lm.get_string("network_parser.lane_to_edge.success", count=len(lane_to_edge_map)))
        return lane_to_edge_map

    except FileNotFoundError:
        logging.error(lm.get_string("network_parser.lane_to_edge.file_not_found_error", path=net_file_path))
        return {}
    except Exception as e:
        logging.error(lm.get_string("network_parser.lane_to_edge.processing_error", error=e), exc_info=True)
        return {}


# --- CHANGE 3: Modify function signature ---
def build_structural_neighborhood_map(
    net_file_path: str, tls_ids_in_sim: list, lm: "LocaleManagerBackend"
) -> defaultdict:
    """
    Builds the structural neighborhood map by traversing the road network graph.
    """
    logging.info(lm.get_string("network_parser.structural_map.start"))

    tls_junctions = set(tls_ids_in_sim)
    junction_connections = defaultdict(list)
    neighborhoods = defaultdict(set)

    try:
        logging.info(lm.get_string("network_parser.structural_map.reading_net_file", path=net_file_path))
        if net_file_path.endswith(".gz"):
            with gzip.open(net_file_path, "rb") as f:
                tree = ET.parse(f)
        else:
            tree = ET.parse(net_file_path)

        root = tree.getroot()
        for edge in root.findall("edge"):
            from_junction = edge.get("from")
            to_junction = edge.get("to")
            if from_junction and to_junction:
                junction_connections[from_junction].append(to_junction)
                junction_connections[to_junction].append(from_junction)

        for start_node in tls_junctions:
            queue = deque([(start_node, [start_node])])
            visited = {start_node}

            while queue:
                current_node, path = queue.popleft()

                for neighbor in junction_connections[current_node]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        new_path = path + [neighbor]

                        if neighbor in tls_junctions:
                            neighborhoods[start_node].add(neighbor)
                        else:
                            queue.append((neighbor, new_path))

        final_neighborhoods = defaultdict(list)
        for tl_id, neighbors_set in neighborhoods.items():
            final_neighborhoods[tl_id] = sorted(list(neighbors_set))
            logging.info(
                lm.get_string(
                    "network_parser.structural_map.neighborhood_found",
                    tl_id=tl_id,
                    neighbors=final_neighborhoods[tl_id],
                )
            )

        logging.info(lm.get_string("network_parser.structural_map.success", count=len(final_neighborhoods)))
        return final_neighborhoods

    except FileNotFoundError as e:
        logging.error(lm.get_string("network_parser.structural_map.file_not_found_error", error=e))
        return defaultdict(list)
    except Exception as e:
        logging.error(lm.get_string("network_parser.structural_map.processing_error", error=e), exc_info=True)
        return defaultdict(list)


def build_neighborhood_map_from_routes(
    net_file_path: str, route_files_list: list, tls_ids_in_sim: list, lm: "LocaleManagerBackend", threshold: int = 1
) -> defaultdict:
    # --- CHANGE 4 ---
    logging.warning(lm.get_string("network_parser.routes_map.obsolete_warning"))
    return defaultdict(list)
