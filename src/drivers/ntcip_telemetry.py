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

# File: src/drivers/ntcip_telemetry.py
# Author: Gabriel Moraes
# Date: 2026-08-14

"""
Telemetry collector and parser for NTCIP 1202 protocol.
Decouples telemetry reading and normalization from driver class (SRP).
"""

import logging
from typing import Any, Callable, Dict, Tuple

from src.drivers.ntcip_config import NtcipConfig

logger = logging.getLogger(__name__)


class NtcipTelemetryCollector:
    """
    Collects and parses telemetry data from an NTCIP 1202 traffic light controller via SNMP.
    """

    def __init__(
        self, snmp_get_fn: Callable[[str], Tuple[bool, Any]], config: NtcipConfig, ip_address: str = ""
    ) -> None:
        self._snmp_get = snmp_get_fn
        self._config = config
        self._ip_address = ip_address

    def collect(self) -> Dict[str, Any]:
        """
        Fetches the current status of the intersection using NTCIP OIDs.
        """
        telemetry: Dict[str, Any] = {
            "protocol": "NTCIP 1202",
            "status": "unknown",
            "active_greens": 0,
            "active_yellows": 0,
            "active_reds": 0,
            "active_ped_calls": 0,
        }

        # Fetch active greens
        greens_oid = self._config.get_telemetry_oid("status_greens")
        success_green, val_green = self._snmp_get(greens_oid) if greens_oid else (False, "OID not found")
        if success_green:
            try:
                telemetry["active_greens"] = int(val_green)
                telemetry["status"] = "online"
            except (ValueError, TypeError):
                pass

        # Fetch active yellows
        yellows_oid = self._config.get_telemetry_oid("status_yellows")
        success_yellow, val_yellow = self._snmp_get(yellows_oid) if yellows_oid else (False, "OID not found")
        if success_yellow:
            try:
                telemetry["active_yellows"] = int(val_yellow)
            except (ValueError, TypeError):
                pass

        # Fetch active reds
        reds_oid = self._config.get_telemetry_oid("status_reds")
        success_red, val_red = self._snmp_get(reds_oid) if reds_oid else (False, "OID not found")
        if success_red:
            try:
                telemetry["active_reds"] = int(val_red)
            except (ValueError, TypeError):
                pass

        # Fetch active ped calls
        peds_oid = self._config.get_telemetry_oid("status_ped_calls")
        success_ped, val_ped = self._snmp_get(peds_oid) if peds_oid else (False, "OID not found")
        if success_ped:
            try:
                telemetry["active_ped_calls"] = int(val_ped)
            except (ValueError, TypeError):
                pass

        if not success_green and not success_yellow and not success_red:
            telemetry["status"] = "offline"
            if self._ip_address:
                logger.warning(f"[{self._ip_address}] Failed to fetch NTCIP telemetry.")

        return telemetry
