# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time


class HftEventLoop:
    """
    SRP: Handles the main background event loop for HFT monitoring, pipe signals,
    and failsafe ticking.
    """

    def __init__(
        self,
        ai_pipe_conn,
        failsafe_manager,
        request_processor,
        sds_data_queue,
        yellow_schedule_manager=None,
    ):
        self.ai_pipe_conn = ai_pipe_conn
        self.failsafe_manager = failsafe_manager
        self.request_processor = request_processor
        self.sds_data_queue = sds_data_queue
        self.yellow_schedule_manager = yellow_schedule_manager
        self.is_running = True
        self._last_schedule_check = 0.0

    def run_loop(self):
        logging.info("[HftEventLoop] Entering main HFT processing loop...")
        while self.is_running:
            # Check for shutdown signal from launcher
            # Drain all pending messages from the AI process pipe
            while self.ai_pipe_conn.poll():
                try:
                    cmd = self.ai_pipe_conn.recv()
                    if isinstance(cmd, tuple) and len(cmd) >= 2 and cmd[0] == "system" and cmd[1] == "shutdown":
                        logging.info("[HftEventLoop] Shutdown signal received. Exiting main loop gracefully...")
                        self.is_running = False
                        break
                    else:
                        self.request_processor.handle_single_request(cmd, sumo_conn=None)
                except EOFError:
                    self.is_running = False
                    break
                except Exception as e:
                    logging.error(f"[HftEventLoop] Pipe poll error: {e}", exc_info=True)
                    break

            # --- FAILSAFE MONITORING (In-Process Synapse Silence Detection) ---
            if not self.failsafe_manager.failsafe_active:
                if not self.failsafe_manager.check_synapse_health():
                    self.failsafe_manager.trigger_failsafe()
            else:
                phase_changes = self.failsafe_manager.tick()
                if phase_changes:
                    try:
                        self.sds_data_queue.put(
                            (
                                "failsafe_phase_update",
                                {"changes": phase_changes, "status": self.failsafe_manager.get_status()},
                            )
                        )
                    except Exception as e:
                        logging.error(f"[HftEventLoop] Error sending failsafe update: {e}", exc_info=True)

            # --- YELLOW SCHEDULE MONITORING (Time-of-day Flashing Control) ---
            now_ts = time.time()
            if self.yellow_schedule_manager and (now_ts - self._last_schedule_check >= 1.0):
                self._last_schedule_check = now_ts
                try:
                    override_mgr = getattr(self.request_processor, "override_manager", None)
                    self.yellow_schedule_manager.tick(override_manager=override_mgr)
                except Exception as e_sched:
                    logging.error(f"[HftEventLoop] Error in yellow schedule tick: {e_sched}", exc_info=True)

            try:
                self.request_processor.process_queues(
                    sumo_conn=None, is_ai_healthy=not self.failsafe_manager.failsafe_active
                )
            except Exception as e_proc:
                logging.error(f"[HftEventLoop] Error in processing loop: {e_proc}", exc_info=True)

            time.sleep(0.05)

    def stop(self):
        self.is_running = False
