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

# File: src/drivers/ntcip_stage_mapper.py
# Author: Gabriel Moraes
# Date: 2026-08-14

"""
HAL Stage-to-Phase bitmask translation logic for NTCIP 1202 protocol.
Extracts mathematical translation and simulation parsing from the driver (SRP & OCP).
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NtcipStageMapper:
    """
    Translates simulation stage indices and SUMO state strings to NTCIP 1202 8-phase bitmasks.
    """

    def __init__(self, default_stage_to_phase_map: Optional[Dict[int, int]] = None) -> None:
        self.default_stage_to_phase_map = default_stage_to_phase_map or {}

    def convert_stage_to_hardware_mask(
        self,
        stage_idx: int,
        green_stages: List[int],
        stage_codes: Optional[Dict[int, str]] = None,
        stage_to_phase_map: Optional[Dict[int, int]] = None,
    ) -> int:
        """
        HAL Translation: Converts a SUMO stage index and its corresponding state string
        to an NTCIP 1202 phase bitmask.
        """
        mapping = stage_to_phase_map if stage_to_phase_map is not None else self.default_stage_to_phase_map
        stage_num = stage_idx + 1

        # Bypass hardcoded map if we have 5 stages (meaning transitional stages are included),
        # since the 4-stage map wouldn't map them correctly.
        use_hardcoded = len(green_stages) == 4 and stage_num in mapping

        if use_hardcoded:
            mask = mapping[stage_num]
            logger.debug(f"[HAL NTCIP 1202] Using hardcoded map for stage {stage_num} -> phase mask: {mask}")
            return mask

        if stage_codes and stage_idx in stage_codes:
            state_str = stage_codes[stage_idx]
            # Find active indices (only green 'g' or yellow 'y' characters)
            active_indices = [i for i, char in enumerate(state_str) if char.lower() in ("g", "y")]
            if not active_indices:
                logger.debug(f"[HAL NTCIP 1202] All red state for stage index {stage_idx} -> phase mask: 0")
                return 0

            # Map each active index to NTCIP phase.
            # Since standard NTCIP has 8 phases, we map index `i` to bit `i % 8`.
            mask = 0
            for idx in active_indices:
                mask |= 1 << (idx % 8)
            logger.debug(
                f"[HAL NTCIP 1202] Dynamically mapped stage index {stage_idx} (state: '{state_str}') -> phase mask: {mask}"
            )
            return mask

        # Fallback to direct bit shifting
        mask = 1 << stage_idx
        logger.debug(f"[HAL NTCIP 1202] Fallback mapping for stage index {stage_idx} -> phase mask: {mask}")
        return mask
