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

# File: ui/handlers/map_data_handler.py
# Author: Gabriel Moraes
# Date: September 2026

"""
Define o MapAssetLoader.

Esta classe especialista tem a responsabilidade única de encontrar e carregar
arquivos de ativos (mapas, coordenadas) do diretório de resultados da
simulação mais recente.
"""

import json
import logging
import os

# Importing the src is necessary for the UI module to find the utils module
import sys
from typing import Any, Dict, Tuple

project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path_to_add = os.path.join(project_root_path, "src")
if src_path_to_add not in sys.path:
    sys.path.insert(0, src_path_to_add)

from src.utils.map_data_parser import parse_map_data
from ui.loader.map_asset_loader import MapAssetLoader as StandardMapAssetLoader


class MapAssetLoader(StandardMapAssetLoader):
    """Encontra e carrega arquivos de ativos da simulação mais recente (Handler wrapper)."""

    pass
