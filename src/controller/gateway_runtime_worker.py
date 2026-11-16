# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Runtime worker managing background command execution, periodic telemetry polling,
event-to-SDS forwarding, and lock-free frame attachment caches.
"""

import logging
import queue
import threading
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class GatewayRuntimeWorker:
    """Owns non-blocking command/polling threads and snapshot caches for HardwareGatewayCoordinator."""

    def __init__(
        self,
        sds_data_queue: Optional[Any] = None,
        conn_mgr_provider: Optional[Callable[[bool], Optional[Any]]] = None,
        evp_service_provider: Optional[Callable[[bool], Optional[Any]]] = None,
        poll_interval_seconds: float = 0.25,
    ) -> None:
        self.sds_data_queue = sds_data_queue
        self._conn_mgr_provider = conn_mgr_provider
        self._evp_service_provider = evp_service_provider
        self.poll_interval_seconds = float(poll_interval_seconds)

        self._state_lock = threading.Lock()
        self._cached_tls_telemetry: Dict[str, Dict[str, Any]] = {}
        self._cached_hardware_status: Dict[str, Dict[str, Any]] = {}
        self._cached_evp_state: Optional[Dict[str, Any]] = None
        self._last_pushed_hw_status: Optional[Dict[str, Dict[str, Any]]] = None

        self._cmd_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._cmd_thread: Optional[threading.Thread] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._started = False

    @property
    def is_started(self) -> bool:
        return self._started

    @is_started.setter
    def is_started(self, value: bool) -> None:
        self._started = bool(value)

    def start(self) -> None:
        """Starts background command worker and telemetry polling threads."""
        if self._started:
            return
        self._started = True
        self._stop_event.clear()

        self._cmd_thread = threading.Thread(
            target=self._command_worker_loop,
            daemon=True,
            name="HardwareGatewayCmdWorker",
        )
        self._poll_thread = threading.Thread(
            target=self._telemetry_poll_loop,
            daemon=True,
            name="HardwareGatewayPollWorker",
        )
        self._cmd_thread.start()
        self._poll_thread.start()
        self.refresh_snapshots(push_to_sds=True)

    def stop(self) -> None:
        """Stops background threads cleanly."""
        self._stop_event.set()
        try:
            self._cmd_queue.put_nowait(None)
        except Exception:
            pass

        for thread in (self._cmd_thread, self._poll_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=1.0)

        self._started = False

    def submit_task(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Queues work on the background worker when running, or runs synchronously when stopped."""
        if self._started and self._cmd_thread is not None and self._cmd_thread.is_alive():
            self._cmd_queue.put((fn, args, kwargs))
            return True
        return fn(*args, **kwargs)

    # --- Event Routing to SDS ---

    def push_sds_event(self, event_tuple: Tuple[str, Any]) -> None:
        """Enqueues a runtime event tuple onto sds_data_queue without blocking."""
        if self.sds_data_queue is None:
            return
        try:
            self.sds_data_queue.put_nowait(event_tuple)
        except queue.Full:
            pass
        except Exception as exc:
            logger.debug(f"[GatewayRuntimeWorker] SDS queue push failed: {exc}")

    def on_hardware_trap(self, event_data: Dict[str, Any]) -> None:
        """Forwards hardware SNMP trap notifications to SDS."""
        if isinstance(event_data, dict):
            self.push_sds_event(("hardware_trap", dict(event_data)))

    def on_go_event(self, event_data: Dict[str, Any]) -> None:
        """Routes unsolicited events arriving from the Go gateway stdout pipe."""
        if not isinstance(event_data, dict):
            return
        evt_type = str(event_data.get("event", "")).lower()
        if evt_type in ("evp_telemetry", "evp_vehicle"):
            payload = event_data.get("data") or event_data
            if isinstance(payload, dict):
                self.push_sds_event(("evp_telemetry", dict(payload)))
            return
        self.push_sds_event(("hardware_trap", dict(event_data)))

    def on_evp_vehicle_update(self, vehicle_data: Dict[str, Any]) -> None:
        """Routes EVPNotifier updates onto SDS."""
        if isinstance(vehicle_data, dict):
            self.push_sds_event(("evp_telemetry", dict(vehicle_data)))

    # --- Thread Loops ---

    def _command_worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._cmd_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None:
                break
            fn, args, kwargs = item
            try:
                fn(*args, **kwargs)
            except Exception as exc:
                logger.error(f"[GatewayRuntimeWorker] Async command error: {exc}", exc_info=True)

    def _telemetry_poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.refresh_snapshots(push_to_sds=True)
            except Exception as exc:
                logger.debug(f"[GatewayRuntimeWorker] Telemetry poll error: {exc}")
            self._stop_event.wait(timeout=self.poll_interval_seconds)

    # --- Snapshots & Frame Attachments ---

    def refresh_snapshots(
        self, push_to_sds: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]:
        """Collects telemetry, hardware connection snapshot, and EVP state into cached dictionaries."""
        conn_mgr = self._conn_mgr_provider(False) if self._conn_mgr_provider else None
        evp_svc = self._evp_service_provider(False) if self._evp_service_provider else None

        tls_telemetry, hardware_status = self._collect_hardware_snapshots(conn_mgr)
        evp_state = self._collect_evp_snapshot(evp_svc)

        should_push_hw = False
        with self._state_lock:
            self._cached_tls_telemetry = tls_telemetry
            self._cached_hardware_status = hardware_status
            self._cached_evp_state = evp_state
            if push_to_sds and hardware_status != self._last_pushed_hw_status:
                self._last_pushed_hw_status = {k: dict(v) for k, v in hardware_status.items()}
                should_push_hw = True

        if should_push_hw:
            self.push_sds_event(("hardware_status_update", hardware_status))

        return tls_telemetry, hardware_status, evp_state

    @staticmethod
    def _collect_hardware_snapshots(
        conn_mgr: Optional[Any],
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        tls_telemetry: Dict[str, Dict[str, Any]] = {}
        hardware_status: Dict[str, Dict[str, Any]] = {}
        if conn_mgr is None:
            return tls_telemetry, hardware_status

        active_conns = getattr(conn_mgr, "active_connections", None)
        if isinstance(active_conns, dict):
            for tl_id, driver in list(active_conns.items()):
                if not getattr(driver, "is_connected", False) or not hasattr(driver, "get_status"):
                    continue
                try:
                    status_data = driver.get_status()
                    if isinstance(status_data, dict):
                        tls_telemetry[str(tl_id)] = dict(status_data)
                except Exception as exc:
                    logger.debug(f"[GatewayRuntimeWorker] Telemetry read failed for {tl_id}: {exc}")

        if hasattr(conn_mgr, "export_hardware_status_snapshot"):
            try:
                raw_snapshot = conn_mgr.export_hardware_status_snapshot()
                if isinstance(raw_snapshot, dict):
                    hardware_status = {str(k): dict(v) for k, v in raw_snapshot.items() if isinstance(v, dict)}
            except Exception as exc:
                logger.debug(f"[GatewayRuntimeWorker] Snapshot export failed: {exc}")

        return tls_telemetry, hardware_status

    @staticmethod
    def _collect_evp_snapshot(evp_svc: Optional[Any]) -> Optional[Dict[str, Any]]:
        if evp_svc is None or not hasattr(evp_svc, "export_remote_snapshot"):
            return None
        try:
            raw_evp = evp_svc.export_remote_snapshot()
            return raw_evp if isinstance(raw_evp, dict) else None
        except Exception as exc:
            logger.debug(f"[GatewayRuntimeWorker] EVP snapshot export failed: {exc}")
            return None

    def get_cached_frame_attachments(self) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]:
        """Returns cached (tls_telemetry, hardware_status, evp_state) without performing hardware I/O."""
        with self._state_lock:
            tls_copy = {k: dict(v) for k, v in self._cached_tls_telemetry.items()}
            hw_copy = {k: dict(v) for k, v in self._cached_hardware_status.items()}
            evp_copy = (
                {
                    "vehicles": dict(self._cached_evp_state.get("vehicles", {})),
                    "active_preemptions": dict(self._cached_evp_state.get("active_preemptions", {})),
                }
                if isinstance(self._cached_evp_state, dict)
                else None
            )
        return tls_copy, hw_copy, evp_copy

    def get_cached_hardware_status(self) -> Dict[str, Dict[str, Any]]:
        """Returns a shallow copy of cached hardware connection status."""
        with self._state_lock:
            return {k: dict(v) for k, v in self._cached_hardware_status.items()}
