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

# File: src/drivers/utmc_action_executor.py
# Author: Gabriel Moraes
# Date: 2026-08-14

"""
Action executor and command dispatcher for UTMC2 protocol.
Decouples action execution, command translation, and dispatch tables (SRP & OCP).
"""

import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple

from src.drivers.utmc_config import UtmcConfig

logger = logging.getLogger(__name__)


class UtmcActionExecutor:
    """
    Dispatches and executes UTMC2 actions using a command registry / dispatch table.
    Open for extension: new action types can be registered via `register_handler`.
    """

    def __init__(
        self,
        snmp_set_fn: Callable[..., Tuple[bool, Any]],
        config: UtmcConfig,
        ip_address: str = "",
        stop_heartbeat_cb: Optional[Callable[[], None]] = None,
        green_stages: Optional[list] = None,
    ) -> None:
        self._snmp_set = snmp_set_fn
        self._config = config
        self._ip_address = ip_address
        self._stop_heartbeat_cb = stop_heartbeat_cb
        self._green_stages = green_stages or []

        # Command dispatch registry (Open-Closed Principle)
        self._handlers: Dict[str, Callable[[Dict[str, Any], int], Tuple[bool, Any]]] = {
            "flash": self._handle_flash,
            "release_flash": self._handle_release_flash,
            "dark": self._handle_dark,
            "release_dark": self._handle_release_dark,
            "release_hold": self._handle_release_hold,
            "hold": self._handle_hold,
            "force_off": self._handle_force_off,
            "omit": self._handle_omit,
            "demand": self._handle_demand,
            "veh_call": self._handle_demand,
            "extend": self._handle_extend,
            "ACTIVATE_LOCAL_FIXED_TIME": self._handle_activate_local_fixed_time,
        }

    def register_handler(self, action_type: str, handler: Callable[[Dict[str, Any], int], Tuple[bool, Any]]) -> None:
        """Allows runtime extension with custom action handlers without modifying the class (OCP)."""
        self._handlers[action_type] = handler

    def execute(self, action_data: Dict[str, Any]) -> bool:
        """
        Translates CARINA's action dictionary into UTMC2 SNMP command execution.
        """
        action_type = action_data.get("action_type")
        stage = action_data.get("stage", 0)

        if not action_type:
            logger.error(f"[{self._ip_address}] Invalid action data provided to UTMC2 Driver.")
            return False

        # Calculate bitmask for the specific stage (HAL support)
        if "stage_mask" in action_data:
            stage_bitmask = action_data["stage_mask"]
        else:
            stage_bitmask = 1 << (stage - 1) if stage > 0 else 0

        handler = self._handlers.get(action_type)
        if not handler:
            logger.warning(f"[{self._ip_address}] Unknown action type: {action_type}")
            return False

        # Actions requiring stage validation
        if action_type in ("hold", "force_off", "omit", "demand", "veh_call", "extend"):
            if stage == 0 and "stage_mask" not in action_data:
                logger.error(f"[{self._ip_address}] Stage required for UTMC action: {action_type}")
                return False

        success, result = handler(action_data, stage_bitmask)

        if not success:
            logger.error(f"[{self._ip_address}] Failed to send UTMC action {action_type}: {result}")

        return success

    # --- Built-in Action Handlers ---

    def _handle_flash(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        logger.debug(f"[{self._ip_address}] Sending UTMC FLASH MODE command")
        oid = self._config.get_system_oid("flash")
        return self._snmp_set(oid, 1) if oid else (False, "Missing flash OID")

    def _handle_release_flash(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        logger.debug(f"[{self._ip_address}] Sending UTMC RELEASE FLASH MODE command")
        oid = self._config.get_system_oid("flash")
        return self._snmp_set(oid, 0) if oid else (False, "Missing flash OID")

    def _handle_dark(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        logger.debug(f"[{self._ip_address}] Sending UTMC DARK MODE command")
        oid = self._config.get_system_oid("dark")
        return self._snmp_set(oid, 1) if oid else (False, "Missing dark OID")

    def _handle_release_dark(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        logger.debug(f"[{self._ip_address}] Sending UTMC RELEASE DARK MODE command")
        oid = self._config.get_system_oid("dark")
        return self._snmp_set(oid, 0) if oid else (False, "Missing dark OID")

    def _handle_release_hold(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        logger.debug(f"[{self._ip_address}] Sending UTMC RELEASE HOLD command")
        oid = self._config.get_stage_oid("hold")
        return self._snmp_set(oid, 0) if oid else (False, "Missing hold OID")

    def _handle_hold(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        stage = action_data.get("stage", 0)
        logger.debug(f"[{self._ip_address}] Sending UTMC HOLD for stage {stage}")
        oid = self._config.get_stage_oid("hold")
        return self._snmp_set(oid, bitmask) if oid else (False, "Missing hold OID")

    def _handle_force_off(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        stage = action_data.get("stage", 0)
        logger.debug(f"[{self._ip_address}] Sending UTMC FORCE-OFF for stage {stage}")
        oid = self._config.get_stage_oid("force_off")
        return self._snmp_set(oid, bitmask) if oid else (False, "Missing force_off OID")

    def _handle_omit(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        stage = action_data.get("stage", 0)
        logger.debug(f"[{self._ip_address}] Sending UTMC OMIT for stage {stage}")
        oid = self._config.get_stage_oid("omit")
        return self._snmp_set(oid, bitmask) if oid else (False, "Missing omit OID")

    def _handle_demand(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        stage = action_data.get("stage", 0)
        logger.debug(f"[{self._ip_address}] Sending UTMC DEMAND (Call) for stage {stage}")
        oid = self._config.get_telemetry_oid("status_demand")
        return self._snmp_set(oid, bitmask) if oid else (False, "Missing status_demand OID")

    def _handle_extend(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        stage = action_data.get("stage", 0)
        logger.debug(f"[{self._ip_address}] Sending UTMC EXTEND for stage {stage}")
        oid = self._config.get_stage_oid("extend")
        return self._snmp_set(oid, bitmask) if oid else (False, "Missing extend OID")

    def _handle_activate_local_fixed_time(self, action_data: Dict[str, Any], bitmask: int) -> Tuple[bool, Any]:
        logger.critical(
            f"[{self._ip_address}] EXECUTING FAILSAFE: Forcing ALL RED for 2 seconds, then releasing to local plans."
        )
        # Compute all-red mask based on green stages count
        num_stages = len(self._green_stages) if self._green_stages else 8
        all_red_mask = (1 << num_stages) - 1 if num_stages > 0 else 65535

        force_off_oid = self._config.get_stage_oid("force_off")
        omit_oid = self._config.get_stage_oid("omit")

        if force_off_oid:
            self._snmp_set(force_off_oid, all_red_mask)
        if omit_oid:
            self._snmp_set(omit_oid, all_red_mask)

        time.sleep(2.0)

        # Release omit so local controller can resume its fixed-time cycle
        success, result = self._snmp_set(omit_oid, 0) if omit_oid else (False, "Missing omit OID")

        # Stop the heartbeat so the controller fully reverts to local mode
        if self._stop_heartbeat_cb:
            self._stop_heartbeat_cb()

        return success, result
