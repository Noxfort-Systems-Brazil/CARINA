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

# File: src/drivers/go_driver_proxy.py
# Author: Gabriel Moraes
# Date: 2026-09-25

"""
Adapter proxy that implements BaseTrafficDriver and delegates all hardware operations
to the high-performance compiled Go Hardware Gateway over OS standard pipes.
"""

import logging
from typing import Any, Dict, List, Optional

from src.drivers.base_driver import BaseTrafficDriver
from src.drivers.go_gateway_client import GoGatewayClient

logger = logging.getLogger(__name__)


class GoTrafficDriverProxy(BaseTrafficDriver):
    """
    Traffic controller driver proxy.
    Maintains 100% compliance with BaseTrafficDriver contract while routing
    execution to the Go Hardware Gateway subprocess.
    """

    def __init__(
        self,
        ip_address: str,
        port: int,
        intersection_id: str = "Desconhecido",
        community_string: str = "public",
        green_stages: Optional[List[int]] = None,
        protocol_name: str = "NTCIP 1202",
        brand: str = "Não informado",
        model: str = "Não informado",
        client: Optional[GoGatewayClient] = None,
    ) -> None:
        super().__init__(
            ip_address=ip_address,
            port=port,
            intersection_id=intersection_id,
            community_string=community_string,
            green_stages=green_stages,
        )

        self.protocol_name = protocol_name
        self.brand = brand
        self.model = model
        self.client = client or GoGatewayClient.get_instance()

        # Stop Python-side heartbeat since Go handles it natively with zero GIL
        if hasattr(self, "heartbeat_manager"):
            self.heartbeat_manager.stop()

    def get_protocol_name(self) -> str:
        return self.protocol_name

    def send_action(self, action_data: Dict[str, Any]) -> bool:
        """Forwards raw action dictionary to the Go gateway."""
        return self.client.apply_action(self.intersection_id, action_data)

    def apply_logical_action(
        self,
        action: int,
        current_stage_idx: int,
        green_stages: List[int],
        stage_codes: Optional[Dict[int, str]] = None,
    ) -> bool:
        """Forwards high-level logical AI action to the Go gateway."""
        return self.client.apply_logical_action(
            self.intersection_id,
            action,
            current_stage_idx,
            green_stages,
            stage_codes=stage_codes,
        )

    def apply_decision(self, action: str) -> bool:
        """Forwards pure high-level AI decision ('HOLD' or 'ADVANCE') to the Go gateway."""
        return self.client.apply_decision(self.intersection_id, action)

    def get_telemetry(self) -> Dict[str, Any]:
        """Retrieves real-time telemetry from the Go gateway."""
        telemetry = self.client.get_telemetry(self.intersection_id)
        telemetry["intersection_id"] = self.intersection_id
        telemetry["brand"] = self.brand
        telemetry["model"] = self.model
        return telemetry

    def send_heartbeat_pulse(self) -> bool:
        """In Go mode, heartbeat is managed automatically by the Go daemon."""
        return True

    def start_heartbeat(self) -> None:
        """Managed automatically in Go upon connect."""
        pass

    def stop_heartbeat(self) -> None:
        """Stops heartbeat by ensuring the intersection disconnects from the Go gateway."""
        try:
            self.shutdown()
        except Exception as e:
            logger.debug(f"[{self.ip_address}] Error stopping heartbeat: {e}")

    def release_control(self) -> bool:
        """Releases remote holds and overrides via Go gateway."""
        return self.client.apply_action(self.intersection_id, {"action_type": "release_hold"})

    def shutdown(self) -> None:
        """Disconnects intersection from the Go gateway."""
        try:
            self.client.disconnect_intersection(self.intersection_id)
        except Exception as e:
            logger.warning(f"[{self.ip_address}] Error disconnecting from Go gateway: {e}")
