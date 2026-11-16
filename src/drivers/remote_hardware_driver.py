# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
IPC proxy implementing both BaseTrafficDriver and the TrafficLightDriver duck-typed
contract for worker processes running in remote gateway role (e.g., AI_Process).

Instead of spawning local Go gateway subprocesses or holding local UDP SNMP sockets,
this proxy forwards hardware commands asynchronously to the gateway owner
(CentralController) over the multiprocessing Pipe as 2-element tuples and mirrors
real hardware telemetry pushed downstream.
"""

import logging
import threading
from typing import Any, Dict, List, Optional

try:
    from src.drivers.base_driver import BaseTrafficDriver
    from src.drivers.traffic_color_logger import TrafficColorLogger
    from src.drivers.traffic_map_loader import TrafficMapLoader
except ImportError:  # pragma: no cover - fallback when running with src/ directly on sys.path
    from drivers.base_driver import BaseTrafficDriver
    from drivers.traffic_color_logger import TrafficColorLogger
    from drivers.traffic_map_loader import TrafficMapLoader

logger = logging.getLogger(__name__)


class RemoteHardwareDriverProxy(BaseTrafficDriver):
    """
    Lightweight proxy placed in HardwareConnectionManager.active_connections when
    the process runs with CARINA_GATEWAY_ROLE=remote.
    """

    def __init__(
        self,
        intersection_id: str,
        ip_address: str = "",
        port: int = 161,
        community_string: str = "public",
        protocol_name: str = "RemoteGatewayIPC",
        brand: str = "Não informado",
        model: str = "Não informado",
        is_connected: bool = True,
        green_stages: Optional[List[int]] = None,
        stage_codes: Optional[Dict[int, str]] = None,
        pipe_conn: Optional[Any] = None,
        locale_manager: Any = None,
    ) -> None:
        self._init_base_attrs(
            intersection_id=intersection_id,
            ip_address=ip_address,
            port=port,
            community_string=community_string,
            green_stages=green_stages,
        )
        # Skip python-side heartbeat thread spawned by BaseTrafficDriver.__init__
        if hasattr(self, "heartbeat_manager"):
            try:
                self.heartbeat_manager.stop()
            except Exception:
                pass

        self.protocol_name = str(protocol_name or "RemoteGatewayIPC")
        self.brand = str(brand or "Não informado")
        self.model = str(model or "Não informado")
        self.is_connected = bool(is_connected)
        self.stage_codes: Dict[int, str] = dict(stage_codes or {})
        self.stage_states: Dict[int, str] = dict(self.stage_codes)
        self.pipe_conn = pipe_conn
        self.locale_manager = locale_manager
        self.hardware_driver = self
        self._lock = threading.Lock()
        self.last_telemetry: Dict[str, Any] = {
            "intersection_id": self.intersection_id,
            "status": "online" if self.is_connected else "offline",
            "protocol": self.protocol_name,
            "brand": self.brand,
            "model": self.model,
        }

    def _init_base_attrs(
        self,
        intersection_id: str,
        ip_address: str,
        port: int,
        community_string: str,
        green_stages: Optional[List[int]],
    ) -> None:
        super().__init__(
            ip_address=ip_address,
            port=port,
            intersection_id=intersection_id,
            community_string=community_string,
            green_stages=green_stages,
        )

    def set_pipe_conn(self, pipe_conn: Optional[Any]) -> None:
        """Updates the IPC pipe handle used to dispatch commands to CentralController."""
        with self._lock:
            self.pipe_conn = pipe_conn

    def update_from_status(self, info: Dict[str, Any]) -> None:
        """Synchronizes metadata and connectivity state from a CentralController status snapshot."""
        if not isinstance(info, dict):
            return
        with self._lock:
            if "is_connected" in info:
                self.is_connected = bool(info["is_connected"])
            if info.get("ip_address"):
                self.ip_address = str(info["ip_address"])
            if info.get("brand"):
                self.brand = str(info["brand"])
            if info.get("model"):
                self.model = str(info["model"])
            if info.get("protocol"):
                self.protocol_name = str(info["protocol"])
            if isinstance(info.get("green_stages"), (list, tuple)):
                self.green_stages = [int(x) for x in info["green_stages"]]
            if isinstance(info.get("stage_codes"), dict):
                self.stage_codes = {int(k): str(v) for k, v in info["stage_codes"].items()}
                self.stage_states = dict(self.stage_codes)

            self.last_telemetry["intersection_id"] = self.intersection_id
            self.last_telemetry["status"] = "online" if self.is_connected else "offline"
            self.last_telemetry["protocol"] = self.protocol_name
            self.last_telemetry["brand"] = self.brand
            self.last_telemetry["model"] = self.model

    def update_telemetry(self, telemetry: Dict[str, Any]) -> None:
        """Caches the latest field telemetry snapshot pushed from CentralController."""
        if not isinstance(telemetry, dict):
            return
        with self._lock:
            merged = dict(self.last_telemetry)
            merged.update(telemetry)
            merged["intersection_id"] = self.intersection_id
            if not merged.get("brand") and self.brand:
                merged["brand"] = self.brand
            if not merged.get("model") and self.model:
                merged["model"] = self.model
            if not merged.get("protocol") and self.protocol_name:
                merged["protocol"] = self.protocol_name
            self.last_telemetry = merged

    def _dispatch_command(self, cmd: str, **payload_fields: Any) -> bool:
        with self._lock:
            conn = self.pipe_conn
            connected = self.is_connected
        if not connected and cmd != "release_control":
            return False
        if conn is None or getattr(conn, "closed", False):
            return False

        payload: Dict[str, Any] = {
            "cmd": cmd,
            "intersection_id": self.intersection_id,
        }
        payload.update(payload_fields)
        try:
            conn.send(("ai_hardware_cmd", payload))
            return True
        except Exception as exc:
            logger.debug(f"[RemoteHardwareDriverProxy:{self.intersection_id}] IPC send '{cmd}' failed: {exc}")
            return False

    # --- BaseTrafficDriver Contract ---

    def get_protocol_name(self) -> str:
        return self.protocol_name

    def send_action(self, action_data: Dict[str, Any]) -> bool:
        return self._dispatch_command(
            "apply_action",
            action_data=dict(action_data or {}),
        )

    def apply_action(self, action_data: Dict[str, Any]) -> bool:
        """TrafficLightDriver-compatible alias used by ActionSupervisor.send_stage_hold."""
        return self.send_action(action_data)

    def apply_logical_action(
        self,
        action: int,
        current_stage_idx: int,
        green_stages: List[int],
        stage_codes: Optional[Dict[int, str]] = None,
    ) -> bool:
        resolved_greens = list(green_stages) if green_stages else list(self.green_stages or [])
        resolved_codes = dict(stage_codes) if stage_codes else dict(self.stage_codes or {})
        return self._dispatch_command(
            "apply_logical_action",
            action=int(action),
            current_stage_idx=int(current_stage_idx),
            green_stages=resolved_greens,
            stage_codes=resolved_codes,
        )

    def apply_decision(self, action: str) -> bool:
        return self._dispatch_command(
            "apply_decision",
            action=str(action),
        )

    def get_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.last_telemetry)

    def get_status(self) -> Dict[str, Any]:
        """TrafficLightDriver-compatible telemetry accessor."""
        with self._lock:
            if not self.is_connected:
                return {
                    "intersection_id": self.intersection_id,
                    "status": "offline",
                    "protocol": "none",
                    "brand": "Desconectado",
                    "model": "Desconectado",
                    "active_greens": 0,
                    "active_yellows": 0,
                    "active_reds": 0,
                    "active_ped_calls": 0,
                }
            return dict(self.last_telemetry)

    def send_heartbeat_pulse(self) -> bool:
        return bool(self.is_connected)

    def start_heartbeat(self) -> None:
        pass

    def stop_heartbeat(self) -> None:
        pass

    def release_control(self) -> bool:
        return self._dispatch_command("release_control")

    # --- TrafficLightDriver Helper Compatibility ---

    def log_carina_colors(self, current_stage_idx: int, stage_codes: Optional[Dict[int, str]] = None) -> None:
        if not self.stage_states:
            try:
                self.stage_states = TrafficMapLoader.load_stage_states(
                    self.intersection_id, locale_manager=self.locale_manager
                )
            except Exception:
                self.stage_states = {}
        active_states = self.stage_states if self.stage_states else (stage_codes or {})
        TrafficColorLogger.log_stage(
            intersection_id=self.intersection_id,
            current_stage_idx=current_stage_idx,
            active_states=active_states,
            locale_manager=self.locale_manager,
        )

    def log_carina_override(self, override_type: str) -> None:
        TrafficColorLogger.log_override(
            intersection_id=self.intersection_id,
            override_type=override_type,
            locale_manager=self.locale_manager,
        )

    def shutdown(self) -> None:
        with self._lock:
            self.is_connected = False
            self.last_telemetry["status"] = "offline"


def sync_remote_driver_proxies(
    conn_mgr: Any,
    hardware_status: Dict[str, Dict[str, Any]],
    pipe_conn: Optional[Any] = None,
    state_extractor: Any = None,
    prune_missing: bool = False,
) -> List[str]:
    """Backwards-compatible delegate forwarding to `remote_proxy_synchronizer.sync_remote_driver_proxies`."""
    try:
        from src.drivers.remote_proxy_synchronizer import sync_remote_driver_proxies as _sync
    except ImportError:  # pragma: no cover
        from drivers.remote_proxy_synchronizer import sync_remote_driver_proxies as _sync
    return _sync(
        conn_mgr=conn_mgr,
        hardware_status=hardware_status,
        pipe_conn=pipe_conn,
        state_extractor=state_extractor,
        prune_missing=prune_missing,
    )
