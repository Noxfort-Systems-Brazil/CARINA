# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
import time
from multiprocessing import Queue
from multiprocessing.connection import Connection
from typing import Any, Dict, Optional

from utils.map_processor import MapProcessor


class ControllerTopologyCoordinator:
    """
    Responsible for loading, structural extraction, and continuous caching
    of network topology and Agent 'Maturity Phases' in the CentralController.
    """

    def __init__(self, project_root: str, ai_pipe_conn: Connection, sds_data_queue: Queue):
        self.project_root = project_root
        self.ai_pipe_conn = ai_pipe_conn
        self.sds_data_queue = sds_data_queue

        # Agent maturity cache (ID -> Phase)
        self.agent_maturity_cache: Dict[str, str] = {}

        # Store the loaded .net.xml path for FailsafeManager/FixedTimeController
        self.net_file_path: Optional[str] = None

    def try_restore_state(self):
        """Attempts to load existing topology to restore maturity cache AND notify AI/UI to load map."""
        try:
            session_name = "hft_live_session"
            from utils.paths import get_base_output_dir

            maps_dir = os.path.join(get_base_output_dir(), "results", session_name, "maps")
            json_path = os.path.join(maps_dir, "map_topology.json")

            if os.path.exists(json_path):
                logging.info("[CentralController] Restoring state from existing topology...")
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    nodes = data.get("nodes", [])
                    count = 0
                    for node in nodes:
                        if node.get("type") == "traffic_light":
                            # Defaults to CHILD if no phase persistence
                            self.agent_maturity_cache[node["id"]] = "CHILD"
                            count += 1
                logging.info(f"[CentralController] State restored: {count} agents identified in cache.")

            # 1. Find and Load the .net.xml file for the AI Engine
            net_xml_path = None
            for file_name in os.listdir(maps_dir):
                if file_name.endswith(".net.xml") or file_name.endswith(".net.xml.gz"):
                    net_xml_path = os.path.join(maps_dir, file_name)
                    break

            if net_xml_path:
                logging.info(f"[CentralController] Found Network Map: {net_xml_path}. Commanding AI to load...")
                self.net_file_path = net_xml_path  # Store for FailsafeManager
                # Send agnostic load command config for AI RequestProcessor
                self.ai_pipe_conn.send(("custom", "load_map", (net_xml_path,), {}))

                if not os.path.exists(json_path):
                    logging.info(
                        "[CentralController] map_topology.json is missing! Extracting JSON topology from map..."
                    )
                    try:
                        self.agent_maturity_cache = MapProcessor.extract_topology_to_json(net_xml_path, json_path)
                    except Exception as e:
                        logging.error(f"Error extracting JSON topology: {e}", exc_info=True)

                # 2. NOTIFY UI (This fixes the 'Waiting for Connection' issue)
                try:
                    self.sds_data_queue.put(("initial_map_geometry", {"net_file": net_xml_path}))
                    logging.info("[CentralController] 'initial_map_geometry' event sent to SDS queue (Restored State).")
                except Exception as e:
                    logging.error(f"Error notifying UI during restore: {e}", exc_info=True)

                # Give AI a brief moment to digest the map before traffic hits
                time.sleep(0.5)
            else:
                logging.warning("[CentralController] No .net.xml map found. AI might not initialize correctly.")

        except Exception as e:
            logging.warning(f"[CentralController] Failed to restore state: {e}", exc_info=True)

    def handle_new_map(self, map_path: str, maps_output_dir: str, telemetry_aggregator: Any):
        """
        Processes a full map reload from a new source.
        """
        logging.info(f"Processing new map: {map_path}")

        # 1. Extract Vector Topology to JSON (for Flet UI) & Get Maturity Cache
        try:
            json_path = os.path.join(maps_output_dir, "map_topology.json")

            # Using MapProcessor to handle I/O and parsing
            self.agent_maturity_cache = MapProcessor.extract_topology_to_json(map_path, json_path)

            # Reset aggregator when map changes
            if telemetry_aggregator:
                telemetry_aggregator.reset()

        except Exception as e:
            logging.error(f"Error extracting JSON topology from map: {e}", exc_info=True)

        # 2. Notify AI
        try:
            self.ai_pipe_conn.send(("custom", "load_map", (map_path,), {}))
            self.net_file_path = map_path  # Store for FailsafeManager
        except Exception as e:
            logging.error(f"Error notifying AI about new map: {e}", exc_info=True)

        # 3. Notify UI (SDS)
        try:
            self.sds_data_queue.put(("initial_map_geometry", {"net_file": map_path}))
            logging.info("'initial_map_geometry' event sent to SDS queue.")
        except Exception as e:
            logging.error(f"Error notifying UI about new map: {e}", exc_info=True)


# Backward-compatibility alias
TopologyManager = ControllerTopologyCoordinator

__all__ = ["ControllerTopologyCoordinator", "TopologyManager"]
