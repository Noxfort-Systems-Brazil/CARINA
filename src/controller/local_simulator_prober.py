# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Local UTMC/SNMP simulator port prober (SRP).
Isolates candidate port enumeration (1610-1615) from ConnectionOperationHandler.
"""

import logging
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LocalSimulatorProber:
    """Probes localhost simulator ports when an explicit port was not specified."""

    DEFAULT_PORTS: Tuple[int, ...] = (1610, 1611, 1612, 1613, 1614, 1615)

    def __init__(self, ports: Iterable[int] = DEFAULT_PORTS) -> None:
        self._ports: Tuple[int, ...] = tuple(ports)

    @staticmethod
    def _collect_used_ports(
        intersection_id: str,
        active_connections: Dict[str, Any],
        saved_ips: Dict[str, str],
    ) -> set:
        used_ports = set()
        for pid, drv in active_connections.items():
            if pid != intersection_id and getattr(drv, "is_connected", False):
                p_str = saved_ips.get(pid, "")
                if ":" in p_str:
                    try:
                        used_ports.add(int(p_str.split(":")[-1]))
                    except ValueError:
                        pass
        return used_ports

    def probe_local_simulator(
        self,
        intersection_id: str,
        connect_ip: str,
        green_stages: List[int],
        driver_extra: Dict[str, Any],
        active_connections: Dict[str, Any],
        saved_ips: Dict[str, str],
        driver_builder: Callable[..., Any],
        locale_manager: Any = None,
    ) -> Optional[Tuple[Any, int]]:
        """Attempts connecting to localhost candidate simulator ports; returns (driver, port) if found."""
        used_ports = self._collect_used_ports(intersection_id, active_connections, saved_ips)
        for port_try in self._ports:
            if port_try in used_ports:
                continue
            logger.info(f"[{intersection_id}] Testando autodetecção de simulador na porta {port_try}...")
            driver_try = driver_builder(
                intersection_id=intersection_id,
                ip_address=connect_ip,
                port=port_try,
                green_stages=green_stages,
                locale_manager=locale_manager,
                **driver_extra,
            )
            if getattr(driver_try, "is_connected", False):
                logger.info(f"[{intersection_id}] ✅ Simulador UTMC autodetectado na porta {port_try}!")
                return driver_try, port_try
        return None
