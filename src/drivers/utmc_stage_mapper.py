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

# File: src/drivers/utmc_stage_mapper.py
# Author: Gabriel Moraes
# Date: 2026-08-14

"""
HAL Stage bitmask translation logic for UTMC2 protocol.
Extracts mathematical translation from the driver class (SRP & OCP).
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class UtmcStageMapper:
    """
    Translates simulation stage indices and SUMO state strings to UTMC2 stage bitmasks.
    """

    def convert_stage_to_hardware_mask(
        self, stage_idx: int, green_stages: Optional[List[int]] = None, stage_codes: Optional[Dict[int, str]] = None
    ) -> int:
        """
        HAL Translation: Converts a SUMO stage index and its corresponding state string
        to a UTMC2 stage bitmask.
        """
        # UTMC2 expects a stage bitmask where stage_idx corresponds to bit `stage_idx`.
        mask = 1 << stage_idx
        if stage_codes and stage_idx in stage_codes:
            state_str = stage_codes[stage_idx]
            logger.debug(
                f"[HAL UTMC2] Translating stage index {stage_idx} (state: '{state_str}') -> stage mask: {mask}"
            )
        else:
            logger.debug(f"[HAL UTMC2] Translating stage index {stage_idx} (no state string) -> stage mask: {mask}")

        return mask
