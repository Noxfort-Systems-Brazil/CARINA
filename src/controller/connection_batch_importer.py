# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Batch DB restoration and CSV bulk-connection importer for hardware controllers."""

import logging
import os
import threading
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger("src.controller.connection_manager")


class ConnectionBatchImporter:
    """Restores saved hardware connections from DB and connects entries imported via CSV."""

    def __init__(
        self,
        active_connections: Dict[str, Any],
        saved_ips: Dict[str, str],
        saved_snmp_configs: Dict[str, Dict[str, Any]],
        locale_manager: Any,
        config_repo: Any,
        csv_store: Any,
        get_string_fn: Callable[..., str],
    ) -> None:
        self.active_connections = active_connections
        self.saved_ips = saved_ips
        self.saved_snmp_configs = saved_snmp_configs
        self.locale_manager = locale_manager
        self._config_repo = config_repo
        self._csv_store = csv_store
        self._get_string = get_string_fn

    def restore_saved_connections_async(
        self,
        known_intersections: List[str],
        toggle_func: Callable[..., bool],
    ) -> None:
        """Loads saved hardware connections from repository and connects them on background threads."""

        def _bg_restore() -> None:
            try:
                db_configs = self._config_repo.load_all_connections_db(locale_manager=self.locale_manager)
                if not db_configs:
                    return
                snmp_map = self._config_repo.load_all_snmp_configs_db(locale_manager=self.locale_manager)
                logger.info(
                    f"[HardwareConnectionManager] Found {len(db_configs)} saved hardware connection(s) in DB. Restoring..."
                )
                for tl_id, ip in db_configs.items():
                    self.saved_ips[tl_id] = ip
                    snmp_cfg = snmp_map.get(tl_id)
                    if snmp_cfg:
                        self.saved_snmp_configs[tl_id] = snmp_cfg
                    if tl_id not in known_intersections:
                        known_intersections.append(tl_id)
                    conn_kwargs: Dict[str, Any] = {"save_to_db": False}
                    if snmp_cfg:
                        conn_kwargs["snmp_config"] = snmp_cfg
                    threading.Thread(
                        target=toggle_func,
                        args=(tl_id, ip, "connect"),
                        kwargs=conn_kwargs,
                        daemon=True,
                        name=f"AutoConnect-{tl_id}",
                    ).start()
            except Exception as exc:
                logger.error(
                    f"[HardwareConnectionManager] Asynchronous DB connection restore error: {exc}", exc_info=True
                )

        threading.Thread(target=_bg_restore, daemon=True, name="HWConnectionManager-DBRestore").start()

    def import_csv_and_bulk_connect(
        self,
        filepath: str,
        known_intersections: List[str],
        toggle_func: Callable[..., bool],
        save_to_db: bool = True,
    ) -> Tuple[int, int]:
        """Reads CSV file, updates saved IPs/SNMP configs, and triggers bulk connections."""
        success_count = 0
        total_attempted = 0
        configs = self._csv_store.import_csv_config(filepath)
        csv_entries = self._csv_store.import_csv_entries(filepath) if filepath and os.path.exists(str(filepath)) else {}

        for tl_id, ip in configs.items():
            self.saved_ips[tl_id] = ip
            snmp_cfg = (csv_entries.get(tl_id) or {}).get("snmp_config")
            if snmp_cfg:
                self.saved_snmp_configs[tl_id] = snmp_cfg
            if tl_id not in known_intersections:
                known_intersections.append(tl_id)

            total_attempted += 1
            logger.info(
                self._get_string(
                    "connection_manager.hw_manager.bulk_testing",
                    default="[Bulk Import] Testing connection for {id} at {ip}...",
                    id=tl_id,
                    ip=ip,
                )
            )
            if tl_id in self.active_connections:
                try:
                    self.active_connections[tl_id].shutdown()
                except Exception as exc:
                    logger.debug("[controller] Ignored recoverable error: %s", exc)
                del self.active_connections[tl_id]

            toggle_kwargs: Dict[str, Any] = {"save_to_db": save_to_db}
            if snmp_cfg:
                toggle_kwargs["snmp_config"] = snmp_cfg
            if toggle_func(tl_id, ip, "connect", **toggle_kwargs):
                success_count += 1

        logger.info(
            self._get_string(
                "connection_manager.hw_manager.bulk_finished",
                default="Bulk connection finished: {success}/{total} connected successfully.",
                success=success_count,
                total=total_attempted,
            )
        )
        return success_count, total_attempted
