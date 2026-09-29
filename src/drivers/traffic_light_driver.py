# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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

# File: src/drivers/traffic_light_driver.py
# Author: Gabriel Moraes
# Date: 2026-02-22 (Refactored 2026-09-25)

"""
High-level manager for a single traffic light intersection.
Acts as a pure orchestrator between the CARINA engine and underlying hardware drivers.
Refactored to comply with SOLID and Clean Architecture by delegating I/O and parsing concerns.
"""

import logging
from typing import Any, Dict, List, Optional

from src.drivers.base_driver import BaseTrafficDriver
from src.drivers.driver_factory import DriverFactory
from src.drivers.traffic_color_logger import TrafficColorLogger
from src.drivers.traffic_map_loader import TrafficMapLoader

logger = logging.getLogger(__name__)
cmd_logger = None  # Injected optionally by ConnectionManager


class TrafficLightDriver:
    """
    Logical intersection controller in the CARINA engine.
    Orchestrates hardware drivers, map phase states, and telemetry.
    """

    def __init__(
        self,
        intersection_id: str,
        ip_address: str,
        port: int,
        community_string: str = "public",
        green_stages: Optional[List[int]] = None,
        locale_manager: Any = None,
    ) -> None:
        self.intersection_id = intersection_id
        self.ip_address = ip_address
        self.port = port
        self.community_string = community_string
        self.locale_manager = locale_manager

        self.hardware_driver: Optional[BaseTrafficDriver] = None
        self.is_connected = False

        self.current_stage: Optional[int] = None
        self.green_stages: List[int] = green_stages if green_stages is not None else []
        self.stage_states: Dict[int, str] = self._load_stage_states_from_map()

        logger.info(
            self._get_string(
                "drivers.traffic_light.init",
                default="[Intersection {id}] Initializing TrafficLightDriver...",
                id=self.intersection_id,
            )
        )
        self._connect()

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def _connect(self) -> None:
        """Connects to hardware driver via DriverFactory discovery."""
        self.hardware_driver = DriverFactory.create_and_connect_driver(
            self.ip_address,
            self.port,
            self.community_string,
            self.intersection_id,
            green_stages=self.green_stages,
            locale_manager=self.locale_manager,
        )

        if self.hardware_driver is not None:
            self.is_connected = True
            logger.info(
                self._get_string(
                    "drivers.traffic_light.connected",
                    default="[Intersection {id}] Connected via {protocol}",
                    id=self.intersection_id,
                    protocol=self.hardware_driver.get_protocol_name(),
                )
            )
            self.hardware_driver.start_heartbeat()
        else:
            self.is_connected = False
            logger.error(
                self._get_string(
                    "drivers.traffic_light.connect_failed",
                    default="[Intersection {id}] Failed to connect to hardware at {ip}:{port}",
                    id=self.intersection_id,
                    ip=self.ip_address,
                    port=self.port,
                )
            )

    def _load_stage_states_from_map(self) -> Dict[int, str]:
        """Delegates SUMO map phase parsing to TrafficMapLoader (SRP)."""
        return TrafficMapLoader.load_stage_states(self.intersection_id, locale_manager=self.locale_manager)

    def apply_logical_action(
        self,
        action: int,
        current_stage_idx: int,
        green_stages: List[int],
        stage_codes: Optional[Dict[int, str]] = None,
    ) -> bool:
        """Dispatches high-level AI logical action (0 = NEXT_STAGE, 1 = HOLD) to hardware."""
        self.current_stage = current_stage_idx
        self.green_stages = green_stages

        if not self.is_connected or self.hardware_driver is None:
            logger.warning(
                self._get_string(
                    "drivers.traffic_light.action_disconnected",
                    default="[Intersection {id}] Cannot apply logical action. Driver is disconnected.",
                    id=self.intersection_id,
                )
            )
            return False

        return self.hardware_driver.apply_logical_action(action, current_stage_idx, green_stages, stage_codes)

    def apply_decision(self, action: str) -> bool:
        """Dispatches pure neural network decision ('HOLD' or 'ADVANCE') to hardware driver."""
        if not self.is_connected or self.hardware_driver is None:
            return False
        return self.hardware_driver.apply_decision(action)

    def apply_action(self, action_data: Dict[str, Any]) -> bool:
        """Dispatches raw command action dictionary to hardware driver."""
        if not self.is_connected or self.hardware_driver is None:
            logger.warning(
                self._get_string(
                    "drivers.traffic_light.action_disconnected",
                    default="[Intersection {id}] Cannot apply action. Driver is disconnected.",
                    id=self.intersection_id,
                )
            )
            return False

        logger.debug(
            self._get_string(
                "drivers.traffic_light.applying_action",
                default="[Intersection {id}] Applying action: {action}",
                id=self.intersection_id,
                action=action_data,
            )
        )
        if cmd_logger:
            cmd_logger.info(
                self._get_string(
                    "drivers.traffic_light.cmd_sending",
                    default="CARINA sending command to {id} ({ip}): {action}",
                    id=self.intersection_id,
                    ip=self.ip_address,
                    action=action_data,
                )
            )

        return self.hardware_driver.send_action(action_data)

    def log_carina_colors(self, current_stage_idx: int, stage_codes: Optional[Dict[int, str]] = None) -> None:
        """Delegates stage color logging to TrafficColorLogger (SRP)."""
        if not hasattr(self, "stage_states") or not self.stage_states:
            self.stage_states = self._load_stage_states_from_map()

        active_states = self.stage_states if self.stage_states else (stage_codes or {})
        TrafficColorLogger.log_stage(
            intersection_id=self.intersection_id,
            current_stage_idx=current_stage_idx,
            active_states=active_states,
            locale_manager=self.locale_manager,
        )

    def log_carina_override(self, override_type: str) -> None:
        """Delegates manual override logging to TrafficColorLogger (SRP)."""
        TrafficColorLogger.log_override(
            intersection_id=self.intersection_id,
            override_type=override_type,
            locale_manager=self.locale_manager,
        )

    def get_status(self) -> Dict[str, Any]:
        """Retrieves real-time telemetry from hardware driver."""
        if not self.is_connected or self.hardware_driver is None:
            return {
                "intersection_id": self.intersection_id,
                "status": "offline",
                "protocol": "none",
                "brand": "Não informado",
                "model": "Não informado",
                "active_greens": 0,
                "active_yellows": 0,
                "active_reds": 0,
                "active_ped_calls": 0,
            }

        telemetry = self.hardware_driver.get_telemetry()
        telemetry["intersection_id"] = self.intersection_id
        telemetry["brand"] = getattr(self.hardware_driver, "brand", "Não informado")
        telemetry["model"] = getattr(self.hardware_driver, "model", "Não informado")
        return telemetry

    def shutdown(self) -> None:
        """Safely shuts down hardware driver, releasing control and stopping watchdog."""
        if self.hardware_driver is not None:
            logger.info(
                self._get_string(
                    "drivers.traffic_light.shutdown",
                    default="[Intersection {id}] Shutting down driver. Releasing hardware control and stopping heartbeat...",
                    id=self.intersection_id,
                )
            )
            try:
                if hasattr(self.hardware_driver, "release_control") and callable(self.hardware_driver.release_control):
                    self.hardware_driver.release_control()
            except Exception as e:
                logger.warning(
                    self._get_string(
                        "drivers.traffic_light.release_failed",
                        default="[Intersection {id}] Warning: Failed to release hardware control during shutdown: {error}",
                        id=self.intersection_id,
                        error=e,
                    )
                )

            try:
                self.hardware_driver.stop_heartbeat()
            except Exception as e:
                logger.warning(f"Error stopping heartbeat for intersection {self.intersection_id}: {e}")

            try:
                if hasattr(self.hardware_driver, "shutdown") and callable(self.hardware_driver.shutdown):
                    self.hardware_driver.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down hardware driver for intersection {self.intersection_id}: {e}")

            self.is_connected = False
            self.hardware_driver = None
