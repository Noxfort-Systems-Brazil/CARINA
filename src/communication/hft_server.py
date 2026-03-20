# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
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
#
# File: src/communication/hft_server.py
# Author: Gabriel Moraes
# Date: 2026-02-20

import logging
import time
import os
import sys
from datetime import datetime
from typing import Optional

# Ensure project root and proto paths are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
proto_path = os.path.join(project_root, 'proto')

if proto_path not in sys.path:
    sys.path.insert(0, proto_path)

# Import generated gRPC modules
try:
    import synapse_hft_pb2 as pb2 # type: ignore
    import synapse_hft_pb2_grpc as pb2_grpc # type: ignore
except ImportError:
    logging.critical("[HFTServer] Failed to import generated gRPC modules. Ensure 'proto' folder exists and contains generated files.")
    pb2, pb2_grpc = None, None # type: ignore


class CarinaHFTImpl(pb2_grpc.HFTLinkServicer): # type: ignore
    """
    Implementation of the High-Frequency Traffic (HFT) Link gRPC Service.
    Handles incoming connections from the Perception Layer (Synapse).
    """

    def __init__(self, controller_instance):
        """
        Args:
            controller_instance: Reference to the CentralController to delegate logic.
        """
        self.controller = controller_instance
        self.state = "IDLE"
        
        # Dedicated logger for interval metrics in logs/hft
        self.interval_logger = self._setup_interval_logger()

    def _setup_interval_logger(self) -> Optional[logging.Logger]:
        """
        Configures a specific logger to write ONLY the inter-arrival times
        to 'logs/hft/hft_inter_arrival.log'.
        """
        try:
            from src.utils.paths import get_base_output_dir
            log_dir = os.path.join(get_base_output_dir(), 'logs', 'hft')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'hft_inter_arrival.log')
            
            logger = logging.getLogger('HFT_Interval_Logger')
            logger.setLevel(logging.INFO)
            logger.propagate = False  # Prevent propagation to root logger (console)
            
            # Avoid adding multiple handlers if re-initialized
            if not logger.handlers:
                handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
                # Simple format: just the message
                formatter = logging.Formatter('%(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            
            return logger
        except Exception as e:
            logging.error(f"[HFT] Failed to setup interval logger: {e}")
            return None

    def Ping(self, request, context):
        """Health check method."""
        return pb2.SystemState(active=True, state=self.state, server_time=int(time.time()))

    def LoadScenario(self, request, context):
        """
        Receives the traffic network topology (map) from Synapse.
        Saves the provided map file and triggers map processing in the controller.
        """
        logging.info(f"[HFT] Receiving scenario from Synapse (Hash: {request.map_hash})...")
        success = True
        msg = "Map processed"

        if request.map_file_content:
            try:
                # Define correct folder structure: results/hft_live_session/maps
                session_name = "hft_live_session"
                from src.utils.paths import get_base_output_dir
                session_dir = os.path.join(get_base_output_dir(), "results", session_name)
                maps_dir = os.path.join(session_dir, "maps")
                
                # Ensure folder exists
                os.makedirs(maps_dir, exist_ok=True)
                
                # --- NEW: Save peak_schedule_json if present ---
                if request.peak_schedule_json:
                    peak_schedule_path = os.path.join(session_dir, "peak_schedule.json")
                    with open(peak_schedule_path, "w", encoding="utf-8") as f:
                        f.write(request.peak_schedule_json)
                    logging.info(f"[HFT] Peak Schedule JSON saved successfully at: {peak_schedule_path}")
                # -----------------------------------------------
                
                # Extract the original file name sent by Synapse, or use a default if missing
                original_filename = request.map_file_name
                if not original_filename:
                    original_filename = f"{session_name}.net.xml"
                    logging.warning(f"[HFT] map_file_name not provided by Synapse. Falling back to {original_filename}")
                
                # Save the file (binary or xml) directly to the maps folder using the correct name
                map_path = os.path.join(maps_dir, original_filename)
                
                with open(map_path, "wb") as f:
                    f.write(request.map_file_content)
                
                logging.info(f"[HFT] Map saved successfully at: {map_path}")
                
                # Process topology and notify AI via Controller
                self.controller.handle_new_map(map_path, maps_dir)
                
                self.state = "READY"
            except Exception as e:
                logging.error(f"[HFT] Error saving/processing map: {e}", exc_info=True)
                success = False
                msg = str(e)
        else:
            logging.warning("[HFT] LoadScenario received without file content.")
            success = False
            msg = "Empty map content"

        return pb2.ScenarioStatus(accepted=success, message=msg)

    def SystemControl(self, request, context):
        """
        Handles Start/Stop commands for the AI Session.
        """
        cmd = request.action
        if cmd == pb2.ControlCommand.START:
            self.state = "RUNNING"
            self.controller.start_ai_session()
            print(f"🚀 [SYSTEM] HFT Control Started. State is now RUNNING.")
        elif cmd == pb2.ControlCommand.STOP:
            self.state = "IDLE"
            self.controller.stop_ai_session()
            print(f"🛑 [SYSTEM] HFT Control Stopped. State is now IDLE.")
        return pb2.CommandResponse(success=True, new_state=self.state)

    def StreamTraffic(self, request_iterator, context):
        """
        Receives the stream of Traffic Frames from Synapse.
        Logs the time difference (Delta) between consecutive frames.
        Delegates processing to the controller.
        """
        # Reset counters for this new stream session
        msg_counter = 0
        last_recv_time = 0.0

        try:
            # THIS LOOP WAITS for data from Synapse
            for frame in request_iterator:
                
                current_recv_time = time.time()
                msg_counter += 1
                
                # --- INTER-ARRIVAL CALCULATION (Delta) ---
                if msg_counter > 1 and last_recv_time > 0:
                    delta_ms = (current_recv_time - last_recv_time) * 1000
                    
                    if self.interval_logger:
                        # Log Format: [HH:MM:SS.mmm] Delta: X ms
                        ts_str = datetime.fromtimestamp(current_recv_time).strftime('%H:%M:%S.%f')[:-3]
                        log_msg = f"[{ts_str}] Delta: {delta_ms:.2f} ms"
                        self.interval_logger.info(log_msg)
                
                last_recv_time = current_recv_time

                # --- DECISION LOGIC ---
                if self.state == "RUNNING":
                    # Trigger CARINA Logic via Controller
                    self.controller.process_traffic_frame(frame)
                else:
                    pass
                    
        except Exception as e:
            logging.error(f"[HFT] Error in traffic stream: {e}")
            print(f"❌ [HFT] Stream Connection Lost: {e}")
            
        return pb2.SystemState(active=True, state=self.state)