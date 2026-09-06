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

# File: src/drivers/ntcip_driver.py
# Author: Gabriel Moraes
# Date: 2026-08-14

"""
NTCIP 1202 protocol implementation for traffic light controllers.
Acts as a Facade / Orchestrator uniting configuration, HAL translation,
telemetry parsing, and action execution (SOLID architecture).
"""

import logging
from typing import Any, Dict, List, Optional

from src.drivers.base_driver import BaseTrafficDriver
from src.drivers.ntcip_action_executor import NtcipActionExecutor
from src.drivers.ntcip_config import NtcipConfig
from src.drivers.ntcip_stage_mapper import NtcipStageMapper
from src.drivers.ntcip_telemetry import NtcipTelemetryCollector

logger = logging.getLogger(__name__)


class NtcipDriver(BaseTrafficDriver):
    """
    Driver specifically built to handle the NTCIP 1202 protocol.
    Acts as a Facade / Orchestrator that delegates specialized responsibilities
    to NtcipConfig, NtcipStageMapper, NtcipActionExecutor, and NtcipTelemetryCollector.
    """

    def __init__(
        self,
        ip_address: str,
        port: int,
        intersection_id: str = "Desconhecido",
        community_string: str = "public",
        green_stages: Optional[List[int]] = None,
        config: Optional[NtcipConfig] = None,
        stage_mapper: Optional[NtcipStageMapper] = None,
        action_executor: Optional[NtcipActionExecutor] = None,
        telemetry_collector: Optional[NtcipTelemetryCollector] = None,
    ) -> None:
        super().__init__(ip_address, port, intersection_id, community_string, green_stages=green_stages)

        # 1. Configuration / OID Repository (SRP & DIP)
        self.config = config or NtcipConfig()

        # 2. Stage-to-Phase HAL Mapper (SRP & OCP)
        self.stage_mapper = stage_mapper or NtcipStageMapper(self.config.stage_to_phase_map)

        # 3. Action / Command Executor (SRP & OCP)
        self.action_executor = action_executor or NtcipActionExecutor(
            snmp_set_fn=lambda oid, val, vt=None: self.snmp_set(oid, val, vt),
            config=self.config,
            ip_address=self.ip_address,
            stop_heartbeat_cb=self.stop_heartbeat,
            green_stages=self.green_stages,
        )

        # 4. Telemetry Collector (SRP)
        self.telemetry_collector = telemetry_collector or NtcipTelemetryCollector(
            snmp_get_fn=lambda oid: self.snmp_get(oid), config=self.config, ip_address=self.ip_address
        )

        logger.info(f"[{self.ip_address}:{self.port}] Initialized NTCIP Driver (Facade Architecture).")

    # =========================================================================
    # Properties for Backwards Compatibility
    # =========================================================================

    @property
    def oids(self) -> Dict[str, Any]:
        """Exposes OID mappings for backward compatibility."""
        return self.config.oids

    @oids.setter
    def oids(self, value: Dict[str, Any]) -> None:
        self.config.oids = value

    @property
    def stage_to_phase_map(self) -> Dict[int, int]:
        """Exposes dynamic stage-to-phase mapping."""
        return self.config.stage_to_phase_map

    @stage_to_phase_map.setter
    def stage_to_phase_map(self, value: Dict[int, int]) -> None:
        self.config._stage_to_phase_map = value

    # =========================================================================
    # Protocol Interface Implementations
    # =========================================================================

    def get_protocol_name(self) -> str:
        return "NTCIP 1202"

    def convert_stage_to_hardware_mask(
        self, stage_idx: int, green_stages: List[int], stage_codes: Optional[Dict[int, str]] = None
    ) -> int:
        """
        HAL Translation: Delegates stage index and SUMO state string conversion
        to the dedicated NtcipStageMapper.
        """
        return self.stage_mapper.convert_stage_to_hardware_mask(
            stage_idx=stage_idx,
            green_stages=green_stages,
            stage_codes=stage_codes,
            stage_to_phase_map=self.config.stage_to_phase_map,
        )

    def send_action(self, action_data: Dict[str, Any]) -> bool:
        """
        Translates and dispatches CARINA actions by delegating to NtcipActionExecutor.
        """
        return self.action_executor.execute(action_data)

    def get_telemetry(self) -> Dict[str, Any]:
        """
        Fetches current intersection status by delegating to NtcipTelemetryCollector.
        """
        return self.telemetry_collector.collect()

    def send_heartbeat_pulse(self) -> bool:
        """
        Sends a heartbeat pulse to maintain remote control over the NTCIP controller.
        """
        heartbeat_oid = self.config.get_system_oid("heartbeat")
        if not heartbeat_oid:
            logger.error(f"[{self.ip_address}] Missing heartbeat OID in NTCIP configuration.")
            return False

        success, result = self.snmp_set(heartbeat_oid, 1)
        if not success:
            logger.error(f"[{self.ip_address}] NTCIP Heartbeat pulse failed: {result}")

        return success

    def apply_logical_action(
        self, action: int, current_stage_idx: int, green_stages: List[int], stage_codes: Optional[Dict[int, str]] = None
    ) -> bool:
        """
        Orchestrates NTCIP-specific logical action sequence translation.
        Translates raw AI actions (0 = NEXT_STAGE, 1 = HOLD) using NTCIP phase commands.
        """
        if not green_stages or current_stage_idx not in green_stages:
            return False

        try:
            current_list_idx = green_stages.index(current_stage_idx)

            if action == 0:  # NEXT_STAGE
                next_list_idx = (current_list_idx + 1) % len(green_stages)
                target_stage_idx = green_stages[next_list_idx]
                next_stage_mask = self.convert_stage_to_hardware_mask(target_stage_idx, green_stages, stage_codes)
                current_stage_mask = self.convert_stage_to_hardware_mask(current_stage_idx, green_stages, stage_codes)

                logger.info(
                    f"[{self.ip_address}] NTCIP HAL translating NEXT_STAGE: stage {current_stage_idx} -> "
                    f"{target_stage_idx} (mask {current_stage_mask} -> {next_stage_mask})"
                )

                # Protocol specific sequence translation:
                # 1. Release active hold
                self.send_action({"action_type": "release_hold"})

                # 2. Send FORCE_OFF command for current stage
                self.send_action({"action_type": "force_off", "stage_mask": current_stage_mask})

                # 3. Call next stage to trigger transition
                self.send_action({"action_type": "veh_call", "stage_mask": next_stage_mask})
                return True

            else:  # HOLD
                stage_mask = self.convert_stage_to_hardware_mask(current_stage_idx, green_stages, stage_codes)
                logger.debug(
                    f"[{self.ip_address}] NTCIP HAL translating HOLD for stage {current_stage_idx} (mask {stage_mask})"
                )
                return self.send_action({"action_type": "hold", "stage_mask": stage_mask})

        except Exception as e:
            logger.error(f"[{self.ip_address}] Error in NTCIP apply_logical_action: {e}")
            return False

    def release_control(self) -> bool:
        """
        Releases remote control holds, overrides, and force-offs on the NTCIP controller,
        safely returning the intersection to its local autonomous plan.
        """
        logger.info(
            f"[{self.ip_address}] Releasing NTCIP remote control commands (Release HOLD, OMIT, FORCE-OFF, FLASH, DARK)..."
        )
        success = True
        try:
            hold_oid = self.config.get_phase_oid("hold")
            if hold_oid:
                self.snmp_set(hold_oid, 0)

            force_off_oid = self.config.get_phase_oid("force_off")
            if force_off_oid:
                self.snmp_set(force_off_oid, 0)

            omit_oid = self.config.get_phase_oid("omit")
            if omit_oid:
                self.snmp_set(omit_oid, 0)

            flash_oid = self.config.get_system_oid("flash")
            if flash_oid:
                self.snmp_set(flash_oid, 0)

            dark_oid = self.config.get_system_oid("dark")
            if dark_oid:
                self.snmp_set(dark_oid, 0)

            logger.info(f"[{self.ip_address}] NTCIP remote control released successfully.")
        except Exception as e:
            logger.error(f"[{self.ip_address}] Error releasing NTCIP control: {e}")
            success = False

        return success
