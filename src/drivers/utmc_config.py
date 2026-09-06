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

# File: src/drivers/utmc_config.py
# Author: Gabriel Moraes
# Date: 2026-08-14

"""
Configuration provider and OID repository for UTMC2 protocol.
Decouples configuration loading and file I/O from driver business logic (SRP & DIP).
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "configs", "utmc_oids.json")


class UtmcConfig:
    """
    Encapsulates UTMC2 OID mappings and configuration definitions.
    Can be loaded from a JSON file or initialized directly with a configuration dictionary.
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._oids: Dict[str, Any] = {"stage_control": {}, "telemetry": {}, "system": {}}

        if config_dict is not None:
            self._load_from_dict(config_dict)
        else:
            self._load_from_file(self.config_path)

    def _load_from_file(self, path: str) -> None:
        """Loads configuration from a JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._load_from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load UTMC OIDs from {path}: {e}")
            self._oids = {"stage_control": {}, "telemetry": {}, "system": {}}

    def _load_from_dict(self, data: Dict[str, Any]) -> None:
        """Populates internal structures from a dictionary."""
        self._oids = data

    @property
    def oids(self) -> Dict[str, Any]:
        """Returns the raw OID dictionary for backwards compatibility."""
        return self._oids

    @oids.setter
    def oids(self, value: Dict[str, Any]) -> None:
        self._oids = value

    def get_stage_oid(self, name: str) -> Optional[str]:
        """Retrieves a stage control OID by name (e.g., 'hold', 'force_off', 'omit', 'extend')."""
        return self._oids.get("stage_control", {}).get(name)

    def get_telemetry_oid(self, name: str) -> Optional[str]:
        """Retrieves a telemetry OID by name (e.g., 'status_active', 'status_leaving', 'status_demand', 'status_ped_demand')."""
        return self._oids.get("telemetry", {}).get(name)

    def get_system_oid(self, name: str) -> Optional[str]:
        """Retrieves a system control OID by name (e.g., 'flash', 'dark', 'watchdog')."""
        return self._oids.get("system", {}).get(name)
