# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Controller Layer Protocols (SOLID: ISP & DIP).
Defines narrow contracts for CentralController collaborators.
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class ITopologyCoordinator(Protocol):
    """Contract for CentralController topology restoration and map reload coordination."""

    agent_maturity_cache: Dict[str, str]
    net_file_path: Optional[str]

    def try_restore_state(self) -> None: ...

    def handle_new_map(self, map_path: str, maps_output_dir: str, telemetry_aggregator: Any) -> None: ...


@runtime_checkable
class IFailsafeManager(Protocol):
    """Contract for autonomous failsafe timeout monitoring and activation."""

    def set_failsafe_timeout(self, timeout_seconds: float) -> None: ...

    def record_frame_received(self) -> None: ...

    def check_silence_timeout(self) -> bool: ...


@runtime_checkable
class IOverrideManager(Protocol):
    """Contract for operator manual overrides and scheduled flashing yellow overrides."""

    def set_override(self, tls_id: str, mode: str, stage_index: Optional[int] = None) -> None: ...

    def clear_override(self, tls_id: str) -> None: ...

    def get_override(self, tls_id: str) -> Optional[Dict[str, Any]]: ...


@runtime_checkable
class IHealthMonitor(Protocol):
    """Contract for AI process heartbeat health monitoring."""

    def record_heartbeat(self) -> None: ...

    def is_healthy(self) -> bool: ...


@runtime_checkable
class ITelemetryAggregator(Protocol):
    """Contract for visual heatmap telemetry aggregation."""

    def reset(self) -> None: ...


@runtime_checkable
class ITrafficFrameProcessor(Protocol):
    """Contract for processing incoming HFT TrafficFrame telemetry streams."""

    def set_system_ready(self, ready: bool) -> None: ...

    def process_frame(self, frame: Any) -> Any: ...


@runtime_checkable
class IRequestProcessor(Protocol):
    """Contract for processing IPC requests from the AI Engine and UI."""

    def set_readiness_callbacks(
        self, on_ui_ready: Callable[[], None], on_backend_ready: Callable[[], None]
    ) -> None: ...

    def process_ai_message(self, msg: Any) -> bool: ...

    def process_ui_commands(self) -> None: ...


@runtime_checkable
class IYellowScheduleManager(Protocol):
    """Contract for scheduled nighttime yellow flashing evaluation."""

    def evaluate_schedule(self, known_tls_ids: Any = None) -> None: ...

    def update_schedule(self, config: Dict[str, Any]) -> None: ...


@runtime_checkable
class IHardwareSnapshotProvider(Protocol):
    """Segregated read-only contract for cached hardware telemetry, status, and EVP snapshots."""

    def refresh_snapshots(
        self, push_to_sds: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]: ...

    def get_cached_frame_attachments(self) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]: ...

    def get_cached_hardware_status(self) -> Dict[str, Dict[str, Any]]: ...


@runtime_checkable
class IFailsafeHardwareHook(Protocol):
    """Segregated contract for emergency hardware release and Watchdog recovery hooks."""

    def on_failsafe_triggered(self) -> None: ...

    def on_failsafe_recovered(self) -> None: ...


@runtime_checkable
class IAIHardwareCommandDispatcher(Protocol):
    """Segregated contract for asynchronous execution of AI-originated hardware and EVP commands."""

    def submit_task(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any: ...

    def execute_ai_hardware_cmd(self, payload: Dict[str, Any]) -> bool: ...

    def execute_ai_evp_preempt(self, payload: Dict[str, Any]) -> bool: ...


@runtime_checkable
class IFenixReconciliationDispatcher(Protocol):
    """Segregated contract for F.E.N.I.X. post-resurrection stage reconciliation."""

    def dispatch_fenix_reconcile_stages(self, ai_pipe_conn: Optional[Any] = None) -> Dict[str, int]: ...

    def handle_fenix_handover_complete(self, payload: Optional[Dict[str, Any]] = None) -> bool: ...


@runtime_checkable
class IAdminGatewayCommands(Protocol):
    """Segregated contract for UI/administrator hardware, CSV, EVP, Tailscale, and override commands."""

    def submit_task(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any: ...

    def toggle_hardware_connection(
        self,
        intersection_id: str,
        ip_address: Optional[str] = None,
        action: str = "toggle",
        snmp_config: Optional[Dict[str, Any]] = None,
    ) -> bool: ...

    def sync_hardware_csv(self, payload: Dict[str, Any]) -> Tuple[int, int]: ...

    def set_evp_fleet(self, payload: Dict[str, Any]) -> bool: ...

    def handle_tailscale_command(self, cmd_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: ...

    def sync_override_to_hardware(self, target_tls: List[str], mode: str) -> None: ...


@runtime_checkable
class ITailscaleGatewayAdapter(Protocol):
    """Infrastructure port for Tailscale Funnel CLI and Go gateway RPC operations."""

    def execute(self, cmd_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: ...


@runtime_checkable
class IRemoteGatewayBackend(Protocol):
    """Port abstracting Tailscale domain discovery and Go remote web gateway lifecycle for UI controllers."""

    def detect_domain(self) -> str: ...

    def is_remote_role(self) -> bool: ...

    def test_connection(self) -> Tuple[bool, str, str]: ...

    def enable_gateway(self, port: int = 2201) -> Tuple[bool, str, str]: ...

    def disable_gateway(self) -> None: ...

    def get_status(self) -> Dict[str, Any]: ...

    def sync_enabled_state(self, enabled: bool) -> None: ...


@runtime_checkable
class IGatewaySettingsPersister(Protocol):
    """Port for persisting remote gateway settings across UI config, INI, environment, and backend."""

    def persist(self, gateway_enabled: bool, backend: Optional[IRemoteGatewayBackend] = None) -> None: ...


@runtime_checkable
class IHardwareGatewayCoordinator(
    IHardwareSnapshotProvider,
    IFailsafeHardwareHook,
    IAIHardwareCommandDispatcher,
    IFenixReconciliationDispatcher,
    IAdminGatewayCommands,
    Protocol,
):
    """Composite lifecycle facade contract for the gateway-owner coordinator."""

    def start(self) -> None: ...

    def stop(self) -> None: ...


__all__ = [
    "ITopologyCoordinator",
    "IFailsafeManager",
    "IOverrideManager",
    "IHealthMonitor",
    "ITelemetryAggregator",
    "ITrafficFrameProcessor",
    "IRequestProcessor",
    "IYellowScheduleManager",
    "IHardwareSnapshotProvider",
    "IFailsafeHardwareHook",
    "IAIHardwareCommandDispatcher",
    "IFenixReconciliationDispatcher",
    "IAdminGatewayCommands",
    "ITailscaleGatewayAdapter",
    "IRemoteGatewayBackend",
    "IGatewaySettingsPersister",
    "IHardwareGatewayCoordinator",
]
