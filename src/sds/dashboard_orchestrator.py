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

# File: src/sds/dashboard_orchestrator.py (MODIFIED FOR TRANSLATION)
# Author: Gabriel Moraes
# Date: October 2, 2025

import configparser
import logging
import os
import queue
import sys
import threading
from multiprocessing import Queue
from typing import TYPE_CHECKING, Optional

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

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
        Inicializa o orquestrador e seus componentes especialistas.
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

        logging.info(lm.get_string("sds_orchestrator.init.orchestrator_created"))

    def run(self):
        """
        Inicia os serviços e entra no loop principal de processamento de dados.
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

        except KeyboardInterrupt:
            logging.info(lm.get_string("sds_orchestrator.run.interrupt_received"))
        except Exception as e:
            logging.error(lm.get_string("sds_orchestrator.run.fatal_error", error=e), exc_info=True)
        finally:
            if hasattr(self, "ws_server") and self.ws_server:
                try:
                    self.ws_server.stop()
                except Exception:
                    pass
            logging.info(lm.get_string("sds_orchestrator.run.orchestrator_finished"))
