# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Thin Lifecycle Facade & Coordinator running inside CentralController when CARINA_GATEWAY_ROLE=owner.
Composes segregated single-purpose collaborators adhering to SOLID and Clean Architecture:
- GatewayRuntimeWorker (background threads, polling, SDS event forwarding, snapshot cache)
- HardwareCommandService (hardware toggle, CSV, overrides, AI commands, EVP, failsafe)
- FenixStageDispatcher (F.E.N.I.X. post-resurrection stage reconciliation & handover)
- TailscaleGatewayAdapter (infrastructure Tailscale CLI & Go RPC adapter)
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from src.controller.fenix_stage_dispatcher import FenixStageDispatcher
    from src.controller.gateway_runtime_worker import GatewayRuntimeWorker
    from src.controller.hardware_command_service import HardwareCommandService
    from src.drivers.tailscale_gateway_adapter import TailscaleGatewayAdapter
except ImportError:  # pragma: no cover
    from controller.fenix_stage_dispatcher import FenixStageDispatcher
    from controller.gateway_runtime_worker import GatewayRuntimeWorker
    from controller.hardware_command_service import HardwareCommandService
    from drivers.tailscale_gateway_adapter import TailscaleGatewayAdapter

logger = logging.getLogger(__name__)


def is_gateway_owner_role() -> bool:
    """Returns True when CARINA_GATEWAY_ROLE explicitly assigns gateway ownership to this process."""
    return os.environ.get("CARINA_GATEWAY_ROLE", "").strip().lower() == "owner"


class HardwareGatewayCoordinator:
    """
    Lifecycle Facade coordinating owner-process hardware, Go gateway, EVP, Tailscale,
    and F.E.N.I.X. subsystems via injected single-responsibility collaborators.
    """

    def __init__(
        self,
        sds_data_queue: Optional[Any] = None,
        ai_pipe_conn: Optional[Any] = None,
        topology_manager: Optional[Any] = None,
        fenix_queue: Optional[Any] = None,
        connection_manager: Optional[Any] = None,
        go_client: Optional[Any] = None,
        evp_service: Optional[Any] = None,
        locale_manager: Optional[Any] = None,
        poll_interval_seconds: float = 0.25,
        runtime_worker: Optional[GatewayRuntimeWorker] = None,
        command_service: Optional[HardwareCommandService] = None,
        fenix_dispatcher: Optional[FenixStageDispatcher] = None,
        tailscale_adapter: Optional[TailscaleGatewayAdapter] = None,
    ) -> None:
        self.sds_data_queue = sds_data_queue
        self.ai_pipe_conn = ai_pipe_conn
        self.topology_manager = topology_manager
        self.fenix_queue = fenix_queue
        self._conn_mgr = connection_manager
        self._go_client = go_client
        self._evp_service = evp_service
        self.locale_manager = locale_manager
        self.poll_interval_seconds = float(poll_interval_seconds)
        self._evp_listener_registered = False
        self._evp_bridge = None

        self._runtime = runtime_worker or GatewayRuntimeWorker(
            sds_data_queue=sds_data_queue,
            conn_mgr_provider=self._resolve_connection_manager,
            evp_service_provider=self._resolve_evp_service,
            poll_interval_seconds=poll_interval_seconds,
        )
        self._commands = command_service or HardwareCommandService(
            conn_mgr_provider=self._resolve_connection_manager,
            go_client_provider=self._resolve_go_client,
            evp_service_provider=self._resolve_evp_service,
            refresh_snapshots=self._runtime.refresh_snapshots,
            push_sds_event=self._runtime.push_sds_event,
            ai_pipe_provider=lambda: self.ai_pipe_conn,
            locale_manager=locale_manager,
        )
        self._fenix = fenix_dispatcher or FenixStageDispatcher(
            conn_mgr_provider=self._resolve_connection_manager,
            refresh_snapshots=self._runtime.refresh_snapshots,
            topology_manager=topology_manager,
            ai_pipe_provider=lambda: self.ai_pipe_conn,
            fenix_queue_provider=lambda: self.fenix_queue,
            locale_manager=locale_manager,
        )
        self._tailscale = tailscale_adapter or TailscaleGatewayAdapter(
            go_client_provider=lambda: self._resolve_go_client(force=True),
            locale_manager=locale_manager,
        )

    @property
    def _started(self) -> bool:
        return self._runtime.is_started

    @_started.setter
    def _started(self, value: bool) -> None:
        self._runtime.is_started = bool(value)

    # --- Lazy Infrastructure Resolution ---

    def _resolve_go_client(self, force: bool = True) -> Optional[Any]:
        if self._go_client is not None:
            return self._go_client
        if not force and not is_gateway_owner_role():
            return None
        try:
            from src.drivers.go_gateway_client import GoGatewayClient

            self._go_client = GoGatewayClient.get_instance()
        except Exception as exc:
            logger.debug(f"[HardwareGatewayCoordinator] GoGatewayClient unavailable: {exc}")
        return self._go_client

    def _resolve_connection_manager(self, force: bool = True) -> Optional[Any]:
        if self._conn_mgr is not None:
            return self._conn_mgr
        if not force and not is_gateway_owner_role():
            return None
        try:
            from src.controller.connection_manager import HardwareConnectionManager

            self._conn_mgr = HardwareConnectionManager.get_instance(locale_manager=self.locale_manager)
        except Exception as exc:
            logger.debug(f"[HardwareGatewayCoordinator] HardwareConnectionManager unavailable: {exc}")
        return self._conn_mgr

    def _resolve_evp_service(self, force: bool = True) -> Optional[Any]:
        if self._evp_service is not None:
            return self._evp_service
        if not force and not is_gateway_owner_role():
            return None
        try:
            from src.evp.evp_service import EVPService

            self._evp_service = EVPService.get_instance()
        except Exception as exc:
            logger.debug(f"[HardwareGatewayCoordinator] EVPService unavailable: {exc}")
        return self._evp_service

    # --- Lifecycle ---

    def start(self) -> None:
        """Starts Go Gateway, hardware trap callbacks, EVP bridge, and runtime background workers."""
        if self._runtime.is_started:
            return

        go_client = self._resolve_go_client(force=True)
        if go_client is not None:
            try:
                go_client.start()
                if hasattr(go_client, "register_ui_callback"):
                    go_client.register_ui_callback(self._runtime.on_go_event)
            except Exception as exc:
                logger.warning(f"[HardwareGatewayCoordinator] Go gateway startup error: {exc}", exc_info=True)

        conn_mgr = self._resolve_connection_manager(force=True)
        if conn_mgr is not None:
            listener = getattr(conn_mgr, "event_listener", None)
            if listener is not None:
                listener.on_event_callback = self._runtime.on_hardware_trap

        evp_svc = self._resolve_evp_service(force=True)
        if evp_svc is not None:
            try:
                from src.evp.evp_bridge import EVPBridge
                from src.evp.evp_notifier import EVPNotifier

                if self._evp_bridge is None:
                    self._evp_bridge = EVPBridge(evp_service=evp_svc)
                if not self._evp_listener_registered:
                    EVPNotifier.get_instance().register_listener(self._runtime.on_evp_vehicle_update)
                    self._evp_listener_registered = True
            except Exception as exc:
                logger.debug(f"[HardwareGatewayCoordinator] EVP initialization note: {exc}")

        self._runtime.start()
        logger.info("[HardwareGatewayCoordinator] Gateway owner coordinator started.")

    def stop(self) -> None:
        """Stops runtime worker threads, unregisters EVP listeners, and shuts down hardware drivers & Go."""
        self._runtime.stop()

        if self._evp_listener_registered:
            try:
                from src.evp.evp_notifier import EVPNotifier

                EVPNotifier.get_instance().unregister_listener(self._runtime.on_evp_vehicle_update)
            except Exception:
                pass
            self._evp_listener_registered = False

        if self._conn_mgr is not None and hasattr(self._conn_mgr, "shutdown_all"):
            try:
                self._conn_mgr.shutdown_all()
            except Exception as exc:
                logger.debug(f"[HardwareGatewayCoordinator] Hardware shutdown warning: {exc}")

        if self._go_client is not None and hasattr(self._go_client, "stop"):
            try:
                self._go_client.stop()
            except Exception as exc:
                logger.debug(f"[HardwareGatewayCoordinator] Go gateway stop warning: {exc}")

    # --- Delegated Ports ---

    def submit_task(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return self._runtime.submit_task(fn, *args, **kwargs)

    def refresh_snapshots(
        self, push_to_sds: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]:
        return self._runtime.refresh_snapshots(push_to_sds=push_to_sds)

    def get_cached_frame_attachments(self) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]:
        return self._runtime.get_cached_frame_attachments()

    def get_cached_hardware_status(self) -> Dict[str, Dict[str, Any]]:
        return self._runtime.get_cached_hardware_status()

    def toggle_hardware_connection(
        self,
        intersection_id: str,
        ip_address: Optional[str] = None,
        action: str = "toggle",
        snmp_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return self._commands.toggle_hardware_connection(
            intersection_id=intersection_id,
            ip_address=ip_address,
            action=action,
            snmp_config=snmp_config,
        )

    def sync_hardware_csv(self, payload: Dict[str, Any]) -> Tuple[int, int]:
        return self._commands.sync_hardware_csv(payload)

    def set_evp_fleet(self, payload: Dict[str, Any]) -> bool:
        return self._commands.set_evp_fleet(payload)

    def handle_tailscale_command(self, cmd_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self._tailscale.execute(cmd_type, payload)
        self._runtime.push_sds_event(("tailscale_response", response))
        return response

    def sync_override_to_hardware(self, target_tls: List[str], mode: str) -> None:
        self._commands.sync_override_to_hardware(target_tls, mode)

    def execute_ai_hardware_cmd(self, payload: Dict[str, Any]) -> bool:
        return self._commands.execute_ai_hardware_cmd(payload)

    def execute_ai_evp_preempt(self, payload: Dict[str, Any]) -> bool:
        return self._commands.execute_ai_evp_preempt(payload)

    def on_failsafe_triggered(self) -> None:
        self._commands.on_failsafe_triggered()

    def on_failsafe_recovered(self) -> None:
        self._commands.on_failsafe_recovered()

    def dispatch_fenix_reconcile_stages(self, ai_pipe_conn: Optional[Any] = None) -> Dict[str, int]:
        return self._fenix.dispatch_fenix_reconcile_stages(ai_pipe_conn=ai_pipe_conn)

    def handle_fenix_handover_complete(self, payload: Optional[Dict[str, Any]] = None) -> bool:
        return self._fenix.handle_fenix_handover_complete(payload=payload)
