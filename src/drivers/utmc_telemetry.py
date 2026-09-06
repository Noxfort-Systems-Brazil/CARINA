# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/drivers/utmc_telemetry.py
# Author: Gabriel Moraes
# Date: 2026-08-14

"""
Telemetry collector and parser for UTMC2 protocol.
Decouples telemetry reading and normalization from driver class (SRP).
"""

import logging
from typing import Any, Callable, Dict, Tuple

from src.drivers.utmc_config import UtmcConfig

logger = logging.getLogger(__name__)


class UtmcTelemetryCollector:
    """
    Collects and parses telemetry data from a UTMC2 traffic light controller via SNMP.
    """

    def __init__(
        self, snmp_get_fn: Callable[[str], Tuple[bool, Any]], config: UtmcConfig, ip_address: str = ""
    ) -> None:
        self._snmp_get = snmp_get_fn
        self._config = config
        self._ip_address = ip_address

    def collect(self) -> Dict[str, Any]:
        """
        Fetches the current status of the intersection using UTMC OIDs.
        """
        telemetry: Dict[str, Any] = {
            "protocol": "UTMC2",
            "status": "unknown",
            "active_greens": 0,
            "active_yellows": 0,
            "active_reds": 0,
            "active_ped_calls": 0,
        }

        # Fetch active stage (green)
        active_oid = self._config.get_telemetry_oid("status_active")
        success_active, val_active = self._snmp_get(active_oid) if active_oid else (False, "OID not found")
        if success_active:
            try:
                telemetry["active_greens"] = int(val_active)
                telemetry["status"] = "online"
            except (ValueError, TypeError):
                pass

        # Fetch leaving stage (yellow/amber)
        leaving_oid = self._config.get_telemetry_oid("status_leaving")
        success_leaving, val_leaving = self._snmp_get(leaving_oid) if leaving_oid else (False, "OID not found")
        if success_leaving:
            try:
                telemetry["active_yellows"] = int(val_leaving)
            except (ValueError, TypeError):
                pass

        # Fetch active ped calls
        ped_oid = self._config.get_telemetry_oid("status_ped_demand")
        success_ped, val_ped = self._snmp_get(ped_oid) if ped_oid else (False, "OID not found")
        if success_ped:
            try:
                telemetry["active_ped_calls"] = int(val_ped)
            except (ValueError, TypeError):
                pass

        if not success_active and not success_leaving:
            telemetry["status"] = "offline"
            if self._ip_address:
                logger.warning(f"[{self._ip_address}] Failed to fetch UTMC telemetry.")

        return telemetry
