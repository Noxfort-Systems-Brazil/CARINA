# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging


class HftSystemFacade:
    """
    SRP/OCP: Facade to expose only the strictly necessary system functions to the external HFT Server.
    Prevents the gRPC server from being tightly coupled to the CentralController god-class.
    """

    def __init__(
        self,
        topology_manager,
        topology_recorder_bridge,
        telemetry_aggregator,
        watchdog_queue,
        ui_command_queue,
        traffic_frame_processor,
        failsafe_manager=None,
    ):
        self.topology_manager = topology_manager
        self.topology_recorder_bridge = topology_recorder_bridge
        self.telemetry_aggregator = telemetry_aggregator
        self.watchdog_queue = watchdog_queue
        self.ui_command_queue = ui_command_queue
        self.traffic_frame_processor = traffic_frame_processor
        self.failsafe_manager = failsafe_manager

    def handle_new_map(self, map_path: str, maps_output_dir: str):
        self.topology_manager.handle_new_map(map_path, maps_output_dir, self.telemetry_aggregator)
        self.topology_recorder_bridge.update_recorder_topology(map_path)

    def start_ai_session(self):
        logging.info("AI Session started.")

    def stop_ai_session(self):
        logging.info("AI Session stopped.")

    def process_traffic_frame(self, frame):
        self.traffic_frame_processor.process_traffic_frame(frame)
