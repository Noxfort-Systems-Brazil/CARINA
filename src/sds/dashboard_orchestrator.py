# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
import queue
import threading
from multiprocessing import Queue
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from sds.cco_broadcast_client import CCOBroadcastClient
from sds.data_processor import DataProcessor
from sds.websocket_server import WebSocketServer


class Orchestrator:
    """The maestro that manages the workflow of the SDS service."""

    def __init__(
        self,
        sds_data_queue: Queue,
        settings: configparser.ConfigParser,
        ui_command_queue: Queue,
        locale_manager: "LocaleManagerBackend",
        ui_telemetry_queue: Optional[Queue] = None,
    ):
        """
        Initializes the orchestrator and its specialist components.
        """
        self.data_queue = sds_data_queue
        self.locale_manager = locale_manager
        self.ui_telemetry_queue = ui_telemetry_queue
        lm = self.locale_manager

        self.processor = DataProcessor(settings, lm)
        if self.ui_telemetry_queue is None:
            self.ws_server = WebSocketServer(ui_command_queue=ui_command_queue, locale_manager=lm)
        else:
            self.ws_server = None

        self._cco_client = CCOBroadcastClient(timeout=0.15)
        logging.info(lm.get_string("sds_orchestrator.init.orchestrator_created"))

    def run(self):
        """
        Starts the services and enters the main data processing loop.
        """
        lm = self.locale_manager
        try:
            if self.ws_server:
                ws_thread = threading.Thread(target=self.ws_server.start, daemon=True)
                ws_thread.start()
                logging.info(lm.get_string("sds_orchestrator.run.ws_thread_started"))
            else:
                logging.info("[SDS Orchestrator] Running in zero-port IPC mode (multiprocessing.Queue).")

            logging.info(lm.get_string("sds_orchestrator.run.main_loop_start"))
            while True:
                raw_sim_data = self.data_queue.get()

                if raw_sim_data is None:
                    break

                ui_data_package = self.processor.process_for_ui(raw_sim_data)

                if ui_data_package:
                    if self.ui_telemetry_queue is not None:
                        try:
                            self.ui_telemetry_queue.put_nowait(ui_data_package)
                        except queue.Full:
                            # Drop oldest non-critical frame to prevent queue stall if UI is busy
                            try:
                                _ = self.ui_telemetry_queue.get_nowait()
                                self.ui_telemetry_queue.put_nowait(ui_data_package)
                            except Exception:
                                pass
                    elif self.ws_server:
                        self.ws_server.broadcast(ui_data_package)

                    # Forward telemetry non-blocking (latest-wins) to Go Gateway (Videowall CCO SSE)
                    self._cco_client.enqueue_broadcast(ui_data_package)

        except KeyboardInterrupt:
            logging.info(lm.get_string("sds_orchestrator.run.interrupt_received"))
        except Exception as e:
            logging.error(lm.get_string("sds_orchestrator.run.fatal_error", error=e), exc_info=True)
        finally:
            try:
                self._cco_client.close()
            except Exception:
                pass
            if hasattr(self, "ws_server") and self.ws_server:
                try:
                    self.ws_server.stop()
                except Exception:
                    pass
            logging.info(lm.get_string("sds_orchestrator.run.orchestrator_finished"))
