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

# File: src/drivers/ntcip_config.py
# Author: Gabriel Moraes
# Date: 2026-08-14

"""
Configuration provider and OID repository for NTCIP 1202 protocol.
Decouples configuration loading and file I/O from driver business logic (SRP & DIP).
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "configs", "ntcip_oids.json")


class NtcipConfig:
    """
    Encapsulates NTCIP 1202 OID mappings and configuration definitions.
    Can be loaded from a JSON file or initialized directly with a configuration dictionary.
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._oids: Dict[str, Any] = {"phase_control": {}, "telemetry": {}, "system": {}}
        self._stage_to_phase_map: Dict[int, int] = {}

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
            logger.error(f"Failed to load NTCIP OIDs from {path}: {e}")
            self._oids = {"phase_control": {}, "telemetry": {}, "system": {}}
            self._stage_to_phase_map = {}

    def _load_from_dict(self, data: Dict[str, Any]) -> None:
        """Populates internal structures from a dictionary."""
        self._oids = data
        raw_map = data.get("stage_to_phase_map", {})
        self._stage_to_phase_map = {int(k): int(v) for k, v in raw_map.items()}

    @property
    def oids(self) -> Dict[str, Any]:
        """Returns the raw OID dictionary for backwards compatibility."""
        return self._oids

    @property
    def stage_to_phase_map(self) -> Dict[int, int]:
        """Returns the parsed mapping from stage index (1-based) to NTCIP phase bitmask."""
        return self._stage_to_phase_map

    def get_phase_oid(self, name: str) -> Optional[str]:
        """Retrieves a phase control OID by name (e.g., 'hold', 'force_off', 'omit', etc.)."""
        return self._oids.get("phase_control", {}).get(name)

    def get_telemetry_oid(self, name: str) -> Optional[str]:
        """Retrieves a telemetry OID by name (e.g., 'status_greens', 'status_yellows', etc.)."""
        return self._oids.get("telemetry", {}).get(name)

    def get_system_oid(self, name: str) -> Optional[str]:
        """Retrieves a system control OID by name (e.g., 'flash', 'dark', 'heartbeat')."""
        return self._oids.get("system", {}).get(name)
