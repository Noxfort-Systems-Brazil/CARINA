# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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

# File: src/settings/ini_storage.py
# Author: Gabriel Moraes
# Date: 2026-09-12

"""
Handles atomic, safe I/O for INI configuration files using configparser.
Complies with Single Responsibility Principle (SRP).
"""

import configparser
import logging
import os
from typing import Optional

try:
    from settings.interfaces import ISettingsStorage
except ImportError:
    from src.settings.interfaces import ISettingsStorage

try:
    from utils.paths import resource_path
except ImportError:
    from src.utils.paths import resource_path


class IniFileStorage(ISettingsStorage):
    """Encapsulates disk operations for reading and writing INI configuration files."""

    def __init__(self, file_path: Optional[str] = None):
        if file_path:
            self._file_path = file_path
        else:
            self._file_path = resource_path(os.path.join("config", "settings.ini"))

    @property
    def storage_path(self) -> str:
        return self._file_path

    def exists(self) -> bool:
        """Returns whether the configuration file exists on disk."""
        return os.path.isfile(self._file_path)

    def read_config(self) -> configparser.ConfigParser:
        """
        Reads and parses the INI file from disk.
        Raises FileNotFoundError if the file does not exist.
        """
        config = configparser.ConfigParser()
        if not self.exists():
            logging.error(f"[IniFileStorage] Configuration file not found at {self._file_path}")
            raise FileNotFoundError(f"Settings file not found at {self._file_path}")
        config.read(self._file_path, encoding="utf-8")
        return config

    def write_config(self, config: configparser.ConfigParser) -> bool:
        """
        Atomically writes the ConfigParser structure to the INI file.
        Returns True on success, False on IOError.
        """
        try:
            parent_dir = os.path.dirname(self._file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            with open(self._file_path, "w", encoding="utf-8") as configfile:
                config.write(configfile)
            logging.info(f"[IniFileStorage] Settings saved successfully at {self._file_path}")
            return True
        except IOError as e:
            logging.error(f"[IniFileStorage] Failed to write configuration file: {e}")
            return False
