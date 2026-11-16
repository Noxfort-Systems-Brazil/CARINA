# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Handles hardware driver connection lifecycle (connect, disconnect, toggle, bulk import)
with injected repository, driver factory, simulator prober, and remote release fallback (DIP / SRP).
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.controller.connection_batch_importer import ConnectionBatchImporter
from src.controller.connection_config_repo import ConnectionConfigRepository
from src.controller.local_simulator_prober import LocalSimulatorProber
from src.drivers.traffic_light_driver import TrafficLightDriver
from src.utils.network_address_parser import NetworkAddressParser

logger = logging.getLogger("src.controller.connection_manager")


class _DefaultTrafficDriverFactory:
    """Default ITrafficDriverFactory resolving module TrafficLightDriver dynamically for patch compatibility."""

    def create_driver(
        self,
        intersection_id: str,
        ip_address: str,
        port: int,
        green_stages: Optional[List[int]] = None,
        locale_manager: Any = None,
        **extra_kwargs: Any,
    ) -> Any:
        return TrafficLightDriver(
            intersection_id=intersection_id,
            ip_address=ip_address,
            port=port,
            green_stages=green_stages,
            locale_manager=locale_manager,
            **extra_kwargs,
        )


class ConnectionOperationHandler:
    """Orchestrates hardware connection lifecycle using injected repository and driver abstractions."""

    def __init__(
        self,
        active_connections: Dict[str, Any],
        saved_ips: Dict[str, str],
        locale_manager: Any = None,
        saved_snmp_configs: Optional[Dict[str, Dict[str, Any]]] = None,
        config_repo: Any = ConnectionConfigRepository,
        csv_store: Any = ConnectionConfigRepository,
        driver_factory: Optional[Any] = None,
        simulator_prober: Optional[LocalSimulatorProber] = None,
        remote_disconnect_fn: Optional[Callable[[List[str]], None]] = None,
    ):
        self.active_connections = active_connections
        self.saved_ips = saved_ips
        self.locale_manager = locale_manager
        self.saved_snmp_configs: Dict[str, Dict[str, Any]] = (
            saved_snmp_configs if saved_snmp_configs is not None else {}
        )
        self._config_repo = config_repo
        self._csv_store = csv_store
        self._driver_factory = driver_factory or _DefaultTrafficDriverFactory()
        self._simulator_prober = simulator_prober or LocalSimulatorProber()
        self._remote_disconnect_fn = remote_disconnect_fn
        self._batch_importer = ConnectionBatchImporter(
            active_connections=self.active_connections,
            saved_ips=self.saved_ips,
            saved_snmp_configs=self.saved_snmp_configs,
            locale_manager=self.locale_manager,
            config_repo=self._config_repo,
            csv_store=self._csv_store,
            get_string_fn=self._get_string,
        )

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    @staticmethod
    def _possible_ids(intersection_id: str) -> List[str]:
        s_id = str(intersection_id)
        return [s_id, s_id.replace("tl_", "")] if s_id.startswith("tl_") else [s_id, f"tl_{s_id}"]

    def _create_driver(self, **kwargs: Any) -> Any:
        if callable(getattr(self._driver_factory, "create_driver", None)):
            return self._driver_factory.create_driver(**kwargs)
        return self._driver_factory(**kwargs)

    def _fallback_remote_disconnect(self, possible_ids: List[str]) -> None:
        if self._remote_disconnect_fn is not None:
            self._remote_disconnect_fn(possible_ids)
            return
        try:
            from src.drivers.go_gateway_client import GoGatewayClient

            client = GoGatewayClient.get_instance()
            if client.is_running():
                for pid in possible_ids:
                    if client.disconnect_intersection(pid):
                        break
        except Exception as exc:
            logger.debug(f"Direct Go gateway disconnect fallback: {exc}")

    def restore_saved_connections_async(self, known_intersections: List[str], toggle_func: Callable[..., bool]) -> None:
        """Loads saved hardware connections from repository asynchronously."""
        self._batch_importer.restore_saved_connections_async(known_intersections, toggle_func)

    def _resolve_saved_snmp_config(
        self, possible_ids: List[str], explicit_snmp: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if explicit_snmp:
            return explicit_snmp
        for pid in possible_ids:
            if pid in self.saved_snmp_configs:
                return self.saved_snmp_configs[pid]
        return None

    def _disconnect(self, intersection_id: str, possible_ids: List[str], save_to_db: bool) -> bool:
        logger.info(
            self._get_string(
                "connection_manager.hw_manager.disconnecting",
                default="[{id}] Disconnecting hardware control...",
                id=intersection_id,
            )
        )
        driver_shutdown_ok = False
        for pid in possible_ids:
            if pid in self.active_connections:
                try:
                    self.active_connections[pid].shutdown()
                    driver_shutdown_ok = True
                except Exception as exc:
                    logger.warning(f"Error shutting down driver for {pid}: {exc}", exc_info=True)
                del self.active_connections[pid]
            self.saved_ips.pop(pid, None)
            self.saved_snmp_configs.pop(pid, None)
            if save_to_db:
                self._config_repo.remove_connection_db(pid, self.locale_manager)

        self.saved_ips.pop(intersection_id, None)
        if not driver_shutdown_ok:
            self._fallback_remote_disconnect(possible_ids)
        return False

    def _abort_connect(self, intersection_id: str, locale_key: str, default_msg: str, save_to_db: bool) -> bool:
        logger.error(self._get_string(locale_key, default=default_msg, id=intersection_id))
        if save_to_db:
            self._config_repo.remove_connection_db(intersection_id, self.locale_manager)
        return False

    def _connect(
        self,
        intersection_id: str,
        possible_ids: List[str],
        ip_address: Optional[str],
        green_stages_provider: Optional[Callable[[str], List[int]]],
        save_to_db: bool,
        snmp_config: Optional[Dict[str, Any]],
    ) -> bool:
        if ip_address:
            self.saved_ips[intersection_id] = ip_address.strip()

        effective_snmp = self._resolve_saved_snmp_config(possible_ids, snmp_config)
        if snmp_config:
            self.saved_snmp_configs[intersection_id] = snmp_config

        target_ip = self.saved_ips.get(intersection_id)
        if not target_ip:
            return self._abort_connect(
                intersection_id,
                "connection_manager.hw_manager.no_ip_error",
                "[{id}] Cannot connect: No IP address provided.",
                save_to_db,
            )

        is_valid, connect_ip, connect_port, clean_saved = NetworkAddressParser.parse_and_validate_ip(target_ip)
        if not is_valid:
            return self._abort_connect(
                intersection_id,
                "connection_manager.hw_manager.invalid_ip_format",
                "[{id}] Invalid IP address: no valid IPv4 found in input.",
                save_to_db,
            )

        self.saved_ips[intersection_id] = clean_saved
        logger.info(
            self._get_string(
                "connection_manager.hw_manager.connecting",
                default="[{id}] Attempting to connect hardware at IP {ip} (Port {port})...",
                id=intersection_id,
                ip=connect_ip,
                port=connect_port,
            )
        )

        green_stages = green_stages_provider(intersection_id) if green_stages_provider else []
        driver_extra: Dict[str, Any] = {}
        if effective_snmp:
            driver_extra["snmp_config"] = effective_snmp
            if effective_snmp.get("community"):
                driver_extra["community_string"] = str(effective_snmp["community"])
            cfg_path = effective_snmp.get("config_path") or effective_snmp.get("oid_config_path")
            if cfg_path:
                driver_extra["config_path"] = str(cfg_path)

        driver = self._create_driver(
            intersection_id=intersection_id,
            ip_address=connect_ip,
            port=connect_port,
            green_stages=green_stages,
            locale_manager=self.locale_manager,
            **driver_extra,
        )

        if (
            not getattr(driver, "is_connected", False)
            and connect_ip in ("127.0.0.1", "localhost")
            and ":" not in str(target_ip)
        ):
            probed = self._simulator_prober.probe_local_simulator(
                intersection_id=intersection_id,
                connect_ip=connect_ip,
                green_stages=green_stages,
                driver_extra=driver_extra,
                active_connections=self.active_connections,
                saved_ips=self.saved_ips,
                driver_builder=self._create_driver,
                locale_manager=self.locale_manager,
            )
            if probed is not None:
                driver, connect_port = probed
                clean_saved = f"{connect_ip}:{connect_port}"
                self.saved_ips[intersection_id] = clean_saved

        if not getattr(driver, "is_connected", False):
            return False

        self.active_connections[intersection_id] = driver
        if save_to_db:
            save_kwargs = {"snmp_config": effective_snmp} if effective_snmp else {}
            self._config_repo.save_connection_db(intersection_id, clean_saved, self.locale_manager, **save_kwargs)
        return True

    def toggle_connection(
        self,
        intersection_id: str,
        ip_address: str = None,
        action: str = "toggle",
        green_stages_provider: Callable[[str], List[int]] = None,
        save_to_db: bool = True,
        snmp_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Attempts to connect via SNMP/UTMC or safely shuts down driver for target intersection."""
        possible_ids = self._possible_ids(intersection_id)
        is_connected = any(
            pid in self.active_connections and getattr(self.active_connections[pid], "is_connected", False)
            for pid in possible_ids
        )

        if action == "disconnect" or (action == "toggle" and is_connected):
            return self._disconnect(intersection_id, possible_ids, save_to_db)
        if action == "connect" or (action == "toggle" and not is_connected):
            return self._connect(
                intersection_id, possible_ids, ip_address, green_stages_provider, save_to_db, snmp_config
            )
        return False

    def import_csv_and_bulk_connect(
        self,
        filepath: str,
        known_intersections: List[str],
        toggle_func: Callable[..., bool],
        save_to_db: bool = True,
    ) -> Tuple[int, int]:
        """Reads CSV file, updates saved IPs/SNMP configs, and triggers bulk connections."""
        return self._batch_importer.import_csv_and_bulk_connect(
            filepath, known_intersections, toggle_func, save_to_db=save_to_db
        )

    def shutdown_all_connections(self) -> None:
        """Safely terminates all active driver instances and clears connection state."""
        logger.info(
            self._get_string(
                "connection_manager.hw_manager.shutdown_all",
                default="Shutting down all active hardware connections...",
            )
        )
        for tl_id, driver in list(self.active_connections.items()):
            try:
                driver.shutdown()
            except Exception as exc:
                logger.warning(f"Error shutting down driver {tl_id}: {exc}", exc_info=True)
        self.active_connections.clear()
        self.saved_ips.clear()
