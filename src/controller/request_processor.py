# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
from multiprocessing import Queue
from multiprocessing.connection import Connection
from queue import Empty
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from controller.failsafe_manager import FailsafeManager
    from controller.health_monitor import AIHealthMonitor
    from controller.override_manager import OverrideManager
    from controller.topology_manager import TopologyManager
    from utils.locale_manager_backend import LocaleManagerBackend

# Import Handlers
try:
    from src.handlers.ai_request_handler import AIRequestHandler
    from src.handlers.ui_command_handler import UICommandHandler
    from src.handlers.watchdog_command_handler import WatchdogCommandHandler
except ImportError:
    from handlers.ai_request_handler import AIRequestHandler
    from handlers.ui_command_handler import UICommandHandler
    from handlers.watchdog_command_handler import WatchdogCommandHandler
from security.security_manager import SecurityManager


class EnvironmentConnectionException(RuntimeError):
    pass


class RequestProcessor:
    """
    Message Bus Orchestrator.
    Reads queues and delegates incoming messages to specific handlers (SOLID SRP).
    """

    def __init__(
        self,
        settings: configparser.ConfigParser,
        ai_pipe_conn: Connection,
        watchdog_q: Queue,
        health_monitor: "AIHealthMonitor",
        sds_data_queue: Queue,
        sas_data_queue: Queue,
        ui_command_queue: Queue,
        locale_manager: "LocaleManagerBackend",
        override_manager: "OverrideManager",
        failsafe_manager: "FailsafeManager",
        topology_manager: "TopologyManager",
        mfd_trigger_queue: Queue = None,
        yellow_schedule_manager=None,
    ):

        self.ai_pipe_conn = ai_pipe_conn
        self.watchdog_q = watchdog_q
        self.ui_command_queue = ui_command_queue
        self.yellow_schedule_manager = yellow_schedule_manager

        # Shared State
        self.override_commands_buffer = []

        # Initialize Specialized Handlers
        self.security_manager = SecurityManager()
        self.ui_handler = UICommandHandler(
            locale_manager,
            override_manager,
            failsafe_manager,
            self.security_manager,
            sds_data_queue,
            sas_data_queue,
            mfd_trigger_queue=mfd_trigger_queue,
            yellow_schedule_manager=yellow_schedule_manager,
        )
        self.ai_handler = AIRequestHandler(
            locale_manager, topology_manager, sds_data_queue, sas_data_queue, health_monitor, override_manager
        )
        self.watchdog_handler = WatchdogCommandHandler(locale_manager)

        logging.info(locale_manager.get_string("request_processor.init.processor_created"))

    def set_readiness_callbacks(self, ui_cb, backend_cb):
        self.ui_handler.set_ui_ready_callback(ui_cb)
        self.ai_handler.set_backend_ready_callback(backend_cb)

    def handle_single_request(self, request: Any, sumo_conn: Any):
        try:
            collect_func = getattr(self, "_collect_batched_step_data", None)
            self.ai_handler.process(request, sumo_conn, self.ai_pipe_conn, self.override_commands_buffer, collect_func)
        except EnvironmentConnectionException as e_conn:
            logging.error(f"[RequestProcessor] Erro de Conexão com Ambiente: {e_conn}", exc_info=True)
            if self.ai_pipe_conn and not self.ai_pipe_conn.closed:
                self.ai_pipe_conn.send(e_conn)
        except Exception as e:
            logging.error(f"[RequestProcessor] AI Request Handler throwed unexpected error: {e}", exc_info=True)
            if self.ai_pipe_conn and not self.ai_pipe_conn.closed:
                try:
                    self.ai_pipe_conn.send(e)
                except Exception as _exc:
                    logging.debug("[controller] Ignored recoverable error: %s", _exc)

    def process_queues(self, sumo_conn: Any, is_ai_healthy: bool):
        # UI Commands (Flet Interface)
        try:
            while True:
                command = self.ui_command_queue.get_nowait()
                if isinstance(command, dict):
                    if command.get("type") == "set_hardware_connection":
                        payload = command.get("payload", {})
                        action = payload.get("action", "toggle")
                        if self.ai_pipe_conn and not self.ai_pipe_conn.closed:
                            self.ai_pipe_conn.send(
                                (
                                    "hardware",
                                    "toggle_connection",
                                    (payload.get("intersection_id"), payload.get("ip_address"), action),
                                    {},
                                )
                            )
                    else:
                        self.ui_handler.process(command, sumo_conn, self.override_commands_buffer)
        except Empty:
            pass
        except EnvironmentConnectionException as e_conn:
            logging.error(f"[RequestProcessor] Erro de Conexão ao processar comando da UI: {e_conn}", exc_info=True)
        except Exception as e:
            logging.error(f"[RequestProcessor] Erro critico no UI Handler: {e}", exc_info=True)

        if is_ai_healthy:
            pass  # Previously we polled ai_pipe_conn here, now handled by HftEventLoop

            # NOTE: Watchdog queue is NO LONGER drained here.
            # The watchdog_queue is exclusively owned by the Watchdog process
            # for heartbeat monitoring. Failsafe state is now managed in-process
            # by FailsafeManager.check_synapse_health() in the CentralController.
