# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import threading
from typing import Any, Callable, Dict, List, Tuple

from src.controller.connection_config_repo import ConnectionConfigRepository
from src.drivers.traffic_light_driver import TrafficLightDriver
from src.utils.network_address_parser import NetworkAddressParser

logger = logging.getLogger("src.controller.connection_manager")


class ConnectionOperationHandler:
    """
    Handles hardware driver connection lifecycle (connect, disconnect, toggle, bulk import)
    and synchronizes settings with ConnectionConfigRepository.
    """

    def __init__(self, active_connections: Dict[str, Any], saved_ips: Dict[str, str], locale_manager: Any = None):
        self.active_connections = active_connections
        self.saved_ips = saved_ips
        self.locale_manager = locale_manager

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def restore_saved_connections_async(self, known_intersections: List[str], toggle_func: Callable[..., bool]) -> None:
        """Loads saved hardware connections from DB asynchronously in a background daemon thread."""
        def _bg_restore():
            try:
                db_configs = ConnectionConfigRepository.load_all_connections_db(locale_manager=self.locale_manager)
                if db_configs:
                    logger.info(f"[HardwareConnectionManager] Found {len(db_configs)} saved hardware connection(s) in DB. Restoring...")
                    for tl_id, ip in db_configs.items():
                        self.saved_ips[tl_id] = ip
                        if tl_id not in known_intersections:
                            known_intersections.append(tl_id)
                        threading.Thread(
                            target=toggle_func,
                            args=(tl_id, ip, "connect"),
                            kwargs={"save_to_db": False},
                            daemon=True,
                            name=f"AutoConnect-{tl_id}",
                        ).start()
            except Exception as e:
                logger.error(f"[HardwareConnectionManager] Asynchronous DB connection restore error: {e}", exc_info=True)

        threading.Thread(target=_bg_restore, daemon=True, name="HWConnectionManager-DBRestore").start()

    def toggle_connection(
        self,
        intersection_id: str,
        ip_address: str = None,
        action: str = "toggle",
        green_stages_provider: Callable[[str], List[int]] = None,
        save_to_db: bool = True,
    ) -> bool:
        """Attempts to connect via SNMP/UTMC or safely shuts down driver for target intersection."""
        possible_ids = [str(intersection_id)]
        if str(intersection_id).startswith("tl_"):
            possible_ids.append(str(intersection_id).replace("tl_", ""))
        else:
            possible_ids.append(f"tl_{intersection_id}")

        is_currently_connected = any(
            pid in self.active_connections and getattr(self.active_connections[pid], "is_connected", False)
            for pid in possible_ids
        )

        if action == "disconnect" or (action == "toggle" and is_currently_connected):
            logger.info(self._get_string("connection_manager.hw_manager.disconnecting", default="[{id}] Disconnecting hardware control...", id=intersection_id))
            for pid in possible_ids:
                if pid in self.active_connections:
                    try:
                        self.active_connections[pid].shutdown()
                    except Exception as e:
                        logger.warning(f"Error shutting down driver for {pid}: {e}", exc_info=True)
                    del self.active_connections[pid]
                if pid in self.saved_ips:
                    del self.saved_ips[pid]
                if save_to_db:
                    ConnectionConfigRepository.remove_connection_db(pid, self.locale_manager)

            if intersection_id in self.saved_ips:
                del self.saved_ips[intersection_id]

            # Direct fallback ensuring Go Gateway releases and terminates any lingering driver
            try:
                from src.drivers.go_gateway_client import GoGatewayClient
                client = GoGatewayClient.get_instance()
                if client.is_running():
                    for pid in possible_ids:
                        client.disconnect_intersection(pid)
            except Exception as e:
                logger.debug(f"Direct Go gateway disconnect fallback: {e}")
            return False

        elif action == "connect" or (action == "toggle" and not is_currently_connected):
            if ip_address:
                self.saved_ips[intersection_id] = ip_address.strip()

            target_ip = self.saved_ips.get(intersection_id)
            if not target_ip:
                logger.error(self._get_string("connection_manager.hw_manager.no_ip_error", default="[{id}] Cannot connect: No IP address provided.", id=intersection_id))
                if save_to_db:
                    ConnectionConfigRepository.remove_connection_db(intersection_id, self.locale_manager)
                return False

            is_valid, connect_ip, connect_port, clean_saved = NetworkAddressParser.parse_and_validate_ip(target_ip)
            if not is_valid:
                logger.error(self._get_string("connection_manager.hw_manager.invalid_ip_format", default="[{id}] Invalid IP address: no valid IPv4 found in input.", id=intersection_id))
                if save_to_db:
                    ConnectionConfigRepository.remove_connection_db(intersection_id, self.locale_manager)
                return False

            self.saved_ips[intersection_id] = clean_saved
            logger.info(self._get_string("connection_manager.hw_manager.connecting", default="[{id}] Attempting to connect hardware at IP {ip} (Port {port})...", id=intersection_id, ip=connect_ip, port=connect_port))

            green_stages = green_stages_provider(intersection_id) if green_stages_provider else []

            driver = TrafficLightDriver(
                intersection_id=intersection_id,
                ip_address=connect_ip,
                port=connect_port,
                green_stages=green_stages,
                locale_manager=self.locale_manager,
            )

            # Resilient auto-detection of local simulator (EVP_SIMULATOR ports 1610-1615)
            if not getattr(driver, "is_connected", False) and connect_ip in ("127.0.0.1", "localhost") and ":" not in str(target_ip):
                used_ports = set()
                for pid, drv in self.active_connections.items():
                    if pid != intersection_id and getattr(drv, "is_connected", False):
                        p_str = self.saved_ips.get(pid, "")
                        if ":" in p_str:
                            try:
                                used_ports.add(int(p_str.split(":")[-1]))
                            except ValueError:
                                pass
                candidate_ports = [p for p in [1610, 1611, 1612, 1613, 1614, 1615] if p not in used_ports]
                for port_try in candidate_ports:
                    logger.info(f"[{intersection_id}] Testando autodetecção de simulador na porta {port_try}...")
                    driver_try = TrafficLightDriver(
                        intersection_id=intersection_id,
                        ip_address=connect_ip,
                        port=port_try,
                        green_stages=green_stages,
                        locale_manager=self.locale_manager,
                    )
                    if getattr(driver_try, "is_connected", False):
                        driver = driver_try
                        connect_port = port_try
                        clean_saved = f"{connect_ip}:{connect_port}"
                        self.saved_ips[intersection_id] = clean_saved
                        logger.info(f"[{intersection_id}] ✅ Simulador UTMC autodetectado na porta {connect_port}!")
                        break

            if getattr(driver, "is_connected", False):
                self.active_connections[intersection_id] = driver
                if save_to_db:
                    ConnectionConfigRepository.save_connection_db(intersection_id, clean_saved, self.locale_manager)
                return True
            else:
                return False

        return False

    def import_csv_and_bulk_connect(
        self,
        filepath: str,
        known_intersections: List[str],
        toggle_func: Callable[..., bool],
        save_to_db: bool = True,
    ) -> Tuple[int, int]:
        """
        Reads CSV file, updates internal IPs, and triggers bulk connection tests.

        Args:
            filepath (str): Path to CSV configuration file.
            known_intersections (List[str]): Shared list of known intersection IDs.
            toggle_func (Callable): Reference to toggle_connection function.
            save_to_db (bool): Whether to persist connections to database. Defaults to True.

        Returns:
            Tuple[int, int]: (success_count, total_attempted)
        """
        success_count = 0
        total_attempted = 0

        configs = ConnectionConfigRepository.import_csv_config(filepath)
        for tl_id, ip in configs.items():
            self.saved_ips[tl_id] = ip
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
                except Exception as _exc:
                    logger.debug("[controller] Ignored recoverable error: %s", _exc)
                del self.active_connections[tl_id]

            is_connected = toggle_func(tl_id, ip, "connect", save_to_db=save_to_db)
            if is_connected:
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

    def shutdown_all_connections(self) -> None:
        """Safely terminates all active driver instances and clears connection state."""
        logger.info(
            self._get_string(
                "connection_manager.hw_manager.shutdown_all", default="Shutting down all active hardware connections..."
            )
        )
        for tl_id, driver in list(self.active_connections.items()):
            try:
                driver.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down driver {tl_id}: {e}", exc_info=True)
        self.active_connections.clear()
        self.saved_ips.clear()
