# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Dependency Injection & IoC Service Container (SOLID: SRP + DIP).
Modeled after SYNAPSE_CORE's ServiceContainer to decouple collaborator
instantiation from CentralController lifecycle orchestration.
"""

import configparser
import logging
import os
from multiprocessing import Queue
from multiprocessing.connection import Connection
from typing import TYPE_CHECKING, Any, Dict, Optional

from communication.grpc_server_manager import GrpcServerManager
from communication.monitor_client import MonitorClient
from communication.pipe_utils import wrap_thread_safe_pipe
from controller.failsafe_manager import FailsafeManager
from controller.hardware_gateway_coordinator import HardwareGatewayCoordinator
from controller.health_monitor import AIHealthMonitor
from controller.override_manager import OverrideManager
from controller.request_processor import RequestProcessor
from controller.system_readiness_latch import SystemReadinessLatch
from controller.topology_manager import ControllerTopologyCoordinator
from controller.traffic_frame_processor import TrafficFrameProcessor
from controller.yellow_schedule_manager import YellowScheduleManager
from core.hft_event_loop import HftEventLoop
from core.hft_system_facade import HftSystemFacade
from database.database_manager import DatabaseManager
from sas.topology_recorder_bridge import TopologyRecorderBridge
from sas.traffic_data_recorder import TrafficDataRecorder
from sds.telemetry_aggregator import TelemetryAggregator
from utils.settings_manager import SettingsManager

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class CentralControllerContainer:
    """
    IoC Container that wires all CentralController collaborators.
    Supports explicit dependency overrides for isolated unit testing (DIP)
    as well as module namespace resolution for legacy patch compatibility.
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
        mfd_trigger_queue: Optional[Queue] = None,
        project_root: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
        factory_namespace: Optional[Any] = None,
    ) -> None:
        self.settings = settings
        self.ai_pipe_conn = wrap_thread_safe_pipe(ai_pipe_conn)
        self.watchdog_queue = watchdog_queue
        self.sds_data_queue = sds_data_queue
        self.sas_data_queue = sas_data_queue
        self.ui_command_queue = ui_command_queue
        self.locale_manager = locale_manager
        self.mfd_trigger_queue = mfd_trigger_queue
        self.project_root = project_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.overrides: Dict[str, Any] = dict(overrides) if overrides else {}
        self._ns = factory_namespace

    def _resolve_cls(self, attr_name: str, default_cls: Any) -> Any:
        """Resolves class from optional namespace (preserving unittest.mock.patch hooks) or default."""
        if self._ns is not None and hasattr(self._ns, attr_name):
            return getattr(self._ns, attr_name)
        return default_cls

    def build(self) -> Dict[str, Any]:
        """Instantiates and connects all CentralController subsystems, returning a wired dictionary."""
        ov = self.overrides

        override_cls = self._resolve_cls("OverrideManager", OverrideManager)
        override_manager = ov.get("override_manager") or override_cls(locale_manager=self.locale_manager)

        aggregator_cls = self._resolve_cls("TelemetryAggregator", TelemetryAggregator)
        telemetry_aggregator = ov.get("telemetry_aggregator") or aggregator_cls(update_interval=5.0)

        heartbeat_timeout = self.settings.getfloat("WATCHDOG", "heartbeat_timeout_seconds", fallback=5.0)
        health_cls = self._resolve_cls("AIHealthMonitor", AIHealthMonitor)
        health_monitor = ov.get("health_monitor") or health_cls(
            heartbeat_timeout=heartbeat_timeout, locale_manager=self.locale_manager
        )

        if "monitor_client" in ov:
            monitor_client = ov["monitor_client"]
        else:
            settings_mgr_cls = self._resolve_cls("SettingsManager", SettingsManager)
            monitor_cls = self._resolve_cls("MonitorClient", MonitorClient)
            monitor_client = monitor_cls(settings_mgr_cls(), self.locale_manager)
            monitor_client.start()

        topo_cls = self._resolve_cls("TopologyManager", ControllerTopologyCoordinator)
        topology_manager = ov.get("topology_manager") or topo_cls(
            project_root=self.project_root,
            ai_pipe_conn=self.ai_pipe_conn,
            sds_data_queue=self.sds_data_queue,
        )

        if "hardware_gateway_coordinator" in ov:
            hardware_gateway_coordinator = ov["hardware_gateway_coordinator"]
        else:
            hw_gw_cls = self._resolve_cls("HardwareGatewayCoordinator", HardwareGatewayCoordinator)
            hardware_gateway_coordinator = hw_gw_cls(
                sds_data_queue=self.sds_data_queue,
                ai_pipe_conn=self.ai_pipe_conn,
                topology_manager=topology_manager,
                locale_manager=self.locale_manager,
            )

        failsafe_cls = self._resolve_cls("FailsafeManager", FailsafeManager)
        failsafe_manager = ov.get("failsafe_manager") or failsafe_cls(
            ai_pipe_conn=self.ai_pipe_conn,
            monitor_client=monitor_client,
            locale_manager=self.locale_manager,
            hardware_gateway_coordinator=hardware_gateway_coordinator,
        )
        if hasattr(failsafe_manager, "set_failsafe_timeout"):
            failsafe_manager.set_failsafe_timeout(heartbeat_timeout)

        db_manager = ov.get("db_manager")
        traffic_data_recorder = ov.get("traffic_data_recorder")
        if "db_manager" not in ov and "traffic_data_recorder" not in ov:
            try:
                db_cls = self._resolve_cls("DatabaseManager", DatabaseManager)
                rec_cls = self._resolve_cls("TrafficDataRecorder", TrafficDataRecorder)
                db_manager = db_cls(self.locale_manager)
                traffic_data_recorder = rec_cls(db_manager=db_manager, batch_size=10, topology_manager=topology_manager)
            except Exception as e:
                logging.warning(
                    self.locale_manager.get_string(
                        "central_controller.traffic_recorder_fail",
                        default="[CentralController] Failed to initialize TrafficDataRecorder: {error}",
                        error=e,
                    ),
                    exc_info=True,
                )
                db_manager = None
                traffic_data_recorder = None

        frame_proc_cls = self._resolve_cls("TrafficFrameProcessor", TrafficFrameProcessor)
        traffic_frame_processor = ov.get("traffic_frame_processor") or frame_proc_cls(
            ai_pipe_conn=self.ai_pipe_conn,
            watchdog_queue=self.watchdog_queue,
            sds_data_queue=self.sds_data_queue,
            failsafe_manager=failsafe_manager,
            topology_manager=topology_manager,
            telemetry_aggregator=telemetry_aggregator,
            override_manager=override_manager,
            traffic_data_recorder=traffic_data_recorder,
            hardware_gateway_coordinator=hardware_gateway_coordinator,
        )

        schedule_config = {}
        if self.settings.has_section("YELLOW_SCHEDULE"):
            schedule_config = dict(self.settings.items("YELLOW_SCHEDULE"))
        yellow_cls = self._resolve_cls("YellowScheduleManager", YellowScheduleManager)
        yellow_schedule_manager = ov.get("yellow_schedule_manager") or yellow_cls(
            settings_dict=schedule_config,
            override_manager=override_manager,
            locale_manager=self.locale_manager,
            sds_data_queue=self.sds_data_queue,
        )

        req_proc_cls = self._resolve_cls("RequestProcessor", RequestProcessor)
        request_processor = ov.get("request_processor") or req_proc_cls(
            settings=self.settings,
            ai_pipe_conn=self.ai_pipe_conn,
            watchdog_q=self.watchdog_queue,
            health_monitor=health_monitor,
            sds_data_queue=self.sds_data_queue,
            sas_data_queue=self.sas_data_queue,
            ui_command_queue=self.ui_command_queue,
            locale_manager=self.locale_manager,
            override_manager=override_manager,
            failsafe_manager=failsafe_manager,
            topology_manager=topology_manager,
            mfd_trigger_queue=self.mfd_trigger_queue,
            yellow_schedule_manager=yellow_schedule_manager,
            hardware_gateway_coordinator=hardware_gateway_coordinator,
        )

        latch_cls = self._resolve_cls("SystemReadinessLatch", SystemReadinessLatch)
        readiness_latch = ov.get("readiness_latch") or latch_cls(traffic_frame_processor)
        if hasattr(request_processor, "set_readiness_callbacks"):
            request_processor.set_readiness_callbacks(readiness_latch.set_ui_ready, readiness_latch.set_backend_ready)

        bridge_cls = self._resolve_cls("TopologyRecorderBridge", TopologyRecorderBridge)
        topology_recorder_bridge = ov.get("topology_recorder_bridge") or bridge_cls(
            traffic_data_recorder=traffic_data_recorder, locale_manager=self.locale_manager
        )

        if hasattr(topology_manager, "try_restore_state"):
            topology_manager.try_restore_state()

        facade_cls = self._resolve_cls("HftSystemFacade", HftSystemFacade)
        hft_system_facade = ov.get("hft_system_facade") or facade_cls(
            topology_manager=topology_manager,
            topology_recorder_bridge=topology_recorder_bridge,
            telemetry_aggregator=telemetry_aggregator,
            watchdog_queue=self.watchdog_queue,
            ui_command_queue=self.ui_command_queue,
            traffic_frame_processor=traffic_frame_processor,
            failsafe_manager=failsafe_manager,
        )

        grpc_mgr_cls = self._resolve_cls("GrpcServerManager", GrpcServerManager)
        grpc_server_manager = ov.get("grpc_server_manager") or grpc_mgr_cls(
            settings=self.settings,
            locale_manager=self.locale_manager,
            implementation_instance=hft_system_facade,
        )

        loop_cls = self._resolve_cls("HftEventLoop", HftEventLoop)
        hft_event_loop = ov.get("hft_event_loop") or loop_cls(
            ai_pipe_conn=self.ai_pipe_conn,
            failsafe_manager=failsafe_manager,
            request_processor=request_processor,
            sds_data_queue=self.sds_data_queue,
            yellow_schedule_manager=yellow_schedule_manager,
        )

        return {
            "override_manager": override_manager,
            "telemetry_aggregator": telemetry_aggregator,
            "health_monitor": health_monitor,
            "monitor_client": monitor_client,
            "failsafe_manager": failsafe_manager,
            "topology_manager": topology_manager,
            "db_manager": db_manager,
            "traffic_data_recorder": traffic_data_recorder,
            "traffic_frame_processor": traffic_frame_processor,
            "yellow_schedule_manager": yellow_schedule_manager,
            "request_processor": request_processor,
            "readiness_latch": readiness_latch,
            "topology_recorder_bridge": topology_recorder_bridge,
            "hft_system_facade": hft_system_facade,
            "grpc_server_manager": grpc_server_manager,
            "hft_event_loop": hft_event_loop,
            "hardware_gateway_coordinator": hardware_gateway_coordinator,
        }


# Alias matching SYNAPSE_CORE naming convention
ServiceContainer = CentralControllerContainer

__all__ = ["CentralControllerContainer", "ServiceContainer"]
