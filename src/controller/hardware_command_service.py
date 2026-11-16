# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Facade service orchestrating hardware connection toggles, CSV sync, EVP fleet commands,
manual/AI hardware overrides, and Watchdog failsafe hooks via dedicated collaborators.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from src.controller.connection_config_repo import ConnectionConfigRepository
    from src.controller.evp_fleet_command_handler import EvpFleetCommandHandler
    from src.controller.hardware_override_dispatcher import HardwareOverrideDispatcher
except ImportError:  # pragma: no cover
    from controller.connection_config_repo import ConnectionConfigRepository
    from controller.evp_fleet_command_handler import EvpFleetCommandHandler
    from controller.hardware_override_dispatcher import HardwareOverrideDispatcher

logger = logging.getLogger(__name__)


class HardwareCommandService:
    """Executes operational hardware, override, EVP, and failsafe commands against owner drivers."""

    def __init__(
        self,
        conn_mgr_provider: Callable[[bool], Optional[Any]],
        go_client_provider: Callable[[bool], Optional[Any]],
        evp_service_provider: Callable[[bool], Optional[Any]],
        refresh_snapshots: Callable[[bool], Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]],
        push_sds_event: Callable[[Tuple[str, Any]], None],
        ai_pipe_provider: Optional[Callable[[], Optional[Any]]] = None,
        locale_manager: Optional[Any] = None,
        config_repo: Any = ConnectionConfigRepository,
    ) -> None:
        self._conn_mgr_provider = conn_mgr_provider
        self._refresh_snapshots = refresh_snapshots
        self._push_sds_event = push_sds_event
        self._ai_pipe_provider = ai_pipe_provider
        self.locale_manager = locale_manager
        self._config_repo = config_repo

        self._evp_handler = EvpFleetCommandHandler(
            evp_service_provider=evp_service_provider,
            go_client_provider=go_client_provider,
            refresh_snapshots=refresh_snapshots,
        )
        self._override_dispatcher = HardwareOverrideDispatcher(
            conn_mgr_provider=conn_mgr_provider,
            go_client_provider=go_client_provider,
        )
        self._active_overrides = self._override_dispatcher._active_overrides

    @staticmethod
    def resolve_active_driver(active_conns: Any, tl_id: str) -> Optional[Any]:
        """Resolves a driver entry from active_connections across tl_-prefixed/unprefixed variants."""
        return HardwareOverrideDispatcher.resolve_active_driver(active_conns, tl_id)

    def toggle_hardware_connection(
        self,
        intersection_id: str,
        ip_address: Optional[str] = None,
        action: str = "toggle",
        snmp_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Executes connect/disconnect/toggle locally and syncs snapshot state to SDS and AI."""
        conn_mgr = self._conn_mgr_provider(True)
        if conn_mgr is None:
            return False

        kwargs: Dict[str, Any] = {
            "intersection_id": intersection_id,
            "ip_address": ip_address,
            "action": action,
            "save_to_db": True,
        }
        if snmp_config is not None:
            kwargs["snmp_config"] = snmp_config

        result = bool(conn_mgr.toggle_connection(**kwargs))
        _, hw_status, _ = self._refresh_snapshots(True)
        self._push_sds_event(("hardware_status_update", hw_status))
        self._notify_ai_toggle(intersection_id, ip_address, action, hw_status)
        return result

    def _notify_ai_toggle(
        self,
        intersection_id: str,
        ip_address: Optional[str],
        action: str,
        hw_status: Dict[str, Dict[str, Any]],
    ) -> None:
        pipe = self._ai_pipe_provider() if self._ai_pipe_provider is not None else None
        if pipe is None or getattr(pipe, "closed", False):
            return
        try:
            pipe.send(
                (
                    "hardware",
                    "toggle_connection",
                    (intersection_id, ip_address, action),
                    {"hardware_status": hw_status},
                )
            )
        except Exception as exc:
            logger.debug(f"[HardwareCommandService] AI hardware sync notify skipped: {exc}")

    def sync_hardware_csv(self, payload: Dict[str, Any]) -> Tuple[int, int]:
        """Applies imported hardware CSV entries (or filepath) on owner HardwareConnectionManager."""
        conn_mgr = self._conn_mgr_provider(True)
        if conn_mgr is None:
            return 0, 0

        entries = payload.get("entries")
        filepath = payload.get("filepath")
        save_to_db = bool(payload.get("save_to_db", True))

        if isinstance(entries, dict):
            return self._sync_csv_entries(conn_mgr, entries, save_to_db=save_to_db)

        if filepath and hasattr(conn_mgr, "import_csv_config"):
            ok_cnt, err_cnt = conn_mgr.import_csv_config(str(filepath), save_to_db=save_to_db)
            _, hw_status, _ = self._refresh_snapshots(True)
            self._push_sds_event(("hardware_status_update", hw_status))
            return ok_cnt, err_cnt

        return 0, 0

    def _sync_csv_entries(self, conn_mgr: Any, entries: Dict[str, Any], save_to_db: bool) -> Tuple[int, int]:
        success_count = 0
        fail_count = 0
        for tl_id, entry in entries.items():
            if not isinstance(entry, dict):
                continue
            ip = str(entry.get("ip", "")).strip()
            if not ip:
                continue
            snmp_cfg = entry.get("snmp_config")
            if snmp_cfg and hasattr(conn_mgr, "saved_snmp_configs"):
                conn_mgr.saved_snmp_configs[tl_id] = dict(snmp_cfg)
            if save_to_db and self._config_repo is not None:
                self._config_repo.save_connection_db(
                    tl_id,
                    ip,
                    locale_manager=self.locale_manager,
                    snmp_config=snmp_cfg,
                )
            conn_mgr.saved_ips[tl_id] = ip
            if self.toggle_hardware_connection(
                intersection_id=tl_id,
                ip_address=ip,
                action="connect",
                snmp_config=snmp_cfg,
            ):
                success_count += 1
            else:
                fail_count += 1
        return success_count, fail_count

    def set_evp_fleet(self, payload: Dict[str, Any]) -> bool:
        """Delegates EVP fleet mutations to EvpFleetCommandHandler."""
        return self._evp_handler.set_evp_fleet(payload)

    def execute_ai_evp_preempt(self, payload: Dict[str, Any]) -> bool:
        """Delegates EVP preemption commands to EvpFleetCommandHandler."""
        return self._evp_handler.execute_ai_evp_preempt(payload)

    def sync_override_to_hardware(self, target_tls: List[str], mode: str) -> None:
        """Delegates manual hardware overrides to HardwareOverrideDispatcher."""
        self._override_dispatcher.sync_override_to_hardware(target_tls, mode)

    def execute_ai_hardware_cmd(self, payload: Dict[str, Any]) -> bool:
        """Delegates AI hardware IPC commands to HardwareOverrideDispatcher."""
        return self._override_dispatcher.execute_ai_hardware_cmd(payload)

    def on_failsafe_triggered(self) -> None:
        """Delegates emergency failsafe release to HardwareOverrideDispatcher."""
        self._override_dispatcher.on_failsafe_triggered()

    def on_failsafe_recovered(self) -> None:
        """Resumes hardware heartbeats and refreshes snapshots upon Watchdog recovery."""
        if hasattr(self._override_dispatcher, "on_failsafe_recovered"):
            self._override_dispatcher.on_failsafe_recovered()
        self._refresh_snapshots(True)
