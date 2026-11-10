# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MapAssetLoader.

This specialized class has the sole responsibility of finding and loading
asset files (maps, coordinates) from the most recent simulation results directory.
"""

import json
import logging

# Importing the src is necessary for the UI module to find the utils module
from typing import Any, Dict, Tuple

from src.utils.map_data_parser import parse_map_data
from ui.loader.map_asset_loader import MapAssetLoader as StandardMapAssetLoader


class MapAssetLoader(StandardMapAssetLoader):
    """Finds and loads asset files from the most recent simulation (Handler wrapper)."""

    pass
