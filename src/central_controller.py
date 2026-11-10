# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import json
import logging
import os
import sys
import time
from concurrent import futures
from multiprocessing import Queue
from multiprocessing.connection import Connection
from typing import TYPE_CHECKING, Dict

import grpc

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

try:
    import synapse_hft_pb2 as pb2  # type: ignore
    import synapse_hft_pb2_grpc as pb2_grpc  # type: ignore
except ImportError:
    logging.critical(
        "[CentralController] Failed to import generated gRPC modules. Ensure 'proto' folder exists and contains generated files."
    )
    pb2, pb2_grpc = None, None  # type: ignore

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from communication.grpc_server_manager import GrpcServerManager
from communication.hft_server import CarinaHFTImpl
from communication.monitor_client import MonitorClient
from controller.failsafe_manager import FailsafeManager
from controller.health_monitor import AIHealthMonitor
from controller.override_manager import OverrideManager
from controller.request_processor import RequestProcessor
from controller.system_readiness_latch import SystemReadinessLatch
from controller.topology_manager import TopologyManager
from controller.traffic_frame_processor import TrafficFrameProcessor
from controller.yellow_schedule_manager import YellowScheduleManager
from core.hft_event_loop import HftEventLoop
from core.hft_system_facade import HftSystemFacade
from database.database_manager import DatabaseManager
from sas.topology_recorder_bridge import TopologyRecorderBridge
from sas.traffic_data_recorder import TrafficDataRecorder
from sds.telemetry_aggregator import TelemetryAggregator
from utils.map_processor import MapProcessor
from utils.safety_rules import SafetyRules
from utils.settings_manager import SettingsManager


from typing import TYPE_CHECKING, Any, Dict, Optional

from factories.service_container import CentralControllerContainer


# --- CENTRAL CONTROLLER ---
class CentralController:
    """
    The Brain of the Operation.
    Orchestrates the flow of data between the Perception Layer (Synapse),
    the AI Engine, the Safety Watchdog, and the User Interface.

    Adheres to SRP & DIP: Collaborator instantiation is delegated to
    CentralControllerContainer, and pre-built services can be injected directly.
    """

    def __init__(
        self,
        settings: configparser.ConfigParser,
        ai_pipe_conn: Connection,
        watchdog_queue: Queue,
        sds_data_queue: Queue,
        sas_data_queue: Queue,
        ui_command_queue: Queue,
        locale_manager: "LocaleManagerBackend",
        mfd_trigger_queue: Queue = None,
        services: Optional[Dict[str, Any]] = None,
    ):
        self.settings = settings
        self.ai_pipe_conn = ai_pipe_conn
        self.watchdog_queue = watchdog_queue
        self.sds_data_queue = sds_data_queue
        self.ui_command_queue = ui_command_queue
        self.locale_manager = locale_manager
        self.mfd_trigger_queue = mfd_trigger_queue

        container = CentralControllerContainer(
            settings=settings,
            ai_pipe_conn=ai_pipe_conn,
            watchdog_queue=watchdog_queue,
            sds_data_queue=sds_data_queue,
            sas_data_queue=sas_data_queue,
            ui_command_queue=ui_command_queue,
            locale_manager=locale_manager,
            mfd_trigger_queue=mfd_trigger_queue,
            project_root=project_root,
            overrides=services,
            factory_namespace=sys.modules[__name__],
        )
        wired = container.build()

        self.override_manager = wired["override_manager"]
        self.telemetry_aggregator = wired["telemetry_aggregator"]
        self.health_monitor = wired["health_monitor"]
        self.monitor_client = wired["monitor_client"]
        self.failsafe_manager = wired["failsafe_manager"]
        self.topology_manager = wired["topology_manager"]
        self.db_manager = wired["db_manager"]
        self.traffic_data_recorder = wired["traffic_data_recorder"]
        self.traffic_frame_processor = wired["traffic_frame_processor"]
        self.yellow_schedule_manager = wired["yellow_schedule_manager"]
        self.request_processor = wired["request_processor"]
        self.readiness_latch = wired["readiness_latch"]
        self.topology_recorder_bridge = wired["topology_recorder_bridge"]
        self.hft_system_facade = wired["hft_system_facade"]
        self.grpc_server_manager = wired["grpc_server_manager"]
        self.hft_event_loop = wired["hft_event_loop"]
        self.is_running = True

    def run(self):
        lm = self.locale_manager
        logging.info(
            lm.get_string("central_controller.starting", default="[DIAGNOSTICS] Starting HFT CentralController.")
        )
        server_port = self.settings.get("SYNAPSE", "port", fallback="50051")
        max_workers = self.settings.getint("SYNAPSE", "max_workers", fallback=10)

        try:
            self.grpc_server_manager.start()
            # --- MAIN HFT LOOP ---
            self.hft_event_loop.run_loop()

        except KeyboardInterrupt:
            logging.info(lm.get_string("central_controller.manual_interrupt", default="Manual interruption received."))
        except Exception as e:
            logging.critical(
                lm.get_string(
                    "central_controller.grpc_fatal_error", default="Fatal error in gRPC server: {error}", error=e
                ),
                exc_info=True,
            )
        finally:
            self.stop()

    def stop(self):
        logging.info(
            self.locale_manager.get_string("central_controller.stopping", default="Stopping CentralController...")
        )
        self.is_running = False
        if hasattr(self, "hft_event_loop"):
            self.hft_event_loop.stop()

        # We no longer deactivate local FixedTimeController here since CARINA is agnostic
        # and delegating it to Edge hardware.
        pass

        if self.grpc_server_manager:
            self.grpc_server_manager.stop()
        try:
            self.ai_pipe_conn.send(("system", "shutdown", (), {}))
        except (BrokenPipeError, OSError, EOFError, Exception):
            pass
        if getattr(self, "monitor_client", None):
            shutdown_msg = self.locale_manager.get_string("monitor.shutdown", default="CARINA System Shutting Down...")
            self.monitor_client.stop(shutdown_message=shutdown_msg)
