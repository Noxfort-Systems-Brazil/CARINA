# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Description:
Responsible for discovering intersection IDs and stage information from SUMO network map files.
Helps satisfy Single Responsibility Principle (SRP) for Connection Manager.
"""

import glob
import gzip
import logging
import os
import xml.etree.ElementTree as ET
from typing import List

from src.utils.paths import get_base_output_dir

logger = logging.getLogger(__name__)


class MapTopologyDiscoverer:
    """
    Helper class responsible for parsing network map files and extracting topology information.
    """

    @staticmethod
    def get_map_file() -> str:
        """
        Locates the SUMO network map file (.net.xml or .net.xml.gz).
        """
        maps_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session", "maps")
        search_gz = os.path.join(maps_dir, "*.net.xml.gz")
        search_xml = os.path.join(maps_dir, "*.net.xml")
        files = glob.glob(search_gz) + glob.glob(search_xml)
        return files[0] if files else ""

    @classmethod
    def discover_intersections(cls) -> List[str]:
        """
        Scans the map file and extracts all valid traffic light intersection IDs.
        """
        target_file = cls.get_map_file()
        if not target_file:
            logger.warning("No network map found. Intersections list will be empty.")
            return []

        tl_ids = set()
        try:
            opener = gzip.open if target_file.endswith(".gz") else open
            with opener(target_file, "rt", encoding="utf-8") as f:
                tree = ET.parse(f)

            root = tree.getroot()
            for tl in root.findall("tlLogic"):
                tl_id = tl.get("id")
                if tl_id:
                    tl_ids.add(tl_id)

            logger.info(f"Discovered {len(tl_ids)} intersections from {os.path.basename(target_file)}.")
            return sorted(list(tl_ids))
        except Exception as e:
            logger.error(f"Failed to parse network file {target_file} for intersections: {e}", exc_info=True)
            return []

    @classmethod
    def get_green_stages(cls, intersection_id: str) -> List[int]:
        """
        Parses the map file to extract all stage indices for a specific intersection (no filtering).
        """
        target_file = cls.get_map_file()
        if not target_file:
            return []

        try:
            opener = gzip.open if target_file.endswith(".gz") else open
            with opener(target_file, "rt", encoding="utf-8") as f:
                tree = ET.parse(f)

            root = tree.getroot()
            target_ids = {str(intersection_id), str(intersection_id).replace("tl_", ""), f"tl_{intersection_id}"}
            for tl_logic in root.findall("tlLogic"):
                if tl_logic.get("id") in target_ids:
                    return list(range(len(tl_logic.findall("phase"))))
        except Exception as e:
            logger.error(f"Failed to parse stages for intersection {intersection_id}: {e}", exc_info=True)
        return []
