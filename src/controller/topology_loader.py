# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Topology Loader
---------------
Handles loading and processing of SUMO network topology files for the fixed-time controller.
"""

import logging
from typing import List, Tuple

from src.controller.common_types import StageDefinition
from src.controller.stage_derivator import derive_yellow_state
from src.controller.stage_extractor import extract_green_stages
from src.controller.stage_validator import validate_stages
from src.domain.value_objects import IntersectionData

logger = logging.getLogger(__name__)


class TopologyLoader:
    """
    Handles loading and processing of SUMO network topology files.

    This class is responsible for:
    - Parsing SUMO .net.xml files
    - Extracting traffic light programs
    - Processing phases for fixed-time control
    """

    def __init__(self, green_chars: frozenset = frozenset({"G", "g"})):
        """
        Args:
            green_chars: Set of characters considered as green signals in SUMO
        """
        self._green_chars = green_chars

    def load_topology(self, net_file_path: str) -> Tuple[List[IntersectionData], bool]:
        """
        Extract TLS programs from the SUMO .net.xml network file.

        Args:
            net_file_path: Absolute path to the .net.xml file.

        Returns:
            Tuple of (list of intersection data, success flag)
        """
        try:
            import sumolib  # type: ignore

            net = sumolib.net.readNet(net_file_path, withPrograms=True, withInternal=False)
        except ImportError:
            logger.error("[TopologyLoader] sumolib not available. Cannot load topology.")
            return [], False
        except Exception as e:
            logger.error(f"[TopologyLoader] Failed to parse network file '{net_file_path}': {e}", exc_info=True)
            return [], False

        tls_list = net.getTrafficLights()
        if not tls_list:
            logger.warning("[TopologyLoader] No traffic lights found in topology.")
            return [], False

        intersections = []
        loaded_count = 0
        for tls in tls_list:
            tls_id = tls.getID()
            programs = tls.getPrograms()

            if not programs:
                logger.warning(f"[TopologyLoader] TLS '{tls_id}' has no programs. Skipping.")
                continue

            # Use the first (default) program — program ID "0" in SUMO convention
            program = list(programs.values())[0]
            original_stages = program.getPhases()

            # Extract GREEN phases (phases that have actual green movement)
            # Filter out pure-yellow and pure-red transitional phases
            green_stages = extract_green_stages(tls_id, original_stages, self._green_chars)

            if not green_stages:
                logger.warning(
                    f"[TopologyLoader] TLS '{tls_id}' has no usable green stages. "
                    f"Will remain ALL_RED during failsafe."
                )
                continue

            # Build PhaseDefinitions with derived yellow and all-red strings
            phase_definitions = []
            for state_str in green_stages:
                yellow_str = derive_yellow_state(state_str)
                all_red_str = "r" * len(state_str)
                phase_definitions.append(
                    StageDefinition(state_string=state_str, yellow_string=yellow_str, all_red_string=all_red_str)
                )

            # SAFETY VALIDATION: verify each phase's internal consistency
            if not validate_stages(tls_id, phase_definitions):
                logger.critical(
                    f"[TopologyLoader] ⚠️  VALIDATION FAILED for TLS '{tls_id}'! "
                    f"This intersection will remain ALL_RED permanently during failsafe."
                )
                # Force permanent ALL_RED for this intersection
                signal_len = len(green_stages[0])
                all_red = "r" * signal_len
                phase_definitions = [
                    StageDefinition(state_string=all_red, yellow_string=all_red, all_red_string=all_red)
                ]

            intersections.append(IntersectionData(tls_id=tls_id, phase_definitions=phase_definitions))
            loaded_count += 1

            cycle_length = (2.0 + 4.0 + 15.0) * len(phase_definitions)  # Default timings
            logger.info(
                f"[TopologyLoader] TLS '{tls_id}': {len(phase_definitions)} phases, " f"cycle = {cycle_length:.0f}s"
            )

        logger.info(
            f"[TopologyLoader] Topology loaded: {loaded_count} intersections ready "
            f"({len(tls_list) - loaded_count} skipped)."
        )
        return intersections, loaded_count > 0
