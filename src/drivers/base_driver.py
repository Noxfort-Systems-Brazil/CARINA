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

# File: src/drivers/base_driver.py
# Author: Gabriel Moraes
# Date: 2026-02-22

"""
Base abstraction for traffic light controllers.
Defines the high-level interface contract for traffic light drivers (SOLID & Clean Architecture).
"""

import ipaddress
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseTrafficDriver(ABC):
    """
    Abstract base class for all traffic controller drivers.
    Defines the contract between the CARINA engine/UI and the underlying hardware proxy.
    """

    def __init__(
        self,
        ip_address: str,
        port: int,
        intersection_id: str = "Desconhecido",
        community_string: str = "public",
        timeout: int = 2,
        retries: int = 1,
        green_stages: Optional[List[int]] = None,
    ) -> None:
        self.intersection_id = intersection_id
        self.green_stages = green_stages if green_stages is not None else []

        # Robust IP sanitization: extract a valid IPv4 address from any input
        ip_address = str(ip_address).strip()
        ip_port_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::(\d{1,5}))?", ip_address)
        if ip_port_match:
            candidate_ip = ip_port_match.group(1)
            try:
                ipaddress.ip_address(candidate_ip)  # Validate it's a real IPv4
                ip_address = candidate_ip
                if ip_port_match.group(2):
                    port = int(ip_port_match.group(2))
            except ValueError:
                pass

        self.ip_address = ip_address
        self.port = port

        # Hardware device metadata (Manufacturer & Model)
        self.brand: str = "Não informado"
        self.model: str = "Não informado"
        self.sys_descr: str = ""

    # =========================================================================
    # Abstract Methods to be implemented by specific drivers / proxies
    # =========================================================================

    @abstractmethod
    def get_protocol_name(self) -> str:
        pass

    @abstractmethod
    def send_action(self, action_data: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def apply_decision(self, action: str) -> bool:
        """Applies a pure neural network decision ('HOLD' or 'ADVANCE')."""
        pass

    @abstractmethod
    def apply_logical_action(
        self, action: int, current_stage_idx: int, green_stages: list, stage_codes: dict = None
    ) -> bool:
        pass

    @abstractmethod
    def get_telemetry(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def send_heartbeat_pulse(self) -> bool:
        pass

    @abstractmethod
    def release_control(self) -> bool:
        pass

    def start_heartbeat(self) -> None:
        pass

    def stop_heartbeat(self) -> None:
        pass

    def shutdown(self) -> None:
        self.release_control()
