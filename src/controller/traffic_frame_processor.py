import logging
from multiprocessing import Queue
from multiprocessing.connection import Connection
from typing import Any

from controller.failsafe_manager import FailsafeManager
from controller.topology_manager import TopologyManager

class TrafficFrameProcessor:
    """
    Responsável por desempacotar frames de hardware/synapse e roteá-los
    corretamente para a IA e o agregador visual da UI.
    """
    def __init__(self, ai_pipe_conn: Connection, watchdog_queue: Queue, sds_data_queue: Queue, 
                 failsafe_manager: FailsafeManager, topology_manager: TopologyManager, telemetry_aggregator: Any):
        self.ai_pipe_conn = ai_pipe_conn
        self.watchdog_queue = watchdog_queue
        self.sds_data_queue = sds_data_queue
        
        self.failsafe_manager = failsafe_manager
        self.topology_manager = topology_manager
        self.telemetry_aggregator = telemetry_aggregator
        
        # --- NEW: Two-Stage Readiness Latch ---
        self.is_system_ready = False
        
    def set_system_ready(self, state: bool):
        self.is_system_ready = state

    def process_traffic_frame(self, frame: Any):
        """
        Processes a single Traffic Frame received from Synapse.
        This is the TRIGGER for the AI Decision Cycle.
        """
        # 1. WATCHDOG HEARTBEAT
        try:
            self.watchdog_queue.put("HEARTBEAT")
        except Exception as e:
            logging.error(f"Failed to send Heartbeat: {e}")

        # 2. FAILSAFE RECOVERY
        self.failsafe_manager.attempt_recovery()

        # 3. NORMAL PROCESSING (AI Step)
        current_time = frame.timestamp
        
        traffic_data = {'timestamp': current_time, 'sequence_id': frame.sequence_id, 'edges': {}}
        
        # Prepare data for AI (still manual as it is control logic, not visualization)
        for edge_id, state in frame.edges.items():
            traffic_data['edges'][edge_id] = {
                'occupancy': state.occupancy,
                'mean_speed': state.mean_speed,
                'queue_length': state.queue_length
            }

        # AGREEMENT: This is the ONLY place triggering the HFT Step.
        if self.is_system_ready:
            try: 
                self.ai_pipe_conn.send(('custom', 'hft_step', (traffic_data,), {}))
            except Exception as e: 
                logging.error(f"Error sending frame to AI: {e}")
        else:
            # Drop AI frame dispatch, but allow visualization to continue.
            pass

        # 4. VISUALIZATION AGGREGATION
        self.telemetry_aggregator.process_frame(frame)
        
        if self.telemetry_aggregator.should_update(current_time):
            # Pass maturity cache so aggregator can include it in the payload
            if not self.topology_manager.agent_maturity_cache:
                self.topology_manager.try_restore_state()
            
            rich_payload = self.telemetry_aggregator.compute_rich_payload(
                current_time, 
                self.topology_manager.agent_maturity_cache
            )
            
            try:
                self.sds_data_queue.put(('hft_rich_update', rich_payload))
            except Exception as e:
                logging.error(f"Error putting rich update on SDS queue: {e}")
