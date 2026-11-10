# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
High-performance IPC Client bridging CARINA Python core with the compiled Go Hardware Gateway.
Acts as a unified Facade coordinating process supervision, pipe transport, and event dispatching.
"""

import logging
import os
import threading
from typing import Any, Callable, Dict, Optional

from src.drivers.go_event_dispatcher import GoEventDispatcher
from src.drivers.go_pipe_transport import GoPipeTransport
from src.drivers.go_process_manager import GoProcessManager
from src.utils.paths import resource_path

logger = logging.getLogger(__name__)


class GoGatewayClient:
    """
    Facade managing the Go hardware gateway client lifecycle and command dispatch.
    Delegates process management, pipe communication, and event routing (SRP).
    """

    _instance: Optional["GoGatewayClient"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls, binary_path: Optional[str] = None) -> "GoGatewayClient":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(binary_path=binary_path)
            return cls._instance

    def __init__(self, binary_path: Optional[str] = None) -> None:
        if binary_path is None:
            binary_path = resource_path(os.path.join("bin", "carina-go"))

        self.binary_path = binary_path
        self.process_manager = GoProcessManager(binary_path=self.binary_path)
        self.event_dispatcher = GoEventDispatcher()
        self.transport = GoPipeTransport(on_event_received=self.event_dispatcher.dispatch)
        self._start_lock = threading.Lock()

    @property
    def process(self):
        """Backward compatibility for direct process inspection."""
        return self.process_manager.process

    def is_running(self) -> bool:
        """Checks whether the Go gateway is running via subprocess pipes."""
        return self.transport.is_connected(self.process_manager.process)

    def start(self) -> bool:
        """Starts the Go gateway client via anonymous OS pipes (stdin/stdout)."""
        with self._start_lock:
            if self.is_running():
                return True

            # Spawn Go binary with anonymous OS pipes (stdin/stdout)
            if not self.process_manager.start():
                return False

            if self.process_manager.process is not None:
                self.transport.start_stdout_reader(self.process_manager.process)

            if self.ping(timeout=3.0):
                logger.info("[GoGatewayClient] ✅ Go Hardware Gateway connected successfully via stdin/stdout.")
                return True
            else:
                logger.error("[GoGatewayClient] Go Hardware Gateway ping failed on startup.")
                self.stop()
                return False

    def stop(self) -> None:
        """Stops the Go gateway client and cleans up pipe/process resources."""

        def _pre_stop():
            try:
                self.transport.send_raw(self.process_manager.process, {"id": 0, "cmd": "emergency_release"})
            except Exception as _exc:
                logger.debug("[drivers] Ignored recoverable error: %s", _exc)

        self.transport.stop()
        if self.process_manager.is_running():
            self.process_manager.stop(pre_stop_hook=_pre_stop)

    def register_ui_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Registers a callback for UI updates upon receiving field traps/alarms."""
        self.event_dispatcher.register_ui_callback(callback)

    def send_command(self, cmd: str, timeout: float = 3.0, **kwargs) -> Dict[str, Any]:
        """Sends a synchronous command over stdin and waits for its response on stdout."""
        if not self.is_running():
            if not self.start():
                return {"success": False, "error": "Gateway Go não está ativo"}

        return self.transport.send_command(
            self.process_manager.process,
            cmd=cmd,
            timeout=timeout,
            **kwargs,
        )

    # =========================================================================
    # High-Level Traffic Driver APIs
    # =========================================================================

    def ping(self, timeout: float = 2.0) -> bool:
        res = self.send_command("ping", timeout=timeout)
        return bool(res.get("success", False))

    def connect_intersection(
        self,
        intersection_id: str,
        ip: str,
        port: int = 161,
        community: str = "public",
        protocol: str = "auto",
        green_stages: Optional[list] = None,
        config_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Connects an intersection to the Go gateway."""
        payload: Dict[str, Any] = {
            "intersection_id": intersection_id,
            "ip": ip,
            "port": port,
            "community": community,
            "protocol": protocol,
            "green_stages": green_stages or [],
        }
        if config_path:
            payload["config_path"] = config_path

        return self.send_command("connect", timeout=5.0, **payload)

    def disconnect_intersection(self, intersection_id: str) -> bool:
        """Disconnects an intersection from the Go gateway."""
        res = self.send_command("disconnect", timeout=3.0, intersection_id=intersection_id)
        if not res.get("success", False):
            alt_id = intersection_id[3:] if str(intersection_id).startswith("tl_") else f"tl_{intersection_id}"
            res = self.send_command("disconnect", timeout=3.0, intersection_id=alt_id)
        return bool(res.get("success", False))

    def apply_decision(self, intersection_id: str, decision: str) -> bool:
        """Sends the pure neural network decision ('HOLD' or 'ADVANCE') to the Go gateway."""
        res = self.send_command(
            "decision",
            timeout=2.0,
            intersection_id=intersection_id,
            decision=decision,
        )
        return bool(res.get("success", False))

    def apply_action(self, intersection_id: str, action_data: Dict[str, Any]) -> bool:
        """Sends an action dict (hold, force_off, flash, dark, etc.) to the Go gateway."""
        res = self.send_command(
            "apply_action",
            timeout=2.0,
            intersection_id=intersection_id,
            action_data=action_data,
        )
        return bool(res.get("success", False))

    def apply_logical_action(
        self,
        intersection_id: str,
        action: int,
        current_stage_idx: int,
        green_stages: list,
        stage_codes: Optional[Dict[int, str]] = None,
    ) -> bool:
        """Sends logical action (0 = NEXT_STAGE, 1 = HOLD) to the Go gateway."""
        res = self.send_command(
            "apply_logical_action",
            timeout=2.0,
            intersection_id=intersection_id,
            action=action,
            current_stage_idx=current_stage_idx,
            green_stages=green_stages,
            stage_codes=stage_codes or {},
        )
        return bool(res.get("success", False))

    def get_telemetry(self, intersection_id: str) -> Dict[str, Any]:
        """Queries telemetry from the Go gateway."""
        res = self.send_command("get_telemetry", timeout=2.0, intersection_id=intersection_id)
        if res.get("success", False) and "telemetry" in res:
            return res["telemetry"]
        return {
            "intersection_id": intersection_id,
            "status": "offline",
            "protocol": "none",
            "brand": "Não informado",
            "model": "Não informado",
            "active_greens": 0,
            "active_yellows": 0,
            "active_reds": 0,
            "active_ped_calls": 0,
        }

    def emergency_release_all(self) -> bool:
        """Signals the Go gateway to release control on all active intersections."""
        res = self.send_command("emergency_release", timeout=3.0)
        return bool(res.get("success", False))

    def broadcast_cco(self, data: Dict[str, Any]) -> None:
        """Sends fire-and-forget CCO broadcast without waiting on stdout response."""
        if not self.is_running():
            return
        try:
            self.transport.send_raw(self.process_manager.process, {"id": 0, "cmd": "cco_broadcast", "data": data})
        except Exception as e:
            logger.debug(f"[GoGatewayClient] Falha ao enviar broadcast_cco assíncrono: {e}")
