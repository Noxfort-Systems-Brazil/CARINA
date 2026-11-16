# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
SumoGraphTopologyLoader: Parses SUMO .net.xml networks and constructs graph topologies (nodes & edges)
using BFS reachability traversal.
Satisfies Single Responsibility Principle (SRP) by decoupling topology parsing
from neural agent inference.
"""

import logging
import os
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

import sumolib
import torch

from utils.sumo_net_cache import read_sumo_net_cached


class SumoGraphTopologyLoader:
    """
    Parses SUMO .net.xml networks and constructs graph topologies (nodes & edges)
    using BFS reachability traversal.
    """

    def __init__(self, locale_manager: Any = None, logger: Optional[logging.Logger] = None):
        self.locale_manager = locale_manager
        self.logger = logger or logging.getLogger(__name__)

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def load_topology(
        self, net_file: str, device: torch.device
    ) -> Tuple[Dict[str, int], Dict[int, str], int, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """
        Parses the SUMO .net.xml file to extract traffic lights as nodes
        and physical connections as edges using BFS traversal, including edge attributes
        (distance, speed limit, travel time).
        """
        print(
            f"INFO: "
            + self._get_string(
                "strategist_agent.building_graph",
                default="[Strategist] Building Graph from: {net_file}",
                net_file=net_file,
            )
        )

        if not os.path.exists(net_file):
            msg = self._get_string(
                "strategist_agent.net_not_found",
                default="SUMO Network file not found at: {net_file}. Graph not built.",
                net_file=net_file,
            )
            print(f"ERROR: [Strategist] {msg}")
            self.logger.error(msg)
            return {}, {}, 0, None, None

        self.logger.info(
            self._get_string(
                "strategist_agent.building_graph_log",
                default="Building Strategist Graph from: {net_file}",
                net_file=net_file,
            )
        )

        try:
            net = read_sumo_net_cached(net_file, reader_fn=sumolib.net.readNet, with_programs=False, with_internal=None)
            traffic_lights = net.getTrafficLights()

            tls_id_to_idx = {tls.getID(): i for i, tls in enumerate(traffic_lights)}
            idx_to_tls_id = {i: tls.getID() for i, tls in enumerate(traffic_lights)}
            num_nodes = len(traffic_lights)

            source_nodes: List[int] = []
            target_nodes: List[int] = []
            edge_attr_list: List[List[float]] = []
            tls_ids_set = set(tls_id_to_idx.keys())

            for tls in traffic_lights:
                tls_id = tls.getID()
                src_idx = tls_id_to_idx[tls_id]
                node = net.getNode(tls_id)
                if not node:
                    continue

                neighbors_map = self.find_downstream_tls(node, tls_ids_set, net)
                for neighbor_id in sorted(neighbors_map.keys()):
                    if neighbor_id != tls_id:
                        tgt_idx = tls_id_to_idx[neighbor_id]
                        dist, spd, tt = neighbors_map[neighbor_id]
                        source_nodes.append(src_idx)
                        target_nodes.append(tgt_idx)
                        # Normalized: distance in km, speed relative to 30 m/s (~108 km/h), travel time in minutes
                        edge_attr_list.append([dist / 1000.0, spd / 30.0, tt / 60.0])

            if source_nodes:
                edge_index = torch.tensor([source_nodes, target_nodes], dtype=torch.long).to(device)
                edge_attr = torch.tensor(edge_attr_list, dtype=torch.float32).to(device)
                success_msg = self._get_string(
                    "strategist_agent.graph_built_success",
                    default="[Strategist] Graph built successfully. Nodes: {nodes}, Edges: {edges}",
                    nodes=num_nodes,
                    edges=len(source_nodes),
                )
                print(f"INFO: {success_msg}")
                self.logger.info(success_msg)
            else:
                warn_msg = self._get_string(
                    "strategist_agent.no_connections",
                    default="[Strategist] No connections found between traffic lights. Graph is disconnected.",
                )
                print(f"WARNING: {warn_msg}")
                self.logger.warning(warn_msg)
                edge_index = torch.empty((2, 0), dtype=torch.long, device=device)
                edge_attr = torch.empty((0, 3), dtype=torch.float32, device=device)

            return tls_id_to_idx, idx_to_tls_id, num_nodes, edge_index, edge_attr

        except Exception as e:
            err_msg = self._get_string(
                "strategist_agent.build_failed", default="Failed to build graph topology: {error}", error=e
            )
            print(f"ERROR: [Strategist] {err_msg}")
            self.logger.error(err_msg, exc_info=True)
            raise e

    @staticmethod
    def find_downstream_tls(start_node: Any, tls_ids_set: Set[str], net: Any) -> Dict[str, Tuple[float, float, float]]:
        """
        Traverses the network starting from start_node to find reachable Traffic Lights.
        Returns a dictionary mapping neighbor_id -> (distance_meters, max_speed_mps, travel_time_seconds).
        Stops traversing a branch when a TLS is found.
        """
        found_neighbors: Dict[str, Tuple[float, float, float]] = {}
        visited_nodes = set()
        queue = deque([(start_node, 0.0, 50.0)])
        visited_nodes.add(start_node.getID())

        max_depth = 10
        depth_tracker = {start_node.getID(): 0}

        while queue:
            current_node, cum_len, min_spd = queue.popleft()
            current_depth = depth_tracker[current_node.getID()]
            if current_depth >= max_depth:
                continue

            for edge in current_node.getOutgoing():
                next_node = edge.getToNode()
                next_node_id = next_node.getID()
                if next_node_id in visited_nodes:
                    continue

                visited_nodes.add(next_node_id)
                depth_tracker[next_node_id] = current_depth + 1

                try:
                    raw_len = edge.getLength()
                    edge_len = float(raw_len) if isinstance(raw_len, (int, float)) else 100.0
                except Exception:
                    edge_len = 100.0

                try:
                    raw_spd = edge.getSpeed()
                    edge_spd = float(raw_spd) if isinstance(raw_spd, (int, float)) else 13.89
                except Exception:
                    edge_spd = 13.89

                new_cum_len = cum_len + max(0.0, edge_len)
                new_min_spd = max(1.0, min(min_spd, edge_spd))

                if next_node_id in tls_ids_set:
                    travel_time = new_cum_len / new_min_spd
                    if next_node_id not in found_neighbors:
                        found_neighbors[next_node_id] = (new_cum_len, new_min_spd, travel_time)
                    continue
                else:
                    queue.append((next_node, new_cum_len, new_min_spd))

        return found_neighbors
