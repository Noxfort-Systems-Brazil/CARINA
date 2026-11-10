# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging


class TopologyRecorderBridge:
    """
    Extracts edge topology (length, lanes, max_speed) from the SUMO net file
    and pushes it to the TrafficDataRecorder for sample enrichment.
    """

    def __init__(self, traffic_data_recorder, locale_manager):
        self.traffic_data_recorder = traffic_data_recorder
        self.locale_manager = locale_manager

    def update_recorder_topology(self, net_file_path: str):
        if not self.traffic_data_recorder or not net_file_path:
            return
        try:
            from utils.network_topology_parser import NetworkTopologyParser

            parser = NetworkTopologyParser(self.locale_manager)
            _, junction_incoming_edges = parser.build(net_file_path)

            # Flatten all edges into a single dict of {edge_id: {length, lanes, max_speed}}
            topology_edges = {}
            for j_id, edges in junction_incoming_edges.items():
                for edge_id, edge_data in edges.items():
                    topology_edges[edge_id] = {
                        "length": edge_data.get("length", 0),
                        "lanes": edge_data.get("num_lanes", 1),
                        "max_speed": edge_data.get("speed_limit", 13.89),
                    }
            self.traffic_data_recorder.set_topology(topology_edges)
        except Exception as e:
            logging.warning(f"[TopologyRecorderBridge] Failed to update recorder topology: {e}", exc_info=True)
