# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Loads and parses traffic light phase configurations from the SUMO network map (.net.xml / .net.xml.gz).
Isolated responsibility according to the Single Responsibility Principle (SRP).
"""

import gzip
import logging
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TrafficMapLoader:
    """
    Utility service to extract stage and phase definitions for specific
    traffic controllers from SUMO network topology maps.
    """

    @staticmethod
    def load_stage_states(
        intersection_id: str,
        map_file: Optional[str] = None,
        locale_manager: Optional[Any] = None,
    ) -> Dict[int, str]:
        """
        Parses the SUMO network map (.net.xml or .net.xml.gz) to extract
        the phase states for the given intersection_id.
        """

        def _get_string(key: str, default: str = None, **kwargs) -> str:
            if locale_manager and hasattr(locale_manager, "get_string"):
                return locale_manager.get_string(key, default=default, **kwargs)
            return default.format(**kwargs) if default and kwargs else (default or key)

        try:
            if not map_file:
                try:
                    from src.controller.map_discoverer import MapTopologyDiscoverer

                    map_file = MapTopologyDiscoverer.get_map_file()
                except Exception as discover_err:
                    logger.debug(f"[TrafficMapLoader] MapTopologyDiscoverer not available: {discover_err}")
                    return {}

            if not map_file or not os.path.exists(map_file):
                logger.warning(
                    _get_string(
                        "drivers.traffic_light.map_not_found",
                        default="[Intersection {id}] Map file not found: {path}",
                        id=intersection_id,
                        path=map_file,
                    )
                )
                return {}

            opener = gzip.open if map_file.endswith(".gz") else open
            with opener(map_file, "rt", encoding="utf-8") as f:
                tree = ET.parse(f)

            root = tree.getroot()
            states: Dict[int, str] = {}
            target_ids = {intersection_id, intersection_id.replace("tl_", ""), f"tl_{intersection_id}"}
            for tl in root.findall("tlLogic"):
                if tl.get("id") in target_ids:
                    for idx, phase in enumerate(tl.findall("phase")):
                        state = phase.get("state")
                        if state:
                            states[idx] = state
            return states

        except Exception as e:
            logger.error(
                _get_string(
                    "drivers.traffic_light.map_load_failed",
                    default="[Intersection {id}] Failed to load stage states from map: {error}",
                    id=intersection_id,
                    error=e,
                )
            , exc_info=True)
            return {}
