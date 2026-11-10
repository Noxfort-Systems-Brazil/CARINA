# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Provides SumoGeoBoundsReader for fast, memory-efficient extraction of
geographic (origBoundary) and local Cartesian (convBoundary) bounds
from SUMO network files (.net.xml and .net.xml.gz).
Follows Single Responsibility Principle (SRP).
"""

import gzip
import logging
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class SumoGeoBounds:
    """Encapsulates geographic and Cartesian boundaries of a SUMO network."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    proj_parameter: Optional[str] = None
    net_offset: Tuple[float, float] = (0.0, 0.0)

    @property
    def has_geo_coords(self) -> bool:
        """Checks if the network contains valid geographic coordinates (WGS84)."""
        return not (self.min_lon == 0.0 and self.max_lon == 0.0 and self.min_lat == 0.0 and self.max_lat == 0.0)


class SumoGeoBoundsReader:
    """
    Parses <location> element from SUMO network files without loading
    the full network graph into memory.
    """

    @staticmethod
    def read_bounds(net_file_path: str) -> Optional[SumoGeoBounds]:
        """
        Reads bounds from a SUMO network file (.net.xml or .net.xml.gz).

        Args:
            net_file_path: Absolute or relative path to the .net.xml / .net.xml.gz file.

        Returns:
            SumoGeoBounds instance if <location> was found and parsed, or None.
        """
        if not net_file_path or not os.path.exists(net_file_path):
            logging.warning(f"[GeoBoundsReader] Arquivo de rede não encontrado: {net_file_path}")
            return None

        is_gzipped = net_file_path.endswith(".gz")

        try:
            open_fn = gzip.open if is_gzipped else open
            with open_fn(net_file_path, "rb") as f:
                # Use iterparse for high memory efficiency: stop at the first <location> tag
                context = ET.iterparse(f, events=("start",))
                for event, elem in context:
                    if elem.tag == "location":
                        bounds = SumoGeoBoundsReader._parse_location_element(elem)
                        elem.clear()
                        return bounds
                    # If we passed configuration or reached edges/junctions without <location>, abort early
                    if elem.tag in ("junction", "edge"):
                        break

            logging.warning(f"[GeoBoundsReader] Tag <location> não encontrada em: {net_file_path}")
            return None
        except Exception as e:
            logging.error(f"[GeoBoundsReader] Erro ao ler metadados geográficos de {net_file_path}: {e}", exc_info=True)
            return None

    @staticmethod
    def _parse_location_element(elem: ET.Element) -> Optional[SumoGeoBounds]:
        """Extracts boundaries from the XML <location> element."""
        try:
            conv_boundary_str = elem.attrib.get("convBoundary", "")
            orig_boundary_str = elem.attrib.get("origBoundary", "")
            proj_parameter = elem.attrib.get("projParameter")
            net_offset_str = elem.attrib.get("netOffset", "0,0")

            # Parse convBoundary (min_x, min_y, max_x, max_y)
            min_x, min_y, max_x, max_y = 0.0, 0.0, 0.0, 0.0
            if conv_boundary_str:
                parts = [float(v.strip()) for v in conv_boundary_str.split(",")]
                if len(parts) == 4:
                    min_x, min_y, max_x, max_y = parts

            # Parse origBoundary (min_lon, min_lat, max_lon, max_lat)
            min_lon, min_lat, max_lon, max_lat = 0.0, 0.0, 0.0, 0.0
            if orig_boundary_str:
                parts = [float(v.strip()) for v in orig_boundary_str.split(",")]
                if len(parts) == 4:
                    min_lon, min_lat, max_lon, max_lat = parts

            # Parse netOffset
            offset_x, offset_y = 0.0, 0.0
            if net_offset_str:
                offset_parts = [float(v.strip()) for v in net_offset_str.split(",")]
                if len(offset_parts) == 2:
                    offset_x, offset_y = offset_parts

            return SumoGeoBounds(
                min_lon=min_lon,
                min_lat=min_lat,
                max_lon=max_lon,
                max_lat=max_lat,
                min_x=min_x,
                min_y=min_y,
                max_x=max_x,
                max_y=max_y,
                proj_parameter=proj_parameter,
                net_offset=(offset_x, offset_y),
            )
        except Exception as e:
            logging.error(f"[GeoBoundsReader] Erro ao analisar atributos de <location>: {e}", exc_info=True)
            return None
