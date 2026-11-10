# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Controller Layer Protocols (SOLID: ISP & DIP).
Defines narrow contracts for CentralController collaborators.
"""

from typing import Any, Callable, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class ITopologyCoordinator(Protocol):
    """Contract for CentralController topology restoration and map reload coordination."""

    agent_maturity_cache: Dict[str, str]
    net_file_path: Optional[str]

    def try_restore_state(self) -> None:
        ...

    def handle_new_map(self, map_path: str, maps_output_dir: str, telemetry_aggregator: Any) -> None:
        ...


@runtime_checkable
class IFailsafeManager(Protocol):
    """Contract for autonomous failsafe timeout monitoring and activation."""

    def set_failsafe_timeout(self, timeout_seconds: float) -> None:
        ...

    def record_frame_received(self) -> None:
        ...

    def check_silence_timeout(self) -> bool:
        ...


@runtime_checkable
class IOverrideManager(Protocol):
    """Contract for operator manual overrides and scheduled flashing yellow overrides."""

    def set_override(self, tls_id: str, mode: str, stage_index: Optional[int] = None) -> None:
        ...

    def clear_override(self, tls_id: str) -> None:
        ...

    def get_override(self, tls_id: str) -> Optional[Dict[str, Any]]:
        ...


@runtime_checkable
class IHealthMonitor(Protocol):
    """Contract for AI process heartbeat health monitoring."""

    def record_heartbeat(self) -> None:
        ...

    def is_healthy(self) -> bool:
        ...


@runtime_checkable
class ITelemetryAggregator(Protocol):
    """Contract for visual heatmap telemetry aggregation."""

    def reset(self) -> None:
        ...


@runtime_checkable
class ITrafficFrameProcessor(Protocol):
    """Contract for processing incoming HFT TrafficFrame telemetry streams."""

    def set_system_ready(self, ready: bool) -> None:
        ...

    def process_frame(self, frame: Any) -> Any:
        ...


@runtime_checkable
class IRequestProcessor(Protocol):
    """Contract for processing IPC requests from the AI Engine and UI."""

    def set_readiness_callbacks(self, on_ui_ready: Callable[[], None], on_backend_ready: Callable[[], None]) -> None:
        ...

    def process_ai_message(self, msg: Any) -> bool:
        ...

    def process_ui_commands(self) -> None:
        ...


@runtime_checkable
class IYellowScheduleManager(Protocol):
    """Contract for scheduled nighttime yellow flashing evaluation."""

    def evaluate_schedule(self, known_tls_ids: Any = None) -> None:
        ...

    def update_schedule(self, config: Dict[str, Any]) -> None:
        ...


__all__ = [
    "ITopologyCoordinator",
    "IFailsafeManager",
    "IOverrideManager",
    "IHealthMonitor",
    "ITelemetryAggregator",
    "ITrafficFrameProcessor",
    "IRequestProcessor",
    "IYellowScheduleManager",
]
